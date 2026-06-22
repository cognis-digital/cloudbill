"""Smoke tests for CLOUDBILL. Standard library only, no network."""
import csv
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cloudbill import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    load_records,
    summarize,
    detect_anomalies,
    to_focus,
)
from cloudbill.cli import main  # noqa: E402
from cloudbill.core import CloudBillError  # noqa: E402

CSV = (
    "provider,account,service,region,date,cost,currency\n"
    "aws,a1,EC2,us-east-1,2026-05-10,40,USD\n"
    "aws,a1,EC2,us-east-1,2026-05-11,41,USD\n"
    "aws,a1,EC2,us-east-1,2026-05-12,39,USD\n"
    "aws,a1,EC2,us-east-1,2026-05-13,42,USD\n"
    "aws,a1,EC2,us-east-1,2026-05-14,500,USD\n"
    "azure,a2,VM,eastus,2026-05-10,20,USD\n"
)

DEMO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "demos", "01-basic", "usage.csv")


class TestCore(unittest.TestCase):
    def test_version_constants(self):
        self.assertEqual(TOOL_NAME, "cloudbill")
        self.assertTrue(TOOL_VERSION)

    def test_load_csv(self):
        recs = load_records(CSV)
        self.assertEqual(len(recs), 6)
        self.assertEqual(recs[0].provider, "aws")
        self.assertAlmostEqual(recs[4].cost, 500.0)

    def test_load_json_and_alias(self):
        data = json.dumps([
            {"cloud": "aws", "BillingAccountId": "x", "ServiceName": "S3",
             "Region": "us-east-1", "ChargePeriodStart": "2026-05-10T00:00:00",
             "BilledCost": "12.50"}
        ])
        recs = load_records(data)
        self.assertEqual(recs[0].service, "S3")
        self.assertEqual(recs[0].date.isoformat(), "2026-05-10")
        self.assertAlmostEqual(recs[0].cost, 12.5)

    def test_summarize(self):
        rep = summarize(load_records(CSV), group_by="service")
        self.assertEqual(rep["record_count"], 6)
        self.assertEqual(rep["groups"][0]["group"], "EC2")
        self.assertAlmostEqual(rep["total_cost"], 682.0)

    def test_detect_anomaly(self):
        anomalies = detect_anomalies(load_records(CSV), z_threshold=2.0)
        self.assertTrue(any(a.group == "EC2" and a.date == "2026-05-14"
                            for a in anomalies))

    def test_to_focus(self):
        rows = to_focus(load_records(CSV))
        self.assertIn("BilledCost", rows[0])
        self.assertIn("ChargePeriodStart", rows[0])

    def test_bad_input(self):
        with self.assertRaises(CloudBillError):
            load_records("")
        with self.assertRaises(CloudBillError):
            load_records("not json or csv with no comma", fmt="json")


class TestCLI(unittest.TestCase):
    def _capture(self, argv):
        out = io.StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            code = main(argv)
        finally:
            sys.stdout = old
        return code, out.getvalue()

    def test_report_json(self):
        code, output = self._capture(["--format", "json", "report", DEMO])
        self.assertEqual(code, 0)
        parsed = json.loads(output)
        self.assertEqual(parsed["group_by"], "service")
        self.assertGreater(parsed["total_cost"], 0)

    def test_anomalies_finds_ec2_spike(self):
        code, output = self._capture(["--format", "json", "anomalies", DEMO])
        self.assertEqual(code, 0)
        parsed = json.loads(output)
        self.assertGreaterEqual(parsed["count"], 1)
        self.assertTrue(any(a["group"] == "AmazonEC2"
                            for a in parsed["anomalies"]))

    def test_focus_table(self):
        code, output = self._capture(["--format", "table", "focus", DEMO])
        self.assertEqual(code, 0)
        self.assertIn("BilledCost", output)

    def test_missing_file_returns_nonzero(self):
        code, _ = self._capture(["report", "does-not-exist.csv"])
        self.assertEqual(code, 1)

    def test_focus_csv_export(self):
        code, output = self._capture(["--format", "csv", "focus", DEMO])
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(output)))
        self.assertEqual(len(rows), 36)  # one row per input line
        self.assertIn("BilledCost", rows[0])
        self.assertIn("ChargePeriodStart", rows[0])

    def test_report_csv_export(self):
        code, output = self._capture(
            ["--format", "csv", "report", DEMO, "--group-by", "provider"])
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(output)))
        self.assertEqual({r["group"] for r in rows}, {"aws", "azure", "gcp"})
        self.assertEqual(set(rows[0].keys()), {"group", "cost", "pct"})

    def test_anomalies_csv_export(self):
        code, output = self._capture(["--format", "csv", "anomalies", DEMO])
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(output)))
        self.assertTrue(any(r["group"] == "AmazonEC2" for r in rows))
        self.assertIn("severity", rows[0])


class TestDemos(unittest.TestCase):
    """Every shipped demo must actually load and produce the documented output."""

    DEMOS_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demos")

    def _load(self, *parts):
        path = os.path.join(self.DEMOS_DIR, *parts)
        with open(path, "r", encoding="utf-8") as fh:
            return load_records(fh.read())

    def test_aws_cur_aliases_resolve(self):
        recs = self._load("04-aws-cur-aliases", "cur.csv")
        # CUR-native headers must normalize without preprocessing.
        self.assertTrue(any(r.service == "AmazonEC2" for r in recs))
        anomalies = detect_anomalies(recs, min_history=3)
        self.assertTrue(any(a.group == "AWSDataTransfer" for a in anomalies))

    def test_azure_aliases_and_eur(self):
        recs = self._load("05-azure-cost-mgmt", "azure_costs.csv")
        rep = summarize(recs, group_by="account")
        self.assertEqual(rep["currency"], "EUR")
        self.assertEqual(len(rep["groups"]), 2)

    def test_gcp_json_nested_rows(self):
        recs = self._load("06-gcp-json", "gcp_billing.json")
        anomalies = detect_anomalies(recs)
        self.assertTrue(any(a.group == "BigQuery" and a.severity == "critical"
                            for a in anomalies))

    def test_savings_plan_expiry_spike(self):
        recs = self._load("07-savings-plan-spike", "usage.csv")
        anomalies = detect_anomalies(recs)
        self.assertTrue(any(a.group == "AmazonEC2" and a.date == "2026-01-14"
                            for a in anomalies))

    def test_focus_export_csv_demo(self):
        recs = self._load("08-focus-export-csv", "mixed_providers.csv")
        self.assertEqual(len(to_focus(recs)), 6)

    def test_multicurrency_is_mixed(self):
        recs = self._load("09-multicurrency", "global_costs.csv")
        self.assertEqual(summarize(recs)["currency"], "MIXED")

    def test_sparse_defaults(self):
        recs = self._load("10-tag-untagged-region", "sparse.csv")
        self.assertTrue(all(r.account == "unknown" for r in recs))
        self.assertTrue(all(r.region == "global" for r in recs))

    def test_ci_budget_gate_data_has_spike(self):
        recs = self._load("11-ci-budget-gate", "daily_drop.csv")
        anomalies = detect_anomalies(recs)
        self.assertTrue(any(a.group == "AmazonEC2" and a.severity == "critical"
                            for a in anomalies))


if __name__ == "__main__":
    unittest.main()
