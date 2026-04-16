# Phase Plan: Deep Bootstrapping Chain

**Status:** `active`
**Date:** 2026-04-16

## Goal
Systematically derive the full ~36 elementary functions from the Odrzywołek (2026) paper using the optimized discovery engine, with a focus on trigonometric and higher-order exponential functions.

## Tasks
1. [ ] **Pre-computation Cleanup**: Run `scripts/cleanup_duplicates.py` to ensure a clean starting state for the registry.
2. [ ] **Trigonometric Core**:
    - [ ] Derive `sin(x)` using `eml_discover` tool.
    - [ ] Derive `cos(x)` using `eml_discover` tool.
    - [ ] Derive `tan(x)` using `eml_discover` tool.
3. [ ] **Hyperbolic Expansion**:
    - [ ] Derive `sinh(x)`, `cosh(x)`, `tanh(x)`.
4. [ ] **Higher-Order Identities**:
    - [ ] Derive `exp(exp(x))` (The "Double Exp").
    - [ ] Derive `ln(ln(x))` (The "Double Log").
5. [ ] **Automated Verification**: Run `pytest tests/test_formulas.py` to ensure all newly discovered formulas meet the transcedental test point criteria.
6. [ ] **Registry Consolidation**: Update the registry metadata and descriptions for the newly discovered functions.

## Success Criteria
1. Registry contains verified EML forms for `sin`, `cos`, `tan`, `exp(exp(x))`, etc.
2. Verification history shows zero regressions across the expanded set.
3. Total K (node count) for discovered identities is comparable or better than the paper's references.
