"""
Comprehensive test suite for src/agentdb/doc_zoom.py

Coverage target: 90%+
Tests: doc_zoom(), _get_available_levels(), main()
"""

import pytest
import sqlite3
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

from src.agentdb.doc_zoom import doc_zoom, _get_available_levels, main


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create temporary database with documents_multilevel table."""
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    conn = sqlite3.connect(db_path)

    # Create documents_multilevel table
    conn.execute("""
        CREATE TABLE documents_multilevel (
            id INTEGER PRIMARY KEY,
            doc_path TEXT NOT NULL,
            section_id TEXT NOT NULL,
            section_title TEXT,
            doc_type TEXT,
            file_hash TEXT,
            section_hash TEXT,
            start_line INTEGER,
            summary_l0 TEXT,
            contract_l1 TEXT,
            outline_l2 TEXT,
            excerpt_l3 TEXT,
            content_l4 TEXT,
            updated_at TEXT,
            UNIQUE(doc_path, section_id, file_hash)
        )
    """)

    # Insert test data
    conn.execute("""
        INSERT INTO documents_multilevel (
            doc_path, section_id, section_title, doc_type, file_hash, section_hash,
            start_line, summary_l0, contract_l1, outline_l2, excerpt_l3, content_l4,
            updated_at
        ) VALUES (
            'docs/API.md', 'POST_/symbols', 'POST /symbols', 'api_reference',
            'sha256:abc123', 'sha256:def456', 10,
            'Create new symbol', 'POST /symbols - Create symbol', 'Outline content',
            'Excerpt content', 'Full content here', '2025-01-01 12:00:00'
        )
    """)

    conn.execute("""
        INSERT INTO documents_multilevel (
            doc_path, section_id, section_title, doc_type, file_hash, section_hash,
            start_line, summary_l0, contract_l1, content_l4, updated_at
        ) VALUES (
            'docs/API.md', 'GET_/health', 'GET /health', 'api_reference',
            'sha256:abc123', 'sha256:xyz789', 50,
            'Health check endpoint', 'GET /health - Check system health',
            'Full health endpoint documentation', '2025-01-01 12:00:00'
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink()


@pytest.fixture
def sample_section():
    """Sample section dict for testing."""
    return {
        'id': 1,
        'doc_path': 'docs/API.md',
        'section_id': 'POST_/symbols',
        'section_title': 'POST /symbols',
        'doc_type': 'api_reference',
        'file_hash': 'sha256:abc123',
        'section_hash': 'sha256:def456',
        'start_line': 10,
        'summary_l0': 'Create new symbol',
        'contract_l1': 'POST /symbols - Create symbol',
        'outline_l2': 'Outline content',
        'excerpt_l3': 'Excerpt content',
        'content_l4': 'Full content here',
        'updated_at': '2025-01-01 12:00:00'
    }


# ============================================================================
# TESTS: doc_zoom() function
# ============================================================================

class TestDocZoom:
    """Tests for doc_zoom() main function."""

    def test_retrieve_specific_section_level_1(self, temp_db):
        """Test retrieving specific section at level 1."""
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id='POST_/symbols',
            target_level=1
        )

        assert result['section_id'] == 'POST_/symbols'
        assert result['section_title'] == 'POST /symbols'
        assert result['current_level'] == 1
        assert result['content'] == 'POST /symbols - Create symbol'
        assert not result['was_auto_completed']
        assert result['token_savings'] > 0  # Should save tokens vs L4

    def test_retrieve_all_levels(self, temp_db):
        """Test retrieving section at each level (L0-L4)."""
        for level in [0, 1, 2, 3, 4]:
            result = doc_zoom(
                db_path=temp_db,
                doc_path='docs/API.md',
                section_id='POST_/symbols',
                target_level=level
            )

            assert result['current_level'] == level
            assert result['content'] is not None

    def test_section_not_found(self, temp_db):
        """Test error when section doesn't exist."""
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id='NONEXISTENT_SECTION',
            target_level=1
        )

        assert result['error'] == 'not_found'
        assert 'NONEXISTENT_SECTION' in result['message']

    def test_document_not_found(self, temp_db):
        """Test error when document doesn't exist."""
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/NONEXISTENT.md',
            section_id='POST_/symbols',
            target_level=1
        )

        assert result['error'] == 'not_found'

    def test_list_all_sections(self, temp_db):
        """Test listing all sections when section_id is None."""
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id=None,
            target_level=1
        )

        assert 'sections' in result
        assert result['total_sections'] == 2
        assert len(result['sections']) == 2
        assert result['sections'][0]['section_id'] == 'POST_/symbols'
        assert result['sections'][1]['section_id'] == 'GET_/health'

    def test_list_sections_not_found(self, temp_db):
        """Test listing sections for non-existent document."""
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/MISSING.md',
            section_id=None,
            target_level=1
        )

        assert result['error'] == 'not_found'
        assert 'No sections found' in result['message']

    def test_token_savings_calculation(self, temp_db):
        """Test token savings calculation for levels < 4."""
        result_l0 = doc_zoom(temp_db, 'docs/API.md', 'POST_/symbols', 0)
        result_l4 = doc_zoom(temp_db, 'docs/API.md', 'POST_/symbols', 4)

        # L0 should have token savings (or 0 if similar length)
        assert result_l0['token_savings'] >= 0

        # L4 should have no savings
        assert result_l4['token_savings'] == 0

    @patch('dashboard.app.prompting.adaptive_zoom.get_zoom_recommender')
    def test_adaptive_level_recommendation(self, mock_get_recommender, temp_db):
        """Test adaptive level selection based on query."""
        # Mock recommender
        mock_recommender = Mock()
        mock_recommender.recommend_level.return_value = 2
        mock_get_recommender.return_value = mock_recommender

        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id='POST_/symbols',
            target_level=0,  # Will be overridden
            query="How does the API work?",
            use_adaptive=True
        )

        # Should use adaptive level 2
        assert result['current_level'] == 2
        assert result['content'] == 'Outline content'
        mock_recommender.recommend_level.assert_called_once_with("How does the API work?")

    @patch('dashboard.app.prompting.doc_level_generator.get_doc_level_generator')
    def test_auto_complete_missing_level(self, mock_get_generator, temp_db):
        """Test auto-completion of missing level."""
        # Mock generator
        mock_generator = Mock()
        completed_section = {
            'id': 1,
            'doc_path': 'docs/API.md',
            'section_id': 'GET_/health',
            'section_title': 'GET /health',
            'doc_type': 'api_reference',
            'file_hash': 'sha256:abc123',
            'section_hash': 'sha256:xyz789',
            'outline_l2': 'AUTO-GENERATED: Outline for health check',  # Generated
            'content_l4': 'Full health endpoint documentation'
        }
        mock_generator.complete_missing_levels.return_value = completed_section
        mock_get_generator.return_value = mock_generator

        # GET_/health section is missing outline_l2
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id='GET_/health',
            target_level=2,
            auto_complete=True
        )

        assert result['was_auto_completed']
        assert result['content'] == 'AUTO-GENERATED: Outline for health check'
        mock_generator.complete_missing_levels.assert_called_once()

    def test_available_levels_included(self, temp_db):
        """Test that available_levels is included in response."""
        result = doc_zoom(temp_db, 'docs/API.md', 'POST_/symbols', 1)

        assert 'available_levels' in result
        assert 0 in result['available_levels']
        assert 1 in result['available_levels']
        assert 2 in result['available_levels']
        assert 3 in result['available_levels']
        assert 4 in result['available_levels']

    def test_hashes_included_in_response(self, temp_db):
        """Test that file_hash and section_hash are included."""
        result = doc_zoom(temp_db, 'docs/API.md', 'POST_/symbols', 1)

        assert result['file_hash'] == 'sha256:abc123'
        assert result['section_hash'] == 'sha256:def456'


# ============================================================================
# TESTS: _get_available_levels() helper
# ============================================================================

class TestGetAvailableLevels:
    """Tests for _get_available_levels() helper function."""

    def test_all_levels_present(self, sample_section):
        """Test section with all levels 0-4."""
        levels = _get_available_levels(sample_section)

        assert levels == [0, 1, 2, 3, 4]

    def test_partial_levels(self):
        """Test section with only some levels."""
        section = {
            'summary_l0': 'Summary',
            'contract_l1': 'Contract',
            'content_l4': 'Full content',
            # Missing l2, l3
        }

        levels = _get_available_levels(section)
        assert levels == [0, 1, 4]

    def test_empty_section(self):
        """Test section with no levels."""
        section = {}
        levels = _get_available_levels(section)

        assert levels == []

    def test_only_l0(self):
        """Test section with only L0."""
        section = {'summary_l0': 'Summary only'}
        levels = _get_available_levels(section)

        assert levels == [0]

    def test_only_l4(self):
        """Test section with only L4."""
        section = {'content_l4': 'Full content only'}
        levels = _get_available_levels(section)

        assert levels == [4]


# ============================================================================
# TESTS: main() CLI function
# ============================================================================

class TestMain:
    """Tests for main() CLI entry point."""

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--section', 'POST_/symbols', '--db', 'test.db', '--json'])
    @patch('src.agentdb.doc_zoom.doc_zoom')
    @patch('builtins.print')
    def test_json_output(self, mock_print, mock_doc_zoom):
        """Test JSON output mode."""
        mock_doc_zoom.return_value = {
            'section_id': 'POST_/symbols',
            'content': 'Test content'
        }

        main()

        # Should print JSON
        mock_print.assert_called_once()
        call_args = str(mock_print.call_args)
        assert 'POST_/symbols' in call_args

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--adaptive'])
    def test_adaptive_without_query_error(self):
        """Test that --adaptive requires --query."""
        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 2  # argparse error code

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--section', 'POST_/symbols', '--db', 'test.db'])
    @patch('src.agentdb.doc_zoom.doc_zoom')
    @patch('builtins.print')
    def test_human_readable_output_section(self, mock_print, mock_doc_zoom):
        """Test human-readable output for single section."""
        mock_doc_zoom.return_value = {
            'doc_path': 'docs/API.md',
            'section_id': 'POST_/symbols',
            'section_title': 'POST /symbols',
            'current_level': 1,
            'content': 'Test content',
            'was_auto_completed': False,
            'token_savings': 100,
            'available_levels': [0, 1, 4]
        }

        main()

        # Should print human-readable format
        assert mock_print.call_count > 0

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--db', 'test.db'])
    @patch('src.agentdb.doc_zoom.doc_zoom')
    @patch('builtins.print')
    def test_list_sections_output(self, mock_print, mock_doc_zoom):
        """Test output when listing sections."""
        mock_doc_zoom.return_value = {
            'doc_path': 'docs/API.md',
            'total_sections': 2,
            'sections': [
                {'section_id': 'POST_/symbols', 'section_title': 'POST /symbols', 'summary_l0': 'Create symbol'},
                {'section_id': 'GET_/health', 'section_title': 'GET /health', 'summary_l0': None}
            ]
        }

        main()

        # Should print section list
        assert mock_print.call_count > 0

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--section', 'MISSING', '--db', 'test.db'])
    @patch('src.agentdb.doc_zoom.doc_zoom')
    def test_error_handling(self, mock_doc_zoom):
        """Test error handling and exit code."""
        mock_doc_zoom.return_value = {
            'error': 'not_found',
            'message': 'Section not found'
        }

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1

    @patch('sys.argv', ['doc-zoom', '--path', 'docs/API.md', '--section', 'TEST', '--db', 'test.db'])
    @patch('src.agentdb.doc_zoom.doc_zoom')
    def test_exception_handling(self, mock_doc_zoom):
        """Test exception handling in main()."""
        mock_doc_zoom.side_effect = Exception("Database error")

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Edge case tests for doc_zoom.py."""

    def test_level_0_no_token_savings_edge(self, temp_db):
        """Test edge case: L0 with same length as L4."""
        # This shouldn't happen in practice but test robustness
        result = doc_zoom(temp_db, 'docs/API.md', 'POST_/symbols', 0)
        assert result['token_savings'] >= 0  # Never negative

    def test_missing_optional_fields(self, temp_db):
        """Test handling of missing optional fields."""
        result = doc_zoom(temp_db, 'docs/API.md', 'GET_/health', 2, auto_complete=False)

        # Missing outline_l2 without auto_complete should return None
        assert result['content'] is None or result['content'] == ''

    @patch('dashboard.app.prompting.adaptive_zoom.get_zoom_recommender')
    def test_adaptive_with_no_query(self, mock_get_recommender, temp_db):
        """Test adaptive mode without query string."""
        # Shouldn't use adaptive if query is None/empty
        result = doc_zoom(
            db_path=temp_db,
            doc_path='docs/API.md',
            section_id='POST_/symbols',
            target_level=1,
            query=None,
            use_adaptive=True
        )

        # Should not call recommender
        mock_get_recommender.assert_not_called()
        # Should use specified level
        assert result['current_level'] == 1
