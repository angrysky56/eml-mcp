---
title: "Vectorized Layer-Wise Unrolling of EML FFNs"
created_at: "2026-04-16"
status: pending
area: transformer-enhancements
priority: medium
---

# Vectorized Layer-Wise Unrolling of EML FFNs

## Problem
Current `EMLCompiledFFN` uses recursive module calls which is inefficient for deep trees and lacks standard tensor parallelism.

## Proposed Solution
Unroll the EML tree level-by-level into a sequence of parallel operations mapping each depth to a unified linear layer.
- Stage 1: All nodes at depth 1.
- Stage 2: All nodes at depth 2 (consuming outputs of depth 1 or terminals).
- Reduce: Final root node computation.
