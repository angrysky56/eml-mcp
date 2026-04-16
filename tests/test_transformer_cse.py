import torch
import torch.nn as nn
from eml_mcp.trees import var, eml_node, const
from eml_mcp.transformer import EMLCompiledFFN

def test_cse_node_reuse():
    """Verify that redundant sub-trees are only computed once (sharing tape index)."""
    x_node = var("x")
    # Subtree: exp(x) = eml(x, 1)
    exp_x = eml_node(x_node, const(1.0))
    
    # Root: eml(exp(x), exp(x))
    # Structural redundancy: exp(x) appears twice.
    root = eml_node(exp_x, exp_x)
    
    ffn = EMLCompiledFFN(root, ["x"])
    
    # Analyze unique nodes:
    # 1. x (VAR)
    # 2. 1.0 (CONST)
    # 3. eml(x, 1.0) (EML) - exp_x
    # 4. eml(exp_x, exp_x) (EML) - root
    # Total unique nodes = 4
    
    print(f"Num nodes (structural): {ffn.num_nodes}")
    assert ffn.num_nodes == 4
    
    x_val = torch.tensor([[1.0]], dtype=torch.float64)
    out = ffn(x_val).squeeze()
    
    # Manual check: eml(exp(1), exp(1)) = exp(exp(1)) - ln(exp(1))
    # = exp(e) - 1
    val_e = torch.exp(torch.tensor(1.0, dtype=torch.float64))
    expected = torch.exp(val_e) - 1.0
    assert torch.allclose(out, expected)

def test_semantic_cse():
    """Verify that semantic identities are reduced, leading to further CSE."""
    x_node = var("x")
    # exp(ln(x))
    # ln(x) = eml(1, eml(eml(1, x), 1))
    # Note: simplification rules may vary, but exp(ln(x)) should go to x.
    ln_x = eml_node(const(1.0), eml_node(eml_node(const(1.0), x_node), const(1.0)))
    exp_ln_x = eml_node(ln_x, const(1.0))
    
    ffn = EMLCompiledFFN(exp_ln_x, ["x"])
    
    # exp(ln(x)) should simplify to x
    # So num_nodes should be 1
    print(f"Num nodes (semantic): {ffn.num_nodes}")
    assert ffn.num_nodes == 1
    
    x_val = torch.tensor([[2.5]], dtype=torch.float64)
    out = ffn(x_val).squeeze()
    assert torch.allclose(out, torch.tensor(2.5, dtype=torch.float64))

if __name__ == "__main__":
    test_cse_node_reuse()
    test_semantic_cse()
    print("All CSE tests passed!")
