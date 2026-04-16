"""
EML binary tree structures — EMLNode, NodeType, and factory functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from eml_mcp.primitives import _safe_exp, _safe_log


class NodeType(StrEnum):
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

    def copy(self) -> EMLNode:
        """Create a recursive deep copy of this tree."""
        if self.node_type == NodeType.CONST:
            return EMLNode(node_type=NodeType.CONST, value=self.value)
        elif self.node_type == NodeType.VAR:
            return EMLNode(node_type=NodeType.VAR, var_name=self.var_name)
        elif self.node_type == NodeType.EML:
            return EMLNode(node_type=NodeType.EML, left=self.left.copy(), right=self.right.copy())
        raise ValueError(f"Unknown node type: {self.node_type}")

    def substitute(self, var_mappings: dict[str, EMLNode]) -> EMLNode:
        """Return a new tree with variables replaced by provided subtrees."""
        if self.node_type == NodeType.VAR and self.var_name in var_mappings:
            return var_mappings[self.var_name].copy()

        if self.node_type == NodeType.CONST:
            return EMLNode(node_type=NodeType.CONST, value=self.value)
        elif self.node_type == NodeType.VAR:
            return EMLNode(node_type=NodeType.VAR, var_name=self.var_name)
        elif self.node_type == NodeType.EML:
            return EMLNode(
                node_type=NodeType.EML,
                left=self.left.substitute(var_mappings),
                right=self.right.substitute(var_mappings),
            )
        raise ValueError(f"Unknown node type: {self.node_type}")

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

    def to_signature(self, test_points: list[complex]) -> list[complex] | None:
        """Compute the functional signature of this tree on test points.

        Returns None if evaluation fails or produces non-finite results.
        """
        import math

        outputs = []
        for point in test_points:
            try:
                # Supply 1.0 for other potential variables like 'y' during basic check
                val = self.evaluate({"x": point, "y": complex(1.0)})
                if math.isnan(val.real) or math.isinf(val.real):
                    return None
                outputs.append(val)
            except (ValueError, ZeroDivisionError, OverflowError):
                return None
        return outputs

    def __eq__(self, other: object) -> bool:
        """Structural equality check."""
        if not isinstance(other, EMLNode):
            return False
        if self.node_type != other.node_type:
            return False
        if self.node_type == NodeType.CONST:
            return abs(self.value - other.value) < 1e-15
        if self.node_type == NodeType.VAR:
            return self.var_name == other.var_name
        return self.left == other.left and self.right == other.right

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EMLNode:
        """Reconstruct an EMLNode tree from a dictionary (inverse of to_dict)."""
        node_type_str = data["type"]
        if node_type_str == "const":
            raw = data["value"]
            if isinstance(raw, dict):
                value = complex(raw["real"], raw["imag"])
            else:
                value = complex(raw)
            return cls(node_type=NodeType.CONST, value=value)
        elif node_type_str == "var":
            return cls(node_type=NodeType.VAR, var_name=data["name"])
        elif node_type_str == "eml":
            left = cls.from_dict(data["left"])
            right = cls.from_dict(data["right"])
            return cls(node_type=NodeType.EML, left=left, right=right)
        raise ValueError(f"Unknown node type: {node_type_str}")


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
