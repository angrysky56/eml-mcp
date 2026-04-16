# Phase 8: EML-Transformer Prototype - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning
**Source:** Roadmap & Requirements

<domain>
## Phase Boundary

This phase delivers the prototype implementation of the "EML-Transformer" compiler. It focuses on mapping discrete EML formula trees (previously derived via symbolic regression and discovery) directly into the weight tensors of a Feed-Forward Network (FFN) layer. This serves as an "L-1 Compiler" that transforms parsed EML structures into analytical neural network weights that execute the EML function natively within a PyTorch neural network context.
</domain>

<decisions>
## Implementation Decisions

### EML-to-Tensor Compilation
- **Direct Weight Initialization:** Implement logic to take an EML tree representation and analytically derive weight matrices and biases for an FFN-like PyTorch module.
- **Activation Functions:** The layer must respect the core `eml(x, y) = exp(x) - ln(y)` formulation. The internal architecture of the compiled FFN must use exact `exp` and `log` operations (with appropriate safeguards against log(0)) to ensure machine-epsilon precision.
- **Recursive Unrolling:** The compiler handles nested EML trees by mapping each level of tree depth to distinct sub-layers or sequential operations in the model tensor.

### Verification
- **Numerical Tolerance:** The compiled EML-Transformer outputs MUST match the direct mathematical execution of the EML tree within PyTorch float64/float32 precision bounds.
- **Test Suite:** Create a verification script that initializes a transformer module with known EML formulas (like simple expressions) and compares its forward pass against reference implementations. 
</decisions>

<canonical_refs>
## Canonical References
**Downstream agents MUST read these before planning or implementing.**
- `.planning/ROADMAP.md` — Phase 8 definitions and success criteria.
- `.planning/REQUIREMENTS.md` — XFMR-01 and XFMR-02 execution goals.
- `src/eml_mcp/regression.py` — Existing Master Tree structure to understand current PyTorch representations.
- `src/eml_mcp/compiler.py` — The core logic for basic EML structures.
</canonical_refs>

<specifics>
## Specific Ideas
- Introduce an `EMLTransformerFFN(nn.Module)` class in a new or existing module (e.g., `src/eml_mcp/transformer.py`) that acts as the target for the L-1 compilation.
- Ensure gradient propagation isn't broken, though this tool simply initializes a network analytically (so weights could be frozen or used as initialization for fine-tuning).
</specifics>

<deferred>
## Deferred Ideas
- Multi-variable functions of more than 2 variables.
- Direct GPU/CUDA acceleration at a low-level operator implementation (keep standard PyTorch code).
- Complex KV-caching MoR logic (recursive sharing) is deferred until we establish the fundamental weight mapping works.
</deferred>
