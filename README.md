# EML MCP Server

A Model Context Protocol server implementing the **EML (Exp-Minus-Log) operator** — a single binary function that generates all standard elementary functions.

```
eml(x, y) = exp(x) - ln(y)
```

Paired with the constant `1`, this operator reconstructs arithmetic, all transcendental functions, and constants including `e`, `π`, and `i`. It is the continuous-domain analogue of the NAND gate for Boolean logic.

**Based on:** Odrzywołek (2026), "All elementary functions from a single operator" — [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

## Quick Start

```json
{
  "mcpServers": {
    "eml-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/eml-mcp", "run", "server.py"]
    }
  }
}
```

```bash
cd eml-mcp
uv venv --python 3.12 --seed
source .venv/bin/activate
uv sync
```


## Tools

| Tool | Description |
|------|-------------|
| `eml_evaluate` | Evaluate eml(x, y) = exp(x) - ln(y) on given inputs |
| `eml_list_formulas` | List all known EML decompositions (exp, ln, e, zero) |
| `eml_tree_info` | Inspect a formula's full tree structure, RPN code, and optionally evaluate |
| `eml_compile` | Convert elementary expressions to pure EML form |
| `eml_verify` | Verify an EML tree against its reference function using transcendental test points |
| `eml_master_tree` | Build parameterized master formula trees for symbolic regression |

## Resources

| URI | Description |
|-----|-------------|
| `eml://grammar` | The EML context-free grammar and key identities |
| `eml://complexity-table` | Kolmogorov complexity (K) of functions in EML representation |

## Key Concepts

**Grammar:** `S → 1 | eml(S, S)` — every elementary expression is a binary tree of identical nodes.

**Examples:**
- `e = eml(1, 1)` — depth 1, K=3
- `exp(x) = eml(x, 1)` — depth 1, K=3
- `ln(x) = eml(1, eml(eml(1, x), 1))` — depth 3, K=7

**Symbolic Regression:** Master formula trees are parameterized EML circuits optimized via Adam. When the generating law is elementary, trained weights snap to exact closed-form expressions (MSE ~ 1e-32).

## Architecture

```
eml_core.py    — EML operator, binary tree structures, known formulas, verification
server.py      — FastMCP server exposing tools and resources
```

The core engine uses `complex128` throughout — trigonometric functions and π require complex intermediates via Euler's formula. Works cleanly with NumPy and PyTorch.

## Related

- [SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage) — Odrzywołek's original EML toolkit
- [hybrid-ai-mcp](../hybrid-ai-mcp) — Boolean-domain companion (McCulloch-Pitts neurons, NAND logic)
- [mcp-logic](https://github.com/angrysky56) — Automated reasoning server for verifying EML identities

## License

MIT
