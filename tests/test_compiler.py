import pytest

from eml_mcp.compiler import EMLCompiler
from eml_mcp.trees import NodeType


def test_compiler_basic_constants():
    compiler = EMLCompiler()

    node = compiler.compile("1")
    assert node.node_type == NodeType.CONST
    assert node.value == 1.0

    node = compiler.compile("0")
    # 'zero' is built into seed formulas
    assert node.node_type == NodeType.EML
    assert node.evaluate() == 0.0


def test_compiler_variables():
    compiler = EMLCompiler()

    node = compiler.compile("x")
    assert node.node_type == NodeType.VAR
    assert node.var_name == "x"


def test_compiler_basic_functions():
    compiler = EMLCompiler()

    # "exp(x)" is a known seed formula
    node = compiler.compile("exp(x)")
    assert node.node_type == NodeType.EML
    # Since exp(x) is composed, the root is eml, etc.
    # Just evaluating it at 0 to check if it's exp
    assert abs(node.evaluate({"x": 0.0}) - 1.0) < 1e-10


def test_compiler_composition():
    compiler = EMLCompiler()

    node = compiler.compile("exp(ln(x))")
    assert node.node_type == NodeType.EML
    assert abs(node.evaluate({"x": 2.0}) - 2.0) < 1e-10


def test_compiler_invalid_syntax():
    compiler = EMLCompiler()
    with pytest.raises(ValueError, match="Syntax error"):
        compiler.compile("x + ")


def test_compiler_unknown_function():
    compiler = EMLCompiler()
    with pytest.raises(ValueError, match="Unknown function 'unknown'"):
        compiler.compile("unknown(x)")


def test_compiler_unknown_operator():
    compiler = EMLCompiler()
    # The default DB does not have an 'pow' operator yet
    with pytest.raises(ValueError, match="Operator 'pow' is not yet in the database"):
        compiler.compile("x ** y")
