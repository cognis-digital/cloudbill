# Demo 06 — GCP BigQuery billing export (JSON, nested rows)

## Where the data came from

`gcp_billing.json` is shaped like the JSON you get when you query a **GCP
detailed billing export** out of BigQuery and dump the result. The cost rows are
nested under a top-level `"rows"` key (cloudbill unwraps `rows`/`data`/
`records`/`lineItems` automatically), and individual fields use a mix of GCP-ish
names: `project_id`, `ServiceName`, `location`, `usage_date`, plus numeric costs
stored **as strings** (a very common export quirk).

The project `analytics-prod-7781` runs Compute Engine, BigQuery, and Cloud
Storage. On `2026-02-13` **BigQuery** explodes from ~$31/day to **$412.75** — the
textbook "someone ran a full-table scan / a `SELECT *` against a huge dataset"
on-demand query blowout.

## Run it

```bash
# Auto-detects JSON, unwraps "rows", parses string costs
python -m cloudbill report demos/06-gcp-json/gcp_billing.json

# Catch the BigQuery query-cost spike
python -m cloudbill --format json anomalies demos/06-gcp-json/gcp_billing.json
```

## What to expect

- `report` totals all three services and shows Compute Engine + the BigQuery
  spike day at the top.
- `anomalies` flags `BigQuery` on `2026-02-13` as a critical spike.

## How to act

BigQuery on-demand spikes are usually one bad query or a runaway scheduled
query. Find it in the BigQuery jobs view by `total_bytes_billed`, then either add
a `maximum_bytes_billed` guardrail or move that workload to flat-rate slots.
