"""
EML Symbolic Attention Mechanism.

This module implements a routing mechanism that selectively weights the outputs
of multiple EML functional heads using a scaled dot-product attention mechanism.
"""

from __future__ import annotations
import torch
import torch.nn as nn
from torch import Tensor


class EMLSymbolicAttention(nn.Module):
    """Attention mechanism for routing signals through EML functional heads.

    Instead of attending over tokens in a sequence, this mechanism attends over
    different functional identities (heads) computed by an EMLCompiledFFN.
    """

    def __init__(
        self,
        num_heads: int,
        input_dim: int,
        embed_dim: int = 32,
        dtype: torch.dtype = torch.float32,
    ):
        """Initialize the attention module.

        Args:
            num_heads: Number of EML functional heads to attend over.
            input_dim: Dimension of the input context x.
            embed_dim: Latent dimension for query/key projections.
            dtype: Floating point precision (match EMLCompiledFFN if needed).
        """
        super().__init__()
        self.num_heads = num_heads
        self.input_dim = input_dim
        self.embed_dim = embed_dim

        # Query projection from the input context
        self.q_proj = nn.Linear(input_dim, embed_dim, dtype=dtype)

        # Key projection for head signatures
        self.k_proj = nn.Linear(embed_dim, embed_dim, dtype=dtype)

        # Learnable head embeddings: each functional identity has a signature
        self.head_embeddings = nn.Parameter(torch.randn(num_heads, embed_dim, dtype=dtype))

        self.scale = embed_dim**-0.5

    def forward(self, x: Tensor, heads_output: Tensor) -> tuple[Tensor, Tensor]:
        """Forward pass.

        Args:
            x: Input context of shape (..., input_dim).
            heads_output: Output of EMLCompiledFFN of shape (..., num_heads).

        Returns:
            - Aggregated output of shape (...).
            - Attention weights of shape (..., num_heads).
        """
        # 1. Compute Query from context
        # q shape: (..., embed_dim)
        q = self.q_proj(x)

        # 2. Compute Keys from head signatures
        # k shape: (num_heads, embed_dim)
        k = self.k_proj(self.head_embeddings)

        # 3. Scaled dot-product attention
        # (..., embed_dim) @ (embed_dim, num_heads) -> (..., num_heads)
        attn_scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        attn_weights = torch.softmax(attn_scores, dim=-1)

        # 4. Aggregate functional heads
        # (..., num_heads) * (..., num_heads) -> (..., num_heads) -> sum -> (...)
        out = (attn_weights * heads_output).sum(dim=-1)

        return out, attn_weights
