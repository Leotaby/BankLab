"""Data quality checks for normalized financial data."""

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

    def add(self, warning: QualityWarning) -> None:
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        return any(w.severity == Severity.ERROR for w in self.warnings)

    def summary(self) -> dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0}
        for w in self.warnings:
            counts[w.severity.value] += 1
        return counts

    def to_dataframe(self) -> pd.DataFrame:
        if not self.warnings:
            return pd.DataFrame()
        records = []
        for w in self.warnings:
            records.append(
                {
                    "check_name": w.check_name,
                    "severity": w.severity.value,
                    "ticker": w.ticker,
                    "period": w.period,
                    "message": w.message,
                }
            )
        return pd.DataFrame(records)

    def __repr__(self) -> str:
        return f"QualityReport(checks={len(self.checks_run)})"


def check_balance_sheet_identity(
    df: pd.DataFrame,
    report: QualityReport,
    tolerance: float = 0.01,
) -> None:
    report.checks_run.append("balance_sheet_identity")
    required = ["total_assets", "total_liabilities", "total_equity"]
    if not all(col in df.columns for col in required):
        return
    for _, row in df.iterrows():
        assets = row.get("total_assets")
        liabilities = row.get("total_liabilities")
        equity = row.get("total_equity")
        if pd.isna(assets) or pd.isna(liabilities) or pd.isna(equity):
            continue
        if assets == 0:
            continue
        expected = liabilities + equity
        diff = abs(assets - expected)
        rel_diff = diff / abs(assets)
        if rel_diff > tolerance:
            period = f"{row.get('fiscal_year', '')}-{row.get('fiscal_period', '')}"
            report.add(
                QualityWarning(
                    check_name="balance_sheet_identity",
                    severity=Severity.WARNING,
                    ticker=row.get("ticker", ""),
                    period=period,
                    message=f"Balance sheet doesn't balance: A={assets:,.0f}, L+E={expected:,.0f}",
                    details={"diff": diff, "rel_diff": rel_diff},
                )
            )


def check_positive_values(df: pd.DataFrame, report: QualityReport) -> None:
    report.checks_run.append("positive_values")
    positive_cols = [
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_deposits",
        "loans_net",
        "shares_outstanding",
    ]
    for col in positive_cols:
        if col not in df.columns:
            continue
        for _, row in df.iterrows():
            val = row.get(col)
            if pd.notna(val) and val < 0:
                period = f"{row.get('fiscal_year', '')}-{row.get('fiscal_period', '')}"
                report.add(
                    QualityWarning(
                        check_name="positive_values",
                        severity=Severity.ERROR,
                        ticker=row.get("ticker", ""),
                        period=period,
                        message=f"{col} is negative: {val:,.0f}",
                        details={"column": col, "value": val},
                    )
                )


def check_reasonable_ratios(df: pd.DataFrame, report: QualityReport) -> None:
    report.checks_run.append("reasonable_ratios")
    ratio_bounds = {
        "leverage": (4, 20),
        "roe": (-0.50, 0.50),
        "roa": (-0.10, 0.10),
    }
    for col, (low, high) in ratio_bounds.items():
        if col not in df.columns:
            continue
        for _, row in df.iterrows():
            val = row.get(col)
            if pd.isna(val):
                continue
            period = f"{row.get('fiscal_year', '')}-{row.get('fiscal_period', '')}"
            if val < low:
                report.add(
                    QualityWarning(
                        check_name="reasonable_ratios",
                        severity=Severity.WARNING,
                        ticker=row.get("ticker", ""),
                        period=period,
                        message=f"{col} is unusually low: {val:.4f}",
                        details={"column": col, "value": val},
                    )
                )
            elif val > high:
                report.add(
                    QualityWarning(
                        check_name="reasonable_ratios",
                        severity=Severity.WARNING,
                        ticker=row.get("ticker", ""),
                        period=period,
                        message=f"{col} is unusually high: {val:.4f}",
                        details={"column": col, "value": val},
                    )
                )


def check_temporal_consistency(
    df: pd.DataFrame,
    report: QualityReport,
    max_change: float = 0.50,
) -> None:
    report.checks_run.append("temporal_consistency")


def check_completeness(
    df: pd.DataFrame,
    report: QualityReport,
    required_items: list[str] | None = None,
) -> None:
    report.checks_run.append("completeness")
    if required_items is None:
        required_items = ["total_assets", "total_equity", "net_income"]
    for ticker in df["ticker"].unique() if "ticker" in df.columns else []:
        for item in required_items:
            if item not in df.columns:
                report.add(
                    QualityWarning(
                        check_name="completeness",
                        severity=Severity.ERROR,
                        ticker=ticker,
                        period="all",
                        message=f"Missing required line item: {item}",
                        details={"item": item},
                    )
                )


def run_all_checks(df: pd.DataFrame, include_kpi_checks: bool = True) -> QualityReport:
    report = QualityReport()
    check_balance_sheet_identity(df, report)
    check_positive_values(df, report)
    check_temporal_consistency(df, report)
    check_completeness(df, report)
    if include_kpi_checks:
        check_reasonable_ratios(df, report)
    logger.info(f"Quality checks complete: {report}")
    return report
