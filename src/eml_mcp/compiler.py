"""
EML Compiler
============

Compiles human-readable mathematical expressions into EML trees.
Uses standard Python AST parsing and handles substitution into discovered formulas.
"""

import ast
import json

from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode, NodeType, const, var


class EMLCompiler:
    """Compiles human-readable mathematical expressions into EML trees."""

    def __init__(self, db: EMLFormulaDB | None = None):
        self.db = db or EMLFormulaDB()

    def compile(self, expression: str) -> EMLNode:
        """Compile a math expression string to an EMLNode tree.

        Args:
            expression: String like 'exp(x)' or 'ln(y) + 1'

        Returns:
            An EMLNode tree representing the composed expression.
        """
        # Parse expression securely as an AST expression
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Syntax error in expression: {e}") from e

        return self._visit(tree.body)

    def _visit(self, node: ast.AST) -> EMLNode:
        if isinstance(node, ast.Name):
            if node.id == "e":
                formula = self.db.get_formula("e")
                if not formula:
                    raise ValueError("Formula 'e' not found in DB")
                tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
                return tree.copy()
            return var(node.id)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, complex)):
                if node.value == 0:
                    formula = self.db.get_formula("zero")
                    if formula:
                        tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
                        return tree.copy()
                    # Fallback if 'zero' not in DB yet
                    return const(0.0)
                return const(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are supported")

            func_name = node.func.id
            args = [self._visit(arg) for arg in node.args]

            if func_name == "eml":
                if len(args) != 2:
                    raise ValueError(f"eml() requires 2 arguments, got {len(args)}")
                return EMLNode(node_type=NodeType.EML, left=args[0], right=args[1])

            formula = self.db.get_formula(func_name)
            if not formula:
                raise ValueError(
                    f"Unknown function {func_name!r}. The compiler can only use functions "
                    f"already registered in the database (currently: seeds + prior discoveries). "
                    f"To derive an EML form for it first, run: "
                    f"eml_discover(target_expression='math.{func_name}(x)')"
                )

            tree = EMLNode.from_dict(json.loads(formula["tree_json"]))

            if len(args) == 1:
                return tree.substitute({"x": args[0]})
            elif len(args) == 2:
                return tree.substitute({"x": args[0], "y": args[1]})
            else:
                raise ValueError(f"Unsupported number of arguments for {func_name}: {len(args)}")

        elif isinstance(node, ast.BinOp):
            left = self._visit(node.left)
            right = self._visit(node.right)

            if isinstance(node.op, ast.Add):
                op_name = "add"
            elif isinstance(node.op, ast.Sub):
                op_name = "subtract"
            elif isinstance(node.op, ast.Mult):
                op_name = "multiply"
            elif isinstance(node.op, ast.Div):
                op_name = "divide"
            elif isinstance(node.op, ast.Pow):
                op_name = "pow"
            else:
                raise ValueError(f"Unsupported binary operator: {type(node.op)}")

            formula = self.db.get_formula(op_name)
            if not formula:
                raise ValueError(
                    f"Operator {op_name!r} is not yet in the database. "
                    f"Seeded operators are: add, subtract, multiply. For others "
                    f"(e.g. divide, pow), run: "
                    f"eml_discover(target_expression='x / y')  # or 'x**y', etc."
                )

            tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
            return tree.substitute({"x": left, "y": right})

        elif isinstance(node, ast.UnaryOp):
            operand = self._visit(node.operand)
            if isinstance(node.op, ast.USub):
                op_name = "negate"
            else:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")

            formula = self.db.get_formula(op_name)
            if not formula:
                raise ValueError(
                    f"Unary operator {op_name!r} is not yet in the database. "
                    "Ensure 'negate' is registered."
                )

            tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
            return tree.substitute({"x": operand})

        raise ValueError(f"Unsupported AST node: {type(node)}")
