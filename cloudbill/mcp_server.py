"""CLOUDBILL MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from cloudbill.core import load_records, summarize, detect_anomalies

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
    def cloudbill_report(text: str, group_by: str = "service") -> str:
        """Summarize multi-cloud costs from CSV/JSON text. Returns a JSON report."""
        import json as _json
        from cloudbill.core import CloudBillError
        try:
            records = load_records(text)
            return _json.dumps(summarize(records, group_by=group_by))
        except CloudBillError as exc:
            return _json.dumps({"error": str(exc)})

    @app.tool()
    def cloudbill_anomalies(text: str, group_by: str = "service",
                            z_threshold: float = 2.5) -> str:
        """Detect spend anomalies in CSV/JSON cost data. Returns JSON findings."""
        import json as _json
        from cloudbill.core import CloudBillError
        try:
            records = load_records(text)
            found = detect_anomalies(records, group_by=group_by,
                                     z_threshold=z_threshold)
            return _json.dumps({"count": len(found),
                                 "anomalies": [a.as_dict() for a in found]})
        except CloudBillError as exc:
            return _json.dumps({"error": str(exc)})

    app.run()
    return 0
