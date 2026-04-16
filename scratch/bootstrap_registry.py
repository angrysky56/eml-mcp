import cmath
import json
import math

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import EMLNode


def bootstrap_phase7():
    db = EMLFormulaDB("eml_formulas.db")
    engine = DiscoveryEngine(db)

    targets = [
        ("reciprocal", "1/x", "1/x"),
        ("divide", "x/y", "x/y"),
        ("exp_exp", "exp(exp(x))", "exp(exp(x))"),
        # ("sin", "sin(x)", "sin(x)"), # Might be deep
        # ("cos", "cos(x)", "cos(x)"),
        # ("tan", "tan(x)", "tan(x)"),
    ]

    for name, desc, expr in targets:
        print(f"\nDistilling '{name}' ({expr})...")
        if db.formula_exists(name):
            print(f"Skipping '{name}', already exists.")
            continue

        results = engine.find_target(
            target_expression=expr, max_iterations=200, tolerance=1e-10
        )

        if results.get("status") == "error":
            print(f"ERROR distilling '{name}': {results.get('message')}")
            continue

        if results.get("exact_match"):
            match = results["exact_match"]
            tree = match["tree"]
            print(
                f"FOUND EXACT match for {name}: {match['expression']} (K={tree.node_count})"
            )

            # Add to registry
            db.add_formula(
                name=name,
                description=f"Derived: {desc}",
                tree=tree,
                variables=["x", "y"] if "y" in expr else ["x"],
                note="Systematically derived in Phase 7 bootstrapping.",
            )
            # Add derivation
            db.add_derivation(
                formula_name=name,
                parent_a=None,
                parent_b=None,
                method="discovery",
                details={"target_expression": expr, "mse": match["mse"]},
            )
        else:
            best = (
                results["nearby_discoveries"][0]
                if results.get("nearby_discoveries")
                else None
            )
            mse_str = f"{best['mse']:.2e}" if best else "N/A"
            print(f"No exact match for {name}. Best MSE: {mse_str}")

    db.close()


if __name__ == "__main__":
    bootstrap_phase7()
