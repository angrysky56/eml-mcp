# CONVENTIONS.md — Code Style & Patterns

## Python Style

- **Formatter:** `black` (via Trunk), targeting Python 3.12+
- **Linter:** `ruff` with rules `B` (bugbear), `D3` (docstring conventions), `E` (pycodestyle), `F` (pyflakes)
- **Import order:** `isort` managed
- **Line length:** Not enforced (`E501` explicitly ignored in `ruff.toml`); handled by `black`
- **Type hints:** All public functions are fully annotated
- **Future annotations:** `from __future__ import annotations` in every module (enables forward references)

## Docstrings

All public functions and classes have Google-style docstrings:

```python
def eml(x: complex, y: complex) -> complex:
    """The EML (Exp-Minus-Log) Sheffer operator.

    eml(x, y) = exp(x) - ln(y)

    This single binary operator, paired with the constant 1,
    generates all standard elementary functions.

    Args:
        x: First argument (feeds into exp).
        y: Second argument (feeds into ln).

    Returns:
        exp(x) - ln(y) as a complex number.
    """
```

Properties have one-line docstrings. Private helpers (`_safe_exp`, `_compile_result`) have brief descriptions.

## Type Hints

- Uses union syntax: `float | complex | None` (Python 3.10+ style, enabled via `from __future__ import annotations`)
- Uses `dict[str, Any]`, `list[str]` lower-case generics (not `Dict`, `List`)
- `callable` (lowercase) used where strict typing would require `Callable[..., Any]` — acceptable given the research nature of the code

## Module Structure Pattern

Each module is organized with commented section banners:

```python
# ==================== Section Name ====================
```

This visual separation is consistent across `eml_core.py` and `server.py` and serves as a lightweight substitute for sub-modules.

## Error Handling

### In eml_core.py
- `EMLNode.evaluate()` raises `ValueError` for unbound variables or unknown node types
- `_safe_log(0)` returns `complex(-inf, 0)` — extended reals convention, not an exception
- `_safe_exp` clamps real part to `[-700, 700]` silently — numerical safety, not an error condition

### In server.py (MCP tools)
- Tools use `try/except Exception as e` broad catch at the top level, returning `{"status": "error", "message": str(e)}`
- Inner loops (`eml_verify`, `eml_tree_info`) use narrow catches: `(ValueError, ZeroDivisionError, OverflowError)`
- Errors return dicts with `"status": "error"` and `"message"` keys — consistent across all tools
- Unknown formula names return structured errors with `"available"` list for discoverability
- All logging goes to `stderr` via `logger.error(...)` — never to stdout (MCP protocol channel)

### Bandit suppression
```python
# trunk-ignore(bandit/B105)
"pass": False,
```
Used once to suppress a false-positive Bandit B105 (hardcoded password detection on the string `"pass"` as a dict key).

## Return Data Patterns

All MCP tools return plain `dict` (no Pydantic models). Consistent response shape:

**Success:**
```python
{
    "result": <value>,
    "formula": "eml(x, y) = exp(x) - ln(y)",
    "components": {...},
    "explanation": "...",
}
```

**Tree info:**
```python
{
    "name": str,
    "description": str,
    "expression": str,          # human-readable
    "rpn": str,                 # space-separated RPN tokens
    "depth": int,
    "K": int,                   # node count = Kolmogorov complexity
    "leaf_count": int,
    "node_count": int,          # same as K
    "tree": dict,               # recursive JSON-serializable dict
}
```

**Error:**
```python
{"status": "error", "message": str, "available": list}
```

**Verify:**
```python
{
    "passed": bool,
    "max_error": float,
    "tolerance": float,
    "n_tests": int,
    "details": [{"input": ..., "tree_output": ..., "reference": ..., "error": float, "pass": bool}],
}
```

## Numerical Output Convention

`extract_real(z, tolerance=1e-10)` is used whenever displaying complex results to users:
- Returns `z.real` (float) if `|z.imag| < 1e-10`
- Returns the full complex `z` otherwise
- Applied consistently in all tool return values and verification details

## Immutability

All builder functions (`build_*_tree()`) create fresh `EMLNode` instances every call — no shared mutable state. `_1()` and `_x()` are factory functions rather than constants to avoid aliasing issues between tree nodes.

## Constants Used as Sentinels

`ONE = const(1.0)` is defined but not used in tree construction (superseded by `_1()` factory to preserve node independence). Kept as a readable reference constant.

## Commit Convention

The project uses **Conventional Commits**:
- `feat:` — new formula or tool
- `fix:` — bug fixes
- `docs:` — documentation changes
- `refactor:` — restructuring without behavior change
