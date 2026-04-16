
from eml_mcp.database import EMLFormulaDB
from eml_mcp.compiler import EMLCompiler
import json

db = EMLFormulaDB("eml_formulas.db")
compiler = EMLCompiler(db)
try:
    tree = compiler.compile("exp(exp(x))")
    print("SUCCESS: Compiled exp(exp(x))")
    print(f"Tree: {tree.to_expression()}")
except Exception as e:
    print(f"FAILURE: {e}")
db.close()
