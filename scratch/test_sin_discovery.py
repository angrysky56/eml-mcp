import math
import cmath
import json
import logging
from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.trees import EMLNode

def test_sin_discovery():
    logging.basicConfig(level=logging.INFO)
    db = EMLFormulaDB("eml_formulas.db")
    engine = DiscoveryEngine(db)
    
    target = "sin(x)"
    print(f"Searching for {target}...")
    
    # We increase max_iterations because sin(x) is harder
    results = engine.find_target(target_expression=target, max_iterations=2000, tolerance=1e-8)
    
    if results.get("exact_match"):
        print(f"SUCCESS: Found {results['exact_match']['name']}")
        print(f"Expression: {results['exact_match']['expression']}")
        print(f"MSE: {results['exact_match']['mse']}")
        print(f"K: {results['exact_match']['tree'].node_count}")
    else:
        print("FAILED to find exact match")
        if results.get("nearby_discoveries"):
            best = results["nearby_discoveries"][0]
            print(f"Best MSE: {best['mse']}")
            print(f"Best Name: {best['name']}")
            print(f"Best Expression: {best['expression']}")
            print(f"Best K: {best['tree'].node_count}")
    
    db.close()

if __name__ == "__main__":
    test_sin_discovery()
