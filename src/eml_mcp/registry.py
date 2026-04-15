"""
EML formula registry — builder functions, KNOWN_FORMULAS, and numerical verification.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from eml_mcp.primitives import DTYPE, _safe_exp, _safe_log, eml
from eml_mcp.trees import (
    EMLNode,
    NodeType,
    _1,
    _x,
    const,
    eml_node,
    extract_real,
    var,
)


def build_exp_tree() -> EMLNode:
    """exp(x) = eml(x, 1) — depth 1, K=3."""
    return eml_node(_x(), _1())


def build_e_tree() -> EMLNode:
    """e = eml(1, 1) — depth 1, K=3."""
    return eml_node(_1(), _1())


def build_ln_tree() -> EMLNode:
    """ln(x) = eml(1, eml(eml(1, x), 1)) — depth 3, K=7.

    Equivalent to: e - ln(exp(e) / x) = ln(x)
    This is equation (5) from the paper.
    """
    inner = eml_node(_1(), _x())  # eml(1, x) = e - ln(x)
    middle = eml_node(inner, _1())  # eml(eml(1,x), 1) = exp(e - ln(x))
    return eml_node(_1(), middle)  # eml(1, ...) = e - ln(exp(e-ln(x)))


def build_zero_tree() -> EMLNode:
    """0 = ln(1) via EML — K=7.

    ln(1) = eml(1, eml(eml(1, 1), 1))
    Trace: eml(1,1)=e, eml(e,1)=exp(e), eml(1,exp(e))=e-ln(exp(e))=e-e=0
    """
    return build_ln_from_subtree(_1())  # ln(1) = 0


def build_ln_from_subtree(subtree: EMLNode) -> EMLNode:
    """ln(subtree) using the EML ln pattern.

    ln(z) = eml(1, eml(eml(1, z), 1))
    """
    inner = eml_node(_1(), subtree)
    middle = eml_node(inner, _1())
    return eml_node(_1(), middle)


def build_exp_from_subtree(subtree: EMLNode) -> EMLNode:
    """exp(subtree) = eml(subtree, 1)."""
    return eml_node(subtree, _1())


def build_subtract_tree() -> EMLNode:
    """x - y = eml(ln(x), exp(y)) — compiler depth ~5."""
    left = build_ln_from_subtree(var("x"))  # ln(x)
    right = build_exp_from_subtree(var("y"))  # exp(y)
    return eml_node(left, right)


def build_negate_tree() -> EMLNode:
    """-x = 0 - x = eml(ln(0), exp(x))."""
    zero = build_zero_tree()
    left = build_ln_from_subtree(zero)  # ln(0) = -inf
    right = build_exp_from_subtree(var("x"))  # exp(x)
    return eml_node(left, right)


def build_add_tree() -> EMLNode:
    """x + y = x - (0 - y) = x - (-y)."""
    zero = build_zero_tree()
    neg_y_left = build_ln_from_subtree(zero)
    neg_y_right = build_exp_from_subtree(var("y"))
    neg_y = eml_node(neg_y_left, neg_y_right)

    left = build_ln_from_subtree(var("x"))
    right = build_exp_from_subtree(neg_y)
    return eml_node(left, right)


def build_multiply_tree() -> EMLNode:
    """x × y = exp(ln(x) + ln(y))."""
    ln_x = build_ln_from_subtree(var("x"))
    ln_y = build_ln_from_subtree(var("y"))

    zero = build_zero_tree()
    neg_lny_left = build_ln_from_subtree(zero)
    neg_lny_right = build_exp_from_subtree(ln_y)
    neg_lny = eml_node(neg_lny_left, neg_lny_right)  # -(ln(y))

    add_left = build_ln_from_subtree(ln_x)
    add_right = build_exp_from_subtree(neg_lny)
    addition = eml_node(add_left, add_right)  # ln(x) + ln(y)

    return build_exp_from_subtree(addition)


KNOWN_FORMULAS: dict[str, dict[str, Any]] = {
    "exp": {
        "description": "Exponential function exp(x)",
        "builder": build_exp_tree,
        "depth": 1,
        "K": 3,
        "variables": ["x"],
    },
    "e": {
        "description": "Euler's number e ≈ 2.71828",
        "builder": build_e_tree,
        "depth": 1,
        "K": 3,
        "variables": [],
    },
    "ln": {
        "description": "Natural logarithm ln(x)",
        "builder": build_ln_tree,
        "depth": 3,
        "K": 7,
        "variables": ["x"],
    },
    "zero": {
        "description": "Constant 0 = ln(1)",
        "builder": build_zero_tree,
        "depth": 3,
        "K": 7,
        "variables": [],
    },
    "subtract": {
        "description": "Subtraction x - y = eml(ln(x), exp(y))",
        "builder": build_subtract_tree,
        "depth": 4,
        "K": 11,
        "variables": ["x", "y"],
        "note": "Matches paper's direct search optimum (K=11)",
    },
    "negate": {
        "description": "Negation -x = 0 - x (uses extended reals: ln(0)=-∞)",
        "builder": build_negate_tree,
        "depth": 7,
        "K": 17,
        "variables": ["x"],
        "note": "Paper direct search K=15; our compiler path K=17",
    },
    "add": {
        "description": "Addition x + y = x - (0 - y)",
        "builder": build_add_tree,
        "depth": 9,
        "K": 27,
        "variables": ["x", "y"],
        "note": "Matches paper compiler K=27; direct search K=19",
    },
    "multiply": {
        "description": "Multiplication x × y = exp(ln(x) + ln(y))",
        "builder": build_multiply_tree,
        "depth": 10,
        "K": 41,
        "variables": ["x", "y"],
        "note": "Matches paper compiler K=41; direct search K=17",
    },
}


def build_master_tree(depth: int, var_names: list[str] | None = None) -> dict[str, Any]:
    """Build a parameterized master formula tree for symbolic regression."""
    if var_names is None:
        var_names = ["x"]

    n_leaves = 2**depth
    n_internal = 2**depth - 1
    leaf_params = n_leaves * (1 + len(var_names))
    internal_params = (n_internal - 1) * (2 + len(var_names)) if n_internal > 1 else 0
    total_params = leaf_params + internal_params

    return {
        "depth": depth,
        "n_leaves": n_leaves,
        "n_internal_nodes": n_internal,
        "total_parameters": total_params,
        "formula_paper": f"5×2^{depth} - 6 = {5 * (2 ** depth) - 6}",
        "variables": var_names,
        "description": (
            f"Level-{depth} master formula: a complete binary tree with "
            f"{n_leaves} leaves and {n_internal} EML nodes. Contains ALL "
            f"possible elementary formulas up to this depth."
        ),
    }


def verify_eml_identity(
    tree: EMLNode,
    reference_fn: callable,
    test_points: list[complex] | None = None,
    variables: dict[str, complex] | None = None,
    tolerance: float = 1e-10,
) -> dict[str, Any]:
    """Verify an EML tree against a reference function."""
    if test_points is None:
        test_points = [
            complex(0.5772156649015329),
            complex(1.2824271291006226),
            complex(1.4142135623730951),
            complex(1.6180339887498949),
            complex(2.5),
            complex(0.1),
        ]

    results = []
    max_error = 0.0

    for point in test_points:
        var_bindings = variables or {"x": point}
        if "x" in var_bindings and variables is None:
            var_bindings = {"x": point}

        try:
            tree_val = tree.evaluate(var_bindings)
            ref_val = complex(reference_fn(point))
            error = abs(tree_val - ref_val)
            max_error = max(max_error, error)
            results.append(
                {
                    "input": extract_real(point),
                    "tree_output": extract_real(tree_val),
                    "reference": extract_real(ref_val),
                    "error": error,
                    "pass": error < tolerance,
                }
            )
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            results.append(
                {
                    "input": extract_real(point),
                    "error": str(e),
                    "pass": False,
                }
            )

    passed = all(r["pass"] for r in results)
    return {
        "passed": passed,
        "max_error": max_error,
        "tolerance": tolerance,
        "n_tests": len(results),
        "details": results,
    }
