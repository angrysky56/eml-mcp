import math

from eml_mcp.compiler import EMLCompiler
from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode


def add_divide():
    db = EMLFormulaDB("eml_formulas.db")
    compiler = EMLCompiler(db)

    # divide(x, y) = x * (1/y)
    expr = "multiply(x, reciprocal(y))"
    print(f"Compiling '{expr}'...")
    try:
        tree = compiler.compile(expr)
        print(f"SUCCESS: K={tree.node_count}")

        db.add_formula(
            name="divide",
            description="Division x / y = x * (1/y)",
            tree=tree,
            variables=["x", "y"],
            note="Systematically derived from multiply and reciprocal.",
        )
        print("Added 'divide' to registry.")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    add_divide()
