# TESTING.md — Test Structure & Practices

## Current State

**No test files exist in the repository.** The `pytest` and `pytest-asyncio` dependencies are declared in `pyproject.toml` under `[project.optional-dependencies] dev`, but no `tests/` directory, no `test_*.py` files, and no `conftest.py` are present.

The live MCP server tools (accessible via the `eml-mcp` MCP server) serve as the primary validation mechanism in the current iteration.

## Verification Strategy (Active)

In lieu of a traditional test suite, the codebase uses **numerical verification via `eml_verify`**, which is itself an MCP tool backed by `verify_eml_identity()` in `eml_core.py`.

### How It Works

```python
def verify_eml_identity(
    tree: EMLNode,
    reference_fn: callable,
    test_points: list[complex] | None = None,
    variables: dict[str, complex] | None = None,
    tolerance: float = 1e-10,
) -> dict[str, Any]:
```

Default test points (algebraically independent transcendentals, per Odrzywołek 2026):
```python
[
    complex(0.5772156649015329),   # Euler-Mascheroni γ
    complex(1.2824271291006226),   # Glaisher-Kinkelin A
    complex(1.4142135623730951),   # √2
    complex(1.6180339887498949),   # Golden ratio φ
    complex(2.5),
    complex(0.1),
]
```

**Tolerance:** `1e-10` (default). Under the Schanuel conjecture, coincidental equality at transcendental points is vanishingly unlikely, making these strong checks.

### Reference Functions Defined

In `server.py:eml_verify`, reference functions are defined inline:

| Formula     | Reference Function                              |
|-------------|------------------------------------------------|
| `exp`       | `lambda z: complex(math.e**z.real)`            |
| `e`         | `lambda _: complex(math.e)`                    |
| `ln`        | `lambda z: complex(math.log(z.real))`          |
| `zero`      | `lambda _: complex(0.0)`                       |
| `subtract`  | `lambda x, y: complex(x - y)` (paired points) |
| `negate`    | `lambda z: complex(-z)`                        |
| `add`       | `lambda x, y: complex(x + y)` (paired points) |
| `multiply`  | `lambda x, y: complex(x * y)` (paired points) |

Multivariate formulas use paired test points:
```python
[
    (complex(2.5), complex(1.3)),
    (complex(0.5772...), complex(1.6180...)),  # γ, φ
    (complex(√2), complex(A)),                  # √2, Glaisher-Kinkelin
    (complex(3.0), complex(0.7)),
    (complex(0.1), complex(2.0)),
]
```

## Planned Test Infrastructure

When implemented, tests should follow this structure:

```
tests/
├── conftest.py           # shared fixtures (sample trees, test points)
├── test_eml_core.py      # unit tests for eml_core.py
│   ├── test_eml_operator     # eml(x,y) basic correctness
│   ├── test_safe_exp         # clamping behavior at boundary
│   ├── test_safe_log         # zero input → -inf
│   ├── test_eml_node         # evaluate, depth, leaf_count, node_count
│   ├── test_known_formulas   # all 8 builders produce correct K/depth
│   └── test_verify_engine    # verify_eml_identity against reference
└── test_server.py        # integration tests for MCP tools
    ├── test_eml_evaluate
    ├── test_eml_list_formulas
    ├── test_eml_tree_info
    ├── test_eml_compile      # all aliases, compositions, error cases
    ├── test_eml_verify       # all 8 formulas pass
    └── test_eml_master_tree  # depth 1-6, parameter count formula
```

## Key Test Cases Needed

### `eml_core.py`

```python
# Operator correctness
assert eml(0, 1) == pytest.approx(1.0)          # exp(0) - ln(1) = 1 - 0 = 1
assert abs(eml(1, 1).real - math.e) < 1e-10     # e = eml(1,1)

# Safe boundaries
assert _safe_exp(complex(800)).real == math.exp(700)  # clamped
assert _safe_log(0) == complex(float("-inf"), 0)       # extended reals

# Tree metrics
tree = build_exp_tree()
assert tree.depth == 1
assert tree.node_count == 3     # K=3
assert tree.leaf_count == 2

# All registry formulas verifiable
for name, info in KNOWN_FORMULAS.items():
    tree = info["builder"]()
    assert tree.node_count == info["K"]
    assert tree.depth == info["depth"]
```

### `eml_compile` edge cases

```python
# Error case — unsupported expression
result = eml_compile("sin(x)")
assert result["status"] == "error"

# Alias resolution
result = eml_compile("e^x")
assert result["K"] == 3  # same as "exp"

# Composition
result = eml_compile("exp(exp(x))")
assert "K" in result  # should succeed
```

## Running Tests (When Implemented)

```bash
source .venv/bin/activate
pytest tests/ -v
pytest tests/ --tb=short -q   # quiet mode
```

## Security Scanning

`bandit` runs via Trunk on every check. Known suppression:
```python
# trunk-ignore(bandit/B105)
```
On `"pass": False` — false positive, not a hardcoded password.
