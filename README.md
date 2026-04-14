# EML MCP Server

A Model Context Protocol server implementing the **EML (Exp-Minus-Log) operator** — a single binary function that generates all standard elementary functions.

```
eml(x, y) = exp(x) - ln(y)
```

Paired with the constant `1`, this operator reconstructs arithmetic, all transcendental functions, and constants including `e`, `π`, and `i`. It is the continuous-domain analogue of the NAND gate for Boolean logic.

**Based on:** Odrzywołek (2026), _"All elementary functions from a single operator"_ — [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)

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

## Core Idea

Every elementary function — exp, ln, sin, cos, addition, multiplication, powers, roots — can be expressed as a binary tree where:

- Every internal node computes `eml(left, right) = exp(left) - ln(right)`
- Every leaf is either the constant `1` or an input variable `x`

The grammar is: **`S → 1 | x | eml(S, S)`**

This is the continuous analogue of how every Boolean function reduces to NAND gates.

### Examples

```
e       = eml(1, 1)                           depth 1,  K=3
exp(x)  = eml(x, 1)                           depth 1,  K=3
ln(x)   = eml(1, eml(eml(1, x), 1))           depth 3,  K=7
x - y   = eml(ln(x), exp(y))                  depth 4,  K=11
x × y   = exp(ln(x) + ln(y))                  depth 10, K=41
```

## Complexity Metric (K)

The server reports **K** — the Kolmogorov complexity of each formula, defined as the **total node count** (internal EML nodes + leaf terminals) in the tree. This matches the paper's definition: for a full binary tree with _L_ leaves, K = 2L − 1.

The server also reports **leaf_count** — the number of terminal nodes only. Both metrics are useful:

- **K** (node count) — directly comparable to the paper's Table 4
- **leaf_count** — counts the `1`'s and variables, useful for understanding tree structure

### Our Trees vs. the Paper

Our compiler uses a **compositional approach** (build subtraction from ln + exp, build addition from subtraction + negation, etc.) which follows a different path than the paper's `VerifyBaseSet` bootstrapping procedure. The paper also reports results from exhaustive **direct search** (brute-force enumeration of all trees up to size N). Three values are worth tracking:

| Formula | Our K | Paper Compiler K | Paper Direct Search K | Notes                              |
| ------- | ----: | ---------------: | --------------------: | ---------------------------------- |
| exp(x)  |     3 |                3 |                     3 | All agree — optimal                |
| e       |     3 |                3 |                     3 | All agree — optimal                |
| ln(x)   |     7 |                7 |                     7 | All agree — optimal                |
| 0       |     7 |                7 |                     7 | All agree — optimal                |
| x − y   |    11 |               83 |                    11 | We match the direct search optimum |
| −x      |    17 |               57 |                    15 | 2 nodes above optimum              |
| x + y   |    27 |               27 |                    19 | Matches paper compiler             |
| x × y   |    41 |               41 |                    17 | Matches paper compiler             |

**Key takeaway:** For simple primitives (exp, ln, e, zero) all methods agree. For arithmetic, our compositional compiler sometimes finds the optimal tree (subtract), sometimes matches the paper's compiler (add, multiply), and is always far better than nothing. The gap between compiler K and direct search K shows the space for future optimization — the paper notes direct search as computationally expensive but producing significantly smaller trees.

## Tools

| Tool                | Description                                                                        |
| ------------------- | ---------------------------------------------------------------------------------- |
| `eml_evaluate`      | Evaluate `eml(x, y) = exp(x) - ln(y)` on given inputs                              |
| `eml_list_formulas` | List all known EML decompositions with K, depth, and expressions                   |
| `eml_tree_info`     | Inspect a formula's full tree structure, RPN code, and optionally evaluate         |
| `eml_compile`       | Convert elementary expressions to pure EML form                                    |
| `eml_verify`        | Verify an EML tree against its reference function using transcendental test points |
| `eml_master_tree`   | Build parameterized master formula trees for symbolic regression                   |

### Supported Formulas

The registry currently supports:

| Name       | Expression     | Aliases                 |
| ---------- | -------------- | ----------------------- |
| `exp`      | exp(x)         | `exp(x)`, `e^x`         |
| `e`        | Euler's number | `euler`                 |
| `ln`       | ln(x)          | `ln(x)`, `log(x)`       |
| `zero`     | 0              | `0`                     |
| `subtract` | x − y          | `x-y`, `x - y`          |
| `negate`   | −x             | `-x`, `neg(x)`          |
| `add`      | x + y          | `x+y`, `x + y`          |
| `multiply` | x × y          | `x*y`, `x * y`, `x × y` |

Compositions like `exp(exp(x))`, `ln(ln(x))`, `exp(ln(x))`, and `ln(exp(x))` are also supported via the compiler.

## Resources

| URI                      | Description                                     |
| ------------------------ | ----------------------------------------------- |
| `eml://grammar`          | The EML context-free grammar and key identities |
| `eml://complexity-table` | Full complexity table from the paper (Table 4)  |

## Use Cases

### 1. Symbolic Regression

The **master formula** at level _n_ is a complete binary tree of 2ⁿ EML nodes containing ALL elementary function expressions up to that depth. Train it with gradient descent:

```
Level 2: 14 parameters → 100% blind recovery
Level 3: 34 parameters → ~25% blind recovery
Level 5: 154 parameters → 100% from perturbed correct weights
```

When the generating law is elementary, trained weights snap from continuous values to exact 0/1 — bringing MSE to ~10⁻³² (machine epsilon squared). This is **interpretable AI**: the learned function has a closed-form expression.

### 2. Complexity Analysis

Measure the structural complexity of mathematical expressions on a uniform scale. EML's K provides a principled Kolmogorov-like complexity measure for elementary functions — the length of the shortest pure-EML program computing the function.

### 3. Verification

Verify symbolic identities numerically using algebraically independent transcendental test points (Euler-Mascheroni, Glaisher-Kinkelin constants). Under the Schanuel conjecture, coincidental agreement is vanishingly unlikely.

### 4. Cross-Domain Connections

EML is one instance of a **Minimal Generative Architecture (MGA)** — the same structural pattern (minimal primitives + recursion + boundary constraints = unbounded complexity) appears across:

| Domain               | Primitive      | Generates                          |
| -------------------- | -------------- | ---------------------------------- |
| Boolean logic        | NAND gate      | All logic circuits                 |
| Continuous math      | EML operator   | All elementary functions           |
| Evolutionary biology | 4 gene actions | Emergent morphology (OpenPraparat) |

## Architecture

```
eml_core.py    — EML operator, binary tree structures, known formulas, verification
server.py      — FastMCP server exposing tools and resources
```

The core engine uses `complex128` throughout — trigonometric functions and π require complex intermediates via Euler's formula. Works cleanly with NumPy and PyTorch.

## Related

- [SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage) — Odrzywołek's original EML toolkit
- [hybrid-ai-mcp](https://github.com/angrysky56/hybrid-ai-mcp) — Boolean-domain companion (McCulloch-Pitts neurons, NAND logic)
- [mcp-logic](https://github.com/angrysky56) — Automated reasoning server for verifying EML identities

## License

MIT
