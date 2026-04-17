# EML MCP Server

A Model Context Protocol server implementing the **EML (Exp-Minus-Log) operator** — a single binary function that generates all standard elementary functions.

```
eml(x, y) = exp(x) − ln(y)
```

Paired with the constant `1`, this operator reconstructs arithmetic, all transcendental functions, and constants including `e`, `π`, and `i`. It is the continuous-domain analogue of the NAND gate for Boolean logic.

**Based on:** Odrzywołek (2026), _"All elementary functions from a single operator"_ — [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

## Status

- **Current milestone:** v3.0 (Analytical Compilation), Completed — see `.planning/STATE.md`.
- **Live catalog:** [`docs/FORMULAS.md`](docs/FORMULAS.md) — auto-generated from the SQLite DB; regenerate with `uv run python scripts/export_catalog.py`.
- **Persistence:** Every seed, compiled composition, verification result, and symbolic-regression output is written to `eml_formulas.db`. The server ships with ~36 seeded/discovered primitives and accumulates more via discovery.
- **Catalog simplification:** `scripts/migrate_simplify_catalog.py` compresses stored trees via the identity-rule simplifier. On the seeded catalog it reduces total K by ~73% (1451 → 393). New discoveries are simplified before storage automatically. See [`docs/simplifier_k_reduction.md`](docs/simplifier_k_reduction.md).
- **Analytical Compilation:** `EMLCompiledFFN` mapping symbolic trees to high-performance PyTorch models with `torch.compile` support (4x speedup).
- **Non-blocking discovery:** long searches can be launched as background jobs (`eml_discover_start` → `eml_discover_status` → `eml_discover_result`, with `eml_discover_cancel` for cooperative stop). See [`docs/async_discovery.md`](docs/async_discovery.md).

## Quick Start

```json
{
  "mcpServers": {
    "eml-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/eml-mcp", "run", "eml-mcp"]
    }
  }
}
```

```bash
cd eml-mcp
uv venv --python 3.12 --seed
source .venv/bin/activate
uv sync
```

The server will create `eml_formulas.db` in its working directory on first run and seed it with the eight primitive formulas. Override the path with `EML_DB_PATH=/custom/path.db`.

## Core Idea

Every elementary function — `exp`, `ln`, `sin`, `cos`, addition, multiplication, powers, roots — can be expressed as a binary tree where:

- Every internal node computes `eml(left, right) = exp(left) − ln(right)`
- Every leaf is either the constant `1` or an input variable `x`

The grammar is: **`S → 1 | x | eml(S, S)`**

This is the continuous analogue of how every Boolean function reduces to NAND gates.

### Examples

```
e       = eml(1, 1)                           depth 1,  K=3
exp(x)  = eml(x, 1)                           depth 1,  K=3
ln(x)   = eml(1, eml(eml(1, x), 1))           depth 3,  K=7
x − y   = eml(ln(x), exp(y))                  depth 4,  K=11
x × y   = exp(ln(x) + ln(y))                  depth 10, K=41
```

## Complexity Metric (K)

The server reports **K** — a Kolmogorov-style complexity defined as the **total node count** (internal EML nodes + leaf terminals) in the tree. This matches the paper's definition: for a full binary tree with _L_ leaves, K = 2L − 1.

The server also reports **leaf_count** — the number of terminal nodes only. Both metrics are useful:

- **K** (node count) — directly comparable to the paper's Table 4
- **leaf_count** — counts the `1`'s and variables, useful for understanding tree structure

### Our trees vs. the paper

The compiler uses a **compositional approach** (build subtraction from ln + exp, build addition from subtraction + negation, etc.) which follows a different path than the paper's `VerifyBaseSet` bootstrapping procedure. The paper also reports results from exhaustive **direct search** (brute-force enumeration of all trees up to size N). Three values are worth tracking:

| Formula | Our K | Paper Compiler K | Paper Direct Search K | Notes                              |
| ------- | ----: | ---------------: | --------------------: | ---------------------------------- |
| exp(x)  |     3 |                3 |                     3 | All agree — optimal                |
| e       |     3 |                3 |                     3 | All agree — optimal                |
| ln(x)   |     7 |                7 |                     7 | All agree — optimal                |
| 0       |     7 |                7 |                     7 | All agree — optimal                |
| x − y   |    11 |               83 |                    11 | Matches direct search optimum      |
| −x      |    17 |               57 |                    15 | 2 nodes above optimum              |
| x + y   |    27 |               27 |                    19 | Matches paper compiler             |
| x × y   |    41 |               41 |                    17 | Matches paper compiler             |

For simple primitives (exp, ln, e, zero) all methods agree. For arithmetic, the compositional compiler sometimes matches the direct-search optimum (subtract), sometimes matches the paper's compiler (add, multiply), and is always far better than nothing. The gap between compiler K and direct-search K is the space the Discovery Engine is pointed at.

## Architecture

The server is organized into five layers that build on each other:

1. **Primitives & trees** (`primitives.py`, `trees.py`) — the `eml()` operator with `complex128` internals, safe arithmetic, and the `EMLNode` binary-tree data structure with evaluation, RPN, and substitution.
2. **Registry** (`registry.py`) — hand-built seed formulas (`exp`, `ln`, `e`, `zero`, `subtract`, `negate`, `add`, `multiply`) with their known compiler decompositions, plus the master-tree constructor and identity verifier.
3. **Persistence** (`database.py`) — SQLite (`eml_formulas.db`) with four tables: `formulas`, `derivations` (provenance), `verifications` (per-tolerance results), and `regression_results`. Signatures (tree outputs on standard test points) are cached per formula to make novelty checks O(1) instead of re-evaluating trees.
4. **Compiler & simplifier** (`compiler.py`, `simplifier.py`) — AST-based translation from Python math expressions into EML trees via registered primitives, plus identity-rule reduction (`exp(ln(x)) → x`, constant folding).
5. **Discovery** (`discovery.py`, `regression.py`, `similarity.py`) — two complementary search strategies:
   - **Evolutionary / novelty search** (`eml_discover`): random composition + mutation + hill climbing, ranked by MSE against the target, with Zhang-Shasha tree edit distance as a tiebreaker. Runs single-process or parallel via `ProcessPoolExecutor`.
   - **Gradient-based symbolic regression** (`eml_symbolic_regression`): builds a parameterized master formula tree (5·2ⁿ − 6 parameters at depth _n_), optimizes with Adam on complex128 data, then snaps weights to exact 0/1.

All tools share the same database singleton, so discoveries made by one invocation are immediately visible to `eml_list_formulas`, `eml_compile`, and the `eml://formulas` resource.

## Tools

| Tool                      | Description                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| `eml_evaluate`            | Evaluate `eml(x, y) = exp(x) − ln(y)` on given inputs                                       |
| `eml_explain`             | Provide a step-by-step evaluation trace (identity reduction log) for a formula              |
| `eml_list_formulas`       | List the live formula catalog from SQLite (seeds + discoveries)                             |
| `eml_tree_info`           | Inspect a formula's full tree structure, RPN code, and optionally evaluate                  |
| `eml_compile`             | Compile a Python math expression into an EML tree via registered primitives                 |
| `eml_verify`              | Verify an EML tree against its reference function using transcendental test points          |
| `eml_master_tree`         | Build a parameterized master formula tree for symbolic regression                           |
| `eml_symbolic_regression` | Gradient-based recovery (Adam on `complex128`); snaps weights to 0/1 on success             |
| `eml_discover`            | Evolutionary search for a formula matching a target expression; persists novel stable finds |
| `eml_discover_start`      | Launch evolutionary search as a background job; returns job_id immediately                  |
| `eml_discover_status`     | Poll progress of a background job (iterations_done, best_mse, best_k, best_expression)      |
| `eml_discover_result`     | Retrieve the final result dict of a completed/cancelled job                                 |
| `eml_discover_cancel`     | Request cooperative cancel; best-so-far is preserved                                        |
| `eml_discover_list`       | List recent jobs (any status), newest first                                                 |
| `eml_simplify`            | Apply identity rules (`exp(ln(x)) → x`) and constant folding; reports K reduction           |
| `eml_similarity`          | Zhang-Shasha tree edit distance and normalized similarity between two formulas              |

## Resources

| URI                      | Description                                                     |
| ------------------------ | --------------------------------------------------------------- |
| `eml://grammar`          | EML context-free grammar and key identities                     |
| `eml://formulas`         | **Live** formula catalog (JSON) read directly from SQLite       |
| `eml://complexity-table` | Full complexity table from the paper (Table 4)                  |

## Formula catalog

The live catalog is in [`docs/FORMULAS.md`](docs/FORMULAS.md) and is regenerated from the SQLite DB with:

```bash
uv run python scripts/export_catalog.py
```

Currently: **8 seeded primitives** and a growing set of **discovered formulas** from prior `eml_discover` and `eml_symbolic_regression` runs. Clients can also fetch the catalog live via the `eml://formulas` resource.

## Use cases

### 1. Exact symbolic regression

The **master formula** at level _n_ is a complete binary tree of 2ⁿ EML nodes containing every elementary function expression up to that depth. Train it with gradient descent:

```
Level 2: 14 parameters → 100% blind recovery
Level 3: 34 parameters → ~25% blind recovery
Level 5: 154 parameters → 100% from perturbed correct weights
```

When the generating law is elementary, trained weights snap from continuous values to exact 0/1 — bringing MSE to ~10⁻³² (machine epsilon squared). This is **interpretable AI**: the learned function has a closed-form expression.

### 2. Targeted discovery with proximity fallback

`eml_discover` performs an evolutionary search for a target expression. If an exact match (MSE < tolerance) is found, it is persisted as a named formula with provenance. If not, the top-N nearest candidates are returned — so even a failed search is diagnostic.

### 3. Complexity analysis

Measure the structural complexity of mathematical expressions on a uniform scale. K provides a principled Kolmogorov-like complexity measure for elementary functions — the length of the shortest pure-EML program computing the function.

### 4. Verification at machine precision

`eml_verify` uses algebraically independent transcendental test points (Euler-Mascheroni, Glaisher-Kinkelin, φ, √2) to check a stored tree against its reference function. Under the Schanuel conjecture, coincidental agreement across these points is vanishingly unlikely.

### 5. Cross-domain connections

EML is one instance of a **Minimal Generative Architecture (MGA)** — the same structural pattern (minimal primitives + recursion + boundary constraints = unbounded complexity) appears across:

| Domain               | Primitive      | Generates                          |
| -------------------- | -------------- | ---------------------------------- |
| Boolean logic        | NAND gate      | All logic circuits                 |
| Continuous math      | EML operator   | All elementary functions           |
| Evolutionary biology | 4 gene actions | Emergent morphology (OpenPraparat) |

See `docs/cross_domain_exploration.md` for the extended mapping.

### 6. Non-blocking long searches

Long evolutionary searches can be managed asynchronously using the background job tools. You can launch a search (`eml_discover_start`), poll its progress (`eml_discover_status`), retrieve final results (`eml_discover_result`), list recent jobs (`eml_discover_list`), or stop it early while preserving the best candidate (`eml_discover_cancel`). See [`docs/async_discovery.md`](docs/async_discovery.md).

## Known limitations

- **Depth ceiling.** `eml_symbolic_regression` is documented stable up to depth 2 and usable but unstable at depth 3+. Depth 4+ typically requires warm-starting from perturbed correct weights. This is a numerical-stability property of the gradient descent, not a bug per se.
- **Compiler coverage.** The AST compiler (`eml_compile`) only knows the 8 seed primitives plus whatever has been discovered into the DB. Arbitrary functions (`sin`, `cos`, `sqrt`, …) must be derived first with `eml_discover` before they can appear in a compiled expression. Error messages now include the exact `eml_discover` call to run.

## Maintenance

Two utility scripts, both safe to run repeatedly:

```bash
# Regenerate the human-readable catalog from the SQLite DB.
uv run python scripts/export_catalog.py

# Dedupe catalog rows that share an output signature.
# Default is dry-run — prints the plan without mutating. Pass --apply to execute.
uv run python scripts/cleanup_duplicates.py
uv run python scripts/cleanup_duplicates.py --apply
```

## Project layout

```
src/eml_mcp/
  ├── __init__.py        — Package exports
  ├── __main__.py        — Package entry point
  ├── primitives.py      — EML operator, safe arithmetic, standard test points
  ├── trees.py           — EMLNode data structure (eval, RPN, substitution)
  ├── registry.py        — Seed formula builders and identity verifier
  ├── database.py        — SQLite persistence (formulas, derivations, verifications, regressions)
  ├── compiler.py        — Python AST → EML tree compiler
  ├── simplifier.py      — Identity-rule reduction and constant folding
  ├── similarity.py      — Zhang-Shasha tree edit distance
  ├── discovery.py       — Evolutionary / novelty search engine
  ├── regression.py      — PyTorch master-tree training (optional, requires `[sr]` extra)
  ├── transformer.py     — AOT/JIT compilation of symbolic trees to analytical FFNNs
  ├── attention.py       — Symbolic attention routing over functional heads
  └── server.py          — FastMCP tool and resource definitions
scripts/
  └── export_catalog.py  — Regenerate docs/FORMULAS.md from the live DB
tests/                   — pytest suite (formulas, compiler, discovery, similarity, SR recovery, ...)
docs/
  ├── FORMULAS.md                   — Auto-generated formula catalog
  ├── cross_domain_exploration.md   — MGA cross-domain mapping
  └── eml_transformer_architecture.md
```

The core engine uses `complex128` throughout — trigonometric functions and π require complex intermediates via Euler's formula. Works cleanly with NumPy and PyTorch.

## Related

- [SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage) — Odrzywołek's original EML toolkit
- [hybrid-ai-mcp](https://github.com/angrysky56/hybrid-ai-mcp) — Boolean-domain companion (McCulloch-Pitts neurons, NAND logic)
- [mcp-logic](https://github.com/angrysky56/mcp-logic) — Automated reasoning server for verifying EML identities

## License

MIT
