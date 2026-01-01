"""Market analytics pipeline orchestrator."""

import logging
from pathlib import Path

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.market.factors import (
    estimate_capm,
    estimate_ff5,
    estimate_rolling_betas,
    factor_results_to_dataframe,
)
from banklab.market.returns import (
    compute_drawdowns,
    compute_max_drawdown,
    compute_return_metrics,
    compute_returns,
    compute_rolling_volatility,
    returns_to_quarterly,
)

logger = logging.getLogger(__name__)


class MarketPipeline:
    """Run all market analytics and save outputs."""

    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        self.processed_dir = self.config.processed_dir

    def run(self) -> dict[str, Path]:
        """
        Run complete market analytics pipeline.

        Returns
        -------
        dict[str, Path]
            Mapping of output names to file paths
        """
        logger.info("=" * 60)
        logger.info("Starting Market Analytics Pipeline")
        logger.info("=" * 60)

        outputs = {}

        # Load data
        prices = pd.read_parquet(self.processed_dir / "prices_daily.parquet")
        factors = pd.read_parquet(self.processed_dir / "factors_daily.parquet")

        logger.info(f"Loaded {len(prices)} price records")
        logger.info(f"Loaded {len(factors)} factor records")

        # Step 1: Compute returns
        logger.info("Step 1: Computing returns...")
        returns = compute_returns(prices)
        returns = compute_rolling_volatility(returns)
        returns = compute_drawdowns(returns)

        output_path = self.processed_dir / "returns_daily.parquet"
        returns.to_parquet(output_path, index=False)
        outputs["returns_daily"] = output_path
        logger.info(f"Saved {len(returns)} rows to {output_path}")

        # Step 2: Quarterly returns
        logger.info("Step 2: Computing quarterly returns...")
        returns_q = returns_to_quarterly(returns)

        output_path = self.processed_dir / "returns_quarterly.parquet"
        returns_q.to_parquet(output_path, index=False)
        outputs["returns_quarterly"] = output_path
        logger.info(f"Saved {len(returns_q)} rows to {output_path}")

        # Step 3: Return metrics
        logger.info("Step 3: Computing return metrics...")
        rf_data = factors[["date", "rf"]].copy()
        metrics = compute_return_metrics(returns, rf_data)
        metrics_df = pd.DataFrame([vars(m) for m in metrics])

        output_path = self.processed_dir / "return_metrics.parquet"
        metrics_df.to_parquet(output_path, index=False)
        outputs["return_metrics"] = output_path
        logger.info(f"Saved {len(metrics_df)} rows to {output_path}")

        # Step 4: Max drawdowns
        logger.info("Step 4: Computing max drawdowns...")
        max_dd = compute_max_drawdown(returns)

        output_path = self.processed_dir / "max_drawdowns.parquet"
        max_dd.to_parquet(output_path, index=False)
        outputs["max_drawdowns"] = output_path
        logger.info(f"Saved {len(max_dd)} rows to {output_path}")

        # Step 5: Factor models
        logger.info("Step 5: Estimating factor models...")
        capm_results = estimate_capm(returns, factors)
        ff5_results = estimate_ff5(returns, factors)

        all_factor_results = capm_results + ff5_results
        factor_df = factor_results_to_dataframe(all_factor_results)

        output_path = self.processed_dir / "factor_exposures.parquet"
        factor_df.to_parquet(output_path, index=False)
        outputs["factor_exposures"] = output_path
        logger.info(f"Saved {len(factor_df)} factor model results to {output_path}")

        # Step 6: Rolling betas
        logger.info("Step 6: Computing rolling betas...")
        rolling_betas = estimate_rolling_betas(returns, factors, window=252)

        output_path = self.processed_dir / "rolling_betas.parquet"
        rolling_betas.to_parquet(output_path, index=False)
        outputs["rolling_betas"] = output_path
        logger.info(f"Saved {len(rolling_betas)} rolling beta observations to {output_path}")

        logger.info("=" * 60)
        logger.info("Market Analytics Pipeline complete!")
        for name, path in outputs.items():
            logger.info(f"  {name}: {path}")
        logger.info("=" * 60)

        return outputs


def run_market_pipeline(config: Config | None = None) -> dict[str, Path]:
    """Convenience function to run market pipeline."""
    pipeline = MarketPipeline(config)
    return pipeline.run()
