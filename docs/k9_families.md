# K=9 Formula Families

Empirical observation from multiple evolutionary-discovery runs: both
pure-additive offsets `x + c` and pure scalings `c·x` admit K=9 EML
decompositions. These are **two-parameter templates** — the structural
shape is fixed; only the embedded constant changes with `c`. Once the
template is recognized, discovery for a new member of the family
collapses to constant fitting and resolves in zero evolutionary
iterations (it matches the DB seed on the first pass).

Both families beat the paper's compositional compiler K values (27 for
`add(x, c)`, 41 for `multiply(c, x)`) substantially.

## Notation

Throughout: `ε = -697.281718171541`. This is the EML compiler's finite
stand-in for `ln(ln(0)) = -∞`. On the standard test points
`exp(ε) ≈ 10⁻³⁰³`, which is indistinguishable from zero at machine
precision, so `eml(ε, z) = exp(ε) - ln(z) ≈ -ln(z)`. We'll write this as
`~ -ln(z)` when derivations are clearer that way.

## Family 1 — additive offsets `x + c`

**Template:** `eml(ln(x), e^(-c))`

**Unrolled form (K=9):**
```
eml(eml(1, eml(eml(1, x), 1)), e^(-c))
```

**Derivation:**
- The outer `eml(A, B)` computes `exp(A) - ln(B)`.
- Left subtree `A = ln(x)` (K=7, the standard natural-log decomposition).
- Right subtree `B = e^(-c)` (K=1, a literal constant).
- Result: `exp(ln(x)) - ln(e^(-c)) = x - (-c) = x + c`.

Total nodes: 7 (ln) + 1 (constant) + 1 (outer eml) = **9**.

**Domain:** any real `c` — the embedded constant `e^(-c)` is always a
positive real for real `c`, so `ln(e^(-c)) = -c` is always well-defined.

**Observed instances in the catalog:**

| Target  | Embedded constant       | Discovery    |
| ------- | ----------------------- | ------------ |
| `x + 1` | `e^(-1) ≈ 0.3679`       | Found iter 0 |
| `x + 2` | `e^(-2) ≈ 0.1353`       | Found iter 0 |

## Family 2 — scalings `c·x` (for c > 0)

**Template:** `eml(ln(ln(c)), eml(eml(ε, x), 1))`

**Unrolled form (K=9):**
```
eml(eml(ln(ln(c)), eml(eml(ε, x), 1)), 1)
```

**Derivation:**
- Outer `eml(A, 1) = exp(A)`.
- `A = eml(ln(ln(c)), B) = exp(ln(ln(c))) - ln(B) = ln(c) - ln(B)`.
- `B = eml(eml(ε, x), 1) = exp(exp(ε) - ln(x)) = exp(-ln(x)) = 1/x`.
- So `A = ln(c) - ln(1/x) = ln(c) + ln(x) = ln(c·x)`.
- Result: `exp(ln(c·x)) = c·x`.

Total nodes: 1 (ln(ln(c)) constant) + 1 (ε constant) + 1 (x variable) +
1 (literal 1) + 1 (literal 1 on outer) + 4 eml nodes = **9**.

**Domain:** `c > 1` gives a real `ln(ln(c))`. For `c = 1` the constant
is `ln(0) = -∞`, so the template degenerates. For `0 < c < 1` the
constant `ln(ln(c))` is complex, which is representable in the
`complex128`-backed engine but leaves the "real functions" regime. For
`c = e` the constant collapses to `ln(1) = 0`, giving the clean
`eml(eml(0, eml(eml(ε, x), 1)), 1) = e·x`.

**Observed instances in the catalog:**

| Target  | Embedded constant          | Discovery     |
| ------- | -------------------------- | ------------- |
| `2·x`   | `ln(ln(2)) ≈ -0.3665`      | Found iter ≈50 |

## Why both are K=9

The grammar forces every internal node to be a binary `eml` operation
over two subtrees that are themselves EML expressions. The smallest
useful univariate affine shape that's still *functional* (not a
constant) has to encode:

- at least one `x`-bearing leaf,
- enough depth to apply `exp` and/or `ln` around `x`,
- a distinct constant (unless `c` happens to equal one of the
  "free" values like `e` or `0` that the grammar already produces).

K=9 is what falls out when you need `ln(x)` on one side and a
constant-as-leaf on the other. Smaller (K=7, K=5, K=3) is only
achievable when the target itself is already a seed primitive
(`ln`, `exp`, `reciprocal`, `e`, `exp_exp`).

## Family 3? — multivariate `x + y`, `c·y`, etc.

Both families above are univariate in `x`. The bivariate analogues —
`x + y` or `c·y` — are just the same template with the variable
substituted. The current evolutionary engine happily finds these by
mutating the univariate template and substituting `y` for `x`. The K
cost is unchanged: both `ln(y)` and `ln(x)` are K=7 subtrees.

**Not yet verified:** a K=11 family for `x + y` (the full bivariate
add). The existing `subtract` seed is K=11 (`eml(ln(x), exp(y))`), and
the symmetry `x + y = x - (-y)` suggests a K=13 form via `negate`.
Direct-search by the paper finds K=19 for `add`. This is a gap worth
targeting with a focused evolutionary run.

## Diagnostic value

Recognizing a family makes debugging and reasoning much cheaper:

- If a discovery run for `c·x` produces anything **larger than K=9**,
  the optimizer got stuck in a local basin before the family's
  template emerged.
- If a result for `x + c` has a different shape than `eml(ln(x), k)`,
  either the constant isn't a pure `e^(-c)` (suggesting a
  parameter-fitting issue) or the search found a structurally
  different representation worth comparing by tree-edit distance.
- When seeding a new search, injecting the family template directly
  into the candidate pool would let evolution focus on constant
  fitting instead of structure discovery. (Not yet implemented — a
  natural extension.)

## Open questions

1. Is there a **K=9 family for `x^c`** (integer powers)? The existing
   `x²` is stored at K=21; a cleaner decomposition may exist.
2. Do these K=9 families have **K=7 instances for specific `c` values**
   that cause the outer node to degenerate? The `e·x` case above only
   gets down to K=9, not K=7, because the `exp` outer wrap is still
   required.
3. Is there a **K=11 `x + y`** template, closing the gap with
   `subtract`'s K=11?

Each of these is an evolutionary-discovery target; progress tracks in
`docs/FORMULAS.md`.
