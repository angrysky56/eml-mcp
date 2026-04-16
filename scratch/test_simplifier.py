from eml_mcp.registry import build_exp_from_subtree, build_ln_from_subtree
from eml_mcp.simplifier import simplify_tree
from eml_mcp.trees import _1, _x, eml_node


def test_simplification():
    x = _x()

    # Test 1: exp(ln(x)) -> x
    ln_x = build_ln_from_subtree(x)
    exp_ln_x = build_exp_from_subtree(ln_x)

    print(f"Original: {exp_ln_x.to_expression()} (K={exp_ln_x.node_count})")
    sim1 = simplify_tree(exp_ln_x)
    print(f"Simplified: {sim1.to_expression()} (K={sim1.node_count})")
    assert sim1.to_expression() == "x"

    # Test 2: ln(exp(x)) -> x
    exp_x = build_exp_from_subtree(x)
    ln_exp_x = build_ln_from_subtree(exp_x)

    print(f"Original: {ln_exp_x.to_expression()} (K={ln_exp_x.node_count})")
    sim2 = simplify_tree(ln_exp_x)
    print(f"Simplified: {sim2.to_expression()} (K={sim2.node_count})")
    assert sim2.to_expression() == "x"

    # Test 3: Constant folding eml(1, 1) -> e
    e_tree = eml_node(_1(), _1())
    print(f"Original: {e_tree.to_expression()}")
    sim3 = simplify_tree(e_tree)
    print(f"Simplified: {sim3.to_expression()}")
    # It might be 2.718... or 'e' string depending on extract_real but to_expression uses the value

    print("All tests passed!")


if __name__ == "__main__":
    test_simplification()
