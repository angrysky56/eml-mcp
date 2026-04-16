"""
Tests for the SQLite persistence layer (EMLFormulaDB).
"""

import json
import os

import pytest

from eml_mcp.database import EMLFormulaDB
from eml_mcp.registry import SEED_FORMULAS
from eml_mcp.trees import EMLNode, const, eml_node, var

TEST_DB_PATH = "test_eml_formulas.db"


@pytest.fixture
def db():
    """Fixture to provide a clean test database."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    db_instance = EMLFormulaDB(db_path=TEST_DB_PATH)
    yield db_instance

    # Clean up after tests
    if os.path.exists(TEST_DB_PATH):
        db_instance.close()
        os.remove(TEST_DB_PATH)


def test_db_initialization_and_seeding(db):
    """Verify that the database is initialized with seed formulas."""
    formulas = db.list_formulas()
    # Should have at least the 8 seed formulas
    assert len(formulas) >= 8

    names = [f["name"] for f in formulas]
    for seed_name in SEED_FORMULAS:
        assert seed_name in names


def test_add_and_get_formula(db):
    """Test adding a custom formula and retrieving it."""
    # Create a simple tree: exp(exp(x))
    x_var = var("x")
    inside = eml_node(x_var, const(1.0))
    root = eml_node(inside, const(1.0))

    db.add_formula(name="exp_exp", description="Double exponential", tree=root, variables=["x"])

    formula = db.get_formula("exp_exp")
    assert formula is not None
    assert formula["name"] == "exp_exp"
    assert formula["description"] == "Double exponential"

    # Verify tree reconstruction
    reconstructed_tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
    assert reconstructed_tree.node_count == root.node_count
    assert reconstructed_tree.depth == root.depth

    # Numerical check
    val = 0.5
    assert abs(reconstructed_tree.evaluate({"x": val}) - root.evaluate({"x": val})) < 1e-10


def test_search_formulas(db):
    """Test searching for formulas by keyword."""
    # Seed data usually has 'exponential' in description for 'exp'
    results = db.search_formulas("exp")
    names = [r["name"] for r in results]
    assert "exp" in names


def test_add_verification(db):
    """Test adding verification results."""
    db.add_verification(
        formula_name="exp",
        passed=True,
        max_error=1.23e-15,
        tolerance=1e-10,
        n_tests=5,
        details=[{"point": 1.0, "error": 0.0}],
    )

    # get_formula should now include latest_verification fields
    formula = db.get_formula("exp")
    assert formula["verification_passed"] == 1
    assert formula["max_error"] == 1.23e-15
    assert "latest_verification" in formula


def test_add_derivation(db):
    """Test adding a derivation record."""
    db.add_derivation(
        formula_name="exp",
        parent_a=None,
        parent_b=None,
        method="seed",
        details={"source": "arXiv:2603.21852v2"},
    )

    derivations = db.get_derivations("exp")
    assert len(derivations) > 0
    # The last one added should have our details
    last_derivation = derivations[-1]
    assert last_derivation["method"] == "seed"
    assert "arXiv" in last_derivation["details"]
