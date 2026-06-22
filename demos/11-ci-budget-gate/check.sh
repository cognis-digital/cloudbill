#!/usr/bin/env sh
# CI budget gate: fail the pipeline if today's billing drop contains a spend
# anomaly. Wire this into a nightly job that runs after each billing export.
#
# Usage: sh demos/11-ci-budget-gate/check.sh demos/11-ci-budget-gate/daily_drop.csv
set -eu

INPUT="${1:-demos/11-ci-budget-gate/daily_drop.csv}"

# Count anomalies via the JSON output. jq -e sets a non-zero exit when the
# expression is false, which we translate into a clear pass/fail message.
if python -m cloudbill --format json anomalies "$INPUT" | jq -e '.count == 0' >/dev/null; then
  echo "OK: no cloud spend anomalies in $INPUT"
  exit 0
else
  echo "FAIL: cloud spend anomaly detected in $INPUT" >&2
  python -m cloudbill anomalies "$INPUT" >&2
  exit 1
fi
