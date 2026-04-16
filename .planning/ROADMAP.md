# Roadmap: EML-MCP

**Core Value:** Numerically correct EML results at machine-epsilon precision

## Completed Milestones
- [v1.0 (Foundation)](file:///.planning/milestones/v1.0-ROADMAP.md) — 2026-04-16 | Architecture, Persistence, and Goal-Directed Discovery

---

## Milestone 2: Discovery Optimization & Symbolic Regression (v2.0)

### Phase 5: Symbolic Regression & Parallel Discovery
**Goal:** Implement the "Master Formula Tree" approach with gradient descent (Adam) optimization and weight snapping to recover discrete EML identities from data. Parallelize the discovery engine for higher throughput.
**Requirements:** SR-01, SR-02, COMP-02
**Success Criteria:**
1. Master formula tree optimizes weights against target function data points.
2. "Snapping" weights to 0/1 recovers known EML identities with high accuracy.
3. Discovery engine runs in parallel (multi-process) to explore larger composition depths.

### Phase 6: Structural Similarity & Tree Optimization
**Goal:** Implement tree edit distance (Zhang-Shasha) to rank formulas by structural simplicity. Develop a "Simplifier" that reduces redundant EML compositions.
**Requirements:** COMP-01 (Partial), DISC-04 (Enhancement)
**Success Criteria:**
1. `eml_discover` ranks results by both MSE and structural complexity.
2. Identities like `exp(ln(x)) -> x` are automatically simplified in the registry.

### Phase 7: Deep Bootstrapping Chain
**Goal:** Systematically derive the full ~36 elementary functions from the Odrzywołek (2026) paper using the optimized discovery engine.
**Requirements:** COMP-01
**Success Criteria:**
1. Registry contains verified EML forms for `sin`, `cos`, `tan`, `erf`, `bessel`, etc.
2. Verification history shows zero regressions across the expanded set.

### Phase 8: EML-Transformer Prototype
**Goal:** Implement the EML-Transformer compiler pattern: mapping EML trees directly to transformer weight tensors (analytical FFN construction).
**Requirements:** MODEL-01, MODEL-02, MODEL-03
**Success Criteria:**
1. A small transformer model is initialized with EML-derived weights.
2. Model output matches reference function behavior within strict numerical tolerance.

---
*Roadmap updated: 2026-04-16*
