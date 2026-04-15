# ARCHITECTURE.md — System Architecture

## Pattern

**Single-responsibility MCP server** with a clean two-layer split:
- `eml_core.py` — pure computation engine (no MCP, no I/O)
- `server.py` — MCP adapter exposing core functions as tools/resources

This follows the **Adapter / Ports-and-Adapters** pattern: the core is framework-agnostic and testable in isolation; the server is a thin adapter that translates MCP calls into core calls.

## Data Flow

```
MCP Client (Claude, Antigravity, etc.)
    │  JSON-RPC over stdio
    ▼
server.py  (FastMCP tool handlers)
    │  imports and calls
    ▼
eml_core.py  (EML operator, tree structures, formula registry, verification)
    │
    ▼
numpy (complex128 arithmetic)
```

No async, no threads, no queues. Fully synchronous call path.

## Core Abstractions (eml_core.py)

### 1. EML Operator
```python
def eml(x: complex, y: complex) -> complex:
    return _safe_exp(x) - _safe_log(y)
```
The fundamental primitive. Everything else is composed from this.

### 2. EMLNode Tree
```python
@dataclass
class EMLNode:
    node_type: NodeType   # CONST | VAR | EML
    value: complex | None
    var_name: str | None
    left: EMLNode | None   # exp input subtree
    right: EMLNode | None  # ln input subtree
```
Recursive binary tree. Grammar: `S → 1 | x | eml(S, S)`.
Key methods: `.evaluate(variables)`, `.depth`, `.leaf_count`, `.node_count` (K), `.to_rpn()`, `.to_expression()`, `.to_dict()`.

### 3. Formula Registry
```python
KNOWN_FORMULAS: dict[str, dict[str, Any]] = {
    "exp": {"builder": build_exp_tree, "depth": 1, "K": 3, ...},
    "ln":  {"builder": build_ln_tree,  "depth": 3, "K": 7, ...},
    ...  # 8 formulas total
}
```
Maps formula names to builder functions and metadata. The single source of truth for all named EML implementations.

### 4. Builder Functions
Pure factory functions that construct `EMLNode` trees. Named `build_*_tree()`. Two categories:
- **Primitive builders**: `build_exp_tree()`, `build_e_tree()`, `build_ln_tree()`, `build_zero_tree()`  
- **Composite builders**: `build_subtract_tree()`, `build_negate_tree()`, `build_add_tree()`, `build_multiply_tree()`

Composite builders compose the primitives, e.g.:
```python
def build_add_tree() -> EMLNode:
    # x + y = x - (-y) = x - (0 - y)
    neg_y = eml_node(build_ln_from_subtree(build_zero_tree()),
                     build_exp_from_subtree(var("y")))
    return eml_node(build_ln_from_subtree(var("x")),
                    build_exp_from_subtree(neg_y))
```

### 5. Helper Subtree Builders
```python
def build_ln_from_subtree(subtree: EMLNode) -> EMLNode:
    # ln(z) = eml(1, eml(eml(1, z), 1))
    ...
def build_exp_from_subtree(subtree: EMLNode) -> EMLNode:
    # exp(z) = eml(z, 1)
    ...
```
Reusable building blocks for constructing composite formulas. Critical for the bootstrapping chain from Odrzywołek's `VerifyBaseSet`.

### 6. Verification Engine
```python
def verify_eml_identity(tree, reference_fn, test_points, variables, tolerance) -> dict:
```
Evaluates the tree against a reference function at algebraically independent transcendental test points (Euler-Mascheroni `γ ≈ 0.577`, Glaisher-Kinkelin `A ≈ 1.282`, `√2`, `φ`). Returns pass/fail + max error.

### 7. Master Formula Tree
```python
def build_master_tree(depth: int, var_names) -> dict:
```
Parameterized tree structure for symbolic regression. Computes parameter count formula `5×2^n - 6` from the paper.

## Server Layer (server.py)

Six `@mcp.tool(...)` decorated functions, one `@mcp.resource(...)` per URI. Each tool:
1. Validates inputs
2. Looks up formula in `KNOWN_FORMULAS` or builds tree directly
3. Calls core functions
4. Returns a structured `dict` (FastMCP serializes to JSON)

Private helper `_compile_result(expression, tree)` deduplicates the response formatting for `eml_compile`.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `complex128` everywhere | Trig functions and π require complex intermediates; correctness over performance |
| Exp clamping `[-700, 700]` | Prevents `float64` overflow at `exp(710)`; consistent with IEEE754 conventions |
| `_safe_log(0) = -∞` | Extended reals convention; enables the negation formula via `ln(0) = -∞` |
| Separate `eml_core.py` from `server.py` | Testable core; swappable transport layer |
| Registry pattern (`KNOWN_FORMULAS`) | Single source of truth; tools discover formulas by name |
| All tools `readOnlyHint=True` | EML computation has no side effects; correct signal to MCP clients |

## Numerical Architecture

The EML tree evaluation is a recursive descent, not vectorized. Each `evaluate()` call processes one complex scalar. For batch evaluation, `eml_array()` in `eml_core.py` provides a vectorized path (used in future symbolic regression work, not in current MCP tools).

## Future Architecture (from docs/)

`docs/eml_transformer_architecture.md` specifies a **EML-Transformer**: a transformer whose FFN blocks use the EML operator as the activation function, with analytically constructed weights (zero training). The MCP server functions as the reference oracle and tree builder during that compilation pipeline. Key phases:
1. **Static compiler** (schedule → allocate → construct weights)  
2. **MoR integration** (shared EML block + recursion router)
3. **Hybrid LLM** (frozen EML block alongside learned language layers)
