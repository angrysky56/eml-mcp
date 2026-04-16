"""
EML Symbolic Regression module using PyTorch.

Implements the Master Formula Tree approach from Odrzywołek (2026) for
recovering exact EML identities from numerical data using gradient descent.
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


class SelectionGate(nn.Module):
    """Parameterized selection of inputs for a leaf node.

    Combines variables (x, y, ...) and common constants (1, 0, e)
    into a differentiable linear combination.
    """

    def __init__(self, variable_names: list[str], constants: list[float] | None = None):
        super().__init__()
        self.variable_names = variable_names
        self.constants = constants if constants is not None else [1.0, 0.0, math.e]

        # Initialize weights with small random noise to break symmetry
        n_inputs = len(self.variable_names) + len(self.constants)
        self.selection_logits = nn.Parameter(torch.randn(n_inputs) * 0.01)

    def forward(self, variables: dict[str, Tensor], temperature: float = 1.0) -> Tensor:
        """Compute the weighted combination of inputs."""
        probs = torch.softmax(self.selection_logits / (temperature + 1e-8), dim=0).to(torch.complex128)

        inputs = []
        # Variables
        for name in self.variable_names:
            inputs.append(variables[name])

        # Constants
        batch_shape = inputs[0].shape if inputs else (1,)
        for c in self.constants:
            val = torch.full(
                batch_shape,
                c,
                dtype=torch.complex128,
                device=self.selection_logits.device,
            )
            inputs.append(val)

        # Stack and multiply by probabilities
        input_stack = torch.stack(inputs, dim=-1)
        return (input_stack * probs).sum(dim=-1)

    def get_formula(self) -> str:
        """Extract the 'snapped' symbolic formula from current weights."""
        with torch.no_grad():
            idx = torch.argmax(self.selection_logits).item()

            if idx < len(self.variable_names):
                return self.variable_names[idx]
            else:
                c_idx = idx - len(self.variable_names)
                c = self.constants[c_idx]
                if c == math.e:
                    return "e"
                return str(int(c) if c.is_integer() else c)


class EMLNode(nn.Module):
    """A differentiable EML operator node."""

    def __init__(self, left: nn.Module, right: nn.Module):
        super().__init__()
        self.left = left
        self.right = right

    def forward(self, variables: dict[str, Tensor], temperature: float = 1.0) -> Tensor:
        """Apply eml(x, y) = exp(x) - ln(y)."""
        x = self.left(variables, temperature=temperature)
        y = self.right(variables, temperature=temperature)

        # Soft clamping for gradients: linear in [-50, 50], log growth outside
        threshold = 50.0
        x_real = x.real
        # Above threshold: threshold + log(1 + x - threshold)
        x_real = torch.where(x_real > threshold, threshold + torch.log(1.0 + x_real - threshold), x_real)
        # Below -threshold: -threshold - log(1 - (x + threshold))
        x_real = torch.where(x_real < -threshold, -threshold - torch.log(1.0 - (x_real + threshold)), x_real)
        
        exp_x = torch.exp(torch.complex(x_real, x.imag))
        
        # Clip magnitude of exp_x for stability while preserving phase
        exp_x = torch.polar(exp_x.abs().clamp(max=1e30), exp_x.angle())

        # Safe complex log
        y_mag = y.abs().clamp(min=1e-15)
        y_real = y.real
        y_imag = y.imag
        # Stabilize atan2 gradient near origin
        is_near_origin = (y_real.abs() < 1e-18) & (y_imag.abs() < 1e-18)
        y_real_safe = torch.where(is_near_origin, y_real + 1e-18, y_real)
        ln_y = torch.complex(torch.log(y_mag), torch.atan2(y_imag, y_real_safe))

        return exp_x - ln_y

    def get_formula(self) -> str:
        """Get the symbolic formula for this node."""
        return f"eml({self.left.get_formula()}, {self.right.get_formula()})"


class EMLMasterTree(nn.Module):
    """Full binary tree of EML nodes for symbolic regression."""

    def __init__(self, depth: int, variable_names: list[str]):
        super().__init__()
        self.depth = depth
        self.variable_names = variable_names
        self.root = self._build_tree(depth)

    def _build_tree(self, depth: int) -> nn.Module:
        if depth == 0:
            return SelectionGate(self.variable_names)
        return EMLNode(self._build_tree(depth - 1), self._build_tree(depth - 1))

    def forward(self, variables: dict[str, Tensor], temperature: float = 1.0) -> Tensor:
        return self.root(variables, temperature=temperature)

    def get_formula(self) -> str:
        """Get the full symbolic formula of the tree."""
        return self.root.get_formula()

    def get_discrete_formula(self) -> str:
        """Extract the learned discrete formula string."""
        return self._build_discrete_formula(self.root)

    def _build_discrete_formula(self, node: EMLNode) -> str:
        if isinstance(node, SelectionGate):
            return node.get_formula()

        # Internal node: recursively build left and right
        left_str = self._build_discrete_formula(node.left)
        right_str = self._build_discrete_formula(node.right)
        return f"eml({left_str}, {right_str})"


def train_eml_tree(
    target_data: dict[str, Tensor],
    target_values: Tensor,
    depth: int = 3,
    epochs: int = 2000,
    lr: float = 0.01,
) -> EMLMasterTree:
    """Train a master tree to match target values."""
    var_names = list(target_data.keys())
    model = EMLMasterTree(depth, var_names)
    # Slow starting learning rate for stability
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        # Temperature schedule: start high (1.0), decay to low (0.01)
        temp = max(0.01, 1.0 * (0.999**epoch))
        
        optimizer.zero_grad()
        output = model(target_data, temperature=temp)

        # Huber Loss is more robust to outliers (large initial errors)
        loss = F.huber_loss(output.real, target_values.real, delta=1.0) + \
               F.huber_loss(output.imag, target_values.imag, delta=1.0)

        if torch.isnan(loss) or torch.isinf(loss):
            print(f"Stopping at epoch {epoch}: Invalid loss ({loss.item()}) encountered.")
            break

        loss.backward()

        # Check for NaN gradients
        has_nan_grad = False
        for name, param in model.named_parameters():
            if param.grad is not None and torch.isnan(param.grad).any():
                print(f"NaN gradient in {name} at epoch {epoch}")
                has_nan_grad = True
        
        if has_nan_grad:
            print(f"Stopping at epoch {epoch} due to NaN gradients.")
            break

        # Gradient clipping is essential for deep EML trees
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=10.0)

        optimizer.step()

        if epoch % 200 == 0:
            print(f"Epoch {epoch}: Loss = {loss.item():.2e}")

    return model
