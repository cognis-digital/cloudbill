"""CLOUDBILL - Multi-cloud cost report, anomaly detection, and FOCUS export.

A zero-install, standard-library-only FinOps CLI in the spirit of OptScale and
the FOCUS (FinOps Open Cost & Usage Specification) standard.

Ingests cost/usage rows from multiple cloud providers (AWS/Azure/GCP-shaped CSV
or JSON), normalizes them, builds cost reports, detects spend anomalies, and
exports a FOCUS-conformant dataset.
"""
from .core import (
    CostRecord,
    load_records,
    summarize,
    detect_anomalies,
    to_focus,
    Anomaly,
)

TOOL_NAME = "cloudbill"
TOOL_VERSION = "1.0.0"

__all__ = [
    "CostRecord",
    "load_records",
    "summarize",
    "detect_anomalies",
    "to_focus",
    "Anomaly",
    "TOOL_NAME",
    "TOOL_VERSION",
]
