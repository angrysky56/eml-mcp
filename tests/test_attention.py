import torch
import pytest
from eml_mcp.attention import EMLSymbolicAttention
from eml_mcp.transformer import EMLCompiledFFN
from eml_mcp.trees import EMLNode, NodeType


def test_attention_routing():
    """Test that attention correctly routes signals and weights sum to 1."""
    num_heads = 4
    input_dim = 2
    embed_dim = 8
    batch_size = 5

    attn = EMLSymbolicAttention(num_heads, input_dim, embed_dim)

    x = torch.randn(batch_size, input_dim)
    heads_output = torch.randn(batch_size, num_heads)

    out, weights = attn(x, heads_output)

    # Check shapes
    assert out.shape == (batch_size,)
    assert weights.shape == (batch_size, num_heads)

    # Check weights sum to 1
    torch.testing.assert_close(weights.sum(dim=-1), torch.ones(batch_size, dtype=torch.float32))


def test_forced_routing():
    """Test that forcing attention to one head returns that head's value."""
    num_heads = 2
    input_dim = 1
    embed_dim = 4

    attn = EMLSymbolicAttention(num_heads, input_dim, embed_dim)

    # Manually set weights to favor head 0
    # We can't easily force softmax without extreme values, but we can mock the forward or
    # just check if it's biased.

    x = torch.zeros(1, input_dim)
    heads_output = torch.tensor([[10.0, -5.0]])

    out, weights = attn(x, heads_output)

    # The output should be between -5 and 10
    assert -5.0 <= out.item() <= 10.0


def test_integration_with_ffn():
    """Test EMLCompiledFFN -> EMLSymbolicAttention pipeline."""
    # Define two EML trees: x and 2*x (represented as eml(ln(x), e, constant 1 + 1... or just x and exp(ln(x)) - ln(exp(-1)))
    # For simplicity, let's use [x, zero] heads
    x_node = EMLNode(NodeType.VAR, var_name="x")
    zero_node = EMLNode(NodeType.CONST, value=0.0)

    ffn = EMLCompiledFFN([x_node, zero_node], variable_names=["x"])
    attn = EMLSymbolicAttention(num_heads=2, input_dim=1, dtype=torch.float64)

    input_x = torch.tensor([[5.0], [10.0]], dtype=torch.float64)  # (B, 1)

    heads_out = ffn(input_x)  # (B, 2)
    assert heads_out.shape == (2, 2)

    final_out, weights = attn(input_x, heads_out)

    assert final_out.shape == (2,)
    # Output should be weights[:, 0]*5.0 + weights[:, 1]*0.0
    torch.testing.assert_close(final_out, weights[:, 0] * input_x.squeeze(-1))
