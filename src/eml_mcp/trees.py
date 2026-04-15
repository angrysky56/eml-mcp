"""
EML binary tree structures — EMLNode, NodeType, and factory functions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from eml_mcp.primitives import DTYPE, _safe_exp, _safe_log


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
            # eml(x, y) = exp(x) - ln(y)
            # Using _safe_exp and _safe_log directly here to avoid circular imports
            # if we were to import 'eml' from operator.py
            return _safe_exp(left_val) - _safe_log(right_val)
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
            v = self.value.real if self.value.imag == 0 else self.value
            return [str(v.real) if isinstance(v, complex) and v.imag == 0 else str(v)]
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


def extract_real(z: complex, tolerance: float = 1e-10) -> float | complex:
    """Extract real part if imaginary part is negligible.

    EML operates in the complex domain but most results are real-valued.
    This cleans up the output for display.
    """
    if abs(z.imag) < tolerance:
        return z.real
    return z
