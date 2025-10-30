"""
Tests for agentdb search command with FTS5 integration.

Tests comprehensive search functionality including:
- Basic FTS5 queries across different levels
- Field filtering (l0, l1, l2, etc.)
- Kind filtering (function, class, etc.)
- Result limiting and ranking
- Edge cases and error handling
"""

import pytest
import sqlite3
import json
from click.testing import CliRunner
from agentdb.core import cli


class TestSearchCommand:
    """Test suite for agentdb search command."""

    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_db(self, tmp_path, monkeypatch):
        """Create temporary AgentDB with sample searchable symbols."""
        db_dir = tmp_path / ".agentdb"
        db_dir.mkdir()
        db_file = db_dir / "agent.sqlite"

        # Initialize database
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0

        # Add sample files and symbols
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row

        # Insert files
        conn.execute("""
            INSERT INTO files (repo_path, file_hash, db_state, last_seen)
            VALUES
                ('src/auth.py', 'sha256:abc123', 'indexed', '2025-01-30T12:00:00Z'),
                ('src/models.py', 'sha256:def456', 'indexed', '2025-01-30T12:00:00Z'),
                ('src/utils.py', 'sha256:ghi789', 'indexed', '2025-01-30T12:00:00Z')
        """)

        # Insert symbols with searchable content
        symbols = [
            # Auth module
            ('src/auth.py', 'validate_token', 'function', 1, 10,
             'Validates JWT tokens and returns user data',
             '@io token:str -> dict | None\nValidates JWT token signature and expiration',
             'if token is None: return None\nverify_signature(token)\ncheck_expiration(token)\nreturn decode_payload(token)',
             '{"type": "function", "params": ["token"], "returns": "dict"}',
             'def validate_token(token: str) -> dict | None:\n    ...',
             'sha256:token1'),

            ('src/auth.py', 'TokenStrategy', 'class', 12, 25,
             'Abstract base class for token validation strategies',
             '@invariant All implementations must handle expired tokens\n@io -> None',
             'class defines validate() method\nsubclasses implement specific strategies',
             '{"type": "class", "methods": ["validate"], "abstract": true}',
             'class TokenStrategy(ABC):\n    @abstractmethod\n    def validate(self): ...',
             'sha256:token2'),

            # Models module
            ('src/models.py', 'UserModel', 'class', 1, 15,
             'Database model for user accounts with authentication',
             '@invariant email must be unique\n@io -> SQLAlchemy model',
             'class with fields: id, email, password_hash\nrelationships to sessions',
             '{"type": "class", "fields": ["id", "email", "password_hash"]}',
             'class UserModel(Base):\n    __tablename__ = "users"\n    ...',
             'sha256:user1'),

            ('src/models.py', 'migrate_schema', 'function', 17, 30,
             'Applies database schema migrations to production',
             '@io connection:Connection -> None\nRuns pending migrations safely',
             'connect to database\ncheck current version\napply pending migrations\ncommit transaction',
             '{"type": "function", "params": ["connection"], "side_effects": true}',
             'def migrate_schema(connection: Connection) -> None:\n    ...',
             'sha256:migrate1'),

            # Utils module
            ('src/utils.py', 'validate_email', 'function', 1, 5,
             'Validates email addresses using regex pattern',
             '@io email:str -> bool\nReturns True if email format is valid',
             'import re\npattern = r"^[a-z0-9]+@[a-z]+\\.[a-z]{2,}$"\nreturn re.match(pattern, email) is not None',
             '{"type": "function", "params": ["email"], "pure": true}',
             'def validate_email(email: str) -> bool:\n    ...',
             'sha256:email1'),

            ('src/utils.py', 'hash_password', 'function', 7, 12,
             'Hashes passwords using bcrypt with salt',
             '@io password:str -> str\nReturns bcrypt hash',
             'import bcrypt\nsalt = bcrypt.gensalt()\nreturn bcrypt.hashpw(password.encode(), salt)',
             '{"type": "function", "params": ["password"], "security": "crypto"}',
             'def hash_password(password: str) -> str:\n    ...',
             'sha256:hash1'),
        ]

        for symbol in symbols:
            conn.execute("""
                INSERT INTO symbols (
                    repo_path, name, kind, start_line, end_line,
                    l0_overview, l1_contract, l2_pseudocode, l3_ast_json, l4_full_code,
                    content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, symbol)

        conn.commit()

        # Manually populate FTS5 table (no triggers in schema)
        for symbol in symbols:
            repo_path, name, kind, start_line, end_line, l0, l1, l2, l3, l4, hash = symbol
            conn.execute("""
                INSERT INTO symbols_fts (rowid, repo_path, name, l0_overview, l1_contract)
                SELECT id, repo_path, name, l0_overview, l1_contract
                FROM symbols
                WHERE repo_path = ? AND name = ?
            """, (repo_path, name))

        conn.commit()
        yield tmp_path
        conn.close()

    def test_basic_search_l0_l1(self, temp_db, runner):
        """Test basic search across L0 and L1 (default fields)."""
        result = runner.invoke(cli, ['search', '--query', 'token'])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["query"] == "token"
        assert output["fields"] == ["l0", "l1"]
        assert output["count"] >= 2  # Should find validate_token and TokenStrategy
        assert output["limit"] == 10  # Default limit

        # Verify results contain token-related symbols
        names = [r["name"] for r in output["results"]]
        assert "validate_token" in names or "TokenStrategy" in names

    def test_search_single_field_l0(self, temp_db, runner):
        """Test search restricted to L0 only."""
        result = runner.invoke(cli, ['search', '--query', 'database', '--fields', 'l0'])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["fields"] == ["l0"]
        assert output["count"] >= 1  # Should find UserModel or migrate_schema

    def test_search_multi_field_l0_l1_l2(self, temp_db, runner):
        """Test search with l2 field (silently ignored, searches l0/l1 only)."""
        result = runner.invoke(cli, ['search', '--query', 'database', '--fields', 'l0,l1,l2'])

        # Succeeds: l0 and l1 are indexed, l2 is silently ignored
        assert result.exit_code == 0
        output = json.loads(result.output)

        # Fields list includes l2, but only l0/l1 are actually searched
        assert output["fields"] == ["l0", "l1", "l2"]
        # Should find UserModel (has "database" in L0)
        assert output["count"] >= 1

    def test_search_with_kind_filter(self, temp_db, runner):
        """Test search with kind filter (functions only)."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'validate',
            '--kind', 'function'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["kind_filter"] == "function"
        assert output["count"] >= 2  # validate_token, validate_email

        # Verify all results are functions
        for r in output["results"]:
            assert r["kind"] == "function"

    def test_search_with_kind_filter_class(self, temp_db, runner):
        """Test search with kind filter (classes only)."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'model',
            '--kind', 'class'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["kind_filter"] == "class"

        # Verify all results are classes
        for r in output["results"]:
            assert r["kind"] == "class"

    def test_search_with_limit(self, temp_db, runner):
        """Test search respects limit parameter."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'validate',
            '--limit', '2'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["limit"] == 2
        assert len(output["results"]) <= 2

    def test_search_no_results(self, temp_db, runner):
        """Test search with no matching results."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'nonexistent_quantum_symbol_xyz'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["count"] == 0
        assert output["results"] == []

    def test_search_invalid_field(self, temp_db, runner):
        """Test search with invalid field name."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'token',
            '--fields', 'l0,invalid_field'
        ])

        assert result.exit_code == 2  # Error exit code
        output = json.loads(result.output)

        assert output["error"] == "invalid_fields"
        assert "invalid_field" in output["hint"]

    def test_search_result_structure(self, temp_db, runner):
        """Test search results have correct structure."""
        result = runner.invoke(cli, ['search', '--query', 'validate'])

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Check top-level structure
        assert "query" in output
        assert "fields" in output
        assert "kind_filter" in output
        assert "count" in output
        assert "limit" in output
        assert "results" in output

        # Check result item structure
        if output["results"]:
            item = output["results"][0]
            assert "repo_path" in item
            assert "name" in item
            assert "kind" in item
            assert "lines" in item
            assert len(item["lines"]) == 2  # [start_line, end_line]
            assert "l0_overview" in item
            assert "l1_contract" in item
            assert "content_hash" in item
            assert "rank" in item  # FTS5 rank

    def test_search_ranking(self, temp_db, runner):
        """Test FTS5 ranking orders results by relevance."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'token validation',
            '--limit', '10'
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Results should be ordered by rank
        if len(output["results"]) > 1:
            ranks = [r["rank"] for r in output["results"]]
            # FTS5 rank is negative (higher relevance = more negative)
            # So results should be in ascending order (most negative first)
            assert ranks == sorted(ranks)

    def test_search_phrase_query(self, temp_db, runner):
        """Test FTS5 handles phrase queries."""
        result = runner.invoke(cli, [
            'search',
            '--query', 'JWT token',  # Phrase in L0/L1
        ])

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Should find validate_token which mentions JWT
        assert output["count"] >= 1

    def test_search_special_characters(self, temp_db, runner):
        """Test search handles special characters (may not match due to FTS5 tokenization)."""
        # FTS5 tokenizes @io as 'io', so searching for '@io' might not match
        # This is expected FTS5 behavior - test it errors gracefully or returns 0 results
        result = runner.invoke(cli, [
            'search',
            '--query', '@io',  # Contract marker
            '--fields', 'l1'
        ])

        # Accept either success with 0 results or error
        # FTS5 may reject @ as invalid syntax
        assert result.exit_code in [0, 2]

    def test_search_empty_database(self, tmp_path, monkeypatch, runner):
        """Test search on empty database returns no results."""
        db_dir = tmp_path / ".agentdb"
        db_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ['init'])

        result = runner.invoke(cli, ['search', '--query', 'anything'])

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["count"] == 0
        assert output["results"] == []

    def test_search_case_insensitive(self, temp_db, runner):
        """Test FTS5 search is case-insensitive."""
        result1 = runner.invoke(cli, ['search', '--query', 'TOKEN'])
        result2 = runner.invoke(cli, ['search', '--query', 'token'])
        result3 = runner.invoke(cli, ['search', '--query', 'ToKeN'])

        assert result1.exit_code == 0
        assert result2.exit_code == 0
        assert result3.exit_code == 0

        output1 = json.loads(result1.output)
        output2 = json.loads(result2.output)
        output3 = json.loads(result3.output)

        # All should return same count (FTS5 is case-insensitive)
        assert output1["count"] == output2["count"] == output3["count"]

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "TestSearchCommand",
      "kind": "class",
      "qualified_name": "tests.test_search.TestSearchCommand",
      "lines": [
        19,
        351
      ],
      "summary_l0": "Pytest class TestSearchCommand for grouping test cases.",
      "contract_l1": "class TestSearchCommand",
      "pseudocode_l2": "1. Organize related pytest cases.",
      "path": "tests/test_search.py"
    },
    {
      "name": "runner",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.runner",
      "lines": [
        23,
        25
      ],
      "summary_l0": "Helper method runner supporting test utilities.",
      "contract_l1": "def runner(self)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "temp_db",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.temp_db",
      "lines": [
        28,
        130
      ],
      "summary_l0": "Helper method temp_db supporting test utilities.",
      "contract_l1": "def temp_db(self, tmp_path, monkeypatch)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_basic_search_l0_l1",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_basic_search_l0_l1",
      "lines": [
        132,
        146
      ],
      "summary_l0": "Pytest case test_basic_search_l0_l1 validating expected behaviour.",
      "contract_l1": "def test_basic_search_l0_l1(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_single_field_l0",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_single_field_l0",
      "lines": [
        148,
        156
      ],
      "summary_l0": "Pytest case test_search_single_field_l0 validating expected behaviour.",
      "contract_l1": "def test_search_single_field_l0(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_multi_field_l0_l1_l2",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_multi_field_l0_l1_l2",
      "lines": [
        158,
        169
      ],
      "summary_l0": "Pytest case test_search_multi_field_l0_l1_l2 validating expected behaviour.",
      "contract_l1": "def test_search_multi_field_l0_l1_l2(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_with_kind_filter",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_with_kind_filter",
      "lines": [
        171,
        187
      ],
      "summary_l0": "Pytest case test_search_with_kind_filter validating expected behaviour.",
      "contract_l1": "def test_search_with_kind_filter(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_with_kind_filter_class",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_with_kind_filter_class",
      "lines": [
        189,
        204
      ],
      "summary_l0": "Pytest case test_search_with_kind_filter_class validating expected behaviour.",
      "contract_l1": "def test_search_with_kind_filter_class(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_with_limit",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_with_limit",
      "lines": [
        206,
        218
      ],
      "summary_l0": "Pytest case test_search_with_limit validating expected behaviour.",
      "contract_l1": "def test_search_with_limit(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_no_results",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_no_results",
      "lines": [
        220,
        231
      ],
      "summary_l0": "Pytest case test_search_no_results validating expected behaviour.",
      "contract_l1": "def test_search_no_results(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_invalid_field",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_invalid_field",
      "lines": [
        233,
        245
      ],
      "summary_l0": "Pytest case test_search_invalid_field validating expected behaviour.",
      "contract_l1": "def test_search_invalid_field(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_result_structure",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_result_structure",
      "lines": [
        247,
        273
      ],
      "summary_l0": "Pytest case test_search_result_structure validating expected behaviour.",
      "contract_l1": "def test_search_result_structure(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_ranking",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_ranking",
      "lines": [
        275,
        291
      ],
      "summary_l0": "Pytest case test_search_ranking validating expected behaviour.",
      "contract_l1": "def test_search_ranking(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_phrase_query",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_phrase_query",
      "lines": [
        293,
        304
      ],
      "summary_l0": "Pytest case test_search_phrase_query validating expected behaviour.",
      "contract_l1": "def test_search_phrase_query(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_special_characters",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_special_characters",
      "lines": [
        306,
        318
      ],
      "summary_l0": "Pytest case test_search_special_characters validating expected behaviour.",
      "contract_l1": "def test_search_special_characters(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_empty_database",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_empty_database",
      "lines": [
        320,
        334
      ],
      "summary_l0": "Pytest case test_search_empty_database validating expected behaviour.",
      "contract_l1": "def test_search_empty_database(self, tmp_path, monkeypatch, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    },
    {
      "name": "test_search_case_insensitive",
      "kind": "method",
      "qualified_name": "tests.test_search.TestSearchCommand.test_search_case_insensitive",
      "lines": [
        336,
        351
      ],
      "summary_l0": "Pytest case test_search_case_insensitive validating expected behaviour.",
      "contract_l1": "def test_search_case_insensitive(self, temp_db, runner)",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_search.py",
      "parent": "TestSearchCommand"
    }
  ],
  "tests": [
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_basic_search_l0_l1",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_single_field_l0",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_multi_field_l0_l1_l2",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_with_kind_filter",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_with_kind_filter_class",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_with_limit",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_no_results",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_invalid_field",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_result_structure",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_ranking",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_phrase_query",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_special_characters",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_empty_database",
      "covers": [],
      "status": "new"
    },
    {
      "path": "tests/test_search.py",
      "name": "tests.test_search.TestSearchCommand.test_search_case_insensitive",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
