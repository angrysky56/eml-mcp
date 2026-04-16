# Configuration & Deployment

Since `eml-mcp` operates primarily as a background MCP server interface via `FastMCP` mapped over standard I/O streams, configuration focuses largely on client binding.

## MCP Client Configuration

### Claude Desktop Example (Or general `mcp.json`)

To install `eml-mcp` so your AI assistant can communicate with it, point the config at `uv`:

```json
{
  "mcpServers": {
    "eml-mcp": {
      "command": "/home/ty/.local/bin/uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/eml-mcp",
        "eml-mcp"
      ],
      "env": {}
    }
  }
}
```

### Environment Variables

Currently, `eml-mcp` limits structural parameter configuration to inline arguments passed within tool calls rather than via environment bindings. 
Constants such as CPU parallelism counts (`workers`), thresholding variables (`tolerance`), and timeout conditions (`iterations`) are configurable dynamically via MCP Tool API calls payload dictionaries on a per-session basis.

*(Note: We rely on standard POSIX signaling for cancelling or pausing discovery job threads).*
