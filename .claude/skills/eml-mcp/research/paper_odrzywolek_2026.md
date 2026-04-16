# Odrzywołek 2026 — "All elementary functions from a single operator"

- **arXiv**: [2603.21852v2](https://arxiv.org/html/2603.21852v2)
- **Reference implementation**: [VA00/SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage)

## Core claim

Every standard elementary function — `exp`, `ln`, `sin`, `cos`,
addition, multiplication, powers, roots — can be expressed as a binary
tree where every internal node is the same operator

```
eml(x, y) = exp(x) - ln(y)
```

and every leaf is either the constant `1` or an input variable. The
grammar is `S → 1 | x | eml(S, S)`.

This is the continuous analogue of the NAND theorem in Boolean logic.

## Paper's main quantitative results (Table 4)

K is the total node count of the smallest pure-EML tree computing the
function. The paper reports two K values per function:

- **Compiler K** — via the paper's compositional construction (build
  `subtract` from `ln`/`exp`, build `add` from `subtract` + `negate`,
  etc.). This is what our seed catalog originally stored.
- **Direct-search K** — via brute-force enumeration of all trees up to
  size N. Often substantially smaller.

Examples from the paper:

| Function | Compiler K | Direct-search K |
| -------- | ---------: | --------------: |
| `exp(x)` |          3 |               3 |
| `ln(x)`  |          7 |               7 |
| `x − y`  |         83 |              11 |
| `−x`     |         57 |              15 |
| `x + y`  |         27 |              19 |
| `x × y`  |         41 |              17 |

## How this server's implementation differs

- Uses `complex128` internals throughout (paper uses real arithmetic
  + Euler-form extensions when needed).
- Adds an **evolutionary discovery** mode (`eml_discover`) that the
  paper doesn't emphasize — the paper focuses on the grammar theorem
  and enumerative search.
- Adds **gradient-based symbolic regression** via the Mixture-of-
  Recursions trick (`eml_symbolic_regression`). The paper describes
  this approach conceptually; our implementation uses PyTorch + Adam.
- Applies the identity simplifier systematically after every
  discovery, so stored K reflects the simplified form. The paper
  reports raw direct-search K values.
- Catalog persistence in SQLite with provenance tracking.

## Verification methodology

The paper describes verifying identities on "algebraically independent
transcendental test points" — values like Euler-Mascheroni `γ`,
Glaisher-Kinkelin, `√2`, `φ`. Under Schanuel's conjecture, a candidate
tree that agrees with the reference function on all such points must
compute the exact same function (coincidental agreement has measure zero).

Our `eml_verify` uses this methodology with six test points. The
`TEST_POINTS` constant in `src/eml_mcp/primitives.py` is the
authoritative list.

## Open items mentioned in the paper

- Whether there exists a direct-search optimum for every function that
  beats the compositional compiler — the paper gives examples where
  yes and examples where the compiler is already tight.
- The precise K bounds for specific transcendentals like the Gamma
  function, Riemann zeta, etc. Our catalog doesn't include these yet.
- Whether EML has a normal-form theorem analogous to Boolean logic's
  Zhegalkin normal form. Open.

## Pointers within this repo

- `docs/k9_families.md` — a family of K=9 identities that beat the
  paper's direct-search for `c·x` (paper: K=17; ours: K=9). Presumed
  novel; not yet cross-referenced against the published literature.
- `docs/cross_domain_exploration.md` — connections to Boolean NAND,
  biological gene-regulatory minimality.
- `docs/simplifier_k_reduction.md` — the 73% catalog K reduction from
  systematic identity-rule simplification.
