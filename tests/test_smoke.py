"""Smoke tests for CLOUDBILL. Standard library only, no network."""
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


class TestHardening(unittest.TestCase):
    """Tests covering the new input-validation and error-handling paths."""

    # --- core.py ---

    def test_tool_name_version_in_core(self):
        """TOOL_NAME / TOOL_VERSION must be defined directly in core."""
        from cloudbill.core import TOOL_NAME as TN, TOOL_VERSION as TV
        self.assertEqual(TN, "cloudbill")
        self.assertTrue(TV)

    def test_load_records_non_string_raises(self):
        with self.assertRaises(CloudBillError):
            load_records(None)  # type: ignore[arg-type]

    def test_load_records_unknown_format_raises(self):
        csv_text = "date,cost\n2026-01-01,5.0\n"
        with self.assertRaises(CloudBillError) as ctx:
            load_records(csv_text, fmt="parquet")
        self.assertIn("unknown format", str(ctx.exception))

    def test_summarize_invalid_group_by_raises(self):
        recs = load_records(CSV)
        with self.assertRaises(CloudBillError) as ctx:
            summarize(recs, group_by="nonsense")
        self.assertIn("invalid group_by", str(ctx.exception))

    def test_detect_anomalies_invalid_group_by_raises(self):
        recs = load_records(CSV)
        with self.assertRaises(CloudBillError) as ctx:
            detect_anomalies(recs, group_by="nonsense")
        self.assertIn("invalid group_by", str(ctx.exception))

    def test_detect_anomalies_bad_threshold_raises(self):
        recs = load_records(CSV)
        with self.assertRaises(CloudBillError) as ctx:
            detect_anomalies(recs, z_threshold=0.0)
        self.assertIn("z_threshold", str(ctx.exception))

    def test_detect_anomalies_bad_min_history_raises(self):
        recs = load_records(CSV)
        with self.assertRaises(CloudBillError) as ctx:
            detect_anomalies(recs, min_history=0)
        self.assertIn("min_history", str(ctx.exception))

    def test_to_focus_empty_list_returns_empty(self):
        self.assertEqual(to_focus([]), [])

    # --- cli.py ---

    def _capture(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            code = main(argv)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
        return code, out.getvalue(), err.getvalue()

    def test_cli_negative_threshold_returns_2(self):
        code, _, err = self._capture(
            ["--format", "json", "anomalies", DEMO, "--threshold", "-1"]
        )
        self.assertEqual(code, 2)
        self.assertIn("threshold", err.lower())

    def test_cli_zero_min_history_returns_2(self):
        code, _, err = self._capture(
            ["--format", "json", "anomalies", DEMO, "--min-history", "0"]
        )
        self.assertEqual(code, 2)
        self.assertIn("min-history", err.lower())

    def test_cli_missing_file_has_informative_message(self):
        code, _, err = self._capture(["report", "no-such-file.csv"])
        self.assertEqual(code, 1)
        self.assertIn("no-such-file.csv", err)

    def test_cli_malformed_json_returns_1(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            tf.write("{bad json}")
            tf_path = tf.name
        try:
            code, _, err = self._capture(
                ["--format", "json", "report", "--input-format", "json", tf_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("error", err.lower())
        finally:
            os.unlink(tf_path)


if __name__ == "__main__":
    unittest.main()
