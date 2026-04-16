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
</task> [DONE]

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
</task> [DONE]

<task>
<id>3</id>
<title>Support Hybrid-Learnable (Analytical + Delta) EML Weights</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Implement a hybrid weight structure: $W = W_{fixed} + \Delta W_{trainable}$. The analytical EML weights provide the "structural prior," while the trainable delta allows the model to fine-tune the function during backpropagation.
</action>
<acceptance_criteria>
- `EMLCompiledFFN` supports an optional trainable delta for its weights.
- Gradients correctly propagate through the trainable delta during backpropagation without modifying the fixed structure.
</acceptance_criteria>
</task> [DONE]

<task>
<id>4</id>
<title>Implement Complex-Valued Support in EML Transformer blocks</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Upgrade `EMLCompiledFFN` to use `torch.complex128` or `torch.complex64`. Remove `relu` clamping in favor of safe complex logarithms to maintain phase consistency across layers.
</action>
<acceptance_criteria>
- Module computes forward pass using complex tensors.
- Safe complex logarithms correctly handle branch cuts and zero-values without relying on real domain ReLU clamping.
</acceptance_criteria>
</task> [DONE]

<task>
<id>5</id>
<title>Vectorized Layer-Wise Unrolling of EML FFNs</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Unroll the EML tree level-by-level into a sequence of parallel operations mapping each depth to a unified linear layer. Stage 1 computes depth 1, Stage 2 consumes outputs of depth 1, and so on until the final reduction.
</action>
<acceptance_criteria>
- Recursive tensor calls are replaced by layer-wise unrolled PyTorch operations.
- Parallel computations are applied across nodes at the same tree depth.
</acceptance_criteria>
</task> [DONE]

<task>
<id>6</id>
<title>Add Multi-Identity 'Heads' to EML-Transformer FFN</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Extend `EMLCompiledFFN` to compute multiple identities in parallel (e.g., 8, 16, or 32 distinct EML-derived functions) forming a "basis set" of analytical functions to attend to.
</action>
<acceptance_criteria>
- FFN accepts configuration to run multiple EML functions concurrently as parallel heads.
- Forward pass outputs a stacked/concatenated high-dimensional representation.
</acceptance_criteria>
</task> [DONE]

<task>
<id>7</id>
<title>Cache and Reuse Redundant Sub-tree Activations</title>
<read_first>
- src/eml_mcp/transformer.py
</read_first>
<action>
Map the symbolic simplifier's common sub-expression elimination (CSE) findings into the FFN architecture. Store intermediate activation results of unique sub-trees and reuse them across the depth of the FFN expansion.
</action>
<acceptance_criteria>
- Repeated EML sub-trees are computed only once per forward pass.
- Activation caching significantly reduces redundant computations during deep function evaluation.
</acceptance_criteria>
</task> [DONE]
