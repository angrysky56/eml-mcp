"""
EML Compiler
============

Compiles human-readable mathematical expressions into EML trees.
Uses standard Python AST parsing and handles substitution into discovered formulas.
"""

import ast
import json

from eml_mcp.database import EMLFormulaDB
from eml_mcp.trees import EMLNode, const, var


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
            if isinstance(node.value, int | float):
                if node.value == 0:
                    formula = self.db.get_formula("zero")
                    if formula:
                        tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
                        return tree.copy()
                    raise ValueError("Formula 'zero' not found in DB")
                elif node.value == 1:
                    return const(1.0)
                else:
                    raise ValueError(
                        f"Constant {node.value} not natively supported without derivation"
                    )
            raise ValueError(f"Unsupported constant: {node.value}")

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are supported")

            func_name = node.func.id
            args = [self._visit(arg) for arg in node.args]

            formula = self.db.get_formula(func_name)
            if not formula:
                raise ValueError(f"Unknown function: {func_name}")

            tree = EMLNode.from_dict(json.loads(formula["tree_json"]))

            if len(args) == 1:
                return tree.substitute({"x": args[0]})
            elif len(args) == 2:
                return tree.substitute({"x": args[0], "y": args[1]})
            else:
                raise ValueError(
                    f"Unsupported number of arguments for {func_name}: {len(args)}"
                )

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
                    f"Operator '{op_name}' not found in DB. Must be discovered first."
                )

            tree = EMLNode.from_dict(json.loads(formula["tree_json"]))
            return tree.substitute({"x": left, "y": right})

        raise ValueError(f"Unsupported AST node: {type(node)}")
