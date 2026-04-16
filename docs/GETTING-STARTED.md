# Getting Started with EML-MCP

This guide will help you understand how to use `eml-mcp` tools within your MCP client environment (like Claude Desktop).

## What is EML?

EML stands for Exp-Minus-Log. It's a continuous Sheffer operator:
`eml(x, y) = exp(x) - ln(y)`

This single primitive operator, combined with the constant `1`, is mathematically capable of reproducing all standard elementary functions (addition, multiplication, sine, cosine, etc.).

## Using the Tools

Once configured, the MCP server exposes several tools you can utilize for advanced numeric reasoning.

### 1. `eml_list_formulas`
Ask the server what established formulas it already knows.
```json
{
  "eml_list_formulas": {}
}
```

### 2. `eml_evaluate`
Evaluate the foundational EML expression directly given numeric `x` and `y` conditions.

### 3. `eml_simplify`
Provide an unoptimized EML tree and apply equality saturation and pattern rewriting to retrieve the minimal structure.
For example, feeding it `eml(eml(1, eml(eml(1, x), 1)), 1)` reduces reliably back to `x` thanks to the integrated E-Graph!

### 4. `eml_discover`
Propose a target behavior using standard Python operators (e.g. `math.cos(x)`) to ask the Discovery Engine to synthesize an EML tree representation.

*Tip:* For complex targets, you might want to use `eml_discover_start` instead, which offloads the heavy evolutionary computation to the background. You can subsequently query `eml_discover_status` periodically.

## Symbolic Regression
If you are confident in your dataset mappings, you can request an AI optimization trace directly utilizing `eml_symbolic_regression`, which brings Gradient Descent down upon the discrete representation using an innovative Mixture-of-Recursions neural technique.
