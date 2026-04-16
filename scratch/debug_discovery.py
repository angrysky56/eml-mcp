import cmath
import json
import logging
import math

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.trees import EMLNode


def debug_discovery():
    logging.basicConfig(level=logging.INFO)
    db = EMLFormulaDB("eml_formulas.db")
    engine = DiscoveryEngine(db)

    # Let's try to find exp(exp(x)) specifically
    target = "exp(exp(x))"
    print(f"Searching for {target}...")

    results = engine.find_target(target_expression=target, max_iterations=500)

    if results.get("exact_match"):
        print(f"SUCCESS: Found {results['exact_match']['expression']}")
    else:
        print("FAILED to find exact match")
        if results.get("nearby_discoveries"):
            print(f"Best MSE: {results['nearby_discoveries'][0]['mse']}")
            print(f"Best Expression: {results['nearby_discoveries'][0]['expression']}")

    db.close()


if __name__ == "__main__":
    debug_discovery()
