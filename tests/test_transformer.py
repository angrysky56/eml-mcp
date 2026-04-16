"""
Tests for the EML-Transformer compiler.
"""

import torch
import pytest
import math
from eml_mcp.transformer import EMLCompiledFFN
from eml_mcp.compiler import EMLCompiler
from eml_mcp.trees import EMLNode, NodeType
from eml_mcp.database import EMLFormulaDB


@pytest.fixture
def compiler():
    return EMLCompiler()


def test_exp_node(compiler):
    # eml(x, 1) -> exp(x) - ln(1) = exp(x)
    tree = compiler.compile("exp(x)")
    model = EMLCompiledFFN(tree, variable_names=["x"])
    model.eval()

    x_vals = torch.linspace(-2, 2, 10, dtype=torch.float64).unsqueeze(-1)
    with torch.no_grad():
        output = model(x_vals)
        expected = torch.exp(x_vals).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)


def test_ln_node(compiler):
    # eml(1, x) -> exp(1) - ln(x) = e - ln(x)
    tree = compiler.compile("eml(1, x)")
    model = EMLCompiledFFN(tree, variable_names=["x"])
    model.eval()

    # x must be positive for log
    x_vals = torch.linspace(0.1, 5, 10, dtype=torch.float64).unsqueeze(-1)
    with torch.no_grad():
        output = model(x_vals)
        expected = math.e - torch.log(x_vals).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)


def test_complex_mode_exp(compiler):
    # eml(x, 1) in complex mode
    tree = compiler.compile("exp(x)")
    model = EMLCompiledFFN(tree, variable_names=["x"], complex_mode=True)
    model.eval()

    # Complex inputs
    x_real = torch.linspace(-1, 1, 5, dtype=torch.float64)
    x_imag = torch.linspace(-1, 1, 5, dtype=torch.float64)
    x_vals = torch.complex(x_real, x_imag).unsqueeze(-1)

    with torch.no_grad():
        output = model(x_vals)
        expected = torch.exp(x_vals).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)


def test_complex_mode_eml(compiler):
    # tree for eml(x, y)
    tree = compiler.compile("eml(x, y)")
    model = EMLCompiledFFN(tree, variable_names=["x", "y"], complex_mode=True)
    model.eval()

    # Complex inputs: x = 1.0 + 1.0j, y = 2.0 - 0.5j
    x = torch.tensor([1.0 + 1.0j], dtype=torch.complex128)
    y = torch.tensor([2.0 - 0.5j], dtype=torch.complex128)
    inputs = torch.stack([x, y], dim=-1)

    with torch.no_grad():
        output = model(inputs)
        # expected: exp(x) - ln(y)
        # torch.log(complex) uses principal branch
        expected = torch.exp(x) - torch.log(y)

    assert torch.allclose(output, expected, atol=1e-10)


def test_nested_eml(compiler):
    # eml(x, eml(x, 1)) -> exp(x) - ln(exp(x)) = exp(x) - x
    tree = compiler.compile("eml(x, exp(x))")
    model = EMLCompiledFFN(tree, variable_names=["x"])
    model.eval()

    x_vals = torch.linspace(0.1, 2, 10, dtype=torch.float64).unsqueeze(-1)
    with torch.no_grad():
        output = model(x_vals)
        expected = (torch.exp(x_vals) - x_vals).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)


def test_variable_mapping(compiler):
    # Multiple variables
    tree = compiler.compile("eml(x, y)")
    model = EMLCompiledFFN(tree, variable_names=["x", "y"])
    model.eval()

    x = torch.tensor([1.0, 2.0], dtype=torch.float64)
    y = torch.tensor([0.5, 3.0], dtype=torch.float64)
    inputs = torch.stack([x, y], dim=-1)  # Shape (2, 2)

    with torch.no_grad():
        output = model(inputs)
        expected = torch.exp(x) - torch.log(y)

    assert torch.allclose(output, expected, atol=1e-10)


def test_learnable_deltas(compiler):
    tree = compiler.compile("exp(x)")
    model = EMLCompiledFFN(tree, variable_names=["x"], learnable=True)

    # Ensure parameters exist
    params = list(model.parameters())
    assert len(params) > 0

    x_vals = torch.tensor([[1.0]], dtype=torch.float64)
    output = model(x_vals)

    # Target loss: make output match some arbitrary value
    loss = (output - 5.0).pow(2).sum()
    loss.backward()

    # Check if gradients are non-zero
    for p in model.parameters():
        assert p.grad is not None
        assert not torch.allclose(p.grad, torch.zeros_like(p.grad))


def test_recursive_call():
    """Test that CALL nodes are expanded during compilation."""
    db = EMLFormulaDB(":memory:")

    # Create a CALL node: exp(x)
    # The 'exp' formula in DB expects 'x'
    x_node = EMLNode(NodeType.VAR, var_name="x")
    call_node = EMLNode(NodeType.CALL, func_name="exp", args={"x": x_node})

    # Use x as the input variable
    model = EMLCompiledFFN(call_node, variable_names=["x"], db=db)
    model.eval()

    x_vals = torch.linspace(-2, 2, 5, dtype=torch.float64).unsqueeze(-1)
    with torch.no_grad():
        output = model(x_vals)
        expected = torch.exp(x_vals).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)


def test_deep_recursive_call():
    """Test expansion of calls within calls."""
    db = EMLFormulaDB(":memory:")

    # exp(exp(x))
    x_node = EMLNode(NodeType.VAR, var_name="x")
    inner_call = EMLNode(NodeType.CALL, func_name="exp", args={"x": x_node})
    outer_call = EMLNode(NodeType.CALL, func_name="exp", args={"x": inner_call})

    model = EMLCompiledFFN(outer_call, variable_names=["x"], db=db)
    model.eval()

    x_vals = torch.linspace(-1, 1, 5, dtype=torch.float64).unsqueeze(-1)
    with torch.no_grad():
        output = model(x_vals)
        expected = torch.exp(torch.exp(x_vals)).squeeze(-1)

    assert torch.allclose(output, expected, atol=1e-10)
