import math
import os
import sys

import torch

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from eml_mcp.regression import EMLMasterTree, train_eml_tree


def simulated_perception_nn(mse_val: float):
    """
    Mocks a Perception NN that evaluates the fit.
    Returns simulated probabilities.
    """
    # If MSE is low, we don't need more depth, and we're good.
    if mse_val < 0.1:
        return {"needs_more_depth": 0.05, "is_scaling_error": 0.1, "mse_is_low": 0.95}
    elif mse_val < 5.0:
        return {
            "needs_more_depth": 0.4,
            "is_scaling_error": 0.8,  # Likely just off by a constant
            "mse_is_low": 0.3,
        }
    else:
        return {"needs_more_depth": 0.95, "is_scaling_error": 0.2, "mse_is_low": 0.01}


def run_mor_loop():
    print("Starting EML MoR Residual Composition Prototype")

    # Generate Target Data
    # Let's try to fit f(x) = x**2 + x
    x_real = torch.linspace(-2, 2, 100, dtype=torch.float64)
    x = torch.complex(x_real, torch.zeros_like(x_real))
    target_values = x**2 + x

    variables = {"x": x}
    formulas = {"x": "x"}

    max_steps = 4

    for step in range(1, max_steps + 1):
        print(f"\n--- MoR Step {step} ---")
        print(f"Available variables: {list(variables.keys())}")

        # Train a depth=1 block treating all current variables as inputs
        # We limit epochs for the prototype
        epochs = 1000

        # We need a new tree for each step
        var_names = list(variables.keys())
        model = EMLMasterTree(depth=1, variable_names=var_names)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.05)

        best_loss = float("inf")
        best_output = None

        for epoch in range(epochs):
            # temp schedule
            temp = max(0.01, 1.0 * (0.999**epoch))
            optimizer.zero_grad()
            output = model(variables, temperature=temp)

            # Simple MSE
            diff = output - target_values
            loss = (diff.real**2).mean() + (diff.imag**2).mean()

            if torch.isnan(loss) or torch.isinf(loss):
                break

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            optimizer.step()

            if loss.item() < best_loss:
                best_loss = loss.item()
                best_output = output.detach().clone()

        # Final formula for this step
        step_formula_raw = model.get_discrete_formula()

        # Substitute var names back into the formula string
        step_formula = step_formula_raw
        for var_name, var_expr in sorted(
            formulas.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if var_name != "x":
                # Replace exact whole words (simplified for prototype)
                step_formula = step_formula.replace(var_name, f"[{var_expr}]")

        print(f"Step {step} Best MSE: {best_loss:.4f}")
        print(f"Raw Discrete Formula: {step_formula_raw}")
        print(f"Composed Formula: {step_formula}")

        # Evaluate using Perception NN
        nn_outputs = simulated_perception_nn(best_loss)
        print(f"Perception NN Outputs: {nn_outputs}")

        # In a real run, Hybrid-AI MCP would evaluate these outputs.
        # Let's mock the decision rule here based on our MCP weights:
        # Rule: [-1.0, 1.5, -0.6] acting on [1.0, mse_is_low, is_scaling_error]
        score = (
            -1.0 + 1.5 * nn_outputs["mse_is_low"] - 0.6 * nn_outputs["is_scaling_error"]
        )
        fired = score >= 1.0

        print(
            f"Hybrid-AI MCP Halt Rule Score: {score:.2f} (Threshold 1.0) -> Fired: {fired}"
        )

        if fired:
            print(f"** Success! MoR Loop Halted via Hybrid-AI Gate at step {step} **")
            break

        print("-> Continuing to next recursion step. Wrapping residual.")
        # Add new variable
        new_var_name = f"h_{step}"
        variables[new_var_name] = best_output
        formulas[new_var_name] = step_formula_raw


if __name__ == "__main__":
    run_mor_loop()
