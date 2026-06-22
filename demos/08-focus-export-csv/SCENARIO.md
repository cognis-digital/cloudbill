# Demo 08 — FOCUS export to CSV for a downstream data warehouse

## Where the data came from

`mixed_providers.csv` is a single day of normalized spend across **four**
providers — AWS, Azure, GCP, and OCI — the kind of unified extract a central
FinOps team assembles before loading it into a warehouse or BI tool. The goal
here is the **export**, not anomaly hunting: convert these heterogeneous rows
into a single **FOCUS 1.0**-conformant dataset that every provider can share.

This demo exercises cloudbill's `--format csv` output (see the FOCUS columns:
`BillingAccountId`, `ChargePeriodStart`, `ProviderName`, `ServiceName`,
`RegionId`, `BilledCost`, `EffectiveCost`, `BillingCurrency`, `ChargeCategory`).

## Run it

```bash
# FOCUS export as JSON (for an API / agent)
python -m cloudbill --format json focus demos/08-focus-export-csv/mixed_providers.csv

# FOCUS export as CSV — load straight into BigQuery / Snowflake / a spreadsheet
python -m cloudbill --format csv focus demos/08-focus-export-csv/mixed_providers.csv \
  > focus_2026-05-01.csv

# CSV also works for report and anomalies output:
python -m cloudbill --format csv report demos/08-focus-export-csv/mixed_providers.csv --group-by provider
```

## What to expect

- The `focus` CSV has a FOCUS column header row followed by one row per input
  line — six data rows, all providers folded into one schema.
- `--format csv report` emits a `group,cost,pct` breakdown ready for a chart.

## How to act

FOCUS is the FinOps Foundation's open billing schema. Emitting it as CSV gives
you a provider-neutral table you can `COPY`/`LOAD DATA` into any warehouse and
join across clouds without per-vendor column gymnastics.
