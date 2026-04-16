# Development Guide

Welcome to the `eml-mcp` development guide!

## Environment Setup

This project uses `uv` for dependency management entirely. If you don't have `uv` installed, please install it via astral's scripts.

### 1. Virtual Environment
Run `uv venv` in the root of the project to instantiate `.venv`.

### 2. Synchronization
Install dependencies:
```bash
uv pip sync pyproject.toml
```
During development, if you add dependencies to your `pyproject.toml`, refresh them dynamically:
```bash
uv pip install -e .
```

## Structure

- `src/eml_mcp/` - Internal module code.
    - `primitives.py` - Root EML arithmetic handling float overflows and branching logic.
    - `simplifier.py` - Core Equality Graph implementation. Read this first if looking to inject new reduction `RULES`.
    - `discovery.py` - Evolutionary mutation worker pool implementation.
    - `server.py` - FastMCP server wiring.
- `tests/` - A suite of robust `pytest` workflows. Keep tests running.

## Contribution Workflow

We strictly follow:
- **TDD Pattern**: Write failing tests before patching internal representations.
- **Pure Functions**: Node logic inside `trees.py` must stay purely functional to be compatible with immutable hashing during E-graph population.

When adding new E-graph reductions (`RULES` in `simplifier.py`), observe performance side-effects. Pattern expansions must ideally funnel complex topologies out of permutations rapidly.
