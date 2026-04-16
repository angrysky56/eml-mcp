import json
from eml_mcp.database import EMLFormulaDB, deserialize_signature
from eml_mcp.discovery import DiscoveryEngine
from eml_mcp.primitives import TEST_POINTS
from eml_mcp.trees import EMLNode

def test_phase6():
    db = EMLFormulaDB("test_p6.db")
    engine = DiscoveryEngine(db)
    
    # 1. Check if seed formulas have signatures
    formulas = db.list_formulas()
    print(f"Loaded {len(formulas)} formulas.")
    
    for f in formulas:
        sig = deserialize_signature(f.get("signature"))
        if sig:
            print(f"Formula '{f['name']}' has signature: {len(sig)} points.")
        else:
            print(f"Formula '{f['name']}' is MISSING signature!")
            # Manually trigger add to fix it if it was added before the change
            tree = EMLNode.from_dict(json.loads(f["tree_json"]))
            vars = json.loads(f["variables"])
            # This should now populate it
            db.conn.execute("DELETE FROM formulas WHERE name = ?", (f["name"],))
            db.add_formula(f["name"], f["description"], tree, vars)
            updated = db.get_formula(f["name"])
            updated_sig = deserialize_signature(updated.get("signature"))
            print(f"  Fixed! New signature: {len(updated_sig) if updated_sig else 'NONE'}")

    # 2. Test targeted discovery with TED ranking
    print("\nTesting targeted discovery for 'exp(x)'...")
    target = "exp(x)"
    results = engine.find_target(target_expression=target, max_iterations=20)
    
    print(f"Exact match: {results['exact_match']['name'] if results['exact_match'] else 'NONE'}")
    print("\nNearby results:")
    for m in results["nearby_discoveries"]:
        ted = m.get("ted", "N/A")
        print(f" - {m['name']}: MSE={m['mse']:.2e}, TED={ted}, Expr={m['expression']}")

    # 3. Verify novelty search uses signatures (cache sync check)
    print("\nTesting novelty check cache...")
    # exp(x) should NOT be novel
    exp_tree = EMLNode.from_dict(json.loads(formulas[0]["tree_json"])) # Assuming exp is 0
    # Find exp
    for f in formulas:
        if f["name"] == "exp":
            exp_tree = EMLNode.from_dict(json.loads(f["tree_json"]))
            break

    is_novel = engine.is_novel_and_stable(exp_tree)
    print(f"Is 'exp(x)' novel? {is_novel} (Expect False)")
    
    db.close()

if __name__ == "__main__":
    test_phase6()
