"""Market data loader for daily stock prices.

Uses Stooq as a free CSV source for daily OHLCV data.
"""

import io
import logging
from typing import Literal

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.utils.cache import CacheManager, DataManifest
from banklab.utils.http import PoliteRequester

logger = logging.getLogger(__name__)

# Stooq CSV endpoint
STOOQ_URL = "https://stooq.com/q/d/l/?s={ticker}.us&i=d"


class MarketLoader:
    """Load daily stock prices from Stooq.

    Features:
    - Free CSV download
    - Automatic return calculation
    - Caching with manifest tracking
    """

    def __init__(self, config: Config | None = None):
        """Initialize market loader.

        Args:
            config: BankLab configuration
        """
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()

        self.requester = PoliteRequester(
            user_agent="BankLab Research (contact@example.com)",
            rate_limit=0.5,  # Be polite to free services
        )
        self.manifest = DataManifest(self.config.manifest_path)
        self.cache = CacheManager(self.config.raw_dir / "market", self.manifest)

    def download_prices(
        self,
        ticker: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Download daily prices for a ticker.

        Args:
            ticker: Stock ticker (e.g., 'JPM')
            force_refresh: If True, re-download even if cached

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume
        """
        ticker_lower = ticker.lower()
        cache_key = f"prices_{ticker_lower}.csv"

        # Check cache
        if not force_refresh:
            cached = self.cache.load_text(cache_key)
            if cached:
                logger.info(f"Loading cached prices for {ticker}")
                return self._parse_stooq_csv(cached, ticker)

        # Download fresh
        url = STOOQ_URL.format(ticker=ticker_lower)
        logger.info(f"Downloading prices for {ticker} from Stooq")

        csv_text = self.requester.get_text(url)

        # Cache the raw CSV
        self.cache.store(
            cache_key,
            csv_text,
            url,
            notes=f"Daily prices for {ticker}",
        )

        return self._parse_stooq_csv(csv_text, ticker)

    def _parse_stooq_csv(self, csv_text: str, ticker: str) -> pd.DataFrame:
        """Parse Stooq CSV format.

        Args:
            csv_text: Raw CSV content
            ticker: Ticker symbol for labeling

        Returns:
            Parsed DataFrame
        """
        df = pd.read_csv(io.StringIO(csv_text))

        # Standardize column names
        df.columns = [c.lower() for c in df.columns]

        # Parse date
        df["date"] = pd.to_datetime(df["date"])

        # Add ticker column
        df["ticker"] = ticker.upper()

        # Sort by date ascending
        df = df.sort_values("date").reset_index(drop=True)

        logger.info(f"Parsed {len(df)} price records for {ticker}")
        return df

    def compute_returns(
        self,
        prices_df: pd.DataFrame,
        price_col: str = "close",
        method: Literal["simple", "log"] = "simple",
    ) -> pd.DataFrame:
        """Compute returns from prices.

        Args:
            prices_df: DataFrame with date, ticker, and price columns
            price_col: Column to compute returns from
            method: 'simple' for arithmetic returns, 'log' for log returns

        Returns:
            DataFrame with added 'ret' column
        """
        df = prices_df.copy()

        # Compute returns per ticker
        if method == "log":
            import numpy as np

            df["ret"] = df.groupby("ticker")[price_col].transform(lambda x: np.log(x / x.shift(1)))
        else:
            df["ret"] = df.groupby("ticker")[price_col].transform(lambda x: x.pct_change())

        return df

    def load_all_tickers(
        self,
        tickers: list[str] | None = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Load and combine prices for multiple tickers.

        Args:
            tickers: List of tickers (defaults to config.tickers)
            force_refresh: If True, re-download all

        Returns:
            Combined DataFrame with daily prices and returns
        """
        tickers = tickers or self.config.tickers

        dfs = []
        for ticker in tickers:
            df = self.download_prices(ticker, force_refresh=force_refresh)
            df = self.compute_returns(df)
            dfs.append(df)

        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)

        logger.info(f"Loaded {len(combined)} total price records for {len(tickers)} tickers")
        return combined

    def to_parquet_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert to final parquet schema.

        Args:
            df: Raw prices DataFrame

        Returns:
            DataFrame with schema: date, ticker, close, ret
        """
        output = df[["date", "ticker", "close", "ret"]].copy()
        output["date"] = pd.to_datetime(output["date"]).dt.date
        return output
