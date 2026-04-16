import cmath
import math

import numpy as np

from eml_mcp.compiler import EMLCompiler
from eml_mcp.database import EMLFormulaDB
from eml_mcp.primitives import TEST_POINTS
from eml_mcp.trees import EMLNode


def verify_and_add(db, name, description, expr, target_fn):
    compiler = EMLCompiler(db)
    print(f"\nBootstrapping {name}...")
    try:
        tree = compiler.compile(expr)
        print(f"Compiled to {tree.node_count} nodes.")

        # Verify
        errors = []
        for p in TEST_POINTS:
            val = tree.evaluate({"x": p})
            target = target_fn(p)
            errors.append(abs(val - target) ** 2)

        mse = float(np.mean(errors))
        print(f"MSE: {mse:.2e}")

        if mse < 1e-10:
            db.add_formula(
                name=name,
                description=description,
                tree=tree,
                variables=["x"],
                note=f"Systematically derived via EML identity: {expr}",
            )
            print(f"Added '{name}' to registry.")
            return True
        else:
            print(f"FAILED verification (MSE too high).")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


def bootstrap_trig_manual():
    db = EMLFormulaDB("eml_formulas.db")

    # sin(x) = (exp(1j * x) - exp(-1j * x)) / (2j)
    # Using the formulas: subtract(x, y), multiply(x, y), divide(x, y), exp(x), negate(x)
    sin_expr = (
        "divide(subtract(exp(multiply(1j, x)), exp(multiply(negate(1j), x))), 2j)"
    )
    verify_and_add(db, "sin", "Sine function sin(x)", sin_expr, cmath.sin)

    # cos(x) = (exp(1j * x) + exp(-1j * x)) / 2
    cos_expr = "divide(add(exp(multiply(1j, x)), exp(multiply(negate(1j), x))), 2.0)"
    verify_and_add(db, "cos", "Cosine function cos(x)", cos_expr, cmath.cos)

    # tan(x) = sin(x) / cos(x)
    # tan_expr = "divide(sin(x), cos(x))"
    # Actually simpler: tan(x) = sin(x) / cos(x)
    # But let's see if we can just use the sin/cos we just added
    tan_expr = "divide(sin(x), cos(x))"
    verify_and_add(db, "tan", "Tangent function tan(x)", tan_expr, cmath.tan)

    db.close()


if __name__ == "__main__":
    bootstrap_trig_manual()
