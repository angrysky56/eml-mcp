# K=9 families — quick reference

Full write-up: [`docs/k9_families.md`](../../../../docs/k9_families.md)

## Fast lookup

### `x + c` for any real `c`

**Template:** `eml(ln(x), e^(-c))`, K=9.

```
# x + 1:  eml(ln(x), 0.3679...)      # 1/e
# x + 2:  eml(ln(x), 0.1353...)      # 1/e²
# x - 1:  eml(ln(x), 2.7183...)      # e
# x + c:  eml(ln(x), math.exp(-c))
```

Where `ln(x) = eml(1, eml(eml(1, x), 1))` is the K=7 standard form.

### `c·x` for `c > 1`

**Template:** `eml(ln(ln(c)), eml(eml(-697.28..., x), 1))` with outer
`eml(..., 1)` wrap — total K=9.

```
# 2·x:  eml(-0.3665..., eml(eml(-697.28..., x), 1))   # ln(ln(2))
# e·x:  eml(0, eml(eml(-697.28..., x), 1))            # ln(ln(e)) = 0
# c·x:  eml(math.log(math.log(c)), eml(eml(-697.28..., x), 1))
```

For `0 < c < 1`: `ln(ln(c))` is complex. Representable, but leaves real-
function regime.

## When these shortcuts matter

- If a discovery run for `c·x` returns K > 9, the search got stuck —
  rerun with more iterations or a different seed.
- If benchmarking K values against the paper's direct-search, these
  families already beat the paper for these targets (paper: `x+y` at
  K=19, `c·x` at K=17 for specific `c`; these templates: K=9).
- When verifying a tree for one of these targets, you can skip
  evolutionary search entirely and just plug the constants.

## Open slots

- K=9 for `x^c` (integer powers): unknown, possibly doesn't exist. `x²`
  is currently K=21.
- K=11 for `x + y` (full bivariate add): plausible by analogy with
  `subtract` (also K=11); not yet discovered.
