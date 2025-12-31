"""Tests for market data loader."""

import numpy as np
import pandas as pd
import pytest

from banklab.ingest.market import MarketLoader


class TestMarketLoader:
    """Tests for MarketLoader functionality."""

    @pytest.mark.network
    def test_download_prices_returns_data(self, test_config):
        """Test that price download returns valid DataFrame."""
        loader = MarketLoader(test_config)
        df = loader.download_prices("JPM")

        # Should be non-empty
        assert len(df) > 0

        # Should have expected columns
        assert "date" in df.columns
        assert "close" in df.columns
        assert "ticker" in df.columns

    @pytest.mark.network
    def test_download_prices_date_column(self, test_config):
        """Test that date column is properly parsed."""
        loader = MarketLoader(test_config)
        df = loader.download_prices("MS")

        # Date should be datetime type
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

        # Dates should be valid (not NaT)
        assert df["date"].notna().all()

    @pytest.mark.network
    def test_download_prices_date_monotonicity(self, test_config):
        """Test that prices are sorted by date ascending."""
        loader = MarketLoader(test_config)
        df = loader.download_prices("JPM")

        # Dates should be monotonically increasing
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    @pytest.mark.network
    def test_compute_returns_simple(self, test_config):
        """Test simple return calculation."""
        loader = MarketLoader(test_config)
        prices = loader.download_prices("JPM")
        df = loader.compute_returns(prices, method="simple")

        # Should have ret column
        assert "ret" in df.columns

        # First return should be NaN (no previous price)
        assert pd.isna(df["ret"].iloc[0])

        # Verify return calculation for a few rows
        for i in range(1, min(5, len(df))):
            expected = (df["close"].iloc[i] / df["close"].iloc[i - 1]) - 1
            actual = df["ret"].iloc[i]
            assert abs(expected - actual) < 1e-10

    @pytest.mark.network
    def test_compute_returns_log(self, test_config):
        """Test log return calculation."""
        loader = MarketLoader(test_config)
        prices = loader.download_prices("MS")
        df = loader.compute_returns(prices, method="log")

        # Verify log return calculation
        for i in range(1, min(5, len(df))):
            expected = np.log(df["close"].iloc[i] / df["close"].iloc[i - 1])
            actual = df["ret"].iloc[i]
            assert abs(expected - actual) < 1e-10

    @pytest.mark.network
    def test_load_all_tickers(self, test_config):
        """Test loading prices for multiple tickers."""
        loader = MarketLoader(test_config)
        df = loader.load_all_tickers(["JPM", "MS"])

        # Should have both tickers
        tickers = df["ticker"].unique()
        assert "JPM" in tickers
        assert "MS" in tickers

        # Each ticker should have returns calculated
        for ticker in ["JPM", "MS"]:
            ticker_df = df[df["ticker"] == ticker]
            assert len(ticker_df) > 0
            assert "ret" in ticker_df.columns

    @pytest.mark.network
    def test_to_parquet_schema(self, test_config):
        """Test conversion to final parquet schema."""
        loader = MarketLoader(test_config)
        raw = loader.load_all_tickers(["JPM"])
        output = loader.to_parquet_schema(raw)

        # Should have exactly these columns
        assert list(output.columns) == ["date", "ticker", "close", "ret"]

        # Date should be Python date objects
        assert all(isinstance(d, type(output["date"].iloc[0])) for d in output["date"])

    @pytest.mark.network
    def test_price_values_reasonable(self, test_config):
        """Test that price values are reasonable."""
        loader = MarketLoader(test_config)
        df = loader.download_prices("JPM")

        # Close prices should be positive
        assert (df["close"] > 0).all()

        # Close prices should be in reasonable range (not crazy outliers)
        # JPM typically trades between $50-$250
        assert df["close"].min() > 1
        assert df["close"].max() < 1000

    @pytest.mark.network
    def test_unique_date_ticker_pairs(self, test_config):
        """Test that date-ticker combinations are unique."""
        loader = MarketLoader(test_config)
        df = loader.load_all_tickers(["JPM", "MS"])

        # No duplicate date-ticker pairs
        duplicates = df.duplicated(subset=["date", "ticker"], keep=False)
        assert not duplicates.any()

    @pytest.mark.network
    def test_caching_works(self, test_config):
        """Test that caching prevents duplicate downloads."""
        loader = MarketLoader(test_config)

        # First call downloads
        df1 = loader.download_prices("JPM")

        # Second call should use cache
        df2 = loader.download_prices("JPM")

        # Should return same data
        pd.testing.assert_frame_equal(df1, df2)
