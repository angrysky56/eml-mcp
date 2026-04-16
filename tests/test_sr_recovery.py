"""
Test suite for EML Symbolic Regression recovery of exp(x).
"""

import pytest

torch = pytest.importorskip("torch")

from eml_mcp.regression import train_eml_tree  # noqa: E402


def test_recover_exp():
    """Verify that SR can recover the exp(x) identity (depth 1)."""
    print("\nTesting Symbolic Regression recovery of exp(x)...")

    # Generate data for exp(x)
    x = torch.linspace(0.1, 2.0, 20, dtype=torch.complex128)
    y_target = torch.exp(x)

    target_data = {"x": x}

    # Train a depth-1 tree
    model = train_eml_tree(target_data, y_target, depth=1, epochs=3000, lr=0.1)

    formula = model.get_formula()
    print(f"Final Formula: {formula}")

    # exp(x) = eml(x, 1) or eml(x, 1.0)
    assert "eml(x, 1)" in formula or "eml(x, 1.0)" in formula


if __name__ == "__main__":
    test_recover_exp()
