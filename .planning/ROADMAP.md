# Roadmap: EML-MCP

**Core Value:** Numerically correct EML results at machine-epsilon precision

## Completed Milestones
- [v1.0 (Foundation)](file:///.planning/milestones/v1.0-ROADMAP.md) — 2026-04-16 | Architecture, Persistence, and Goal-Directed Discovery
- [v2.0 (Deep Discovery)](file:///.planning/milestones/v2.0-ROADMAP.md) — 2026-04-16 | SR, Structural Analysis, and EML-Transformer Prototype
- [v3.0 (Production Readiness)](file:///.planning/milestones/v3.0-ROADMAP.md) — 2026-04-16 | Performance (torch.compile), Stability, and Diagnostics

---

## Milestone 4: Scaling & Evolution (v4.0)

### Phase 11: Dynamic Topology Optimization
**Goal:** Implement pruning mechanisms for the EML-Transformer that remove functionally redundant heads during training based on symbolic identities.
**Requirements:** OPT-01, MODEL-07
**Success Criteria:**
1. Transformer dynamically reduces its own complexity while maintaining accuracy.
2. Pruning decisions correlate with EML simplification rules (e.g., redundant identities).

### Phase 12: Multi-Variable Sheffer Discovery
**Goal:** Extend the EML engine to handle multi-variable input functions (mEML) as primitive nodes.
**Requirements:** DISC-07, COMP-03
**Success Criteria:**
1. Discovery engine successfully derives 2D functions (e.g., addition, mult) as primitive compositions.
2. Registry supports N-ary EML structures.

---
*Roadmap updated: 2026-04-16 | v3.0 Archive Complete*
