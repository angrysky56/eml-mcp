# EML-MCP

## What This Is

An MCP (Model Context Protocol) server that gives AI assistants access to the EML (Exp-Minus-Log) operator — the single binary operator that generates all elementary functions from the constant 1. The continuous analogue of the NAND gate. Based on Odrzywołek (2026). Currently functional on GitHub as a stdio MCP server, used by Claude, Gemini, and other MCP-compatible agents.

## Core Value

The EML operator and its formula registry must produce numerically correct results at machine-epsilon precision for every known elementary function — correctness is non-negotiable because everything downstream (symbolic regression, MOP policy discovery, eventual transformer compilation) depends on it.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ EML operator evaluation (`eml(x, y) = exp(x) - ln(y)`) — existing
- ✓ Binary tree engine (`EMLNode`) with depth-first evaluation — existing
- ✓ Formula registry with 8 named formulas (exp, ln, e, zero, negate, subtract, add, multiply) — existing
- ✓ Numerical verification against transcendental test points per Schanuel conjecture — existing
- ✓ Master formula tree generation for symbolic regression — existing
- ✓ MCP server with 6 tools and 2 resources via FastMCP — existing
- ✓ Complex128 arithmetic throughout for correctness — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] **Package restructure** — Move flat files into `src/eml_mcp/` package with submodules
- [ ] **SQLite persistence layer** — Formula registry, cached trees, verification history, derivation provenance, symbolic regression results; replaces hardcoded `KNOWN_FORMULAS` dict
- [ ] **Expression AST** — Parse mathematical expressions (`"sin(x)"`, `"exp(ln(x))"`, `"a + b"`) into an intermediate AST representation
- [ ] **EML compiler** — Compile ASTs down to EML trees by composing known formulas; not a fixed bootstrapping chain but an exploratory derivation engine that discovers formulas by composition + numerical verification
- [ ] **Formula discovery engine** — Iterate: compose existing formulas → verify candidates → persist winners to DB; guided by complexity minimization (find shortest trees), not a prescribed derivation order
- [ ] **MCP tools for DB access** — AI-facing tools to search formulas, compose candidates, verify, persist; designed for agent consumption, not human readability
- [ ] **Test suite** — pytest covering all existing formulas, the compiler, DB operations, and the MCP tool surface
- [ ] **CI pipeline** — GitHub Actions for lint (trunk) + test on push/PR

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **EML-Transformer compilation** (EML tree → transformer weights) — separate project when the engine proves itself; architecture spec lives in `docs/` as reference
- **MOP policy discovery from simulation data** — depends on EML SR working first; future project
- **OpenPraparat / OEE integration** — requires MOP working first; research-stage
- **GUI / web interface** — MCP is the interface; AI agents are the users
- **Renaming the project** — it's on GitHub as `eml-mcp`, functional, and the MCP server is the primary interface until model compilation is proven

## Context

### Theoretical Foundation

EML is the computational substrate layer (L-1 in the extended EFHF framework). The Minimal Generative Architecture (MGA) pattern — minimal primitives + recursion + boundary constraints = unbounded complexity — appears across NAND (Boolean), EML (continuous math), MOP (cognition), and OpenPraparat (evolution). This server implements the EML instance.

The paper's bootstrapping chain prescribes a specific derivation order (~36 primitives). Our approach differs: we let the system *discover* derivations by exploratory composition rather than following the paper's fixed recipe. This is philosophically aligned with MOP's insight that entropy-maximizing exploration outperforms prescribed objectives. Our subtraction tree (K=11) already beats the paper's compiler path (K=83), validating this approach.

### Current State

- 2 Python files (`eml_core.py` at 541 lines, `server.py` at 345 lines), flat in project root
- 8 formulas hardcoded in a Python dict (`KNOWN_FORMULAS`)
- No tests, no CI, no persistence
- `eml_compile` is a static alias map with 4 hardcoded compositions — no parser, no AST
- Architecture spec for EML-Transformer exists in `docs/` (764 lines) but has zero implementation
- MGA synthesis document exists in external wiki linking EML to MOP, EFHF, OpenPraparat

### Codebase Map

Full analysis in `.planning/codebase/` (7 documents, 816 lines):
- `ARCHITECTURE.md` — Two-layer adapter pattern (core + MCP server)
- `STACK.md` — Python 3.12, FastMCP, NumPy complex128
- `CONCERNS.md` — 14 issues catalogued, prioritized

## Constraints

- **Language**: Python 3.12+ — established, dependencies locked
- **Precision**: Complex128 (float64 real + float64 imag) — required by paper for trigonometric functions via Euler's formula
- **MCP compatibility**: Must remain a valid MCP stdio server — existing users depend on it
- **No training-time dependencies in core**: PyTorch stays in the `sr` optional group — core engine runs without GPU
- **DB**: SQLite — zero external dependencies, single-file, embeddable; no Postgres/Redis

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Exploratory derivation over fixed bootstrapping chain | MOP suggests entropy-maximizing exploration beats prescribed objectives; our K=11 subtraction tree already beats paper's K=83 | — Pending |
| SQLite for persistence | Zero dependency, embeddable, sufficient for formula counts in the hundreds; agents don't need concurrent write throughput | — Pending |
| Formulas live in DB, not code | Hardcoded dict doesn't scale, can't track provenance or derivation history, prevents discovery | — Pending |
| Package as `src/eml_mcp/` | Standard Python packaging; allows proper imports, test discovery, and eventual PyPI distribution | — Pending |
| MCP tools designed for AI consumption | Primary users are AI agents, not humans; optimize for structured data, not readability | — Pending |
| EML-Transformer is a separate project | Prove the engine works first; model compilation is a different problem with different dependencies (PyTorch, GPU) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after initialization*
