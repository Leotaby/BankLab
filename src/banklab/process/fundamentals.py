"""Phase 2 pipeline: Fundamentals normalization and KPI calculation.

This module orchestrates the transformation from raw XBRL facts to
standardized quarterly financials and KPIs.

Output Files
------------
- fundamentals_quarterly.parquet: Normalized line items (long format)
- fundamentals_quarterly_wide.parquet: Same data in wide format
- kpis_quarterly.parquet: Calculated KPIs (long format)
- data_dictionary.csv: Documentation of all line items
- quality_report.csv: Data quality warnings
"""

import logging
from pathlib import Path

import pandas as pd

from banklab.clean.xbrl_normalize import XBRLNormalizer
from banklab.config import DEFAULT_CONFIG, Config
from banklab.kpi.kpi import KPI_DEFINITIONS, calculate_all_kpis
from banklab.quality.checks import run_all_checks

logger = logging.getLogger(__name__)


class FundamentalsPipeline:
    """Pipeline for fundamentals normalization and KPI calculation."""

    def __init__(self, config: Config | None = None):
        """Initialize pipeline.

        Args:
            config: BankLab configuration
        """
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()

    def run(self) -> dict[str, Path]:
        """Run full fundamentals pipeline.

        Returns:
            Dictionary of output name -> file path
        """
        logger.info("=" * 60)
        logger.info("Starting Fundamentals Pipeline (Phase 2)")
        logger.info("=" * 60)

        outputs = {}

        # Step 1: Normalize raw facts
        logger.info("Step 1: Normalizing XBRL facts...")
        normalized = self._normalize_facts()
        outputs["fundamentals_quarterly"] = self._save_fundamentals(normalized)

        # Step 2: Create wide format
        logger.info("Step 2: Creating wide format...")
        normalizer = XBRLNormalizer(self.config)
        wide = normalizer.to_wide_format(normalized)
        outputs["fundamentals_quarterly_wide"] = self._save_wide(wide)

        # Step 3: Calculate KPIs
        logger.info("Step 3: Calculating KPIs...")
        kpis = self._calculate_kpis(wide)
        outputs["kpis_quarterly"] = self._save_kpis(kpis)

        # Step 4: Run quality checks
        logger.info("Step 4: Running quality checks...")
        # Merge KPIs into wide for checking
        wide_with_kpis = wide.merge(
            kpis.pivot(
                index=["ticker", "fiscal_year", "fiscal_period"], columns="kpi_name", values="value"
            ).reset_index(),
            on=["ticker", "fiscal_year", "fiscal_period"],
            how="left",
        )
        quality_report = run_all_checks(wide_with_kpis)
        outputs["quality_report"] = self._save_quality_report(quality_report)

        # Step 5: Generate data dictionary
        logger.info("Step 5: Generating data dictionary...")
        outputs["data_dictionary"] = self._save_data_dictionary()

        logger.info("=" * 60)
        logger.info("Fundamentals Pipeline complete!")
        for name, path in outputs.items():
            logger.info(f"  {name}: {path}")
        logger.info("=" * 60)

        return outputs

    def _normalize_facts(self) -> pd.DataFrame:
        """Load and normalize raw facts."""
        raw_path = self.config.processed_dir / "fundamentals_raw_facts.parquet"

        if not raw_path.exists():
            raise FileNotFoundError(
                f"Raw facts not found at {raw_path}. Run 'make data' first to download SEC data."
            )

        raw_facts = pd.read_parquet(raw_path)
        logger.info(f"Loaded {len(raw_facts):,} raw facts")

        normalizer = XBRLNormalizer(self.config)
        normalized = normalizer.normalize(raw_facts)

        return normalized

    def _calculate_kpis(self, wide: pd.DataFrame) -> pd.DataFrame:
        """Calculate all KPIs from wide-format fundamentals."""
        records = []

        for _, row in wide.iterrows():
            kpis = calculate_all_kpis(row)

            for kpi_name, value in kpis.items():
                if pd.notna(value):
                    records.append(
                        {
                            "ticker": row["ticker"],
                            "fiscal_year": row["fiscal_year"],
                            "fiscal_period": row["fiscal_period"],
                            "date": row["date"],
                            "kpi_name": kpi_name,
                            "value": value,
                        }
                    )

        kpis_df = pd.DataFrame(records)

        # Add metadata from definitions
        def get_display_name(name):
            return KPI_DEFINITIONS.get(name, {}).display_name if name in KPI_DEFINITIONS else name

        def get_category(name):
            return KPI_DEFINITIONS.get(name, {}).category if name in KPI_DEFINITIONS else "other"

        def get_unit(name):
            return KPI_DEFINITIONS.get(name, {}).unit if name in KPI_DEFINITIONS else "unknown"

        kpis_df["display_name"] = kpis_df["kpi_name"].apply(
            lambda x: KPI_DEFINITIONS[x].display_name if x in KPI_DEFINITIONS else x
        )
        kpis_df["category"] = kpis_df["kpi_name"].apply(
            lambda x: KPI_DEFINITIONS[x].category if x in KPI_DEFINITIONS else "other"
        )
        kpis_df["unit"] = kpis_df["kpi_name"].apply(
            lambda x: KPI_DEFINITIONS[x].unit if x in KPI_DEFINITIONS else "unknown"
        )

        logger.info(f"Calculated {len(kpis_df):,} KPI observations")
        return kpis_df

    def _save_fundamentals(self, df: pd.DataFrame) -> Path:
        """Save normalized fundamentals."""
        path = self.config.processed_dir / "fundamentals_quarterly.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(df):,} rows to {path}")
        return path

    def _save_wide(self, df: pd.DataFrame) -> Path:
        """Save wide-format fundamentals."""
        path = self.config.processed_dir / "fundamentals_quarterly_wide.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(df):,} rows to {path}")
        return path

    def _save_kpis(self, df: pd.DataFrame) -> Path:
        """Save KPIs."""
        path = self.config.processed_dir / "kpis_quarterly.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Saved {len(df):,} rows to {path}")
        return path

    def _save_quality_report(self, report) -> Path:
        """Save quality report."""
        path = self.config.processed_dir / "quality_report.csv"
        report_df = report.to_dataframe()
        if len(report_df) > 0:
            report_df.to_csv(path, index=False)
        else:
            # Create empty file with headers
            pd.DataFrame(columns=["check_name", "severity", "ticker", "period", "message"]).to_csv(
                path, index=False
            )
        logger.info(f"Saved quality report to {path}: {report}")
        return path

    def _save_data_dictionary(self) -> Path:
        """Save data dictionary."""
        normalizer = XBRLNormalizer(self.config)
        data_dict = normalizer.get_data_dictionary()

        path = self.config.processed_dir / "data_dictionary.csv"
        data_dict.to_csv(path, index=False)
        logger.info(f"Saved data dictionary to {path}")
        return path


def run_fundamentals_pipeline(config: Config | None = None) -> dict[str, Path]:
    """Convenience function to run the fundamentals pipeline.

    Args:
        config: BankLab configuration

    Returns:
        Dictionary of output paths
    """
    pipeline = FundamentalsPipeline(config)
    return pipeline.run()
