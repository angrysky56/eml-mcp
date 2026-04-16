import os
import time

import pytest

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine


@pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Parallel speedup benchmark is too slow for CI"
)
def test_parallel_speedup():
    print("\nBenchmarking Parallel Discovery...")
    db_path = "test_parallel_benchmark.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = EMLFormulaDB(db_path)
    engine = DiscoveryEngine(db)

    # 100 iterations is enough to see the benefit of parallelization
    iters = 100

    # 1. Sequential
    start = time.time()
    seq_discovered = engine.explore(iterations=iters, workers=1)
    seq_time = time.time() - start
    print(f"Sequential ({iters} iters): {seq_time:.2f}s, Discovered: {len(seq_discovered)}")

    workers = min(4, os.cpu_count() or 1)
    # Reset cache for fair comparison
    engine._cache_synced = False

    # 2. Parallel
    start = time.time()
    par_discovered = engine.explore(iterations=iters, workers=workers)
    par_time = time.time() - start
    print(
        f"Parallel ({workers} workers, {iters} iters): {par_time:.2f}s, Discovered: {len(par_discovered)}"
    )

    if par_time < seq_time:
        print(f"Speedup: {seq_time / par_time:.2f}x")
    else:
        print("No speedup observed (parallel overhead might be high for small tasks)")

    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    test_parallel_speedup()
