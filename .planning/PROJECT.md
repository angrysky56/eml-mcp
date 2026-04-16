# EML-MCP

## What This Is

An MCP (Model Context Protocol) server that provides AI assistants with access to the EML (Exp-Minus-Log) operator — the core generative primitive of elementary mathematics. Since v3.0, it includes an **EML-Transformer** prototype that compiles symbolic EML trees into analytical feed-forward networks (FFNs) using PyTorch, enabling memory-efficient and numerically transparent model architecture.

## Core Value

The EML system provides a **numerically stable, minimal functional basis** for symbolic regression and transformer architectures. By using a single binary operator (EML) and high-precision complex arithmetic, it ensures that derived functions preserve transcendental properties at machine-epsilon precision, which is critical for scientific and engineering applications where "black-box" MLPs fail to maintain analytical constraints.

## Requirements

### Validated

- ✓ **Foundation (v1.0)**: Modularized package, SQL persistence, AST-based compiler, initial discovery engine.
- ✓ **Symbolic Regression (v2.0)**: Master Formula Tree (Adam) optimization and "Weight Snapping" (Phases 5-6).
- ✓ **Extended Registry (v2.0)**: Deep bootstrapping of ~36 elementary functions including trigonometric and special functions (Phase 7).
- ✓ **Analytical Weight Compilation (v2.0)**: `EMLCompiledFFN` prototype mapping symbolic trees to PyTorch weights (Phase 8).
- ✓ **Structural Reasoning (v2.0)**: Zhang-Shasha Tree Edit Distance for structural complexity ranking and simplification rules.
- ✓ **Symbolic Attention (v2.0)**: Selective functional basis weighting and recursive token embedding (Phase 9).
- ✓ **Performance & Stabilization (v3.0)**: `torch.compile` optimization (4x speedup), complex-valued arithmetic robustness, and `eml_explain` diagnostic tracing (Phase 10).

### Active

- [ ] **Dynamic Topology Shrinkage**: Pruning EML-Transformer heads based on symbolic identity redundancy during training.
- [ ] **Multi-Variable EML (mEML)**: Extending the compiler and discovery engine to handle multi-variate Sheffer operators.
- [ ] **Integration with MOP**: Using EML-derived policies for cognitive science applications.

### Out of Scope

- **Real-time Training GUIs**: The focus is on the engine; training visualization is left to TensorBoard or standard tools.
- **Support for non-transcendental backends**: EML is fundamentally built on `exp` and `log`; linear-only backends are not supported.

## Context

### Theoretical Foundation

EML (Exp-Minus-Log) is the continuous gate-depth equivalent of the NAND gate. It exists at the substrate layer of the Minimal Generative Architecture (MGA). By discovering functional identities rather than hardcoding them, we achieve architectures that are structurally minimal (K-complexity prioritized). Our discovery of a K=11 subtraction tree (beating the paper's K=83) validates this exploratory approach.

### Current State (v3.0)

- **Registry**: ~36 verified formulas with full provenance and verification history in SQLite.
- **Transformer**: `EMLCompiledFFN` module optimized with `torch.compile` (mode="reduce-overhead").
- **Precision**: Strict `complex128` (float64 real/imag) for transcendental stability.
- **Diagnostic**: `eml_explain` provides full hierarchical evaluation traces for any EML tree.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Exploratory derivation over fixed chain | Discovery beats prescription (K=11 vs K=83). | Core Engine Strategy |
| `torch.compile` for tape execution | Sequential stage execution is slow; JIT fusion achieves 4x performance boost. | Implemented (v3.0) |
| Complex128 as default dtype | Truncation errors in float32 break transcendental identities like Euler's. | Non-negotiable |
| SQLite for metadata persistence | Low overhead, portable, perfect for formula counts in the hundreds. | Implemented (v1.0) |
| Weight Snapping in SR | Converts continuous optimization landscapes into discrete symbolic structures. | Implemented (v2.0) |

---
*Last updated: 2026-04-16 | Milestone 3 (Production Readiness) Completed*
