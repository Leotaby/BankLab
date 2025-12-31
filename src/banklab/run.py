"""BankLab CLI entry point.

Usage:
    python -m banklab.run --stage data           # Download raw data
    python -m banklab.run --stage fundamentals   # Normalize + calculate KPIs
    python -m banklab.run --stage report         # Generate Quarto report
    python -m banklab.run --stage all            # Full pipeline
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
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


def run_fundamentals(config: Config) -> None:
    """Run fundamentals normalization and KPI calculation."""
    from banklab.process.fundamentals import FundamentalsPipeline

    pipeline = FundamentalsPipeline(config)
    pipeline.run()


def run_report(config: Config) -> None:
    """Generate analysis report from processed data."""
    logger.info("Generating analysis report...")

    # Check if Quarto is available
    report_path = Path("reports/fundamentals_review.qmd")
    if not report_path.exists():
        logger.error(f"Report template not found at {report_path}")
        sys.exit(1)

    # Try to render with Quarto
    try:
        result = subprocess.run(
            ["quarto", "render", str(report_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            logger.info("Report rendered successfully!")
            logger.info("Output: reports/fundamentals_review.html")
        else:
            logger.warning("Quarto render failed. Falling back to summary mode.")
            logger.warning(f"Error: {result.stderr}")
            _run_summary_report(config)
    except FileNotFoundError:
        logger.warning("Quarto not found. Install from https://quarto.org")
        logger.info("Falling back to text summary...")
        _run_summary_report(config)


def _run_summary_report(config: Config) -> None:
    """Generate text summary when Quarto is not available."""
    import pandas as pd

    # Validate data exists
    pipeline = DataPipeline(config)
    validation = pipeline.validate_outputs()

    missing = [f for f, valid in validation.items() if not valid]
    if missing:
        logger.error(f"Missing data files: {missing}")
        logger.error("Run 'python -m banklab.run --stage data' first")
        sys.exit(1)

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
    logger.info(f"\nFundamentals (raw): {len(fundamentals)} records")
    logger.info(f"  Tickers: {fundamentals['ticker'].unique().tolist()}")
    logger.info(f"  Unique tags: {fundamentals['tag'].nunique()}")

    # KPIs summary (if exists)
    kpis_path = config.processed_dir / "kpis_quarterly.parquet"
    if kpis_path.exists():
        kpis = pd.read_parquet(kpis_path)
        logger.info(f"\nKPIs: {len(kpis)} records")
        logger.info(f"  KPI types: {kpis['kpi_name'].nunique()}")

    logger.info("\n" + "=" * 60)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BankLab: JPM vs Morgan Stanley Analytics Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m banklab.run --stage data           Download raw data
  python -m banklab.run --stage fundamentals   Normalize facts + calculate KPIs
  python -m banklab.run --stage report         Generate Quarto report
  python -m banklab.run --stage all            Full pipeline
  python -m banklab.run --stage data -f        Force refresh all data
        """,
    )

    parser.add_argument(
        "--stage",
        type=str,
        choices=["data", "fundamentals", "report", "all"],
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
        config.data_dir = Path(args.data_dir)

    # Run requested stage
    stage: Literal["data", "fundamentals", "report", "all"] = args.stage

    if stage in ("data", "all"):
        run_data(config, force_refresh=args.force_refresh)

    if stage in ("fundamentals", "all"):
        run_fundamentals(config)

    if stage in ("report", "all"):
        run_report(config)

    logger.info("Done!")


if __name__ == "__main__":
    main()
