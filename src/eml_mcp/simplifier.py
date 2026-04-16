"""
EML Tree Simplifier
===================

Reduces redundant EML compositions and performs constant folding to minimize
tree complexity (node count K).
"""

from eml_mcp.primitives import _safe_exp, _safe_log
from eml_mcp.trees import EMLNode, NodeType, const, eml_node


def get_exp_input(node: EMLNode) -> EMLNode | None:
    """Check if node is exp(z) = eml(z, 1) and return z."""
    if node.node_type == NodeType.EML:
        if node.right.node_type == NodeType.CONST and abs(node.right.value - 1.0) < 1e-15:
            return node.left
    return None


def get_ln_input(node: EMLNode) -> EMLNode | None:
    """Check if node is ln(z) = eml(1, eml(eml(1, z), 1)) and return z."""
    if node.node_type != NodeType.EML:
        return None
    # eml(1, ...)
    if not (node.left.node_type == NodeType.CONST and abs(node.left.value - 1.0) < 1e-15):
        return None

    # ... eml(..., 1)
    middle = node.right
    if middle.node_type != NodeType.EML:
        return None
    if not (middle.right.node_type == NodeType.CONST and abs(middle.right.value - 1.0) < 1e-15):
        return None

    # ... eml(1, z) ...
    inner = middle.left
    if inner.node_type != NodeType.EML:
        return None
    if not (inner.left.node_type == NodeType.CONST and abs(inner.left.value - 1.0) < 1e-15):
        return None

    return inner.right


def simplify_tree(node: EMLNode) -> EMLNode:
    """Recursively simplify an EML tree."""
    if node.node_type != NodeType.EML:
        return node.copy()

    # 1. Simplify children first (post-order)
    left = simplify_tree(node.left)
    right = simplify_tree(node.right)
    simplified = eml_node(left, right)

    # 2. Constant Folding
    if left.node_type == NodeType.CONST and right.node_type == NodeType.CONST:
        try:
            val = _safe_exp(left.value) - _safe_log(right.value)
            return const(val)
        except (ValueError, ZeroDivisionError, OverflowError):
            pass

    # 3. Identity: exp(ln(z)) -> z
    exp_in = get_exp_input(simplified)
    if exp_in:
        ln_in = get_ln_input(exp_in)
        if ln_in:
            return ln_in.copy()

    # 4. Identity: ln(exp(z)) -> z
    ln_in = get_ln_input(simplified)
    if ln_in:
        exp_in = get_exp_input(ln_in)
        if exp_in:
            return exp_in.copy()

    # 5. Redundant eml(1, 1) -> e
    if left.node_type == NodeType.CONST and abs(left.value - 1.0) < 1e-15:
        if right.node_type == NodeType.CONST and abs(right.value - 1.0) < 1e-15:
            return const(2.718281828459045)  # math.e

    return simplified
