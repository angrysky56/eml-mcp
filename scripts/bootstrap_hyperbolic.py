import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode, const, var, eml_node

def derive_functions():
    db = EMLFormulaDB()
    
    add_row = db.get_formula("add", include_verification=False)
    sub_row = db.get_formula("subtract", include_verification=False)
    exp_row = db.get_formula("exp", include_verification=False)
    neg_row = db.get_formula("negate", include_verification=False)
    ln_row = db.get_formula("ln", include_verification=False)
    mul_row = db.get_formula("multiply", include_verification=False)
    recip_row = db.get_formula("reciprocal", include_verification=False)
    
    import json
    def load_tree(row):
        if row is None: return None
        return EMLNode.from_dict(json.loads(row["tree_json"])) if type(row["tree_json"]) is str else EMLNode.from_dict(row["tree_json"])

    add_tree = load_tree(add_row)
    sub_tree = load_tree(sub_row)
    exp_tree = load_tree(exp_row)
    neg_tree = load_tree(neg_row)
    ln_tree = load_tree(ln_row)
    mul_tree = load_tree(mul_row)
    recip_tree = load_tree(recip_row)
    
    x_var = var("x")
    y_var = var("y")
    
    # Re-create divide: multiply(x, reciprocal(y))
    div_tree = mul_tree.substitute({"x": x_var, "y": recip_tree.substitute({"x": y_var})})
    if not db.formula_exists("divide"):
        db.add_formula(
            name="divide",
            description="Division x / y = x * (1/y)",
            tree=div_tree,
            variables=["x", "y"],
            note="Systematically derived from multiply and reciprocal."
        )
        print("Restored divide")
    
    # exp(x)
    exp_x = exp_tree.substitute({"x": x_var})
    
    # exp(-x)
    neg_x = neg_tree.substitute({"x": x_var})
    exp_neg_x = exp_tree.substitute({"x": neg_x})
    
    # 2.0 const tree - we just use const(2.0)
    c_2 = const(2.0)
    
    # sinh(x) = (exp(x) - exp(-x)) / 2
    sub_exp = sub_tree.substitute({"x": exp_x, "y": exp_neg_x})
    sinh_tree = div_tree.substitute({"x": sub_exp, "y": c_2})
    
    if not db.formula_exists("sinh"):
        db.add_formula(
            name="sinh",
            description="Hyperbolic sine sinh(x)",
            tree=sinh_tree,
            variables=["x"],
            note="Systematically derived via EML identity: divide(subtract(exp(x), exp(negate(x))), 2.0)"
        )
        print("Added sinh")
    else:
        print("sinh exists")
        
    # cosh(x) = (exp(x) + exp(-x)) / 2
    add_exp = add_tree.substitute({"x": exp_x, "y": exp_neg_x})
    cosh_tree = div_tree.substitute({"x": add_exp, "y": c_2})
    
    if not db.formula_exists("cosh"):
        db.add_formula(
            name="cosh",
            description="Hyperbolic cosine cosh(x)",
            tree=cosh_tree,
            variables=["x"],
            note="Systematically derived via EML identity: divide(add(exp(x), exp(negate(x))), 2.0)"
        )
        print("Added cosh")
    else:
        print("cosh exists")
        
    # tanh(x) = sinh(x) / cosh(x)
    tanh_tree = div_tree.substitute({"x": sinh_tree, "y": cosh_tree})
    if not db.formula_exists("tanh"):
        db.add_formula(
            name="tanh",
            description="Hyperbolic tangent tanh(x)",
            tree=tanh_tree,
            variables=["x"],
            note="Systematically derived via EML identity: divide(sinh(x), cosh(x))"
        )
        print("Added tanh")
    else:
        print("tanh exists")
        
    # ln(ln(x))
    ln_ln_x = ln_tree.substitute({"x": ln_tree.substitute({"x": x_var})})
    if not db.formula_exists("ln_ln"):
        db.add_formula(
            name="ln_ln",
            description="Derived: ln(ln(x))",
            tree=ln_ln_x,
            variables=["x"],
            note="Systematically derived in Phase 7 bootstrapping."
        )
        print("Added ln_ln")
    else:
        print("ln_ln exists")

if __name__ == "__main__":
    derive_functions()
