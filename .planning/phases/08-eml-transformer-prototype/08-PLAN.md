---
wave: 1
depends_on: []
files_modified:
  - "src/eml_mcp/transformer.py"
  - "tests/test_transformer.py"
autonomous: true
---

# Phase 8: EML-Transformer Prototype - Execution Plan

## Goal
Implement analytical FFN construction that compiles discrete EML formula trees into structural PyTorch transformer/FFN weights, and verify its native PyTorch forward pass replicates the symbolic formulas.

## Tasks

<task>
<id>1</id>
<title>Implement EML-compiled FFN Module</title>
<read_first>
- src/eml_mcp/regression.py
- src/eml_mcp/compiler.py
</read_first>
<action>
Create `src/eml_mcp/transformer.py`.
Implement an `EMLCompiledFFN` mapping an array of variables `["x"]` or expressions into dual-path affine matrices (`W_e` and `W_l`) using `nn.Linear` layers minus bias adjustments based on parsed operations. It should replicate nested operations inside a structured feed-forward module.
Include basic support for depth-1 and depth-2 unrolled trees and handle epsilon stability for `log`.
</action>
<acceptance_criteria>
- `src/eml_mcp/transformer.py` is present.
- `EMLCompiledFFN` class defined, inheriting from `torch.nn.Module`.
- Implements `forward(x)` that computes `torch.exp(W_e * x) - torch.log(relu(W_l * x) + eps)`.
</acceptance_criteria>
</task>

<task>
<id>2</id>
<title>Write Verification Spec and Test Suite</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Create `tests/test_transformer.py` to assert the outputs of `EMLCompiledFFN` against standard `eval()` or analytical PyTorch evaluation of functions like `eml(x, 1)` -> `exp(x)` and `eml(1, x)` -> `e - ln(x)`. Test over various `x` ranges to ensure correct weight broadcasting and gradient-safe math.
</action>
<acceptance_criteria>
- `tests/test_transformer.py` exists and contains at least 3 test functions (e.g. `test_exp_node`, `test_ln_node`, `test_identity`).
- All tests pass when run via `uv run pytest tests/test_transformer.py`.
- Strict numerical tolerance checked (`torch.allclose`).
</acceptance_criteria>
</task>
