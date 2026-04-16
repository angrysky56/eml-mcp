---
title: "Cache and Reuse Redundant Sub-tree Activations"
created_at: "2026-04-16"
status: pending
area: transformer-enhancements
priority: low
---

# Cache and Reuse Redundant Sub-tree Activations

## Problem
Complex EML trees often re-use the same sub-trees (e.g. nested hyperbolic functions). Re-computing them in an FFN is wasteful.

## Proposed Solution
Map the symbolic simplifier's common sub-expression elimination (CSE) findings into the FFN architecture. Store intermediate activation results of unique sub-trees and reuse them across the depth of the FFN expansion.
