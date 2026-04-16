import time

from eml_mcp.database import EMLFormulaDB
from eml_mcp.discovery import DiscoveryEngine


def test_parallel_speedup():
    print("\nBenchmarking Parallel Discovery...")
    db = EMLFormulaDB("test_parallel.db")
    engine = DiscoveryEngine(db)

    iters = 100

    # 1. Sequential
    start = time.time()
    seq_discovered = engine.explore(iterations=iters, workers=1)
    seq_time = time.time() - start
    print(f"Sequential (100 iters): {seq_time:.2f}s, Discovered: {len(seq_discovered)}")

    # 2. Parallel
    start = time.time()
    par_discovered = engine.explore(iterations=iters, workers=4)
    par_time = time.time() - start
    print(f"Parallel (4 workers, 100 iters): {par_time:.2f}s, Discovered: {len(par_discovered)}")

    if par_time < seq_time:
        print(f"Speedup: {seq_time / par_time:.2f}x")
    else:
        print("No speedup observed (likely overhead for small iters)")

    db.close()


if __name__ == "__main__":
    test_parallel_speedup()
