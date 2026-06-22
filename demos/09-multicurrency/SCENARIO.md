# Demo 09 — Multi-currency billing and the MIXED guard

## Where the data came from

`global_costs.csv` is a spend extract from a company with regional billing
accounts that each settle in their **local currency**: a US team in USD, an EU
team in EUR, a UK team in GBP, and an APAC team in JPY. This is deliberately a
trap: naively summing the `cost` column across currencies produces a meaningless
number.

cloudbill does **not** silently fake an FX conversion. When records span more
than one currency, the report's `currency` field is set to `MIXED` so the
ambiguity is visible rather than hidden.

## Run it

```bash
# Group by account — note the MIXED currency flag in the output
python -m cloudbill --format json report demos/09-multicurrency/global_costs.csv --group-by account

# Per-account totals as a table
python -m cloudbill report demos/09-multicurrency/global_costs.csv --group-by account
```

## What to expect

- The report's top-level `currency` field is `MIXED` (not USD/EUR/etc.).
- Each account's raw-number total is correct *within its own currency*; the JPY
  account looks huge purely because of unit scale.

## How to act

`MIXED` is your cue to normalize to a single reporting currency **before**
comparing accounts. Convert each account at your finance team's agreed rate (or
filter to one currency at a time) — don't trust a cross-currency grand total.
