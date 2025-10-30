#!/usr/bin/env python3

"""
Auto-tag all Python files using Z.AI GLM.

This script:
1. Finds all Python files in src/
2. Extracts functions and classes
3. Uses GLM to generate L0/L1/L2 for each symbol
4. Appends AGTAG blocks to files
5. Ingests tagged files into agentdb

"""
Cost: ~$0.002 for entire codebase (vs $0.05 with Claude)
Time: ~2-3 minutes for ~12 Python files


import os
import sys
import ast
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agentdb.glm_generator import GLMGenerator


def extract_python_symbols(file_path: str) -> List[Dict[str, Any]]:
    """Extract functions and classes from Python file using AST.

    Args:
        file_path: Path to Python file

    Returns:
        List of symbols with name, kind, lines, code
    """

    with open(file_path, 'r') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"⚠️ Syntax error in {file_path}: {e}")
        return []

    symbols = []
    lines = content.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            start_line = node.lineno
            end_line = node.end_lineno or start_line

            # Extract code for this symbol
            symbol_code = '\n'.join(lines[start_line-1:end_line])

            # Determine kind
            kind = 'function' if isinstance(node, ast.FunctionDef) else 'class'

            # Get signature for functions
            signature = None
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                returns = ast.unparse(node.returns) if node.returns else 'Any'
                signature = f"def {node.name}({', '.join(args)}) -> {returns}"

            symbols.append({
                'name': node.name,
                'kind': kind,
                'start_line': start_line,
                'end_line': end_line,
                'code': symbol_code,
                'signature': signature,
                'repo_path': file_path
            })

    return symbols


def auto_tag_file(
    file_path: str,
    glm: GLMGenerator,
    dry_run: bool = False
) -> bool:
    """Auto-tag a single Python file with AGTAG block.

    Args:
        file_path: Path to Python file
        glm: GLM generator instance
        dry_run: If True, don't modify file

    Returns:
        True if successfully tagged
    """

    print(f"\n{'='*60}")
    print(f"Processing: {file_path}")
    print('='*60)

    # Read current content
    with open(file_path, 'r') as f:
        content = f.read()

    # Check if already has AGTAG
    if '<!--AGTAG v1 START-->' in content:
        print("⚠️ File already has AGTAG, skipping")
        return False

    # Extract symbols
    symbols = extract_python_symbols(file_path)

    if not symbols:
        print("⚠️ No functions or classes found")
        return False

    print(f"Found {len(symbols)} symbols:")
    for sym in symbols:
        print(f"  - {sym['kind']}: {sym['name']} (lines {sym['start_line']}-{sym['end_line']})")

    # Generate levels for each symbol
    print("\nGenerating L0/L1/L2 with GLM...")

    tagged_symbols = []

    for i, symbol in enumerate(symbols):
        print(f"\n{i+1}/{len(symbols)}: {symbol['name']}")

        try:
            levels = glm.generate_symbol_levels(
                code=symbol['code'],
                symbol_name=symbol['name'],
                repo_path=file_path,
                kind=symbol['kind']
            )

            # Combine symbol metadata with generated levels
            tagged_symbol = {
                'name': symbol['name'],
                'kind': symbol['kind'],
                'signature': symbol['signature'],
                'lines': [symbol['start_line'], symbol['end_line']],
                'summary_l0': levels['l0_overview'],
                'contract_l1': levels['l1_contract'],
                'pseudocode_l2': levels['l2_pseudocode']
            }

            tagged_symbols.append(tagged_symbol)

            print(f"  ✅ L0: {levels['l0_overview'][:60]}...")

        except Exception as e:
            print(f"  ❌ Failed: {e}")
            # Add placeholder
            tagged_symbols.append({
                'name': symbol['name'],
                'kind': symbol['kind'],
                'signature': symbol['signature'],
                'lines': [symbol['start_line'], symbol['end_line']],
                'summary_l0': f"Implements {symbol['name']}",
                'contract_l1': "@io see source code",
                'pseudocode_l2': "See source code"
            })

    # Create AGTAG block
    agtag = {
        'version': 'v1',
        'symbols': tagged_symbols
    }

    agtag_json = json.dumps(agtag, indent=2)

    # Append to file
    new_content = f"{content}\n\n<!--AGTAG v1 START-->\n{agtag_json}\n<!--AGTAG v1 END-->\n"

    if dry_run:
        print("\n[DRY RUN] Would append AGTAG:")
        print(agtag_json[:300] + "...")
    else:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"\n✅ AGTAG appended to {file_path}")

    return True


def auto_tag_all_python_files(
    project_root: str = ".",
    glm: GLMGenerator = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """Auto-tag all Python files in project.

    Args:
        project_root: Project root directory
        glm: GLM generator (or creates new one)
        dry_run: If True, don't modify files

    Returns:
        Dict with stats: tagged, skipped, failed
    """

    if glm is None:
        glm = GLMGenerator()

    # Find all Python files in src/
    src_dir = Path(project_root) / 'src'
    python_files = list(src_dir.rglob('*.py'))

    # Exclude __pycache__ and test files
    python_files = [
        f for f in python_files
        if '__pycache__' not in str(f) and 'test_' not in f.name
    ]

    print(f"\nFound {len(python_files)} Python files to process")

    stats = {'tagged': 0, 'skipped': 0, 'failed': 0}

    for file_path in python_files:
        try:
            success = auto_tag_file(str(file_path), glm, dry_run)
            if success:
                stats['tagged'] += 1
            else:
                stats['skipped'] += 1
        except Exception as e:
            print(f"\n❌ Error processing {file_path}: {e}")
            stats['failed'] += 1

    return stats


def ingest_tagged_files(project_root: str = "."):
    """Ingest all tagged Python files into agentdb.

    Runs agentdb ingest for each tagged file.
    """

    print("\n" + "="*60)
    print("Ingesting tagged files into agentdb...")
    print("="*60)

    src_dir = Path(project_root) / 'src'
    python_files = list(src_dir.rglob('*.py'))
    python_files = [
        f for f in python_files
        if '__pycache__' not in str(f) and 'test_' not in f.name
    ]

    for file_path in python_files:
        # Check if has AGTAG
        with open(file_path, 'r') as f:
            if '<!--AGTAG v1 START-->' not in f.read():
                continue

        # Get relative path from project root
        rel_path = file_path.relative_to(project_root)

        print(f"\nIngesting {rel_path}...")

        # Run agentdb ingest
        import subprocess
        result = subprocess.run(
            ['.venv/bin/agentdb', 'ingest', '--path', str(rel_path)],
            stdin=open(file_path, 'r'),
            capture_output=True,
            text=True,
            cwd=project_root
        )

        if result.returncode == 0:
            print(f"  ✅ Ingested successfully")
        else:
            print(f"  ❌ Failed: {result.stderr[:200]}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Auto-tag Python files with GLM')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without modifying files')
    parser.add_argument('--ingest', action='store_true',
                       help='Ingest tagged files into agentdb after tagging')
    parser.add_argument('--project-root', default='.',
                       help='Project root directory')

    args = parser.parse_args()

    # Check for API key
    if not os.getenv('Z_AI_API_KEY'):
        print("❌ Z_AI_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export Z_AI_API_KEY='ee18b161f3ce4bf6a314e914429bd91b.SHTDun4RNpiQjBNl'")
        exit(1)

    print("\n" + "="*60)
    print("Auto-tagging Python files with Z.AI GLM")
    print("="*60)
    print(f"Project root: {args.project_root}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("="*60)

    # Run auto-tagging
    glm = GLMGenerator()
    stats = auto_tag_all_python_files(
        project_root=args.project_root,
        glm=glm,
        dry_run=args.dry_run
    )

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Tagged:  {stats['tagged']} files")
    print(f"Skipped: {stats['skipped']} files (already tagged)")
    print(f"Failed:  {stats['failed']} files")

    # Cost estimate
    total_files = stats['tagged']
    estimated_tokens = total_files * 500  # ~500 tokens per file
    cost = estimated_tokens / 1_000_000 * 0.14  # $0.14/M
    print(f"\nEstimated cost: ${cost:.4f} (vs ${cost*21:.4f} with Claude)")

    # Ingest if requested
    if args.ingest and not args.dry_run and stats['tagged'] > 0:
        ingest_tagged_files(args.project_root)

    print("\n✅ Auto-tagging complete!")
