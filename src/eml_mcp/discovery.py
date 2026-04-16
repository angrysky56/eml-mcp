"""
EML Discovery Engine
====================

Explores the EML space to discover novel stable formulas using a novelty search approach.
Supports targeted formula discovery by functional proximity (MSE).
"""

import ast
import cmath
import json
import logging
import math
import operator
import secrets
import sqlite3
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from eml_mcp.compiler import EMLCompiler
from eml_mcp.database import EMLFormulaDB, deserialize_signature
from eml_mcp.primitives import TEST_POINTS
from eml_mcp.similarity import tree_edit_distance
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import EMLNode, var

logger = logging.getLogger(__name__)


def safe_eval_math(expression: str, x: complex) -> complex:
    """Safely evaluate a mathematical expression using AST walking.

    Acts as a 'Feature Filter' to ensure the target expression is within
    the engine's mathematical domain.
    """
    # Explicit whitelist of allowed operations
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: lambda v: v,
    }

    # Highly inclusive library of math/cmath primitives
    functions = {
        # Exponential/Log
        "exp": cmath.exp,
        "log": cmath.log,
        "ln": cmath.log,
        "log10": cmath.log10,
        "sqrt": cmath.sqrt,
        # Trig
        "sin": cmath.sin,
        "cos": cmath.cos,
        "tan": cmath.tan,
        "asin": cmath.asin,
        "acos": cmath.acos,
        "atan": cmath.atan,
        # Hyperbolic
        "sinh": cmath.sinh,
        "cosh": cmath.cosh,
        "tanh": cmath.tanh,
        # Other
        "abs": abs,
        "phase": cmath.phase,
        "polar": cmath.polar,
        "rect": cmath.rect,
    }

    # Allowed variables and constants
    constants = {
        "x": x,
        "pi": math.pi,
        "e": math.e,
        "tau": getattr(math, "tau", 6.283185307179586),
        "j": 1j,
    }

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.BinOp):
            return operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return operators[type(node.op)](_eval(node.operand))
        elif isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name not in functions:
                raise ValueError(
                    f"Function '{name}' is not in the system's supported mathematical domain."
                )
            return functions[name](*[_eval(arg) for arg in node.args])
        elif isinstance(node, ast.Name):
            if node.id in constants:
                return constants[node.id]
            if node.id in ("math", "cmath"):
                return node.id
            raise ValueError(f"Reference '{node.id}' is not a recognized constant or variable.")
        elif isinstance(node, ast.Constant):
            return complex(node.value)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in ("math", "cmath"):
                if node.attr in functions:
                    return functions[node.attr]
                if node.attr in constants:
                    return constants[node.attr]
            raise ValueError(f"Attribute access '.{node.attr}' is restricted.")
        else:
            raise TypeError(
                f"Expression uses '{type(node).__name__}' which is outside the system's focus."
            )

    try:
        tree = ast.parse(expression, mode="eval")
        return complex(_eval(tree))
    except (
        ValueError,
        TypeError,
        SyntaxError,
        KeyError,
        ZeroDivisionError,
        OverflowError,
    ) as e:
        raise ValueError(f"Could not calculate expression: {e}") from e


class DiscoveryEngine:
    """Explores the EML space to discover novel stable formulas."""

    def __init__(
        self,
        db: EMLFormulaDB | None = None,
        test_points: list[complex] | None = None,
    ):
        """Initialize the Discovery Engine.

        Args:
            db: Optional EMLFormulaDB instance.
            test_points: Optional list of complex test points for functional matching.
        """
        self.db = db
        self.test_points = test_points or TEST_POINTS
        # Cache for (name, outputs) to avoid O(N^2) evaluation overhead
        self._formula_cache: list[tuple[str, list[complex]]] = []
        self._cache_synced = False

    def _extract_variables(self, node: EMLNode) -> set[str]:
        """Extract all unique variable names from a tree."""
        if node.node_type == "var":
            return {node.var_name}
        elif node.node_type == "eml":
            return self._extract_variables(node.left) | self._extract_variables(node.right)
        return set()

    def generate_random_composition(
        self, base_formulas: list[dict[str, Any]] | None = None
    ) -> tuple[EMLNode, dict[str, Any]]:
        """Generate a new formula by randomly composing existing ones."""
        formulas = (
            base_formulas
            if base_formulas is not None
            else (self.db.list_formulas() if self.db else [])
        )
        if not formulas:
            raise ValueError("No base formulas available to compose from")

        # Use secrets for RNG to satisfy security linters and ensure high-quality randomness
        base_record = secrets.choice(formulas)
        base_tree = EMLNode.from_dict(json.loads(base_record["tree_json"]))
        base_vars = json.loads(base_record["variables"])

        details = {"base": base_record["name"], "substitutions": {}}

        mappings = {}
        for v in base_vars:
            if secrets.SystemRandom().random() < 0.6:  # 60% chance to substitute
                sub_record = secrets.choice(formulas)
                sub_tree = EMLNode.from_dict(json.loads(sub_record["tree_json"]))
                mappings[v] = sub_tree
                details["substitutions"][v] = sub_record["name"]
            else:
                mappings[v] = var(v)
                details["substitutions"][v] = "identity"

        new_tree = base_tree.substitute(mappings)
        return new_tree, details

    def _eval_tree_safe(self, tree: EMLNode) -> list[complex] | None:
        """Evaluate a tree against test points safely. Returns None if it fails or overflows."""
        outputs = []
        for point in self.test_points:
            try:
                # Supply 1.0 for other potential variables like 'y' during basic check
                val = tree.evaluate({"x": point, "y": complex(1.0)})
                if math.isnan(val.real) or math.isinf(val.real):
                    return None
                outputs.append(val)
            except (ValueError, ZeroDivisionError, OverflowError):
                return None
        return outputs

    def compute_mse(self, outputs: list[complex], targets: list[complex]) -> float:
        """Compute the Mean Squared Error between two arrays of complex values."""
        if not outputs or not targets or len(outputs) != len(targets):
            return float("inf")
        try:
            mse = sum((abs(o - t) ** 2) for o, t in zip(outputs, targets, strict=False)) / len(
                outputs
            )
            return mse
        except OverflowError:
            return float("inf")

    def is_novel_and_stable(
        self, tree: EMLNode, check_outputs: list[complex] | None = None
    ) -> bool:
        """Check if a tree is mathematically stable and produces novel outputs."""
        outputs = check_outputs if check_outputs is not None else self._eval_tree_safe(tree)
        if outputs is None:
            return False

        # Sync cache if not already done
        if not self._cache_synced:
            self._formula_cache = []
            if self.db:
                for f_record in self.db.list_formulas():
                    name = f_record["name"]
                    sig_raw = f_record.get("signature")
                    f_outputs = deserialize_signature(sig_raw)

                    # Fallback if signature missing (transition logic)
                    if f_outputs is None:
                        f_tree = EMLNode.from_dict(json.loads(f_record["tree_json"]))
                        f_outputs = self._eval_tree_safe(f_tree)

                    if f_outputs:
                        self._formula_cache.append((name, f_outputs))
            self._cache_synced = True

        # Verify against all known formulas in cache to ensure novelty
        for _, f_outputs in self._formula_cache:
            mse = self.compute_mse(outputs, f_outputs)
            if mse < 1e-10:
                return False  # Matches an existing formula

        return True

    def explore(self, iterations: int = 100, workers: int = 1) -> list[str]:
        """Run a novelty search to discover new stable formulas.

        Args:
            iterations: Number of discovery iterations to run.
            workers: Number of parallel processes to use (if > 1).

        Returns:
            List of names of newly discovered and persisted formulas.
        """
        if workers > 1:
            return self.explore_parallel(workers=workers, iterations=iterations)

        self._cache_synced = False  # Force refresh at start of run

        discovered = []
        for _ in range(iterations):
            tree, details = self.generate_random_composition()
            # Simplify before checking novelty
            tree = simplify_tree(tree)
            outputs = self._eval_tree_safe(tree)

            # Check stability: result must be finite and not absurdly large
            if not outputs or not all(cmath.isfinite(o) and abs(o) < 1e10 for o in outputs):
                continue

            if tree and self.is_novel_and_stable(tree, check_outputs=outputs):
                used_vars = sorted(list(self._extract_variables(tree)))
                # Use random suffix to avoid collisions in parallel execution
                suffix = secrets.token_hex(3)
                name = f"discovered_{suffix}"
                try:
                    self.db.add_formula(
                        name=name,
                        description="Randomly discovered stable EML composition.",
                        tree=tree,
                        variables=used_vars,
                        note="Novelty Search emergent formula.",
                    )
                    self.db.add_derivation(
                        formula_name=name,
                        parent_a=None,
                        parent_b=None,
                        method="composition",
                        details=details,
                    )
                    self._formula_cache.append((name, outputs))
                    discovered.extend([name])
                except (sqlite3.Error, RuntimeError) as e:
                    # Likely a name collision or DB lock, skip this iteration
                    logger.debug("Discovery collision or DB error: %s", e)
                    continue
        return discovered

    def discover_and_verify(
        self, iterations: int, base_formulas: list[dict[str, Any]] | None = None
    ) -> list[tuple[Any, dict, list[complex]]]:
        """Run discovery loop and return candidates without database side effects.

        Args:
            iterations: Number of iterations for this task.
            base_formulas: Optional list of base formulas to compose from.

        Returns:
            List of (tree, details, outputs) tuples representing potential new formulas.
        """
        candidates = []
        for _ in range(iterations):
            try:
                tree, details = self.generate_random_composition(base_formulas=base_formulas)
                tree = simplify_tree(tree)
                outputs = self._eval_tree_safe(tree)

                if not outputs or not all(cmath.isfinite(o) and abs(o) < 1e10 for o in outputs):
                    continue

                # Initial novelty check against current local state
                if tree and self.is_novel_and_stable(tree, check_outputs=outputs):
                    candidates.append((tree, details, outputs))
            except (ArithmeticError, ValueError, TypeError) as e:
                logger.debug("Work task iteration failed: %s", e)
                continue
        return candidates

    def explore_parallel(self, workers: int = 4, iterations: int = 100) -> list[str]:
        """Explore EML space using multiple processes."""
        chunk_size = max(1, iterations // workers)
        discovered = []

        # Pre-fetch base formulas to avoid DB access in workers
        base_formulas = self.db.list_formulas() if self.db else []

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for _ in range(workers):
                futures.append(
                    executor.submit(
                        _explore_worker_task,
                        chunk_size,
                        self.test_points,
                        base_formulas,
                    )
                )

            for future in as_completed(futures):
                try:
                    candidates = future.result()
                    for tree, details, outputs in candidates:
                        # Re-verify novelty against latest global state in main process
                        if self.is_novel_and_stable(tree, check_outputs=outputs):
                            used_vars = sorted(list(self._extract_variables(tree)))
                            suffix = secrets.token_hex(3)
                            name = f"discovered_{suffix}"
                            self.db.add_formula(
                                name=name,
                                description="Parallel discovered stable formula.",
                                tree=tree,
                                variables=used_vars,
                                note="Novelty Search emergent formula.",
                            )
                            self.db.add_derivation(
                                formula_name=name,
                                parent_a=None,
                                parent_b=None,
                                method="composition",
                                details=details,
                            )
                            self._formula_cache.append((name, outputs))
                            discovered.append(name)
                except (RuntimeError, ValueError) as e:
                    logger.error("Parallel exploration worker failed: %s", e)

        return discovered

    def find_target(
        self,
        target_evaluator: Callable[[complex], complex] | None = None,
        target_expression: str | None = None,
        max_iterations: int = 100,
        top_n: int = 5,
        tolerance: float = 1e-10,
        workers: int = 1,
    ) -> dict[str, Any]:
        """Search for an EML formula matching a target behavior."""
        self._cache_synced = False  # Refresh cache for targeted run
        # 1. Generate target data
        try:
            x_vals = self.test_points
            target_outputs = []

            if target_evaluator:
                for x in x_vals:
                    target_outputs.append(complex(target_evaluator(x)))
            elif target_expression:
                for x in x_vals:
                    val = safe_eval_math(target_expression, x)
                    target_outputs.append(complex(val))
            else:
                return {
                    "status": "error",
                    "message": "Either target_expression or target_evaluator must be provided",
                }
        except (ValueError, TypeError, NameError, SyntaxError) as e:
            return {"status": "error", "message": f"Failed to evaluate target: {e}"}

        # 2. Compile target if possible for structural ranking
        target_tree = None
        if target_expression:
            try:
                compiler = EMLCompiler(self.db)
                target_tree = compiler.compile(target_expression)
                # target_tree = simplify_tree(target_tree) # Optional
            except (ValueError, SyntaxError):
                pass

        best_matches = []

        def record_candidate(name: str, tree: EMLNode, details: str, outputs: list[complex]):
            mse = self.compute_mse(outputs, target_outputs)
            # Remove redundant or identical values
            if any(m["name"] == name for m in best_matches):
                return

            ted = None
            if target_tree:
                try:
                    ted = tree_edit_distance(tree, target_tree)
                except Exception:
                    pass

            item = {
                "name": name,
                "expression": tree.to_expression(),
                "tree": tree,
                "mse": mse,
                "details": details,
            }
            if ted is not None:
                item["ted"] = ted
            best_matches.append(item)

        # 1. Check existing DB formulas
        for f_record in self.db.list_formulas() if self.db else []:
            f_tree = EMLNode.from_dict(json.loads(f_record["tree_json"]))
            f_outputs = self._eval_tree_safe(f_tree)
            if f_outputs is not None:
                record_candidate(f_record["name"], f_tree, "existing DB formula", f_outputs)

        # 2. Explore for targeted generation
        if workers > 1:
            # Reusing existing parallel exploration for discovery phase
            logger.info("Running parallel targeted exploration with %d workers", workers)
            discovered_names = self.explore(iterations=max_iterations, workers=workers)
            for name in discovered_names:
                f_record = self.db.get_formula(name)
                if not f_record:
                    continue
                tree = EMLNode.from_dict(json.loads(f_record["tree_json"]))
                outputs = self._eval_tree_safe(tree)
                if outputs:
                    record_candidate(name, tree, "Parallel discovery", outputs)
        else:
            for _ in range(max_iterations):
                try:
                    tree, details = self.generate_random_composition()
                    tree = simplify_tree(tree)
                    outputs = self._eval_tree_safe(tree)
                    if outputs is None:
                        continue

                    if self.is_novel_and_stable(tree, check_outputs=outputs):
                        used_vars = sorted(list(self._extract_variables(tree)))
                        # Use random suffix to avoid collisions
                        suffix = secrets.token_hex(2)
                        name = f"discovered_target_{suffix}"
                        if self.db:
                            self.db.add_formula(
                                name=name,
                                description="Targeted discovery composition.",
                                tree=tree,
                                variables=used_vars,
                                note="Targeted search formula.",
                            )
                            self.db.add_derivation(
                                formula_name=name,
                                parent_a=None,
                                parent_b=None,
                                method="targeted_composition",
                                details=details,
                            )
                        record_candidate(name, tree, f"Composition: {details}", outputs)
                except (OverflowError, ValueError) as e:
                    logger.debug("Composition failed during discovery: %s", e)

        # Sort by MSE primarily, then TED (if available), then K
        best_matches.sort(
            key=lambda x: (x["mse"], x.get("ted", float("inf")), x["tree"].node_count)
        )

        exact_match = None
        if best_matches and best_matches[0]["mse"] < tolerance:
            exact_match = best_matches[0]

        return {
            "status": "success",
            "exact_match": exact_match,
            "nearby_discoveries": best_matches[:top_n],
        }


def _explore_worker_task(
    iterations: int, test_points: list[complex], base_formulas: list[dict[str, Any]]
) -> list[tuple[Any, dict, list[complex]]]:
    """Worker task for parallel exploration. No database access."""
    # We define a dummy engine without a DB to avoid connection issues
    # but still use its composition logic.
    engine = DiscoveryEngine(db=None, test_points=test_points)  # type: ignore
    return engine.discover_and_verify(iterations, base_formulas=base_formulas)
