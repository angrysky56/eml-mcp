# Tool decision tree

## Sync `eml_discover` vs async `eml_discover_start`

Rule of thumb: **sync for expected seconds; async for expected minutes.**

### Use sync (`eml_discover`) when:

- Target is in the K=9 additive-offset family (`x + c`) — resolves in
  iteration 0 by seeding from `discovered_d432aaea` (the `exp(x) - 1`
  pattern) or similar.
- Target is already in the catalog under a different name (the engine
  will signature-match and reuse).
- You're fine being blocked — short exploratory probe, answer-or-fail
  in under a minute.

### Use async (`eml_discover_start`) when:

- Target is transcendental (`sin`, `cos`, `tan`, hyperbolics) or
  composite (`sin(x) + x`, `x * exp(x)`).
- Target is a higher power (`x**3`, `x**4`) — no K=9 family here, and
  the search needs room.
- You plan to issue additional tool calls while waiting.
- You might want to abandon the search based on early MSE signal.

### Decision protocol for unknown targets

1. Call `eml_list_formulas` — check if the target is already in the
   catalog. If yes, done: call `eml_tree_info(name)`.
2. If not, call `eml_compile(expression)` — the AST compiler may emit
   a tree using existing primitives (often large K, but deterministic).
3. If `eml_compile` fails or you want a shorter form, start an async
   job with moderate parameters (`iterations=500`, `stagnation_limit=200`).
4. Poll every minute. If MSE is still above `0.5` after 100 iterations,
   the search is unlikely to close — cancel and either refine the
   target (e.g. reparameterize) or accept the nearby-discoveries as
   proximity fallback.

## Worked examples

### `x + 5` — trivial additive offset
```
eml_discover_start("x + 5", iterations=50)
# Expect: iteration 0, K=9, expression = eml(ln(x), e^-5)
```

### `math.sin(x)` — already in catalog
```
eml_tree_info("sin")
# K=39 after simplification. No discovery needed.
```

### `x**3` — unknown, moderate search
```
jid = eml_discover_start("x**3", iterations=500, stagnation_limit=150)
# Poll every 30s. If stagnating above MSE 0.05 at iter 100, cancel.
# The x² catalog entry (K=21) is a potential seed but x³ is harder.
```

### `math.log(x, 10)` — reparameterize
```
# log base 10 isn't a native primitive. Reparameterize:
#   log10(x) = ln(x) / ln(10) = ln(x) * (1/ln(10))
# Discovering it directly may be slow; starting from the known ln(x)
# seed and scaling is faster:
eml_discover_start("math.log(x) / math.log(10)", iterations=300)
```

## Gradient-based regression (`eml_symbolic_regression`)

Use when:
- You want a specific functional form and the target is smooth.
- Depth 1–2 master tree is sufficient (14–34 parameters).
- You're OK with stochastic success — the optimizer lands in discrete
  attractors; perturb and retry on failure.

Avoid when:
- Target involves `1j`, step functions, or sharp transitions.
- Depth 4+ — the docs call this "unstable" and it genuinely is.
  Evolutionary `eml_discover` handles deep trees better.
