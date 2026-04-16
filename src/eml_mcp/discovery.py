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
import random
import secrets
import sqlite3
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

import numpy as np

from eml_mcp.database import EMLFormulaDB, deserialize_signature
from eml_mcp.primitives import TEST_POINTS
from eml_mcp.similarity import tree_edit_distance
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import EMLNode, NodeType, const, var

logger = logging.getLogger(__name__)


def safe_eval_math(expression: str, x: complex, **kwargs: complex) -> complex:
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
        **kwargs,
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
        self.target_expression: str | None = None
        self._evaluate_target_fn: Callable[[complex], complex] | None = None

    def _evaluate_target(self, x: complex) -> complex:
        """Evaluate target behavior at a point."""
        try:
            return self._evaluate_target_fn(x)
        except Exception:
            return complex(float("nan"))

    def _calculate_mse(self, node: EMLNode) -> float:
        """Calculate Mean Squared Error against target points."""
        errors = []
        for p in self.test_points:
            try:
                # Target value
                target_val = self._evaluate_target(p)
                if not np.isfinite(target_val):
                    continue

                # EML value - provide defaults for common variables
                # x is the primary test point
                # y, z are alternative variables that might be in the tree
                val = node.evaluate({"x": p, "y": p * 1.1 + 0.1, "z": p * 0.9 - 0.1})

                if not np.isfinite(val):
                    errors.append(1e6)  # Large penalty for NaN/Inf
                    continue

                diff = target_val - val
                errors.append(np.abs(diff) ** 2)
            except Exception:
                errors.append(1e6)

        if not errors:
            return 1e6

        return float(np.mean(errors))

    def _extract_variables(self, node: EMLNode) -> set[str]:
        """Extract all unique variable names from a tree."""
        variables = set()

        def traverse(n: EMLNode):
            if n.node_type == NodeType.VAR:
                variables.add(n.var_name)
            elif n.node_type == NodeType.EML:
                traverse(n.left)
                if n.right:
                    traverse(n.right)

        traverse(node)
        return variables

    def generate_random_composition(
        self,
        base_formulas: list[dict[str, Any]] | None = None,
        max_complexity: int | None = None,
        max_depth: int = 2,
        _current_depth: int = 0,
    ) -> tuple[EMLNode, dict[str, Any]]:
        """Generate a new formula by randomly composing existing ones.

        Args:
            base_formulas: Optional list of base formulas.
            max_complexity: Optional maximum node count for the resulting tree.
            max_depth: Maximum recursion depth for compositions.
        """

        formulas = (
            base_formulas
            if base_formulas is not None
            else (self.db.list_formulas() if self.db else [])
        )
        if not formulas:
            raise ValueError("No base formulas available to compose from")

        # Defensive: drop any rows missing the fields we rely on below.
        # These *shouldn't* exist given the NOT NULL schema constraints, but
        # transient states (partial writes, sqlite3.Row reuse across cursors)
        # have produced them in practice and crashed the search loop.
        formulas = [
            f
            for f in formulas
            if f.get("name") and f.get("tree_json") and f.get("variables") is not None
        ]
        if not formulas:
            raise ValueError("All candidate formulas were malformed (missing name/tree_json)")

        # Filter by complexity if requested
        if max_complexity is not None:
            formulas = [f for f in formulas if (f.get("k") or 0) <= max_complexity]
            if not formulas:
                # Fallback to absolute basics if nothing fits
                formulas = [
                    f
                    for f in (self.db.list_formulas() if self.db else [])
                    if f.get("name") in ("exp", "ln", "e", "zero")
                ]

        # Weight formulas by inverse complexity to favor simple building blocks.
        # NOTE: earlier code parsed tree_json and looked up a non-existent
        # "node_count" key, which silently made every weight uniform. The `k`
        # column already stores the correct node count; use it directly.
        weights = []
        for f in formulas:
            k = f.get("k") or 1
            is_core = not f["name"].startswith("discovered_")
            weight = (10.0 if is_core else 1.0) / max(k, 1)
            weights.append(weight)

        base_record = random.choices(formulas, weights=weights, k=1)[0]
        base_tree = EMLNode.from_dict(json.loads(base_record["tree_json"]))
        base_vars = json.loads(base_record["variables"])

        details = {"base": base_record["name"], "substitutions": {}}
        mappings = {}

        for v in base_vars:
            # 50% chance to substitute if we haven't reached max depth
            if _current_depth < max_depth and random.random() < 0.5:
                try:
                    sub_tree, sub_details = self.generate_random_composition(
                        base_formulas=formulas,
                        max_complexity=max_complexity,
                        max_depth=max_depth,
                        _current_depth=_current_depth + 1,
                    )
                    # Check complexity limit for substitution
                    if max_complexity is None or (
                        base_tree.node_count + sub_tree.node_count < max_complexity * 2
                    ):
                        mappings[v] = sub_tree
                        details["substitutions"][v] = sub_details
                    else:
                        mappings[v] = var(v)
                        details["substitutions"][v] = "identity"
                except (ValueError, RecursionError):
                    mappings[v] = var(v)
                    details["substitutions"][v] = "identity"
            else:
                mappings[v] = var(v)
                details["substitutions"][v] = "identity"

        new_tree = base_tree.substitute(mappings)
        return new_tree, details

    def _eval_tree_safe(
        self, tree: EMLNode, variables: dict[str, complex] | None = None
    ) -> list[complex] | None:
        """Evaluate a tree against test points safely.

        Args:
            tree: The EMLNode to evaluate.
            variables: Extra variable bindings (e.g. y=0.1).
        """
        outputs = []
        # Use more diverse extra vars to distinguish bivariate better
        extra_vars = variables or {"y": complex(0.42)}
        for point in self.test_points:
            try:
                bindings = {"x": point, **extra_vars}
                val = tree.evaluate(bindings)
                if not cmath.isfinite(val.real) or not cmath.isfinite(val.imag):
                    return None
                if abs(val) > 1e20:  # Sanity bound for stability
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

        # Delegate to the shared signature-match helper
        return self._find_matching_formula_by_outputs(outputs) is None

    def _ensure_cache_synced(self) -> None:
        """Populate the (name, outputs) cache from the DB if not already synced."""
        if self._cache_synced:
            return
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

    def _find_matching_formula_by_outputs(
        self, outputs: list[complex], tolerance: float = 1e-10
    ) -> str | None:
        """Return the name of an existing formula whose signature matches, else None.

        This is the deduplication primitive. Two formulas that produce the same
        outputs on the standard test points are treated as functionally identical
        (under the Schanuel-conjecture-backed transcendental sampling approach).
        """
        self._ensure_cache_synced()
        for name, f_outputs in self._formula_cache:
            if self.compute_mse(outputs, f_outputs) < tolerance:
                return name
        return None

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

    def _mutate_tree(self, tree: EMLNode) -> EMLNode:
        """Apply a random mutation to an EML tree."""

        new_tree = tree.copy()

        # 1. Collect all nodes in the copy for potential mutation
        all_nodes = []

        def collect(n):
            all_nodes.append(n)
            if n.node_type == NodeType.EML:
                if n.left:
                    collect(n.left)
                if n.right:
                    collect(n.right)

        collect(new_tree)

        if not all_nodes:
            return new_tree

        target_node = random.choice(all_nodes)
        mutation_type = random.random()

        if mutation_type < 0.3:  # Point mutation / Leaf swap
            if target_node.node_type == NodeType.VAR:
                target_node.var_name = random.choice(["x", "y"])
            elif target_node.node_type == NodeType.CONST:
                # Toggle between common constants
                vals = [0.0, 1.0, 2.0, math.pi, math.e]
                target_node.value = complex(random.choice(vals))
            else:  # Convert EML to leaf
                leaf = random.choice([var("x"), var("y"), const(1.0)])
                target_node.node_type = leaf.node_type
                target_node.var_name = leaf.var_name
                target_node.value = leaf.value
                target_node.left = None
                target_node.right = None

        elif mutation_type < 0.6:  # Subtree replacement
            try:
                sub, _ = self.generate_random_composition(max_depth=0)
                target_node.node_type = sub.node_type
                target_node.var_name = sub.var_name
                target_node.value = sub.value
                target_node.left = sub.left
                target_node.right = sub.right
            except ValueError:
                pass

        elif mutation_type < 0.8:  # Expansion (wrap in EML)
            old_node = target_node.copy()
            try:
                other, _ = self.generate_random_composition(max_depth=0)
                target_node.node_type = NodeType.EML
                if random.random() < 0.5:
                    target_node.left = old_node
                    target_node.right = other
                else:
                    target_node.left = other
                    target_node.right = old_node
                target_node.var_name = None
                target_node.value = None
            except ValueError:
                pass

        else:  # Shrinkage (unwrap)
            if target_node.node_type == NodeType.EML and target_node.left and target_node.right:
                child = random.choice([target_node.left, target_node.right])
                target_node.node_type = child.node_type
                target_node.var_name = child.var_name
                target_node.value = child.value
                target_node.left = child.left
                target_node.right = child.right

        return new_tree

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
        target: str | Callable[[complex], complex],
        max_iterations: int = 1000,
        tolerance: float = 1e-8,
        top_n: int = 3,
        **_kwargs,
    ) -> dict[str, Any]:
        """
        Search for an EML formula matching a target behavior.
        Uses a combination of bootstrapping, random composition, and mutational search.

        Args:
            target: Python expression string or a callable evaluator.
            max_iterations: Maximum search iterations.
            tolerance: MSE threshold for exact match.
            top_n: Number of nearby candidates to return.
        """
        if isinstance(target, str):
            self.target_expression = target
            self._evaluate_target_fn = lambda x: safe_eval_math(target, x)
        else:
            self.target_expression = "custom_evaluator"
            self._evaluate_target_fn = target

        logger.info("Starting discovery for target: %s", self.target_expression)

        candidates = []

        # 1. Bootstrapping: Seed with compiled target if possible
        if isinstance(target, str):
            try:
                from eml_mcp.compiler import EMLCompiler

                compiler = EMLCompiler()
                compiled_tree = compiler.compile(target)
                if compiled_tree:
                    mse = self._calculate_mse(compiled_tree)
                    candidates.append(
                        {
                            "tree": compiled_tree,
                            "mse": mse,
                            "ted": 0.0,
                            "fitness": 1.0 / (1.0 + mse),
                        }
                    )
                    logger.info("Seeded with compiled tree. Initial MSE: %.2e", mse)
            except Exception as e:
                logger.debug("Compiler seeding failed: %s", e)

        # Seed with existing formulas from DB
        for alias in self.db.list_formulas():
            f = self.db.get_formula(alias["name"])
            tree = EMLNode.from_dict(json.loads(f["tree_json"]))
            mse = self._calculate_mse(tree)
            candidates.append(
                {
                    "tree": tree,
                    "mse": mse,
                    "ted": 99.0,
                    "fitness": 1.0 / (1.0 + mse),
                    "name": alias["name"],
                }
            )

        # Ensure we have some candidates
        if not candidates:
            candidates.append({"tree": var("x"), "mse": 1e6, "ted": 99.0, "fitness": 1e-6})

        # 3. Evolutionary Search Loop
        for i in range(max_iterations):
            # Sort by MSE primarily
            candidates.sort(key=lambda x: x["mse"])
            candidates = candidates[:10]  # Keep top 10 elites

            # Exit if we hit tolerance
            if candidates[0]["mse"] < tolerance:
                logger.info("Exact match found at iteration %d!", i)
                break

            # Logging progress
            if i % 100 == 0:
                logger.info("Iter %d: Best MSE = %.2e", i, candidates[0]["mse"])

            new_candidates = []

            # Select parents weighted by inverse MSE
            weights = [1.0 / (1.0 + c["mse"]) for c in candidates]
            total_w = sum(weights)
            probs = (
                [w / total_w for w in weights]
                if total_w > 0
                else [1.0 / len(candidates)] * len(candidates)
            )

            # Create mutants
            for _ in range(20):  # Lambda = 20
                parent = random.choices(candidates, weights=probs, k=1)[0]
                mutant_tree = self._mutate_tree(parent["tree"].copy())

                # Simplify mutant
                mutant_tree = simplify_tree(mutant_tree)

                mse = self._calculate_mse(mutant_tree)
                new_candidates.append(
                    {
                        "tree": mutant_tree,
                        "mse": mse,
                        "ted": tree_edit_distance(parent["tree"], mutant_tree),
                    }
                )

                # Local hill climbing if mutation was good
                if mse < parent["mse"]:
                    for _ in range(3):  # Small burst of local mutations
                        hc_tree = self._mutate_tree(mutant_tree.copy())
                        hc_tree = simplify_tree(hc_tree)
                        hc_mse = self._calculate_mse(hc_tree)
                        new_candidates.append(
                            {
                                "tree": hc_tree,
                                "mse": hc_mse,
                                "ted": tree_edit_distance(mutant_tree, hc_tree),
                            }
                        )

            candidates.extend(new_candidates)

            # Occasionally add a completely random tree to maintain diversity
            if i % 50 == 0:
                random_tree = self.generate_random_composition(max_complexity=3, max_depth=2)[0]
                candidates.append(
                    {
                        "tree": random_tree,
                        "mse": self._calculate_mse(random_tree),
                        "ted": 99.0,
                    }
                )

        # Final ranking
        # Final ranking
        candidates.sort(key=lambda x: x["mse"])

        # Prepare result with consistent keys to avoid KeyErrors
        result = {
            "exact_match": None,
            "nearby_discoveries": [
                {
                    "name": c.get("name", f"candidate_{idx}"),
                    "expression": str(c["tree"]),
                    "mse": c["mse"],
                    "k": c["tree"].node_count,
                    "details": "Existing Seed" if c.get("name") else "Mutational variant",
                    "ted": c.get("ted"),
                }
                for idx, c in enumerate(candidates[:top_n])
            ],
        }

        # Check if the best candidate is an exact match
        best_overall = candidates[0]
        if best_overall["mse"] < tolerance:
            # check if it was a seeded formula
            if best_overall.get("name"):
                name = best_overall["name"]
                reused = True
            else:
                # Dedup check: signature-match against the existing catalog
                # before minting a new name. Prevents the "12 copies of
                # exp(exp(x))" accumulation bug.
                best_outputs = self._eval_tree_safe(best_overall["tree"])
                existing_name = (
                    self._find_matching_formula_by_outputs(best_outputs)
                    if best_outputs is not None
                    else None
                )
                if existing_name is not None:
                    name = existing_name
                    reused = True
                    logger.info(
                        "Reusing existing formula %r (signature match for target %r)",
                        name,
                        self.target_expression,
                    )
                else:
                    name = f"discovered_{secrets.token_hex(4)}"
                    used_vars = sorted(list(self._extract_variables(best_overall["tree"])))

                    # Add new discovery to DB
                    self.db.add_formula(
                        name=name,
                        description=f"Auto-discovered matching '{self.target_expression}'",
                        tree=best_overall["tree"],
                        variables=used_vars,
                        note=f"Targeted search best MSE: {best_overall['mse']:.2e}",
                    )
                    self.db.add_derivation(
                        formula_name=name,
                        parent_a=None,
                        parent_b=None,
                        method="evolutionary_search",
                        details=f"Target: {self.target_expression}",
                    )
                    # Keep the cache in sync so further searches in this session
                    # see the new formula immediately.
                    if best_outputs is not None:
                        self._formula_cache.append((name, best_outputs))
                    reused = False

            result["exact_match"] = {
                "name": name,
                "expression": str(best_overall["tree"]),
                "mse": best_overall["mse"],
                "k": best_overall["tree"].node_count,
                "details": f"Evolutionary match for '{self.target_expression}'",
                "reused_existing": reused,
            }

        return result


def _explore_worker_task(
    iterations: int, test_points: list[complex], base_formulas: list[dict[str, Any]]
) -> list[tuple[Any, dict, list[complex]]]:
    """Worker task for parallel exploration. No database access."""
    # We define a dummy engine without a DB to avoid connection issues
    # but still use its composition logic.
    engine = DiscoveryEngine(db=None, test_points=test_points)  # type: ignore
    return engine.discover_and_verify(iterations, base_formulas=base_formulas)
