"""Factor model estimation: CAPM, Fama-French 5, rolling betas."""

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class FactorModelResult:
    """Results from a factor model regression."""

    ticker: str
    model: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    n_obs: int
    alpha: float
    alpha_tstat: float
    alpha_pval: float
    r_squared: float
    adj_r_squared: float
    betas: dict[str, float]
    beta_tstats: dict[str, float]
    residual_vol: float


def estimate_capm(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
    min_obs: int = 60,
) -> list[FactorModelResult]:
    """
    Estimate CAPM for each ticker.

    Parameters
    ----------
    returns : pd.DataFrame
        Columns: ticker, date, return
    factors : pd.DataFrame
        Columns: date, mktrf, rf
    min_obs : int
        Minimum observations required

    Returns
    -------
    list[FactorModelResult]
    """
    results = []

    for ticker in returns["ticker"].unique():
        ticker_ret = returns[returns["ticker"] == ticker][["date", "return"]]
        merged = ticker_ret.merge(factors[["date", "mktrf", "rf"]], on="date")
        merged = merged.dropna()

        if len(merged) < min_obs:
            logger.warning(f"CAPM: {ticker} has only {len(merged)} obs, skipping")
            continue

        # Excess returns
        y = merged["return"].values - merged["rf"].values
        X = np.column_stack([np.ones(len(merged)), merged["mktrf"].values])

        # OLS
        beta_hat, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        y_hat = X @ beta_hat
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        adj_r2 = 1 - (1 - r2) * (len(y) - 1) / (len(y) - 2)

        # Standard errors (OLS)
        mse = ss_res / (len(y) - 2)
        var_beta = mse * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(var_beta))

        alpha, beta_mkt = beta_hat
        t_alpha = alpha / se[0] if se[0] > 0 else 0
        t_beta = beta_mkt / se[1] if se[1] > 0 else 0

        results.append(
            FactorModelResult(
                ticker=ticker,
                model="CAPM",
                period_start=merged["date"].min(),
                period_end=merged["date"].max(),
                n_obs=len(merged),
                alpha=alpha * 252,  # Annualized
                alpha_tstat=t_alpha,
                alpha_pval=2 * (1 - stats.t.cdf(abs(t_alpha), len(y) - 2)),
                r_squared=r2,
                adj_r_squared=adj_r2,
                betas={"mktrf": beta_mkt},
                beta_tstats={"mktrf": t_beta},
                residual_vol=np.sqrt(mse) * np.sqrt(252),
            )
        )

    return results


def estimate_ff5(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
    min_obs: int = 60,
) -> list[FactorModelResult]:
    """
    Estimate Fama-French 5-factor model for each ticker.

    Parameters
    ----------
    returns : pd.DataFrame
        Columns: ticker, date, return
    factors : pd.DataFrame
        Columns: date, mktrf, smb, hml, rmw, cma, rf

    Returns
    -------
    list[FactorModelResult]
    """
    factor_cols = ["mktrf", "smb", "hml", "rmw", "cma"]
    results = []

    for ticker in returns["ticker"].unique():
        ticker_ret = returns[returns["ticker"] == ticker][["date", "return"]]
        merged = ticker_ret.merge(factors, on="date")
        merged = merged.dropna()

        if len(merged) < min_obs:
            logger.warning(f"FF5: {ticker} has only {len(merged)} obs, skipping")
            continue

        # Excess returns
        y = merged["return"].values - merged["rf"].values
        X = np.column_stack([np.ones(len(merged))] + [merged[f].values for f in factor_cols])

        # OLS
        beta_hat, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        y_hat = X @ beta_hat
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        k = len(factor_cols) + 1
        adj_r2 = 1 - (1 - r2) * (len(y) - 1) / (len(y) - k)

        # Standard errors
        mse = ss_res / (len(y) - k)
        var_beta = mse * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(var_beta))

        alpha = beta_hat[0]
        t_alpha = alpha / se[0] if se[0] > 0 else 0

        betas = {f: beta_hat[i + 1] for i, f in enumerate(factor_cols)}
        t_stats = {
            f: beta_hat[i + 1] / se[i + 1] if se[i + 1] > 0 else 0
            for i, f in enumerate(factor_cols)
        }

        results.append(
            FactorModelResult(
                ticker=ticker,
                model="FF5",
                period_start=merged["date"].min(),
                period_end=merged["date"].max(),
                n_obs=len(merged),
                alpha=alpha * 252,
                alpha_tstat=t_alpha,
                alpha_pval=2 * (1 - stats.t.cdf(abs(t_alpha), len(y) - k)),
                r_squared=r2,
                adj_r_squared=adj_r2,
                betas=betas,
                beta_tstats=t_stats,
                residual_vol=np.sqrt(mse) * np.sqrt(252),
            )
        )

    return results


def estimate_rolling_betas(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
    window: int = 252,
    min_obs: int = 126,
    model: Literal["CAPM", "FF5"] = "CAPM",
) -> pd.DataFrame:
    """
    Estimate rolling factor betas.

    Parameters
    ----------
    returns : pd.DataFrame
        Columns: ticker, date, return
    factors : pd.DataFrame
        Factor data
    window : int
        Rolling window in trading days
    min_obs : int
        Minimum observations in window
    model : str
        'CAPM' or 'FF5'

    Returns
    -------
    pd.DataFrame
        Columns: ticker, date, beta_mktrf, [beta_smb, ...], r_squared
    """
    if model == "CAPM":
        factor_cols = ["mktrf"]
    else:
        factor_cols = ["mktrf", "smb", "hml", "rmw", "cma"]

    results = []

    for ticker in returns["ticker"].unique():
        ticker_ret = returns[returns["ticker"] == ticker][["date", "return"]]
        merged = ticker_ret.merge(factors, on="date").sort_values("date")
        merged = merged.dropna()

        if len(merged) < window:
            logger.warning(f"Rolling betas: {ticker} has insufficient data")
            continue

        for i in range(window, len(merged) + 1):
            window_data = merged.iloc[i - window : i]

            if len(window_data) < min_obs:
                continue

            y = window_data["return"].values - window_data["rf"].values
            X = np.column_stack(
                [np.ones(len(window_data))] + [window_data[f].values for f in factor_cols]
            )

            try:
                beta_hat, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                y_hat = X @ beta_hat
                ss_res = np.sum((y - y_hat) ** 2)
                ss_tot = np.sum((y - y.mean()) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

                row = {
                    "ticker": ticker,
                    "date": window_data["date"].iloc[-1],
                    "r_squared": r2,
                }
                for j, f in enumerate(factor_cols):
                    row[f"beta_{f}"] = beta_hat[j + 1]

                results.append(row)
            except Exception as e:
                logger.warning(f"Rolling beta error at {window_data['date'].iloc[-1]}: {e}")
                continue

    return pd.DataFrame(results)


def factor_results_to_dataframe(results: list[FactorModelResult]) -> pd.DataFrame:
    """Convert list of FactorModelResult to DataFrame."""
    records = []
    for r in results:
        row = {
            "ticker": r.ticker,
            "model": r.model,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "n_obs": r.n_obs,
            "alpha_ann": r.alpha,
            "alpha_tstat": r.alpha_tstat,
            "alpha_pval": r.alpha_pval,
            "r_squared": r.r_squared,
            "adj_r_squared": r.adj_r_squared,
            "residual_vol": r.residual_vol,
        }
        for factor, beta in r.betas.items():
            row[f"beta_{factor}"] = beta
        for factor, tstat in r.beta_tstats.items():
            row[f"tstat_{factor}"] = tstat
        records.append(row)
    return pd.DataFrame(records)
