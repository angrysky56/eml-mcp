---
plan: "01"
phase: "1"
wave: 1
depends_on: []
objective: "Create src/eml_mcp/ package skeleton and split eml_core.py into four focused submodules"
files_modified:
  - src/eml_mcp/__init__.py
  - src/eml_mcp/operator.py
  - src/eml_mcp/trees.py
  - src/eml_mcp/registry.py
  - src/eml_mcp/__main__.py
requirements: [PKG-01, PKG-02]
autonomous: true
must_haves:
  - src/eml_mcp/ directory exists as a proper Python package
  - eml_core.py content fully distributed across operator.py, trees.py, registry.py
  - No functionality removed — every public symbol still accessible via package imports
---

## Objective

Split the monolithic `eml_core.py` (540 lines) into four focused submodules within a proper `src/eml_mcp/` package. Each submodule has a single responsibility. The old `eml_core.py` must remain at root for now (Plan 04 removes it after server migration confirms correctness).

---

## Task 1: Create package skeleton

<read_first>
- eml_core.py (full file — understand all symbols before splitting)
- pyproject.toml (understand current build config)
</read_first>

<action>
Create these directories and empty files:

```
src/
  eml_mcp/
    __init__.py      (non-empty — see content below)
    operator.py
    trees.py
    registry.py
    __main__.py
```

Create `src/eml_mcp/__init__.py` with this exact content:
```python
"""
EML-MCP: Model Context Protocol server for the EML (Exp-Minus-Log) Sheffer operator.

All elementary functions from a single binary operator, based on Odrzywołek (2026).
Reference: https://arxiv.org/html/2603.21852v2
"""

from eml_mcp.operator import DTYPE, EXP_CLAMP_MAX, EXP_CLAMP_MIN, eml, eml_array
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

__all__ = [
    "DTYPE", "EXP_CLAMP_MAX", "EXP_CLAMP_MIN",
    "eml", "eml_array",
    "EMLNode", "NodeType", "const", "eml_node", "extract_real", "var",
    "KNOWN_FORMULAS",
    "build_add_tree", "build_e_tree", "build_exp_from_subtree", "build_exp_tree",
    "build_ln_from_subtree", "build_ln_tree", "build_master_tree",
    "build_multiply_tree", "build_negate_tree", "build_subtract_tree",
    "build_zero_tree", "verify_eml_identity",
]
```
</action>

<acceptance_criteria>
- `ls src/eml_mcp/` shows: `__init__.py`, `operator.py`, `trees.py`, `registry.py`, `__main__.py`
- `src/eml_mcp/__init__.py` contains `from eml_mcp.operator import`
- `src/eml_mcp/__init__.py` contains `from eml_mcp.trees import`
- `src/eml_mcp/__init__.py` contains `from eml_mcp.registry import`
</acceptance_criteria>

---

## Task 2: Create operator.py

<read_first>
- eml_core.py lines 1–90 (module docstring, DTYPE, EXP_CLAMP_*, _safe_exp, _safe_log, eml, eml_array)
</read_first>

<action>
Create `src/eml_mcp/operator.py` containing exactly the following symbols from `eml_core.py`, preserving all docstrings and comments verbatim:

1. Module docstring (adapted: "EML Operator — core arithmetic primitives")
2. Imports: `from __future__ import annotations`, `numpy as np`
3. `DTYPE = np.complex128`  (line 31 of eml_core.py)
4. `EXP_CLAMP_MAX = 700.0` (line 35)
5. `EXP_CLAMP_MIN = -700.0` (line 36)
6. `_safe_exp(z)` function (lines 39–46) — preserve exactly, no changes
7. `_safe_log(z)` function (lines 48–62) — preserve exactly, no changes
8. `eml(x, y)` function (lines 66–83) — preserve exactly, including full docstring
9. `eml_array(x, y)` function (lines 84–90) — preserve exactly

No other symbols from eml_core.py go in operator.py.
</action>

<acceptance_criteria>
- `grep "^DTYPE\|^EXP_CLAMP\|^def eml\|^def _safe" src/eml_mcp/operator.py` returns 6 matches
- `grep "class\|EMLNode\|KNOWN_FORMULAS\|build_" src/eml_mcp/operator.py` returns empty (no cross-contamination)
- `python -c "from eml_mcp.operator import eml, DTYPE, EXP_CLAMP_MAX; print(eml(0, 1))"` exits 0 and prints `1+0j`
</acceptance_criteria>

---

## Task 3: Create trees.py

<read_first>
- eml_core.py lines 92–225 (NodeType enum, EMLNode dataclass, const, var, eml_node, ONE, _1, _x, extract_real)
- src/eml_mcp/operator.py (import _safe_exp, _safe_log, DTYPE from here)
</read_first>

<action>
Create `src/eml_mcp/trees.py` containing exactly:

1. Module docstring: "EML binary tree structures — EMLNode, NodeType, and factory functions."
2. Imports:
   ```python
   from __future__ import annotations
   import json
   from dataclasses import dataclass, field
   from enum import Enum
   from typing import Any
   import numpy as np
   from eml_mcp.operator import DTYPE, _safe_exp, _safe_log
   ```
3. `NodeType` class (lines 92–99 of eml_core.py) — preserve exactly
4. `EMLNode` dataclass (lines 101–189) — preserve exactly, including all methods
5. `const(value)` function (lines 191–195) — preserve exactly
6. `var(name)` function (lines 196–200) — preserve exactly
7. `eml_node(left, right)` function (lines 201–206) — preserve exactly
8. `ONE = const(1.0)` (line 207) — preserve (keep as documented dead code with comment)
9. `_1()` function (lines 210–213) — preserve exactly
10. `_x()` function (lines 215–222) — preserve exactly
11. `extract_real(z, tolerance)` function (lines 410–422) — move here (it's a tree utility)

**Important:** `EMLNode.evaluate()` calls `_safe_exp` and `_safe_log` internally — those must be imported from `eml_mcp.operator`.
</action>

<acceptance_criteria>
- `grep "^class NodeType\|^class EMLNode\|^def const\|^def var\|^def eml_node\|^def extract_real" src/eml_mcp/trees.py` returns 6 matches
- `grep "from eml_mcp.operator import" src/eml_mcp/trees.py` returns 1 match
- `python -c "from eml_mcp.trees import EMLNode, NodeType, const, var, eml_node; n = eml_node(const(1.0), const(1.0)); print(n.leaf_count)"` exits 0 and prints `2`
</acceptance_criteria>

---

## Task 4: Create registry.py

<read_first>
- eml_core.py lines 210–540 (builder functions, KNOWN_FORMULAS, build_master_tree, verify_eml_identity)
- src/eml_mcp/operator.py (import eml, _safe_exp, _safe_log, DTYPE)
- src/eml_mcp/trees.py (import EMLNode, NodeType, const, var, eml_node, _1, _x, extract_real)
</read_first>

<action>
Create `src/eml_mcp/registry.py` containing:

1. Module docstring: "EML formula registry — builder functions, KNOWN_FORMULAS, and numerical verification."
2. Imports:
   ```python
   from __future__ import annotations
   import math
   from typing import Any
   import numpy as np
   from eml_mcp.operator import DTYPE, eml, _safe_exp, _safe_log
   from eml_mcp.trees import EMLNode, NodeType, const, var, eml_node, _1, _x, extract_real
   ```
3. All builder functions from eml_core.py (lines 224–408), in order:
   - `build_exp_tree()` (line 224)
   - `build_e_tree()` (line 229)
   - `build_ln_tree()` (line 234)
   - `build_zero_tree()` (line 245)
   - `build_ln_from_subtree(subtree)` (line 254)
   - `build_exp_from_subtree(subtree)` (line 264)
   - `build_subtract_tree()` (line 273)
   - `build_negate_tree()` (line 287)
   - `build_add_tree()` (line 300)
   - `build_multiply_tree()` (line 318)
4. `KNOWN_FORMULAS` dict (lines 346–408) — preserve exactly with all metadata
5. `build_master_tree(depth, var_names)` (lines 424–466) — preserve exactly
6. `verify_eml_identity(tree, reference_fn, test_points, var_names)` (lines 468–540) — preserve exactly
</action>

<acceptance_criteria>
- `grep "^def build_\|^KNOWN_FORMULAS\|^def verify_\|^def build_master" src/eml_mcp/registry.py | wc -l` prints `13`
- `grep "from eml_mcp.operator import\|from eml_mcp.trees import" src/eml_mcp/registry.py | wc -l` prints `2`
- `python -c "from eml_mcp.registry import KNOWN_FORMULAS; print(list(KNOWN_FORMULAS.keys()))"` exits 0 and prints list of 8 formula names
- `python -c "from eml_mcp.registry import build_exp_tree; t = build_exp_tree(); print(t.leaf_count)"` exits 0 and prints `3`
</acceptance_criteria>

---

## Task 5: Create __main__.py

<read_first>
- server.py lines 611–615 (the `if __name__ == "__main__":` block)
</read_first>

<action>
Create `src/eml_mcp/__main__.py` with this exact content:

```python
"""Entry point for `python -m eml_mcp` and `uv run eml-mcp`."""

from eml_mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
```

Note: `eml_mcp.server` (Plan 02) does not exist yet — this file is written now but only tested after Plan 02 completes.
</action>

<acceptance_criteria>
- `cat src/eml_mcp/__main__.py` contains `from eml_mcp.server import mcp`
- `cat src/eml_mcp/__main__.py` contains `mcp.run()`
- File is 6 lines or fewer
</acceptance_criteria>
