# Phase 8: EML-Transformer Prototype - Technical Research

## Architecture: EML to Feed-Forward Network (FFN) Mapping

The problem of converting discrete EML blocks (from discovery/regression) to transformer weight tensors requires us to formally map the EML primitive `eml(x, y) = exp(x) - ln(y)` to a neural network forward pass.

A typical linear+activation layer looks like: `layer(x) = activation(W * x + b)`.
Since `eml` is not a single typical activation, we can express it as a customized sub-layer or dual-pathway layer.

Let a tree node evaluate `H = exp(W_e * X + b_e) - ln(W_l * X + b_l)`.

To represent this structure natively as a PyTorch FFN without changing the runtime environment, we should design a module like `EMLTransformerBlock` that explicitly constructs the `W_e` and `W_l` weight matrices and applies the respective scalar non-linearities (`exp` and `log`).

### Steps for Analytical FFN mapping:
1. Traverse the generated binary tree of `EMLNode` identities.
2. At each depth `d`, gather all required `exp` pathways and `log` pathways.
3. Build block-diagonal sparse or dense routing weights that combine variables into the specified pairs.
4. Construct the PyTorch module (`nn.Linear` layers paired with `torch.exp` and `torch.log`).

This is our "L-1 Compiler": translating symbolic representations into matrix operations. 

## Code Interactions & Dependencies

- `src/eml_mcp/compiler.py`: Already maps string/AST into expressions. We may need a function like `compile_eml_to_tensor_ffn(formula: str) -> nn.Module`.
- `src/eml_mcp/transformer.py`: New module designated to house the mapping logic and `EMLTransformerBlock` and related structures.

## Verification Approach
We need to verify the forward-pass execution.
- Validate `compiled_model.forward(x)` numerically matches the string `eval()` or numerical execution over a range of inputs (e.g. `x = [0.1, 1.0, 10.0]`).
- Address nan/inf errors for `ln(0)` or `ln(-ve)` paths gracefully, possibly standardizing on `relu+eps` in the log pathway as required.

## Validation Architecture
- [ ] Create PyTorch Module matching EML FFN layout.
- [ ] Write compiler to seed weights in the PyTorch Module from tree components.
- [ ] Pytest verification suite testing outputs against epsilon tolerance.
