# Demo 05 — Azure Cost Management export, grouped by subscription

## Where the data came from

`azure_costs.csv` mimics an **Azure Cost Management** "Cost analysis" CSV export
(EUR-billed tenant). It uses Azure's native column names — `SubscriptionId`,
`MeterCategory`, `ResourceLocation`, `UsageDate`, `PretaxCost`,
`BillingCurrency` — which cloudbill maps onto its normalized fields via aliases.

There are **two subscriptions**: a production one
(`...111111111111`) carrying VMs, Storage, and Azure SQL, and a smaller one
(`...222222222222`). Everything is in **EUR**, so this also exercises non-USD
currency handling.

## Run it

```bash
# Spend per subscription (account dimension)
python -m cloudbill report demos/05-azure-cost-mgmt/azure_costs.csv --group-by account

# Spend per region
python -m cloudbill report demos/05-azure-cost-mgmt/azure_costs.csv --group-by region

# Spend per Azure meter category (service dimension), as JSON
python -m cloudbill --format json report demos/05-azure-cost-mgmt/azure_costs.csv --group-by service
```

## What to expect

- `--group-by account` splits the two subscription GUIDs and shows the prod
  subscription dominating.
- The report `currency` field reads `EUR` (single-currency input).
- `Virtual Machines` is the top meter category overall.

## How to act

Subscription-level grouping is the first FinOps cut for showback/chargeback:
attribute the prod subscription's VM spend to its owning team, then drill into
region to spot anything running outside your approved `westeurope` footprint.
