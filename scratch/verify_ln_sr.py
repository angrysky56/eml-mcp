
import torch
import torch.nn as nn
import torch.nn.functional as F
from eml_mcp.regression import train_eml_tree, EMLMasterTree
import math

def test_regression_ln():
    print("Testing regression for ln(x)...")
    # Avoid values near zero for ln(x) for stability
    x = torch.linspace(1.5, 4.0, 10, dtype=torch.complex128)
    y_target = torch.log(x)
    target_data = {"x": x}
    
    # ln(x) = eml(1, eml(eml(1, x), 1)) — depth 3
    # We'll use depth 3
    model = train_eml_tree(target_data, y_target, depth=3, epochs=2000, lr=0.01)
    formula = model.get_discrete_formula()
    print(f"Recovered: {formula}")
    
    # Verify values
    from eml_mcp.compiler import EMLCompiler
    from eml_mcp.database import EMLFormulaDB
    import os
    if os.path.exists("eml_formulas_test.db"):
        os.remove("eml_formulas_test.db")
        
    db = EMLFormulaDB("eml_formulas_test.db")
    compiler = EMLCompiler(db)
    
    # Try to compile the recovered formula
    try:
        recovered_tree = compiler.compile(formula)
        
        errors = []
        for val in x:
            res = recovered_tree.evaluate({"x": complex(val)})
            errors.append(abs(res - complex(torch.log(val))))
        
        avg_error = sum(errors) / len(errors)
        print(f"Average Error: {avg_error:.2e}")
        if avg_error < 1e-6:
            print("Success!")
        else:
            print(f"Average error: {avg_error}")
    except Exception as e:
        print(f"Compilation failed for '{formula}': {e}")
    finally:
        db.close()
        if os.path.exists("eml_formulas_test.db"):
            os.remove("eml_formulas_test.db")

if __name__ == "__main__":
    test_regression_ln()
