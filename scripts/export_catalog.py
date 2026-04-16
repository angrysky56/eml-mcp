#!/usr/bin/env python3
"""
Export the live EML formula catalog from SQLite to Markdown.

Regenerates `docs/FORMULAS.md` from `eml_formulas.db` so the human-readable
catalog stays in sync with whatever the Discovery Engine has learned.

Usage:
    uv run python scripts/export_catalog.py
    uv run python scripts/export_catalog.py --out docs/FORMULAS.md --db eml_formulas.db

The generated file is intended to be committed — it gives reviewers visibility
into the current set of primitives without needing to start the MCP server.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "eml_formulas.db"
DEFAULT_OUT = REPO_ROOT / "docs" / "FORMULAS.md"


def load_formulas(db_path: Path) -> list[dict]:
    """Read every row from the formulas table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("SELECT * FROM formulas ORDER BY k ASC, name ASC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def format_expression(expr: str, max_len: int = 90) -> str:
    """Truncate very long expressions with a pointer to the RPN form."""
    if len(expr) <= max_len:
        return f"`{expr}`"
    return f"`{expr[: max_len - 3]}...` _(see RPN for full form)_"


def render_markdown(formulas: list[dict], db_path: Path) -> str:
    """Render the catalog as a Markdown document."""
    seeds = [f for f in formulas if not f["name"].startswith("discovered")]
    discoveries = [f for f in formulas if f["name"].startswith("discovered")]

    timestamp = datetime.now(tz=UTC).isoformat(timespec="seconds")
    lines: list[str] = []

    lines.append("# EML Formula Catalog")
    lines.append("")
    lines.append(
        f"_Auto-generated from `{db_path.name}` at {timestamp}. "
        "Do not edit by hand — regenerate with `uv run python scripts/export_catalog.py`._"
    )
    lines.append("")
    lines.append("**Grammar:** `S → 1 | eml(S, S)`  ·  **Reference:** Odrzywołek (2026), [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)")
    lines.append("")
    lines.append(
        f"**Totals:** {len(formulas)} formulas "
        f"({len(seeds)} seeded / {len(discoveries)} discovered)"
    )
    lines.append("")

    return "\n".join(lines) + _render_seeds(seeds) + _render_discoveries(discoveries)


def _render_seeds(seeds: list[dict]) -> str:
    """Render the seeded/compiler primitives as a compact table."""
    if not seeds:
        return ""
    parts: list[str] = ["", "## Seeded primitives", ""]
    parts.append("| Name | Variables | Depth | K | Description |")
    parts.append("|------|-----------|------:|--:|-------------|")
    for f in seeds:
        variables = ", ".join(json.loads(f["variables"])) or "—"
        parts.append(
            f"| `{f['name']}` | {variables} | {f['depth']} | {f['k']} | "
            f"{f['description'].replace('|', '\\|')} |"
        )
    parts.append("")
    parts.append("### Seed expressions")
    parts.append("")
    for f in seeds:
        parts.append(f"**`{f['name']}`** — K={f['k']}, depth={f['depth']}, leaves={f['leaf_count']}")
        parts.append("")
        parts.append(f"- Expression: {format_expression(f['expression'])}")
        parts.append(f"- RPN: `{f['rpn']}`")
        if f.get("note"):
            parts.append(f"- Note: {f['note']}")
        parts.append("")
    return "\n".join(parts)


def _render_discoveries(discoveries: list[dict]) -> str:
    """Render the evolutionarily discovered formulas grouped by K."""
    if not discoveries:
        return "\n## Discovered formulas\n\n_None yet. Run `eml_discover` to populate._\n"

    parts: list[str] = ["", "## Discovered formulas", ""]
    parts.append(
        "Formulas below were produced by the evolutionary Discovery Engine "
        "(`eml_discover`) or by gradient-based symbolic regression "
        "(`eml_symbolic_regression`). Each one passed novelty and stability "
        "checks against the prior catalog before being persisted."
    )
    parts.append("")
    parts.append("| Name | K | Depth | Expression | Note |")
    parts.append("|------|--:|------:|------------|------|")
    for f in sorted(discoveries, key=lambda r: (r["k"], r["name"])):
        expr = format_expression(f["expression"], max_len=60)
        note = (f.get("note") or "").replace("|", "\\|")
        parts.append(
            f"| `{f['name']}` | {f['k']} | {f['depth']} | {expr} | {note} |"
        )
    parts.append("")
    return "\n".join(parts)


def main() -> int:
    """Read CLI arguments and export the formula catalog to Markdown."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("EML_DB_PATH", str(DEFAULT_DB))),
        help="Path to eml_formulas.db (env: EML_DB_PATH)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output Markdown path (default: docs/FORMULAS.md)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        parser.error(f"Database not found: {args.db}")

    formulas = load_formulas(args.db)
    markdown = render_markdown(formulas, args.db)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")

    print(
        f"Wrote {len(formulas)} formulas ({sum(1 for f in formulas if not f['name'].startswith('discovered'))} seeded, "
        f"{sum(1 for f in formulas if f['name'].startswith('discovered'))} discovered) "
        f"→ {args.out.relative_to(REPO_ROOT) if args.out.is_relative_to(REPO_ROOT) else args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
