"""FRED macro data loader.

Downloads economic indicators from the Federal Reserve Economic Data API.
"""

import json
import logging

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.utils.cache import CacheManager, DataManifest
from banklab.utils.http import PoliteRequester

logger = logging.getLogger(__name__)

# FRED API endpoint
FRED_OBSERVATIONS_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id={series_id}&api_key={api_key}&file_type=json"
)


class MacroLoader:
    """Load macroeconomic data from FRED.

    Default series:
    - DFF: Federal Funds Rate (daily)
    - DGS10: 10-Year Treasury Yield (daily)
    - DGS2: 2-Year Treasury Yield (daily)
    - GDPC1: Real GDP (quarterly)
    - UNRATE: Unemployment Rate (monthly)
    - CPIAUCSL: Consumer Price Index (monthly)
    """

    def __init__(self, config: Config | None = None):
        """Initialize macro loader.

        Args:
            config: BankLab configuration

        Raises:
            ValueError: If FRED API key not configured
        """
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()

        if not self.config.fred_api_key:
            raise ValueError(
                "FRED_API_KEY environment variable not set. "
                "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
            )

        self.requester = PoliteRequester(
            user_agent="BankLab Research (contact@example.com)",
            rate_limit=0.5,  # FRED is generous but be polite
        )
        self.manifest = DataManifest(self.config.manifest_path)
        self.cache = CacheManager(self.config.raw_dir / "fred", self.manifest)

    def download_series(
        self,
        series_id: str,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Download a FRED series.

        Args:
            series_id: FRED series identifier (e.g., 'DFF')
            force_refresh: If True, re-download even if cached

        Returns:
            DataFrame with columns: date, value
        """
        cache_key = f"fred_{series_id}.json"

        # Check cache
        if not force_refresh:
            cached = self.cache.load_text(cache_key)
            if cached:
                logger.info(f"Loading cached FRED series {series_id}")
                return self._parse_fred_json(json.loads(cached), series_id)

        # Download fresh
        url = FRED_OBSERVATIONS_URL.format(
            series_id=series_id,
            api_key=self.config.fred_api_key,
        )
        logger.info(f"Downloading FRED series {series_id}")
        data = self.requester.get_json(url)

        # Cache the response
        self.cache.store(
            cache_key,
            json.dumps(data),
            # Don't include API key in manifest
            f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}",
            notes=f"FRED series {series_id}",
        )

        return self._parse_fred_json(data, series_id)

    def _parse_fred_json(self, data: dict, series_id: str) -> pd.DataFrame:
        """Parse FRED JSON response.

        Args:
            data: Raw JSON response
            series_id: Series identifier for labeling

        Returns:
            Parsed DataFrame
        """
        observations = data.get("observations", [])

        df = pd.DataFrame(observations)
        if df.empty:
            return pd.DataFrame(columns=["date", "series_id", "value"])

        # Parse date and value
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["series_id"] = series_id

        # Keep only valid observations
        df = df[["date", "series_id", "value"]].dropna()
        df = df.sort_values("date").reset_index(drop=True)

        logger.info(f"Parsed {len(df)} observations for {series_id}")
        return df

    def load_all_series(
        self,
        series_ids: list[str] | None = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Load and combine multiple FRED series.

        Args:
            series_ids: List of series IDs (defaults to config.fred_series)
            force_refresh: If True, re-download all

        Returns:
            Combined DataFrame in long format
        """
        series_ids = series_ids or self.config.fred_series

        dfs = []
        for series_id in series_ids:
            try:
                df = self.download_series(series_id, force_refresh=force_refresh)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to load FRED series {series_id}: {e}")

        if not dfs:
            return pd.DataFrame(columns=["date", "series_id", "value"])

        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.sort_values(["date", "series_id"]).reset_index(drop=True)

        logger.info(f"Loaded {len(combined)} total observations for {len(series_ids)} series")
        return combined

    def to_parquet_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert to final parquet schema (monthly aggregation).

        Args:
            df: Raw macro DataFrame

        Returns:
            DataFrame with schema: date, series_id, value (monthly)
        """
        output = df.copy()

        # Convert to end-of-month for consistency
        output["date"] = pd.to_datetime(output["date"]).dt.to_period("M").dt.to_timestamp("M")

        # Take last observation per month per series
        output = output.groupby(["date", "series_id"])["value"].last().reset_index()

        output["date"] = output["date"].dt.date
        return output
