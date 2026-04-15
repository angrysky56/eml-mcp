"""
EML MCP Server
===============

A Model Context Protocol server exposing the EML (Exp-Minus-Log) operator
and binary tree structures for continuous mathematics.

Based on Odrzywołek (2026): "All elementary functions from a single operator"
https://arxiv.org/html/2603.21852v2

Tools:
    eml_evaluate     — Evaluate the EML operator on inputs
    eml_compile      — Convert elementary expressions to pure EML form
    eml_tree_info    — Inspect known EML formula trees
    eml_verify       — Verify an EML tree against a reference function
    eml_master_tree  — Build parameterized master formula for symbolic regression
    eml_list_formulas — List all known EML formula decompositions
"""

from __future__ import annotations

import json
import logging
import math
import sys
from typing import Any

from fastmcp import FastMCP

from eml_mcp.primitives import DTYPE, eml
from eml_mcp.registry import (
    KNOWN_FORMULAS,
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
from eml_mcp.trees import EMLNode, NodeType, const, eml_node, extract_real, var

# Logging to stderr for MCP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("eml-mcp")


# ==================== MCP Tools ====================


@mcp.tool(
    name="eml_evaluate",
    annotations={
        "title": "Evaluate EML Operator",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_evaluate(x: float, y: float):
    """Evaluate the EML (Exp-Minus-Log) Sheffer operator.

    Computes eml(x, y) = exp(x) - ln(y).

    This single binary operator, paired with constant 1, generates
    all standard elementary functions — the continuous analogue
    of the NAND gate for Boolean logic.

    Args:
        x: First argument (feeds into exp).
        y: Second argument (feeds into ln).

    Returns:
        dict with real/imaginary parts, explanation, and formula.
    """
    try:
        result = eml(complex(x), complex(y))
        real_result = extract_real(result)

        return {
            "result": (
                real_result
                if isinstance(real_result, float)
                else {"real": result.real, "imag": result.imag}
            ),
            "formula": f"eml({x}, {y}) = exp({x}) - ln({y})",
            "components": {
                "exp_x": extract_real(
                    complex(math.e**x) if abs(x) < 700 else complex(float("inf"))
                ),
                "ln_y": extract_real(complex(math.log(y)) if y > 0 else {"requires_complex": True}),
            },
            "explanation": (
                (
                    f"exp({x}) = {math.exp(x):.6g}, "
                    f"ln({y}) = {math.log(y):.6g}, "
                    f"result = {real_result}"
                )
                if y > 0 and abs(x) < 700
                else f"Result computed in complex domain: {result}"
            ),
        }
    except Exception as e:
        logger.error(f"Error evaluating EML: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool(
    name="eml_list_formulas",
    annotations={
        "title": "List Known EML Formulas",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_list_formulas():
    """List all known EML formula decompositions.

    Shows how standard mathematical functions and constants are
    expressed as pure EML trees (binary trees of identical nodes).

    Returns:
        dict with formula names, descriptions, depths, and leaf counts.
    """
    formulas = {}
    for name, info in KNOWN_FORMULAS.items():
        tree = info["builder"]()
        formulas[name] = {
            "description": info["description"],
            "depth": info["depth"],
            "K": info["K"],
            "leaf_count": tree.leaf_count,
            "variables": info["variables"],
            "expression": tree.to_expression(),
            "rpn": " ".join(tree.to_rpn()),
        }
        if "note" in info:
            formulas[name]["note"] = info["note"]
    return {
        "formulas": formulas,
        "total": len(formulas),
        "grammar": "S → 1 | eml(S, S)",
        "reference": "Odrzywołek (2026), arXiv:2603.21852v2",
    }


@mcp.tool(
    name="eml_tree_info",
    annotations={
        "title": "Inspect EML Formula Tree",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_tree_info(
    formula_name: str,
    evaluate_at: float | None = None,
):
    """Inspect a known EML formula tree and optionally evaluate it.

    Shows the full tree structure, RPN code, and expression for
    a named elementary function decomposed into pure EML form.

    Args:
        formula_name: Name of the formula (e.g., 'exp', 'ln', 'e', 'zero').
        evaluate_at: Optional value to evaluate the tree at.

    Returns:
        dict with tree structure, expression, RPN, depth, and optional result.
    """
    if formula_name not in KNOWN_FORMULAS:
        available = list(KNOWN_FORMULAS.keys())
        return {
            "status": "error",
            "message": f"Unknown formula '{formula_name}'",
            "available": available,
        }

    info = KNOWN_FORMULAS[formula_name]
    tree = info["builder"]()

    result: dict[str, Any] = {
        "name": formula_name,
        "description": info["description"],
        "expression": tree.to_expression(),
        "rpn": " ".join(tree.to_rpn()),
        "depth": tree.depth,
        "K": tree.node_count,
        "leaf_count": tree.leaf_count,
        "node_count": tree.node_count,
        "tree": tree.to_dict(),
    }
    if "note" in info:
        result["note"] = info["note"]

    if evaluate_at is not None and info["variables"]:
        variables = {info["variables"][0]: complex(evaluate_at)}
        try:
            val = tree.evaluate(variables)
            result["evaluation"] = {
                "input": evaluate_at,
                "output": extract_real(val),
            }
        except Exception as e:
            result["evaluation"] = {"error": str(e)}
    elif evaluate_at is not None and not info["variables"]:
        # It's a constant, just evaluate
        try:
            val = tree.evaluate()
            result["evaluation"] = {"output": extract_real(val)}
        except Exception as e:
            result["evaluation"] = {"error": str(e)}

    return result


@mcp.tool(
    name="eml_compile",
    annotations={
        "title": "Compile Expression to EML",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_compile(expression: str):
    """Compile an elementary expression to pure EML form.

    Converts standard mathematical expressions into nested EML
    operator trees. Currently supports: exp(x), ln(x), e, 0,
    and compositions thereof.

    Args:
        expression: Mathematical expression string (e.g., 'exp(x)',
                    'ln(x)', 'e', '0', 'exp(exp(x))').

    Returns:
        dict with the EML tree, expression, RPN code, and complexity.
    """
    # Normalize
    expr = expression.strip().lower()

    # Direct formula lookup
    if expr in KNOWN_FORMULAS:
        tree = KNOWN_FORMULAS[expr]["builder"]()
        return {
            "input": expression,
            "eml_expression": tree.to_expression(),
            "rpn": " ".join(tree.to_rpn()),
            "depth": tree.depth,
            "K": tree.node_count,
            "leaf_count": tree.leaf_count,
            "tree": tree.to_dict(),
        }

    # Handle common aliases
    alias_map = {
        "exp(x)": "exp",
        "e^x": "exp",
        "ln(x)": "ln",
        "log(x)": "ln",
        "euler": "e",
        "0": "zero",
        "x-y": "subtract",
        "x - y": "subtract",
        "-x": "negate",
        "neg(x)": "negate",
        "x+y": "add",
        "x + y": "add",
        "x*y": "multiply",
        "x × y": "multiply",
        "x * y": "multiply",
    }
    if expr in alias_map:
        key = alias_map[expr]
        tree = KNOWN_FORMULAS[key]["builder"]()
        return {
            "input": expression,
            "eml_expression": tree.to_expression(),
            "rpn": " ".join(tree.to_rpn()),
            "depth": tree.depth,
            "K": tree.node_count,
            "leaf_count": tree.leaf_count,
            "tree": tree.to_dict(),
        }

    # Handle compositions: exp(exp(x)), ln(ln(x)), exp(ln(x)), ln(exp(x))
    if expr == "exp(exp(x))":
        inner = build_exp_tree()
        tree = build_exp_from_subtree(inner)
        return _compile_result(expression, tree)
    elif expr == "ln(ln(x))":
        inner = build_ln_tree()
        tree = build_ln_from_subtree(inner)
        return _compile_result(expression, tree)
    elif expr in ("exp(ln(x))", "x"):
        # exp(ln(x)) = x (identity)
        inner = build_ln_tree()
        tree = build_exp_from_subtree(inner)
        return _compile_result(expression, tree)
    elif expr == "ln(exp(x))":
        inner = build_exp_tree()
        tree = build_ln_from_subtree(inner)
        return _compile_result(expression, tree)

    return {
        "status": "error",
        "input": expression,
        "message": (
            f"Cannot compile '{expression}' yet. "
            f"Supported: {list(KNOWN_FORMULAS.keys())} "
            f"plus compositions like exp(exp(x)), ln(ln(x))."
        ),
        "note": (
            "Full compiler requires the bootstrapping chain from "
            "Odrzywołek's VerifyBaseSet procedure. The complete chain "
            "builds ~36 primitives iteratively from EML + 1."
        ),
    }


def _compile_result(expression: str, tree: EMLNode):
    """Helper to format compile results."""
    return {
        "input": expression,
        "eml_expression": tree.to_expression(),
        "rpn": " ".join(tree.to_rpn()),
        "depth": tree.depth,
        "K": tree.node_count,
        "leaf_count": tree.leaf_count,
        "tree": tree.to_dict(),
    }


@mcp.tool(
    name="eml_verify",
    annotations={
        "title": "Verify EML Identity",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_verify(
    formula_name: str,
    tolerance: float = 1e-10,
):
    """Verify a known EML formula against its reference function.

    Uses algebraically independent transcendental test points
    (Euler-Mascheroni, Glaisher-Kinkelin constants) following
    the paper's numeric bootstrapping verification approach.

    Under the Schanuel conjecture, coincidental equality between
    such expressions is vanishingly unlikely.

    Args:
        formula_name: Name of the formula to verify (e.g., 'exp', 'ln', 'e').
        tolerance: Maximum acceptable absolute error (default: 1e-10).

    Returns:
        dict with pass/fail status, max error, and per-point results.
    """
    if formula_name not in KNOWN_FORMULAS:
        return {
            "status": "error",
            "message": f"Unknown formula '{formula_name}'",
            "available": list(KNOWN_FORMULAS.keys()),
        }

    info = KNOWN_FORMULAS[formula_name]
    tree = info["builder"]()

    # Define reference functions
    ref_functions = {
        "exp": lambda z: complex(math.e**z.real) if abs(z.real) < 700 else complex(float("inf")),
        "e": lambda _: complex(math.e),
        "ln": lambda z: complex(math.log(z.real)) if z.real > 0 else complex(float("nan")),
        "zero": lambda _: complex(0.0),
        "subtract": lambda x, y: complex(x - y),
        "negate": lambda z: complex(-z),
        "add": lambda x, y: complex(x + y),
        "multiply": lambda x, y: complex(x * y),
    }

    if formula_name not in ref_functions:
        return {
            "status": "error",
            "message": f"No reference function defined for '{formula_name}'",
        }

    ref_fn = ref_functions[formula_name]
    variables = info.get("variables", [])

    # Handle multivariate formulas (two-variable: x, y)
    if len(variables) == 2:
        # Paired test points for binary operations
        test_pairs = [
            (complex(2.5), complex(1.3)),
            (complex(0.5772156649015329), complex(1.6180339887498949)),
            (complex(1.4142135623730951), complex(1.2824271291006226)),
            (complex(3.0), complex(0.7)),
            (complex(0.1), complex(2.0)),
        ]
        results = []
        max_error = 0.0
        for xv, yv in test_pairs:
            try:
                var_bindings = {"x": xv, "y": yv}
                tree_val = tree.evaluate(var_bindings)
                ref_val = complex(ref_fn(xv, yv))
                error = abs(tree_val - ref_val)
                max_error = max(max_error, error)
                results.append(
                    {
                        "input": {"x": extract_real(xv), "y": extract_real(yv)},
                        "tree_output": extract_real(tree_val),
                        "reference": extract_real(ref_val),
                        "error": error,
                        "pass": error < tolerance,
                    }
                )
            except (ValueError, ZeroDivisionError, OverflowError) as e:
                results.append(
                    {
                        "input": {"x": extract_real(xv), "y": extract_real(yv)},
                        "error": str(e),
                        "pass": False,
                    }
                )
        passed = all(r["pass"] for r in results)
        result = {
            "passed": passed,
            "max_error": max_error,
            "tolerance": tolerance,
            "n_tests": len(results),
            "details": results,
        }
    else:
        # Univariate or constant — use existing verify_eml_identity
        result = verify_eml_identity(
            tree=tree,
            reference_fn=ref_fn,
            tolerance=tolerance,
        )

    result["formula_name"] = formula_name
    result["eml_expression"] = tree.to_expression()
    return result


@mcp.tool(
    name="eml_master_tree",
    annotations={
        "title": "Build Master Formula Tree",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_master_tree(
    depth: int = 2,
    variables: list[str] | None = None,
):
    """Build a parameterized master formula tree for symbolic regression.

    The master formula at level n contains ALL possible elementary
    formulas up to that depth. Each leaf input is parameterized as
    α_i + β_i·x + γ_i·f, where weights are optimized via gradient
    descent (Adam) and then "snapped" to exact 0/1 values.

    For the univariate case, the level-n master formula has
    5×2^n - 6 parameters.

    Args:
        depth: Tree depth (1-6 recommended). 2^n leaves.
        variables: Input variable names (default: ["x"]).

    Returns:
        dict describing tree structure, parameter count, and usage.
    """
    if depth < 1 or depth > 8:
        return {
            "status": "error",
            "message": "Depth must be between 1 and 8",
        }

    result = build_master_tree(depth, variables)

    # Add recovery statistics from the paper
    recovery_rates = {
        1: "trivial (only exp and e)",
        2: "100% blind recovery",
        3: "~25% blind recovery",
        4: "~25% blind recovery",
        5: "<1% blind recovery (100% from perturbed correct weights)",
        6: "0% blind recovery (100% from perturbed correct weights)",
    }
    result["recovery_rate"] = recovery_rates.get(depth, "unknown")
    result["training_notes"] = (
        "Use torch.complex128 dtype. Clamp exp arguments to [-700, 700]. "
        "Multi-stage: Adam training → hardening phase → weight snap to 0/1. "
        "When successful, MSE drops to ~1e-32 (machine epsilon squared)."
    )
    return result


# ==================== Resources ====================


@mcp.resource("eml://grammar")
def get_eml_grammar() -> str:
    """The EML context-free grammar and key identities."""
    return """
# EML Grammar

S → 1 | eml(S, S)

This trivial grammar generates ALL elementary function expressions
as binary trees of identical EML nodes.

## Key Identities
- e = eml(1, 1)
- exp(x) = eml(x, 1)
- ln(x) = eml(1, eml(eml(1, x), 1))

## The EML Operator
eml(x, y) = exp(x) - ln(y)

## Cousins
- EDL: edl(x, y) = exp(x) / ln(y)  [constant: e]
- -EML: ln(x) - exp(y)              [constant: -∞]

## Reference
Odrzywołek (2026), arXiv:2603.21852v2
""".strip()


@mcp.resource("eml://complexity-table")
def get_complexity_table() -> str:
    """Complexity of elementary functions in EML representation."""
    return """
# EML Complexity Table (from Odrzywołek 2026, Table 4)

## Constants
| Constant | Compiler K | Direct Search K |
|----------|-----------|-----------------|
| 1        | 1         | 1               |
| 0        | 7         | 7               |
| e        | 3         | 3               |
| -1       | 17        | 15              |
| 2        | 27        | 19              |
| π        | 193       | >53             |
| i        | 131       | >55             |

## Functions
| Function | Compiler K | Direct Search K |
|----------|-----------|-----------------|
| exp(x)   | 3         | 3               |
| ln(x)    | 7         | 7               |
| -x       | 57        | 15              |
| 1/x      | 65        | 15              |
| x²       | 75        | 17              |
| √x       | 139       | ≥35             |

## Operators
| Operator | Compiler K | Direct Search K |
|----------|-----------|-----------------|
| x - y    | 83        | 11              |
| x + y    | 27        | 19              |
| x × y    | 41        | 17              |
| x / y    | 105       | 17              |
| x^y      | 49        | 25              |
""".strip()
