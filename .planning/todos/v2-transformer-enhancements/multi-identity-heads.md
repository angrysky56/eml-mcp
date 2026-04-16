---
title: "Add Multi-Identity 'Heads' to EML-Transformer FFN"
created_at: "2026-04-16"
status: pending
area: transformer-enhancements
priority: low
---

# Add Multi-Identity 'Heads' to EML-Transformer FFN

## Problem
Standard FFNs compute a high-dimensional representation. Scalar EML compilation is too narrow for standard LLM architectures.

## Proposed Solution
Extend `EMLCompiledFFN` to compute multiple identities in parallel (e.g., 8, 16, or 32 distinct EML-derived functions). This allows the transformer to have a "basis set" of analytical functions to attend to.
