# Demo 10 — Sparse export: missing account, region, and provider columns

## Where the data came from

`sparse.csv` is the bare-minimum export you get from a quick ad-hoc query or a
poorly-tagged account: only `service`, `date`, and `cost` are present. There is
no `provider`, no `account`, no `region`, and no `currency` column at all.

cloudbill treats `date` and `cost` as the only **required** fields and fills the
rest with safe defaults: missing provider/account/service become `unknown`,
missing region becomes `global`, and missing currency becomes `USD`. The tool
keeps working instead of erroring out on incomplete data.

## Run it

```bash
# Default service grouping still works
python -m cloudbill report demos/10-tag-untagged-region/sparse.csv

# Grouping by a column that doesn't exist collapses to the default placeholder
python -m cloudbill --format json report demos/10-tag-untagged-region/sparse.csv --group-by account

python -m cloudbill --format json report demos/10-tag-untagged-region/sparse.csv --group-by region
```

## What to expect

- `--group-by service` shows real per-service costs (EC2 lines aggregate).
- `--group-by account` yields a single `unknown` group — a clear signal that
  the export carries no account attribution.
- `--group-by region` yields a single `global` group.

## How to act

A report that collapses to `unknown`/`global` is a **tagging-hygiene finding**.
Go back to the billing export and add the account/region/provider columns (or a
cost-allocation tag) so future reports can attribute spend to a real owner.
