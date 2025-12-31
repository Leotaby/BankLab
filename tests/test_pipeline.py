"""Integration tests for the data pipeline."""

import pandas as pd
import pytest

from banklab.process.pipeline import DataPipeline


class TestDataPipelineIntegration:
    """Integration tests for DataPipeline."""

    @pytest.mark.network
    def test_run_prices(self, test_config):
        """Test prices pipeline stage."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_prices()

        # File should exist
        assert output_path.exists()

        # Should be valid parquet
        df = pd.read_parquet(output_path)
        assert len(df) > 0

        # Should have correct schema
        assert list(df.columns) == ["date", "ticker", "close", "ret"]

    @pytest.mark.network
    def test_run_factors(self, test_config):
        """Test factors pipeline stage."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_factors()

        assert output_path.exists()

        df = pd.read_parquet(output_path)
        assert len(df) > 0
        assert list(df.columns) == ["date", "mktrf", "smb", "hml", "rmw", "cma", "rf"]

    @pytest.mark.network
    def test_run_fundamentals(self, test_config):
        """Test fundamentals pipeline stage."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_fundamentals()

        assert output_path.exists()

        df = pd.read_parquet(output_path)
        assert len(df) > 0

        expected_cols = ["date", "cik", "ticker", "tag", "value", "unit", "fp", "fy", "form"]
        assert all(col in df.columns for col in expected_cols)

    def test_run_macro_skips_without_key(self, test_config):
        """Test that macro stage skips gracefully without API key."""
        test_config.fred_api_key = ""

        pipeline = DataPipeline(test_config)
        result = pipeline.run_macro()

        # Should return None without erroring
        assert result is None

    @pytest.mark.network
    def test_validate_outputs_all_present(self, test_config, mock_fred_api_key):
        """Test output validation when all files present."""
        # This is a longer test that runs full pipeline
        pytest.skip("Full pipeline test - run manually with real FRED key")

        pipeline = DataPipeline(test_config)
        pipeline.run_all()

        validation = pipeline.validate_outputs()

        # All files should be present and valid
        for filename, is_valid in validation.items():
            assert is_valid, f"{filename} validation failed"


class TestDataPipelineSchemas:
    """Tests for output data schemas and quality."""

    @pytest.mark.network
    def test_prices_schema_types(self, test_config):
        """Test that prices output has correct types."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_prices()
        df = pd.read_parquet(output_path)

        # Check types
        assert df["ticker"].dtype == "object"  # string
        assert pd.api.types.is_float_dtype(df["close"])
        assert pd.api.types.is_float_dtype(df["ret"])

    @pytest.mark.network
    def test_prices_unique_keys(self, test_config):
        """Test that prices have unique date-ticker combinations."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_prices()
        df = pd.read_parquet(output_path)

        # No duplicates on date + ticker
        duplicates = df.duplicated(subset=["date", "ticker"], keep=False)
        assert not duplicates.any()

    @pytest.mark.network
    def test_factors_unique_dates(self, test_config):
        """Test that factors have unique dates."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_factors()
        df = pd.read_parquet(output_path)

        assert df["date"].is_unique

    @pytest.mark.network
    def test_fundamentals_has_both_tickers(self, test_config):
        """Test that fundamentals includes both JPM and MS."""
        pipeline = DataPipeline(test_config)
        output_path = pipeline.run_fundamentals()
        df = pd.read_parquet(output_path)

        tickers = df["ticker"].unique()
        assert "JPM" in tickers
        assert "MS" in tickers
