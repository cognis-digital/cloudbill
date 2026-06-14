"""Core cost engine for CLOUDBILL.

Standard library only. Defines a normalized CostRecord, loaders for CSV/JSON,
report summarization, time-series anomaly detection, and FOCUS export.
"""
from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Iterable

TOOL_NAME = "cloudbill"
TOOL_VERSION = "0.1.0"

_VALID_GROUP_BY = frozenset({"service", "provider", "account", "region"})

# FOCUS = FinOps Open Cost & Usage Specification. We map our normalized fields
# onto a subset of FOCUS 1.0 column names on export.

# Common column aliases seen across AWS CUR / Azure Cost Management / GCP billing
# exports, mapped to our normalized field names.
_ALIASES: dict[str, tuple[str, ...]] = {
    "provider": ("provider", "cloud", "ProviderName", "BillingAccountType"),
    "account": ("account", "account_id", "BillingAccountId", "SubscriptionId",
                "project_id", "linked_account_id"),
    "service": ("service", "ServiceName", "product", "ServiceCategory",
                "lineItem/ProductCode", "MeterCategory"),
    "region": ("region", "Region", "RegionName", "location", "ResourceLocation"),
    "date": ("date", "usage_date", "UsageDate", "ChargePeriodStart",
             "lineItem/UsageStartDate", "BillingPeriodStart"),
    "cost": ("cost", "BilledCost", "EffectiveCost", "CostInBillingCurrency",
             "UnblendedCost", "lineItem/UnblendedCost", "PretaxCost"),
    "currency": ("currency", "BillingCurrency", "CurrencyCode", "Currency"),
}


class CloudBillError(Exception):
    """Raised on bad input or unrecoverable processing errors."""


@dataclass(frozen=True)
class CostRecord:
    """A single normalized cost/usage line."""

    provider: str
    account: str
    service: str
    region: str
    date: date
    cost: float
    currency: str = "USD"

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class Anomaly:
    """A detected spend anomaly for a (group, date) pair."""

    group: str
    date: str
    cost: float
    baseline: float
    deviation: float  # how many std-devs above baseline (z-score)
    pct_increase: float
    severity: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pick(row: dict[str, Any], field_name: str) -> Any:
    for alias in _ALIASES[field_name]:
        if alias in row and row[alias] not in (None, ""):
            return row[alias]
        # case-insensitive fallback
        for k in row:
            if k.lower() == alias.lower() and row[k] not in (None, ""):
                return row[k]
    return None


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    # Trim time component if present.
    for sep in ("T", " "):
        if sep in s:
            s = s.split(sep, 1)[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise CloudBillError(f"unrecognized date format: {value!r}")


def _parse_cost(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    s = str(value).strip().replace("$", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        raise CloudBillError(f"invalid cost value: {value!r}")


def _record_from_row(row: dict[str, Any], lineno: int) -> CostRecord:
    raw_date = _pick(row, "date")
    raw_cost = _pick(row, "cost")
    if raw_date is None:
        raise CloudBillError(f"row {lineno}: missing a usable date column")
    if raw_cost is None:
        raise CloudBillError(f"row {lineno}: missing a usable cost column")
    return CostRecord(
        provider=str(_pick(row, "provider") or "unknown").lower(),
        account=str(_pick(row, "account") or "unknown"),
        service=str(_pick(row, "service") or "unknown"),
        region=str(_pick(row, "region") or "global"),
        date=_parse_date(raw_date),
        cost=_parse_cost(raw_cost),
        currency=str(_pick(row, "currency") or "USD").upper(),
    )


def load_records(text: str, fmt: str = "auto") -> list[CostRecord]:
    """Parse CSV or JSON cost data into normalized CostRecords.

    JSON may be a list of objects or an object with a top-level "rows"/"data"
    list. CSV must have a header row.
    """
    if not isinstance(text, str):
        raise CloudBillError("input must be a string")
    text = text.strip()
    if not text:
        raise CloudBillError("no input data")

    if fmt == "auto":
        fmt = "json" if text[0] in "[{" else "csv"

    rows: list[dict[str, Any]]
    if fmt == "json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CloudBillError(f"invalid JSON: {exc}") from exc
        if isinstance(parsed, dict):
            for key in ("rows", "data", "records", "lineItems"):
                if isinstance(parsed.get(key), list):
                    parsed = parsed[key]
                    break
            else:
                parsed = [parsed]
        if not isinstance(parsed, list):
            raise CloudBillError("JSON must be a list or contain a list of rows")
        rows = parsed
    elif fmt == "csv":
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    else:
        raise CloudBillError(f"unknown format: {fmt!r}")

    if not rows:
        raise CloudBillError("input contained zero rows")

    records = [_record_from_row(r, i + 1) for i, r in enumerate(rows)]
    return records


def _group_key(rec: CostRecord, dim: str) -> str:
    return {
        "provider": rec.provider,
        "account": rec.account,
        "service": rec.service,
        "region": rec.region,
    }.get(dim, rec.service)


def summarize(
    records: Iterable[CostRecord],
    group_by: str = "service",
) -> dict[str, Any]:
    """Build a cost report grouped by a dimension."""
    if group_by not in _VALID_GROUP_BY:
        raise CloudBillError(
            f"invalid group_by {group_by!r}; "
            f"must be one of {sorted(_VALID_GROUP_BY)}"
        )
    records = list(records)
    if not records:
        raise CloudBillError("no records to summarize")

    by_group: dict[str, float] = {}
    by_day: dict[str, float] = {}
    total = 0.0
    currencies: set[str] = set()
    for rec in records:
        key = _group_key(rec, group_by)
        by_group[key] = by_group.get(key, 0.0) + rec.cost
        d = rec.date.isoformat()
        by_day[d] = by_day.get(d, 0.0) + rec.cost
        total += rec.cost
        currencies.add(rec.currency)

    groups = [
        {
            "group": k,
            "cost": round(v, 4),
            "pct": round(100.0 * v / total, 2) if total else 0.0,
        }
        for k, v in sorted(by_group.items(), key=lambda kv: kv[1], reverse=True)
    ]
    days = sorted(by_day)
    return {
        "group_by": group_by,
        "total_cost": round(total, 4),
        "currency": currencies.pop() if len(currencies) == 1 else "MIXED",
        "record_count": len(records),
        "date_range": {"start": days[0], "end": days[-1]} if days else None,
        "groups": groups,
        "daily_totals": [{"date": d, "cost": round(by_day[d], 4)} for d in days],
    }


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / n
    return mean, math.sqrt(var)


def detect_anomalies(
    records: Iterable[CostRecord],
    group_by: str = "service",
    z_threshold: float = 2.5,
    min_history: int = 3,
) -> list[Anomaly]:
    """Detect daily spend spikes per group using a z-score over prior history.

    For each group, daily costs are walked chronologically. A day is flagged
    when its cost exceeds the mean of all preceding days by more than
    ``z_threshold`` standard deviations (and history is sufficient).
    """
    if group_by not in _VALID_GROUP_BY:
        raise CloudBillError(
            f"invalid group_by {group_by!r}; "
            f"must be one of {sorted(_VALID_GROUP_BY)}"
        )
    if z_threshold <= 0:
        raise CloudBillError(
            f"z_threshold must be positive, got {z_threshold!r}"
        )
    if min_history < 1:
        raise CloudBillError(
            f"min_history must be at least 1, got {min_history!r}"
        )
    records = list(records)
    # Aggregate cost per (group, date).
    series: dict[str, dict[date, float]] = {}
    for rec in records:
        key = _group_key(rec, group_by)
        series.setdefault(key, {})
        series[key][rec.date] = series[key].get(rec.date, 0.0) + rec.cost

    anomalies: list[Anomaly] = []
    for group, day_costs in series.items():
        ordered_days = sorted(day_costs)
        history: list[float] = []
        for d in ordered_days:
            cost = day_costs[d]
            if len(history) >= min_history:
                mean, std = _mean_std(history)
                baseline = mean
                if std > 0:
                    z = (cost - mean) / std
                else:
                    # No variance in history; flag any increase as a spike.
                    z = math.inf if cost > mean else 0.0
                pct = (100.0 * (cost - baseline) / baseline) if baseline else math.inf
                if z >= z_threshold and cost > baseline:
                    if z >= z_threshold * 2:
                        severity = "critical"
                    elif z >= z_threshold * 1.5:
                        severity = "high"
                    else:
                        severity = "medium"
                    anomalies.append(
                        Anomaly(
                            group=group,
                            date=d.isoformat(),
                            cost=round(cost, 4),
                            baseline=round(baseline, 4),
                            deviation=round(z, 2) if math.isfinite(z) else 999.0,
                            pct_increase=round(pct, 2) if math.isfinite(pct) else 999.0,
                            severity=severity,
                        )
                    )
            history.append(cost)

    anomalies.sort(key=lambda a: a.deviation, reverse=True)
    return anomalies


# FOCUS 1.0 column subset we emit on export.
_FOCUS_COLUMNS = [
    "BillingAccountId",
    "ChargePeriodStart",
    "ProviderName",
    "ServiceName",
    "RegionId",
    "BilledCost",
    "EffectiveCost",
    "BillingCurrency",
    "ChargeCategory",
]


def to_focus(records: Iterable[CostRecord]) -> list[dict[str, Any]]:
    """Export normalized records as FOCUS-conformant rows."""
    out: list[dict[str, Any]] = []
    for rec in records:
        out.append(
            {
                "BillingAccountId": rec.account,
                "ChargePeriodStart": rec.date.isoformat(),
                "ProviderName": rec.provider,
                "ServiceName": rec.service,
                "RegionId": rec.region,
                "BilledCost": round(rec.cost, 4),
                "EffectiveCost": round(rec.cost, 4),
                "BillingCurrency": rec.currency,
                "ChargeCategory": "Usage",
            }
        )
    return out
