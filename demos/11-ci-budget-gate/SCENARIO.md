# Demo 11 — CI budget gate (fail the build on a spend spike)

## Where the data came from

`daily_drop.csv` represents the latest **nightly billing export** dropped into
CI. EC2 has run at a steady ~$300/day for five days, then on `2026-06-15` it
nearly **quadruples to $1,180** — exactly the kind of overnight surprise you
want a pipeline to catch before a human notices the invoice. `AmazonS3` stays
flat so you can confirm there are no false alarms.

`check.sh` is a portable POSIX gate: it runs `anomalies --format json`, uses
`jq -e '.count == 0'` to decide pass/fail, and exits non-zero (failing the
build) when anything is flagged.

## Run it

```bash
# Run the gate on the spike file — expect a non-zero exit (FAIL)
sh demos/11-ci-budget-gate/check.sh demos/11-ci-budget-gate/daily_drop.csv

# Point it at a clean export to see the passing path (exit 0)
sh demos/11-ci-budget-gate/check.sh demos/01-basic/usage.csv  # also fails (has a spike)
```

Inline one-liner (no script):

```bash
python -m cloudbill --format json anomalies demos/11-ci-budget-gate/daily_drop.csv \
  | jq -e '.count == 0' || echo "Cloud spend anomaly detected"
```

## What to expect

- On `daily_drop.csv` the gate prints `FAIL`, dumps the offending anomaly table
  to stderr, and exits `1`.
- Substitute a flat export with no spike and the gate prints `OK` and exits `0`.

## How to act

Drop `check.sh` into a nightly GitHub Actions / GitLab CI job triggered after
your billing export lands. A red build is your earliest signal — open the
flagged service, confirm whether it's real demand or a regression, and either
right-size or roll back before the spend compounds across the month.
