import cmath
import json
import math

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.trees import EMLNode, eml_node, var


def test_composition_logic():
    db = EMLFormulaDB("eml_formulas.db")
    engine = DiscoveryEngine(db)

    # Manually check if exp(exp(x)) matches the target
    target_expr = "exp(exp(x))"
    x_vals = engine.test_points
    targets = [complex(cmath.exp(cmath.exp(x))) for x in x_vals]

    # Build exp(exp(x)) manually
    # exp(x) = eml(x, 1)
    from eml_mcp.trees import NodeType

    exp_x = eml_node(var("x"), EMLNode(node_type=NodeType.CONST, value=complex(1.0)))
    exp_exp_x = eml_node(exp_x, EMLNode(node_type=NodeType.CONST, value=complex(1.0)))

    print(f"Manual tree: {exp_exp_x.to_expression()}")

    outputs = []
    for x in x_vals:
        outputs.append(exp_exp_x.evaluate({"x": x}))

    mse = sum(abs(o - t) ** 2 for o, t in zip(outputs, targets)) / len(outputs)
    print(f"MSE of manual tree: {mse}")

    # Check is_novel_and_stable
    is_novel = engine.is_novel_and_stable(exp_exp_x, check_outputs=outputs)
    print(f"Is manual tree novel and stable? {is_novel}")

    db.close()


if __name__ == "__main__":
    test_composition_logic()
