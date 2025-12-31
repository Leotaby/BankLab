"""Tests for data quality checks."""

import pandas as pd

from banklab.quality.checks import (
    QualityReport,
    QualityWarning,
    Severity,
    check_balance_sheet_identity,
    check_completeness,
    check_positive_values,
    check_reasonable_ratios,
    run_all_checks,
)


class TestQualityReport:
    """Tests for QualityReport class."""

    def test_empty_report(self):
        """Test empty report initialization."""
        report = QualityReport()
        assert len(report.warnings) == 0
        assert not report.has_errors()

    def test_add_warning(self):
        """Test adding warnings to report."""
        report = QualityReport()
        warning = QualityWarning(
            check_name="test",
            severity=Severity.WARNING,
            ticker="JPM",
            period="2024-Q1",
            message="Test warning",
        )
        report.add(warning)

        assert len(report.warnings) == 1
        assert not report.has_errors()

    def test_has_errors(self):
        """Test error detection."""
        report = QualityReport()
        report.add(
            QualityWarning(
                check_name="test",
                severity=Severity.ERROR,
                ticker="JPM",
                period="2024-Q1",
                message="Test error",
            )
        )

        assert report.has_errors()

    def test_summary(self):
        """Test summary statistics."""
        report = QualityReport()
        report.add(
            QualityWarning(
                check_name="test",
                severity=Severity.ERROR,
                ticker="JPM",
                period="2024-Q1",
                message="Error",
            )
        )
        report.add(
            QualityWarning(
                check_name="test",
                severity=Severity.WARNING,
                ticker="MS",
                period="2024-Q1",
                message="Warning",
            )
        )
        report.add(
            QualityWarning(
                check_name="test",
                severity=Severity.INFO,
                ticker="JPM",
                period="2024-Q2",
                message="Info",
            )
        )

        summary = report.summary()
        assert summary["error"] == 1
        assert summary["warning"] == 1
        assert summary["info"] == 1

    def test_to_dataframe(self):
        """Test conversion to DataFrame."""
        report = QualityReport()
        report.add(
            QualityWarning(
                check_name="test",
                severity=Severity.WARNING,
                ticker="JPM",
                period="2024-Q1",
                message="Test",
            )
        )

        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "ticker" in df.columns


class TestBalanceSheetIdentity:
    """Tests for balance sheet identity check."""

    def test_balanced_sheet(self):
        """Test that balanced sheet passes."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "total_assets": 100,
                    "total_liabilities": 80,
                    "total_equity": 20,
                }
            ]
        )

        report = QualityReport()
        check_balance_sheet_identity(df, report)

        assert len(report.warnings) == 0

    def test_unbalanced_sheet(self):
        """Test that unbalanced sheet triggers warning."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "total_assets": 100,
                    "total_liabilities": 80,
                    "total_equity": 10,  # Should be 20
                }
            ]
        )

        report = QualityReport()
        check_balance_sheet_identity(df, report, tolerance=0.01)

        assert len(report.warnings) == 1
        assert "doesn't balance" in report.warnings[0].message


class TestPositiveValues:
    """Tests for positive value check."""

    def test_all_positive(self):
        """Test that all positive values pass."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "total_assets": 100,
                    "total_equity": 20,
                }
            ]
        )

        report = QualityReport()
        check_positive_values(df, report)

        assert len(report.warnings) == 0

    def test_negative_assets(self):
        """Test that negative assets trigger error."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "total_assets": -100,
                }
            ]
        )

        report = QualityReport()
        check_positive_values(df, report)

        assert len(report.warnings) == 1
        assert report.warnings[0].severity == Severity.ERROR


class TestReasonableRatios:
    """Tests for ratio reasonableness check."""

    def test_reasonable_ratios(self):
        """Test that reasonable ratios pass."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "roe": 0.10,
                    "roa": 0.01,
                    "leverage": 10,
                }
            ]
        )

        report = QualityReport()
        check_reasonable_ratios(df, report)

        assert len(report.warnings) == 0

    def test_extreme_leverage(self):
        """Test that extreme leverage triggers warning."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "leverage": 50,  # Way too high
                }
            ]
        )

        report = QualityReport()
        check_reasonable_ratios(df, report)

        assert len(report.warnings) == 1
        assert "unusually high" in report.warnings[0].message


class TestCompleteness:
    """Tests for completeness check."""

    def test_complete_data(self):
        """Test that complete data passes."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "total_assets": 100,
                    "total_equity": 20,
                    "net_income": 5,
                }
            ]
        )

        report = QualityReport()
        check_completeness(df, report)

        assert not any(w.severity == Severity.ERROR for w in report.warnings)

    def test_missing_required_column(self):
        """Test that missing required column triggers error."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    # Missing total_assets, total_equity, net_income
                }
            ]
        )

        report = QualityReport()
        check_completeness(df, report, required_items=["total_assets"])

        assert len(report.warnings) == 1
        assert report.warnings[0].severity == Severity.ERROR


class TestRunAllChecks:
    """Tests for the run_all_checks aggregator."""

    def test_runs_all_checks(self):
        """Test that all checks are executed."""
        df = pd.DataFrame(
            [
                {
                    "ticker": "JPM",
                    "fiscal_year": 2024,
                    "fiscal_period": "Q1",
                    "total_assets": 100,
                    "total_liabilities": 80,
                    "total_equity": 20,
                    "net_income": 5,
                }
            ]
        )

        report = run_all_checks(df, include_kpi_checks=False)

        # Should have run multiple checks
        assert len(report.checks_run) >= 3
        assert "balance_sheet_identity" in report.checks_run
        assert "positive_values" in report.checks_run
        assert "completeness" in report.checks_run
