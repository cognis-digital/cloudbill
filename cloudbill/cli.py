"""Command-line interface for CLOUDBILL."""
from __future__ import annotations

import argparse
import csv as _csv
import io
import json
import sys
from typing import Any

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    CloudBillError,
    detect_anomalies,
    load_records,
    summarize,
    to_focus,
)


def _read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _csv_rows(data: Any) -> list[dict[str, Any]]:
    """Flatten the common report/anomaly/focus shapes into CSV rows.

    - ``focus`` export is already a list of flat row dicts.
    - ``report`` emits one row per group (the per-group breakdown).
    - ``anomalies`` emits one row per detected anomaly.
    Anything else falls back to a single key/value row set.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "groups" in data:
        return data["groups"]
    if isinstance(data, dict) and "anomalies" in data:
        return data["anomalies"]
    if isinstance(data, dict):
        return [data]
    return [{"value": data}]


def _emit(data: Any, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(data, indent=2, sort_keys=False))
    elif fmt == "csv":
        rows = _csv_rows(data)
        if not rows:
            return
        # Union of keys, preserving first-seen order, so ragged rows survive.
        cols: list[str] = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        buf = io.StringIO()
        writer = _csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore",
                                 lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        sys.stdout.write(buf.getvalue())
    else:
        _print_table(data)


def _print_table(data: Any) -> None:
    # Render the common report/anomaly/export shapes as aligned text tables.
    if isinstance(data, dict) and "groups" in data:
        print(f"Total: {data['total_cost']} {data['currency']}  "
              f"({data['record_count']} records)")
        rng = data.get("date_range")
        if rng:
            print(f"Period: {rng['start']} -> {rng['end']}")
        print(f"\n{'GROUP':<28}{'COST':>14}{'PCT':>9}")
        print("-" * 51)
        for g in data["groups"]:
            print(f"{g['group']:<28}{g['cost']:>14.2f}{g['pct']:>8.1f}%")
        return
    if isinstance(data, dict) and "anomalies" in data:
        rows = data["anomalies"]
        print(f"Anomalies found: {data['count']}")
        if rows:
            print(f"\n{'GROUP':<22}{'DATE':<12}{'COST':>12}"
                  f"{'BASELINE':>12}{'Z':>7}  SEVERITY")
            print("-" * 78)
            for a in rows:
                print(f"{a['group']:<22}{a['date']:<12}{a['cost']:>12.2f}"
                      f"{a['baseline']:>12.2f}{a['deviation']:>7.1f}  "
                      f"{a['severity']}")
        return
    if isinstance(data, list):
        if not data:
            print("(no rows)")
            return
        cols = list(data[0].keys())
        widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in data)) for c in cols}
        print("  ".join(c.ljust(widths[c]) for c in cols))
        print("  ".join("-" * widths[c] for c in cols))
        for r in data:
            print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
        return
    print(json.dumps(data, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Multi-cloud cost report, anomaly detection, and FOCUS export.",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument("--format", choices=("table", "json", "csv"), default="table",
                   help="output format (default: table)")

    sub = p.add_subparsers(dest="command", required=True)

    common_in = argparse.ArgumentParser(add_help=False)
    common_in.add_argument("input", help="cost data file (CSV/JSON), or - for stdin")
    common_in.add_argument("--input-format", choices=("auto", "csv", "json"),
                           default="auto", help="input parse format (default: auto)")
    common_in.add_argument("--group-by",
                           choices=("service", "provider", "account", "region"),
                           default="service", help="grouping dimension")

    sub.add_parser("report", parents=[common_in],
                   help="summarize costs grouped by a dimension")

    an = sub.add_parser("anomalies", parents=[common_in],
                        help="detect daily spend spikes")
    an.add_argument("--threshold", type=float, default=2.5,
                    help="z-score threshold (default: 2.5)")
    an.add_argument("--min-history", type=int, default=3,
                    help="min prior days before flagging (default: 3)")

    sub.add_parser("focus", parents=[common_in],
                   help="export records as FOCUS-conformant rows")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = _read_input(args.input)
        records = load_records(text, fmt=args.input_format)

        if args.command == "report":
            result: Any = summarize(records, group_by=args.group_by)
        elif args.command == "anomalies":
            found = detect_anomalies(
                records,
                group_by=args.group_by,
                z_threshold=args.threshold,
                min_history=args.min_history,
            )
            result = {"count": len(found), "group_by": args.group_by,
                      "anomalies": [a.as_dict() for a in found]}
        elif args.command == "focus":
            result = to_focus(records)
        else:  # pragma: no cover - argparse enforces choices
            parser.error(f"unknown command: {args.command}")
            return 2
    except (CloudBillError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _emit(result, args.format)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
