# EML Formula Catalog

_Auto-generated from `eml_formulas.db` at 2026-04-16T20:55:12+00:00. Do not edit by hand — regenerate with `uv run python scripts/export_catalog.py`._

**Grammar:** `S → 1 | eml(S, S)`  ·  **Reference:** Odrzywołek (2026), [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

**Totals:** 21 formulas (18 seeded / 3 discovered)

## Seeded primitives

| Name | Variables | Depth | K | Description |
|------|-----------|------:|--:|-------------|
| `e` | — | 1 | 3 | Euler's number e ≈ 2.71828 |
| `exp` | x | 1 | 3 | Exponential function exp(x) |
| `exp_exp` | x | 2 | 5 | Derived: exp(exp(x)) |
| `negate` | x | 2 | 5 | Negation -x = 0 - x (uses extended reals: ln(0)=-∞) |
| `reciprocal` | x | 2 | 5 | Derived: 1/x |
| `ln` | x | 3 | 7 | Natural logarithm ln(x) |
| `zero` | — | 3 | 7 | Constant 0 = ln(1) |
| `subtract` | x, y | 4 | 11 | Subtraction x - y = eml(ln(x), exp(y)) |
| `ln_ln` | x | 6 | 13 | Derived: ln(ln(x)) |
| `add` | x, y | 4 | 15 | Addition x + y = x - (0 - y) |
| `multiply` | x, y | 8 | 21 | Multiplication x × y = exp(ln(x) + ln(y)) |
| `divide` | x, y | 8 | 25 | Division x / y = x * (1/y) |
| `sinh` | x | 13 | 27 | Hyperbolic sine sinh(x) |
| `cosh` | x | 15 | 31 | Hyperbolic cosine cosh(x) |
| `sin` | x | 15 | 39 | Sine function sin(x) |
| `cos` | x | 17 | 43 | Cosine function cos(x) |
| `tanh` | x | 21 | 73 | Hyperbolic tangent tanh(x) |
| `tan` | x | 23 | 97 | Tangent function tan(x) |

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

**`negate`** — K=5, depth=2, leaves=3

- Expression: `eml(-697.281718171541, eml(x, 1))`
- RPN: `-697.281718171541 x 1.0 E E`
- Note: Simplified from K=17 to K=5 by migrate_simplify_catalog.

**`reciprocal`** — K=5, depth=2, leaves=3

- Expression: `eml(eml(-697.281718171541, x), 1)`
- RPN: `-697.281718171541 x E 1.0 E`
- Note: Simplified from K=21 to K=5 by migrate_simplify_catalog.

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

**`add`** — K=15, depth=4, leaves=8

- Expression: `eml(eml(1, eml(eml(1, x), 1)), eml(eml(-697.281718171541, eml(y, 1)), 1))`
- RPN: `1.0 1.0 x E 1.0 E E -697.281718171541 y 1.0 E E 1.0 E E`
- Note: Simplified from K=27 to K=15 by migrate_simplify_catalog.

**`multiply`** — K=21, depth=8, leaves=11

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(-697.281718171541, y...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E -697.281718171541 y E 1.0 E E 1.0 E`
- Note: Simplified from K=41 to K=21 by migrate_simplify_catalog.

**`divide`** — K=25, depth=8, leaves=13

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(-697.281718171541, e...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E -697.281718171541 -697.281718171541 y E 1.0 E E 1.0 E E 1.0 E`
- Note: Simplified from K=61 to K=25 by migrate_simplify_catalog.

**`sinh`** — K=27, depth=13, leaves=14

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(x, eml(eml(eml(-697.281718171541, eml(x...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x -697.281718171541 x 1.0 E E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E 1.0 E`
- Note: Simplified from K=91 to K=27 by migrate_simplify_catalog.

**`cosh`** — K=31, depth=15, leaves=16

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(x, eml(eml(-697.281718171541, eml(eml(e...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x -697.281718171541 -697.281718171541 x 1.0 E E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E 1.0 E`
- Note: Simplified from K=107 to K=31 by migrate_simplify_catalog.

**`sin`** — K=39, depth=15, leaves=20

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml((0.451582705289455+1.5707963267...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 (0.451582705289455+1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E (0.451582705289455-1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E (1.2246467991473532e-16+2j) E 1.0 E`
- Note: Simplified from K=171 to K=39 by migrate_simplify_catalog.

**`cos`** — K=43, depth=17, leaves=22

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml((0.451582705289455+1.5707963267...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 (0.451582705289455+1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E -697.281718171541 (0.451582705289455-1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E 1.0 E`
- Note: Simplified from K=187 to K=43 by migrate_simplify_catalog.

**`tanh`** — K=73, depth=21, leaves=37

- Expression: `eml(eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(x, eml(eml(eml(-6...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 x -697.281718171541 x 1.0 E E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E E 1.0 E E -697.281718171541 -697.281718171541 1.0 1.0 1.0 1.0 x -697.281718171541 -697.281718171541 x 1.0 E E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Simplified from K=257 to K=73 by migrate_simplify_catalog.

**`tan`** — K=97, depth=23, leaves=49

- Expression: `eml(eml(eml(1, eml(eml(1, eml(eml(1, eml(eml(1, eml(1, eml(eml(1, eml(eml(eml((0.451582...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 1.0 1.0 (0.451582705289455+1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E (0.451582705289455-1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E 1.0 E 1.0 E E E 1.0 E E E 1.0 E E (1.2246467991473532e-16+2j) E E 1.0 E E -697.281718171541 -697.281718171541 1.0 1.0 1.0 1.0 (0.451582705289455+1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E -697.281718171541 (0.451582705289455-1.5707963267948966j) -697.281718171541 x E 1.0 E E 1.0 E 1.0 E 1.0 E E 1.0 E E E 1.0 E E E 1.0 E E 2.0 E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Simplified from K=417 to K=97 by migrate_simplify_catalog.

## Discovered formulas

Formulas below were produced by the evolutionary Discovery Engine (`eml_discover`) or by gradient-based symbolic regression (`eml_symbolic_regression`). Each one passed novelty and stability checks against the prior catalog before being persisted.

| Name | K | Depth | Expression | Note |
|------|--:|------:|------------|------|
| `discovered_d432aaea` | 3 | 1 | `eml(x, 2.718281828459045)` | Simplified from K=13 to K=3 by migrate_simplify_catalog. |
| `discovered_526ee564` | 9 | 4 | `eml(eml(-0.3665129205816644, eml(eml(-697.281718171541, x...` _(see RPN for full form)_ | Simplified from K=41 to K=9 by migrate_simplify_catalog. |
| `discovered_b11d6e1f` | 21 | 8 | `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1))...` _(see RPN for full form)_ | Targeted search best MSE: 1.64e-31 |
