
from eml_mcp.similarity import tree_edit_distance
from eml_mcp.trees import const, eml_node, var


def test_ted_identical():
    # Identical trees should have distance 0
    t1 = eml_node(var("x"), const(1.0))
    t2 = eml_node(var("x"), const(1.0))
    assert tree_edit_distance(t1, t2) == 0


def test_ted_different_vars():
    # x vs y
    t1 = var("x")
    t2 = var("y")
    assert tree_edit_distance(t1, t2) == 1


def test_ted_different_consts():
    # 1 vs 2
    t1 = const(1.0)
    t2 = const(2.0)
    assert tree_edit_distance(t1, t2) == 1


def test_ted_structure_change():
    # x vs exp(x)
    t1 = var("x")
    t2 = eml_node(var("x"), const(1.0))
    # exp(x) has 3 nodes total in TED: eml, VAR_X, 1.0
    # VAR_X has 1 node.
    # Edit distance should be 2 (add eml, add 1.0)
    assert tree_edit_distance(t1, t2) == 2


def test_ted_deep_structure():
    # exp(x) vs ln(x)
    # exp(x) = eml(x, 1) -> [eml, x, 1]
    # ln(x) = eml(1, eml(eml(1, x), 1)) -> [eml, 1, eml, eml, 1, x, 1]
    # This is more complex.
    exp_x = eml_node(var("x"), const(1.0))
    ln_x = eml_node(const(1.0), eml_node(eml_node(const(1.0), var("x")), const(1.0)))
    dist = tree_edit_distance(exp_x, ln_x)
    assert dist > 0
    # Should be symmetric
    assert tree_edit_distance(ln_x, exp_x) == dist
