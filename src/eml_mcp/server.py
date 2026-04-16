"""
EML MCP Server
===============

A Model Context Protocol server exposing the EML (Exp-Minus-Log) operator
and binary tree structures for continuous mathematics.

Based on Odrzywołek (2026): "All elementary functions from a single operator"
https://arxiv.org/html/2603.21852v2

Tools:
    eml_evaluate            — Evaluate the EML operator on inputs
    eml_list_formulas       — List the live formula catalog from SQLite
    eml_tree_info           — Inspect a known EML formula tree
    eml_compile             — Compile an elementary expression to pure EML
    eml_verify              — Verify an EML tree against a reference function
    eml_master_tree         — Build a parameterized master formula for SR
    eml_symbolic_regression — Gradient-based SR (PyTorch, Adam)
    eml_discover            — Evolutionary search for a target behavior
    eml_simplify            — Reduce redundant compositions (exp(ln(x))→x)
    eml_similarity          — Zhang-Shasha tree edit distance between formulas

Resources:
    eml://grammar           — The EML context-free grammar and key identities
    eml://formulas          — Live formula catalog (JSON, from SQLite)
    eml://complexity-table  — Complexity table from Odrzywolek (2026)
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from typing import Any

from fastmcp import FastMCP

from eml_mcp.compiler import EMLCompiler
from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine, safe_eval_math
from eml_mcp.primitives import eml
from eml_mcp.registry import (
    build_master_tree,
    verify_eml_identity,
)
from eml_mcp.similarity import tree_edit_distance
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import EMLNode, extract_real

# Optional regression support (requires torch)
try:
    import torch  # noqa: F401

    from eml_mcp.regression import mor_symbolic_regression_loop, train_eml_tree

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Logging to stderr for MCP
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("eml-mcp")


class DBInstance:
    """Holding class for the database singleton."""

    instance: EMLFormulaDB | None = None


def get_db() -> EMLFormulaDB:
    """Singleton getter for the formula database."""
    if DBInstance.instance is None:
        db_path = os.environ.get("EML_DB_PATH", "eml_formulas.db")
        DBInstance.instance = EMLFormulaDB(db_path)
    return DBInstance.instance


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
    except (OverflowError, ValueError, ZeroDivisionError, ArithmeticError) as e:
        logger.error("EML evaluate failed for inputs x=%s, y=%s: %s", x, y, e, exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool(
    name="eml_discover",
    annotations={
        "title": "Discover EML Formula",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
def eml_discover(
    target_expression: str,
    iterations: int = 100,
    top_n: int = 3,
    tolerance: float = 1e-5,
    stagnation_limit: int = 100,
    workers: int = 1,
):
    """Search for an EML formula matching a target behavior.

    Implements Targeted Discovery with Open-Ended Proximity.
    If an exact match is not found, the system returns the top N
    "nearby" formulas based on Mean Squared Error (MSE).

    Args:
        target_expression: Python expression for target function (e.g., 'x**2', 'math.sin(x)').
        iterations: Number of composition iterations to run (default: 100).
        top_n: Number of nearby discoveries to return if no exact match (default: 3).
        tolerance: Distance threshold for considering a match "exact" (default: 1e-5).
        stagnation_limit: Number of iterations without improvement before bailing (default: 100).
        workers: Number of parallel workers to use (default: 1).

    Returns:
        dict with exact_match and nearby_discoveries.
    """

    db = get_db()
    engine = DiscoveryEngine(db)

    try:
        results = engine.find_target(
            target=target_expression,
            max_iterations=iterations,
            top_n=top_n,
            tolerance=tolerance,
            stagnation_limit=stagnation_limit,
            workers=workers,
        )

        # Structure response for clarity
        if results.get("error"):
            return results

        response = {
            "status": "success",
            "iterations": iterations,
            "exact_match": None,
            "nearby_discoveries": [],
        }

        exact_match = results.get("exact_match")
        if isinstance(exact_match, dict):
            item = {
                "name": exact_match["name"],
                "expression": exact_match["expression"],
                "mse": exact_match["mse"],
                "k": exact_match.get("k", 0),
                "details": exact_match["details"],
            }
            if "ted" in exact_match:
                item["structural_distance"] = exact_match["ted"]
            if "reused_existing" in exact_match:
                item["reused_existing"] = exact_match["reused_existing"]
            response["exact_match"] = item

        # Sort is now handled by DiscoveryEngine.find_target, but we ensure output format
        for near in results.get("nearby_discoveries", []):
            item = {
                "name": near["name"],
                "expression": near["expression"],
                "mse": near["mse"],
                "k": near.get("k", 0),
                "details": near["details"],
            }
            if "ted" in near:
                item["structural_distance"] = near["ted"]
            response["nearby_discoveries"].append(item)

        return response

    except (ValueError, TypeError, RuntimeError, AttributeError, KeyError) as e:
        logger.error(
            "Discovery failed for expression %r: %s",
            target_expression,
            e,
            exc_info=True,
        )
        return {"status": "error", "message": str(e), "error_type": type(e).__name__}


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

    db = get_db()
    rows = db.list_formulas()
    formulas = {}
    for row in rows:
        formulas[row["name"]] = {
            "description": row["description"],
            "depth": row["depth"],
            "K": row["k"],
            "leaf_count": row["leaf_count"],
            "variables": json.loads(row["variables"]),
            "expression": row["expression"],
            "rpn": row["rpn"],
        }
        if row.get("note"):
            formulas[row["name"]]["note"] = row["note"]
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

    db = get_db()
    row = db.get_formula(formula_name)
    if row is None:
        available = [r["name"] for r in db.list_formulas()]
        return {
            "status": "error",
            "message": f"Unknown formula '{formula_name}'",
            "available": available,
        }

    tree_dict = json.loads(row["tree_json"])
    tree = EMLNode.from_dict(tree_dict)
    variables = json.loads(row["variables"])

    result: dict[str, Any] = {
        "name": formula_name,
        "description": row["description"],
        "expression": row["expression"],
        "rpn": row["rpn"],
        "depth": row["depth"],
        "K": row["k"],
        "leaf_count": row["leaf_count"],
        "node_count": row["k"],
        "tree": tree_dict,
    }
    if row.get("note"):
        result["note"] = row["note"]

    if evaluate_at is not None and variables:
        var_bindings = {variables[0]: complex(evaluate_at)}
        try:
            val = tree.evaluate(var_bindings)
            result["evaluation"] = {
                "input": evaluate_at,
                "output": extract_real(val),
            }
        except (ValueError, OverflowError, ArithmeticError) as e:
            logger.warning(
                "Tree evaluation failed for formula=%r at x=%s: %s",
                formula_name,
                evaluate_at,
                e,
                exc_info=True,
            )
            result["evaluation"] = {"error": str(e)}
    elif evaluate_at is not None and not variables:
        # It's a constant, just evaluate
        try:
            val = tree.evaluate()
            result["evaluation"] = {"output": extract_real(val)}
        except (ValueError, OverflowError, ArithmeticError) as e:
            logger.warning(
                "Constant evaluation failed for formula=%r: %s",
                formula_name,
                e,
                exc_info=True,
            )
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

    expr = expression.strip().lower()
    db = get_db()

    # Direct formula lookup
    row = db.get_formula(expr)
    if row:
        return {
            "input": expression,
            "eml_expression": row["expression"],
            "rpn": row["rpn"],
            "depth": row["depth"],
            "K": row["k"],
            "leaf_count": row["leaf_count"],
            "tree": json.loads(row["tree_json"]),
        }

    # AST-based recursive compiler
    compiler = EMLCompiler(db)
    try:
        tree = compiler.compile(expr)
        return _compile_result(expression, tree)
    except ValueError as e:
        return {
            "status": "error",
            "input": expression,
            "message": str(e),
            "note": (
                "Full compiler requires the bootstrapping chain from "
                "Odrzywolek's VerifyBaseSet procedure. Ensure the operators or functions you use "
                "are known to the system via the Discovery Engine."
            ),
        }


def _compile_result(expression: str, tree: EMLNode):
    """Format compile results into a dictionary."""
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
        "readOnlyHint": False,
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
    following the paper's numeric bootstrapping verification approach.

    Args:
        formula_name: Name of the formula to verify (e.g., 'exp', 'ln', 'e').
        tolerance: Maximum acceptable absolute error (default: 1e-10).

    Returns:
        dict with pass/fail status, max error, and per-point results.
    """

    db = get_db()
    row = db.get_formula(formula_name)
    if row is None:
        return {
            "status": "error",
            "message": f"Unknown formula '{formula_name}'",
            "available": [f["name"] for f in db.list_formulas()],
        }

    tree = EMLNode.from_dict(json.loads(row["tree_json"]))

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
    variables = json.loads(row["variables"])

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
                # Cast to native Python float — see registry.verify_eml_identity
                error = float(abs(tree_val - ref_val))
                max_error = max(max_error, error)
                results.append(
                    {
                        "input": {"x": extract_real(xv), "y": extract_real(yv)},
                        "tree_output": extract_real(tree_val),
                        "reference": extract_real(ref_val),
                        "error": error,
                        "pass": bool(error < tolerance),
                    }
                )
            except (ValueError, ZeroDivisionError, OverflowError) as e:
                results.append(
                    {
                        "input": {"x": extract_real(xv), "y": extract_real(yv)},
                        "error": str(e),
                        # trunk-ignore(bandit/B105)
                        "pass": False,
                    }
                )
        passed = bool(all(r["pass"] for r in results))
        result = {
            "passed": passed,
            "max_error": float(max_error),
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

    # Persist to DB
    db.add_verification(
        formula_name=formula_name,
        passed=result["passed"],
        max_error=result["max_error"],
        tolerance=tolerance,
        n_tests=result["n_tests"],
        details=result["details"],
    )

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
        "Use torch.complex128 dtype. Clamp exp arguments to [-100, 100]. "
        "Multi-stage: Adam training -> weight snap to 0/1. "
        "When successful, MSE drops to ~1e-32 (machine epsilon squared)."
    )
    return result


@mcp.tool(
    name="eml_symbolic_regression",
    annotations={
        "title": "EML Symbolic Regression",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
def eml_symbolic_regression(
    target_expression: str,
    depth: int = 5,
    epochs: int = 1000,
    lr: float = 0.01,
):
    """Perform gradient-based symbolic regression to recover an EML formula.

    This tool uses PyTorch to optimize a Mixture-of-Recursions (MoR) network
    against numerical data generated from the target expression. It attempts
    to find the exact EML identity by learning the optimal discrete structural
    weights and iteratively applying a shared structural block.

    Args:
        target_expression: Python expression for target function (e.g., 'math.exp(x)').
        depth: Maximum search steps/recursions for MoR (1-5).
        epochs: Number of training epochs per step (default: 1000).
        lr: Learning rate (default: 0.01).

    Returns:
        Recovery results including the discovered formula and loss statistics.
    """

    if not HAS_TORCH:
        return {
            "status": "error",
            "message": "PyTorch is not installed. Install with 'uv pip install -e .[sr]'",
        }

    if depth < 1 or depth > 10:
        return {"status": "error", "message": "Depth must be between 1 and 10."}

    try:
        # Generate training data locally
        x_vals = torch.linspace(0.1, 5.0, 50, dtype=torch.complex128)
        target_data = {"x": x_vals}

        # Evaluate target_expression
        y_targets = []
        for v in x_vals:
            y_targets.append(complex(safe_eval_math(target_expression, complex(v))))
        y_tensor = torch.tensor(y_targets, dtype=torch.complex128)

        # Train
        discovered, mse = mor_symbolic_regression_loop(
            target_expression=target_expression,
            target_data=target_data,
            target_values=y_tensor,
            max_steps=depth,
            epochs_per_step=epochs,
            lr=lr,
        )

        return {
            "status": "success",
            "discovered_formula": discovered,
            "max_steps_allowed": depth,
            "target": target_expression,
            "final_mse": mse,
            "training_summary": (
                f"Optimized MoR iterative loop (max_steps={depth}) for {epochs} epochs/step. "
                f"Obtained formula: {discovered} with MSE {mse:.4e}"
            ),
        }
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error("Symbolic regression failed: %s", e, exc_info=True)
        return {"status": "error", "message": f"Training error: {e}"}
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Unexpected system error during symbolic regression: %s", e, exc_info=True)
        return {"status": "error", "message": f"Internal system failure: {e}"}


@mcp.tool(
    name="eml_simplify",
    annotations={
        "title": "Simplify EML Formula",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_simplify(expression: str):
    """Simplify an EML formula by reducing redundant compositions.

    Applies identity rules like exp(ln(x)) -> x and performs constant folding.

    Args:
        expression: EML formula string or known formula name.

    Returns:
        dict with simplified expression, RPN, and complexity reduction stats.
    """
    db = get_db()
    # 1. Try to get as known formula
    row = db.get_formula(expression)
    if row:
        tree = EMLNode.from_dict(json.loads(row["tree_json"]))
    else:
        # 2. Try to compile if it looks like math
        try:
            compiler = EMLCompiler(db)
            tree = compiler.compile(expression)
        except (ValueError, SyntaxError) as e:
            # 3. Last resort: direct tree rebuild from expression if it uses 'eml('
            logger.debug("Simplification fallback for %s: %s", expression, e)
            return {
                "status": "error",
                "message": f"Could not parse expression '{expression}'",
            }

    old_k = tree.node_count
    simplified = simplify_tree(tree)
    new_k = simplified.node_count

    return {
        "original_expression": tree.to_expression(),
        "simplified_expression": simplified.to_expression(),
        "original_k": old_k,
        "simplified_k": new_k,
        "reduction": f"{((old_k - new_k) / old_k * 100):.1f}%" if old_k > 0 else "0%",
        "rpn": " ".join(simplified.to_rpn()),
        "tree": simplified.to_dict(),
    }


@mcp.tool(
    name="eml_similarity",
    annotations={
        "title": "EML Tree Similarity",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def eml_similarity(formula_a: str, formula_b: str):
    """Compute structural similarity between two EML formulas.

    Uses Zhang-Shasha Tree Edit Distance (TED). A distance of 0 means
    the trees are structurally identical.

    Args:
        formula_a: First formula name or EML expression.
        formula_b: Second formula name or EML expression.

    Returns:
        dict with tree edit distance and complexity metrics.
    """
    db = get_db()

    def get_tree(expr):
        row = db.get_formula(expr)
        if row:
            return EMLNode.from_dict(json.loads(row["tree_json"]))
        compiler = EMLCompiler(db)
        return compiler.compile(expr)

    try:
        tree_a = get_tree(formula_a)
        tree_b = get_tree(formula_b)
    except (ValueError, TypeError, NameError, SyntaxError) as e:
        logger.error("Similarity computation failed: %s", e)
        return {"status": "error", "message": str(e)}

    distance = tree_edit_distance(tree_a, tree_b)

    return {
        "formula_a": tree_a.to_expression(),
        "formula_b": tree_b.to_expression(),
        "tree_edit_distance": distance,
        "k_a": tree_a.node_count,
        "k_b": tree_b.node_count,
        "max_possible_distance": tree_a.node_count + tree_b.node_count,
        "similarity_score": max(0.0, 1.0 - (distance / (tree_a.node_count + tree_b.node_count))),
    }


@mcp.resource("eml://grammar")
def get_eml_grammar() -> str:
    """Return the EML context-free grammar and key identities."""
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


@mcp.resource("eml://formulas")
def get_formula_catalog() -> str:
    """Return the live formula catalog from the SQLite database as JSON.

    This is the authoritative source for what the server currently knows.
    Unlike the static grammar resource, this reflects every seeded, compiled,
    and discovered formula persisted to eml_formulas.db.
    """
    db = get_db()
    rows = db.list_formulas()
    formulas = []
    for row in rows:
        entry = {
            "name": row["name"],
            "description": row["description"],
            "expression": row["expression"],
            "rpn": row["rpn"],
            "depth": row["depth"],
            "K": row["k"],
            "leaf_count": row["leaf_count"],
            "variables": json.loads(row["variables"]),
        }
        if row.get("note"):
            entry["note"] = row["note"]
        if row.get("created_at"):
            entry["created_at"] = row["created_at"]
        formulas.append(entry)

    # Partition seeds vs discoveries for easier consumption
    seeds = [f for f in formulas if not f["name"].startswith("discovered")]
    discoveries = [f for f in formulas if f["name"].startswith("discovered")]

    return json.dumps(
        {
            "total": len(formulas),
            "seed_count": len(seeds),
            "discovered_count": len(discoveries),
            "grammar": "S → 1 | eml(S, S)",
            "reference": "Odrzywołek (2026), arXiv:2603.21852v2",
            "seeds": seeds,
            "discoveries": discoveries,
        },
        indent=2,
        ensure_ascii=False,
    )


@mcp.resource("eml://complexity-table")
def get_complexity_table() -> str:
    """Complexity of elementary functions in EML representation."""
    return """
# EML Complexity Table (from Odrzywolek 2026, Table 4)

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
