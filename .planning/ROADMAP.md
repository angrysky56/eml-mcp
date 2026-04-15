# Roadmap: EML-MCP v1

**Created:** 2026-04-15
**Granularity:** Coarse (4 phases)
**Core Value:** Numerically correct EML results at machine-epsilon precision

---

## Phase 1: Package Restructure & Foundation

**Goal:** Transform flat two-file project into a proper Python package with tests and CI — all existing functionality preserved.

**Requirements:** PKG-01, PKG-02, PKG-03, PKG-04, PKG-05, TEST-01, CI-01, CI-02, CI-03, CI-04

**UI hint:** no

**Success Criteria:**
1. `src/eml_mcp/` package exists with submodules; `eml_core.py` and `server.py` are gone from root
2. `python -m eml_mcp` or `uv run eml-mcp` starts the MCP server identically to before
3. All 6 existing MCP tools return identical results (verified by running each tool before/after)
4. `pytest` passes with tests covering all 8 existing formulas
5. GitHub Actions CI runs lint + test on push

**Depends on:** Nothing (foundation phase)

---

## Phase 2: SQLite Persistence Layer

**Goal:** Replace the hardcoded `KNOWN_FORMULAS` dict with a SQLite-backed formula registry that stores trees, verification history, and derivation provenance.

**Requirements:** DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, TEST-02

**UI hint:** no

**Success Criteria:**
1. SQLite database auto-creates on first run with all 8 seed formulas migrated
2. `eml_list_formulas` returns formulas from DB, not from Python dict
3. `eml_verify` writes verification results to DB with timestamp
4. `eml_tree_info` loads tree structure from DB
5. No hardcoded formula definitions remain in Python source (only seeds: constant 1, EML operator definition)
6. Tests cover all DB CRUD operations and migration

**Depends on:** Phase 1 (package structure for clean imports)

---

## Phase 3: AST, Compiler & Formula Discovery

**Goal:** Build a real expression parser that produces EML trees, plus a discovery engine that explores the formula space by composing existing formulas and verifying results.

**Requirements:** AST-01, AST-02, AST-03, AST-04, AST-05, DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, TEST-03, TEST-04, TEST-05

**UI hint:** no

**Success Criteria:**
1. `eml_compile("sin(x)")` parses the expression, looks up `sin` in DB, and returns the correct EML tree
2. `eml_compile("exp(exp(x))")` composes the `exp` tree with itself and returns a valid result
3. Parser handles operator precedence: `"x + y * z"` parses correctly
4. Compiler reports a clear error for unknown functions (not a crash)
5. Discovery engine can derive at least 2 new formulas not in the seed set by composition
6. All discovered formulas are verified numerically and persisted to DB with provenance
7. Tests cover parser (valid/invalid expressions), compiler (known/unknown functions), and discovery (compose/verify/persist)

**Depends on:** Phase 2 (DB for storing discovered formulas)

---

## Phase 4: MCP Tool Integration & Polish

**Goal:** Expose the DB, compiler, and discovery engine through new MCP tools; update all existing tools to use the DB backend; verify the full tool surface.

**Requirements:** MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, TEST-06

**UI hint:** no

**Success Criteria:**
1. `eml_db_search` returns formulas matching name/complexity/tag queries from DB
2. `eml_db_derive` composes two named formulas, verifies, and persists the result
3. `eml_db_history` returns timestamped verification records for a formula
4. All 6 original tools work against DB backend (not hardcoded dict)
5. All MCP tool responses are structured JSON suitable for AI agent consumption
6. Full test suite passes covering all old and new tools

**Depends on:** Phase 3 (compiler and discovery engine exist to expose)

---

## Summary

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Package Restructure & Foundation | Proper package + tests + CI | PKG-01–05, TEST-01, CI-01–04 | 5 |
| 2 | SQLite Persistence Layer | DB-backed formula registry | DB-01–06, TEST-02 | 6 |
| 3 | AST, Compiler & Discovery | Real parser + exploratory derivation | AST-01–05, DISC-01–05, TEST-03–05 | 7 |
| 4 | MCP Tool Integration & Polish | Expose everything via MCP | MCP-01–05, TEST-06 | 6 |

**Total:** 4 phases | 35 requirements | All v1 requirements covered ✓

---
*Roadmap created: 2026-04-15*
*Last updated: 2026-04-15 after initial creation*
