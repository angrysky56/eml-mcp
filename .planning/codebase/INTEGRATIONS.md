# INTEGRATIONS.md — External Integrations

## MCP Protocol

The server implements the **Model Context Protocol (MCP)** via [FastMCP](https://github.com/jlowin/fastmcp).

- **Transport:** Stdio (default FastMCP transport — reads from stdin, writes to stdout)
- **Protocol version:** MCP compliant (version determined by fastmcp >=3.0.0)
- **Server name:** `"eml-mcp"` (set in `FastMCP("eml-mcp")` in `server.py`)

### Tool Annotations (MCP Hints)

Every tool is registered with the following standard MCP annotations:

```python
{
    "readOnlyHint": True,       # All tools are read-only (no side effects)
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,     # Results depend only on inputs
}
```

### Exposed Tools

| MCP Tool           | Description                                  |
|--------------------|----------------------------------------------|
| `eml_evaluate`     | Evaluate `eml(x,y) = exp(x) - ln(y)`        |
| `eml_list_formulas`| List all known EML decompositions            |
| `eml_tree_info`    | Inspect a named formula's tree structure     |
| `eml_compile`      | Map expression strings → EML form           |
| `eml_verify`       | Verify EML identity against reference fn     |
| `eml_master_tree`  | Build parameterized master formula trees     |

### Exposed Resources

| MCP URI                   | Description                              |
|---------------------------|------------------------------------------|
| `eml://grammar`           | EML context-free grammar and identities  |
| `eml://complexity-table`  | Full complexity table from the paper     |

## Reference Client Config

Clients integrate via `example_mcp_config.json`:

```json
{
  "mcpServers": {
    "eml-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/eml-mcp", "run", "server.py"]
    }
  }
}
```

## External APIs / Databases

**None.** This server has no runtime network dependencies, no database, no auth providers, no webhooks, and no cloud services. It is entirely self-contained.

## Scientific Reference

The mathematical content is based on:
- **Odrzywołek (2026):** "All elementary functions from a single operator" — [arXiv:2603.21852v2](https://arxiv.org/html/2603.21852v2)
- **Related repo:** [SymbolicRegressionPackage](https://github.com/VA00/SymbolicRegressionPackage)

These are informational references only — no runtime API calls are made.

## Related Projects (Ecosystem, Not Integrated at Runtime)

| Project          | Role                                             |
|------------------|--------------------------------------------------|
| `hybrid-ai-mcp`  | Boolean-domain companion (NAND/MCP neurons)      |
| `mcp-logic`      | Automated reasoning server (FOL, Prover9/Mace4)  |

These appear as companion MCP servers but are not runtime dependencies of `eml-mcp`.

## Logging

- **Destination:** `stderr` only (correct for MCP — stdout is the protocol channel)
- **Format:** `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Level:** `INFO`
- **Library:** Python stdlib `logging`
