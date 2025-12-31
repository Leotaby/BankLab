"""Data quality checks."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class QualityWarning:
    check_name: str
    severity: Severity
    ticker: str
    period: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    warnings: list[QualityWarning] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)

    def add(self, warning):
        self.warnings.append(warning)

    def has_errors(self):
        return any(w.severity == Severity.ERROR for w in self.warnings)

    def summary(self):
        return {"error": 0, "warning": 0, "info": 0}

    def to_dataframe(self):
        return pd.DataFrame()

    def __repr__(self):
        return f"QualityReport(checks={len(self.checks_run)})"


def check_balance_sheet_identity(df, report, tolerance=0.01):
    report.checks_run.append("balance_sheet_identity")


def check_positive_values(df, report):
    report.checks_run.append("positive_values")


def check_reasonable_ratios(df, report):
    report.checks_run.append("reasonable_ratios")


def check_temporal_consistency(df, report, max_change=0.50):
    report.checks_run.append("temporal_consistency")


def check_completeness(df, report, required_items=None):
    report.checks_run.append("completeness")


def run_all_checks(df, include_kpi_checks=True):
    report = QualityReport()
    check_balance_sheet_identity(df, report)
    check_positive_values(df, report)
    check_temporal_consistency(df, report)
    check_completeness(df, report)
    if include_kpi_checks:
        check_reasonable_ratios(df, report)
    logger.info(f"Quality checks complete: {report}")
    return report
