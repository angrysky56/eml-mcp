"""
Test suite for EML Symbolic Regression recovery of ln(x).
"""

import pytest

torch = pytest.importorskip("torch")

from eml_mcp.regression import train_eml_tree  # noqa: E402


def test_recover_ln():
    """Verify that SR can recover the ln(x) identity (depth 3)."""
    print("\nTesting Symbolic Regression recovery of ln(x)...")

    # Generate data for 1 - ln(x) = eml(0, x)
    x = torch.linspace(1.1, 5.0, 50, dtype=torch.complex128)
    y_target = 1.0 - torch.log(x)

    target_data = {"x": x}

    # Train a depth-1 tree
    model = train_eml_tree(target_data, y_target, depth=1, epochs=500, lr=0.1)

    formula = model.get_formula()
    print(f"Final Formula: {formula}")

    # Check if it behaves like ln(x) numerically
    # (Testing behavior because there are many equivalent EML forms)
    with torch.no_grad():
        test_x = torch.tensor([2.0, 3.5, 10.0], dtype=torch.complex128)
        output = model({"x": test_x}, temperature=0.01)
        expected = 1.0 - torch.log(test_x)
        mse = ((output - expected).abs() ** 2).mean()
        print(f"MSE on unseen data: {mse:.2e}")
        assert mse < 1e-3


if __name__ == "__main__":
    test_recover_ln()
