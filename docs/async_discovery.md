# Background Discovery Jobs

`eml_discover` runs synchronously: it blocks the MCP connection until the
search finishes or the MCP client's tool-call timeout fires (4 minutes in
most clients). Any target that can't be solved inside that window — `sin`,
`tan`, composite expressions — drops its partial progress on timeout.

The job-backed tools give you a non-blocking alternative: start a search,
get a handle back in milliseconds, poll for progress, and retrieve the
final result when it's ready.

## API

| Tool                     | Purpose                                            |
| ------------------------ | -------------------------------------------------- |
| `eml_discover_start`     | Launch a search on a background thread, return `job_id` |
| `eml_discover_status`    | Poll `iterations_done`, `best_mse`, `best_k`, `best_expression` |
| `eml_discover_result`    | Fetch the full `exact_match` + `nearby_discoveries` dict |
| `eml_discover_cancel`    | Request cooperative cancel; best-so-far is preserved |
| `eml_discover_list`      | List recent jobs (any status), newest first       |

Statuses: `running` → one of `completed`, `cancelled`, `failed`.

## Typical flow

```python
# 1. Kick off a long-running search.
job = eml_discover_start(target_expression="math.sin(x) + x",
                         iterations=1000, stagnation_limit=300)
jid = job["job_id"]

# 2. Poll whenever convenient — the worker runs in the background.
status = eml_discover_status(jid)
# → {"status": "running", "iterations_done": 82,
#    "best_mse": 0.019, "best_k": 117, "best_expression": "eml(...)"}

# 3a. Retrieve when done.
if status["status"] == "completed":
    result = eml_discover_result(jid)
    # → {"result": {"exact_match": ..., "nearby_discoveries": [...]}}

# 3b. Or cancel early — partial result is still preserved.
eml_discover_cancel(jid)
# → {"status": "cancel_requested", "job_id": "job_..."}
```

## Architecture

Jobs are stored in a `discovery_jobs` table alongside the formula
catalog. Progress is checkpointed to SQLite every 5 iterations, so:

- The **MCP connection is never blocked** — `eml_discover_start` returns
  as soon as the job row is inserted.
- **Status polls are cheap** — a single `SELECT` on an indexed row.
- **Jobs survive a server restart** — rows in state `running` that
  predate the process's start can be treated as stale and cleaned up
  manually, but completed/cancelled/failed rows are permanent.
- **Cancellation is cooperative and persistent** — flipping the
  `cancel_requested` bit is a transactional SQL write; the worker
  checks it on every iteration (millisecond-to-second latency depending
  on tree complexity).

The worker itself is a `threading.Thread`. We use threads rather than
subprocesses because:

- The Python-side search loop in `find_target` is a mix of MSE
  evaluation (numpy-heavy, releases the GIL) and tree-structure
  manipulation. Threading lets multiple jobs share the SQLite
  connection cleanly, and the GIL isn't the bottleneck for a single job.
- Inside one job, CPU-heavy work can still be fanned out to processes
  via `workers=N` (the existing `ProcessPoolExecutor` path). Job threads
  and inner-search processes are orthogonal.

### Files involved

- `src/eml_mcp/jobs.py` — `JobStore` class, thread launcher, progress
  callback factory, finalization.
- `src/eml_mcp/discovery.py` — `DiscoveryEngine.find_target` accepts a
  `progress_callback` parameter; raising `DiscoveryCancelled` from the
  callback exits the loop cleanly and returns the best-so-far result
  attached to the exception.
- `src/eml_mcp/database.py` — adds the `discovery_jobs` table and an
  index on `(status, created_at DESC)` for fast `eml_discover_list`.
- `src/eml_mcp/server.py` — five `@mcp.tool` wrappers over `JobStore`.

## Choosing sync vs. async

Keep using sync `eml_discover` when:

- Target is simple and likely to resolve in seconds (`x + c`, `c*x`,
  reuses of existing catalog entries).
- You want a single round-trip answer with no polling.

Prefer async `eml_discover_start` when:

- Target is a transcendental or composite likely to need many iterations.
- You want progress visibility (the `best_expression` field updates
  throughout the run).
- You might want to cancel if the quality plateau isn't good enough.
- You're running multiple searches in parallel and don't want each to
  serialize the MCP channel.

## Observed cancellation behavior

Typical cancel latency on an in-flight job is **one evolutionary
iteration**, which on hard targets like `sin(x) + x` runs 5–10 seconds
per iteration (the 20 mutants × 3 hill-climb bursts × simplify passes
times ≈ 120-node candidates). On easy targets it's sub-second.

When cancelled, the engine still runs its finalization pass on the
candidates collected up to that point: sort by MSE, simplify the top-N,
construct the `nearby_discoveries` list. The cancelled result dict is
identical in shape to a completed one, just with `exact_match: null` and
a `cancelled_at_iteration` field.

## Known rough edges

- The `best_mse` field on the job row reflects the **top-of-heap at
  progress-flush time**, not necessarily the globally-best candidate.
  The finalization pass may surface a slightly better candidate in
  `nearby_discoveries[0]` because it re-sorts the full working set.
  The result dict is authoritative.
- The `_job_store` singleton binds to a `db` instance by identity.
  If you ever swap the DB connection at runtime, reset the singleton
  explicitly.
- Jobs in state `running` after a server crash stay in that state
  forever. A small cleanup step on server boot (mark pre-start
  `running` rows as `failed` with `error='orphaned by restart'`) would
  close that loop — not implemented yet.
