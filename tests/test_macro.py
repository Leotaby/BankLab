"""Tests for FRED macro data loader."""

import pandas as pd
import pytest

from banklab.ingest.macro import MacroLoader


class TestMacroLoader:
    """Tests for MacroLoader functionality."""

    def test_init_requires_api_key(self, test_config):
        """Test that MacroLoader requires FRED API key."""
        test_config.fred_api_key = ""

        with pytest.raises(ValueError, match="FRED_API_KEY"):
            MacroLoader(test_config)

    @pytest.mark.network
    def test_download_series_returns_data(self, test_config, mock_fred_api_key):
        """Test that series download returns valid DataFrame."""
        # Note: This test requires a valid FRED API key
        # Skip if using mock key
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        df = loader.download_series("DFF")

        # Should be non-empty
        assert len(df) > 0

        # Should have expected columns
        assert "date" in df.columns
        assert "series_id" in df.columns
        assert "value" in df.columns

    @pytest.mark.network
    def test_download_series_date_type(self, test_config, mock_fred_api_key):
        """Test that date column is datetime type."""
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        df = loader.download_series("DFF")

        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    @pytest.mark.network
    def test_download_series_date_monotonicity(self, test_config, mock_fred_api_key):
        """Test that series is sorted by date ascending."""
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        df = loader.download_series("DGS10")

        dates = df["date"].tolist()
        assert dates == sorted(dates)

    @pytest.mark.network
    def test_download_series_values_numeric(self, test_config, mock_fred_api_key):
        """Test that values are numeric."""
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        df = loader.download_series("DFF")

        assert pd.api.types.is_numeric_dtype(df["value"])

    @pytest.mark.network
    def test_load_all_series(self, test_config, mock_fred_api_key):
        """Test loading multiple series."""
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        df = loader.load_all_series(["DFF", "DGS10"])

        # Should have both series
        series_ids = df["series_id"].unique()
        assert "DFF" in series_ids
        assert "DGS10" in series_ids

    @pytest.mark.network
    def test_to_parquet_schema_monthly(self, test_config, mock_fred_api_key):
        """Test conversion to monthly parquet schema."""
        if test_config.fred_api_key == "test_api_key_12345":
            pytest.skip("Requires real FRED API key")

        loader = MacroLoader(test_config)
        raw = loader.download_series("DFF")
        output = loader.to_parquet_schema(raw)

        # Should have expected columns
        assert list(output.columns) == ["date", "series_id", "value"]

        # Should have fewer rows (monthly aggregation from daily)
        assert len(output) < len(raw)


class TestMacroLoaderUnit:
    """Unit tests that don't require network or API key."""

    def test_parse_fred_json_empty(self, test_config, mock_fred_api_key):
        """Test parsing empty FRED response."""
        loader = MacroLoader(test_config)

        empty_response = {"observations": []}
        df = loader._parse_fred_json(empty_response, "TEST")

        assert len(df) == 0
        assert list(df.columns) == ["date", "series_id", "value"]

    def test_parse_fred_json_valid(self, test_config, mock_fred_api_key):
        """Test parsing valid FRED response."""
        loader = MacroLoader(test_config)

        response = {
            "observations": [
                {"date": "2024-01-01", "value": "5.25"},
                {"date": "2024-01-02", "value": "5.30"},
                {"date": "2024-01-03", "value": "."},  # Missing value marker
            ]
        }

        df = loader._parse_fred_json(response, "DFF")

        # Should have 2 valid rows (missing value dropped)
        assert len(df) == 2
        assert df["series_id"].iloc[0] == "DFF"
        assert df["value"].iloc[0] == 5.25

    def test_parse_fred_json_dates_sorted(self, test_config, mock_fred_api_key):
        """Test that parsed data is sorted by date."""
        loader = MacroLoader(test_config)

        # Input in wrong order
        response = {
            "observations": [
                {"date": "2024-01-03", "value": "5.30"},
                {"date": "2024-01-01", "value": "5.25"},
                {"date": "2024-01-02", "value": "5.28"},
            ]
        }

        df = loader._parse_fred_json(response, "TEST")

        dates = df["date"].tolist()
        assert dates == sorted(dates)
