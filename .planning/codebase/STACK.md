# STACK.md — Technology Stack

## Language & Runtime

| Item         | Value                          |
|--------------|-------------------------------|
| Language     | Python 3.12+                  |
| Runtime      | CPython                        |
| Package mgr  | `uv` (lockfile: `uv.lock`)    |
| Build system | Hatchling (`pyproject.toml`)  |

## Core Dependencies

| Package        | Version   | Role                                              |
|----------------|-----------|---------------------------------------------------|
| `fastmcp`      | >=3.0.0   | MCP server framework (tool/resource registration) |
| `numpy`        | >=1.24.0  | Vectorized EML ops; `complex128` dtype throughout |
| `pydantic`     | >=2.0.0   | Data validation (pulled in by FastMCP)            |

## Optional Dependencies

| Group | Package           | Version  | Role                                             |
|-------|-------------------|----------|--------------------------------------------------|
| `dev` | `pytest`          | >=7.0.0  | Unit testing framework                           |
| `dev` | `pytest-asyncio`  | >=0.21.0 | Async test support                               |
| `dev` | `ruff`            | >=0.1.0  | Linting/formatting                               |
| `sr`  | `torch`           | >=2.0.0  | Symbolic regression / EML-Transformer PoC (opt) |

## Linting & Formatting (Trunk)

The project uses [Trunk](https://trunk.io) for multi-linter orchestration.
Config: `.trunk/trunk.yaml`, `.trunk/configs/`.

| Tool           | Version   | Role                           |
|----------------|-----------|-------------------------------|
| `ruff`         | 0.15.10   | Python linting (B, D3, E, F)  |
| `black`        | 26.3.1    | Python formatting              |
| `isort`        | 8.0.1     | Import sorting                 |
| `bandit`       | 1.9.4     | Security scanning (Python)     |
| `checkov`      | 3.2.521   | IaC/policy scanning            |
| `markdownlint` | 0.48.0    | Markdown linting               |
| `prettier`     | 3.8.2     | JSON/YAML/markdown formatting  |
| `trufflehog`   | 3.94.3    | Secret scanning                |
| `taplo`        | 0.10.0    | TOML formatting                |

Ruff select rules: `B`, `D3`, `E`, `F`. Ignores: `E501` (line length, handled by formatters).

## Numerical Precision

All arithmetic uses `numpy.complex128` (128-bit complex, i.e., two 64-bit floats). This is enforced globally via the `DTYPE = np.complex128` constant in `eml_core.py`. Required because EML-based derivations of trig functions and π involve complex intermediates via Euler's formula.

EXP clamping: `[-700.0, 700.0]` to prevent `float64` overflow at `exp(710)`.

## Entry Points

```bash
# Run MCP server
uv run server.py
# OR (via config)
uv --directory /path/to/eml-mcp run server.py
```

Required setup:
```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv sync
```
