import math

import torch

from eml_mcp.transformer import EMLCompiledFFN
from eml_mcp.trees import const, eml_node, var


def test_exp_node():
    """Test eml(x, 1) which should be equivalent to exp(x)."""
    # eml(x, 1) = exp(x) - ln(1) = exp(x)
    tree = eml_node(var("x"), const(1.0))
    model = EMLCompiledFFN(variable_names=["x"], node=tree)

    x = torch.linspace(0.1, 2.0, 10).unsqueeze(-1)
    output = model(x)
    expected = torch.exp(x)

    assert torch.allclose(output, expected, atol=1e-6)


def test_ln_node():
    """Test eml(1, x) which should be equivalent to e - ln(x)."""
    # eml(1, x) = exp(1) - ln(x) = e - ln(x)
    tree = eml_node(const(1.0), var("x"))
    model = EMLCompiledFFN(variable_names=["x"], node=tree)

    x = torch.linspace(0.1, 2.0, 10).unsqueeze(-1)
    output = model(x)
    expected = math.e - torch.log(x)

    assert torch.allclose(output, expected, atol=1e-6)


def test_depth_2_identity():
    """Test depth-2 tree: eml(eml(x, 1), 1) which should be exp(exp(x))."""
    # Layer 1: h1 = eml(x, 1) = exp(x)
    # Layer 2: eml(h1, 1) = exp(h1) - ln(1) = exp(exp(x))
    tree = eml_node(eml_node(var("x"), const(1.0)), const(1.0))
    model = EMLCompiledFFN(variable_names=["x"], node=tree)

    x = torch.linspace(0.1, 1.0, 5).unsqueeze(-1)
    output = model(x)
    expected = torch.exp(torch.exp(x))

    assert torch.allclose(output, expected, atol=1e-6)


def test_multi_variable():
    """Test multi-variable support: eml(x, y)."""
    tree = eml_node(var("x"), var("y"))
    model = EMLCompiledFFN(variable_names=["x", "y"], node=tree)

    # x = 1, y = 1
    v = torch.tensor([[1.0, 1.0]])
    output = model(v)
    expected = math.e - 0.0  # exp(1) - ln(1)

    assert torch.allclose(output, torch.tensor([[expected]]), atol=1e-6)

    # x = 0, y = e
    v = torch.tensor([[0.0, math.e]])
    output = model(v)
    expected = 1.0 - 1.0  # exp(0) - ln(e)

    assert torch.allclose(output, torch.tensor([[expected]]), atol=1e-6)


if __name__ == "__main__":
    # Manual run if needed
    test_exp_node()
    test_ln_node()
    test_depth_2_identity()
    test_multi_variable()
    print("All basic transformer tests passed!")
