def test_truth():
    assert True

AGTAG_METADATA = """

<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "test_truth",
      "kind": "function",
      "qualified_name": "tests.test_bootstrap.test_truth",
      "lines": [
        1,
        2
      ],
      "summary_l0": "Pytest case test_truth validating expected behaviour.",
      "contract_l1": "def test_truth()",
      "pseudocode_l2": "1. Execute pytest assertions and validations.",
      "path": "tests/test_bootstrap.py"
    }
  ],
  "tests": [
    {
      "path": "tests/test_bootstrap.py",
      "name": "tests.test_bootstrap.test_truth",
      "covers": [],
      "status": "new"
    }
  ]
}
<!--AGTAG v1 END-->
"""
