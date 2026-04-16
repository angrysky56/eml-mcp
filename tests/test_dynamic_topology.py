import math

import pytest
import torch

from eml_mcp.transformer import EMLCompiledFFN
from eml_mcp.trees import EMLNode, NodeType


def test_etree_mapping():
    # Build tree: eml(0, z)
    z = EMLNode(NodeType.VAR, var_name="z")
    tree = EMLNode(NodeType.EML, left=EMLNode(NodeType.CONST, value=0.0), right=z)

    # Needs to be learnable to have delta_W
    model = EMLCompiledFFN(trees=tree, variable_names=["z"], learnable=True)

    # We artificially manipulate the delta_W to map a root to a different path if we wanted to,
    # but initially the argmax of W_fixed + delta_W will match the original tree.
    etrees = model.network_to_etree()

    assert len(etrees) == 1
    # Check that it reconstructs the tree correctly
    assert etrees[0].node_type == NodeType.EML
    assert etrees[0].right.node_type == NodeType.VAR
    assert etrees[0].right.var_name == "z"
    assert etrees[0].left.node_type == NodeType.CONST
    assert etrees[0].left.value == 0.0


def test_redundant_head_pruning():
    # We will build a model tracking something simple.
    # When we call apply_symbolic_pruning(), it should identify any dead ends
    # (e.g. constant fold them out) and zero them.
    # Let's create an intentionally redundant tree.
    # eml( eml(0, 1), z ) => eml(1, z) because eml(0, 1) = exp(0) - ln(1) = 1.0 - 0.0 = 1.0
    c0 = EMLNode(NodeType.CONST, value=0.0)
    c1 = EMLNode(NodeType.CONST, value=1.0)
    redundant_branch = EMLNode(NodeType.EML, left=c0, right=c1)

    z = EMLNode(NodeType.VAR, var_name="z")
    tree = EMLNode(NodeType.EML, left=redundant_branch, right=z)

    model = EMLCompiledFFN(trees=tree, variable_names=["z"], learnable=True)

    # Pre-pruning forward pass
    x = torch.tensor([[5.0]], dtype=torch.float64)
    out_before = model(x)

    # For tracking pruned features, we just call the pruning method
    model.apply_symbolic_pruning()

    out_after = model(x)

    # The output should remain exactly the same due to mathematical equivalency
    assert torch.allclose(out_before, out_after)


def test_validation_mse_persists():
    # Similar check, verifying that the MSE loss persists across a pruning event.
    x = torch.tensor([[2.0], [3.0]], dtype=torch.float64)
    # eml(x, e) = exp(x) - 1.
    e_val = math.e
    tree = EMLNode(
        NodeType.EML,
        left=EMLNode(NodeType.VAR, var_name="x"),
        right=EMLNode(NodeType.CONST, value=e_val),
    )

    model = EMLCompiledFFN(trees=tree, variable_names=["x"], learnable=True)
    target = torch.exp(x) - 1.0

    loss_before = torch.nn.functional.mse_loss(model(x), target)
    model.apply_symbolic_pruning()
    loss_after = torch.nn.functional.mse_loss(model(x), target)

    assert torch.allclose(loss_before, loss_after)


def test_compiled_graph_pruning():
    tree = EMLNode(NodeType.VAR, var_name="z")
    model = EMLCompiledFFN(trees=tree, variable_names=["z"], learnable=True, compile_model=True)
    # Should safely call pruning even when compiled mode is active.
    model.apply_symbolic_pruning()
    x = torch.tensor([[10.0]], dtype=torch.float64)
    assert torch.allclose(model(x), x)
