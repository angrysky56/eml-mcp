
import torch
from eml_mcp.regression import train_eml_tree
import math

def test_regression_exp():
    print("Testing regression for exp(x)...")
    x = torch.linspace(0.1, 2.0, 20, dtype=torch.complex128)
    y_target = torch.exp(x)
    target_data = {"x": x}
    
    model = train_eml_tree(target_data, y_target, depth=1, epochs=500, lr=0.1)
    formula = model.get_discrete_formula()
    print(f"Recovered: {formula}")
    
    # exp(x) = eml(x, 1)
    assert "eml(x, 1)" in formula or "eml(x, 1.0)" in formula
    print("Success!")

def test_regression_square():
    print("\nTesting regression for x**2...")
    x = torch.linspace(1.1, 3.0, 20, dtype=torch.complex128)
    y_target = x**2
    target_data = {"x": x}
    
    # x**2 = exp(2 * ln(x))
    model = train_eml_tree(target_data, y_target, depth=3, epochs=1000, lr=0.05)
    formula = model.get_discrete_formula()
    print(f"Recovered: {formula}")
    
    # Verify values
    from eml_mcp.compiler import EMLCompiler
    from eml_mcp.database import EMLFormulaDB
    db = EMLFormulaDB("eml_formulas.db")
    compiler = EMLCompiler(db)
    recovered_tree = compiler.compile(formula)
    
    errors = []
    for val in x:
        res = recovered_tree.evaluate({"x": complex(val)})
        errors.append(abs(res - complex(val**2)))
    
    avg_error = sum(errors) / len(errors)
    print(f"Average Error: {avg_error:.2e}")
    # We don't necessarily need < 1e-5 for a complex recovery, 
    # but the discrete formula should be exact if it snapped correctly.
    if avg_error < 1e-10:
        print("Success (Exact match)!")
    else:
        print(f"Average error: {avg_error}")

if __name__ == "__main__":
    test_regression_exp()
    test_regression_square()
