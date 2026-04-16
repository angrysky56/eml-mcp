---
title: "Implement Complex-Valued Support in EML Transformer blocks"
created_at: "2026-04-16"
status: pending
area: transformer-enhancements
priority: medium
---

# Implement Complex-Valued Support in EML Transformer blocks

## Problem
The symbolic EML discovery engine natively handles complex numbers, but the transformer prototype is currently real-valued only.

## Proposed Solution
Upgrade `EMLCompiledFFN` to use `torch.complex128` or `torch.complex64`. Remove `relu` clamping in favor of safe complex logarithms to maintain phase consistency across layers.
