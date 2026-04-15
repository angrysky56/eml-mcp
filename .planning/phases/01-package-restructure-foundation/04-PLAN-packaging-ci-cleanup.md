---
plan: "04"
phase: "1"
wave: 3
depends_on: ["01", "02", "03"]
objective: "Update pyproject.toml for src-layout, add GitHub Actions CI, remove old root-level files"
files_modified:
  - pyproject.toml
  - .github/workflows/ci.yml
  - eml_core.py (DELETE)
  - server.py (DELETE)
requirements: [PKG-05, CI-01, CI-02, CI-03, CI-04]
autonomous: true
must_haves:
  - pyproject.toml build target points to src/eml_mcp/ not root files
  - uv run eml-mcp launches the MCP server
  - GitHub Actions CI runs on push and PR to main
  - Deleting root files only after all tests pass
---

## Objective

Wire the package together at the project level: update `pyproject.toml` for the `src/` layout, add a CI workflow, verify end-to-end startup, then remove the now-superseded root-level files.

---

## Task 1: Update pyproject.toml

<read_first>
- pyproject.toml (full file — understand current build config)
- src/eml_mcp/__init__.py (confirm package structure matches)
</read_first>

<action>
Replace the `[tool.hatch.build.targets.wheel]` section and add `[tool.pytest.ini_options]` and `[tool.ruff]` sections. The full updated `pyproject.toml` must be:

```toml
[project]
name = "eml-mcp"
version = "0.1.0"
description = "MCP server for the EML (Exp-Minus-Log) Sheffer operator — all elementary functions from a single binary operator"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=3.0.0",
    "numpy>=1.24.0",
    "pydantic>=2.0.0",
]

[project.scripts]
eml-mcp = "eml_mcp.__main__:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
sr = [
    "torch>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/eml_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
src = ["src"]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

**Important:** The `[project.scripts]` entry point requires adding a `main()` function. Update `src/eml_mcp/__main__.py` to also expose `main`:

```python
"""Entry point for `python -m eml_mcp` and `uv run eml-mcp`."""

from eml_mcp.server import mcp


def main() -> None:
    """Entry point for the `eml-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
```
</action>

<acceptance_criteria>
- `grep "packages = \[\"src/eml_mcp\"\]" pyproject.toml` returns 1 match
- `grep "eml-mcp = \"eml_mcp.__main__:main\"" pyproject.toml` returns 1 match
- `grep "testpaths = \[\"tests\"\]" pyproject.toml` returns 1 match
- `grep "pythonpath = \[\"src\"\]" pyproject.toml` returns 1 match
</acceptance_criteria>

---

## Task 2: Create GitHub Actions CI workflow

<read_first>
- pyproject.toml (understand dev dependencies: pytest, ruff)
- .trunk/trunk.yaml (if exists — understand current trunk config to align CI with it)
</read_first>

<action>
Create `.github/workflows/ci.yml` with this exact content:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint with ruff (format check)
        run: uv run ruff format --check src/ tests/

      - name: Lint with ruff (lint check)
        run: uv run ruff check src/ tests/

      - name: Run tests
        run: uv run pytest tests/ -v --tb=short

      - name: Upload coverage (optional, non-blocking)
        if: always()
        run: |
          uv run pytest tests/ --cov=eml_mcp --cov-report=term-missing -q || true
```
</action>

<acceptance_criteria>
- `ls .github/workflows/ci.yml` shows file exists
- `grep "on:" .github/workflows/ci.yml` returns 1 match
- `grep "push:" .github/workflows/ci.yml` returns 1 match
- `grep "pull_request:" .github/workflows/ci.yml` returns 1 match
- `grep "uv run pytest" .github/workflows/ci.yml` returns 1 match
- `grep "ruff" .github/workflows/ci.yml | wc -l` prints `2`
</acceptance_criteria>

---

## Task 3: End-to-end verification before root cleanup

<read_first>
- src/eml_mcp/__init__.py
- src/eml_mcp/server.py
- tests/test_formulas.py
</read_first>

<action>
Run the full verification suite before deleting any files:

```bash
cd /home/ty/Repositories/ai_workspace/eml-mcp
source .venv/bin/activate

# 1. Confirm package imports correctly
python -c "import eml_mcp; print('Package imports OK')"

# 2. Run all tests from package (NOT from old root imports)
# Temporarily rename old files to force tests to use package imports
mv eml_core.py eml_core.py.bak
mv server.py server.py.bak

python -m pytest tests/ -v --tb=short

# 3. If tests pass, restore files for next check
# (they are deleted in task 4 only if pytest exits 0)
```

If `pytest` exits non-zero, restore the backup files and stop — do not proceed to Task 4.
</action>

<acceptance_criteria>
- `python -m pytest tests/ -v --tb=short` exits 0
- Output contains `passed` with no `failed` or `error`
- Output contains `test_exp_numerical PASSED`
- Output contains `test_ln_numerical PASSED`
</acceptance_criteria>

---

## Task 4: Remove old root-level files

<read_first>
- Task 3 output (MUST be passing before this task runs)
</read_first>

<action>
Only execute this task after Task 3 (pytest) exits 0.

```bash
cd /home/ty/Repositories/ai_workspace/eml-mcp

# Remove backups created in Task 3 (or originals if Task 3 didn't rename)
rm -f eml_core.py eml_core.py.bak
rm -f server.py server.py.bak
rm -rf __pycache__

# Confirm removal
ls *.py 2>/dev/null && echo "ERROR: .py files remain in root" || echo "Root .py files removed OK"
```

Then run tests once more to confirm nothing is broken after file removal:

```bash
python -m pytest tests/ -q --tb=short
```
</action>

<acceptance_criteria>
- `ls eml_core.py` exits non-zero (file does not exist)
- `ls server.py` exits non-zero (file does not exist)
- `python -m pytest tests/ -q` exits 0 after file removal
- `python -m eml_mcp --help 2>&1 | grep -i "mcp\|error"` exits 0 or shows MCP server help (not ImportError)
</acceptance_criteria>

---

## Task 5: Commit all Phase 1 changes

<read_first>
- .git/HEAD (confirm on correct branch)
</read_first>

<action>
```bash
cd /home/ty/Repositories/ai_workspace/eml-mcp
git add src/ tests/ .github/ pyproject.toml
git rm --cached eml_core.py server.py 2>/dev/null || true
git status
git commit -m "feat(pkg): restructure into src/eml_mcp/ package with tests and CI

- Split eml_core.py into operator.py, trees.py, registry.py
- Migrate server.py to src/eml_mcp/server.py with updated imports
- Add tests/test_formulas.py covering all 8 EML formulas
- Update pyproject.toml for src-layout + add entry point
- Add .github/workflows/ci.yml (lint + test on push/PR)

Closes PKG-01, PKG-02, PKG-03, PKG-04, PKG-05
Closes TEST-01, CI-01, CI-02, CI-03, CI-04"
```
</action>

<acceptance_criteria>
- `git log --oneline -1` contains `feat(pkg): restructure into src/eml_mcp/`
- `git show --stat HEAD | grep "src/eml_mcp"` returns multiple lines
- `git show --stat HEAD | grep "tests/"` returns at least 1 line
- `git show --stat HEAD | grep ".github"` returns 1 line
</acceptance_criteria>
