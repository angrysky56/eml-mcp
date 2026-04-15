# STATE.md — Project Memory

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Numerically correct EML results at machine-epsilon precision
**Current focus:** Phase 1 — Package Restructure & Foundation

## Current State

- **Phase:** 1 of 4
- **Status:** Not started
- **Milestone:** v1
- **Next action:** `/gsd-plan-phase 1` or `/gsd-discuss-phase 1`

## Phase History

(None yet)

## Decisions Log

| Phase | Decision | Context |
|-------|----------|---------|
| Init | Exploratory derivation over fixed bootstrapping | MOP suggests entropy-maximizing exploration; K=11 < K=83 validates |
| Init | SQLite for persistence | Zero-dependency, embeddable, sufficient scale |
| Init | Formulas in DB, not code | Enables discovery, provenance tracking, no hardcoding |
| Init | MCP tools designed for AI agents | Primary users are AI, not humans |

## Blockers

(None)

---
*Last updated: 2026-04-15 after initialization*
