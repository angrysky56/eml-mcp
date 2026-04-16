from eml_mcp.trees import _x, _1, eml_node
from eml_mcp.similarity import tree_edit_distance

def test_ted():
    x = _x()
    one = _1()
    
    # exp(x) = eml(x, 1)
    exp_x = eml_node(x, one)
    # e = eml(1, 1)
    e = eml_node(one, one)
    
    # Distance between exp(x) and e should be 1 (variable x vs constant 1)
    d1 = tree_edit_distance(exp_x, e)
    print(f"Dist(exp(x), e) = {d1}")
    assert d1 == 1
    
    # Distance between x and eml(x, 1) should be 2 (add node 'eml' and leaf '1')
    # Wait, Zhang-Shasha: 
    # x -> eml(x, 1)
    # Insert node 'eml' and node '1'.
    d2 = tree_edit_distance(x, exp_x)
    print(f"Dist(x, exp(x)) = {d2}")
    assert d2 == 2
    
    # Same trees should have distance 0
    d3 = tree_edit_distance(exp_x, exp_x)
    print(f"Dist(exp(x), exp(x)) = {d3}")
    assert d3 == 0

    print("TED tests passed!")

if __name__ == "__main__":
    test_ted()
