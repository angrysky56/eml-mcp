# Requirements: EML-MCP v2 (Optimization & Regression)

**Defined:** 2026-04-16
**Core Value:** Efficiently discover and optimize EML identities through gradient-based search and high-throughput exploration.

## Milestone 2 Requirements

### Symbolic Regression
- [ ] **SR-01**: Implement `MasterFormulaTree` with differentiable weights for leaf inputs (constant 1, x, f).
- [ ] **SR-02**: Implement optimization loop using Adam (or simple gradient descent if zero-dependency is maintained).
- [ ] **SR-03**: Implement "Weight Snapping" logic: convert optimized continuous weights to exact 0/1 values to recover discrete EML identities.
- [ ] **SR-04**: Tool `eml_regress` exposes symbolic regression to MCP, taking a target function and returning the recovered formula.

### Parallel Discovery & Performance
- [ ] **DISC-07**: Multi-process `DiscoveryEngine` to scale composition search across multiple CPU cores.
- [ ] **DISC-08**: Depth-first search (DFS) optimization with pruning based on MSE thresholds.
- [ ] **DISC-09**: Persistent "Search State" to allow resuming interrupted discovery sessions.

### Structural Analysis
- [ ] **TREE-01**: Implement Tree Edit Distance (e.g., Zhang-Shasha) to quantify structural similarity between formulas.
- [ ] **TREE-02**: Automated "Simplifier" that replaces complex trees with equivalent simpler ones found in the registry.

### Complete Bootstrapping Chain
- [ ] **BOOT-01**: Derive and verify v2-grade functions: `sin`, `cos`, `tan`, `atan`.
- [ ] **BOOT-02**: Derive and verify statistical functions: `erf`, `gamma` (approximations).
- [ ] **BOOT-03**: Derive and verify hyperbolic functions: `sinh`, `cosh`, `tanh`.

### EML-Transformer (L-1 Compiler)
- [ ] **XFMR-01**: Analytical FFN weight initialization from EML tree structure.
- [ ] **XFMR-02**: Verification tool to compare transformer layer output against EML reference behavior.

## Out of Scope
- Multi-variable functions of more than 2 variables (staying univariate/bivariate for now).
- Direct GPU acceleration (keep core engine lightweight).

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SR-01 | Phase 5 | Pending |
| SR-02 | Phase 5 | Pending |
| SR-03 | Phase 5 | Pending |
| SR-04 | Phase 5 | Pending |
| DISC-07 | Phase 5 | Pending |
| DISC-08 | Phase 5 | Pending |
| DISC-09 | Phase 5 | Pending |
| TREE-01 | Phase 6 | Pending |
| TREE-02 | Phase 6 | Pending |
| BOOT-01 | Phase 7 | Pending |
| BOOT-02 | Phase 7 | Pending |
| BOOT-03 | Phase 7 | Pending |
| XFMR-01 | Phase 8 | Pending |
| XFMR-02 | Phase 8 | Pending |
