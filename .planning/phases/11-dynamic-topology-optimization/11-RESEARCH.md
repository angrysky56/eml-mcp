# Phase 11: Dynamic Topology Optimization - Research

## Objective
Research how to implement pruning mechanisms for the EML-Transformer that remove functionally redundant heads during training based on symbolic identities.

## Key Findings & Context

1. **EML-Transformer Structure:**
   The `EMLCompiledFFN` (verified in Phase 10) structures Neural Network logic by compiling individual Feed Forward heads as proxies for binary EML operations. Because the network translates directly to EML topological graphs, network layers naturally parallel EML symbolic trees.

2. **Equality Saturation (E-Graph) Integration:**
   As verified during Milestone 3, `simplifier.py` operates a full E-Graph Equality Saturation engine. During PyTorch forward/backward passes, we can inspect head gradients or head activation outputs. If multiple heads converge into structurally identical logic (i.e. they resolve to the same E-Class in the E-Graph), they represent functionally redundant pathways.

3. **Pruning Strategy:**
   - **Continuous Phase (L1/L2 Regularization):** Encourage sparsity within the EML-Transformer attention and FFN layers.
   - **Discrete Pruning (Symbolic Pruning Hook):** Every N epochs, pass the active network topology through the `EGraph` simplifier. Extract the optimal topology via Bellman-Ford traversal. Zero out or entirely drop structural parameters mapped to unselected/sub-optimal branches.
   - **Knowledge Distillation:** Merge the remaining pruned heads back down to a dense form using weight snapping mechanisms designed in earlier milestones.

## Required Implementation Pathway
We will need to modify the active PyTorch models in `src/eml_mcp/models/` to accept a callback from `src/eml_mcp/simplifier.py`.

## Validation Architecture
- Unit tests verifying redundant heads (like duplicated `exp(ln(z))` features encoded in network weights) are explicitly detected and zeroed after the pruning hook is invoked.
- Performance tests proving `Torch.compile()` retains speed after topology structural reduction.
