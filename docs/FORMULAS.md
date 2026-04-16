# EML Formula Catalog

_Auto-generated from `eml_formulas.db` at 2026-04-16T17:40:51+00:00. Do not edit by hand — regenerate with `uv run python scripts/export_catalog.py`._

**Grammar:** `S → 1 | eml(S, S)`  ·  **Reference:** Odrzywołek (2026), [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

**Totals:** 20 formulas (18 seeded / 2 discovered)

## Seeded primitives

| Name | Variables | Depth | K | Description |
|------|-----------|------:|--:|-------------|
| `e` | — | 1 | 3 | Euler's number e ≈ 2.71828 |
| `exp` | x | 1 | 3 | Exponential function exp(x) |
| `exp_exp` | x | 2 | 5 | Derived: exp(exp(x)) |
| `ln` | x | 3 | 7 | Natural logarithm ln(x) |
| `zero` | — | 3 | 7 | Constant 0 = ln(1) |
| `subtract` | x, y | 4 | 11 | Subtraction x - y = eml(ln(x), exp(y)) |
| `ln_ln` | x | 6 | 13 | Derived: ln(ln(x)) |
| `negate` | x | 7 | 17 | Negation -x = 0 - x (uses extended reals: ln(0)=-∞) |
| `reciprocal` | x | 9 | 21 | Derived: 1/x |
| `add` | x, y | 9 | 27 | Addition x + y = x - (0 - y) |
| `multiply` | x, y | 10 | 41 | Multiplication x × y = exp(ln(x) + ln(y)) |
| `divide` | x, y | 17 | 61 | Division x / y = x * (1/y) |
| `sinh` | x | 18 | 91 | Hyperbolic sine sinh(x) |
| `cosh` | x | 20 | 107 | Hyperbolic cosine cosh(x) |
| `sin` | x | 26 | 171 | Sine function sin(x) |
| `cos` | x | 28 | 187 | Cosine function cos(x) |
| `tanh` | x | 30 | 257 | Hyperbolic tangent tanh(x) |
| `tan` | x | 38 | 417 | Tangent function tan(x) |

### Seed expressions

**`e`** — K=3, depth=1, leaves=2

- Expression: `eml(1, 1)`
- RPN: `1.0 1.0 E`

**`exp`** — K=3, depth=1, leaves=2

- Expression: `eml(x, 1)`
- RPN: `x 1.0 E`

**`exp_exp`** — K=5, depth=2, leaves=3

- Expression: `eml(eml(x, 1), 1)`
- RPN: `x 1.0 E 1.0 E`
- Note: Systematically derived in Phase 7 bootstrapping.

**`ln`** — K=7, depth=3, leaves=4

- Expression: `eml(1, eml(eml(1, x), 1))`
- RPN: `1.0 1.0 x E 1.0 E E`

**`zero`** — K=7, depth=3, leaves=4

- Expression: `eml(1, eml(eml(1, 1), 1))`
- RPN: `1.0 1.0 1.0 E 1.0 E E`

**`subtract`** — K=11, depth=4, leaves=6

- Expression: `eml(eml(1, eml(eml(1, x), 1)), eml(y, 1))`
- RPN: `1.0 1.0 x E 1.0 E E y 1.0 E E`
- Note: Matches paper's direct search optimum (K=11)

**`ln_ln`** — K=13, depth=6, leaves=7

- Expression: `eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1))`
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E`
- Note: Systematically derived in Phase 7 bootstrapping.

**`negate`** — K=17, depth=7, leaves=9

- Expression: `eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)), eml(x, 1))`
- RPN: `1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E`
- Note: Paper direct search K=15; our compiler path K=17

**`reciprocal`** — K=21, depth=9, leaves=11

- Expression: `eml(eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)), eml(697.281718171541, 1)...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E x E 1.0 E`
- Note: Systematically derived in Phase 7 bootstrapping.

**`add`** — K=27, depth=9, leaves=14

- Expression: `eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)...` _(see RPN for full form)_
- RPN: `1.0 1.0 x E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E y 1.0 E E 1.0 E E`
- Note: Matches paper compiler K=27; direct search K=19

**`multiply`** — K=41, depth=10, leaves=21

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(eml(1, eml(eml(1, em...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 y E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Matches paper compiler K=41; direct search K=17

**`divide`** — K=61, depth=17, leaves=31

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(eml(1, eml(eml(1, em...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E y E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived from multiply and reciprocal.

**`sinh`** — K=91, depth=18, leaves=46

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 x 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(subtract(exp(x), exp(negate(x))), 2.0)

**`cosh`** — K=107, depth=20, leaves=54

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 x 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(add(exp(x), exp(negate(x))), 2.0)

**`sin`** — K=171, depth=26, leaves=86

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(eml(1, em...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1j E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1j 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2j E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(subtract(exp(multiply(1j, x)), exp(multiply(negate(1j), x))), 2j)

**`cos`** — K=187, depth=28, leaves=94

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(eml(eml(1, em...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1j E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1j 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(add(exp(multiply(1j, x)), exp(multiply(negate(1j), x))), 2.0)

**`tanh`** — K=257, depth=30, leaves=129

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1,...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 x 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 x 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(sinh(x), cosh(x))

**`tan`** — K=417, depth=38, leaves=209

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1,...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1j E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1j 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2j E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1j E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1j 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 x E 1.0 E E 1.0 E E 1.0 E E 1.0 E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 697.281718171541 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Systematically derived via EML identity: divide(sin(x), cos(x))

## Discovered formulas

Formulas below were produced by the evolutionary Discovery Engine (`eml_discover`) or by gradient-based symbolic regression (`eml_symbolic_regression`). Each one passed novelty and stability checks against the prior catalog before being persisted.

| Name | K | Depth | Expression | Note |
|------|--:|------:|------------|------|
| `discovered_d432aaea` | 13 | 5 | `eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(1, 1))` | Targeted search best MSE: 8.22e-33 |
| `discovered_b11d6e1f` | 21 | 8 | `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1))...` _(see RPN for full form)_ | Targeted search best MSE: 1.64e-31 |
