"""
EML binary tree structures — EMLNode, NodeType, and factory functions.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from eml_mcp.primitives import _safe_exp, _safe_log


class NodeType(StrEnum):
    """Types of nodes in an EML expression tree."""

    CONST = "const"  # Terminal: constant 1
    VAR = "var"  # Terminal: input variable
    EML = "eml"  # Internal: eml(left, right)
    CALL = "call"  # Symbolic call to a registered function


@dataclass
class EMLNode:
    """A node in an EML expression tree.

    The grammar is: S → 1 | x | eml(S, S) | func(S, ...)

    Every elementary function expression is a binary tree of
    identical EML nodes — like a circuit of NAND gates.
    """

    node_type: NodeType
    value: complex | None = None  # For CONST nodes
    var_name: str | None = None  # For VAR nodes
    left: EMLNode | None = None  # Left child (exp input)
    right: EMLNode | None = None  # Right child (ln input)
    func_name: str | None = None  # For CALL nodes
    args: dict[str, EMLNode] | None = None  # Arguments for CALL nodes
    tape_idx: int | None = None  # Optional index in a matrix/tape representation

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
            return _safe_exp(left_val) - _safe_log(right_val)
        elif self.node_type == NodeType.CALL:
            raise ValueError(f"Cannot evaluate unexpanded CALL node: {self.func_name}")
        raise ValueError(f"Unknown node type: {self.node_type}")

    def explain(
        self, variables: dict[str, complex] | None = None, depth: int = 0
    ) -> list[str]:
        """Produce a hierarchical trace of how this node is evaluated."""
        indent = "  " * depth
        if self.node_type == NodeType.CONST:
            v_str = f"{self.value.real}" if self.value.imag == 0 else f"{self.value}"
            return [f"{indent}CONST: {v_str}"]

        if self.node_type == NodeType.VAR:
            val = variables.get(self.var_name, "N/A") if variables else "N/A"
            return [f"{indent}VAR '{self.var_name}': {val}"]

        if self.node_type == NodeType.CALL:
            trace = [f"{indent}CALL '{self.func_name}':"]
            for k, v in self.args.items():
                trace.append(f"{indent}  ARG '{k}':")
                trace.extend(v.explain(variables, depth + 2))
            return trace

        if self.node_type == NodeType.EML:
            try:
                l_val = self.left.evaluate(variables)
                r_val = self.right.evaluate(variables)
                e_l = _safe_exp(l_val)
                l_r = _safe_log(r_val)
                res = e_l - l_r

                def format_complex(z: complex) -> str:
                    return (
                        f"{z.real:.4f}"
                        if z.imag == 0
                        else f"{z.real:.4f}+{z.imag:.4f}j"
                    )

                trace = [f"{indent}EML -> {format_complex(res)}"]
                trace.append(
                    f"{indent}  Left: exp({format_complex(l_val)}) = {format_complex(e_l)}"
                )
                trace.extend(self.left.explain(variables, depth + 2))
                trace.append(
                    f"{indent}  Right: ln({format_complex(r_val)}) = {format_complex(l_r)}"
                )
                trace.extend(self.right.explain(variables, depth + 2))
                return trace
            except (ArithmeticError, ValueError, TypeError) as e:
                return [
                    f"{indent}EML (ERROR: {e})",
                    f"{indent}  L: {self.left.to_expression()}",
                    f"{indent}  R: {self.right.to_expression()}",
                ]

        return [f"{indent}UNKNOWN"]

    @property
    def depth(self) -> int:
        """Depth of this subtree."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 0
        if self.node_type == NodeType.EML:
            return 1 + max(self.left.depth, self.right.depth)
        # For CALL, depth is 1 + max of args or 0 if no args?
        # Actually, if we haven't expanded, it's opaque.
        return 1 + max((arg.depth for arg in self.args.values()), default=0)

    @property
    def leaf_count(self) -> int:
        """Number of terminal nodes (constants and variables)."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 1
        if self.node_type == NodeType.EML:
            return self.left.leaf_count + self.right.leaf_count
        return sum(arg.leaf_count for arg in self.args.values())

    @property
    def node_count(self) -> int:
        """Total nodes in the tree."""
        if self.node_type in (NodeType.CONST, NodeType.VAR):
            return 1
        if self.node_type == NodeType.EML:
            return 1 + self.left.node_count + self.right.node_count
        return 1 + sum(arg.node_count for arg in self.args.values())

    def copy(self) -> EMLNode:
        """Create a recursive deep copy of this tree."""
        if self.node_type == NodeType.CONST:
            return EMLNode(node_type=NodeType.CONST, value=self.value)
        elif self.node_type == NodeType.VAR:
            return EMLNode(node_type=NodeType.VAR, var_name=self.var_name)
        elif self.node_type == NodeType.EML:
            return EMLNode(
                node_type=NodeType.EML, left=self.left.copy(), right=self.right.copy()
            )
        elif self.node_type == NodeType.CALL:
            return EMLNode(
                node_type=NodeType.CALL,
                func_name=self.func_name,
                args={k: v.copy() for k, v in self.args.items()} if self.args else None,
            )
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
        elif self.node_type == NodeType.CALL:
            return EMLNode(
                node_type=NodeType.CALL,
                func_name=self.func_name,
                args=(
                    {k: v.substitute(var_mappings) for k, v in self.args.items()}
                    if self.args
                    else None
                ),
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
            if isinstance(v, (float, int)) and math.isfinite(v):
                return str(int(v) if v == int(v) else v)
            return str(v)
        elif self.node_type == NodeType.VAR:
            return self.var_name
        elif self.node_type == NodeType.CALL:
            arg_str = ", ".join(
                f"{k}={v.to_expression()}" for k, v in self.args.items()
            )
            return f"{self.func_name}({arg_str})"
        else:
            return f"eml({self.left.to_expression()}, {self.right.to_expression()})"

    def __str__(self) -> str:
        return self.to_expression()

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
        elif self.node_type == NodeType.CALL:
            return {
                "type": "call",
                "name": self.func_name,
                "args": (
                    {k: v.to_dict() for k, v in self.args.items()} if self.args else {}
                ),
            }
        else:
            return {
                "type": "eml",
                "left": self.left.to_dict(),
                "right": self.right.to_dict(),
            }

    def get_variables(self) -> set[str]:
        """Return all unique variable names in the tree."""
        vars_found = set()

        def collect(node: EMLNode):
            if node.node_type == NodeType.VAR:
                vars_found.add(node.var_name)
            elif node.node_type == NodeType.EML:
                if node.left:
                    collect(node.left)
                if node.right:
                    collect(node.right)

        collect(self)
        return vars_found

    def to_signature(self, test_points: list[complex]) -> list[complex] | None:
        """Compute the functional signature of this tree on test points.

        Returns None if evaluation fails or produces non-finite results.
        Uses N-ary sampling if the tree contains multiple variables.
        """
        vars_in_tree = sorted(list(self.get_variables()))
        if not vars_in_tree:
            # Handle constant trees
            vars_in_tree = ["x"]

        outputs = []
        for p in test_points:
            try:
                # Generate bindings match logic in DiscoveryEngine
                bindings = {}
                for j, v in enumerate(vars_in_tree):
                    scale = 1.1 + (j * 0.13)
                    offset = j * 0.071
                    bindings[v] = p * scale + offset

                val = self.evaluate(bindings)
                if not cmath.isfinite(val.real) or not cmath.isfinite(val.imag):
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
        if self.node_type == NodeType.EML:
            return self.left == other.left and self.right == other.right
        if self.node_type == NodeType.CALL:
            return self.func_name == other.func_name and self.args == other.args
        return False

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
        elif node_type_str == "call":
            args = (
                {k: cls.from_dict(v) for k, v in data["args"].items()}
                if "args" in data
                else None
            )
            return cls(node_type=NodeType.CALL, func_name=data["name"], args=args)
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
