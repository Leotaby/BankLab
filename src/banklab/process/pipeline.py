"""Data processing pipeline.

Orchestrates data download, transformation, and parquet output.
"""

import logging
from pathlib import Path

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.ingest import FactorsLoader, MacroLoader, MarketLoader, SECLoader

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrates full data pipeline from raw to processed.

    Outputs:
    - prices_daily.parquet
    - factors_daily.parquet
    - macro_monthly.parquet
    - fundamentals_raw_facts.parquet
    """

    def __init__(self, config: Config | None = None):
        """Initialize pipeline.

        Args:
            config: BankLab configuration
        """
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()

    def run_prices(self, force_refresh: bool = False) -> Path:
        """Download and process price data.

        Args:
            force_refresh: Re-download even if cached

        Returns:
            Path to output parquet file
        """
        logger.info("Processing prices...")
        loader = MarketLoader(self.config)

        df = loader.load_all_tickers(force_refresh=force_refresh)
        output = loader.to_parquet_schema(df)

        output_path = self.config.processed_dir / "prices_daily.parquet"
        output.to_parquet(output_path, index=False)

        logger.info(f"Saved {len(output)} rows to {output_path}")
        return output_path

    def run_factors(self, force_refresh: bool = False) -> Path:
        """Download and process factor data.

        Args:
            force_refresh: Re-download even if cached

        Returns:
            Path to output parquet file
        """
        logger.info("Processing factors...")
        loader = FactorsLoader(self.config)

        df = loader.download_factors(force_refresh=force_refresh)
        output = loader.to_parquet_schema(df)

        output_path = self.config.processed_dir / "factors_daily.parquet"
        output.to_parquet(output_path, index=False)

        logger.info(f"Saved {len(output)} rows to {output_path}")
        return output_path

    def run_macro(self, force_refresh: bool = False) -> Path | None:
        """Download and process macro data.

        Args:
            force_refresh: Re-download even if cached

        Returns:
            Path to output parquet file, or None if FRED API key not set
        """
        logger.info("Processing macro data...")

        try:
            loader = MacroLoader(self.config)
        except ValueError as e:
            logger.warning(f"Skipping macro data: {e}")
            return None

        df = loader.load_all_series(force_refresh=force_refresh)
        output = loader.to_parquet_schema(df)

        output_path = self.config.processed_dir / "macro_monthly.parquet"
        output.to_parquet(output_path, index=False)

        logger.info(f"Saved {len(output)} rows to {output_path}")
        return output_path

    def run_fundamentals(self, force_refresh: bool = False) -> Path:
        """Download and process SEC fundamentals data.

        Args:
            force_refresh: Re-download even if cached

        Returns:
            Path to output parquet file
        """
        logger.info("Processing fundamentals...")
        loader = SECLoader(self.config)

        df = loader.load_all_tickers()

        # Standardize for parquet
        output = df.copy()
        output["date"] = pd.to_datetime(output["date"]).dt.date

        output_path = self.config.processed_dir / "fundamentals_raw_facts.parquet"
        output.to_parquet(output_path, index=False)

        logger.info(f"Saved {len(output)} rows to {output_path}")
        return output_path

    def run_all(self, force_refresh: bool = False) -> dict[str, Path | None]:
        """Run full data pipeline.

        Args:
            force_refresh: Re-download all data

        Returns:
            Dictionary of stage names to output paths
        """
        logger.info("=" * 60)
        logger.info("Starting BankLab data pipeline")
        logger.info(f"Tickers: {self.config.tickers}")
        logger.info("=" * 60)

        results = {}

        # Run each stage
        results["prices"] = self.run_prices(force_refresh)
        results["factors"] = self.run_factors(force_refresh)
        results["macro"] = self.run_macro(force_refresh)
        results["fundamentals"] = self.run_fundamentals(force_refresh)

        logger.info("=" * 60)
        logger.info("Pipeline complete!")
        for stage, path in results.items():
            if path:
                logger.info(f"  {stage}: {path}")
        logger.info("=" * 60)

        return results

    def validate_outputs(self) -> dict[str, bool]:
        """Validate that all expected outputs exist and are non-empty.

        Returns:
            Dictionary of file names to validation status
        """
        expected_files = [
            "prices_daily.parquet",
            "factors_daily.parquet",
            "macro_monthly.parquet",
            "fundamentals_raw_facts.parquet",
        ]

        results = {}
        for filename in expected_files:
            path = self.config.processed_dir / filename
            if path.exists():
                df = pd.read_parquet(path)
                results[filename] = len(df) > 0
            else:
                results[filename] = False

        return results
