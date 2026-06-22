# Demo 07 — Savings Plan / Reserved Instance expiry detection

## Where the data came from

`usage.csv` is a two-week single-account (`9988-7766-5544`) AWS extract for one
production EC2 fleet in `us-west-2`, plus a steady NAT-gateway (`AmazonVPC`)
line. For the first **12 days** EC2 sits around **$200/day** because the compute
is covered by a 1-year Compute Savings Plan. On day 13 (`2026-01-14`) the plan
**expires** and the same usage reverts to on-demand pricing — EC2 jumps to
**$332/day** with no change in workload.

This is the spike you most want to catch automatically, because nothing
"broke": the resources are healthy, the rate just got worse, and it will recur
every single day until someone re-commits.

## Run it

```bash
# 12 prior days easily clears the default min-history of 3
python -m cloudbill --format json anomalies demos/07-savings-plan-spike/usage.csv

# See the per-day EC2 series in the report's daily_totals
python -m cloudbill --format json report demos/07-savings-plan-spike/usage.csv
```

## What to expect

- `anomalies` flags `AmazonEC2` on `2026-01-14` against a tight ~$200 baseline;
  the low variance of the prior days makes the z-score large.
- `AmazonVPC` stays quiet — no false positive on the steady line.

## How to act

A persistent step-up (not a one-day blip) on compute almost always means a
Savings Plan or RI lapsed. Pull the Savings Plans coverage report, re-purchase
to your committed-use target, and set a calendar reminder ~30 days before the
next expiry.
