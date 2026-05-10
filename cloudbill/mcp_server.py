"""CLOUDBILL MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from cloudbill.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-cloudbill[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-cloudbill[mcp]'")
        return 1
    app = FastMCP("cloudbill")

    @app.tool()
    def cloudbill_scan(target: str) -> str:
        """Multi-cloud cost report, anomaly detection, and FOCUS export. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
