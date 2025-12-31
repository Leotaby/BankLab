"""SEC EDGAR data loader.

Handles:
- Ticker to CIK mapping
- Filing submissions metadata
- XBRL company facts
"""

import json
import logging
from typing import Any

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.utils.cache import CacheManager, DataManifest
from banklab.utils.http import PoliteRequester

logger = logging.getLogger(__name__)

# SEC EDGAR URLs
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


class SECLoader:
    """Load data from SEC EDGAR APIs.

    Implements polite access with rate limiting and caching.
    """

    def __init__(self, config: Config | None = None):
        """Initialize SEC loader.

        Args:
            config: BankLab configuration (uses default if not provided)
        """
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()

        self.requester = PoliteRequester(
            user_agent=self.config.sec_user_agent,
            rate_limit=self.config.sec_rate_limit,
        )
        self.manifest = DataManifest(self.config.manifest_path)
        self.cache = CacheManager(self.config.raw_dir / "sec", self.manifest)

        self._ticker_cik_map: dict[str, str] | None = None

    def get_ticker_cik_map(self) -> dict[str, str]:
        """Get mapping of tickers to CIK numbers.

        Returns:
            Dictionary mapping ticker symbols to zero-padded CIK strings
        """
        if self._ticker_cik_map is not None:
            return self._ticker_cik_map

        cache_key = "company_tickers.json"

        # Try cache first
        cached = self.cache.load_text(cache_key)
        if cached:
            data = json.loads(cached)
        else:
            # Download fresh
            logger.info("Downloading SEC ticker->CIK mapping")
            data = self.requester.get_json(SEC_TICKERS_URL)
            self.cache.store(
                cache_key,
                json.dumps(data),
                SEC_TICKERS_URL,
                notes="SEC ticker to CIK mapping",
            )

        # Parse into ticker -> CIK map (CIK zero-padded to 10 digits)
        self._ticker_cik_map = {
            entry["ticker"]: str(entry["cik_str"]).zfill(10) for entry in data.values()
        }
        logger.info(f"Loaded {len(self._ticker_cik_map)} ticker->CIK mappings")
        return self._ticker_cik_map

    def get_cik(self, ticker: str) -> str:
        """Get CIK for a ticker symbol.

        Args:
            ticker: Stock ticker (e.g., 'JPM')

        Returns:
            Zero-padded CIK string

        Raises:
            ValueError: If ticker not found
        """
        ticker_map = self.get_ticker_cik_map()
        ticker_upper = ticker.upper()
        if ticker_upper not in ticker_map:
            raise ValueError(f"Ticker '{ticker}' not found in SEC database")
        return ticker_map[ticker_upper]

    def get_submissions(self, ticker: str) -> dict[str, Any]:
        """Get filing submissions metadata for a company.

        Args:
            ticker: Stock ticker

        Returns:
            Submissions data including recent filings
        """
        cik = self.get_cik(ticker)
        cache_key = f"submissions_{ticker}_{cik}.json"

        cached = self.cache.load_text(cache_key)
        if cached:
            return json.loads(cached)

        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        logger.info(f"Downloading submissions for {ticker} (CIK: {cik})")
        data = self.requester.get_json(url)

        self.cache.store(
            cache_key,
            json.dumps(data),
            url,
            notes=f"Filing submissions for {ticker}",
        )
        return data

    def get_company_facts(self, ticker: str) -> dict[str, Any]:
        """Get XBRL company facts for a company.

        Args:
            ticker: Stock ticker

        Returns:
            Company facts data including all reported XBRL tags
        """
        cik = self.get_cik(ticker)
        cache_key = f"companyfacts_{ticker}_{cik}.json"

        cached = self.cache.load_text(cache_key)
        if cached:
            return json.loads(cached)

        url = SEC_COMPANY_FACTS_URL.format(cik=cik)
        logger.info(f"Downloading company facts for {ticker} (CIK: {cik})")
        data = self.requester.get_json(url)

        self.cache.store(
            cache_key,
            json.dumps(data),
            url,
            notes=f"XBRL company facts for {ticker}",
        )
        return data

    def extract_facts_to_df(self, ticker: str) -> pd.DataFrame:
        """Extract company facts into a flat DataFrame.

        Args:
            ticker: Stock ticker

        Returns:
            DataFrame with columns: date, cik, ticker, tag, value, unit, fp, fy, form
        """
        facts_data = self.get_company_facts(ticker)
        cik = self.get_cik(ticker)

        rows = []

        # Navigate the nested structure
        # facts_data['facts'][taxonomy][tag]['units'][unit] = list of observations
        for taxonomy, tags in facts_data.get("facts", {}).items():
            for tag, tag_data in tags.items():
                for unit, observations in tag_data.get("units", {}).items():
                    for obs in observations:
                        rows.append(
                            {
                                "date": obs.get("end") or obs.get("filed"),
                                "cik": cik,
                                "ticker": ticker.upper(),
                                "tag": f"{taxonomy}:{tag}",
                                "value": obs.get("val"),
                                "unit": unit,
                                "fp": obs.get("fp", ""),
                                "fy": obs.get("fy"),
                                "form": obs.get("form", ""),
                            }
                        )

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df.sort_values("date").reset_index(drop=True)

        logger.info(f"Extracted {len(df)} facts for {ticker}")
        return df

    def load_all_tickers(self, tickers: list[str] | None = None) -> pd.DataFrame:
        """Load and combine facts for multiple tickers.

        Args:
            tickers: List of tickers (defaults to config.tickers)

        Returns:
            Combined DataFrame of all company facts
        """
        tickers = tickers or self.config.tickers
        dfs = [self.extract_facts_to_df(ticker) for ticker in tickers]
        combined = pd.concat(dfs, ignore_index=True)
        logger.info(f"Loaded {len(combined)} total facts for {len(tickers)} tickers")
        return combined
