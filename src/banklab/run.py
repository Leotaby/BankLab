"""BankLab CLI entry point.

Usage:
    python -m banklab.run --stage data      # Download and process all data
    python -m banklab.run --stage report    # Generate analysis report
    python -m banklab.run --stage all       # Full pipeline
"""

import argparse
import logging
import sys
from typing import Literal

from banklab.config import Config
from banklab.process.pipeline import DataPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_data(config: Config, force_refresh: bool = False) -> None:
    """Run data download and processing pipeline."""
    pipeline = DataPipeline(config)
    pipeline.run_all(force_refresh=force_refresh)


def run_report(config: Config) -> None:
    """Generate analysis report from processed data."""
    logger.info("Generating analysis report...")

    # Validate data exists
    pipeline = DataPipeline(config)
    validation = pipeline.validate_outputs()

    missing = [f for f, valid in validation.items() if not valid]
    if missing:
        logger.error(f"Missing data files: {missing}")
        logger.error("Run 'python -m banklab.run --stage data' first")
        sys.exit(1)

    # TODO: Implement report generation
    # For now, just summarize what we have
    import pandas as pd

    logger.info("=" * 60)
    logger.info("Data Summary Report")
    logger.info("=" * 60)

    # Prices summary
    prices = pd.read_parquet(config.processed_dir / "prices_daily.parquet")
    logger.info(f"\nPrices: {len(prices)} records")
    logger.info(f"  Date range: {prices['date'].min()} to {prices['date'].max()}")
    logger.info(f"  Tickers: {prices['ticker'].unique().tolist()}")

    # Factors summary
    factors = pd.read_parquet(config.processed_dir / "factors_daily.parquet")
    logger.info(f"\nFactors: {len(factors)} records")
    logger.info(f"  Date range: {factors['date'].min()} to {factors['date'].max()}")

    # Macro summary (if exists)
    macro_path = config.processed_dir / "macro_monthly.parquet"
    if macro_path.exists():
        macro = pd.read_parquet(macro_path)
        logger.info(f"\nMacro: {len(macro)} records")
        logger.info(f"  Series: {macro['series_id'].unique().tolist()}")

    # Fundamentals summary
    fundamentals = pd.read_parquet(config.processed_dir / "fundamentals_raw_facts.parquet")
    logger.info(f"\nFundamentals: {len(fundamentals)} records")
    logger.info(f"  Tickers: {fundamentals['ticker'].unique().tolist()}")
    logger.info(f"  Unique tags: {fundamentals['tag'].nunique()}")

    logger.info("\n" + "=" * 60)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BankLab: JPM vs Morgan Stanley Analytics Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m banklab.run --stage data        Download and process all data
  python -m banklab.run --stage report      Generate summary report
  python -m banklab.run --stage all         Full pipeline (data + report)
  python -m banklab.run --stage data -f     Force refresh all data
        """,
    )

    parser.add_argument(
        "--stage",
        type=str,
        choices=["data", "report", "all"],
        default="all",
        help="Pipeline stage to run (default: all)",
    )
    parser.add_argument(
        "-f",
        "--force-refresh",
        action="store_true",
        help="Force re-download of cached data",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Override data directory",
    )

    args = parser.parse_args()

    # Build config
    config = Config()
    if args.data_dir:
        from pathlib import Path

        config.data_dir = Path(args.data_dir)

    # Run requested stage
    stage: Literal["data", "report", "all"] = args.stage

    if stage in ("data", "all"):
        run_data(config, force_refresh=args.force_refresh)

    if stage in ("report", "all"):
        run_report(config)

    logger.info("Done!")


if __name__ == "__main__":
    main()
