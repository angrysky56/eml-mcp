"""
EML-MCP: Model Context Protocol server for the EML (Exp-Minus-Log) Sheffer operator.

All elementary functions from a single binary operator, based on Odrzywołek (2026).
Reference: https://arxiv.org/html/2603.21852v2
"""

from eml_mcp.database import EMLFormulaDB
from eml_mcp.primitives import DTYPE, EXP_CLAMP_MAX, EXP_CLAMP_MIN, eml, eml_array
from eml_mcp.registry import (
    SEED_FORMULAS,
    build_add_tree,
    build_e_tree,
    build_exp_from_subtree,
    build_exp_tree,
    build_ln_from_subtree,
    build_ln_tree,
    build_master_tree,
    build_multiply_tree,
    build_negate_tree,
    build_subtract_tree,
    build_zero_tree,
    verify_eml_identity,
)
from eml_mcp.similarity import tree_edit_distance
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import EMLNode, NodeType, const, eml_node, extract_real, var

__all__ = [
    "DTYPE",
    "EXP_CLAMP_MAX",
    "EXP_CLAMP_MIN",
    "eml",
    "eml_array",
    "EMLNode",
    "NodeType",
    "const",
    "eml_node",
    "extract_real",
    "var",
    "EMLFormulaDB",
    "SEED_FORMULAS",
    "build_add_tree",
    "build_e_tree",
    "build_exp_from_subtree",
    "build_exp_tree",
    "build_ln_from_subtree",
    "build_ln_tree",
    "build_master_tree",
    "build_multiply_tree",
    "build_negate_tree",
    "build_subtract_tree",
    "build_zero_tree",
    "verify_eml_identity",
    "simplify_tree",
    "tree_edit_distance",
]
