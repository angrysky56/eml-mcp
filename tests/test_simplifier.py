from eml_mcp.simplifier import get_exp_input, get_ln_input, simplify_tree
from eml_mcp.trees import const, eml_node, var


def test_get_exp_input():
    # exp(x) = eml(x, 1)
    exp_x = eml_node(var("x"), const(1.0))
    assert get_exp_input(exp_x) == var("x")

    # not an exp
    not_exp = eml_node(var("x"), const(2.0))
    assert get_exp_input(not_exp) is None


def test_get_ln_input():
    # ln(x) = eml(1, eml(eml(1, x), 1))
    # Correct structure for ln(x) in EML:
    # ln(x) = eml(1, eml(eml(1, x), 1))
    # Let's build it
    ln_x = eml_node(const(1.0), eml_node(eml_node(const(1.0), var("x")), const(1.0)))
    assert get_ln_input(ln_x) == var("x")

    # slightly wrong
    wrong_ln = eml_node(const(1.0), eml_node(var("x"), const(1.0)))
    assert get_ln_input(wrong_ln) is None


def test_simplify_constant_folding():
    # eml(0, 1) = exp(0) - ln(1) = 1 - 0 = 1
    node = eml_node(const(0.0), const(1.0))
    simplified = simplify_tree(node)
    assert simplified.node_type.name == "CONST"
    assert abs(simplified.value - 1.0) < 1e-15


def test_simplify_exp_ln():
    # exp(ln(x)) -> x
    ln_x = eml_node(const(1.0), eml_node(eml_node(const(1.0), var("x")), const(1.0)))
    exp_ln_x = eml_node(ln_x, const(1.0))
    simplified = simplify_tree(exp_ln_x)
    assert simplified == var("x")


def test_simplify_ln_exp():
    # ln(exp(x)) -> x
    exp_x = eml_node(var("x"), const(1.0))
    ln_exp_x = eml_node(const(1.0), eml_node(eml_node(const(1.0), exp_x), const(1.0)))
    simplified = simplify_tree(ln_exp_x)
    assert simplified == var("x")


def test_simplify_eml_1_1():
    # eml(1, 1) -> e
    node = eml_node(const(1.0), const(1.0))
    simplified = simplify_tree(node)
    assert simplified.node_type.name == "CONST"
    assert abs(simplified.value - 2.718281828459045) < 1e-15
