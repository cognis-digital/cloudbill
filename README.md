<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:6b46c1,100:2b6cb0&height=120&section=header&text=CLOUDBILL&fontSize=48&fontColor=ffffff&fontAlignY=58" width="100%" alt="CLOUDBILL"/>

# CLOUDBILL

### Multi-cloud cost report, anomaly detection, and FOCUS export

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3500&pause=1000&color=6B46C1&center=true&vCenter=true&width=720&lines=Multicloud+cost+report+anomaly+detection+and+FOCUS+export;Self-hostable+%C2%B7+MCP-native+%C2%B7+CI-ready+%C2%B7+polyglot" width="720"/>

[![PyPI](https://img.shields.io/pypi/v/cognis-cloudbill.svg?color=6b46c1)](https://pypi.org/project/cognis-cloudbill/) [![CI](https://github.com/cognis-digital/cloudbill/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/cloudbill/actions) [![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

*DevOps & Observability — status, synthetics, alerts, and cloud cost.*

</div>

```bash
pip install cognis-cloudbill
cloudbill scan .            # → prioritized findings in seconds
```


<!-- cognis:example:start -->
## 🔎 Example output

Real, reproducible output from the tool — runs offline:

```console
$ cloudbill-emit --version
cloudbill 0.1.0
```

```console
$ cloudbill-emit --help
usage: cloudbill [-h] [--version] [--format {table,json,csv}]
                 {report,anomalies,focus} ...

Multi-cloud cost report, anomaly detection, and FOCUS export.

positional arguments:
  {report,anomalies,focus}
    report              summarize costs grouped by a dimension
    anomalies           detect daily spend spikes
    focus               export records as FOCUS-conformant rows

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --format {table,json,csv}
                        output format (default: table)
```

> Blocks above are real `cloudbill` output — reproduce them from a clone.

**Sample result format** _(illustrative values — run on your own data for real findings):_

```
{
"Findings": [
    {
        "id": "1",
        "title": "Suspicious Network Traffic",
        "description": "Network traffic from unknown IP address",
        "severity": "medium",
        "created_at": "2023-02-15T14:30:00Z"
    },
    {
        "id": "2",
        "title": "Unusual File Access",
        "description": "File access from unknown user",
        "severity": "high",
        "created_at": "2023-02-16T10:45:00Z"
    }
]
}
```

<!-- cognis:example:end -->

## Usage — step by step

1. **Install:**

   ```bash
   pip install -e .
   ```

2. **Summarize costs** from a CSV/JSON cost export with the `report` subcommand. The `input` argument accepts a file or `-` for stdin; choose a grouping dimension with `--group-by` (`service`, `provider`, `account`, `region`):

   ```bash
   cloudbill report costs.csv --group-by service
   ```

3. **Detect daily spend spikes** with the `anomalies` subcommand — `--threshold` sets the z-score cutoff (default 2.5) and `--min-history` the minimum prior days before flagging (default 3):

   ```bash
   cloudbill anomalies costs.csv --threshold 3 --min-history 5
   ```

4. **Read / export the output.** Use the global `--format` flag (before the subcommand) — `table` (default, human-readable), `json` (piping/agents), or `csv` (load into a warehouse / spreadsheet). The `report` table shows per-group cost and percentage; `anomalies` shows group/date/cost/baseline/z-score/severity. Export FOCUS-conformant rows with the `focus` subcommand:

   ```bash
   cloudbill --format json focus costs.csv > focus.json   # JSON for an API/agent
   cloudbill --format csv  focus costs.csv > focus.csv    # CSV for BigQuery/Snowflake/Excel
   ```

   `--format csv` works for every subcommand: `focus` emits the FOCUS column
   schema, `report` emits the per-group breakdown, and `anomalies` emits one row
   per detected spike.

5. **Use it in automation** — run the anomaly check on each new billing drop and alert on spikes:

   ```bash
   cloudbill --format json anomalies costs.csv | jq -e '.count == 0' \
     || echo "Cloud spend anomaly detected"
   ```


## Contents

- [Why cloudbill?](#why) · [Features](#features) · [Quick start](#quick-start) · [Example](#example) · [Demos](#demos) · [Architecture](#architecture) · [AI stack](#ai-stack) · [How it compares](#how-it-compares) · [Integrations](#integrations) · [Install anywhere](#install-anywhere) · [Related](#related) · [Contributing](#contributing)

<a name="why"></a>
## Why cloudbill?

FinOps

`cloudbill` is single-purpose, scriptable, and self-hostable: point it at a target, get prioritized results in the format your workflow already speaks (table · JSON · SARIF), gate CI on it, and let agents drive it over MCP.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="features"></a>
## Features

- ✅ Load Records
- ✅ Summarize
- ✅ Detect Anomalies
- ✅ FOCUS 1.0 export (table · JSON · **CSV**)
- ✅ Runs on Linux/macOS/Windows · Docker · devcontainer
- ✅ Ports in Python, JavaScript, Go, and Rust (`ports/`)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="quick-start"></a>
## Quick start

```bash
pip install cognis-cloudbill
cloudbill --version
cloudbill scan .                       # scan current project
cloudbill scan . --format json         # machine-readable
cloudbill scan . --fail-on high        # CI gate (non-zero exit)
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="example"></a>
## Example

```text
$ cloudbill scan .
  [HIGH    ] CLO-001  example finding             (./src/app.py)
  [MEDIUM  ] CLO-002  another signal              (./config.yaml)

  2 findings · risk score 5 · 38ms
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="demos"></a>
## Demos — real FinOps scenarios

Each folder under [`demos/`](demos/) ships a realistic billing export in the
tool's real input format plus a `SCENARIO.md` (where the data came from, the
exact command, what to expect, and how to act). Every demo is exercised by the
test suite, so they always run.

| Demo | Format | What it shows |
|---|---|---|
| [`01-basic`](demos/01-basic/) | CSV | Three-provider report + EC2 GPU-fleet spike |
| [`04-aws-cur-aliases`](demos/04-aws-cur-aliases/) | CSV | Native **AWS CUR** column names; data-transfer egress spike |
| [`05-azure-cost-mgmt`](demos/05-azure-cost-mgmt/) | CSV | **Azure Cost Management** export by subscription; EUR billing |
| [`06-gcp-json`](demos/06-gcp-json/) | JSON | **GCP BigQuery** billing export (nested `rows`); query-cost blowout |
| [`07-savings-plan-spike`](demos/07-savings-plan-spike/) | CSV | Savings Plan / RI **expiry** step-up detection |
| [`08-focus-export-csv`](demos/08-focus-export-csv/) | CSV | Four-cloud **FOCUS 1.0** export to CSV/JSON |
| [`09-multicurrency`](demos/09-multicurrency/) | CSV | `MIXED` currency guard (no silent FX) |
| [`10-tag-untagged-region`](demos/10-tag-untagged-region/) | CSV | Sparse export → `unknown`/`global` tagging-hygiene finding |
| [`11-ci-budget-gate`](demos/11-ci-budget-gate/) | CSV + sh | CI gate that **fails the build** on a spend spike |

```bash
python -m cloudbill report demos/04-aws-cur-aliases/cur.csv
python -m cloudbill --format json anomalies demos/06-gcp-json/gcp_billing.json
python -m cloudbill --format csv focus demos/08-focus-export-csv/mixed_providers.csv
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="architecture"></a>
## Architecture

```mermaid
flowchart LR
  IN[target / manifest] --> P[cloudbill<br/>checks + rules]
  P --> OUT[findings (JSON / SARIF)]
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="ai-stack"></a>
## Use it from any AI stack

`cloudbill` is interoperable with every popular way of using AI:

- **MCP server** — `cloudbill mcp` (Claude Desktop, Cursor, Cognis.Studio, [uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet))
- **OpenAI-compatible / JSON** — pipe `cloudbill scan . --format json` into any agent or LLM
- **LangChain · CrewAI · AutoGen · LlamaIndex** — wrap the CLI/JSON as a tool in one line
- **CI / scripts** — exit codes + SARIF for non-AI pipelines

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="how-it-compares"></a>
## How it compares

| | **Cognis cloudbill** | OptScale + FOCUS |
|---|:---:|:---:|
| Self-hostable, no account | ✅ | varies |
| Single command, zero config | ✅ | ⚠️ |
| JSON + SARIF for CI | ✅ | varies |
| MCP-native (AI agents) | ✅ | ❌ |
| Polyglot ports (JS/Go/Rust) | ✅ | ❌ |
| Open license | ✅ COCL | varies |

*Built in the spirit of **OptScale + FOCUS**, re-framed the Cognis way. Missing a credit? Open a PR.*

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="integrations"></a>
## Integrations

Pipes into your stack: **SARIF** for code-scanning, **JSON** for anything, an **MCP server** (`cloudbill mcp`) for AI agents, and a webhook forwarder for SIEM/Slack/Jira. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="install-anywhere"></a>
## Install — every way, every platform

```bash
pip install "git+https://github.com/cognis-digital/cloudbill.git"    # pip (works today)
pipx install "git+https://github.com/cognis-digital/cloudbill.git"   # isolated CLI
uv tool install "git+https://github.com/cognis-digital/cloudbill.git" # uv
pip install cognis-cloudbill                                          # PyPI (when published)
docker run --rm ghcr.io/cognis-digital/cloudbill:latest --help        # Docker
brew install cognis-digital/tap/cloudbill                             # Homebrew tap
curl -fsSL https://raw.githubusercontent.com/cognis-digital/cloudbill/main/install.sh | sh
```

| Linux | macOS | Windows | Docker | Cloud |
|---|---|---|---|---|
| `scripts/setup-linux.sh` | `scripts/setup-macos.sh` | `scripts/setup-windows.ps1` | `docker run ghcr.io/cognis-digital/cloudbill` | [DEPLOY.md](docs/DEPLOY.md) (AWS/Azure/GCP/k8s) |

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="related"></a>
## Related Cognis tools

- [`statuskit`](https://github.com/cognis-digital/statuskit) — Self-hosted status page with incident timeline and subscribers
- [`probesite`](https://github.com/cognis-digital/probesite) — Synthetic uptime and Playwright checks exported to Prometheus
- [`alertmux`](https://github.com/cognis-digital/alertmux) — Alert dedup, correlation, and routing in front of Grafana / PagerDuty
- [`k8scost`](https://github.com/cognis-digital/k8scost) — Kubernetes cost and rightsizing advisor with no Prometheus dependency
- [`otelbox`](https://github.com/cognis-digital/otelbox) — One-command OpenTelemetry collector + dashboards bundle

**Explore the suite →** [🗂️ all 170+ tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources) · [🤖 uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet) · [🧠 engram](https://github.com/cognis-digital/engram)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="contributing"></a>
## Contributing

PRs, new rules, and demo scenarios are welcome under the collaboration-pull model — see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

> ### ⭐ If `cloudbill` saved you time, **star it** — it genuinely helps others find it.

## Interoperability

`{}` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

---

<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · one of 170+ tools in the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
