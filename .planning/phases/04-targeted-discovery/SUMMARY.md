# Walkthrough - Phase 4: Targeted Discovery & Open-Ended Proximity

We have successfully implemented the targeted discovery engine for the EML-MCP server, bridging the gap between open-ended novelty search and goal-directed mathematical derivation.

## Key Accomplishments

### 1. Distance Metrics & Function Similarity
- Implemented `compute_mse` in the `DiscoveryEngine` to quantify functional distance between EML trees.
- Added a `_eval_tree_safe` helper that handles overflow and NaN boundary conditions gracefully during test point evaluation.

### 2. Targeted Search Algorithm
- Created `DiscoveryEngine.find_target()`, which performs a depth-limited search for a target mathematical behavior.
- **Open-Ended Fallback**: If an exact match is not found, the system now returns the top `N` "nearby discoveries" based on their MSE scores. This ensures that even "failed" searches provide valuable candidates for further exploration.

### 3. MCP Tool Integration
- Added the `eml_discover` tool to `server.py`.
- Users can now specify a target Python expression (e.g., `math.sin(x)`) and search for its EML representation.
- The tool provides the exact match if it exists in the registry or if one was discovered during exploration, alongside the best proximal alternatives.

## Verification Results

### Automated Tests
Successfully ran 46 tests across the entire suite, including specific tests for the discovery fallback.
`uv run pytest tests/` -> **46 passed in 0.93s**

![Test Results](file:///home/ty/Repositories/ai_workspace/eml-mcp/tests/test_results.png)
> [!NOTE]
> View the full test output in the terminal logs above.

## Future Exploration Points
- **Structural Similarity**: Implementing a secondary distance metric based on tree edit distance (Zhang-Shasha) to rank formulas by structural simplicity.
- **Deep Bootstrapping**: Using `eml_discover` to find EML forms for more complex primitives like ` Bessel` functions or error functions (`erf`).
