"""Return calculations, volatility metrics, and drawdown analysis."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ReturnMetrics:
    """Container for return-based metrics."""

    ticker: str
    period_start: pd.Timestamp
    period_end: pd.Timestamp
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float


def compute_returns(
    prices: pd.DataFrame,
    price_col: str = "close",
    method: str = "log",
) -> pd.DataFrame:
    """
    Compute returns from price series.

    Parameters
    ----------
    prices : pd.DataFrame
        Must have columns: ticker, date, {price_col}
    price_col : str
        Column containing prices
    method : str
        'log' for log returns, 'simple' for arithmetic returns

    Returns
    -------
    pd.DataFrame
        Columns: ticker, date, price, return, cum_return
    """
    df = prices.copy()
    df = df.sort_values(["ticker", "date"])

    if method == "log":
        df["return"] = df.groupby("ticker")[price_col].transform(lambda x: np.log(x / x.shift(1)))
    else:
        df["return"] = df.groupby("ticker")[price_col].pct_change()

    # Cumulative returns
    df["cum_return"] = df.groupby("ticker")["return"].transform(
        lambda x: (1 + x.fillna(0)).cumprod() - 1
    )

    return df[["ticker", "date", price_col, "return", "cum_return"]].rename(
        columns={price_col: "price"}
    )


def compute_rolling_volatility(
    returns: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """
    Compute rolling annualized volatility.

    Parameters
    ----------
    returns : pd.DataFrame
        Must have columns: ticker, date, return
    windows : list[int]
        Rolling window sizes in trading days

    Returns
    -------
    pd.DataFrame
        Original data plus vol_{window}d columns
    """
    if windows is None:
        windows = [21, 63, 252]

    df = returns.copy()
    annualization = np.sqrt(252)

    for window in windows:
        col_name = f"vol_{window}d"
        w = window  # bind loop variable
        df[col_name] = df.groupby("ticker")["return"].transform(
            lambda x, w=w: x.rolling(w, min_periods=w // 2).std() * annualization
        )

    return df


def compute_drawdowns(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Compute drawdown series from returns.

    Parameters
    ----------
    returns : pd.DataFrame
        Must have columns: ticker, date, return

    Returns
    -------
    pd.DataFrame
        Original data plus: cum_wealth, running_max, drawdown
    """
    df = returns.copy()

    # Cumulative wealth (starting at 1)
    df["cum_wealth"] = df.groupby("ticker")["return"].transform(
        lambda x: (1 + x.fillna(0)).cumprod()
    )

    # Running maximum
    df["running_max"] = df.groupby("ticker")["cum_wealth"].transform(lambda x: x.cummax())

    # Drawdown as percentage from peak
    df["drawdown"] = (df["cum_wealth"] - df["running_max"]) / df["running_max"]

    return df


def compute_max_drawdown(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Compute maximum drawdown per ticker.

    Returns
    -------
    pd.DataFrame
        Columns: ticker, max_drawdown, drawdown_start, drawdown_trough, recovery_date
    """
    df = compute_drawdowns(returns)

    results = []
    for ticker in df["ticker"].unique():
        ticker_df = df[df["ticker"] == ticker].copy()
        max_dd = ticker_df["drawdown"].min()

        # Find drawdown period
        max_dd_idx = ticker_df["drawdown"].idxmin()
        max_dd_date = ticker_df.loc[max_dd_idx, "date"]

        # Find peak before drawdown
        pre_dd = ticker_df[ticker_df["date"] <= max_dd_date]
        peak_idx = pre_dd["cum_wealth"].idxmax()
        peak_date = ticker_df.loc[peak_idx, "date"]

        # Find recovery (if any)
        peak_value = ticker_df.loc[peak_idx, "cum_wealth"]
        post_dd = ticker_df[ticker_df["date"] > max_dd_date]
        recovery = post_dd[post_dd["cum_wealth"] >= peak_value]
        recovery_date = recovery["date"].iloc[0] if len(recovery) > 0 else None

        results.append(
            {
                "ticker": ticker,
                "max_drawdown": max_dd,
                "drawdown_start": peak_date,
                "drawdown_trough": max_dd_date,
                "recovery_date": recovery_date,
            }
        )

    return pd.DataFrame(results)


def compute_return_metrics(
    returns: pd.DataFrame,
    risk_free: pd.DataFrame | None = None,
) -> list[ReturnMetrics]:
    """
    Compute comprehensive return metrics per ticker.

    Parameters
    ----------
    returns : pd.DataFrame
        Must have columns: ticker, date, return
    risk_free : pd.DataFrame, optional
        Daily risk-free rate with columns: date, rf

    Returns
    -------
    list[ReturnMetrics]
        Metrics for each ticker
    """
    results = []

    for ticker in returns["ticker"].unique():
        ticker_df = returns[returns["ticker"] == ticker].copy()
        ticker_df = ticker_df.dropna(subset=["return"])

        if len(ticker_df) < 21:
            logger.warning(f"Insufficient data for {ticker}: {len(ticker_df)} obs")
            continue

        # Basic metrics
        total_ret = (1 + ticker_df["return"]).prod() - 1
        n_years = len(ticker_df) / 252
        ann_ret = (1 + total_ret) ** (1 / n_years) - 1 if n_years > 0 else 0
        ann_vol = ticker_df["return"].std() * np.sqrt(252)

        # Risk-adjusted
        if risk_free is not None:
            merged = ticker_df.merge(risk_free, on="date", how="left")
            excess_ret = merged["return"] - merged["rf"].fillna(0)
            avg_excess = excess_ret.mean() * 252
            sharpe = avg_excess / ann_vol if ann_vol > 0 else 0
        else:
            sharpe = ann_ret / ann_vol if ann_vol > 0 else 0

        # Drawdown
        dd_df = compute_drawdowns(ticker_df)
        max_dd = dd_df["drawdown"].min()
        calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0

        results.append(
            ReturnMetrics(
                ticker=ticker,
                period_start=ticker_df["date"].min(),
                period_end=ticker_df["date"].max(),
                total_return=total_ret,
                annualized_return=ann_ret,
                annualized_volatility=ann_vol,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                calmar_ratio=calmar,
            )
        )

    return results


def returns_to_monthly(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily returns to monthly.

    Returns
    -------
    pd.DataFrame
        Columns: ticker, year, month, monthly_return, monthly_vol
    """
    df = returns.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = (
        df.groupby(["ticker", "year", "month"])
        .agg(
            monthly_return=("return", lambda x: (1 + x).prod() - 1),
            monthly_vol=("return", lambda x: x.std() * np.sqrt(21)),
            n_obs=("return", "count"),
        )
        .reset_index()
    )

    return monthly


def returns_to_quarterly(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily returns to quarterly (to match fundamentals).

    Returns
    -------
    pd.DataFrame
        Columns: ticker, year, quarter, quarterly_return, quarterly_vol, n_obs
    """
    df = returns.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter

    quarterly = (
        df.groupby(["ticker", "year", "quarter"])
        .agg(
            quarterly_return=("return", lambda x: (1 + x).prod() - 1),
            quarterly_vol=("return", lambda x: x.std() * np.sqrt(63)),
            n_obs=("return", "count"),
        )
        .reset_index()
    )

    return quarterly
