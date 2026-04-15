# Requirements: EML-MCP

**Defined:** 2026-04-15
**Core Value:** The EML operator and its formula registry must produce numerically correct results at machine-epsilon precision for every known elementary function.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Package Structure

- [ ] **PKG-01**: Project restructured as `src/eml_mcp/` Python package with `__init__.py` and submodules
- [ ] **PKG-02**: `eml_core.py` split into focused submodules (operator, trees, registry, verification)
- [ ] **PKG-03**: `server.py` split into MCP tool handlers and server configuration
- [ ] **PKG-04**: All existing MCP tools work identically after restructure (no breaking changes)
- [ ] **PKG-05**: `pyproject.toml` updated with new package path and entry points

### Persistence

- [ ] **DB-01**: SQLite database stores formula definitions (name, description, tree structure, complexity K, leaf count)
- [ ] **DB-02**: Database stores derivation provenance (which formulas were composed to derive a new one)
- [ ] **DB-03**: Database stores verification results with timestamps (formula, test points, errors, pass/fail)
- [ ] **DB-04**: Database stores symbolic regression results (master tree weights, snap results, target function)
- [ ] **DB-05**: Hardcoded `KNOWN_FORMULAS` dict replaced by DB-backed registry; only irreducible seeds (constant 1, EML operator) remain in code
- [ ] **DB-06**: Database auto-initializes with seed formulas on first run (migration from current hardcoded set)

### AST & Compiler

- [ ] **AST-01**: Expression parser handles standard mathematical notation (`"exp(x)"`, `"sin(x)"`, `"x + y"`, `"x * y"`, `"x^2"`)
- [ ] **AST-02**: Parser produces a typed AST with nodes for constants, variables, unary ops, binary ops
- [ ] **AST-03**: Compiler resolves AST nodes to known EML tree fragments from the DB registry
- [ ] **AST-04**: Compiler composes EML tree fragments to build complete trees for compound expressions
- [ ] **AST-05**: Compiler reports when a requested function has no known EML decomposition (rather than failing silently)

### Formula Discovery

- [ ] **DISC-01**: Discovery engine can compose two existing formulas via the EML operator and evaluate the result
- [ ] **DISC-02**: Discovery engine numerically verifies candidate compositions against reference functions
- [ ] **DISC-03**: Discovery engine persists verified formulas to DB with full provenance
- [ ] **DISC-04**: Discovery engine tracks complexity (K = leaf count) and prefers shorter trees when multiple derivations exist
- [ ] **DISC-05**: Discovery engine can be invoked via MCP tool to explore the formula space on demand

### MCP Tools

- [ ] **MCP-01**: New `eml_db_search` tool searches formula DB by name, complexity, or tag
- [ ] **MCP-02**: New `eml_db_derive` tool composes formulas and verifies/persists results
- [ ] **MCP-03**: New `eml_db_history` tool retrieves verification history for a formula
- [ ] **MCP-04**: Existing `eml_evaluate`, `eml_tree_info`, `eml_verify`, `eml_compile`, `eml_master_tree`, `eml_list_formulas` tools updated to use DB backend
- [ ] **MCP-05**: All MCP tool responses remain structured JSON suitable for AI agent consumption

### Testing

- [ ] **TEST-01**: pytest test suite covering all 8 existing formulas (evaluate, verify identity)
- [ ] **TEST-02**: Tests for DB operations (CRUD, migration, seed initialization)
- [ ] **TEST-03**: Tests for AST parser (valid expressions, error cases, edge cases)
- [ ] **TEST-04**: Tests for compiler (known decompositions, unknown function handling)
- [ ] **TEST-05**: Tests for discovery engine (composition, verification, persistence)
- [ ] **TEST-06**: Tests for MCP tool surface (tool registration, input validation, response shapes)

### CI/CD

- [ ] **CI-01**: GitHub Actions workflow runs on push and PR
- [ ] **CI-02**: CI runs `trunk check` (ruff, black, isort)
- [ ] **CI-03**: CI runs `pytest` with coverage reporting
- [ ] **CI-04**: CI fails on lint errors or test failures

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Compiler Extensions

- **COMP-01**: Full bootstrapping chain implementing all ~36 elementary functions from the paper
- **COMP-02**: Automatic derivation search — systematically explore composition space to find novel decompositions
- **COMP-03**: Multi-variable expression support (functions of x, y, z)

### Symbolic Regression

- **SR-01**: EML master tree training via gradient descent (Adam) on user-provided data
- **SR-02**: Weight snapping to 0/1 for formula recovery
- **SR-03**: PyTorch-backed SR pipeline with GPU support

### Model Architecture

- **MODEL-01**: EML-Transformer compiler (EML tree → transformer weight tensors)
- **MODEL-02**: Analytical FFN weight construction for EML operator
- **MODEL-03**: Verification of compiled transformer output against reference

## Out of Scope

| Feature | Reason |
|---------|--------|
| EML-Transformer implementation | Separate project — prove engine first |
| MOP policy discovery | Requires SR working; future project |
| OpenPraparat integration | Research-stage; requires MOP |
| GUI / web interface | MCP is the interface; AI agents are the users |
| PostgreSQL / Redis | SQLite is sufficient; zero-dependency |
| PyPI publishing | Premature; package structure enables it later |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PKG-01 | Phase 1 | Pending |
| PKG-02 | Phase 1 | Pending |
| PKG-03 | Phase 1 | Pending |
| PKG-04 | Phase 1 | Pending |
| PKG-05 | Phase 1 | Pending |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| DB-04 | Phase 2 | Pending |
| DB-05 | Phase 2 | Pending |
| DB-06 | Phase 2 | Pending |
| AST-01 | Phase 3 | Pending |
| AST-02 | Phase 3 | Pending |
| AST-03 | Phase 3 | Pending |
| AST-04 | Phase 3 | Pending |
| AST-05 | Phase 3 | Pending |
| DISC-01 | Phase 3 | Pending |
| DISC-02 | Phase 3 | Pending |
| DISC-03 | Phase 3 | Pending |
| DISC-04 | Phase 3 | Pending |
| DISC-05 | Phase 3 | Pending |
| MCP-01 | Phase 4 | Pending |
| MCP-02 | Phase 4 | Pending |
| MCP-03 | Phase 4 | Pending |
| MCP-04 | Phase 4 | Pending |
| MCP-05 | Phase 4 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 2 | Pending |
| TEST-03 | Phase 3 | Pending |
| TEST-04 | Phase 3 | Pending |
| TEST-05 | Phase 3 | Pending |
| TEST-06 | Phase 4 | Pending |
| CI-01 | Phase 1 | Pending |
| CI-02 | Phase 1 | Pending |
| CI-03 | Phase 1 | Pending |
| CI-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after initial definition*
