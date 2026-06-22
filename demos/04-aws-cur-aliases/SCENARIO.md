# Demo 04 — AWS Cost & Usage Report (CUR) native column names

## Where the data came from

`cur.csv` is shaped like a trimmed **AWS Cost and Usage Report (CUR)** export
pulled from an S3 billing bucket. Instead of cloudbill's own tidy column names,
it uses the *real* CUR/legacy header names that analysts actually see:
`lineItem/ProductCode`, `linked_account_id`, `lineItem/UsageStartDate`,
`lineItem/UnblendedCost`, `CurrencyCode`. The point of this demo is to prove the
loader's **alias mapping** normalises those without any pre-processing.

The data is a five-day slice for one linked account (`1122-3344-5566`) running
EC2, RDS, and DataTransfer. On `2026-04-05` egress (`AWSDataTransfer`) jumps from
a steady ~$9/day to **$118.60** — the classic "a misconfigured job started
shipping data cross-region / out to the internet" bill shock.

## Run it

```bash
# Cost report grouped by service — proves CUR aliases are understood
python -m cloudbill report demos/04-aws-cur-aliases/cur.csv

# Find the data-transfer egress spike
python -m cloudbill --format json anomalies demos/04-aws-cur-aliases/cur.csv --min-history 3
```

## What to expect

- `report` resolves the CUR headers and shows `AmazonEC2` as the largest line,
  with `AWSDataTransfer` inflated by the spike day.
- `anomalies` flags `AWSDataTransfer` on `2026-04-05` at high/critical severity.

## How to act

Egress spikes are almost always a regression, not real demand. Check for a new
cross-AZ/cross-region data path, a public S3 download, or a chatty replication
job that shipped overnight, and confirm the baseline returns the next day.
