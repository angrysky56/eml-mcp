import cmath
import json
import math

from eml_mcp.compiler import EMLCompiler
from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.trees import EMLNode


def bootstrap_trig():
    db = EMLFormulaDB("eml_formulas.db")
    engine = DiscoveryEngine(db)
    compiler = EMLCompiler(db)

    targets = [
        ("sin", "sin(x)", "sin(x)"),
        ("cos", "cos(x)", "cos(x)"),
        ("tan", "tan(x)", "tan(x)"),
    ]

    for name, desc, expr in targets:
        print(f"\nBootstrapping trig function '{name}' ({expr})...")
        if db.formula_exists(name):
            print(f"Skipping '{name}', already exists.")
            continue

        # Trig functions are harder, increase iterations
        results = engine.find_target(target=expr, max_iterations=500, tolerance=1e-8)

        exact_match = results.get("exact_match")
        if exact_match and isinstance(exact_match, dict):
            tree = compiler.compile(exact_match["expression"])

            print(
                f"SUCCESS: Found {name} = {exact_match['expression']} (K={tree.node_count})"
            )

            db.add_formula(
                name=name,
                description=f"Derived: {desc}",
                tree=tree,
                variables=["x"],
                note="Trig function derived via evolutionary discovery.",
            )
            db.add_derivation(
                formula_name=name,
                parent_a=None,
                parent_b=None,
                method="discovery",
                details={"target_expression": expr, "mse": exact_match["mse"]},
            )
        else:
            best = (
                results["nearby_discoveries"][0]
                if results.get("nearby_discoveries")
                else None
            )
            mse_str = f"{best['mse']:.2e}" if best else "N/A"
            print(f"FAILED to find exact match for {name}. Best MSE: {mse_str}")
            if best:
                print(f"Best found: {best['expression']}")

    db.close()


if __name__ == "__main__":
    bootstrap_trig()
