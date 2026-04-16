# Phase Plan: Structural Similarity & Tree Optimization

**Status:** `completed` (retrospective)
**Date:** 2026-04-16

## Goal
Implement tree edit distance (Zhang-Shasha) to rank formulas by structural simplicity. Develop a "Simplifier" that reduces redundant EML compositions.

## Tasks
1. [x] Implement Zhang-Shasha algorithm in `similarity.py`.
2. [x] Implement `EMLSimplifier` in `simplifier.py`.
3. [x] Integrate structural ranking into `DiscoveryEngine`.
4. [x] Add deduplication to registry search.

## Success Criteria
1. `eml_discover` ranks results by both MSE and structural complexity.
2. Identities like `exp(ln(x)) -> x` are automatically simplified.
