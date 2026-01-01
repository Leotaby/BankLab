"""Tests for market analytics module."""

import numpy as np
import pandas as pd
import pytest

from banklab.market.factors import (
    estimate_capm,
    factor_results_to_dataframe,
)
from banklab.market.returns import (
    compute_drawdowns,
    compute_max_drawdown,
    compute_returns,
    compute_rolling_volatility,
    returns_to_quarterly,
)


class TestComputeReturns:
    """Tests for return calculations."""

    @pytest.fixture
    def sample_prices(self):
        """Create sample price data."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        return pd.DataFrame(
            {
                "ticker": ["TEST"] * 10,
                "date": dates,
                "close": [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
            }
        )

    def test_compute_returns_log(self, sample_prices):
        """Test log return calculation."""
        result = compute_returns(sample_prices, method="log")

        assert "return" in result.columns
        assert "cum_return" in result.columns
        assert len(result) == 10
        assert pd.isna(result["return"].iloc[0])

        expected_ret1 = np.log(102 / 100)
        assert result["return"].iloc[1] == pytest.approx(expected_ret1, rel=1e-6)

    def test_compute_returns_simple(self, sample_prices):
        """Test simple return calculation."""
        result = compute_returns(sample_prices, method="simple")

        expected_ret1 = (102 - 100) / 100
        assert result["return"].iloc[1] == pytest.approx(expected_ret1, rel=1e-6)

    def test_cumulative_returns(self, sample_prices):
        """Test cumulative return calculation."""
        result = compute_returns(sample_prices, method="simple")

        final_cum = result["cum_return"].iloc[-1]
        assert final_cum == pytest.approx(0.10, rel=0.01)


class TestRollingVolatility:
    """Tests for volatility calculations."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample return data."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        returns = np.random.normal(0.001, 0.02, 100)
        return pd.DataFrame(
            {
                "ticker": ["TEST"] * 100,
                "date": dates,
                "return": returns,
            }
        )

    def test_rolling_vol_columns(self, sample_returns):
        """Test that rolling volatility adds correct columns."""
        result = compute_rolling_volatility(sample_returns, windows=[21, 63])

        assert "vol_21d" in result.columns
        assert "vol_63d" in result.columns

    def test_rolling_vol_annualized(self, sample_returns):
        """Test that volatility is annualized."""
        result = compute_rolling_volatility(sample_returns, windows=[21])

        avg_vol = result["vol_21d"].dropna().mean()
        assert 0.1 < avg_vol < 0.6


class TestDrawdowns:
    """Tests for drawdown calculations."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample with known drawdown."""
        return pd.DataFrame(
            {
                "ticker": ["TEST"] * 5,
                "date": pd.date_range("2020-01-01", periods=5),
                "return": [0.10, 0.05, -0.20, -0.10, 0.15],
            }
        )

    def test_drawdown_columns(self, sample_returns):
        """Test that drawdown adds correct columns."""
        result = compute_drawdowns(sample_returns)

        assert "cum_wealth" in result.columns
        assert "running_max" in result.columns
        assert "drawdown" in result.columns

    def test_drawdown_negative(self, sample_returns):
        """Test that drawdowns are negative or zero."""
        result = compute_drawdowns(sample_returns)

        assert (result["drawdown"] <= 0).all()

    def test_max_drawdown(self, sample_returns):
        """Test max drawdown calculation."""
        result = compute_max_drawdown(sample_returns)

        assert len(result) == 1
        assert "max_drawdown" in result.columns
        assert result["max_drawdown"].iloc[0] < 0


class TestReturnsToQuarterly:
    """Tests for quarterly aggregation."""

    @pytest.fixture
    def sample_daily_returns(self):
        """Create sample daily returns spanning quarters."""
        dates = pd.date_range("2020-01-01", "2020-06-30", freq="D")
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))
        return pd.DataFrame(
            {
                "ticker": ["TEST"] * len(dates),
                "date": dates,
                "return": returns,
            }
        )

    def test_quarterly_aggregation(self, sample_daily_returns):
        """Test quarterly return aggregation."""
        result = returns_to_quarterly(sample_daily_returns)

        assert "year" in result.columns
        assert "quarter" in result.columns
        assert "quarterly_return" in result.columns
        assert "quarterly_vol" in result.columns

        # Should have Q1 and Q2 2020
        assert len(result) == 2


class TestFactorModels:
    """Tests for factor model estimation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample returns and factors."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="D")

        # Market returns
        mktrf = np.random.normal(0.0004, 0.01, 252)
        rf = np.full(252, 0.0001)

        # Stock returns with beta = 1.2
        stock_returns = 0.0001 + 1.2 * mktrf + np.random.normal(0, 0.005, 252)

        returns = pd.DataFrame(
            {
                "ticker": ["TEST"] * 252,
                "date": dates,
                "return": stock_returns,
            }
        )

        factors = pd.DataFrame(
            {
                "date": dates,
                "mktrf": mktrf,
                "rf": rf,
                "smb": np.random.normal(0, 0.005, 252),
                "hml": np.random.normal(0, 0.005, 252),
                "rmw": np.random.normal(0, 0.005, 252),
                "cma": np.random.normal(0, 0.005, 252),
            }
        )

        return returns, factors

    def test_capm_estimation(self, sample_data):
        """Test CAPM estimation."""
        returns, factors = sample_data
        results = estimate_capm(returns, factors)

        assert len(results) == 1
        result = results[0]

        assert result.ticker == "TEST"
        assert result.model == "CAPM"
        assert 0.8 < result.betas["mktrf"] < 1.6  # Beta should be near 1.2
        assert result.r_squared > 0.5  # Good fit expected

    def test_factor_results_to_dataframe(self, sample_data):
        """Test conversion to DataFrame."""
        returns, factors = sample_data
        results = estimate_capm(returns, factors)
        df = factor_results_to_dataframe(results)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "ticker" in df.columns
        assert "beta_mktrf" in df.columns
        assert "r_squared" in df.columns
