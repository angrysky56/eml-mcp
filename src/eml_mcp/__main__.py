"""Entry point for `python -m eml_mcp` and `uv run eml-mcp`."""

from eml_mcp.server import mcp


def main() -> None:
    """Entry point for the `eml-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
