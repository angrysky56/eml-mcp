import pytest

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine


@pytest.fixture
def memory_db():
    # Use memory database to avoid polluting the file DB during tests
    db = EMLFormulaDB(":memory:")
    yield db
    db.close()


def test_discovery_engine_initializes(memory_db):
    engine = DiscoveryEngine(memory_db)
    assert len(engine.test_points) == 6


def test_discovery_composition(memory_db):
    engine = DiscoveryEngine(memory_db)

    # Generate random composition
    tree, details = engine.generate_random_composition()
    assert tree is not None
    assert "base" in details
    assert "substitutions" in details
    assert tree.node_count >= 1


def test_discovery_explore_finds_novel_formulas(memory_db):
    engine = DiscoveryEngine(memory_db)

    formulas_before = len(memory_db.list_formulas())

    # Patch random to increase determinism:
    # Force a 100% substitution rate for reproducible novelty,
    # but we can just run a few iterations.
    discovered = engine.explore(iterations=10)

    formulas_after = len(memory_db.list_formulas())
    assert formulas_after == formulas_before + len(discovered)

    if discovered:
        # If it discovered something, verify the details
        for name in discovered:
            assert name.startswith("discovered_")
            formula = memory_db.get_formula(name)
            assert formula is not None
            assert formula["note"] == "Novelty Search emergent formula."

            # Check derivations
            derivations = memory_db.get_derivations(name)
            assert len(derivations) == 1
            assert derivations[0]["method"] == "composition"


def test_discovery_find_target(memory_db):
    engine = DiscoveryEngine(memory_db)

    import cmath

    # 1. Target evaluating exactly to exp(x)
    def target_evaluator(x):
        return cmath.exp(x)

    result = engine.find_target(target_evaluator, max_iterations=5, top_n=2)

    # Should find exact match because "exp" is seeded in the DB
    assert result["exact_match"] is not None
    assert result["exact_match"]["name"] == "exp"
    assert result["exact_match"]["mse"] < 1e-10

    # 2. Target evaluating to a weird function that won't match exactly
    def weird_evaluator(x):
        return x * x * x + 100.0

    # Increase iteration slightly to ensure some generation happens
    result_weird = engine.find_target(weird_evaluator, max_iterations=20, top_n=3)

    assert result_weird["exact_match"] is None
    assert len(result_weird["nearby_discoveries"]) > 0

    # Check that nearby discoveries are sorted by MSE ascending
    mses = [match["mse"] for match in result_weird["nearby_discoveries"]]
    assert mses == sorted(mses)
    # Check that nearby discoveries are sorted by MSE ascending
    mses = [match["mse"] for match in result_weird["nearby_discoveries"]]
    assert mses == sorted(mses)


def test_find_matching_formula_by_outputs_hits_seeded(memory_db):
    """The dedup primitive should recognise a fresh tree whose signature
    matches an existing formula, and return that formula's name."""
    import json

    from eml_mcp.trees import EMLNode

    engine = DiscoveryEngine(memory_db)

    # Build a tree equivalent to `exp` and evaluate it on the standard points
    exp_row = memory_db.get_formula("exp")
    exp_tree = EMLNode.from_dict(json.loads(exp_row["tree_json"]))
    outputs = engine._eval_tree_safe(exp_tree)
    assert outputs is not None

    match = engine._find_matching_formula_by_outputs(outputs)
    assert match == "exp"


def test_find_matching_formula_by_outputs_rejects_unique(memory_db):
    """A signature not in the catalog should return None."""
    engine = DiscoveryEngine(memory_db)

    # Fabricate an output sequence unlikely to collide with any seeded formula
    unique = [complex(17.0 + i, -0.5 * i) for i in range(len(engine.test_points))]
    match = engine._find_matching_formula_by_outputs(unique)
    assert match is None


def test_find_target_is_idempotent_across_repeated_calls(memory_db):
    """Running the same target twice must not grow the catalog.

    This is the end-to-end contract for the dedup fix. Pre-fix, each call
    could mint a fresh `discovered_*` row for the same tree. Post-fix, the
    second call should see the first result and reuse it.
    """
    import cmath

    engine = DiscoveryEngine(memory_db)

    def target(x):
        return cmath.exp(x)

    baseline = len(memory_db.list_formulas())

    result1 = engine.find_target(target, max_iterations=5, top_n=1)
    assert result1["exact_match"] is not None
    count_after_first = len(memory_db.list_formulas())

    result2 = engine.find_target(target, max_iterations=5, top_n=1)
    assert result2["exact_match"] is not None
    count_after_second = len(memory_db.list_formulas())

    # Second call must not have inserted a new row
    assert count_after_second == count_after_first
    # And when reuse happened, the flag should report it honestly
    assert result2["exact_match"]["name"] == result1["exact_match"]["name"]
    assert result2["exact_match"]["reused_existing"] is True
    # Catalog shouldn't have grown beyond what seeds provide either
    assert count_after_second <= baseline + 1
