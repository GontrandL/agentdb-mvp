"""
Simple calculator module for testing AgentDB progressive disclosure.

This module demonstrates L0→L4 progressive disclosure with two functions.
"""


def add(a: int, b: int) -> int:
    """
    Add two integers and return the result.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Sum of a and b
    """
    return a + b


def multiply(a: int, b: int) -> int:
    """
    Multiply two integers and return the result.

    Args:
        a: First integer
        b: Second integer

    Returns:
        Product of a and b
    """
    return a * b


AGTAG_METADATA = """<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "add",
      "kind": "function",
      "signature": "def add(a: int, b: int) -> int",
      "lines": [8, 21],
      "summary_l0": "Add two integers",
      "contract_l1": "@io(a:int, b:int) -> int; @invariant: result == a + b",
      "pseudocode_l2": "1. Accept two integer parameters a and b\\n2. Return sum a + b\\n3. No validation needed for integers"
    },
    {
      "name": "multiply",
      "kind": "function",
      "signature": "def multiply(a: int, b: int) -> int",
      "lines": [24, 37],
      "summary_l0": "Multiply two integers",
      "contract_l1": "@io(a:int, b:int) -> int; @invariant: result == a * b",
      "pseudocode_l2": "1. Accept two integer parameters a and b\\n2. Return product a * b\\n3. No validation needed for integers"
    }
  ],
  "docs": [],
  "tests": []
}
<!--AGTAG v1 END-->
"""
