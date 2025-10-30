from typing import TypedDict, List, Dict, Any, Optional

# AGTAG v1 schema (LLM-facing)
class AGSymbol(TypedDict, total=False):
    """Symbol metadata describing source snippets indexed by AgentDB."""
    path: str
    name: str
    kind: str                 # "function" | "class" | "module" | "file"
    signature: str
    lines: List[int]          # [start, end], 1-based inclusive
    summary_l0: str
    contract_l1: str          # @io, invariants
    pseudocode_l2: str
    ast_excerpt_l3: Dict[str, Any]

class AGDoc(TypedDict, total=False):
    """Documentation section metadata included in AGTAG payloads."""
    path: str
    section: str
    summary: str

class AGTest(TypedDict, total=False):
    """Test metadata for linking automated coverage to symbols."""
    path: str
    name: str
    covers: List[str]         # symbol names or handles
    status: str               # "new" | "updated"

class AGTag(TypedDict, total=False):
    """Top-level AGTAG payload containing symbols, docs, and tests."""
    version: str              # "v1"
    symbols: List[AGSymbol]
    docs: List[AGDoc]
    tests: List[AGTest]
AGTAG_METADATA = """"""
