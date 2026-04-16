# Phase 5 Plan: Symbolic Regression & Parallel Discovery

Implement the gradient-based Symbolic Regression pipeline and refactor the Discovery Engine for parallel execution.

## 1. Research & Specification

- [ ] Define `MasterFormulaTree` architecture with `torch`.
- [ ] Specify "Selection Gate" mechanism for leaf inputs (constants + variables).
- [ ] Design the Adam optimization loop with "clamping" to avoid EML overflows.
- [ ] Research `multiprocessing` integration for `DiscoveryEngine` to avoid GIL bottlenecks.

## 2. Implementation - Symbolic Regression (`regression.py`)

- [ ] Create `src/eml_mcp/regression.py`.
- [ ] Implement `EMLOperator` as a custom autograd function (or just use `torch.exp(x) - torch.log(y)` with appropriate complex handling).
- [ ] Implement `SelectionGate(torch.nn.Module)`:
    - Inputs: `[1, x, e, 0, ...]`
    - Weights: `nn.Parameter`
    - Output: $\sum w_i v_i$
- [ ] Implement `EMLMasterTree(torch.nn.Module)`:
    - Recursively builds a complete binary tree of depth $n$.
    - Leaves are `SelectionGate` instances.
- [ ] Implement `Trainer`:
    - MSE loss function.
    - Adam optimizer.
    - Clamping logic (arguments to exp limited to ~700).
    - Hardening phase: penalizing weights that are not 0 or 1.

## 3. Implementation - Parallel Discovery (`discovery.py`)

- [ ] Add `multiprocessing` support to `DiscoveryEngine`.
- [ ] Implement `ParallelDiscoveryManager`:
    - Distributes work across CPU cores.
    - Collects top-N results from each worker.
    - Aggregates and ranks globally.

## 4. Integration & Tools

- [ ] Update `eml_mcp/server.py`:
    - Upgrade `eml_master_tree` to perform actual optimization.
    - Modify `eml_discover` to allow `--parallel` mode.
- [ ] Handle `torch` optional dependency:
    - Ensure tools return informative errors if `torch` is not installed.

## 5. Verification & Finalization

- [ ] **TDD**: Recover `ln(x)` from data points using `EMLMasterTree` at depth 3.
- [ ] **Benchmark**: Compare single-threaded vs multi-threaded discovery speed for depth-5 compositions.
- [ ] Update `STATE.md` to reflect Phase 5 completion.

## Verification Items (UAT)

1. `eml_master_tree(depth=1, target="x**2")` recovers something close to the EML representation of $x^2$.
2. `eml_discover(..., parallel=True)` utilizes multiple cores (verified via `top` or similar).
3. System stays functional even if `torch` is missing (graceful degradation).
