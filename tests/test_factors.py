"""Tests for Fama-French factors loader."""

import pandas as pd
import pytest

from banklab.ingest.factors import FactorsLoader


class TestFactorsLoader:
    """Tests for FactorsLoader functionality."""

    @pytest.mark.network
    def test_download_factors_returns_data(self, test_config):
        """Test that factor download returns valid DataFrame."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        # Should be non-empty
        assert len(df) > 0

        # Should have many years of data
        assert len(df) > 1000  # ~4 years of daily data minimum

    @pytest.mark.network
    def test_download_factors_columns(self, test_config):
        """Test that factors DataFrame has correct columns."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        expected_cols = ["date", "mktrf", "smb", "hml", "rmw", "cma", "rf"]
        assert list(df.columns) == expected_cols

    @pytest.mark.network
    def test_download_factors_date_type(self, test_config):
        """Test that date column is datetime type."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        assert pd.api.types.is_datetime64_any_dtype(df["date"])
        assert df["date"].notna().all()

    @pytest.mark.network
    def test_download_factors_date_monotonicity(self, test_config):
        """Test that factors are sorted by date ascending."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        # Dates should be monotonically increasing
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    @pytest.mark.network
    def test_factors_are_decimals(self, test_config):
        """Test that factor returns are in decimal form (not percent)."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        factor_cols = ["mktrf", "smb", "hml", "rmw", "cma", "rf"]

        for col in factor_cols:
            # Daily returns should typically be small (< 10%)
            # Values > 0.5 would suggest they're in percent form
            assert df[col].abs().max() < 0.5, f"{col} appears to be in percent, not decimal"

            # Values should be mostly between -0.2 and 0.2 for daily data
            assert df[col].abs().mean() < 0.1

    @pytest.mark.network
    def test_factors_no_missing_values(self, test_config):
        """Test that factors don't have excessive missing values."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        factor_cols = ["mktrf", "smb", "hml", "rmw", "cma", "rf"]

        for col in factor_cols:
            # Allow some missing but not too many
            missing_pct = df[col].isna().sum() / len(df)
            assert missing_pct < 0.01, f"{col} has {missing_pct:.1%} missing values"

    @pytest.mark.network
    def test_to_parquet_schema(self, test_config):
        """Test conversion to final parquet schema."""
        loader = FactorsLoader(test_config)
        raw = loader.download_factors()
        output = loader.to_parquet_schema(raw)

        # Should have correct columns
        expected_cols = ["date", "mktrf", "smb", "hml", "rmw", "cma", "rf"]
        assert list(output.columns) == expected_cols

    @pytest.mark.network
    def test_factors_date_range_reasonable(self, test_config):
        """Test that data covers reasonable date range."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        # Should have data starting before 2000
        min_date = df["date"].min()
        assert min_date.year < 2000

        # Should have relatively recent data (within last year)
        max_date = df["date"].max()
        assert max_date.year >= 2024

    @pytest.mark.network
    def test_rf_rate_reasonable(self, test_config):
        """Test that risk-free rate values are reasonable."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        # RF should be non-negative (mostly)
        # Allow small negative due to data issues but not extremely negative
        assert df["rf"].min() > -0.01

        # RF should be small (daily < 0.1%)
        assert df["rf"].max() < 0.001  # 0.1% daily = ~36% annual

    @pytest.mark.network
    def test_unique_dates(self, test_config):
        """Test that each date appears only once."""
        loader = FactorsLoader(test_config)
        df = loader.download_factors()

        assert df["date"].is_unique

    @pytest.mark.network
    def test_caching_works(self, test_config):
        """Test that caching prevents duplicate downloads."""
        loader = FactorsLoader(test_config)

        # First call downloads
        df1 = loader.download_factors()

        # Second call should use cache
        df2 = loader.download_factors()

        # Should return same data
        pd.testing.assert_frame_equal(df1, df2)
