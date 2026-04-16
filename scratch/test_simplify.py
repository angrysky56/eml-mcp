
from eml_mcp.trees import eml_node, _1, _x
from eml_mcp.simplifier import simplify_tree, get_ln_input, get_exp_input

def test_simplification():
    # exp(ln(x)) = eml(ln(x), 1)
    # ln(x) = eml(1, eml(eml(1, x), 1))
    
    x = _x()
    ln_x = eml_node(_1(), eml_node(eml_node(_1(), x), _1()))
    exp_ln_x = eml_node(ln_x, _1())
    
    print(f"Original: {exp_ln_x.to_expression()}")
    print(f"Original K: {exp_ln_x.node_count}")
    
    simplified = simplify_tree(exp_ln_x)
    print(f"Simplified: {simplified.to_expression()}")
    print(f"Simplified K: {simplified.node_count}")
    
    assert simplified.to_expression() == "x"
    assert simplified.node_count == 1

    # ln(exp(x))
    # exp(x) = eml(x, 1)
    exp_x = eml_node(x, _1())
    ln_exp_x = eml_node(_1(), eml_node(eml_node(_1(), exp_x), _1()))
    
    print(f"Original: {ln_exp_x.to_expression()}")
    simplified_ln_exp = simplify_tree(ln_exp_x)
    print(f"Simplified: {simplified_ln_exp.to_expression()}")
    
    assert simplified_ln_exp.to_expression() == "x"

if __name__ == "__main__":
    test_simplification()
