# EML Formula Catalog

_Auto-generated from `eml_formulas.db` at 2026-04-16T05:30:05+00:00. Do not edit by hand — regenerate with `uv run python scripts/export_catalog.py`._

**Grammar:** `S → 1 | eml(S, S)`  ·  **Reference:** Odrzywołek (2026), [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

**Totals:** 10 formulas (8 seeded / 2 discovered)

## Seeded primitives

| Name | Variables | Depth | K | Description |
|------|-----------|------:|--:|-------------|
| `e` | — | 1 | 3 | Euler's number e ≈ 2.71828 |
| `exp` | x | 1 | 3 | Exponential function exp(x) |
| `ln` | x | 3 | 7 | Natural logarithm ln(x) |
| `zero` | — | 3 | 7 | Constant 0 = ln(1) |
| `subtract` | x, y | 4 | 11 | Subtraction x - y = eml(ln(x), exp(y)) |
| `negate` | x | 7 | 17 | Negation -x = 0 - x (uses extended reals: ln(0)=-∞) |
| `add` | x, y | 9 | 27 | Addition x + y = x - (0 - y) |
| `multiply` | x, y | 10 | 41 | Multiplication x × y = exp(ln(x) + ln(y)) |

### Seed expressions

**`e`** — K=3, depth=1, leaves=2

- Expression: `eml(1, 1)`
- RPN: `1.0 1.0 E`

**`exp`** — K=3, depth=1, leaves=2

- Expression: `eml(x, 1)`
- RPN: `x 1.0 E`

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

**`negate`** — K=17, depth=7, leaves=9

- Expression: `eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)), eml(x, 1))`
- RPN: `1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E x 1.0 E E`
- Note: Paper direct search K=15; our compiler path K=17

**`add`** — K=27, depth=9, leaves=14

- Expression: `eml(eml(1, eml(eml(1, x), 1)), eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, 1), 1))), 1)...` _(see RPN for full form)_
- RPN: `1.0 1.0 x E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E y 1.0 E E 1.0 E E`
- Note: Matches paper compiler K=27; direct search K=19

**`multiply`** — K=41, depth=10, leaves=21

- Expression: `eml(eml(eml(1, eml(eml(1, eml(1, eml(eml(1, x), 1))), 1)), eml(eml(eml(1, eml(eml(1, em...` _(see RPN for full form)_
- RPN: `1.0 1.0 1.0 1.0 x E 1.0 E E E 1.0 E E 1.0 1.0 1.0 1.0 1.0 E 1.0 E E E 1.0 E E 1.0 1.0 y E 1.0 E E 1.0 E E 1.0 E E 1.0 E`
- Note: Matches paper compiler K=41; direct search K=17

## Discovered formulas

Formulas below were produced by the evolutionary Discovery Engine (`eml_discover`) or by gradient-based symbolic regression (`eml_symbolic_regression`). Each one passed novelty and stability checks against the prior catalog before being persisted.

| Name | K | Depth | Expression | Note |
|------|--:|------:|------------|------|
| `discovered_target_0cf76d39` | 5 | 2 | `eml(eml(x, 1), 1)` | Targeted search iteration 22. |
| `discovered_d432aaea` | 13 | 5 | `eml(eml(1, eml(eml(1, eml(x, 1)), 1)), eml(1, 1))` | Targeted search best MSE: 8.22e-33 |
