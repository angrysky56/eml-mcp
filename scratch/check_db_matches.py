"""
Utility script to check the EML database for formulas that match specific functional targets.
"""
import json

from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode


def check_for_reciprocal():
    """
    Search the database for formulas that evaluate close to 1/x for a test point.
    """
    db = EMLFormulaDB("eml_formulas.db")

    test_x = 2.5
    target = 1.0 / test_x

    print(f"Target for 1/{test_x} is {target}")

    for f in db.list_formulas():
        tree = EMLNode.from_dict(json.loads(f["tree_json"]))
        try:
            val = tree.evaluate({"x": complex(test_x)})
            error = abs(val - target)
            if error < 1e-10:
                print(f"FOUND MATCH: {f['name']} - Error: {error}")
                print(f"Expression: {f['expression']}")
        except (ValueError, TypeError, ZeroDivisionError, RuntimeError):
            continue
    db.close()


if __name__ == "__main__":
    check_for_reciprocal()
