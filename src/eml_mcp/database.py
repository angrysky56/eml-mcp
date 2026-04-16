"""
SQLite persistence layer for EML formulas and derivation provenance.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from eml_mcp.primitives import TEST_POINTS
from eml_mcp.trees import EMLNode


def serialize_signature(outputs: list[complex] | None) -> str | None:
    """Serialize a list of complex numbers to JSON for storage."""
    if outputs is None:
        return None
    return json.dumps([{"real": o.real, "imag": o.imag} for o in outputs])


def deserialize_signature(s: str | None) -> list[complex] | None:
    """Deserialize a list of complex numbers from JSON."""
    if not s:
        return None
    try:
        data = json.loads(s)
        return [complex(item["real"], item["imag"]) for item in data]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


class EMLFormulaDB:
    """Manages the SQLite database for EML formulas and results."""

    def __init__(self, db_path: str | Path = "eml_formulas.db"):
        """Initialize the database connection and schema."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

        # Seed if empty
        if not self.list_formulas():
            self._seed_formulas()

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def _create_schema(self) -> None:
        """Create tables if they don't exist."""
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS formulas (
                    name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    tree_json TEXT NOT NULL,
                    rpn TEXT NOT NULL,
                    expression TEXT NOT NULL,
                    depth INTEGER NOT NULL,
                    k INTEGER NOT NULL,
                    leaf_count INTEGER NOT NULL,
                    variables TEXT NOT NULL,
                    signature TEXT, -- JSON array of complex outputs on standard test points
                    note TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS derivations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    formula_name TEXT NOT NULL REFERENCES formulas(name),
                    parent_a TEXT REFERENCES formulas(name),
                    parent_b TEXT REFERENCES formulas(name),
                    method TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    formula_name TEXT NOT NULL REFERENCES formulas(name),
                    passed INTEGER NOT NULL,
                    max_error REAL NOT NULL,
                    tolerance REAL NOT NULL,
                    n_tests INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS regression_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_function TEXT NOT NULL,
                    depth INTEGER NOT NULL,
                    variables TEXT NOT NULL,
                    weights TEXT NOT NULL,
                    snap_result TEXT,
                    mse REAL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS discovery_jobs (
                    job_id TEXT PRIMARY KEY,
                    target_expression TEXT NOT NULL,
                    status TEXT NOT NULL,
                    iterations_requested INTEGER NOT NULL,
                    iterations_done INTEGER NOT NULL DEFAULT 0,
                    tolerance REAL NOT NULL,
                    stagnation_limit INTEGER,
                    workers INTEGER NOT NULL DEFAULT 1,
                    best_mse REAL,
                    best_k INTEGER,
                    best_expression TEXT,
                    result_json TEXT,
                    error TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    tiles_json TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                    ON discovery_jobs(status, created_at DESC);
            """)
            # Migration: add signature column if missing
            try:
                self.conn.execute("ALTER TABLE formulas ADD COLUMN signature TEXT;")
            except sqlite3.OperationalError:
                pass  # Already exists

    def _seed_formulas(self) -> None:
        """Populate the formulas table with initial seed data."""
        # Note: We import here to avoid circular dependencies if someone imports DB in registry
        from eml_mcp.registry import SEED_FORMULAS

        for name, entry in SEED_FORMULAS.items():
            builder = entry["builder"]
            tree = builder()
            self.add_formula(
                name=name,
                description=entry["description"],
                tree=tree,
                variables=entry["variables"],
                note=entry.get("note"),
            )
            self.add_derivation(
                formula_name=name,
                parent_a=None,
                parent_b=None,
                method="seed",
            )

    # Formula CRUD
    def get_formula(self, name: str, include_verification: bool = True) -> dict[str, Any] | None:
        """Retrieve a formula by name, optionally with latest verification."""
        cursor = self.conn.execute("SELECT * FROM formulas WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        if include_verification:
            cursor = self.conn.execute(
                "SELECT passed, max_error, created_at FROM verifications "
                "WHERE formula_name = ? ORDER BY created_at DESC LIMIT 1",
                (name,),
            )
            v_row = cursor.fetchone()
            if v_row:
                data["latest_verification"] = dict(v_row)
                data["verification_passed"] = v_row["passed"]
                data["max_error"] = v_row["max_error"]

        return data

    def list_formulas(self) -> list[dict[str, Any]]:
        """List all stored formulas."""
        cursor = self.conn.execute("SELECT * FROM formulas ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

    def search_formulas(self, query: str) -> list[dict[str, Any]]:
        """Search formulas by name or description."""
        pattern = f"%{query}%"
        cursor = self.conn.execute(
            "SELECT * FROM formulas WHERE name LIKE ? OR description LIKE ? ORDER BY name",
            (pattern, pattern),
        )
        return [dict(row) for row in cursor.fetchall()]

    def add_formula(
        self,
        name: str,
        description: str,
        tree: EMLNode,
        variables: list[str],
        note: str | None = None,
        signature: list[complex] | None = None,
    ) -> None:
        """Add a new formula to the database."""
        if signature is None:
            signature = tree.to_signature(TEST_POINTS)

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO formulas (
                    name, description, tree_json, rpn, expression,
                    depth, k, leaf_count, variables, note, signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    json.dumps(tree.to_dict()),
                    " ".join(tree.to_rpn()),
                    tree.to_expression(),
                    tree.depth,
                    tree.node_count,
                    tree.leaf_count,
                    json.dumps(variables),
                    note,
                    serialize_signature(signature),
                ),
            )

    def formula_exists(self, name: str) -> bool:
        """Check if a formula exists."""
        cursor = self.conn.execute("SELECT 1 FROM formulas WHERE name = ?", (name,))
        return cursor.fetchone() is not None

    def update_formula_tree(
        self,
        name: str,
        tree: EMLNode,
        note: str | None = None,
        signature: list[complex] | None = None,
    ) -> None:
        """Replace the tree of an existing formula.

        Used by (a) the catalog-simplifier migration script to compress
        stored trees in place, and (b) evolutionary discovery when a new
        search finds a functionally-equivalent tree with a lower K than
        the currently-stored form.

        Preserves name, description, variables, created_at; updates
        tree_json, rpn, expression, depth, k, leaf_count, signature,
        updated_at, and optionally note.

        Args:
            name: Primary key of the formula to update.
            tree: New EMLNode to persist.
            note: Optional replacement note. If None, the existing note
                is kept.
            signature: Optional precomputed signature. If None, recompute
                from the tree on TEST_POINTS.
        """
        if signature is None:
            signature = tree.to_signature(TEST_POINTS)

        # Build the UPDATE dynamically only if `note` is provided, so callers
        # who just want to swap the tree don't blank the existing note.
        fields = [
            "tree_json = ?",
            "rpn = ?",
            "expression = ?",
            "depth = ?",
            "k = ?",
            "leaf_count = ?",
            "signature = ?",
            "updated_at = datetime('now')",
        ]
        params: list[Any] = [
            json.dumps(tree.to_dict()),
            " ".join(tree.to_rpn()),
            tree.to_expression(),
            tree.depth,
            tree.node_count,
            tree.leaf_count,
            serialize_signature(signature),
        ]
        if note is not None:
            fields.append("note = ?")
            params.append(note)
        params.append(name)

        with self.conn:
            cursor = self.conn.execute(
                f"UPDATE formulas SET {', '.join(fields)} WHERE name = ?",
                params,
            )
            if cursor.rowcount == 0:
                raise sqlite3.Error(f"No formula named {name!r} to update")

    # Derivation provenance
    def add_derivation(
        self,
        formula_name: str,
        parent_a: str | None,
        parent_b: str | None,
        method: str,
        details: dict | None = None,
    ) -> int:
        """Record formula derivation provenance."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO derivations (formula_name, parent_a, parent_b, method, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    formula_name,
                    parent_a,
                    parent_b,
                    method,
                    json.dumps(details) if details else None,
                ),
            )
            return cursor.lastrowid

    def get_derivations(self, formula_name: str) -> list[dict[str, Any]]:
        """Get derivation history for a formula."""
        cursor = self.conn.execute(
            "SELECT * FROM derivations WHERE formula_name = ?", (formula_name,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # Verification history
    def add_verification(
        self,
        formula_name: str,
        passed: bool,
        max_error: float,
        tolerance: float,
        n_tests: int,
        details: list[dict],
    ) -> int:
        """Log a verification result."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO verifications (
                    formula_name, passed, max_error, tolerance, n_tests, details
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    formula_name,
                    int(passed),
                    max_error,
                    tolerance,
                    n_tests,
                    json.dumps(details),
                ),
            )
            return cursor.lastrowid

    def get_verifications(self, formula_name: str) -> list[dict[str, Any]]:
        """Get verification history for a formula."""
        cursor = self.conn.execute(
            "SELECT * FROM verifications WHERE formula_name = ? ORDER BY created_at DESC",
            (formula_name,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # Regression results
    def add_regression_result(
        self,
        target_function: str,
        depth: int,
        variables: list[str],
        weights: list[float],
        snap_result: dict | None = None,
        mse: float | None = None,
    ) -> int:
        """Log a regression attempt result."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO regression_results (
                    target_function, depth, variables, weights, snap_result, mse
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    target_function,
                    depth,
                    json.dumps(variables),
                    json.dumps(weights),
                    json.dumps(snap_result) if snap_result else None,
                    mse,
                ),
            )
            return cursor.lastrowid
