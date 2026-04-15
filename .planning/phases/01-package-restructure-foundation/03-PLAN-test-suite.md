---
plan: "03"
phase: "1"
wave: 2
depends_on: ["01"]
objective: "Create pytest test suite covering all 8 EML formulas with evaluate and verify checks"
files_modified:
  - tests/__init__.py
  - tests/test_formulas.py
requirements: [TEST-01]
autonomous: true
must_haves:
  - pytest discovers and runs all tests without configuration changes
  - All 8 formulas tested: exp, ln, e, zero, subtract, negate, add, multiply
  - Tests verify both tree structure (leaf_count, depth) and numerical correctness
---

## Objective

Create a `tests/` package with comprehensive formula tests. Tests must cover all 8 formulas in `KNOWN_FORMULAS` with both structural assertions (leaf count, depth) and numerical identity verification using known transcendental test points.

---

## Task 1: Create tests package

<read_first>
- src/eml_mcp/registry.py (KNOWN_FORMULAS keys and metadata: exp K=3 depth=1, ln K=7 depth=3, e K=3 depth=2, zero K=3 depth=2, subtract K=11, negate K=17, add K=35, multiply K=71)
- src/eml_mcp/operator.py (eml function for evaluating operator directly)
</read_first>

<action>
Create `tests/__init__.py` as an empty file:
```python
```

Create `tests/test_formulas.py` with this exact content:

```python
"""
Tests for all 8 EML formula decompositions.

Verifies:
1. Tree structure (leaf_count K and depth match documented values)
2. Numerical identity at transcendental test points (algebraically
   independent constants under Schanuel conjecture, per Odrzywołek 2026)
"""

from __future__ import annotations

import cmath
import math

import numpy as np
import pytest

from eml_mcp.operator import eml
from eml_mcp.registry import (
    KNOWN_FORMULAS,
    build_add_tree,
    build_e_tree,
    build_exp_tree,
    build_ln_tree,
    build_multiply_tree,
    build_negate_tree,
    build_subtract_tree,
    build_zero_tree,
    verify_eml_identity,
)
from eml_mcp.trees import EMLNode, const, var

# ---------------------------------------------------------------------------
# Transcendental test points (algebraically independent under Schanuel)
# Used to make false-positive identity proofs vanishingly unlikely.
# ---------------------------------------------------------------------------

EULER_MASCHERONI = 0.5772156649015328606065121  # γ
GLAISHER_KINKELIN = 1.2824271291006226368753425  # A

TEST_POINTS_UNIVARIATE = [
    complex(EULER_MASCHERONI, 0),
    complex(GLAISHER_KINKELIN, 0),
    complex(0.1, 0),
    complex(1.0, 0),
    complex(2.0, 0),
]

TEST_POINTS_BIVARIATE = [
    (complex(EULER_MASCHERONI, 0), complex(GLAISHER_KINKELIN, 0)),
    (complex(0.5, 0), complex(1.5, 0)),
    (complex(1.0, 0), complex(2.0, 0)),
]

TOLERANCE = 1e-10


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _eval(tree: EMLNode, **vars: complex) -> complex:
    """Evaluate a tree with given variable bindings."""
    return tree.evaluate(vars)


# ---------------------------------------------------------------------------
# Structure tests — verify K (leaf_count) and depth match KNOWN_FORMULAS
# ---------------------------------------------------------------------------


class TestTreeStructure:
    """All 8 formulas must have the documented K and depth values."""

    @pytest.mark.parametrize("name", list(KNOWN_FORMULAS.keys()))
    def test_formula_registered(self, name: str) -> None:
        entry = KNOWN_FORMULAS[name]
        assert "builder" in entry, f"{name}: missing 'builder' key"
        assert "K" in entry, f"{name}: missing 'K' key"
        assert "depth" in entry, f"{name}: missing 'depth' key"

    def test_exp_structure(self) -> None:
        tree = build_exp_tree()
        assert tree.leaf_count == 3, f"exp: expected K=3, got {tree.leaf_count}"
        assert tree.depth == 1, f"exp: expected depth=1, got {tree.depth}"

    def test_ln_structure(self) -> None:
        tree = build_ln_tree()
        assert tree.leaf_count == 7, f"ln: expected K=7, got {tree.leaf_count}"
        assert tree.depth == 3, f"ln: expected depth=3, got {tree.depth}"

    def test_e_structure(self) -> None:
        tree = build_e_tree()
        assert tree.leaf_count == 3, f"e: expected K=3, got {tree.leaf_count}"

    def test_zero_structure(self) -> None:
        tree = build_zero_tree()
        assert tree.leaf_count == 3, f"zero: expected K=3, got {tree.leaf_count}"

    def test_subtract_structure(self) -> None:
        tree = build_subtract_tree()
        assert tree.leaf_count == 11, f"subtract: expected K=11, got {tree.leaf_count}"

    def test_negate_structure(self) -> None:
        tree = build_negate_tree()
        assert tree.leaf_count == 17, f"negate: expected K=17, got {tree.leaf_count}"

    def test_add_structure(self) -> None:
        tree = build_add_tree()
        assert tree.leaf_count == 35, f"add: expected K=35, got {tree.leaf_count}"

    def test_multiply_structure(self) -> None:
        tree = build_multiply_tree()
        assert tree.leaf_count == 71, f"multiply: expected K=71, got {tree.leaf_count}"


# ---------------------------------------------------------------------------
# Numerical identity tests
# ---------------------------------------------------------------------------


class TestEMLOperator:
    """Direct operator: eml(x, y) = exp(x) - ln(y)."""

    def test_eml_at_zero_one(self) -> None:
        result = eml(0.0, 1.0)
        expected = complex(1.0)  # exp(0) - ln(1) = 1 - 0 = 1
        assert abs(result - expected) < TOLERANCE

    def test_eml_at_one_e(self) -> None:
        result = eml(1.0, math.e)
        expected = complex(math.e - 1.0)  # exp(1) - ln(e) = e - 1
        assert abs(result - expected) < TOLERANCE


class TestExpFormula:
    """EML tree for exp(x) must match math.exp at all test points."""

    def test_exp_numerical(self) -> None:
        tree = build_exp_tree()
        for z in TEST_POINTS_UNIVARIATE:
            result = _eval(tree, x=z).real
            expected = math.exp(z.real)
            assert abs(result - expected) < TOLERANCE, (
                f"exp({z.real}): EML={result}, expected={expected}"
            )

    def test_exp_via_verify(self) -> None:
        tree = build_exp_tree()
        ref = lambda z: complex(math.exp(z.real))  # noqa: E731
        passed, max_err, _ = verify_eml_identity(tree, ref)
        assert passed, f"exp verify failed, max_err={max_err}"


class TestLnFormula:
    """EML tree for ln(x) must match math.log at positive test points."""

    def test_ln_numerical(self) -> None:
        tree = build_ln_tree()
        for z in TEST_POINTS_UNIVARIATE:
            if z.real <= 0:
                continue
            result = _eval(tree, x=z).real
            expected = math.log(z.real)
            assert abs(result - expected) < TOLERANCE, (
                f"ln({z.real}): EML={result}, expected={expected}"
            )

    def test_ln_via_verify(self) -> None:
        tree = build_ln_tree()
        ref = lambda z: complex(math.log(abs(z.real)))  # noqa: E731
        passed, max_err, _ = verify_eml_identity(tree, ref)
        assert passed, f"ln verify failed, max_err={max_err}"


class TestEConstant:
    """EML tree for constant e must evaluate to math.e."""

    def test_e_value(self) -> None:
        tree = build_e_tree()
        result = tree.evaluate({}).real
        assert abs(result - math.e) < TOLERANCE, f"e: got {result}"


class TestZeroConstant:
    """EML tree for constant 0 must evaluate to 0."""

    def test_zero_value(self) -> None:
        tree = build_zero_tree()
        result = tree.evaluate({}).real
        assert abs(result) < TOLERANCE, f"zero: got {result}"


class TestSubtractFormula:
    """EML tree for x - y must equal x - y at test points."""

    def test_subtract_numerical(self) -> None:
        tree = build_subtract_tree()
        for x, y in TEST_POINTS_BIVARIATE:
            if x.real <= 0 or y.real <= 0:
                continue
            result = _eval(tree, x=x, y=y).real
            expected = x.real - y.real
            assert abs(result - expected) < TOLERANCE, (
                f"subtract({x.real}, {y.real}): EML={result}, expected={expected}"
            )


class TestNegateFormula:
    """EML tree for -x must equal -x at test points."""

    def test_negate_numerical(self) -> None:
        tree = build_negate_tree()
        for z in TEST_POINTS_UNIVARIATE:
            if z.real <= 0:
                continue
            result = _eval(tree, x=z).real
            expected = -z.real
            assert abs(result - expected) < TOLERANCE, (
                f"negate({z.real}): EML={result}, expected={expected}"
            )


class TestAddFormula:
    """EML tree for x + y must equal x + y at test points."""

    def test_add_numerical(self) -> None:
        tree = build_add_tree()
        for x, y in TEST_POINTS_BIVARIATE:
            result = _eval(tree, x=x, y=y).real
            expected = x.real + y.real
            assert abs(result - expected) < TOLERANCE, (
                f"add({x.real}, {y.real}): EML={result}, expected={expected}"
            )


class TestMultiplyFormula:
    """EML tree for x * y must equal x * y at test points."""

    def test_multiply_numerical(self) -> None:
        tree = build_multiply_tree()
        for x, y in TEST_POINTS_BIVARIATE:
            if x.real <= 0 or y.real <= 0:
                continue
            result = _eval(tree, x=x, y=y).real
            expected = x.real * y.real
            assert abs(result - expected) < TOLERANCE, (
                f"multiply({x.real}, {y.real}): EML={result}, expected={expected}"
            )


# ---------------------------------------------------------------------------
# Verification utility tests
# ---------------------------------------------------------------------------


class TestVerifyEMLIdentity:
    """verify_eml_identity() must correctly pass/fail."""

    def test_verify_passes_for_correct_formula(self) -> None:
        tree = build_exp_tree()
        ref = lambda z: complex(math.exp(z.real))  # noqa: E731
        passed, max_err, _ = verify_eml_identity(tree, ref)
        assert passed is True
        assert max_err < TOLERANCE

    def test_verify_fails_for_wrong_formula(self) -> None:
        tree = build_exp_tree()
        wrong_ref = lambda z: complex(math.log(abs(z.real)) + 1)  # noqa: E731
        passed, max_err, _ = verify_eml_identity(
            tree, wrong_ref,
            test_points=[complex(EULER_MASCHERONI)]
        )
        assert passed is False
```
</action>

<acceptance_criteria>
- `ls tests/` shows `__init__.py` and `test_formulas.py`
- `grep "def test_" tests/test_formulas.py | wc -l` prints `20` or more
- `python -m pytest tests/test_formulas.py --tb=short -q` exits 0 with all tests passing (run after Plan 02 completes so imports resolve)
</acceptance_criteria>
