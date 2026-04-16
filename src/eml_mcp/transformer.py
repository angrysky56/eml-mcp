"""
EML-Transformer Prototype
=========================

Analytical FFN construction that compiles discrete EML formula trees
into structural PyTorch weights.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from eml_mcp.trees import EMLNode, NodeType


class EMLCompiledFFN(nn.Module):
    """
    Analytical FFN module that implements a compiled EML tree stage.

    Computes: out = exp(W_e * x + b_e) - ln(relu(W_l * x + b_l) + eps)

    This replicates nested operations inside a structured feed-forward module.
    Each EMLCompiledFFN instance corresponds to one 'eml(left, right)' operator.
    Nested trees are supported via recursive sub-modules.
    """

    def __init__(
        self, variable_names: list[str], node: EMLNode | None = None, eps: float = 1e-8
    ):
        super().__init__()
        self.variable_names = variable_names
        self.n_vars = len(variable_names)
        self.eps = eps

        # Linear layers representing the dual paths to 'exp' and 'ln'
        self.W_e = nn.Linear(self.n_vars, 1, bias=True)
        self.W_l = nn.Linear(self.n_vars, 1, bias=True)

        # Optional sub-modules for recursive expansion (depth-2 and beyond)
        self.left_sub: EMLCompiledFFN | None = None
        self.right_sub: EMLCompiledFFN | None = None

        if node:
            self.compile_tree(node)

    def compile_tree(self, node: EMLNode) -> None:
        """Analytically derives weight matrices and biases from an EML tree."""
        if node.node_type != NodeType.EML:
            raise ValueError(
                f"Cannot compile terminal node of type {node.node_type} at root of FFN."
            )

        # Left path (exp input)
        self._compile_path("e", node.left)
        # Right path (ln input)
        self._compile_path("l", node.right)

    def _compile_path(self, path: str, child: EMLNode) -> None:
        layer = self.W_e if path == "e" else self.W_l

        with torch.no_grad():
            # Default to zero weights/bias
            nn.init.zeros_(layer.weight)
            nn.init.zeros_(layer.bias)

            if child.node_type == NodeType.CONST:
                layer.bias.fill_(child.value.real)
            elif child.node_type == NodeType.VAR:
                if child.var_name not in self.variable_names:
                    raise ValueError(
                        f"Variable '{child.var_name}' not found in variable_names list."
                    )
                idx = self.variable_names.index(child.var_name)
                layer.weight[0, idx] = 1.0
            elif child.node_type == NodeType.EML:
                # Depth-2 support: create a sub-FFN to compute this child
                sub = EMLCompiledFFN(self.variable_names, node=child, eps=self.eps)
                if path == "e":
                    self.left_sub = sub
                else:
                    self.right_sub = sub

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass implementing the EML activation logic.

        Arguments:
            x: Input tensor of shape (batch, n_vars) match variable_names.

        Returns:
            Computed output tensor.
        """
        # If we have sub-modules (depth-2+), they override the direct linear path
        # for that side of the EML operation.

        if self.left_sub is not None:
            e_input = self.left_sub(x)
        else:
            e_input = self.W_e(x)

        if self.right_sub is not None:
            l_input = self.right_sub(x)
        else:
            l_input = self.W_l(x)

        # exp(e_input) - ln(relu(l_input) + eps)
        e_path = torch.exp(e_input)
        l_path = torch.log(torch.relu(l_input) + self.eps)

        return e_path - l_path
