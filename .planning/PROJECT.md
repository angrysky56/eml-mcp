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
- ✓ **Package restructure** — Moved flat files into `src/eml_mcp/` package with submodules (v1.0)
- ✓ **SQLite persistence layer** — Formula registry, cached trees, verification history, derivation provenance; replaces hardcoded `KNOWN_FORMULAS` dict (v1.0)
- ✓ **Expression AST** — Parse mathematical expressions into intermediate AST (v1.0)
- ✓ **EML compiler** — Compile ASTs down to EML trees by composing known formulas (v1.0)
- ✓ **Formula discovery engine** — Composition + numerical verification with MSE proximity fallback (v1.0)
- ✓ **MCP tools for DB access** — Search, derive, and history tools for agent consumption (v1.0)
- ✓ **Test suite** — 46 pytest cases covering compiler, DB, and tools (v1.0)
- ✓ **CI pipeline** — GitHub Actions for lint (trunk) + test (v1.0)

### Active

<!-- Current scope. Building toward these. -->

- [ ] **Symbolic Regression Pipeline** — Implement Adam-based optimization for master formula trees
- [ ] **Parallel Discovery** — Multi-process discovery for higher throughput and depth
- [ ] **Structural Similarity** — Rank formulas by tree edit distance (Zhang-Shasha)
- [ ] **Deep Bootstrapping** — Derive all ~36 elementary functions from paper


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

- Modularized Python package under `src/eml_mcp/`
- SQLite persistence layer storing formula definitions, provenance, and verification logs
- Goal-directed discovery engine with MSE-based similarity search and proximal fallback
- 46 automated tests passing in CI; strictly formatted with Ruff and Black
- 9 MCP tools exposing registry, compiler, and discovery engine


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
| Exploratory derivation over fixed bootstrapping chain | MOP suggests entropy-maximizing exploration beats prescribed objectives; our K=11 subtraction tree already beats paper's K=83 | Implemented (v1.0) |
| SQLite for persistence | Zero dependency, embeddable, sufficient for formula counts in the hundreds; agents don't need concurrent write throughput | Implemented (v1.0) |
| Formulas live in DB, not code | Hardcoded dict doesn't scale, can't track provenance or derivation history, prevents discovery | Implemented (v1.0) |
| Package as `src/eml_mcp/` | Standard Python packaging; allows proper imports, test discovery, and eventual PyPI distribution | Implemented (v1.0) |
| MCP tools designed for AI consumption | Primary users are AI agents, not humans; optimize for structured data, not readability | Implemented (v1.0) |
| EML-Transformer is a separate project | Prove the engine works first; model compilation is a different problem with different dependencies (PyTorch, GPU) | Validated |

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
