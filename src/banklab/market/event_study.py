"""Event study methodology for earnings announcements."""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class EventStudyResult:
    """Results from an event study."""

    ticker: str
    event_date: pd.Timestamp
    event_type: str
    car_window: tuple[int, int]
    car: float
    car_tstat: float
    car_pval: float
    bhar: float
    n_estimation_days: int
    abnormal_returns: pd.DataFrame


def estimate_event_study(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
    event_dates: pd.DataFrame,
    estimation_window: tuple[int, int] = (-252, -21),
    event_window: tuple[int, int] = (-1, 1),
    model: str = "market",
) -> list[EventStudyResult]:
    """
    Conduct event study around specified dates.

    Parameters
    ----------
    returns : pd.DataFrame
        Columns: ticker, date, return
    factors : pd.DataFrame
        Columns: date, mktrf, rf
    event_dates : pd.DataFrame
        Columns: ticker, event_date, event_type
    estimation_window : tuple
        (start, end) relative to event, for estimating normal returns
    event_window : tuple
        (start, end) relative to event, for measuring abnormal returns
    model : str
        'market' for market model, 'mean' for mean-adjusted

    Returns
    -------
    list[EventStudyResult]
    """
    results = []

    for _, event in event_dates.iterrows():
        ticker = event["ticker"]
        event_date = pd.to_datetime(event["event_date"])
        event_type = event.get("event_type", "earnings")

        # Get ticker returns
        ticker_ret = returns[returns["ticker"] == ticker].copy()
        ticker_ret = ticker_ret.sort_values("date").reset_index(drop=True)

        # Find event date index
        event_idx = ticker_ret[ticker_ret["date"] == event_date].index
        if len(event_idx) == 0:
            # Find closest trading day
            ticker_ret["date_diff"] = abs(
                (ticker_ret["date"] - event_date).dt.total_seconds()
            )
            closest_idx = ticker_ret["date_diff"].idxmin()
            if ticker_ret.loc[closest_idx, "date_diff"] > 5 * 86400:  # 5 days
                logger.warning(f"No trading day near {event_date} for {ticker}")
                continue
            event_idx = closest_idx
        else:
            event_idx = event_idx[0]

        # Define windows
        est_start = event_idx + estimation_window[0]
        est_end = event_idx + estimation_window[1]
        evt_start = event_idx + event_window[0]
        evt_end = event_idx + event_window[1]

        if est_start < 0 or evt_end >= len(ticker_ret):
            logger.warning(f"Insufficient data for event {event_date} {ticker}")
            continue

        # Estimation period data
        est_data = ticker_ret.iloc[est_start : est_end + 1].merge(
            factors[["date", "mktrf", "rf"]], on="date"
        )

        if len(est_data) < 60:
            logger.warning(f"Insufficient estimation data for {ticker} {event_date}")
            continue

        # Estimate normal return model
        if model == "market":
            y_est = est_data["return"].values - est_data["rf"].values
            X_est = np.column_stack([np.ones(len(est_data)), est_data["mktrf"].values])
            beta_hat, _, _, _ = np.linalg.lstsq(X_est, y_est, rcond=None)
            residuals = y_est - X_est @ beta_hat
            sigma = residuals.std()
        else:  # mean-adjusted
            mean_ret = est_data["return"].mean()
            sigma = est_data["return"].std()
            beta_hat = None

        # Event window abnormal returns
        evt_data = ticker_ret.iloc[evt_start : evt_end + 1].merge(
            factors[["date", "mktrf", "rf"]], on="date"
        )

        if model == "market" and beta_hat is not None:
            X_evt = np.column_stack([np.ones(len(evt_data)), evt_data["mktrf"].values])
            expected_ret = X_evt @ beta_hat + evt_data["rf"].values
        else:
            expected_ret = mean_ret

        evt_data = evt_data.copy()
        evt_data["expected_return"] = expected_ret
        evt_data["abnormal_return"] = evt_data["return"] - evt_data["expected_return"]

        # CAR and BHAR
        car = evt_data["abnormal_return"].sum()
        bhar = (1 + evt_data["return"]).prod() - (
            1 + evt_data["expected_return"]
        ).prod()

        # CAR t-statistic (assuming independence)
        n_evt = len(evt_data)
        car_se = sigma * np.sqrt(n_evt) if sigma > 0 else 1
        car_tstat = car / car_se
        car_pval = 2 * (1 - stats.t.cdf(abs(car_tstat), len(est_data) - 2))

        results.append(
            EventStudyResult(
                ticker=ticker,
                event_date=event_date,
                event_type=event_type,
                car_window=event_window,
                car=car,
                car_tstat=car_tstat,
                car_pval=car_pval,
                bhar=bhar,
                n_estimation_days=len(est_data),
                abnormal_returns=evt_data[
                    ["date", "return", "expected_return", "abnormal_return"]
                ],
            )
        )

    return results


def aggregate_event_results(results: list[EventStudyResult]) -> pd.DataFrame:
    """
    Aggregate event study results across events.

    Returns summary statistics for CARs by ticker and overall.
    """
    records = []
    for r in results:
        records.append(
            {
                "ticker": r.ticker,
                "event_date": r.event_date,
                "event_type": r.event_type,
                "car": r.car,
                "car_tstat": r.car_tstat,
                "car_pval": r.car_pval,
                "bhar": r.bhar,
                "significant_5pct": r.car_pval < 0.05,
            }
        )
    return pd.DataFrame(records)


def compute_average_car(
    results: list[EventStudyResult],
    window: tuple[int, int] = (-1, 1),
) -> dict:
    """
    Compute average CAR and test statistics across events.

    Returns
    -------
    dict with keys: avg_car, se_car, t_stat, p_val, n_events
    """
    cars = [r.car for r in results if r.car_window == window]

    if len(cars) == 0:
        return {"avg_car": None, "n_events": 0}

    avg_car = np.mean(cars)
    se_car = np.std(cars, ddof=1) / np.sqrt(len(cars))
    t_stat = avg_car / se_car if se_car > 0 else 0
    p_val = 2 * (1 - stats.t.cdf(abs(t_stat), len(cars) - 1))

    return {
        "avg_car": avg_car,
        "se_car": se_car,
        "t_stat": t_stat,
        "p_val": p_val,
        "n_events": len(cars),
    }
