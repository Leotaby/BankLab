"""Market analytics module."""

from banklab.market.returns import (
    compute_returns,
    compute_rolling_volatility,
    compute_drawdowns,
    compute_max_drawdown,
    compute_return_metrics,
    returns_to_monthly,
    returns_to_quarterly,
)
from banklab.market.factors import (
    estimate_capm,
    estimate_ff5,
    estimate_rolling_betas,
    factor_results_to_dataframe,
)

__all__ = [
    "compute_returns",
    "compute_rolling_volatility",
    "compute_drawdowns",
    "compute_max_drawdown",
    "compute_return_metrics",
    "returns_to_monthly",
    "returns_to_quarterly",
    "estimate_capm",
    "estimate_ff5",
    "estimate_rolling_betas",
    "factor_results_to_dataframe",
]
