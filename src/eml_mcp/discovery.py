"""
EML Discovery Engine
====================

Explores the EML space to discover novel stable formulas using a novelty search approach.
Supports targeted formula discovery by functional proximity (MSE).
"""

import json
import math
import secrets
from typing import Any

from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode, var


class DiscoveryEngine:
    """Explores the EML space to discover novel stable formulas."""

    def __init__(self, db: EMLFormulaDB | None = None):
        self.db = db or EMLFormulaDB()
        self.test_points = [
            complex(0.5772156649015329),
            complex(1.2824271291006226),
            complex(1.4142135623730951),
            complex(1.6180339887498949),
            complex(2.5),
            complex(0.1),
        ]

    def _extract_variables(self, node: EMLNode) -> set[str]:
        """Extract all unique variable names from a tree."""
        if node.node_type == "var":
            return {node.var_name}
        elif node.node_type == "eml":
            return self._extract_variables(node.left) | self._extract_variables(
                node.right
            )
        return set()

    def generate_random_composition(self) -> tuple[EMLNode, dict[str, Any]]:
        """Generate a new formula by randomly composing existing ones."""
        formulas = self.db.list_formulas()
        if not formulas:
            raise ValueError("No base formulas in DB to compose from")

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
            mse = sum(
                (abs(o - t) ** 2) for o, t in zip(outputs, targets, strict=False)
            ) / len(outputs)
            return mse
        except OverflowError:
            return float("inf")

    def is_novel_and_stable(
        self, tree: EMLNode, check_outputs: list[complex] | None = None
    ) -> bool:
        """Check if a tree is mathematically stable and produces novel outputs."""
        outputs = (
            check_outputs if check_outputs is not None else self._eval_tree_safe(tree)
        )
        if outputs is None:
            return False

        # Verify against all known formulas to ensure novelty
        for f_record in self.db.list_formulas():
            f_tree = EMLNode.from_dict(json.loads(f_record["tree_json"]))
            f_outputs = self._eval_tree_safe(f_tree)

            if f_outputs is None:
                continue

            mse = self.compute_mse(outputs, f_outputs)
            if mse < 1e-10:
                return False  # Matches an existing formula

        return True

    def explore(self, iterations: int = 100) -> list[str]:
        """Run a novelty search to discover new stable formulas.

        Implements the Novelty Search philosophy by archiving mathematically stable,
        emergent formulas (the "Library of the Interesting") rather than solely
        targeting specific reference functions.
        """
        discovered = []
        for _ in range(iterations):
            tree, details = self.generate_random_composition()
            outputs = self._eval_tree_safe(tree)

            if self.is_novel_and_stable(tree, check_outputs=outputs):
                used_vars = sorted(list(self._extract_variables(tree)))
                name = f"discovered_{tree.node_count}_{tree.depth}_{secrets.randbelow(9000) + 1000}"
                description = f"Discovered formula via composition: {details}"

                self.db.add_formula(
                    name=name,
                    description=description,
                    tree=tree,
                    variables=used_vars,
                    note="Novelty Search emergent formula.",
                )

                self.db.add_derivation(
                    formula_name=name,
                    parent_a=details["base"],
                    parent_b=None,
                    method="composition",
                    details=details,
                )

                discovered.append(name)

        return discovered

    def find_target(
        self,
        target_evaluator: callable,
        max_iterations: int = 100,
        top_n: int = 3,
        tolerance: float = 1e-5,
    ) -> dict[str, Any]:
        """
        Attempt to find a formula that matches target_evaluator.
        If an exact match is not found within max_iterations, return the top_n nearest formulas.
        """
        target_outputs = []
        for p in self.test_points:
            try:
                target_outputs.append(target_evaluator(p))
            except (
                ArithmeticError,
                ValueError,
                TypeError,
                ZeroDivisionError,
                NameError,
            ):
                return {"error": "Target evaluator failed on test points."}

        best_matches = []

        def record_candidate(
            name: str, tree: EMLNode, details: str, outputs: list[complex]
        ):
            mse = self.compute_mse(outputs, target_outputs)
            # Remove redundant or identical values
            if any(m["name"] == name for m in best_matches):
                return
            best_matches.append(
                {
                    "name": name,
                    "tree": tree,
                    "mse": mse,
                    "details": details,
                    "expression": tree.to_expression(),
                }
            )

        # 1. Check existing DB
        for f_record in self.db.list_formulas():
            f_tree = EMLNode.from_dict(json.loads(f_record["tree_json"]))
            f_outputs = self._eval_tree_safe(f_tree)
            if f_outputs is not None:
                record_candidate(
                    f_record["name"], f_tree, "existing DB formula", f_outputs
                )

        # 2. Explore for targeted generation
        for _ in range(max_iterations):
            tree, details = self.generate_random_composition()
            outputs = self._eval_tree_safe(tree)
            if outputs is None:
                continue

            # If it's functionally new, we may save it
            if self.is_novel_and_stable(tree, check_outputs=outputs):
                used_vars = sorted(list(self._extract_variables(tree)))
                rand_id = secrets.randbelow(9000) + 1000
                actual_name = f"discovered_{tree.node_count}_{tree.depth}_{rand_id}"

                self.db.add_formula(
                    name=actual_name,
                    description=f"Discovered via targeted search composition: {details}",
                    tree=tree,
                    variables=used_vars,
                    note="Target-driven novelty search.",
                )
                self.db.add_derivation(
                    formula_name=actual_name,
                    parent_a=details["base"],
                    parent_b=None,
                    method="targeted_composition",
                    details=details,
                )
                record_candidate(actual_name, tree, f"Composition: {details}", outputs)
            else:
                # Just a candidate; typically identical to an existing formula if we reach here
                # so we don't save to DB.
                pass

        # Sort by MSE
        best_matches.sort(key=lambda x: x["mse"])

        exact_match = None
        if best_matches and best_matches[0]["mse"] <= tolerance**2:
            exact_match = best_matches[0]

        return {"exact_match": exact_match, "nearby_discoveries": best_matches[:top_n]}
