"""Tests for SEC EDGAR data loader."""

import pandas as pd
import pytest

from banklab.ingest.sec import SECLoader


class TestSECLoader:
    """Tests for SECLoader functionality."""

    @pytest.mark.network
    def test_ticker_cik_map_loads(self, test_config):
        """Test that ticker->CIK mapping loads successfully."""
        loader = SECLoader(test_config)
        ticker_map = loader.get_ticker_cik_map()

        # Should have many tickers
        assert len(ticker_map) > 1000

        # JPM and MS should be present
        assert "JPM" in ticker_map
        assert "MS" in ticker_map

    @pytest.mark.network
    def test_get_cik_valid_ticker(self, test_config):
        """Test CIK lookup for valid tickers."""
        loader = SECLoader(test_config)

        jpm_cik = loader.get_cik("JPM")
        ms_cik = loader.get_cik("MS")

        # CIKs should be 10-digit strings
        assert len(jpm_cik) == 10
        assert len(ms_cik) == 10
        assert jpm_cik.isdigit()
        assert ms_cik.isdigit()

        # Known CIKs (may need update if SEC changes)
        assert jpm_cik == "0000019617"  # JPMorgan Chase
        assert ms_cik == "0000895421"  # Morgan Stanley

    @pytest.mark.network
    def test_get_cik_invalid_ticker(self, test_config):
        """Test CIK lookup raises for invalid ticker."""
        loader = SECLoader(test_config)

        with pytest.raises(ValueError, match="not found"):
            loader.get_cik("INVALID_TICKER_XYZ")

    @pytest.mark.network
    def test_get_cik_case_insensitive(self, test_config):
        """Test that ticker lookup is case-insensitive."""
        loader = SECLoader(test_config)

        assert loader.get_cik("jpm") == loader.get_cik("JPM")
        assert loader.get_cik("Ms") == loader.get_cik("MS")

    @pytest.mark.network
    def test_company_facts_returns_data(self, test_config):
        """Test that company facts API returns valid data."""
        loader = SECLoader(test_config)
        facts = loader.get_company_facts("JPM")

        # Should have expected structure
        assert "cik" in facts
        assert "entityName" in facts
        assert "facts" in facts

        # Should have US-GAAP facts
        assert "us-gaap" in facts["facts"]
        assert len(facts["facts"]["us-gaap"]) > 0

    @pytest.mark.network
    def test_extract_facts_to_df(self, test_config):
        """Test extraction of facts to DataFrame."""
        loader = SECLoader(test_config)
        df = loader.extract_facts_to_df("JPM")

        # Should be non-empty
        assert len(df) > 0

        # Should have required columns
        required_cols = ["date", "cik", "ticker", "tag", "value", "unit", "fp", "fy", "form"]
        assert all(col in df.columns for col in required_cols)

        # Ticker should be uppercase
        assert (df["ticker"] == "JPM").all()

        # Date should be datetime
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    @pytest.mark.network
    def test_extract_facts_date_monotonicity(self, test_config):
        """Test that extracted facts are sorted by date."""
        loader = SECLoader(test_config)
        df = loader.extract_facts_to_df("MS")

        # Dates should be monotonically non-decreasing
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    @pytest.mark.network
    def test_load_all_tickers(self, test_config):
        """Test loading facts for multiple tickers."""
        loader = SECLoader(test_config)
        df = loader.load_all_tickers(["JPM", "MS"])

        # Should have data for both tickers
        tickers = df["ticker"].unique()
        assert "JPM" in tickers
        assert "MS" in tickers

        # Each ticker should have data
        assert len(df[df["ticker"] == "JPM"]) > 0
        assert len(df[df["ticker"] == "MS"]) > 0

    @pytest.mark.network
    def test_submissions_returns_data(self, test_config):
        """Test that submissions API returns filing history."""
        loader = SECLoader(test_config)
        submissions = loader.get_submissions("JPM")

        # Should have filing data
        assert "filings" in submissions
        assert "recent" in submissions["filings"]

        # Should have 10-K and 10-Q filings
        forms = submissions["filings"]["recent"]["form"]
        assert "10-K" in forms or "10-Q" in forms

    @pytest.mark.network
    def test_caching_works(self, test_config):
        """Test that caching prevents duplicate downloads."""
        loader = SECLoader(test_config)

        # First call downloads
        facts1 = loader.get_company_facts("JPM")

        # Second call should use cache
        facts2 = loader.get_company_facts("JPM")

        # Should return same data
        assert facts1 == facts2

        # Cache file should exist
        cache_files = list(test_config.raw_dir.glob("sec/*.json"))
        assert len(cache_files) > 0
