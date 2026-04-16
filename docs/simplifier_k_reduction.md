# Simplifier-Driven K Reduction

**TL;DR** — Applying the identity-rule simplifier to every formula in the
catalog reduces total K by **73%** (1451 → 393 nodes across 21 formulas).
The reductions come "for free" — they are semantics-preserving rewrites,
verified by signature-equality on the standard transcendental test points.
Evolutionary discovery was storing trees 2–5x larger than necessary
because it persisted raw evolved candidates without simplification.

## Context

The `eml_discover` and `eml_symbolic_regression` tools generate candidate
trees through random composition and gradient-guided search. A newly-found
candidate that matches the target at machine precision is *functionally*
correct but *structurally* arbitrary — it is whatever shape the search
happened to land on. The identity simplifier (`src/eml_mcp/simplifier.py`)
applies the two ground rules

- `exp(ln(z)) → z`
- `ln(exp(z)) → z`

plus constant folding (`eml(const, const) → const`) over the tree until
fixed point. This is a normalization step, not a search: every rewrite
preserves the function computed by the tree.

## Catalog before and after

Applied via `scripts/migrate_simplify_catalog.py --apply` on the production
database. Rows that reduce are shown; rows where the simplifier found no
redundancy (`exp`, `ln`, `exp_exp`, `ln_ln`, `subtract`, `discovered_b11d6e1f`)
and rows where the only simplification would collapse the formula to a bare
constant (`e`, `zero` — see "Grammar-preservation guard" below) are omitted.

| Formula               | K before | K after | Reduction |
| --------------------- | -------: | ------: | --------: |
| `tan`                 |      417 |      97 |     76.7% |
| `tanh`                |      257 |      73 |     71.6% |
| `cos`                 |      187 |      43 |     77.0% |
| `sin`                 |      171 |      39 |     77.2% |
| `cosh`                |      107 |      31 |     71.0% |
| `sinh`                |       91 |      27 |     70.3% |
| `divide`              |       61 |      25 |     59.0% |
| `discovered_526ee564` (2x) |    41 |       9 |     78.0% |
| `multiply`            |       41 |      21 |     48.8% |
| `add`                 |       27 |      15 |     44.4% |
| `reciprocal`          |       21 |       5 |     76.2% |
| `negate`              |       17 |       5 |     70.6% |
| `discovered_d432aaea` (exp(x)-1) | 13 | 3 |   76.9% |
| **Total (changed rows)** | **1451** | **393** |  **72.9%** |

## Where the reductions come from

The seeded formulas for `cos`, `sin`, `tan`, and their hyperbolic cousins
were built compositionally: `cos(x) = divide(add(exp(ix), exp(-ix)), 2)`.
The compiler faithfully expanded each sub-identity into its full tree,
producing stacks like `exp(ln(exp(ln(...))))` whenever two compositional
steps happened to compose `exp` with `ln` or vice versa. The simplifier
collapses those stacks.

A concrete example. The `reciprocal` primitive was stored as a
21-node tree derived from `1/x = exp(ln(1) - ln(x))`. After simplification:

```
eml(eml(-697.281718171541, x), 1)
```

Five nodes. This is `exp(exp(-∞-proxy) - ln(x)) = exp(-ln(x)) = 1/x`. The
`-697.28` constant is the compiler's finite stand-in for `ln(ln(0)) = -∞`;
on the test points, `exp(-697.28) ≈ 10⁻³⁰³` is indistinguishable from zero
at machine precision.

The most striking reduction was `discovered_526ee564` for `2*x`:

```
before (K=41, compositional multiply(2, x)):
  eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 2), 1))), 1)),
          eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)),
                  eml(eml(1, eml(eml(1, x), 1)), 1)), 1)), 1)

after (K=9):
  eml(eml(-0.3665129205816644, eml(eml(-697.281718171541, x), 1)), 1)
```

Decoding the K=9 form: the outer `eml(⋯, 1)` is `exp(⋯)`; the inner
`eml(-697.28, x) ≈ -ln(x)`; one more layer flips the sign; the constant
`-0.3665... ≈ -ln(e·ln(2))` absorbs the factor. This beats the paper's
compiler value of K=41 for multiplication and approaches the direct-search
optimum.

## Grammar-preservation guard

The pure-EML grammar is

```
S → 1 | x | eml(S, S)
```

Only `1` is admitted as a constant leaf. A sufficiently aggressive
simplifier will constant-fold `eml(1, 1) = e` down to a single leaf node
holding the literal `2.718…`, which is outside the grammar. For seeds
that represent structural constants (`e`, `zero`), this erases the
symbolic derivation and breaks downstream `eml_compile` calls that expect
to embed these constants as sub-trees.

The migration script guards against this with `_count_eml_nodes` — if
simplification produces a tree with zero internal EML nodes, the original
is kept. In the production run this guard fired on `e` and `zero` as
expected.

## What the discovery engine now does

`discovery.py:find_target` now applies `simplify_tree` to every top-N
candidate before presentation, and uses the simplified tree as the
persisted form. The returned result includes both `k` (after simplify)
and `k_before_simplify` so the cost of the raw evolutionary shape is
visible without being the reported complexity.

When a candidate's signature matches an existing formula but its
simplified K is strictly smaller, `find_target` upgrades the existing
formula in place via `EMLFormulaDB.update_formula_tree`, with a note
recording the before/after K values. This closes the loop: once
discovery finds a shorter form for a known function, the catalog gets
the benefit without accumulating duplicate entries.

## Invariants maintained across the migration

For every rewritten row, the migration script verified:

1. **Signature equality** — outputs on the six standard transcendental
   test points agree to `1e-9`.
2. **Grammar preservation** — at least one EML internal node remains.
3. **Schema integrity** — `tree_json`, `rpn`, `expression`, `depth`, `k`,
   `leaf_count`, and `signature` were recomputed from the simplified tree
   in a single transaction.

A full backup of the pre-migration database is at
`eml_formulas.db.pre-simplify-backup`. The 78-test pytest suite passes
against the migrated database with no changes.

## Running the migration yourself

```bash
# Dry run — print the plan, make no changes.
uv run python scripts/migrate_simplify_catalog.py

# Apply on the default DB path (./eml_formulas.db or $EML_DB_PATH).
uv run python scripts/migrate_simplify_catalog.py --apply

# Apply on a specific DB.
uv run python scripts/migrate_simplify_catalog.py --apply --db /path/to.db
```

Safe to re-run — it is idempotent. A second pass after a successful apply
will report zero changes (every row is already at a fixed point of the
simplifier).
