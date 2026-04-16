# Observed behavior — empirical notes

Collected from actual discovery runs. These are **observations**, not
theorems — individual runs vary because the evolutionary search is
stochastic.

## Resolves fast (iteration 0–50)

- **Additive offsets `x + c`**: always iteration 0, K=9. The engine
  seeds from `discovered_d432aaea` (`exp(x) - 1` at K=3) and the
  mutation operator flips the constant cleanly.
- **Simple scalings `c·x`** for `c ∈ {2, e, 10}`: typically iter 30–60,
  K=9. `c·x` for awkward constants (`π·x`, `1.618·x`) can stagnate.
- **Any target signature-matching an existing catalog entry**: iter 0
  via seed-pool reuse. If you see `reused_existing: true` in the
  result, this is what happened.

## Resolves with moderate effort (100–500 iterations)

- **`exp(x) + 1` and similar simple affine transforms of primitives**:
  usually resolves if you seed the search from `exp`'s tree.
- **Polynomials up to degree 3** when seeded from `x²`: occasional
  success; more often stagnates.
- **Linear combinations of known primitives** (`sin + cos`, `exp - ln`):
  variable; depends on whether the optimizer finds the template early.

## Stagnates (cancel after ~100 iterations)

- **Non-polynomial transcendentals not already in the catalog**: `arctan`,
  `erf`, `gamma`. These don't have simple EML identities and the
  mutation operator isn't targeted enough to find them.
- **Composite transcendentals**: `sin(x) + x`, `tan(x²)`, `exp(sin(x))`.
  Even with 500 iterations, MSE typically plateaus around 0.02–0.10.
- **High-degree polynomials**: `x⁴`, `x⁵`. The search wanders toward
  complex-valued `1j` combinations instead of real power structures.
- **Step functions, floor, abs**: not expressible in pure EML (violates
  smoothness), but the search will happily chase them anyway.

## What stagnation looks like

Watch for these signals in `eml_discover_status`:

- `best_mse` hasn't improved in the last 50 iterations.
- `best_k` keeps growing while `best_mse` barely moves — the search
  is adding structure without gaining fit.
- `best_expression` contains `1j` prominently and the target is real-
  valued — the optimizer has drifted into the complex plane.

When any of these hit, `eml_discover_cancel` and preserve the partial
result. The `nearby_discoveries` may still be useful as proximity
fallback or as seeds for a follow-up run.

## Parameter tuning observed so far

- **`stagnation_limit`**: default 200 is reasonable for exploration;
  lower (50–100) for fail-fast probes on uncertain targets.
- **`iterations`**: default 500 is enough for everything that will
  resolve at all; going to 1000+ rarely adds value.
- **`workers > 1`**: only worth it for very long runs (500+ iters) due
  to process-spawn overhead. For typical targets, single-worker is
  faster wall-clock.

## Simplify-at-save impact

Since the simplifier now runs before catalog storage:

- Top-line K reported to clients is 2–5× smaller than raw evolutionary
  K for most non-trivial targets.
- If a fresh discovery reports K=9, the underlying tree was probably
  K=27–41 before simplification — the K=9 families at `docs/k9_families.md`
  absorb a lot of evolutionary variation.
- The `k_before_simplify` field lets you spot cases where the engine
  happened to land on a compact form vs. cases where the simplifier
  did heavy lifting.

## Recommended first-attempt protocol for a new target

```
# 1. Is it already known?
eml_list_formulas()

# 2. Can the compiler build it from existing primitives?
eml_compile("<target>")   # may succeed with large K; acceptable baseline

# 3. Quick sync probe for simple targets
eml_discover("<target>", iterations=100, stagnation_limit=50)

# 4. Async for anything that didn't resolve in step 3
eml_discover_start("<target>", iterations=500, stagnation_limit=200)
# Poll every 30-60s; cancel if MSE plateaus above your tolerance.
```
