# Demo 01 - Basic multi-cloud cost report and anomaly hunt

This scenario uses a small two-week, three-provider billing extract
(`usage.csv`) with AWS, Azure, and GCP line items. It demonstrates the three
core CLOUDBILL workflows: cost reporting, anomaly detection, and FOCUS export.

The data deliberately contains a **spend spike**: on `2026-05-14` the AWS
`AmazonEC2` daily cost jumps from a steady ~$40/day baseline to **$310** (a
classic "someone left a GPU fleet running" anomaly).

## Run it

```bash
# 1. Cost report grouped by service (default)
python -m cloudbill report demos/01-basic/usage.csv

# 2. Same report grouped by provider, as JSON
python -m cloudbill --format json report demos/01-basic/usage.csv --group-by provider

# 3. Detect the EC2 spend spike
python -m cloudbill anomalies demos/01-basic/usage.csv

# 4. Export to a FOCUS-conformant dataset
python -m cloudbill --format json focus demos/01-basic/usage.csv
```

## What to expect

- `report` shows AmazonEC2 as the largest line item by cost.
- `anomalies` flags `AmazonEC2` on `2026-05-14` as a **critical/high** spike
  with a high z-score versus its prior-day baseline.
- `focus` emits rows with FOCUS 1.0 columns (`BilledCost`, `ServiceName`,
  `ChargePeriodStart`, `BillingCurrency`, ...).

The loader auto-detects CSV vs JSON and tolerates common AWS CUR / Azure Cost
Management / GCP billing column names via alias mapping.
