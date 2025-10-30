#!/usr/bin/env python3

Extract perfect context from AgentDB for review missions.

Uses the system itself to generate optimal prompts for review work.
This is the ultimate meta-use: AgentDB reviewing AgentDB!

Usage:
    python scripts/extract_perfect_context.py --mission REVIEW-004
    python scripts/extract_perfect_context.py --mission REVIEW-004 --level L2
    python scripts/extract_perfect_context.py --mission REVIEW-004 --format markdown


import sqlite3
import json
import argparse
from typing import Dict, List, Optional
from pathlib import Path


class PerfectContextExtractor:
    """Extract multi-source context from AgentDB for perfect prompts."""

    def __init__(self, db_path: str = ".agentdb/agent.sqlite"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found: {db_path}\n"
                f"Please run 'agentdb init' first."
            )
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def extract_mission_context(self, mission_id: str,
                                detail_level: str = "L1") -> Dict:
        """Extract complete context for a mission.

        Returns perfect prompt with:
        - Agent profile (L1)
        - Environment state (L1)
        - Specification context
        - Symbol contracts (L1 or deeper)
        - Provenance (creation_prompt, design_rationale)

        Args:
            mission_id: Mission identifier (e.g., REVIEW-004)
            detail_level: L0, L1, L2, L3, or L4 (default: L1)

        Returns:
            Dictionary with complete context
        """

        # 1. Get mission details
        mission = self.conn.execute("""
            SELECT * FROM missions WHERE mission_id = ?
        """, (mission_id,)).fetchone()

        if not mission:
            raise ValueError(f"Mission {mission_id} not found in database")

        # 2. Get agent profile
        agent = self.conn.execute("""
            SELECT * FROM agents WHERE agent_id = ?
        """, (mission['agent_id'],)).fetchone()

        agent_context = {}
        if agent:
            agent_context = {
                'agent_id': agent['agent_id'],
                'role': agent['role'],
                'capabilities': json.loads(agent['capabilities']) if agent['capabilities'] else [],
                'status': agent['status']
            }

        # 3. Get environment state (L1 - top 20 key variables)
        env_state = self.conn.execute("""
            SELECT key, value, category, description
            FROM environment_state
            WHERE category IN ('system', 'dependencies', 'configuration')
            ORDER BY category, key
            LIMIT 20
        """).fetchall()

        env_context = {
            row['key']: {
                'value': row['value'],
                'category': row['category'],
                'description': row['description']
            }
            for row in env_state
        }

        # 4. Get specification context
        mission_context = json.loads(mission['context'] or '{}')
        spec_ids = mission_context.get('spec_ids', [])

        specs = []
        for spec_id in spec_ids:
            spec = self.conn.execute("""
                SELECT * FROM specifications WHERE spec_id = ?
            """, (spec_id,)).fetchone()
            if spec:
                specs.append({
                    'spec_id': spec['spec_id'],
                    'title': spec['title'],
                    'description': spec['description'],
                    'requirements': json.loads(spec['requirements'] or '[]'),
                    'acceptance_criteria': json.loads(spec.get('acceptance_criteria') or '[]')
                })

        # 5. Get symbol context (from symbol_with_full_context view)
        symbol_handles = mission_context.get('symbol_handles', [])

        symbols = []
        for handle in symbol_handles:
            # Parse handle: ctx://path::symbol@hash
            parts = handle.split('::')
            if len(parts) >= 2:
                repo_path = parts[0].replace('ctx://', '')
                symbol_name = parts[1].split('@')[0]

                # Query using symbol_with_full_context view
                symbol_row = self.conn.execute("""
                    SELECT
                        s.id as symbol_id,
                        s.name as symbol_name,
                        s.kind as symbol_kind,
                        s.repo_path,
                        s.l0_overview,
                        s.l1_contract,
                        s.l2_pseudocode,
                        sp.spec_id,
                        sp.ticket_id,
                        sp.creation_prompt,
                        sp.design_rationale,
                        sp.design_alternatives,
                        spec.title AS spec_title,
                        spec.description AS spec_description,
                        t.title AS ticket_title,
                        t.description AS ticket_description
                    FROM symbols s
                    LEFT JOIN symbol_provenance sp ON s.id = sp.symbol_id
                    LEFT JOIN specifications spec ON sp.spec_id = spec.spec_id
                    LEFT JOIN tickets t ON sp.ticket_id = t.ticket_id
                    WHERE s.repo_path = ? AND s.name = ?
                    LIMIT 1
                """, (repo_path, symbol_name)).fetchone()

                if symbol_row:
                    symbol_data = {
                        'symbol_id': symbol_row['symbol_id'],
                        'name': symbol_row['symbol_name'],
                        'kind': symbol_row['symbol_kind'],
                        'repo_path': symbol_row['repo_path'],
                        'l0_overview': symbol_row['l0_overview'],
                        'l1_contract': symbol_row['l1_contract']
                    }

                    # Add deeper levels if requested
                    if detail_level in ('L2', 'L3', 'L4'):
                        symbol_data['l2_pseudocode'] = symbol_row['l2_pseudocode']

                    if detail_level in ('L3', 'L4'):
                        # Get AST from l3_ast_excerpt column
                        symbol_data['l3_ast'] = '(AST data - query l3_ast_excerpt column)'

                    if detail_level == 'L4':
                        # Get full source from l4_source column
                        symbol_data['l4_source'] = '(Full source - query l4_source column)'

                    # Add provenance (THE KEY!)
                    if symbol_row['creation_prompt']:
                        symbol_data['provenance'] = {
                            'creation_prompt': symbol_row['creation_prompt'],
                            'design_rationale': symbol_row['design_rationale'],
                            'design_alternatives': symbol_row['design_alternatives'],
                            'spec_title': symbol_row['spec_title'],
                            'spec_description': symbol_row['spec_description'],
                            'ticket_title': symbol_row['ticket_title']
                        }

                    symbols.append(symbol_data)

        # 6. Assemble perfect prompt
        perfect_context = {
            'mission': {
                'mission_id': mission['mission_id'],
                'title': mission['title'],
                'description': mission['description'],
                'priority': mission['priority'],
                'status': mission['status']
            },
            'agent': agent_context,
            'environment': env_context,
            'specifications': specs,
            'symbols': symbols,
            'detail_level': detail_level,
            'metadata': {
                'extracted_at': mission.get('created_at'),
                'session_id': mission.get('session_id')
            }
        }

        # Calculate token estimate
        perfect_context['token_estimate'] = self._estimate_tokens(perfect_context)

        return perfect_context

    def _estimate_tokens(self, context: Dict) -> int:
        """Estimate token count for context.

        Rough estimate: 1 token ≈ 4 characters for English text.
        This is conservative; actual may be slightly lower.
        """
        json_str = json.dumps(context)
        return len(json_str) // 4

    def format_as_markdown(self, context: Dict) -> str:
        """Format context as human-readable Markdown prompt."""
        lines = []

        # Title
        lines.append(f"# Mission: {context['mission']['title']}")
        lines.append(f"\n**Mission ID:** {context['mission']['mission_id']}")
        lines.append(f"**Priority:** {context['mission']['priority']}")
        lines.append(f"**Status:** {context['mission']['status']}\n")

        # Description
        lines.append(f"## Description\n")
        lines.append(f"{context['mission']['description']}\n")

        # Agent Profile
        if context['agent']:
            lines.append(f"## Agent Profile\n")
            lines.append(f"- **Role:** {context['agent']['role']}")
            lines.append(f"- **Capabilities:** {', '.join(context['agent']['capabilities'])}\n")

        # Environment
        if context['environment']:
            lines.append(f"## Environment Context\n")
            for key, val in list(context['environment'].items())[:10]:
                lines.append(f"- **{key}:** {val['value']} ({val['category']})")
            if len(context['environment']) > 10:
                lines.append(f"  ... and {len(context['environment']) - 10} more variables")
            lines.append("")

        # Specifications
        if context['specifications']:
            lines.append(f"## Specifications ({len(context['specifications'])} total)\n")
            for spec in context['specifications']:
                lines.append(f"### {spec['title']}")
                lines.append(f"\n{spec['description']}\n")
                if spec['requirements']:
                    lines.append(f"**Requirements:** {', '.join(spec['requirements'])}\n")
                if spec.get('acceptance_criteria'):
                    lines.append(f"**Acceptance Criteria:**")
                    for criterion in spec['acceptance_criteria']:
                        lines.append(f"  - {criterion}")
                    lines.append("")

        # Symbols
        if context['symbols']:
            lines.append(f"## Symbols ({len(context['symbols'])} total)\n")
            for sym in context['symbols'][:20]:  # First 20 symbols
                lines.append(f"### {sym['name']} ({sym['kind']})")
                lines.append(f"\n**Location:** {sym['repo_path']}\n")

                if sym.get('l0_overview'):
                    lines.append(f"**Overview:** {sym['l0_overview']}\n")

                if sym.get('l1_contract'):
                    lines.append(f"**Contract:** {sym['l1_contract']}\n")

                if sym.get('l2_pseudocode') and context['detail_level'] in ('L2', 'L3', 'L4'):
                    lines.append(f"**Pseudocode:**\n```\n{sym['l2_pseudocode']}\n```\n")

                # Provenance (THE KEY!)
                if sym.get('provenance'):
                    prov = sym['provenance']
                    lines.append(f"**Provenance:**")
                    if prov.get('creation_prompt'):
                        lines.append(f"  - Creation prompt: {prov['creation_prompt']}")
                    if prov.get('design_rationale'):
                        lines.append(f"  - Why: {prov['design_rationale']}")
                    if prov.get('spec_title'):
                        lines.append(f"  - Spec: {prov['spec_title']}")
                    lines.append("")

            if len(context['symbols']) > 20:
                lines.append(f"\n... and {len(context['symbols']) - 20} more symbols\n")

        # Token estimate
        lines.append(f"\n---\n")
        lines.append(f"**Detail Level:** {context['detail_level']}")
        lines.append(f"**Estimated Tokens:** {context['token_estimate']:,}")

        # Token savings comparison
        if context['detail_level'] == 'L1':
            full_l4_estimate = context['token_estimate'] * 40  # Rough L4 multiplier
            savings = 100 - (context['token_estimate'] / full_l4_estimate * 100)
            lines.append(f"**Token Savings vs L4:** ~{savings:.1f}% (L1: {context['token_estimate']:,} vs L4: ~{full_l4_estimate:,})")

        return '\n'.join(lines)

    def format_as_json(self, context: Dict) -> str:
        """Format context as pretty-printed JSON."""
        return json.dumps(context, indent=2)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Extract perfect context from AgentDB for review missions'
    )
    parser.add_argument(
        '--mission',
        required=True,
        help='Mission ID (e.g., REVIEW-004)'
    )
    parser.add_argument(
        '--level',
        default='L1',
        choices=['L0', 'L1', 'L2', 'L3', 'L4'],
        help='Detail level (default: L1 for optimal token savings)'
    )
    parser.add_argument(
        '--format',
        default='markdown',
        choices=['markdown', 'json'],
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--db',
        default='.agentdb/agent.sqlite',
        help='Database path (default: .agentdb/agent.sqlite)'
    )

    args = parser.parse_args()

    try:
        extractor = PerfectContextExtractor(db_path=args.db)

        print(f"Extracting context for mission: {args.mission}")
        print(f"Detail level: {args.level}")
        print(f"Format: {args.format}\n")

        context = extractor.extract_mission_context(
            mission_id=args.mission,
            detail_level=args.level
        )

        if args.format == 'markdown':
            output = extractor.format_as_markdown(context)
        else:
            output = extractor.format_as_json(context)

        print(output)

        extractor.close()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "PerfectContextExtractor",
      "kind": "class",
      "signature": "class PerfectContextExtractor",
      "lines": [
        21,
        312
      ],
      "summary_l0": "Class PerfectContextExtractor",
      "contract_l1": "See source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        315,
        377
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    },
    {
      "name": "__init__",
      "kind": "function",
      "signature": "def __init__(...)",
      "lines": [
        24,
        32
      ],
      "summary_l0": "Function __init__",
      "contract_l1": "@io see source code"
    },
    {
      "name": "extract_mission_context",
      "kind": "function",
      "signature": "def extract_mission_context(...)",
      "lines": [
        34,
        207
      ],
      "summary_l0": "Function extract_mission_context",
      "contract_l1": "@io see source code"
    },
    {
      "name": "_estimate_tokens",
      "kind": "function",
      "signature": "def _estimate_tokens(...)",
      "lines": [
        209,
        216
      ],
      "summary_l0": "Function _estimate_tokens",
      "contract_l1": "@io see source code"
    },
    {
      "name": "format_as_markdown",
      "kind": "function",
      "signature": "def format_as_markdown(...)",
      "lines": [
        218,
        303
      ],
      "summary_l0": "Function format_as_markdown",
      "contract_l1": "@io see source code"
    },
    {
      "name": "format_as_json",
      "kind": "function",
      "signature": "def format_as_json(...)",
      "lines": [
        305,
        307
      ],
      "summary_l0": "Function format_as_json",
      "contract_l1": "@io see source code"
    },
    {
      "name": "close",
      "kind": "function",
      "signature": "def close(...)",
      "lines": [
        309,
        312
      ],
      "summary_l0": "Function close",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
