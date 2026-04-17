"""Background discovery jobs.

Runs `DiscoveryEngine.find_target` on a worker thread so the MCP server
stays responsive. Every job is checkpointed to SQLite so:

* progress can be polled (`status`, `iterations_done`, `best_mse`, …),
* cancellation is cooperative but persistent (cancel flag lives in the row),
* results survive a server restart.

Concurrency model
-----------------
One `threading.Thread` per job. Threads share the same sqlite3 connection
as the main server (opened with `check_same_thread=False`); writes go
through short transactions so contention is bounded. The DiscoveryEngine
itself may fan out to `ProcessPoolExecutor` workers for the inner search;
that parallelism is orthogonal to the job threading.

The cancel flag is checked every iteration inside the progress callback,
so cancellation latency is one iteration of the evolutionary loop
(milliseconds to seconds depending on tree complexity).
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from typing import Any

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryCancelled, DiscoveryEngine

logger = logging.getLogger(__name__)


# How often to flush progress to the DB (in iterations). Too small and
# we hammer SQLite; too large and status polls look stale.
PROGRESS_FLUSH_EVERY = 5


class JobStore:
    """Thin wrapper over the discovery_jobs table."""

    def __init__(self, db: EMLFormulaDB):
        self.db = db
        # Per-job threads, tracked so we can join them on shutdown if we
        # ever want to. Keyed by job_id.
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        # Sweep any stale `running` rows left over from a previous process
        # that crashed or was killed. These are genuine orphans — no
        # worker thread is actually driving them anymore. Mark as failed
        # so clients don't poll them forever.
        self._sweep_orphans()

    def _sweep_orphans(self) -> None:
        """Mark pre-existing `running` rows as failed on startup."""
        with self.db.conn:
            cur = self.db.conn.execute("""
                UPDATE discovery_jobs
                   SET status = 'failed',
                       error = 'orphaned by server restart',
                       completed_at = datetime('now'),
                       updated_at = datetime('now')
                 WHERE status = 'running'
                """)
            if cur.rowcount > 0:
                logger.info(
                    "Swept %d orphaned running job(s) on startup",
                    cur.rowcount,
                )

    # ---- row I/O -------------------------------------------------------

    def create(
        self,
        target_expression: str,
        iterations: int,
        tolerance: float,
        stagnation_limit: int | None,
        workers: int,
    ) -> str:
        """Insert a `running` job row and return its new job_id."""
        job_id = f"job_{secrets.token_hex(6)}"
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO discovery_jobs (
                    job_id, target_expression, status,
                    iterations_requested, tolerance, stagnation_limit, workers
                ) VALUES (?, ?, 'running', ?, ?, ?, ?)
                """,
                (
                    job_id,
                    target_expression,
                    iterations,
                    tolerance,
                    stagnation_limit,
                    workers,
                ),
            )
        return job_id

    def get(self, job_id: str) -> dict[str, Any] | None:
        cur = self.db.conn.execute(
            "SELECT * FROM discovery_jobs WHERE job_id = ?", (job_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        cur = self.db.conn.execute(
            "SELECT * FROM discovery_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

    def request_cancel(self, job_id: str) -> bool:
        """Flip the cancel flag. Returns True if the job existed and was
        still running."""
        with self.db.conn:
            cur = self.db.conn.execute(
                """
                UPDATE discovery_jobs
                   SET cancel_requested = 1,
                       updated_at = datetime('now')
                 WHERE job_id = ? AND status = 'running'
                """,
                (job_id,),
            )
        return cur.rowcount > 0

    def _is_cancel_requested(self, job_id: str) -> bool:
        cur = self.db.conn.execute(
            "SELECT cancel_requested FROM discovery_jobs WHERE job_id = ?",
            (job_id,),
        )
        row = cur.fetchone()
        return bool(row and row["cancel_requested"])

    def _flush_progress(
        self,
        job_id: str,
        iterations_done: int,
        best_mse: float | None,
        best_k: int | None,
        best_expression: str | None,
        tiles: dict | None = None,
    ) -> None:
        with self.db.conn:
            self.db.conn.execute(
                """
                UPDATE discovery_jobs
                   SET iterations_done = ?,
                       best_mse = ?,
                       best_k = ?,
                       best_expression = ?,
                       tiles_json = ?,
                       updated_at = datetime('now')
                 WHERE job_id = ?
                """,
                (
                    iterations_done,
                    best_mse,
                    best_k,
                    best_expression,
                    json.dumps(tiles) if tiles else None,
                    job_id,
                ),
            )

    def _finish(
        self,
        job_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        # When we have a structured result, promote the final winner into
        # the row's top-level progress columns so `best_mse` / `best_k` /
        # `best_expression` match what `eml_discover_result` actually
        # returns. Otherwise the row would reflect the top-of-heap from
        # the last progress flush, which the finalization pass may have
        # beaten.
        final_mse: float | None = None
        final_k: int | None = None
        final_expr: str | None = None
        if result:
            winner = result.get("exact_match")
            if winner is None:
                nearby = result.get("nearby_discoveries") or []
                winner = nearby[0] if nearby else None
            if winner:
                final_mse = winner.get("mse")
                final_k = winner.get("k")
                final_expr = winner.get("expression")

        with self.db.conn:
            if final_mse is not None:
                self.db.conn.execute(
                    """
                    UPDATE discovery_jobs
                       SET status = ?,
                           result_json = ?,
                           error = ?,
                           best_mse = ?,
                           best_k = ?,
                           best_expression = ?,
                           completed_at = datetime('now'),
                           updated_at = datetime('now')
                     WHERE job_id = ?
                    """,
                    (
                        status,
                        json.dumps(result) if result else None,
                        error,
                        final_mse,
                        final_k,
                        final_expr,
                        job_id,
                    ),
                )
            else:
                # No finalized winner available — leave best_* alone.
                self.db.conn.execute(
                    """
                    UPDATE discovery_jobs
                       SET status = ?,
                           result_json = ?,
                           error = ?,
                           completed_at = datetime('now'),
                           updated_at = datetime('now')
                     WHERE job_id = ?
                    """,
                    (
                        status,
                        json.dumps(result) if result else None,
                        error,
                        job_id,
                    ),
                )

    # ---- thread launcher ----------------------------------------------

    def start_job(
        self,
        target_expression: str,
        iterations: int = 500,
        tolerance: float = 1e-8,
        stagnation_limit: int | None = 200,
        workers: int = 1,
    ) -> str:
        """Create a job row and spawn a worker thread. Returns job_id."""
        job_id = self.create(
            target_expression=target_expression,
            iterations=iterations,
            tolerance=tolerance,
            stagnation_limit=stagnation_limit,
            workers=workers,
        )

        # Spawn the worker. daemon=True means it won't block interpreter
        # exit; the job row already encodes state for polling/resumption.
        thread = threading.Thread(
            target=self._run_job,
            name=f"discovery-{job_id}",
            kwargs={
                "job_id": job_id,
                "target_expression": target_expression,
                "iterations": iterations,
                "tolerance": tolerance,
                "stagnation_limit": stagnation_limit,
                "workers": workers,
            },
            daemon=True,
        )
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return job_id

    def _make_progress_callback(self, job_id: str):
        """Returns a callback the DiscoveryEngine can invoke per iteration.

        The callback both (a) flushes progress and (b) raises
        DiscoveryCancelled if a cancel has been requested — the engine
        catches this and returns the best-so-far cleanly.
        """
        state = {"last_flush_iter": -1}

        def cb(
            iteration: int,
            best_mse: float | None,
            best_k: int | None,
            best_expression: str | None,
        ) -> None:
            # Cancellation is checked on every callback so latency stays low.
            if self._is_cancel_requested(job_id):
                raise DiscoveryCancelled(iteration=iteration)

            # Progress flush is throttled to avoid DB thrash.
            if iteration - state["last_flush_iter"] >= PROGRESS_FLUSH_EVERY:
                self._flush_progress(
                    job_id=job_id,
                    iterations_done=iteration,
                    best_mse=best_mse,
                    best_k=best_k,
                    best_expression=best_expression,
                )
                state["last_flush_iter"] = iteration

        return cb

    def _run_job(
        self,
        job_id: str,
        target_expression: str,
        iterations: int,
        tolerance: float,
        stagnation_limit: int | None,
        workers: int,
    ) -> None:
        """Thread entry point. Wraps `find_target` with status updates."""
        start = time.monotonic()
        engine = DiscoveryEngine(self.db)
        progress_cb = self._make_progress_callback(job_id)

        try:
            result = engine.find_target(
                target=target_expression,
                max_iterations=iterations,
                tolerance=tolerance,
                stagnation_limit=stagnation_limit,
                workers=workers,
                progress_callback=progress_cb,
            )
            elapsed = time.monotonic() - start
            result["elapsed_seconds"] = round(elapsed, 2)
            self._finish(job_id, status="completed", result=result)
            logger.info(
                "Job %s completed in %.1fs (target=%r)",
                job_id,
                elapsed,
                target_expression,
            )
        except DiscoveryCancelled as c:
            # Still try to preserve the best candidate so far.
            partial = getattr(c, "partial_result", None)
            self._finish(job_id, status="cancelled", result=partial)
            logger.info("Job %s cancelled at iter %d", job_id, c.iteration)
        except Exception as e:  # noqa: BLE001 — worker must never leak
            self._finish(job_id, status="failed", error=f"{type(e).__name__}: {e}")
            logger.exception("Job %s failed", job_id)
        finally:
            with self._lock:
                self._threads.pop(job_id, None)


# Module-level singleton, lazily constructed in the MCP server.
_job_store: JobStore | None = None


def get_job_store(db: EMLFormulaDB) -> JobStore:
    """Singleton accessor tied to the DB instance used by the server."""
    global _job_store
    if _job_store is None or _job_store.db is not db:
        _job_store = JobStore(db)
    return _job_store
