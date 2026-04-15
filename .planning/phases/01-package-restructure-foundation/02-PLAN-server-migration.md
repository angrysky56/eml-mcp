---
plan: "02"
phase: "1"
wave: 2
depends_on: ["01"]
objective: "Migrate server.py into src/eml_mcp/server.py with updated imports from package submodules"
files_modified:
  - src/eml_mcp/server.py
requirements: [PKG-03, PKG-04]
autonomous: true
must_haves:
  - All 6 MCP tools present with identical signatures and behavior
  - FastMCP app named "eml-mcp" unchanged
  - Imports updated to use eml_mcp.* submodules not root-level eml_core
---

## Objective

Move `server.py` into the package as `src/eml_mcp/server.py`, updating all imports to reference the new submodules. Every MCP tool must behave identically — same names, same parameters, same return shapes.

---

## Task 1: Copy server.py and update imports

<read_first>
- server.py (full file — 615 lines, understand all imports and tool implementations)
- src/eml_mcp/operator.py (available symbols: eml, eml_array, DTYPE, EXP_CLAMP_MAX, EXP_CLAMP_MIN)
- src/eml_mcp/trees.py (available symbols: EMLNode, NodeType, const, var, eml_node, extract_real)
- src/eml_mcp/registry.py (available symbols: KNOWN_FORMULAS, all build_*_tree, build_master_tree, verify_eml_identity)
</read_first>

<action>
Create `src/eml_mcp/server.py` as a copy of the root `server.py` with these import changes only:

**OLD import block (lines 30–61 in server.py):**
```python
from eml_core import (
    DTYPE,
    KNOWN_FORMULAS,
    EMLNode,
    NodeType,
    build_add_tree,
    build_e_tree,
    build_exp_from_subtree,
    build_exp_tree,
    build_ln_from_subtree,
    build_ln_tree,
    build_master_tree,
    build_multiply_tree,
    build_negate_tree,
    build_subtract_tree,
    build_zero_tree,
    const,
    eml,
    eml_node,
    extract_real,
    var,
    verify_eml_identity,
)
```

**NEW import block** (replace the above with):
```python
from eml_mcp.operator import DTYPE, eml
from eml_mcp.trees import EMLNode, NodeType, const, eml_node, extract_real, var
from eml_mcp.registry import (
    KNOWN_FORMULAS,
    build_add_tree,
    build_e_tree,
    build_exp_from_subtree,
    build_exp_tree,
    build_ln_from_subtree,
    build_ln_tree,
    build_master_tree,
    build_multiply_tree,
    build_negate_tree,
    build_subtract_tree,
    build_zero_tree,
    verify_eml_identity,
)
```

All other content (tool handlers, FastMCP app, resources, logging config) is copied verbatim. Do NOT modify any tool function signatures, docstrings, or logic.

Also remove the `if __name__ == "__main__":` block at the bottom (lines 611–615) — it is now in `__main__.py`.
</action>

<acceptance_criteria>
- `grep "from eml_core" src/eml_mcp/server.py` returns empty (no old imports)
- `grep "from eml_mcp.operator import\|from eml_mcp.trees import\|from eml_mcp.registry import" src/eml_mcp/server.py | wc -l` prints `3`
- `grep "^@mcp.tool\|^def eml_" src/eml_mcp/server.py | wc -l` prints `12` (6 decorators + 6 functions)
- `grep "FastMCP(\"eml-mcp\")" src/eml_mcp/server.py` returns 1 match
- `grep "if __name__" src/eml_mcp/server.py` returns empty (removed)
- `python -c "from eml_mcp.server import mcp; print(type(mcp).__name__)"` exits 0 and prints `FastMCP`
</acceptance_criteria>

---

## Task 2: Smoke-test all 6 tools via server import

<read_first>
- src/eml_mcp/server.py (just written)
</read_first>

<action>
Run these import-level checks to confirm all tool handlers are reachable without errors:

```bash
cd /home/ty/Repositories/ai_workspace/eml-mcp
source .venv/bin/activate
python -c "
from eml_mcp.server import mcp, eml_evaluate, eml_list_formulas, eml_tree_info, eml_compile, eml_verify, eml_master_tree
print('All 6 tools imported OK')
# Quick functional check
result = eml_evaluate(0.0, 1.0)
assert result['status'] == 'ok', f'Expected ok, got {result}'
formulas = eml_list_formulas()
assert len(formulas['formulas']) == 8, f'Expected 8 formulas, got {len(formulas[\"formulas\"])}'
print('Smoke tests passed')
"
```
</action>

<acceptance_criteria>
- Command exits 0
- Stdout contains `All 6 tools imported OK`
- Stdout contains `Smoke tests passed`
</acceptance_criteria>
