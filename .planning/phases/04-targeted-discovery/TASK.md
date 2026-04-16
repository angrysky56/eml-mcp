# Task: Phase 3 - AST, Compiler & Formula Discovery

- [x] **Wave 1: Tree Composition**
    - [x] `trees.py`: Add `EMLNode.substitute(var_mappings: dict[str, EMLNode]) -> EMLNode`
    - [x] `trees.py`: Add `EMLNode.copy() -> EMLNode` (recursive deep copy)
- [x] **Wave 2: Expresion Compiler**
    - [x] `compiler.py`: Create `EMLCompiler` using `ast.parse`
    - [x] Add operator resolution (resolution to DB formulas)
    - [x] `test_compiler.py`: Create unit tests for parsing
- [x] **Wave 3: Novelty Search Discovery Engine**
    - [x] `discovery.py`: Create `DiscoveryEngine` for composing existing formulas
    - [x] Add Novelty Search implementation (saving stable formulas rather than just specific targets)
    - [x] Integrate with `verify_eml_identity` for verification and handling overflow/NaN boundaries
    - [x] `test_discovery.py`: Create unit tests
- [x] **Wave 4: Server Integration**
    - [x] `server.py`: Refactor `eml_compile` to use new `EMLCompiler`
    - [x] Improve server error handling and syntax reporting
- [x] **Final Walkthrough**
    - [x] Full test suite pass
    - [x] Update walkthrough artifact

# Task: Phase 4 - Targeted Discovery & Open-Ended Proximity

- [x] **Wave 1: Distance Metrics**
    - [x] `trees.py` or new location: define distance calculations (MSE) against test points
- [x] **Wave 2: Targeted Search in DiscoveryEngine**
    - [x] `discovery.py`: Add `find_target(reference_sequence, max_iterations, top_n)`
    - [x] `test_discovery.py`: Add tests for targeted search returning "nearby discoveries" when direct match fails
- [x] **Wave 3: Tool Integration**
    - [x] `server.py`: Create `eml_discover` tool for exposing targeted search
- [x] **Wave 4: Verification & Walkthrough**
    - [x] Run full test suite to ensure `find_target` functionality works correctly with open-ended novelty
    - [x] Update walkthrough artifact to highlight results
