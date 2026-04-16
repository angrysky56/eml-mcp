---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: v2-discovery-optimization
status: active
last_updated: "2026-04-16T03:38:00.000Z"
progress:
  total_phases: 8
  completed_phases: 6
  total_plans: 0
  completed_plans: 0
---

# STATE.md — Project Memory

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Numerically correct EML results at machine-epsilon precision
**Current focus:** Phase 7 — Deep Bootstrapping Chain

## Current State

- **Phase:** 7 of 8
- **Status:** Active
- **Milestone:** v2.0
- **Next action:** Systematize the derivation of higher-order identities (sin, cos, exp(exp(x))).

## Phase History

- **Phase 1 (Package Restructure):** Completed 2026-04-15.
- **Phase 2 (SQLite Persistence):** Completed 2026-04-15.
- **Phase 3 (AST & Compiler):** Completed 2026-04-15.
- **Phase 4 (Targeted Discovery):** Completed 2026-04-15.
- **Phase 5 (Symbolic Regression & Parallelism):** Completed 2026-04-16.
- **Phase 6 (Structural Similarity & Tree Optimization):** Completed 2026-04-16.

## Decisions Log

| Phase | Decision | Context |
|-------|----------|---------|
| 1-4 | Foundations | Package structure, SQLite, AST, and Initial Discovery |
| 5 | SelectionGate Initialization | Zeros logit bias towards 1.0 to prevent early divergence |
| 5 | EMLNode soft-clamping | Improved numerical stability for deep compositions |
| 5 | ProcessPool parallelization | Multi-worker discovery without DB connection issues |
| 5 | secrets for RNG | Secure and high-quality randomness in discovery |
| 6 | Structural Ranking | Use Zhang-Shasha TED as primary tie-breaker for MSE |
| 7 (prep) | Signature-based dedup in `find_target` | Prevents duplicate rows for the same tree across repeated target searches; prerequisite for clean Phase 7 sin/cos/tan derivation. Rollout: `_find_matching_formula_by_outputs()` in discovery.py; cleanup of existing duplicates via `scripts/cleanup_duplicates.py`. |

## Blockers

(None)

---
*Last updated: 2026-04-16 after Phase 5 completion*
