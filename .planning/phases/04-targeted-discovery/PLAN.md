# Implementation Plan - Phase 3: AST, Compiler & Formula Discovery

This phase introduces a robust expression parser and compiler that can transform standard mathematical strings into EML trees by recursively composing fragments from the database. It also adds a discovery engine to explore the EML space and derive new identities.

## User Review Required

> [!IMPORTANT]
> **Tree Substitution**: I will add a `substitute` method to `EMLNode`. This involves deep-copying subtrees to ensure that modifying one formula doesn't accidentally affect others sharing the same nodes.
> 
> **Numerical Verification**: Derived formulas will be automatically verified using the `verify_eml_identity` utility. I will need to define reference functions (using `math` or `numpy`) for common operations like `sin`, `cos`, and `reciprocal`.

## Proposed Changes

### [EML Core]

#### [MODIFY] [trees.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/src/eml_mcp/trees.py)
- Add `EMLNode.substitute(var_mappings: dict[str, EMLNode]) -> EMLNode`.
- Add `EMLNode.copy() -> EMLNode` (recursive deep copy).
- Ensure `to_rpn` and `to_expression` handle nested structures correctly.

#### [NEW] [compiler.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/src/eml_mcp/compiler.py)
- `EMLCompiler` class utilizing `ast.parse`.
- Recursive traversal of the Python AST to build `EMLNode` trees.
- Resolution of operators (`+`, `-`, `*`, `/`, `**`) to DB formulas.
- Resolution of function calls (e.g., `exp(x)`) to DB formulas.

#### [NEW] [discovery.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/src/eml_mcp/discovery.py)
- `DiscoveryEngine` for deriving new formulas via compositional crossover and mutation.
- Implementation of **Novelty Search**: Open-ended exploration that archives mathematically stable, emergent formulas (the "Library of the Interesting") rather than solely targeting specific reference functions.
- Integration with `verify_eml_identity` for proof-of-correctness and boundary-condition validation (discarding paths with overflow/NaN).

---

### [Server & Tools]

#### [MODIFY] [server.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/src/eml_mcp/server.py)
- Refactor `eml_compile` to use the new `EMLCompiler`.
- Remove the hardcoded `alias_map` in favor of dynamic DB-backed resolution.
- Enhance error reporting for unknown functions or invalid syntax.

---

### [Testing]

#### [NEW] [test_compiler.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/tests/test_compiler.py)
- Test parsing of basic and compound expressions (`"x + 1"`, `"exp(exp(x))"`).
- Test error handling for invalid syntax and unknown functions.

#### [NEW] [test_discovery.py](file:///home/ty/Repositories/ai_workspace/eml-mcp/tests/test_discovery.py)
- Test derivation of at least 2 new formulas (e.g., `reciprocal`, `divide`).
- Verify provenance tracking and DB persistence.

## Verification Plan

### Automated Tests
- `uv run pytest tests/test_compiler.py`
- `uv run pytest tests/test_discovery.py`
- Full suite pass: `uv run pytest tests/`

### Manual Verification
- Test `eml_compile` via MCP with complex strings: `"exp(ln(x) + ln(y))"`.
- Verify that new formulas appear in `eml_list_formulas` after derivation.

## Phase 4: Targeted Discovery & Open-Ended Proximity

Based on the core claims of Minimal Generative Architectures, the discovery engine should balance open-ended novelty search with targeted goal-directed derivation. If the target is not reached, the system will rely on entropy maximization (novelty search) to return "open-ended nearby discoveries" structurally or output-wise close to the target.

1. **Distance Metric Implementation**
   - Add Mean Squared Error (MSE) calculation over `test_points` to compare generated formulas with a given target evaluator sequence.

2. **Targeted Search Algorithm (`DiscoveryEngine.find_target`)**
   - Accept a reference evaluation function for the target.
   - Run compositional novelty search (or a generic iterative generator) up to a max limit.
   - If a composition matches the target within a strict tolerance (e.g. `1e-5`), return the successful tree.
   - If the limit is reached, return the top N "nearby" formulas (open-ended discoveries sorted by MSE or cosine similarity).

3. **Tool Integration**
   - Add a new tool `eml_discover` in `server.py` that takes a target expression and returns either a direct match or nearby discoveries based on this distance metric.

## User Feedback Required

Please review the proposed Phase 4 plan above, specifically whether MSE across exactly the 6 defined transcendental test points is sufficient for ranking "nearby" discoveries, or if you prefer a different metric (e.g., structural edit distance).
