---
title: Discovery Engine Philosophy
date: 2026-04-15
context: Exploration of minimal-generative-architectures.md
---

# Discovery Engine Philosophy

When building the Phase 3 Discovery Engine for EML formulas, we are adopting a **hybrid targeted + open-ended search approach (Novelty Search)**.

Instead of a rigid directed search where the fitness function is strictly "find the formula that matches exactly $f(x)$", the engine will embrace open-ended emergence constrained by mathematical boundaries.

### The Core Principle
1. **Target**: We still evaluate against a specific target reference function.
2. **Boundary Constraints**: We evaluate formulas for mathematical viability. If it results in `NaN`, overflow, or catastrophic branch cut violations, it "dies".
3. **Preservation of the Interesting**: If a formula survives the boundary constraints and exhibits unique, stable behavior, **we save it to the database**, even if it doesn't match our target function.

### Punctuated Equilibrium
By building a "Library of the Interesting", we maintain a diverse population of building blocks. A formula that appears "useless" today might be the exact stepping-stone (triggering a state-splitting event) needed to compose our exact target tomorrow.

*Reference: LLM-WIKI/wiki/synthesis/minimal-generative-architectures.md*
