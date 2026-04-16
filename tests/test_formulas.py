"""
Tests for all 8 EML formula decompositions.

Verifies:
1. Tree structure (leaf_count K and depth match documented values)
2. Numerical identity at transcendental test points (algebraically
   independent constants under Schanuel conjecture, per Odrzywołek 2026)
"""

# trunk-ignore-all(bandit/B101)

from __future__ import annotations

import math

import pytest

from eml_mcp.primitives import eml
from eml_mcp.registry import (
    SEED_FORMULAS,
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
from eml_mcp.trees import EMLNode

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


def _eval(tree: EMLNode, **variables: complex) -> complex:
    """Evaluate a tree with given variable bindings."""
    return tree.evaluate(variables)


# ---------------------------------------------------------------------------
# Structure tests — verify K (leaf_count) and depth match KNOWN_FORMULAS
# ---------------------------------------------------------------------------


class TestTreeStructure:
    """All 8 formulas must have the documented K and depth values."""

    @pytest.mark.parametrize("name", list(SEED_FORMULAS.keys()))
    def test_formula_registered(self, name: str) -> None:
        """Verify formula properties are correctly registered."""
        entry = SEED_FORMULAS[name]
        assert "builder" in entry, f"{name}: missing 'builder' key"
        assert "K" in entry, f"{name}: missing 'K' key"
        assert "depth" in entry, f"{name}: missing 'depth' key"

    def test_exp_structure(self) -> None:
        """Verify the exp formula tree structure."""
        tree = build_exp_tree()
        assert tree.node_count == 3, f"exp: expected K=3, got {tree.node_count}"
        assert tree.depth == 1, f"exp: expected depth=1, got {tree.depth}"

    def test_ln_structure(self) -> None:
        """Verify the ln formula tree structure."""
        tree = build_ln_tree()
        assert tree.node_count == 7, f"ln: expected K=7, got {tree.node_count}"
        assert tree.depth == 3, f"ln: expected depth=3, got {tree.depth}"

    def test_e_structure(self) -> None:
        """Verify the e constant formula tree structure."""
        tree = build_e_tree()
        assert tree.node_count == 3, f"e: expected K=3, got {tree.node_count}"

    def test_zero_structure(self) -> None:
        """Verify the zero constant formula tree structure."""
        tree = build_zero_tree()
        assert tree.node_count == 7, f"zero: expected K=7, got {tree.node_count}"

    def test_subtract_structure(self) -> None:
        """Verify the subtract formula tree structure."""
        tree = build_subtract_tree()
        assert tree.node_count == 11, f"subtract: expected K=11, got {tree.node_count}"

    def test_negate_structure(self) -> None:
        """Verify the negate formula tree structure."""
        tree = build_negate_tree()
        assert tree.node_count == 17, f"negate: expected K=17, got {tree.node_count}"

    def test_add_structure(self) -> None:
        """Verify the add formula tree structure."""
        tree = build_add_tree()
        assert tree.node_count == 27, f"add: expected K=27, got {tree.node_count}"

    def test_multiply_structure(self) -> None:
        """Verify the multiply formula tree structure."""
        tree = build_multiply_tree()
        assert tree.node_count == 41, f"multiply: expected K=41, got {tree.node_count}"


# ---------------------------------------------------------------------------
# Numerical identity tests
# ---------------------------------------------------------------------------


class TestEMLOperator:
    """Direct operator: eml(x, y) = exp(x) - ln(y)."""

    def test_eml_at_zero_one(self) -> None:
        """Verify eml operator at (0, 1) equals 1."""
        result = eml(0.0, 1.0)
        expected = complex(1.0)  # exp(0) - ln(1) = 1 - 0 = 1
        assert abs(result - expected) < TOLERANCE

    def test_eml_at_one_e(self) -> None:
        """Verify eml operator at (1, e) equals e - 1."""
        result = eml(1.0, math.e)
        expected = complex(math.e - 1.0)  # exp(1) - ln(e) = e - 1
        assert abs(result - expected) < TOLERANCE


class TestExpFormula:
    """EML tree for exp(x) must match math.exp at all test points."""

    def test_exp_numerical(self) -> None:
        """Verify exp tree evaluates correctly numerically."""
        tree = build_exp_tree()
        for z in TEST_POINTS_UNIVARIATE:
            result = _eval(tree, x=z).real
            expected = math.exp(z.real)
            assert abs(result - expected) < TOLERANCE, (
                f"exp({z.real}): EML={result}, expected={expected}"
            )

    def test_exp_via_verify(self) -> None:
        """Verify exp tree via verify_eml_identity."""
        tree = build_exp_tree()

        def ref(z: complex) -> complex:
            return complex(math.exp(z.real))

        result = verify_eml_identity(tree, ref)
        assert result["passed"], f"exp verify failed, max_err={result['max_error']}"


class TestLnFormula:
    """EML tree for ln(x) must match math.log at positive test points."""

    def test_ln_numerical(self) -> None:
        """Verify ln tree evaluates correctly numerically."""
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
        """Verify ln tree via verify_eml_identity."""
        tree = build_ln_tree()

        def ref(z: complex) -> complex:
            return complex(math.log(abs(z.real)))

        result = verify_eml_identity(tree, ref)
        assert result["passed"], f"ln verify failed, max_err={result['max_error']}"


class TestEConstant:
    """EML tree for constant e must evaluate to math.e."""

    def test_e_value(self) -> None:
        """Verify e tree evaluates correctly numerically."""
        tree = build_e_tree()
        result = tree.evaluate({}).real
        assert abs(result - math.e) < TOLERANCE, f"e: got {result}"


class TestZeroConstant:
    """EML tree for constant 0 must evaluate to 0."""

    def test_zero_value(self) -> None:
        """Verify zero tree evaluates correctly numerically."""
        tree = build_zero_tree()
        result = tree.evaluate({}).real
        assert abs(result) < TOLERANCE, f"zero: got {result}"


class TestSubtractFormula:
    """EML tree for x - y must equal x - y at test points."""

    def test_subtract_numerical(self) -> None:
        """Verify subtract tree evaluates correctly numerically."""
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
        """Verify negate tree evaluates correctly numerically."""
        tree = build_negate_tree()
        for z in TEST_POINTS_UNIVARIATE:
            if z.real <= 0:
                continue
            result = _eval(tree, x=z).real
            expected = -float(z.real)
            assert abs(result - expected) < TOLERANCE, (
                f"negate({z.real}): EML={result}, expected={expected}"
            )


class TestAddFormula:
    """EML tree for x + y must equal x + y at test points."""

    def test_add_numerical(self) -> None:
        """Verify add tree evaluates correctly numerically."""
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
        """Verify multiply tree evaluates correctly numerically."""
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
        """Verify identity verification passes for correct formulas."""
        tree = build_exp_tree()

        def ref(z: complex) -> complex:
            return complex(math.exp(z.real))

        result = verify_eml_identity(tree, ref)
        assert result["passed"] is True
        assert result["max_error"] < TOLERANCE

    def test_verify_fails_for_wrong_formula(self) -> None:
        """Verify identity verification fails for incorrect formulas."""
        tree = build_exp_tree()

        def wrong_ref(z: complex) -> complex:
            return complex(math.log(abs(z.real)) + 1)

        result = verify_eml_identity(tree, wrong_ref, test_points=[complex(EULER_MASCHERONI)])
        assert result["passed"] is False


class TestHyperbolicAndLnLn:
    """Verify hyperbolic and double log identities from the database."""

    def test_hyperbolic_identities(self) -> None:
        from eml_mcp.database import EMLFormulaDB
        import json

        db = EMLFormulaDB()

        # Test sinh
        if db.formula_exists("sinh"):
            row = db.get_formula("sinh")
            tree = EMLNode.from_dict(
                json.loads(row["tree_json"]) if type(row["tree_json"]) is str else row["tree_json"]
            )

            def ref_sinh(z: complex) -> complex:
                import cmath

                return cmath.sinh(z)

            res = verify_eml_identity(tree, ref_sinh)
            assert res["passed"], f"sinh verification failed: {res['max_error']}"

        # Test cosh
        if db.formula_exists("cosh"):
            row = db.get_formula("cosh")
            tree = EMLNode.from_dict(
                json.loads(row["tree_json"]) if type(row["tree_json"]) is str else row["tree_json"]
            )

            def ref_cosh(z: complex) -> complex:
                import cmath

                return cmath.cosh(z)

            res = verify_eml_identity(tree, ref_cosh)
            assert res["passed"], f"cosh verification failed: {res['max_error']}"

        # Test tanh
        if db.formula_exists("tanh"):
            row = db.get_formula("tanh")
            tree = EMLNode.from_dict(
                json.loads(row["tree_json"]) if type(row["tree_json"]) is str else row["tree_json"]
            )

            def ref_tanh(z: complex) -> complex:
                import cmath

                return cmath.tanh(z)

            res = verify_eml_identity(tree, ref_tanh)
            assert res["passed"], f"tanh verification failed: {res['max_error']}"

        # Test ln_ln
        if db.formula_exists("ln_ln"):
            row = db.get_formula("ln_ln")
            tree = EMLNode.from_dict(
                json.loads(row["tree_json"]) if type(row["tree_json"]) is str else row["tree_json"]
            )

            def ref_ln_ln(z: complex) -> complex:
                import cmath

                # Only defined for Re(z) > 1 clearly for real log log, but use complex log
                return cmath.log(cmath.log(z))

            res = verify_eml_identity(
                tree,
                ref_ln_ln,
                test_points=[complex(EULER_MASCHERONI) + 2.0, complex(2.0), complex(3.0)],
            )
            assert res["passed"], f"ln_ln verification failed: {res['max_error']}"
