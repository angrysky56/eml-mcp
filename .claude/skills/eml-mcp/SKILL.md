---
name: eml-mcp
description: Use this skill when working with the EML (Exp-Minus-Log) MCP server — discovering pure-EML decompositions of elementary functions, inspecting the formula catalog, running symbolic regression, or reasoning about the Sheffer-style operator `eml(x, y) = exp(x) - ln(y)`. Trigger keywords include "EML", "elementary functions", "Sheffer operator for continuous math", "symbolic regression via EML", "eml_discover", and "K-complexity of a formula".
---

# EML MCP — Agent Skill

## What this is

The EML MCP server exposes the **EML (Exp-Minus-Log) operator**
`eml(x, y) = exp(x) - ln(y)` — a single binary function that, paired
with the constant `1`, generates every standard elementary function.
It's the continuous analogue of the NAND gate. Source:
Odrzywołek 2026, [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2).

The server is at `/home/ty/Repositories/ai_workspace/eml-mcp`. The
SQLite catalog `eml_formulas.db` persists every seed, discovery, and
verification across sessions.

## When to reach for what tool

Routing table — use the smallest/fastest tool that answers the question.

| Question / task                                               | Tool                              |
| ------------------------------------------------------------- | --------------------------------- |
| What formulas exist? What's in the catalog?                   | `eml_list_formulas`               |
| What's the full tree for a known formula?                     | `eml_tree_info`                   |
| Does `eml(a, b)` equal `z` for specific `a, b`?               | `eml_evaluate`                    |
| Is a stored tree correct to machine precision?                | `eml_verify`                      |
| How do these two formulas structurally compare?               | `eml_similarity` (Zhang-Shasha)   |
| Can this expression be simplified?                            | `eml_simplify`                    |
| Compile a Python math expression into an EML tree             | `eml_compile`                     |
| Fast discovery — expect to find it in seconds                 | `eml_discover` (sync, blocking)   |
| **Long discovery — expect minutes, want progress visibility** | `eml_discover_start` (async)      |
| Poll a running job                                            | `eml_discover_status`             |
| Retrieve a finished job's full result                         | `eml_discover_result`             |
| Stop a stuck/slow job, preserve partial progress              | `eml_discover_cancel`             |
| What jobs exist?                                              | `eml_discover_list`               |
| Gradient-based (PyTorch Adam) formula fitting                 | `eml_symbolic_regression`         |
| Build a parameterized master tree for SR                      | `eml_master_tree`                 |

## Hard-earned rules of thumb

1. **Default to async for anything beyond simple additive/scaling
   targets.** The sync `eml_discover` has a 4-minute MCP ceiling and
   loses partial progress on timeout. Async jobs checkpoint every
   5 iterations and survive restarts.

2. **Cancel liberally if MSE plateaus.** Cancellation preserves the
   best-so-far candidate and the top-N `nearby_discoveries`. A cancelled
   job is not a wasted one.

3. **K reported by a fresh discovery is the simplified K.** The engine
   now simplifies before persisting. `k_before_simplify` shows what the
   raw evolutionary tree looked like — usually 2–5× larger.

4. **If `eml_simplify` collapses a tree to a bare `const` or `var`,
   something in your derivation lost the symbolic structure.** This is
   rare but real — `e` and `zero` constant-fold to `2.718…` and `0.0`
   respectively, which is numerically correct but outside the pure-EML
   grammar `S → 1 | x | eml(S, S)`. The migration script guards
   against this; the live simplifier doesn't, so don't blindly trust
   its output when the input was already a seed.

5. **The constant `-697.281718171541` is a finite proxy for
   `ln(ln(0)) = -∞`.** Treat it as "essentially negative infinity" when
   reading trees. `exp(-697.28) ≈ 10⁻³⁰³` is zero at machine precision,
   so `eml(-697.28, z) ≈ -ln(z)`. This constant appears throughout
   compositionally-derived formulas; it's not a bug.

## Reference material

Load these on demand:

- **`reference/tool_decision_tree.md`** — detailed sync-vs-async
  routing, with worked examples for common targets.
- **`reference/k9_families.md`** — the K=9 template for `x + c` and
  `c·x`. Recognizing a family lets you predict K before running search.
- **`reference/operational_gotchas.md`** — the `-697.28` proxy,
  grammar-preservation, signature-based dedup, what the simplifier
  can and can't do.
- **`reference/observed_behavior.md`** — empirical notes on what
  resolves fast vs. stagnates, target selection guidance.
- **`research/paper_odrzywolek_2026.md`** — source paper summary and
  how the server's implementation relates to it.
- **`research/cross_domain_notes.md`** — pointers to the project's
  cross-domain exploration material.

## Files an agent should know about

```
eml-mcp/
├── README.md                              # Human-facing overview
├── docs/
│   ├── FORMULAS.md                        # Auto-generated catalog
│   ├── simplifier_k_reduction.md          # Migration rationale + numbers
│   ├── async_discovery.md                 # Background job architecture
│   ├── k9_families.md                     # Synthesis: K=9 templates
│   ├── cross_domain_exploration.md        # MGA mapping (NAND ↔ EML ↔ biology)
│   └── eml_transformer_architecture.md    # Older speculative design
├── src/eml_mcp/
│   ├── server.py           # @mcp.tool definitions
│   ├── discovery.py        # DiscoveryEngine, find_target, DiscoveryCancelled
│   ├── jobs.py             # Async JobStore, background threads, orphan sweep
│   ├── simplifier.py       # Identity-rule reduction + constant folding
│   ├── database.py         # SQLite schema + formula CRUD + job rows
│   ├── registry.py         # Seed formulas + verify_eml_identity
│   ├── trees.py            # EMLNode data structure
│   └── primitives.py       # eml() operator, test points, safe arithmetic
├── scripts/
│   ├── migrate_simplify_catalog.py   # One-shot K-reduction migration
│   ├── export_catalog.py             # Regenerate docs/FORMULAS.md
│   └── cleanup_duplicates.py         # Dedup catalog by signature
└── eml_formulas.db                    # The catalog (SQLite)
```

## Coding invariants for this project

The user (Ty) prefers:
- `uv` for Python tooling, Python 3.13+
- Type hints using `X | None`, `list[...]`, `dict[...]` (PEP 604/585, no
  `Optional`/`List`/`Dict`)
- `complex128` arithmetic (not `float64`) because trig needs complex
  intermediates via Euler's formula
- Edits over rewrites — `str_replace` / `edit_block`, not wholesale
  file rewrites
- **Never** start/stop/restart the MCP server — Ty manages that. The
  server does not hot-reload; after code changes, wait for Ty to
  restart it.

## Sanity-check workflow for code changes

After non-trivial edits to `src/eml_mcp/`:

```bash
cd /home/ty/Repositories/ai_workspace/eml-mcp
.venv/bin/python -m pytest tests/ -x -q --tb=short
```

All 78 tests should pass. The `test_sr_recovery*.py` tests take several
seconds each (they train torch networks); `test_parallel_discovery.py`
spawns processes; the rest are fast.

After catalog-affecting edits, regenerate the human-readable catalog:

```bash
.venv/bin/python scripts/export_catalog.py
```
