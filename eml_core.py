"""
EML Core Engine
================

Implementation of the EML (Exp-Minus-Log) operator and binary tree structures
for continuous mathematics, based on Odrzywołek (2026).

The EML operator eml(x, y) = exp(x) - ln(y), paired with constant 1,
generates all standard elementary functions — the continuous analogue
of the NAND gate for Boolean logic.

All arithmetic uses complex128 for correctness (trigonometric functions
and π require complex intermediates via Euler's formula).

Reference: https://arxiv.org/html/2603.21852v2
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

# ==================== Constants ====================

# Use complex128 throughout — EML requires complex intermediates
DTYPE = np.complex128


# Safe limits for exp to prevent overflow
EXP_CLAMP_MAX = 700.0  # exp(709) overflows float64
EXP_CLAMP_MIN = -700.0


def _safe_exp(z: complex | np.ndarray) -> complex | np.ndarray:
    """Clamped complex exponential to prevent overflow."""
    if isinstance(z, np.ndarray):
        real_clamped = np.clip(z.real, EXP_CLAMP_MIN, EXP_CLAMP_MAX)
        return np.exp(real_clamped + 1j * z.imag)
    real = max(EXP_CLAMP_MIN, min(EXP_CLAMP_MAX, z.real))
    return np.exp(complex(real, z.imag))


def _safe_log(z: complex | np.ndarray) -> complex | np.ndarray:
    """Complex logarithm (principal branch) with zero handling.

    Uses extended reals convention: ln(0) = -inf, consistent with
    IEEE754 and the EML paper's requirements.
    """
    if isinstance(z, np.ndarray):
        # Handle zero entries
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.log(z.astype(DTYPE))
    if z == 0:
        return complex(float("-inf"), 0.0)
    return np.log(complex(z))


# ==================== EML Operator ====================


def eml(x: complex, y: complex) -> complex:
    """The EML (Exp-Minus-Log) Sheffer operator.

    eml(x, y) = exp(x) - ln(y)

    This single binary operator, paired with the constant 1,
    generates all standard elementary functions.

    Args:
        x: First argument (feeds into exp).
        y: Second argument (feeds into ln).

    Returns:
        exp(x) - ln(y) as a complex number.
    """
    return _safe_exp(complex(x)) - _safe_log(complex(y))


def eml_array(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Vectorized EML operator for array inputs."""
    return _safe_exp(x.astype(DTYPE)) - _safe_log(y.astype(DTYPE))


# ==================== EML Binary Tree ====================


class NodeType(str, Enum):
    """Types of nodes in an EML expression tree."""

    CONST = "const"  # Terminal: constant 1
    VAR = "var"  # Terminal: input variable
    EML = "eml"  # Internal: eml(left, right)


@dataclass
class EMLNode:
    """A node in an EML expression tree.

    The grammar is: S → 1 | x | eml(S, S)

    Every elementary function expression is a binary tree of
    identical EML nodes — like a circuit of NAND gates.
    """

    node_type: NodeType
    value: complex | None = None  # For CONST nodes
    var_name: str | None = None  # For VAR nodes
    left: EMLNode | None = None  # Left child (exp input)
    right: EMLNode | None = None  # Right child (ln input)

    def evaluate(self, variables: dict[str, complex] | None = None) -> complex:
        """Evaluate this EML tree with given variable bindings."""
        if self.node_type == NodeType.CONST:
            return complex(self.value)
        elif self.node_type == NodeType.VAR:
            if variables is None or self.var_name not in variables:
                raise ValueError(f"Variable '{self.var_name}' not bound")
            return complex(variables[self.var_name])
        elif self.node_type == NodeType.EML:
            left_val = self.left.evaluate(variables)
            right_val = self.right.evaluate(variables)
            return eml(left_val, right_val)
        raise ValueError(f"Unknown node type: {self.node_type}")

    @property
    def depth(self) -> int:
        """Depth of this subtree."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 0
        return 1 + max(self.left.depth, self.right.depth)

    @property
    def leaf_count(self) -> int:
        """Number of terminal nodes (constants and variables)."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 1
        return self.left.leaf_count + self.right.leaf_count

    @property
    def node_count(self) -> int:
        """Total nodes in the tree (paper's Kolmogorov complexity K = 2L-1)."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 1
        return 1 + self.left.node_count + self.right.node_count

    def to_rpn(self) -> list[str]:
        """Convert to Reverse Polish Notation program."""
        if self.node_type == NodeType.CONST:
            return [str(self.value.real) if self.value.imag == 0 else str(self.value)]
        elif self.node_type == NodeType.VAR:
            return [self.var_name]
        else:
            return self.left.to_rpn() + self.right.to_rpn() + ["E"]

    def to_expression(self) -> str:
        """Human-readable expression string."""
        if self.node_type == NodeType.CONST:
            v = self.value.real if self.value.imag == 0 else self.value
            return str(int(v) if isinstance(v, float) and v == int(v) else v)
        elif self.node_type == NodeType.VAR:
            return self.var_name
        else:
            return f"eml({self.left.to_expression()}, {self.right.to_expression()})"

    def to_dict(self) -> dict[str, Any]:
        """Serialize tree to dictionary for JSON output."""
        if self.node_type == NodeType.CONST:
            v = self.value
            return {
                "type": "const",
                "value": v.real if v.imag == 0 else {"real": v.real, "imag": v.imag},
            }
        elif self.node_type == NodeType.VAR:
            return {"type": "var", "name": self.var_name}
        else:
            return {
                "type": "eml",
                "left": self.left.to_dict(),
                "right": self.right.to_dict(),
            }


# ==================== Tree Constructors ====================


def const(value: float = 1.0) -> EMLNode:
    """Create a constant leaf node (default: 1)."""
    return EMLNode(node_type=NodeType.CONST, value=complex(value))


def var(name: str = "x") -> EMLNode:
    """Create a variable leaf node."""
    return EMLNode(node_type=NodeType.VAR, var_name=name)


def eml_node(left: EMLNode, right: EMLNode) -> EMLNode:
    """Create an EML internal node: eml(left, right)."""
    return EMLNode(node_type=NodeType.EML, left=left, right=right)


# Shorthand aliases
ONE = const(1.0)


def _1() -> EMLNode:
    """Fresh constant-1 node."""
    return const(1.0)


def _x() -> EMLNode:
    """Fresh x-variable node."""
    return var("x")


# ==================== Known EML Formulas ====================
# From Odrzywołek (2026), Table 4 and Figure 1


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


# ==================== Extended Bootstrapping Chain ====================
# Following the paper's Figure 1 discovery order


def build_subtract_tree() -> EMLNode:
    """x - y = eml(ln(x), exp(y)) — compiler depth ~5.

    Key insight: eml contains subtraction.
    eml(a, b) = exp(a) - ln(b).
    Set a = ln(x) so exp(a) = x.
    Set b = exp(y) so ln(b) = y.
    Then eml(ln(x), exp(y)) = x - y.
    """
    left = build_ln_from_subtree(var("x"))  # ln(x)
    right = build_exp_from_subtree(var("y"))  # exp(y)
    return eml_node(left, right)


def build_negate_tree() -> EMLNode:
    """-x = 0 - x = eml(ln(0), exp(x)).

    Uses extended reals: ln(0) = -inf, exp(-inf) = 0.
    So eml(ln(0), exp(x)) = exp(ln(0)) - ln(exp(x)) = 0 - x = -x.
    Works in IEEE754 via inf and signed zeros.
    """
    zero = build_zero_tree()
    left = build_ln_from_subtree(zero)  # ln(0) = -inf
    right = build_exp_from_subtree(var("x"))  # exp(x)
    return eml_node(left, right)


def build_add_tree() -> EMLNode:
    """x + y = x - (0 - y) = x - (-y).

    Composes subtraction with negation.
    eml(ln(x), exp(eml(ln(0), exp(y))))
    """
    # Inner: -y = eml(ln(0), exp(y))
    zero = build_zero_tree()
    neg_y_left = build_ln_from_subtree(zero)
    neg_y_right = build_exp_from_subtree(var("y"))
    neg_y = eml_node(neg_y_left, neg_y_right)

    # Outer: x - (-y) = eml(ln(x), exp(-y))
    left = build_ln_from_subtree(var("x"))
    right = build_exp_from_subtree(neg_y)
    return eml_node(left, right)


def build_multiply_tree() -> EMLNode:
    """x × y = exp(ln(x) + ln(y)).

    Uses the fundamental log identity: ln(x*y) = ln(x) + ln(y).
    So x*y = exp(ln(x) + ln(y)).
    Composes exp with addition of two ln trees.
    """
    ln_x = build_ln_from_subtree(var("x"))
    ln_y = build_ln_from_subtree(var("y"))

    # ln(x) + ln(y) using the addition pattern: a + b = a - (0 - b)
    zero = build_zero_tree()
    neg_lny_left = build_ln_from_subtree(zero)
    neg_lny_right = build_exp_from_subtree(ln_y)
    neg_lny = eml_node(neg_lny_left, neg_lny_right)  # -(ln(y))

    # a + b = a - (-b) = eml(ln(a), exp(-b))
    # Here a = ln(x), b = ln(y)
    add_left = build_ln_from_subtree(ln_x)
    add_right = build_exp_from_subtree(neg_lny)
    addition = eml_node(add_left, add_right)  # ln(x) + ln(y)

    # exp(ln(x) + ln(y)) = x * y
    return build_exp_from_subtree(addition)


# ==================== Formula Registry ====================

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


def extract_real(z: complex, tolerance: float = 1e-10) -> float | complex:
    """Extract real part if imaginary part is negligible.

    EML operates in the complex domain but most results are real-valued.
    This cleans up the output for display.
    """
    if abs(z.imag) < tolerance:
        return z.real
    return z


# ==================== Master Formula Tree ====================


def build_master_tree(depth: int, var_names: list[str] | None = None) -> dict[str, Any]:
    """Build a parameterized master formula tree for symbolic regression.

    The master formula at level n has 5×2^n - 6 parameters.
    Each leaf input is: α_i + β_i·x + γ_i·f (previous EML output).
    At the lowest level (leaves), only α_i and β_i are used.

    Args:
        depth: Tree depth (1-6 recommended; 2^n leaves).
        var_names: Input variable names (default: ["x"]).

    Returns:
        Dictionary describing the tree structure and parameter count.
    """
    if var_names is None:
        var_names = ["x"]

    n_leaves = 2**depth
    n_internal = 2**depth - 1
    # At leaves: alpha + beta per variable = 1 + len(var_names) params per leaf
    # At internal: alpha + beta per variable + gamma = 2 + len(var_names) params
    leaf_params = n_leaves * (1 + len(var_names))
    internal_params = (n_internal - 1) * (2 + len(var_names)) if n_internal > 1 else 0
    # Top node doesn't need parameterization (it IS the output)
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


# ==================== Verification ====================


def verify_eml_identity(
    tree: EMLNode,
    reference_fn: callable,
    test_points: list[complex] | None = None,
    variables: dict[str, complex] | None = None,
    tolerance: float = 1e-10,
) -> dict[str, Any]:
    """Verify an EML tree against a reference function.

    Uses algebraically independent transcendentals as test points
    (following the paper's numeric bootstrapping approach).

    Args:
        tree: EML expression tree to verify.
        reference_fn: Python callable for the reference function.
        test_points: Custom test points (default: uses transcendentals).
        variables: Variable bindings for multivariate trees.
        tolerance: Maximum acceptable absolute error.

    Returns:
        Verification result with max error and pass/fail status.
    """
    if test_points is None:
        # Euler-Mascheroni, Glaisher-Kinkelin, sqrt(2), golden ratio
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
                    # trunk-ignore(bandit/B105)
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
