import json
import math

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.trees import EMLNode, NodeType, const, var


def reproduce():
    db = EMLFormulaDB("test_repro.db")
    engine = DiscoveryEngine(db)

    # Create a tree that will trigger the inf-to-int conversion in to_expression
    # if it's used as a constant node incorrectly or something.
    # Actually, EMLNode.to_expression is where I fixed it.

    inf_node = const(float("inf"))
    print(f"Inf node expression: {inf_node.to_expression()}")

    # Try discovering something
    print("Running discovery...")
    try:
        engine.find_target("1j", max_iterations=20)
        print("Discovery successful (or at least no crash)")
    except Exception as e:
        print(f"Caught error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce()
