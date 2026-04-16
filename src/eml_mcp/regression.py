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

        n_vars = len(self.variable_names)
        n_consts = len(self.constants)
        total = n_vars + n_consts

        # Initialize logits such that constant 1.0 is favored initially.
        # This prevents the tree from starting with 'x' which leads to rapid divergence.
        # 1.0 is usually index n_vars (first constant)
        self.selection_logits = nn.Parameter(torch.zeros(total))
        with torch.no_grad():
            if n_consts > 0:
                # Set logit for 1.0 to a higher value if it exists
                try:
                    one_idx = self.constants.index(1.0)
                    self.selection_logits[n_vars + one_idx] = 10.0
                except ValueError:
                    pass

    def forward(self, variables: dict[str, Tensor], temperature: float = 1.0) -> Tensor:
        """Compute the weighted combination of inputs."""
        probs = torch.softmax(self.selection_logits / (temperature + 1e-8), dim=0).to(
            torch.complex128
        )

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
                # Check for small integers
                if math.isfinite(c) and abs(c - round(c)) < 1e-9:
                    return str(int(round(c)))
                return str(c)


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

        # Soft clamping for stability while allowing large values
        # We use a threshold of 20.0 for exp(x), as exp(20) is 4.8e8,
        # which is safe for multiple compositions.
        threshold = 20.0
        x_real = x.real

        # Smoothly clamp large real values to prevent inf/nan
        # x_clamped = x in [-threshold, threshold]
        # uses tanh for soft saturation outside range
        x_real_stable = torch.clamp(x_real, min=-threshold, max=threshold)
        # Apply a small residual for values outside the clamp to maintain gradients
        x_real_stable = x_real_stable + 0.01 * (x_real - x_real_stable)

        exp_x = torch.exp(torch.complex(x_real_stable, x.imag))

        # Safe complex log: ensure y is not too close to zero
        # y = exp(x) - ln(y')
        y_mag = y.abs().clamp(min=1e-12, max=1e30)
        y_real = y.real
        y_imag = y.imag

        # Stabilize atan2 gradient near origin
        is_near_origin = (y_real.abs() < 1e-15) & (y_imag.abs() < 1e-15)
        y_real_safe = torch.where(is_near_origin, y_real + 1e-15, y_real)
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
        loss = F.huber_loss(output.real, target_values.real, delta=1.0) + F.huber_loss(
            output.imag, target_values.imag, delta=1.0
        )

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


def simulated_perception_nn(mse_val: float) -> dict[str, float]:
    """
    Simulation of the MoR Perception NN that predicts if more depth is needed.
    """
    if mse_val < 0.1:
        return {"needs_more_depth": 0.05, "is_scaling_error": 0.1, "mse_is_low": 0.95}
    elif mse_val < 5.0:
        return {"needs_more_depth": 0.4, "is_scaling_error": 0.8, "mse_is_low": 0.3}
    else:
        return {"needs_more_depth": 0.95, "is_scaling_error": 0.2, "mse_is_low": 0.01}


def mcculloch_pitts_gate(nn_outputs: dict[str, float], threshold: float = 0.5) -> bool:
    """
    Hybrid-AI MCP gate function, replicating mor_halt_rule_v2.
    Weights: [-1.0, -0.5, 2.0, -1.5] for [bias, is_scaling_error, mse_is_low, needs_more_depth]
    """
    # Convert probabilities to binary using threshold
    binary_inputs = {k: 1.0 if v >= threshold else 0.0 for k, v in nn_outputs.items()}

    score = (
        -1.0
        - 0.5 * binary_inputs["is_scaling_error"]
        + 2.0 * binary_inputs["mse_is_low"]
        - 1.5 * binary_inputs["needs_more_depth"]
    )
    return score >= 1.0


def mor_symbolic_regression_loop(
    target_expression: str,
    target_data: dict[str, Tensor],
    target_values: Tensor,
    max_steps: int = 5,
    epochs_per_step: int = 1000,
    lr: float = 0.01,
) -> tuple[str, float]:
    """
    Mixture-of-Recursions (MoR) loop with Hybrid-AI gating.
    Trains depth=1 blocks iteratively, wrapping residuals.
    """
    variables = {k: v.clone() for k, v in target_data.items()}
    formulas = {k: k for k in target_data.keys()}

    best_final_mse = float("inf")
    best_composed_formula = ""

    for step in range(1, max_steps + 1):
        # We always train a shallow depth block
        model = train_eml_tree(
            target_data=variables,
            target_values=target_values,
            depth=1,  # MoR shared block depth
            epochs=epochs_per_step,
            lr=lr,
        )

        # Get MSE
        with torch.no_grad():
            output = model(variables, temperature=0.01)
            diff = output - target_values
            mse = ((diff.real**2).mean() + (diff.imag**2).mean()).item()

        step_formula_raw = model.get_discrete_formula()

        # Substitute recursive variable formulas back
        step_formula = step_formula_raw
        for var_name, var_expr in sorted(
            formulas.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if var_name != "x":
                step_formula = step_formula.replace(var_name, f"{var_expr}")

        best_final_mse = mse
        best_composed_formula = step_formula

        # 1. Perception NN evaluates
        nn_outputs = simulated_perception_nn(mse)

        # 2. Hybrid-AI gating logic
        halt = mcculloch_pitts_gate(nn_outputs, threshold=0.5)

        if halt:
            break

        # Continue recursion: wrap current output as a new intermediate variable
        new_var_name = f"h_{step}"
        variables[new_var_name] = output.detach().clone()
        formulas[new_var_name] = step_formula_raw

    return best_composed_formula, best_final_mse
