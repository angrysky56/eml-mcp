# Phase 12: Research - Multi-Variable Sheffer Discovery

## Multi-Variable EML (mEML)
The Sheffer operator `eml(x, y) = exp(x) - ln(y)` is universal for all elementary functions. While univariate functions like `sin(x)` or `exp(exp(x))` are straightforward trees, multi-variable operations like `x + y` require sampling multiple variables simultaneously to distinguish them from univariate approximations that might fit on a single dimension.

### Addition Formula
Mathematical identity for addition using `exp` and `ln`:
`x + y = ln(exp(x) + exp(y))`? No, that's LogSumExp.
`x + y = x + y` is trivial if we have variables.
The question is how to get `x + y` from `eml(x, y)`.

In the paper "Decomposition of Elementary Functions into a Single Sheffer Operator", addition is derived as:
`add(x, y) = eml(x, 1/exp(exp(y)))`? 
Wait, `eml(x, y) = exp(x) - ln(y)`.
If I want `exp(x) + ...`
`exp(x) - ln(exp(-y))` = `exp(x) - (-y)` = `exp(x) + y`.
This is still univariate in `exp(x)`.

Actually, to get `x + y`:
`ln(exp(x+y))`
`x+y` is what we want.

The engine needs to find the tree that represents the mapping `(x, y) -> x + y`.
If it picks `add` from the DB, it already has it. But I want it to *discover* it if it wasn't there.

### Sampling Strategy
To distinguish `f(x, y)` from `g(x)`, we must sample points `(x_i, y_i)` where `y_i` is not a fixed function of `x_i`.
Current strategy: `y = x * 1.1 + 0.1` is a linear mapping, which can cause spurious matches if the target also has linear relationships.

Proposed: Monte Carlo sampling in $[0.1, 2.5]^N$ or a fixed grid.
For 10 test points, we can use 10 random tuples.

## Variable Detection
Using `ast.NodeVisitor` to find `ast.Name` nodes:
```python
class VarDetector(ast.NodeVisitor):
    def __init__(self):
        self.vars = set()
    def visit_Name(self, node):
        self.vars.add(node.id)
```
Exclude constants like `e`, `pi`, `j`.
