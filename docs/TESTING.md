# Testing Guide

`eml-mcp` is verified against comprehensive suite of automated tests.

## Running Tests

All testing should be run using `pytest` orchestrated by `uv`:

```bash
uv run pytest tests/
```

This will run all test suites covering discovery functions, simplification algorithms, structural transformations, compiler targets, and similarity tests.

### Targeted Runs

To run specifically tests for the equality-saturation integration:
```bash
uv run pytest tests/test_simplifier.py
```

## Writing Tests

If you are expanding functionality, especially mathematical substitutions or e-graph node rules, add an edge case in the `pytest` structure. 

### Assertions Using `node_to_rpn`
A typical and reliable way to verify tree simplification in python is to translate the tree generated into Reverse Polish Notation (rpn) and verify its textual hash footprint perfectly aligns.

Example:
```python
def test_identity():
    # Construct an explicitly redundant formula
    node = from_string("eml(eml(1, eml(eml(1, x), 1)), 1)")
    reduced = simplify_tree(node)
    
    # Assert
    assert node_to_rpn(reduced) == "x"
```

## Continuous Integration
Any additions to GitHub main branch invokes an ephemeral runner. Because `test_parallel_discovery.py` can be extremely CPU-bound under evolutionary benchmarks, logic utilizing `os.getenv("CI") == "true"` correctly overrides execution delays ensuring fast feedback pipelines on PRs.
