# Operational gotchas

## The `-697.281718171541` constant

This is the EML compiler's finite proxy for `ln(ln(0)) = -∞`. It appears
throughout compositionally-derived formulas: `negate`, `reciprocal`,
`divide`, `cos`, `sin`, `tan`, `sinh`, `cosh`, `tanh`, and several
discovered forms.

**Why it works:** on the standard test points,
`exp(-697.28) ≈ 1.49 × 10⁻³⁰³`, which is numerically indistinguishable
from zero at IEEE-754 double precision. So:

```
eml(-697.28, z) = exp(-697.28) - ln(z) ≈ 0 - ln(z) = -ln(z)
```

When reading a tree, substitute `-697.28...` ↔ "negative infinity" and
the derivation becomes clear.

**Why not just `0` or `ln(0)` directly?** `ln(0)` is actually `-∞` in
extended reals, which NumPy represents as `-inf`. Arithmetic on `-inf`
propagates through expressions in ways that break identities (e.g.
`-inf + inf = nan`). The finite proxy preserves exact identities on the
test points because the compiler uses the Schanuel-conjecture-backed
transcendental sampling, which is unaffected by the ~10⁻³⁰³ remainder.

## Signature-based deduplication

Two formulas are treated as "the same function" iff their outputs on
the six standard transcendental test points agree to `1e-10`:

```python
TEST_POINTS = [
    γ (Euler-Mascheroni), Glaisher-Kinkelin, √2, φ (golden ratio),
    2.5, 0.1,
]
```

Under Schanuel's conjecture, coincidental agreement across all six
algebraically independent points has measure zero. Practically: if two
trees match on all six, they compute the same function.

**What this means operationally:**
- `eml_discover` won't create a duplicate catalog entry for a function
  already present — even if the new tree is structurally different.
- If it finds a **smaller K** for an existing function, it upgrades the
  existing entry in place (see `discovery.py:find_target`, "K-upgrade"
  logic).
- If you want to force a duplicate (e.g. for comparing structural
  variants), you'd need to bypass `add_formula` — there's no public
  API for that and it's probably a bad idea.

## What `eml_simplify` can and can't do

**Can:**
- Formally apply Equality Saturation globally across all subtrees via an E-Graph.
- Automatically collapse identities like `exp(ln(z)) → z` and `ln(exp(z)) → z` out-of-order anywhere in the equivalence class.
- Safely extract the minimal `k`-cost topology using Bellman-Ford graph traversal.
- Constant-fold `eml(c1, c2)` when both are numeric constants, handling cross-branch propagation seamlessly.

**Can't:**
- Inherently know complex algebraic identities (e.g. `x + (-x) → 0`) unless explicitly codified as structural pattern `RULES` in `simplifier.py`.
- Detect arbitrarily different but mathematically identical continuous features outside of its rewrite library (that's what `eml_similarity` + signature matching is for).
- Preserve grammar purity when a mathematically optimal reduction yields a bare constant.

## Grammar purity

Pure-EML grammar: `S → 1 | x | eml(S, S)`. Only `1` is allowed as a
constant leaf.

When the simplifier constant-folds `eml(1, 1) → const(2.718)`, the
resulting tree has a literal `2.718` leaf that's technically outside
the grammar. This is:
- **Fine** for numerical evaluation and verification.
- **Fine** for storage (K metric is still meaningful).
- **Breaks** `eml_compile` when the resulting tree is used as a
  sub-expression — the compiler expects pure-EML sub-trees.

The migration script (`scripts/migrate_simplify_catalog.py`) guards
against this for seeds (`e`, `zero` are not collapsed). New discoveries
from `find_target` do use the simplified form; if one of them collapses
to a bare constant, it's a genuine K=1 result and is stored that way —
just be aware it's a "found constant", not a "found pure-EML tree".

## Server lifecycle

- **No hot reload.** Code changes to `src/eml_mcp/**` require a
  restart. Ty handles this; never do it yourself.
- **Orphaned jobs:** if the server is killed mid-job, the `running`
  row in `discovery_jobs` is now swept on next boot and marked
  `failed` with `error='orphaned by server restart'`.
- **DB singleton:** `get_db()` opens the SQLite file once per process.
  `EML_DB_PATH` env var overrides the default `./eml_formulas.db`.

## Test-point quirks

`DiscoveryEngine._eval_tree_safe` binds extra variables as
`y = complex(0.42)` when the tree is bivariate. This is a deliberate
choice to let the signature distinguish bivariate from univariate forms
that happen to agree on `x`-only test points. If you're building a new
bivariate target, evaluate at `y=0.42` to match the engine's view.
