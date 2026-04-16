#!/usr/bin/env python3
"""
Dedupe the EML formula catalog by output signature.

Groups discovered formulas whose outputs agree on the standard test points
(MSE below --tolerance) and collapses each group to a single canonical entry.

Ranking within a group (best kept, rest removed):
  1. Seeded formulas (names not starting with "discovered") always win.
  2. Lowest K (structural complexity).
  3. Earliest created_at.
  4. Lexicographic name.

Dependent rows in `derivations` and `verifications` are re-pointed to the
kept formula before the loser rows are deleted, preserving provenance.

Default is dry-run. Pass --apply to actually mutate the database.

Usage:
    uv run python scripts/cleanup_duplicates.py              # dry-run report
    uv run python scripts/cleanup_duplicates.py --apply      # actually clean
    uv run python scripts/cleanup_duplicates.py --tolerance 1e-8 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "eml_formulas.db"


def load_formulas(conn: sqlite3.Connection) -> list[dict]:
    """Read every row from the formulas table with parsed signature."""
    cursor = conn.execute("SELECT * FROM formulas ORDER BY name")
    rows = []
    for row in cursor.fetchall():
        d = dict(row)
        sig_raw = d.get("signature")
        if sig_raw:
            try:
                parsed = json.loads(sig_raw)
                d["signature_parsed"] = [complex(p["real"], p["imag"]) for p in parsed]
            except (json.JSONDecodeError, KeyError, TypeError):
                d["signature_parsed"] = None
        else:
            d["signature_parsed"] = None
        rows.append(d)
    return rows


def compute_mse(a: list[complex], b: list[complex]) -> float:
    """MSE between two equal-length complex signatures."""
    if len(a) != len(b) or not a:
        return float("inf")
    return sum(abs(x - y) ** 2 for x, y in zip(a, b, strict=False)) / len(a)


def group_by_signature(formulas: list[dict], tolerance: float) -> list[list[dict]]:
    """Cluster formulas whose signatures agree within `tolerance` (MSE)."""
    groups: list[list[dict]] = []
    for f in formulas:
        if not f["signature_parsed"]:
            # No signature — keep as its own singleton group
            groups.append([f])
            continue

        placed = False
        for group in groups:
            representative = next(
                (g for g in group if g["signature_parsed"] is not None), None
            )
            if representative is None:
                continue
            if compute_mse(f["signature_parsed"], representative["signature_parsed"]) < tolerance:
                group.append(f)
                placed = True
                break
        if not placed:
            groups.append([f])
    return groups


def rank_key(f: dict) -> tuple:
    """Sort key — lower is 'better' (kept first)."""
    is_seeded = 0 if not f["name"].startswith("discovered") else 1
    return (is_seeded, f["k"], f.get("created_at") or "", f["name"])


def find_duplicates(groups: list[list[dict]]) -> list[tuple[dict, list[dict]]]:
    """Return (keeper, losers) pairs for every group with more than one member."""
    pairs: list[tuple[dict, list[dict]]] = []
    for group in groups:
        if len(group) < 2:
            continue
        ranked = sorted(group, key=rank_key)
        pairs.append((ranked[0], ranked[1:]))
    return pairs


def print_report(pairs: list[tuple[dict, list[dict]]], apply: bool) -> None:
    """Render a human-readable dry-run or apply report."""
    mode = "APPLYING" if apply else "DRY RUN"
    print(f"=== Duplicate cleanup — {mode} ===\n")

    if not pairs:
        print("No duplicates found. Catalog is already canonical.")
        return

    total_removed = sum(len(losers) for _, losers in pairs)
    print(f"Found {len(pairs)} duplicate groups, {total_removed} rows marked for removal.\n")

    for keeper, losers in pairs:
        print(f"  KEEP   {keeper['name']}  (K={keeper['k']}, depth={keeper['depth']})")
        print(f"         expression: {keeper['expression'][:70]}")
        for loser in losers:
            print(
                f"  REMOVE {loser['name']}  (K={loser['k']}, depth={loser['depth']})"
            )
        print()


def apply_cleanup(
    conn: sqlite3.Connection, pairs: list[tuple[dict, list[dict]]]
) -> dict[str, int]:
    """Re-point dependent rows to the keeper, then delete the losers.

    Returns counts of affected rows.
    """
    stats = {"derivations_repointed": 0, "verifications_repointed": 0, "formulas_deleted": 0}

    with conn:
        for keeper, losers in pairs:
            keeper_name = keeper["name"]
            loser_names = [loser["name"] for loser in losers]

            # Re-point derivations that reference losers as their formula_name,
            # parent_a, or parent_b — preserves provenance under the canonical name.
            for ln in loser_names:
                cur = conn.execute(
                    "UPDATE derivations SET formula_name = ? WHERE formula_name = ?",
                    (keeper_name, ln),
                )
                stats["derivations_repointed"] += cur.rowcount
                cur = conn.execute(
                    "UPDATE derivations SET parent_a = ? WHERE parent_a = ?",
                    (keeper_name, ln),
                )
                stats["derivations_repointed"] += cur.rowcount
                cur = conn.execute(
                    "UPDATE derivations SET parent_b = ? WHERE parent_b = ?",
                    (keeper_name, ln),
                )
                stats["derivations_repointed"] += cur.rowcount

                cur = conn.execute(
                    "UPDATE verifications SET formula_name = ? WHERE formula_name = ?",
                    (keeper_name, ln),
                )
                stats["verifications_repointed"] += cur.rowcount

                cur = conn.execute("DELETE FROM formulas WHERE name = ?", (ln,))
                stats["formulas_deleted"] += cur.rowcount

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(os.environ.get("EML_DB_PATH", str(DEFAULT_DB))),
        help="Path to eml_formulas.db (env: EML_DB_PATH)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-10,
        help="MSE threshold for signature-equality (default: 1e-10)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the deletions. Without this flag, only prints a report.",
    )
    args = parser.parse_args()

    if not args.db.exists():
        parser.error(f"Database not found: {args.db}")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        formulas = load_formulas(conn)
        groups = group_by_signature(formulas, args.tolerance)
        pairs = find_duplicates(groups)

        print_report(pairs, apply=args.apply)

        if args.apply and pairs:
            stats = apply_cleanup(conn, pairs)
            print("=== Cleanup applied ===")
            print(f"  formulas_deleted:          {stats['formulas_deleted']}")
            print(f"  derivations_repointed:     {stats['derivations_repointed']}")
            print(f"  verifications_repointed:   {stats['verifications_repointed']}")
            print(
                "\nRegenerate docs/FORMULAS.md with: "
                "uv run python scripts/export_catalog.py"
            )
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
