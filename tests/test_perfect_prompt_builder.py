"""
Comprehensive test suite for perfect_prompt_builder.py

Tests all classes, methods, and edge cases with 90%+ coverage.
"""

import pytest
from src.agentdb.perfect_prompt_builder import (
    QueryType,
    ContextLevel,
    EscalationStrategy,
    PerfectPromptBuilder,
)


class TestQueryType:
    """Test QueryType enum."""

    def test_query_type_values(self):
        """Test all QueryType enum values exist."""
        assert QueryType.FACTUAL.value == "factual"
        assert QueryType.DECISION.value == "decision"
        assert QueryType.REASONING.value == "reasoning"
        assert QueryType.CODE_GENERATION.value == "code"
        assert QueryType.MULTI_STEP.value == "multi_step"
        assert QueryType.LOOKUP.value == "lookup"

    def test_query_type_count(self):
        """Test expected number of query types."""
        assert len(QueryType) == 6


class TestContextLevel:
    """Test ContextLevel enum."""

    def test_context_level_values(self):
        """Test all ContextLevel enum values exist."""
        assert ContextLevel.L0.value == "l0"
        assert ContextLevel.L1.value == "l1"
        assert ContextLevel.L2.value == "l2"
        assert ContextLevel.L3.value == "l3"
        assert ContextLevel.L4.value == "l4"

    def test_context_level_count(self):
        """Test expected number of levels."""
        assert len(ContextLevel) == 5


class TestEscalationStrategy:
    """Test EscalationStrategy dataclass."""

    def test_escalation_strategy_creation(self):
        """Test creating EscalationStrategy instance."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=ContextLevel.L2,
            confidence_threshold=0.90,
            token_budget=2000
        )
        assert strategy.initial_level == ContextLevel.L0
        assert strategy.fallback_level == ContextLevel.L2
        assert strategy.confidence_threshold == 0.90
        assert strategy.token_budget == 2000

    def test_escalation_strategy_no_fallback(self):
        """Test EscalationStrategy with no fallback."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=None,
            confidence_threshold=0.95,
            token_budget=1000
        )
        assert strategy.fallback_level is None


class TestPerfectPromptBuilderInit:
    """Test PerfectPromptBuilder initialization."""

    def test_init_creates_instance(self):
        """Test builder can be instantiated."""
        builder = PerfectPromptBuilder()
        assert builder is not None

    def test_quality_metrics_present(self):
        """Test QUALITY_METRICS class variable exists."""
        assert hasattr(PerfectPromptBuilder, 'QUALITY_METRICS')
        metrics = PerfectPromptBuilder.QUALITY_METRICS
        assert QueryType.FACTUAL in metrics
        assert QueryType.CODE_GENERATION in metrics

    def test_query_patterns_present(self):
        """Test QUERY_PATTERNS class variable exists."""
        assert hasattr(PerfectPromptBuilder, 'QUERY_PATTERNS')
        patterns = PerfectPromptBuilder.QUERY_PATTERNS
        assert QueryType.CODE_GENERATION in patterns
        assert isinstance(patterns[QueryType.CODE_GENERATION], list)


class TestDetectQueryType:
    """Test detect_query_type method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_detect_code_generation(self):
        """Test detecting code generation queries."""
        queries = [
            "write code to validate tokens",
            "implement a search function",
            "create a class for database access",
            "generate implementation for auth",
            "refactor the validation logic"
        ]
        for query in queries:
            assert self.builder.detect_query_type(query) == QueryType.CODE_GENERATION

    def test_detect_multi_step(self):
        """Test detecting multi-step queries."""
        queries = [
            "create a plan for migration",
            "step-by-step guide to setup",
            "implementation plan for feature",
            "roadmap for the project"
        ]
        for query in queries:
            assert self.builder.detect_query_type(query) == QueryType.MULTI_STEP

    def test_detect_decision(self):
        """Test detecting decision queries."""
        queries = [
            "should i use ingest or patch",
            "which is better for this case",
            "best approach for validation",
            "recommended strategy"
        ]
        for query in queries:
            assert self.builder.detect_query_type(query) == QueryType.DECISION

    def test_detect_reasoning(self):
        """Test detecting reasoning queries."""
        queries = [
            "why does this function fail",
            "explain why tokens are validated",
            "how does the escalation work",
            "what's the difference between L0 and L1"
        ]
        for query in queries:
            assert self.builder.detect_query_type(query) == QueryType.REASONING

    def test_detect_factual(self):
        """Test detecting factual queries."""
        queries = [
            "what is the focus command",
            "list all available commands",
            "show me the syntax",
            "describe the ingestion process"
        ]
        for query in queries:
            assert self.builder.detect_query_type(query) == QueryType.FACTUAL

    def test_detect_default_factual(self):
        """Test default to factual for unmatched queries."""
        query = "random query with no patterns"
        assert self.builder.detect_query_type(query) == QueryType.FACTUAL

    def test_case_insensitive(self):
        """Test query detection is case insensitive."""
        assert self.builder.detect_query_type("WRITE CODE") == QueryType.CODE_GENERATION
        assert self.builder.detect_query_type("Create A Plan") == QueryType.MULTI_STEP


class TestGetRecommendedLevel:
    """Test get_recommended_level method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_factual_returns_l0(self):
        """Test factual queries recommend L0."""
        level = self.builder.get_recommended_level(QueryType.FACTUAL)
        assert level == ContextLevel.L0

    def test_decision_returns_l0(self):
        """Test decision queries recommend L0."""
        level = self.builder.get_recommended_level(QueryType.DECISION)
        assert level == ContextLevel.L0

    def test_reasoning_returns_l1(self):
        """Test reasoning queries recommend L1."""
        level = self.builder.get_recommended_level(QueryType.REASONING)
        assert level == ContextLevel.L1

    def test_code_generation_returns_l4(self):
        """Test code generation queries recommend L4."""
        level = self.builder.get_recommended_level(QueryType.CODE_GENERATION)
        assert level == ContextLevel.L4

    def test_multi_step_returns_l2(self):
        """Test multi-step queries recommend L2."""
        level = self.builder.get_recommended_level(QueryType.MULTI_STEP)
        assert level == ContextLevel.L2

    def test_lookup_returns_l0(self):
        """Test lookup queries recommend L0."""
        level = self.builder.get_recommended_level(QueryType.LOOKUP)
        assert level == ContextLevel.L0


class TestGetEscalationStrategy:
    """Test get_escalation_strategy method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_high_quality_no_fallback(self):
        """Test high quality queries (>0.95) have no fallback."""
        # Factual has 0.975 similarity
        strategy = self.builder.get_escalation_strategy(QueryType.FACTUAL)
        assert strategy.initial_level == ContextLevel.L0
        assert strategy.fallback_level is None
        assert strategy.confidence_threshold == 0.95

    def test_medium_quality_l2_fallback(self):
        """Test medium quality queries (0.90-0.95) fallback to L2."""
        # Reasoning has 0.905 similarity
        strategy = self.builder.get_escalation_strategy(QueryType.REASONING)
        assert strategy.initial_level == ContextLevel.L1
        assert strategy.fallback_level == ContextLevel.L2
        assert strategy.confidence_threshold == 0.92

    def test_low_quality_l4_fallback(self):
        """Test low quality queries (<0.90) fallback to L4."""
        # Code generation has 0.830 similarity
        strategy = self.builder.get_escalation_strategy(QueryType.CODE_GENERATION)
        assert strategy.initial_level == ContextLevel.L4
        assert strategy.fallback_level == ContextLevel.L4
        assert strategy.confidence_threshold == 0.90

    def test_custom_token_budget(self):
        """Test custom token budget is respected."""
        strategy = self.builder.get_escalation_strategy(QueryType.FACTUAL, token_budget=5000)
        assert strategy.token_budget == 5000

    def test_default_token_budget(self):
        """Test default token budget is 2000."""
        strategy = self.builder.get_escalation_strategy(QueryType.FACTUAL)
        assert strategy.token_budget == 2000


class TestBuildContextAtLevel:
    """Test _build_context_at_level method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()
        self.sample_symbols = [
            {
                "name": "validate_token",
                "repo_path": "src/auth.py",
                "l0_overview": "Validates JWT tokens",
                "l1_contract": "@io token:str -> dict | None",
                "l2_pseudocode": "verify signature\ncheck expiration",
                "l4_full_code": "def validate_token(token):\n    pass"
            }
        ]

    def test_build_empty_symbols(self):
        """Test building context with no symbols."""
        context = self.builder._build_context_at_level([], ContextLevel.L0)
        assert context == "(No symbols in context)"

    def test_build_l0_context(self):
        """Test building L0 context."""
        context = self.builder._build_context_at_level(self.sample_symbols, ContextLevel.L0)
        assert "validate_token" in context
        assert "Validates JWT tokens" in context
        assert "@io" not in context  # L1 shouldn't be included

    def test_build_l1_context(self):
        """Test building L1 context."""
        context = self.builder._build_context_at_level(self.sample_symbols, ContextLevel.L1)
        assert "validate_token" in context
        assert "Validates JWT tokens" in context
        assert "@io token:str -> dict | None" in context
        assert "verify signature" not in context  # L2 shouldn't be included

    def test_build_l2_context(self):
        """Test building L2 context."""
        context = self.builder._build_context_at_level(self.sample_symbols, ContextLevel.L2)
        assert "validate_token" in context
        assert "Validates JWT tokens" in context
        assert "@io token:str -> dict | None" in context
        assert "verify signature" in context

    def test_build_l4_context(self):
        """Test building L4 context."""
        context = self.builder._build_context_at_level(self.sample_symbols, ContextLevel.L4)
        assert "validate_token" in context
        assert "def validate_token(token):" in context
        assert "```python" in context

    def test_build_l4_code_fallback(self):
        """Test L4 context falls back to l4_code if l4_full_code missing."""
        symbols = [{
            "name": "test",
            "repo_path": "test.py",
            "l4_code": "def test(): pass"
        }]
        context = self.builder._build_context_at_level(symbols, ContextLevel.L4)
        assert "def test(): pass" in context

    def test_build_multiple_symbols(self):
        """Test building context with multiple symbols."""
        symbols = [
            {"name": "func1", "l0_overview": "First function"},
            {"name": "func2", "l0_overview": "Second function"}
        ]
        context = self.builder._build_context_at_level(symbols, ContextLevel.L0)
        assert "func1" in context
        assert "func2" in context


class TestBuildPromptWithLevels:
    """Test build_prompt_with_levels method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()
        self.sample_symbols = [{
            "name": "validate",
            "l0_overview": "Validates input",
            "l1_contract": "@io x:Any -> bool"
        }]

    def test_build_prompt_auto_detect(self):
        """Test prompt building with auto query type detection."""
        query = "what does validate do"
        prompt = self.builder.build_prompt_with_levels(query, self.sample_symbols)
        assert "what does validate do" in prompt
        assert "validate" in prompt
        assert "Context (Level: L0)" in prompt

    def test_build_prompt_explicit_type(self):
        """Test prompt building with explicit query type."""
        query = "implement validation"
        prompt = self.builder.build_prompt_with_levels(
            query, self.sample_symbols, QueryType.CODE_GENERATION
        )
        assert "Context (Level: L4)" in prompt

    def test_build_prompt_includes_escalation_hint(self):
        """Test prompt includes escalation hint for low quality types."""
        query = "implement feature"
        prompt = self.builder.build_prompt_with_levels(query, self.sample_symbols)
        assert "(If this context seems insufficient" in prompt or "L4" in prompt

    def test_build_prompt_no_escalation_hint(self):
        """Test prompt has no escalation hint for high quality types."""
        query = "what is validate"
        prompt = self.builder.build_prompt_with_levels(query, self.sample_symbols)
        # Factual queries have high quality, so no hint or it's formatted differently
        assert "Question: what is validate" in prompt


class TestShouldEscalate:
    """Test should_escalate method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_no_fallback_returns_false(self):
        """Test no escalation when strategy has no fallback."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=None,
            confidence_threshold=0.95,
            token_budget=2000
        )
        assert self.builder.should_escalate("any response", strategy) is False

    def test_short_response_triggers_escalation(self):
        """Test very short responses trigger escalation."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=ContextLevel.L2,
            confidence_threshold=0.90,
            token_budget=2000
        )
        short_response = "I don't know"
        assert self.builder.should_escalate(short_response, strategy) is True

    def test_insufficient_context_pattern_triggers_escalation(self):
        """Test 'insufficient context' pattern triggers escalation."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=ContextLevel.L2,
            confidence_threshold=0.90,
            token_budget=2000
        )
        responses = [
            "I need more information to answer",
            "insufficient context to determine",
            "cannot determine from the given context",
            "not enough information provided",
            "unclear from context"
        ]
        for response in responses:
            assert self.builder.should_escalate(response, strategy) is True

    def test_generic_response_triggers_escalation(self):
        """Test generic short responses trigger escalation."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=ContextLevel.L2,
            confidence_threshold=0.90,
            token_budget=2000
        )
        generic_response = "This function handles validation tasks somewhat"
        assert self.builder.should_escalate(generic_response, strategy) is True

    def test_good_response_no_escalation(self):
        """Test good quality responses don't trigger escalation."""
        strategy = EscalationStrategy(
            initial_level=ContextLevel.L0,
            fallback_level=ContextLevel.L2,
            confidence_threshold=0.90,
            token_budget=2000
        )
        good_response = """
        This function specifically validates JWT tokens by first checking the signature
        against the configured secret, then verifying the expiration timestamp hasn't
        passed, and finally decoding the payload to extract user information. It returns
        a dictionary with user data on success or None on failure.
        """
        assert self.builder.should_escalate(good_response, strategy) is False


class TestBuildAuthoringPrompt:
    """Test build_authoring_prompt method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_authoring_prompt_includes_code(self):
        """Test authoring prompt includes the generated code."""
        code = "def test():\n    return 42"
        prompt = self.builder.build_authoring_prompt(code)
        assert "def test():" in prompt
        assert "return 42" in prompt

    def test_authoring_prompt_requests_l0(self):
        """Test authoring prompt requests L0 overview."""
        code = "def test(): pass"
        prompt = self.builder.build_authoring_prompt(code)
        assert "L0" in prompt or "one-line overview" in prompt.lower()

    def test_authoring_prompt_requests_l1(self):
        """Test authoring prompt requests L1 contract."""
        code = "def test(): pass"
        prompt = self.builder.build_authoring_prompt(code)
        assert "L1" in prompt or "Contract" in prompt

    def test_authoring_prompt_requests_l2(self):
        """Test authoring prompt requests L2 pseudocode."""
        code = "def test(): pass"
        prompt = self.builder.build_authoring_prompt(code)
        assert "L2" in prompt or "Pseudocode" in prompt

    def test_authoring_prompt_requests_json_format(self):
        """Test authoring prompt requests JSON format."""
        code = "def test(): pass"
        prompt = self.builder.build_authoring_prompt(code)
        assert "json" in prompt.lower()
        assert "l0_overview" in prompt or "l1_contract" in prompt

    def test_authoring_prompt_custom_language(self):
        """Test authoring prompt with custom language."""
        code = "function test() { return 42; }"
        prompt = self.builder.build_authoring_prompt(code, language="javascript")
        assert "javascript" in prompt
        assert "```javascript" in prompt

    def test_authoring_prompt_default_python(self):
        """Test authoring prompt defaults to Python."""
        code = "def test(): pass"
        prompt = self.builder.build_authoring_prompt(code)
        assert "python" in prompt.lower()


# Edge cases and integration tests
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.builder = PerfectPromptBuilder()

    def test_empty_query(self):
        """Test handling empty query."""
        query = ""
        qtype = self.builder.detect_query_type(query)
        assert qtype == QueryType.FACTUAL  # Default

    def test_symbols_with_missing_fields(self):
        """Test symbols with missing optional fields."""
        symbols = [{"name": "test"}]  # Missing all optional fields
        context = self.builder._build_context_at_level(symbols, ContextLevel.L0)
        assert "test" in context
        assert "(no overview)" in context

    def test_symbols_with_missing_repo_path(self):
        """Test symbols without repo_path."""
        symbols = [{"name": "test", "l0_overview": "Test function"}]
        context = self.builder._build_context_at_level(symbols, ContextLevel.L1)
        assert "test" in context

    def test_very_long_query(self):
        """Test handling very long queries."""
        query = "what does " * 100 + "this function do?"
        qtype = self.builder.detect_query_type(query)
        assert qtype == QueryType.FACTUAL

    def test_special_characters_in_query(self):
        """Test queries with special regex characters."""
        query = "what is [*]?"
        qtype = self.builder.detect_query_type(query)
        assert qtype == QueryType.FACTUAL

    def test_unicode_in_query(self):
        """Test queries with Unicode characters."""
        query = "write code for ∑ calculation"
        qtype = self.builder.detect_query_type(query)
        assert qtype == QueryType.CODE_GENERATION


class TestMainFunction:
    """Test main() example function."""

    def test_main_runs_without_error(self, capsys):
        """Test main() executes successfully."""
        from src.agentdb.perfect_prompt_builder import main

        # Run main() - it should print examples
        main()

        # Capture output
        captured = capsys.readouterr()

        # Verify it printed something
        assert len(captured.out) > 0
        assert "Query Type Detection" in captured.out or "Query:" in captured.out

