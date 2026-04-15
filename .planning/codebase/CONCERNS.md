# CONCERNS.md — Technical Debt, Known Issues & Risk Areas

## Critical Issues

### 1. No Test Suite
**Severity: High**

Zero test files exist despite `pytest` being in `dev` dependencies. The entire verification strategy relies on the `eml_verify` MCP tool — which means:
- Regressions in `eml_core.py` have no automated detection
- CI has no test stage (no CI config exists at all)
- Adding new formulas without tests risks silent breakage

**What exists:** `verify_eml_identity()` in `eml_core.py` is a solid foundation for building tests — it just isn't wired up as pytest fixtures yet.

### 2. No CI/CD
**Severity: Medium-High**

No GitHub Actions, no `.circleci/`, no CI configuration of any kind. Trunk is set up for local use only. Code could be pushed in a broken state without automated checks.

---

## Formula Compiler Gaps

### 3. `eml_compile` Has Very Limited Coverage
**Severity: Medium**

`eml_compile` in `server.py` (lines 252–345) only handles:
- Direct name lookups (`"exp"`, `"ln"`, `"e"`, `"zero"`, etc.)
- A static alias map (hardcoded strings like `"exp(x)"`, `"e^x"`)
- Four hardcoded compositions: `exp(exp(x))`, `ln(ln(x))`, `exp(ln(x))`, `ln(exp(x))`

Any other input returns an error. There's no parser, no AST, no grammar. Inputs like `"exp(ln(x) + ln(y))"` will fail even though the tree can be built manually.

**Note in code:**
```python
"Full compiler requires the bootstrapping chain from Odrzywołek's VerifyBaseSet procedure."
```

### 4. K Values for Composite Formulas Don't Match Paper's Compiler Path
**Severity: Low (documented, not a bug)**

Our subtraction tree has K=11 (matches paper's *direct search* optimum), while paper's compiler path gives K=83. Our negate tree is K=17 vs. paper's 15. These are documented in the README and in `KNOWN_FORMULAS` notes but could confuse users comparing results.

---

## Code Quality Concerns

### 5. Broad Exception Catch in MCP Tool Handlers
**Severity: Low**

```python
# server.py:124
except Exception as e:
    logger.error(f"Error evaluating EML: {e}")
    return {"status": "error", "message": str(e)}
```

The top-level `eml_evaluate` tool catches `Exception` broadly. While acceptable for MCP server stability, it masks unexpected errors (e.g., `numpy` broadcasting bugs, `TypeError` from wrong input types). Inner loops use narrower catches `(ValueError, ZeroDivisionError, OverflowError)` which is better practice.

### 6. `callable` Type Hint (Lowercase)
**Severity: Low**

```python
# eml_core.py:470
reference_fn: callable,
```

`callable` (lowercase) is deprecated as a type hint — should be `Callable[..., complex]` from `typing`. Works at runtime but violates strict typing and may trigger linter warnings in strict mode.

### 7. `ONE` Global Constant Not Used in Construction
**Severity: Low (technical debt, not a bug)**

```python
ONE = const(1.0)  # eml_core.py:207
```

`ONE` is defined but all builders use `_1()` factory calls instead, to avoid node aliasing. `ONE` is effectively dead code. Should either be removed or documented as intentional reference constant.

### 8. `extract_real` Tolerance Param Unused in Server
**Severity: Trivial**

`extract_real(z, tolerance=1e-10)` has a configurable tolerance but server code always calls it with default. Not a bug, but slightly misleading API.

---

## Numerical / Mathematical Concerns

### 9. Negation Formula Uses Extended Reals (`ln(0) = -∞`)
**Severity: Medium (works, but fragile)**

```python
def build_negate_tree() -> EMLNode:
    # -x = eml(ln(0), exp(x))
    # Uses extended reals: ln(0) = -inf, exp(-inf) = 0
```

This relies on IEEE754 behavior of infinity propagation through `numpy`. Works correctly on all standard platforms but is mathematically unusual — `ln(0)` is undefined in standard analysis. Any future change to `_safe_log` behavior for zero could silently break negation and all formulas that compose it (add, multiply).

### 10. Verification Test Points Hardcoded in Two Locations
**Severity: Low**

The transcendental test points (Euler-Mascheroni, Glaisher-Kinkelin, etc.) are defined:
1. In `eml_core.py:verify_eml_identity()` as defaults
2. In the `eml_verify` multivariate branch in `server.py` as a separate hardcoded list

These should be a single shared constant to prevent drift.

### 11. `exp` Reference Function Uses `math.e**z.real` Not `math.exp`
**Severity: Trivial**

```python
"exp": lambda z: (
    complex(math.e**z.real) if abs(z.real) < 700 else complex(float("inf"))
),
```

`math.e**z.real` is slightly less precise than `math.exp(z.real)` due to floating-point exponentiation vs. the hardware `exp` instruction. Difference is sub-ULP but inconsistent with stated machine-epsilon goals.

---

## Architecture / Future Risks

### 12. No Package Structure — Flat Module
**Severity: Low (appropriate for current size)**

Both modules live flat in the project root. If the codebase grows (e.g., adding a `compiler/` for the transformer compilation pipeline, a `tests/` package, or a `symbolic_regression/` module), the flat layout will need refactoring. The `pyproject.toml` build target already includes only `server.py` and `eml_core.py`, which is fine now.

### 13. EML-Transformer Architecture Is Purely Speculative
**Severity: Informational**

`docs/eml_transformer_architecture.md` (764 lines) is a detailed research spec for an EML-compiled transformer — but no implementation exists. The planned roadmap (Phase 1: exp PoC → Phase 5: hybrid LLM) has zero code yet. The MCP server is currently the oracle/tool layer for a future implementation.

### 14. `torch` Is Optional But Required for Key Use Cases
**Severity: Medium**

The symbolic regression / EML-Transformer use cases require `torch`, but it's in the `sr` optional group. New contributors attempting Phase 1 (PyTorch PoC) will hit an import error unless they install `pip install -e ".[sr]"`. No runtime guard or helpful error message exists.

---

## Summary Priority Table

| # | Concern | Severity | Effort to Fix |
|---|---------|----------|---------------|
| 1 | No test suite | High | Medium (2-3 days) |
| 2 | No CI/CD | Medium-High | Low (1 day) |
| 3 | Limited `eml_compile` | Medium | High (requires parser) |
| 9 | Fragile negation via `ln(0)` | Medium | Low (add guard + comment) |
| 14 | `torch` not installed by default | Medium | Low (add import guard) |
| 5 | Broad exception catch | Low | Low (narrow exception types) |
| 6 | `callable` type hint | Low | Trivial |
| 7 | Dead `ONE` constant | Low | Trivial (delete or document) |
| 10 | Duplicated test points | Low | Low |
| 11 | `math.e**z` vs `math.exp` | Trivial | Trivial |
| 12 | Flat module layout | Low | Medium (future refactor) |
