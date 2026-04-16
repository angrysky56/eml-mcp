"""Simplify every formula tree in the catalog in place.

One-shot migration: walks the `formulas` table, applies the semantics-
preserving simplifier (`exp(ln(z))→z`, `ln(exp(z))→z`, constant folding)
to each tree, and writes the simplified form back when K decreases.

Safety: the simplifier is *algebraic*, not numerical, so a simplified
tree must produce identical outputs on the standard test points. The
script verifies this signature-equality before committing each row and
refuses to mutate any row that fails the check.

Default is dry-run — prints a plan. Pass `--apply` to actually write.

Usage:
    uv run python scripts/migrate_simplify_catalog.py
    uv run python scripts/migrate_simplify_catalog.py --apply
    uv run python scripts/migrate_simplify_catalog.py --apply --db /path/to/custom.db
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Make sibling src/ importable when run directly
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eml_mcp.database import EMLFormulaDB, deserialize_signature  # noqa: E402
from eml_mcp.primitives import TEST_POINTS  # noqa: E402
from eml_mcp.simplifier import simplify_tree  # noqa: E402
from eml_mcp.trees import EMLNode, NodeType  # noqa: E402


SIGNATURE_TOLERANCE = 1e-9


def _count_eml_nodes(tree: EMLNode) -> int:
    """Count internal EML nodes (not constants or variables)."""
    if tree.node_type != NodeType.EML:
        return 0
    c = 1
    if tree.left is not None:
        c += _count_eml_nodes(tree.left)
    if tree.right is not None:
        c += _count_eml_nodes(tree.right)
    return c


def _signatures_agree(a: list[complex], b: list[complex]) -> tuple[bool, float]:
    """Return (agree, max_abs_diff). Agree means every point matches within tolerance."""
    if len(a) != len(b):
        return False, math.inf
    max_diff = 0.0
    for x, y in zip(a, b, strict=False):
        # Non-finite on one side but not the other is a disagreement.
        x_finite = math.isfinite(x.real) and math.isfinite(x.imag)
        y_finite = math.isfinite(y.real) and math.isfinite(y.imag)
        if x_finite != y_finite:
            return False, math.inf
        if not x_finite:
            continue
        d = abs(x - y)
        if d > max_diff:
            max_diff = d
    return max_diff <= SIGNATURE_TOLERANCE, max_diff


def plan_migration(db: EMLFormulaDB) -> list[dict]:
    """Build the migration plan without mutating anything.

    Returns a list of per-row plan dicts. Rows where simplification
    produces the same K (or a larger one, which shouldn't happen but
    is defended against) are tagged `skip=True`.
    """
    plan = []
    for row in db.list_formulas():
        name = row["name"]
        try:
            tree = EMLNode.from_dict(json.loads(row["tree_json"]))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            plan.append({"name": name, "skip": True, "reason": f"bad tree_json: {e}"})
            continue

        original_k = tree.node_count
        simplified = simplify_tree(tree)
        new_k = simplified.node_count

        if new_k >= original_k:
            plan.append(
                {
                    "name": name,
                    "skip": True,
                    "reason": "no reduction",
                    "original_k": original_k,
                    "new_k": new_k,
                }
            )
            continue

        # Grammar-preservation guard: refuse to collapse a formula down to a
        # bare constant or variable. The EML grammar is S → 1 | x | eml(S, S);
        # a formula stored as const(2.718) is numerically correct but outside
        # the grammar and breaks downstream uses like `eml_compile`. Seeds
        # like `e` and `zero` *will* fold to literals under constant-folding,
        # and we deliberately keep their symbolic decomposition.
        if _count_eml_nodes(simplified) == 0:
            plan.append(
                {
                    "name": name,
                    "skip": True,
                    "reason": "would collapse to bare const/var (grammar violation)",
                    "original_k": original_k,
                    "new_k": new_k,
                }
            )
            continue

        # Verify signature equivalence on standard test points.
        try:
            old_sig = tree.to_signature(TEST_POINTS)
            new_sig = simplified.to_signature(TEST_POINTS)
        except (ValueError, OverflowError, ZeroDivisionError) as e:
            plan.append(
                {"name": name, "skip": True, "reason": f"signature eval failed: {e}"}
            )
            continue

        agree, max_diff = _signatures_agree(old_sig, new_sig)
        if not agree:
            plan.append(
                {
                    "name": name,
                    "skip": True,
                    "reason": f"signature disagreement (max_diff={max_diff:.2e})",
                    "original_k": original_k,
                    "new_k": new_k,
                }
            )
            continue

        plan.append(
            {
                "name": name,
                "skip": False,
                "original_k": original_k,
                "new_k": new_k,
                "reduction_pct": 100.0 * (original_k - new_k) / max(original_k, 1),
                "max_signature_diff": max_diff,
                "simplified_tree": simplified,
                "new_signature": new_sig,
            }
        )

    return plan


def apply_migration(db: EMLFormulaDB, plan: list[dict]) -> None:
    """Write simplified trees back for every non-skipped plan entry."""
    for entry in plan:
        if entry.get("skip"):
            continue
        note_suffix = (
            f"Simplified from K={entry['original_k']} to K={entry['new_k']} "
            f"by migrate_simplify_catalog."
        )
        db.update_formula_tree(
            name=entry["name"],
            tree=entry["simplified_tree"],
            note=note_suffix,
            signature=entry["new_signature"],
        )


def format_plan(plan: list[dict]) -> str:
    """Human-readable summary table."""
    changed = [p for p in plan if not p.get("skip")]
    skipped = [p for p in plan if p.get("skip")]

    lines = []
    lines.append(f"Migration plan: {len(changed)} formula(s) will be simplified, "
                 f"{len(skipped)} skipped.")
    lines.append("")

    if changed:
        lines.append(f"{'name':<32} {'K before':>10} {'K after':>10} {'reduction':>12}")
        lines.append("-" * 68)
        # Sort by biggest reduction first
        for entry in sorted(changed, key=lambda p: -(p['original_k'] - p['new_k'])):
            lines.append(
                f"{entry['name']:<32} {entry['original_k']:>10d} "
                f"{entry['new_k']:>10d} {entry['reduction_pct']:>11.1f}%"
            )
        total_before = sum(p["original_k"] for p in changed)
        total_after = sum(p["new_k"] for p in changed)
        lines.append("-" * 68)
        lines.append(
            f"{'TOTAL (changed rows)':<32} {total_before:>10d} {total_after:>10d} "
            f"{100.0 * (total_before - total_after) / max(total_before, 1):>11.1f}%"
        )
        lines.append("")

    if skipped:
        lines.append("Skipped rows:")
        for entry in skipped:
            lines.append(f"  {entry['name']}: {entry.get('reason', 'unknown')}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write changes. Default is dry-run.",
    )
    parser.add_argument(
        "--db", default=None,
        help="Override the DB path (default: $EML_DB_PATH or ./eml_formulas.db)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Don't print the plan table, just a summary line.",
    )
    args = parser.parse_args()

    db_path = args.db or os.environ.get("EML_DB_PATH") or "eml_formulas.db"
    if not Path(db_path).exists():
        print(f"error: database not found at {db_path}", file=sys.stderr)
        return 1

    db = EMLFormulaDB(db_path)
    try:
        plan = plan_migration(db)

        if not args.quiet:
            print(format_plan(plan))

        changed = [p for p in plan if not p.get("skip")]
        if not changed:
            print("Nothing to do.")
            return 0

        if args.apply:
            apply_migration(db, plan)
            print(f"Applied {len(changed)} simplification(s) to {db_path}.")
        else:
            print("\nDry run — pass --apply to commit these changes.")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
