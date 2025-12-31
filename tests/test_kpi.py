"""Unit tests for KPI calculation functions.

These tests use small toy dataframes to verify KPI calculations are correct.
All tests are deterministic and don't require network access.
"""

import numpy as np
import pandas as pd
import pytest

from banklab.kpi.kpi import (
    allowance_coverage_ratio,
    book_value_per_share,
    calculate_all_kpis,
    earnings_per_share,
    efficiency_ratio,
    equity_to_assets,
    leverage_ratio,
    loan_to_deposit_ratio,
    net_interest_margin,
    pre_provision_net_revenue,
    price_to_book,
    price_to_earnings,
    qoq_growth,
    return_on_assets,
    return_on_equity,
    tangible_book_value_per_share,
    tangible_equity_ratio,
    yoy_growth,
)


class TestProfitabilityKPIs:
    """Tests for profitability metrics."""

    def test_roe_basic(self):
        """Test basic ROE calculation."""
        result = return_on_equity(
            net_income=5_000_000,
            total_equity=50_000_000,
            annualize=False,
        )
        assert result == pytest.approx(0.10)

    def test_roe_annualized(self):
        """Test annualized ROE."""
        result = return_on_equity(
            net_income=1_250_000,
            total_equity=50_000_000,
            annualize=True,
            periods_per_year=4,
        )
        assert result == pytest.approx(0.10)

    def test_roe_zero_equity(self):
        """Test ROE with zero equity returns NaN."""
        result = return_on_equity(net_income=5_000_000, total_equity=0, annualize=False)
        assert np.isnan(result)

    def test_roe_negative_income(self):
        """Test ROE handles negative income."""
        result = return_on_equity(
            net_income=-5_000_000,
            total_equity=50_000_000,
            annualize=False,
        )
        assert result == pytest.approx(-0.10)

    def test_roa_basic(self):
        """Test basic ROA calculation."""
        result = return_on_assets(
            net_income=5_000_000,
            total_assets=500_000_000,
            annualize=False,
        )
        assert result == pytest.approx(0.01)

    def test_roa_annualized(self):
        """Test annualized ROA."""
        result = return_on_assets(
            net_income=1_250_000,
            total_assets=500_000_000,
            annualize=True,
            periods_per_year=4,
        )
        assert result == pytest.approx(0.01)

    def test_nim_basic(self):
        """Test net interest margin calculation."""
        result = net_interest_margin(
            net_interest_income=3_000_000,
            total_assets=400_000_000,
            annualize=False,
        )
        assert result == pytest.approx(0.0075)

    def test_nim_annualized(self):
        """Test annualized NIM."""
        result = net_interest_margin(
            net_interest_income=3_000_000,
            total_assets=400_000_000,
            annualize=True,
            periods_per_year=4,
        )
        assert result == pytest.approx(0.03)

    def test_efficiency_ratio_basic(self):
        """Test efficiency ratio calculation."""
        result = efficiency_ratio(
            noninterest_expense=6_000_000,
            total_revenue=10_000_000,
        )
        assert result == pytest.approx(0.60)

    def test_efficiency_ratio_zero_revenue(self):
        """Test efficiency ratio with zero revenue."""
        result = efficiency_ratio(noninterest_expense=6_000_000, total_revenue=0)
        assert np.isnan(result)

    def test_ppnr_basic(self):
        """Test PPNR calculation."""
        result = pre_provision_net_revenue(
            net_interest_income=5_000_000,
            noninterest_income=3_000_000,
            noninterest_expense=4_000_000,
        )
        assert result == 4_000_000


class TestValuationKPIs:
    """Tests for valuation metrics."""

    def test_eps_basic(self):
        """Test EPS calculation."""
        result = earnings_per_share(
            net_income=10_000_000,
            shares_outstanding=1_000_000,
        )
        assert result == pytest.approx(10.0)

    def test_eps_zero_shares(self):
        """Test EPS with zero shares."""
        result = earnings_per_share(net_income=10_000_000, shares_outstanding=0)
        assert np.isnan(result)

    def test_bvps_basic(self):
        """Test book value per share."""
        result = book_value_per_share(
            total_equity=50_000_000,
            shares_outstanding=1_000_000,
        )
        assert result == pytest.approx(50.0)

    def test_tbvps_basic(self):
        """Test tangible book value per share."""
        result = tangible_book_value_per_share(
            total_equity=50_000_000,
            goodwill=5_000_000,
            intangible_assets=2_000_000,
            shares_outstanding=1_000_000,
        )
        assert result == pytest.approx(43.0)

    def test_tbvps_no_intangibles(self):
        """Test TBVPS when intangibles are None/NaN."""
        result = tangible_book_value_per_share(
            total_equity=50_000_000,
            goodwill=None,
            intangible_assets=np.nan,
            shares_outstanding=1_000_000,
        )
        assert result == pytest.approx(50.0)

    def test_price_to_book(self):
        """Test P/B ratio."""
        result = price_to_book(stock_price=75.0, book_value_per_share=50.0)
        assert result == pytest.approx(1.5)

    def test_price_to_earnings(self):
        """Test P/E ratio."""
        result = price_to_earnings(stock_price=100.0, eps_ttm=10.0)
        assert result == pytest.approx(10.0)


class TestCapitalKPIs:
    """Tests for capital and leverage metrics."""

    def test_equity_to_assets(self):
        """Test equity/assets ratio."""
        result = equity_to_assets(
            total_equity=50_000_000,
            total_assets=500_000_000,
        )
        assert result == pytest.approx(0.10)

    def test_tangible_equity_ratio(self):
        """Test TCE ratio calculation."""
        result = tangible_equity_ratio(
            total_equity=50_000_000,
            goodwill=5_000_000,
            intangible_assets=2_000_000,
            total_assets=500_000_000,
        )
        expected = (50 - 5 - 2) / (500 - 5 - 2)
        assert result == pytest.approx(expected)

    def test_leverage_ratio(self):
        """Test leverage multiple."""
        result = leverage_ratio(
            total_assets=500_000_000,
            total_equity=50_000_000,
        )
        assert result == pytest.approx(10.0)


class TestAssetQualityKPIs:
    """Tests for asset quality metrics."""

    def test_allowance_coverage(self):
        """Test allowance coverage ratio."""
        result = allowance_coverage_ratio(
            allowance_for_loan_losses=5_000_000,
            loans_net=95_000_000,
        )
        assert result == pytest.approx(0.05)

    def test_loan_to_deposit(self):
        """Test loan-to-deposit ratio."""
        result = loan_to_deposit_ratio(
            loans_net=80_000_000,
            total_deposits=100_000_000,
        )
        assert result == pytest.approx(0.80)


class TestGrowthKPIs:
    """Tests for growth metrics."""

    def test_yoy_growth_positive(self):
        """Test YoY growth - positive case."""
        result = yoy_growth(current_value=110, prior_year_value=100)
        assert result == pytest.approx(0.10)

    def test_yoy_growth_negative(self):
        """Test YoY growth - decline."""
        result = yoy_growth(current_value=90, prior_year_value=100)
        assert result == pytest.approx(-0.10)

    def test_yoy_growth_zero_prior(self):
        """Test YoY growth with zero prior value."""
        result = yoy_growth(current_value=100, prior_year_value=0)
        assert np.isnan(result)

    def test_qoq_growth(self):
        """Test QoQ growth."""
        result = qoq_growth(current_value=105, prior_quarter_value=100)
        assert result == pytest.approx(0.05)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_inputs(self):
        """Test that None inputs return NaN."""
        assert np.isnan(return_on_equity(None, 50_000_000, annualize=False))
        assert np.isnan(return_on_equity(5_000_000, None, annualize=False))
        assert np.isnan(efficiency_ratio(None, 10_000_000))

    def test_nan_inputs(self):
        """Test that NaN inputs return NaN."""
        assert np.isnan(return_on_equity(np.nan, 50_000_000, annualize=False))
        assert np.isnan(book_value_per_share(np.nan, 1_000_000))

    def test_mixed_valid_invalid(self):
        """Test functions handle mixed valid/invalid gracefully."""
        result = tangible_book_value_per_share(
            total_equity=50_000_000,
            goodwill=None,
            intangible_assets=None,
            shares_outstanding=1_000_000,
        )
        assert result == pytest.approx(50.0)


class TestCalculateAllKPIs:
    """Tests for the aggregator function."""

    def test_calculate_all_kpis_basic(self):
        """Test calculating all KPIs from a row."""
        row = pd.Series(
            {
                "ticker": "TEST",
                "fiscal_year": 2024,
                "fiscal_period": "Q4",
                "net_income": 5_000_000,
                "total_equity": 50_000_000,
                "total_assets": 500_000_000,
                "net_interest_income": 8_000_000,
                "noninterest_income": 4_000_000,
                "noninterest_expense": 6_000_000,
                "total_revenue": 12_000_000,
                "shares_outstanding": 1_000_000,
                "goodwill": 5_000_000,
                "intangible_assets": 2_000_000,
                "loans_net": 80_000_000,
                "total_deposits": 100_000_000,
                "allowance_for_loan_losses": 4_000_000,
            }
        )

        kpis = calculate_all_kpis(row)

        assert "roe" in kpis
        assert "roa" in kpis
        assert "eps" in kpis
        assert "bvps" in kpis
        assert "tbvps" in kpis
        assert "leverage" in kpis

        assert kpis["eps"] == pytest.approx(5.0)
        assert kpis["bvps"] == pytest.approx(50.0)
        assert kpis["leverage"] == pytest.approx(10.0)

    def test_calculate_all_kpis_missing_data(self):
        """Test KPI calculation with missing line items."""
        row = pd.Series(
            {
                "ticker": "TEST",
                "fiscal_year": 2024,
                "fiscal_period": "Q4",
                "net_income": 5_000_000,
                "total_equity": 50_000_000,
            }
        )

        kpis = calculate_all_kpis(row)

        assert not np.isnan(kpis["roe"])
        assert np.isnan(kpis["ldr"])
