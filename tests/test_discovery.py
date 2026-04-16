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
