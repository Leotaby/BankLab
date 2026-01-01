"""Build analysis-ready panel dataset for econometric modeling."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config

logger = logging.getLogger(__name__)


class ModelingDatasetBuilder:
    """
    Build panel dataset joining KPIs, market data, and macro variables.

    Output is quarterly panel suitable for Stata/R analysis.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        self.processed_dir = self.config.processed_dir

    def load_kpis(self) -> pd.DataFrame:
        """Load and reshape KPIs to wide format."""
        kpis = pd.read_parquet(self.processed_dir / "kpis_quarterly.parquet")

        # Pivot to wide
        kpi_wide = kpis.pivot_table(
            index=["ticker", "fiscal_year", "fiscal_period", "date"],
            columns="kpi_name",
            values="value",
            aggfunc="first",
        ).reset_index()

        return kpi_wide

    def load_fundamentals(self) -> pd.DataFrame:
        """Load fundamentals for control variables."""
        fund = pd.read_parquet(
            self.processed_dir / "fundamentals_quarterly_wide.parquet"
        )

        # Select control variables
        controls = ["ticker", "fiscal_year", "fiscal_period", "date"]
        if "total_assets" in fund.columns:
            fund["log_assets"] = np.log(fund["total_assets"].replace(0, np.nan))
            controls.append("log_assets")
        if "total_equity" in fund.columns and "total_assets" in fund.columns:
            fund["equity_ratio"] = fund["total_equity"] / fund["total_assets"]
            controls.append("equity_ratio")

        return fund[[c for c in controls if c in fund.columns]]

    def load_market_data(self) -> pd.DataFrame:
        """Load quarterly market returns and betas."""
        from banklab.market.returns import compute_returns, returns_to_quarterly

        prices = pd.read_parquet(self.processed_dir / "prices_daily.parquet")
        daily_ret = compute_returns(prices)
        returns = returns_to_quarterly(daily_ret)

        # Load rolling betas if available
        beta_path = self.processed_dir / "rolling_betas.parquet"
        if beta_path.exists():
            betas = pd.read_parquet(beta_path)
            # Get quarter-end betas
            betas["year"] = betas["date"].dt.year
            betas["quarter"] = betas["date"].dt.quarter
            betas_q = (
                betas.groupby(["ticker", "year", "quarter"])
                .last()
                .reset_index()[["ticker", "year", "quarter", "beta_mktrf", "r_squared"]]
            )
            returns = returns.merge(
                betas_q, on=["ticker", "year", "quarter"], how="left"
            )

        return returns

    def load_macro_data(self) -> pd.DataFrame:
        """Load and transform macro data to quarterly frequency."""
        macro = pd.read_parquet(self.processed_dir / "macro_monthly.parquet")

        # Pivot to wide
        macro_wide = macro.pivot_table(
            index=["year", "month"], columns="series_id", values="value", aggfunc="first"
        ).reset_index()

        # Compute derived variables
        if "DGS10" in macro_wide.columns and "DGS2" in macro_wide.columns:
            macro_wide["term_spread"] = macro_wide["DGS10"] - macro_wide["DGS2"]

        if "CPIAUCSL" in macro_wide.columns:
            macro_wide["cpi_yoy"] = macro_wide["CPIAUCSL"].pct_change(12) * 100

        if "GDPC1" in macro_wide.columns:
            # GDP is quarterly, forward fill
            macro_wide["gdp_growth"] = macro_wide["GDPC1"].pct_change(4) * 100

        # Aggregate to quarterly (end of quarter)
        macro_wide["quarter"] = (macro_wide["month"] - 1) // 3 + 1
        macro_q = macro_wide.groupby(["year", "quarter"]).last().reset_index()

        # Rename columns
        rename_map = {
            "DFF": "fed_funds",
            "UNRATE": "unemployment",
            "DGS10": "treasury_10y",
            "DGS2": "treasury_2y",
        }
        macro_q = macro_q.rename(columns=rename_map)

        # Select final columns
        macro_cols = [
            "year",
            "quarter",
            "fed_funds",
            "term_spread",
            "unemployment",
            "gdp_growth",
            "cpi_yoy",
        ]
        macro_q = macro_q[[c for c in macro_cols if c in macro_q.columns]]

        return macro_q

    def add_lags(
        self,
        df: pd.DataFrame,
        cols: list[str],
        lags: list[int] | None = None,
    ) -> pd.DataFrame:
        """Add lagged variables for specified columns."""
        if lags is None:
            lags = [1, 2]

        df = df.sort_values(["ticker", "fiscal_year", "fiscal_period"])

        for col in cols:
            if col not in df.columns:
                continue
            for lag in lags:
                lag_col = f"{col}_lag{lag}"
                df[lag_col] = df.groupby("ticker")[col].shift(lag)

        return df

    def build(self, output_path: Path | None = None) -> pd.DataFrame:
        """
        Build complete modeling dataset.

        Returns
        -------
        pd.DataFrame
            Panel dataset ready for econometric analysis
        """
        logger.info("Building modeling dataset...")

        # Load components
        kpis = self.load_kpis()
        logger.info(f"Loaded {len(kpis)} KPI observations")

        fundamentals = self.load_fundamentals()
        logger.info(f"Loaded {len(fundamentals)} fundamental observations")

        market = self.load_market_data()
        logger.info(f"Loaded {len(market)} market observations")

        macro = self.load_macro_data()
        logger.info(f"Loaded {len(macro)} macro observations")

        # Merge KPIs and fundamentals
        df = kpis.merge(
            fundamentals,
            on=["ticker", "fiscal_year", "fiscal_period", "date"],
            how="left",
        )

        # Derive year/quarter for merging
        df["year"] = df["fiscal_year"]
        df["quarter"] = (
            df["fiscal_period"].str.extract(r"Q(\d)").astype(float).squeeze()
        )
        # Handle FY periods
        df.loc[df["fiscal_period"] == "FY", "quarter"] = 4

        # Merge market data
        df = df.merge(market, on=["ticker", "year", "quarter"], how="left")

        # Merge macro data
        df = df.merge(macro, on=["year", "quarter"], how="left")

        # Add lagged macro variables
        macro_vars = [
            "fed_funds",
            "term_spread",
            "unemployment",
            "gdp_growth",
            "cpi_yoy",
        ]
        df = self.add_lags(df, [c for c in macro_vars if c in df.columns])

        # Add time fixed effects
        df["quarter_fe"] = df["quarter"].astype("Int64")
        df["year_fe"] = df["year"]

        # Bank indicator
        df["bank_id"] = df["ticker"].map({"JPM": 1, "MS": 2})

        # Sort and clean
        df = df.sort_values(["ticker", "year", "quarter"]).reset_index(drop=True)

        # Filter to valid observations
        df = df[df["quarter"].notna()]

        logger.info(f"Final dataset: {len(df)} observations")

        # Save
        if output_path is None:
            output_path = self.processed_dir / "modeling_dataset.parquet"

        df.to_parquet(output_path, index=False)
        logger.info(f"Saved to {output_path}")

        # Also save as CSV for Stata
        csv_path = output_path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV for Stata: {csv_path}")

        return df


def build_modeling_dataset(config: Config | None = None) -> pd.DataFrame:
    """Convenience function to build modeling dataset."""
    builder = ModelingDatasetBuilder(config)
    return builder.build()
