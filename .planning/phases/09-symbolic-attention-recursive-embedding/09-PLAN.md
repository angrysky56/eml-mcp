---
wave: 1
depends_on: []
files_modified:
  - "src/eml_mcp/attention.py"
  - "tests/test_attention.py"
  - "src/eml_mcp/transformer.py"
  - "benchmarks/benchmark_eml_vs_mlp.py"
autonomous: true
---

# Phase 9: Symbolic Attention & Recursive Embedding - Execution Plan

## Goal
Implement symbolic attention mechanism and recursive token embedding. Quantify EML Transformer performance against standard MLP topologies.

## Tasks

<task>
<id>1</id>
<title>Implement Symbolic Attention Mechanism</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Create `src/eml_mcp/attention.py`.
Implement an `EMLSymbolicAttention` module that takes the multi-head output of `EMLCompiledFFN` (the functional basis set representing various analytical identities) and selectively weights them using a standard scaled dot-product attention mechanism. The attention should act as a routing mechanism, allowing the network to "listen" to the most relevant functional heads for a given input.
</action>
<acceptance_criteria>
- `src/eml_mcp/attention.py` is present.
- `EMLSymbolicAttention` class defined, inheriting from `torch.nn.Module`.
- FFN accepts multiple EML formula heads, and the attention module cleanly aggregates them based on query/key/value projections.
- Output shapes are mathematically correct and preserve batch dimensions.
</acceptance_criteria>
</task>

<task>
<id>2</id>
<title>Write Symbolic Attention Tests</title>
<read_first>
- src/eml_mcp/attention.py
- tests/test_transformer.py
</read_first>
<action>
Create `tests/test_attention.py` to verify that `EMLSymbolicAttention` correctly routes signals from the `EMLCompiledFFN` output. Test scenarios where specific attention weights are forced to verify the aggregated output matches the expected functional head.
</action>
<acceptance_criteria>
- `tests/test_attention.py` exists and contains at least 2 test functions.
- Attention weights sum to 1 across the head dimension.
- All tests pass when run via `uv run pytest tests/test_attention.py`.
</acceptance_criteria>
</task>

<task>
<id>3</id>
<title>Implement Recursive Token Embedding</title>
<read_first>
- src/eml_mcp/transformer.py
- src/eml_mcp/trees.py
</read_first>
<action>
Extend the compilation logic in `EMLCompiledFFN` to allow treating complex, previously discovered identities (like `sin` or `cos`) as primitive "tokens" or sub-graphs without fully unrolling them every time if they are precompiled. This implies allowing EML structures to be nested structurally into larger transformer contexts as reusable blocks. Since our tape approach inherently flattens nodes, ensure that importing a registered formula from the database seamlessly stitches its DAG into the current tape.
</action>
<acceptance_criteria>
- `EMLCompiledFFN` accepts compound formulas referencing other functions and correctly builds the tape.
- Shared sub-expressions inside these recursive tokens are correctly optimized via CSE.
</acceptance_criteria>
</task>

<task>
<id>4</id>
<title>Develop Performance Benchmark Suite</title>
<read_first>
- src/eml_mcp/transformer.py
- src/eml_mcp/attention.py
</read_first>
<action>
Create `benchmarks/benchmark_eml_vs_mlp.py`.
Implement a performance test comparing an `EMLCompiledFFN` (with a small basis set of functions + attention) against a standard PyTorch `nn.Sequential` MLP with equivalent parameter counts and depths. Benchmark forward-pass latency, memory usage (using CUDA/CPU profiling), and convergence speed on a simple synthetic dataset.
</action>
<acceptance_criteria>
- `benchmarks/benchmark_eml_vs_mlp.py` is present and executable.
- Script outputs a comparative report of parameter counts, forward pass times, and gradient computation time.
</acceptance_criteria>
</task>
