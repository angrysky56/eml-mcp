# STRUCTURE.md — Directory Layout & Organization

## Top-Level Layout

```
eml-mcp/
├── eml_core.py              # Core EML engine (operator, trees, registry, verification)
├── server.py                # FastMCP server (tools and resources)
├── pyproject.toml           # Project metadata, deps, build config
├── uv.lock                  # Locked dependency graph
├── README.md                # User-facing documentation
├── example_mcp_config.json  # Sample MCP client configuration
│
├── docs/                    # Research & architecture documentation
│   ├── eml_transformer_architecture.md   # EML-Transformer formal spec (764 lines)
│   └── cross_domain_exploration.md      # MGA cross-domain analysis
│
├── .trunk/                  # Trunk linter orchestration
│   ├── trunk.yaml           # Enabled linters & actions
│   └── configs/
│       ├── ruff.toml        # Ruff rules (B, D3, E, F; ignore E501)
│       ├── .isort.cfg       # Import sorting config
│       └── .markdownlint.yaml
│
├── .venv/                   # Python virtual environment (uv-managed)
├── __pycache__/             # Python bytecode cache
└── .git/                    # Git repository
```

## Source File Responsibilities

### `eml_core.py` (541 lines)

| Section (by comment block) | Contents |
|---------------------------|----------|
| Constants | `DTYPE`, `EXP_CLAMP_MAX/MIN`, `_safe_exp`, `_safe_log` |
| EML Operator | `eml()`, `eml_array()` |
| EML Binary Tree | `NodeType` enum, `EMLNode` dataclass |
| Tree Constructors | `const()`, `var()`, `eml_node()`, `ONE`, `_1()`, `_x()` |
| Known EML Formulas | `build_exp_tree()`, `build_e_tree()`, `build_ln_tree()`, `build_zero_tree()`, `build_ln_from_subtree()`, `build_exp_from_subtree()` |
| Extended Bootstrapping Chain | `build_subtract_tree()`, `build_negate_tree()`, `build_add_tree()`, `build_multiply_tree()` |
| Formula Registry | `KNOWN_FORMULAS` dict |
| Utilities | `extract_real()` |
| Master Formula Tree | `build_master_tree()` |
| Verification | `verify_eml_identity()` |

### `server.py` (620 lines)

| Section (by comment block) | Contents |
|---------------------------|----------|
| Logging setup | `logging.basicConfig(stream=sys.stderr)` |
| FastMCP init | `mcp = FastMCP("eml-mcp")` |
| MCP Tools | `eml_evaluate`, `eml_list_formulas`, `eml_tree_info`, `eml_compile`, `eml_verify`, `eml_master_tree` |
| Private helpers | `_compile_result()` |
| Resources | `get_eml_grammar()`, `get_complexity_table()` |
| Main | `mcp.run()` entrypoint |

## Naming Conventions

### Files
- Core logic: `eml_core.py` — flat module, no sub-packages
- Server: `server.py` — standard FastMCP naming
- Docs: lowercase with underscores, `.md` extension

### Functions
- **Builder functions:** `build_<name>_tree()` — returns `EMLNode`
- **Subtree helpers:** `build_<op>_from_subtree(subtree)` — parameterized builders
- **MCP tool handlers:** same name as the MCP tool string, e.g., `eml_evaluate`, `eml_verify`
- **Private helpers:** single underscore prefix, e.g., `_safe_exp`, `_safe_log`, `_compile_result`
- **Short constructors:** `_1()`, `_x()` — generate fresh leaf nodes

### Classes / Types
- `NodeType` — `str` Enum with values `"const"`, `"var"`, `"eml"`
- `EMLNode` — `@dataclass` with snake_case fields

### Constants
- Module-level ALLCAPS: `DTYPE`, `EXP_CLAMP_MAX`, `EXP_CLAMP_MIN`, `KNOWN_FORMULAS`, `ONE`

### Dict Keys (in KNOWN_FORMULAS registry)
- `"builder"` — callable returning root `EMLNode`
- `"description"` — human-readable description
- `"depth"` — integer tree depth
- `"K"` — integer node count (Kolmogorov complexity)
- `"variables"` — list of variable name strings
- `"note"` — optional string, notes on compiler vs. paper K discrepancy

## Key File Paths

| Item | Path |
|------|------|
| EML operator implementation | `eml_core.py:66` |
| EMLNode dataclass | `eml_core.py:101` |
| KNOWN_FORMULAS registry | `eml_core.py:346` |
| verify_eml_identity() | `eml_core.py:468` |
| FastMCP server init | `server.py:63` |
| eml_compile tool | `server.py:252` |
| eml_verify tool | `server.py:361` |
| EML-Transformer spec | `docs/eml_transformer_architecture.md` |
| Ruff config | `.trunk/configs/ruff.toml` |
| Dependency manifest | `pyproject.toml` |
