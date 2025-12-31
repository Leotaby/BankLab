"""Fama-French factor data loader."""

import io
import logging
import zipfile

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config
from banklab.utils.cache import CacheManager, DataManifest
from banklab.utils.http import PoliteRequester

logger = logging.getLogger(__name__)

FF_5_FACTORS_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
)


class FactorsLoader:
    def __init__(self, config: Config | None = None):
        self.config = config or DEFAULT_CONFIG
        self.config.ensure_dirs()
        self.requester = PoliteRequester(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            rate_limit=1.0,
        )
        self.requester.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        self.manifest = DataManifest(self.config.manifest_path)
        self.cache = CacheManager(self.config.raw_dir / "factors", self.manifest)

    def download_factors(self, force_refresh: bool = False) -> pd.DataFrame:
        cache_key = "ff5_daily.zip"
        if not force_refresh:
            cached = self.cache.load_bytes(cache_key)
            if cached:
                logger.info("Loading cached Fama-French factors")
                return self._parse_ff_zip(cached)
        logger.info("Downloading Fama-French 5-factor data")
        zip_bytes = self.requester.get_bytes(FF_5_FACTORS_URL)
        self.cache.store(
            cache_key, zip_bytes, FF_5_FACTORS_URL, notes="Fama-French daily 5-factor model"
        )
        return self._parse_ff_zip(zip_bytes)

    def _parse_ff_zip(self, zip_bytes: bytes) -> pd.DataFrame:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Find CSV file (case-insensitive)
            csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_files:
                # List what's actually in the zip for debugging
                logger.error(f"No CSV found in ZIP. Contents: {zf.namelist()}")
                raise ValueError(f"No CSV file found in ZIP. Contents: {zf.namelist()}")
            csv_name = csv_files[0]
            logger.info(f"Parsing {csv_name}")
            csv_bytes = zf.read(csv_name)

        csv_text = csv_bytes.decode("utf-8")
        lines = csv_text.split("\n")

        # Find where data starts (line starting with 8 digits = date)
        data_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and len(stripped) >= 8:
                # Check if first 8 chars are digits (YYYYMMDD format)
                first_part = stripped.split(",")[0].strip()
                if first_part.isdigit() and len(first_part) == 8:
                    data_start = i
                    break

        logger.info(f"Data starts at line {data_start}")

        df = pd.read_csv(
            io.StringIO("\n".join(lines[data_start:])),
            header=None,
            names=["date", "mktrf", "smb", "hml", "rmw", "cma", "rf"],
            on_bad_lines="skip",
        )

        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["date"])

        for col in ["mktrf", "smb", "hml", "rmw", "cma", "rf"]:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100

        df = df.sort_values("date").reset_index(drop=True)
        logger.info(f"Parsed {len(df)} daily factor observations")
        return df

    def to_parquet_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        output = df[["date", "mktrf", "smb", "hml", "rmw", "cma", "rf"]].copy()
        output["date"] = pd.to_datetime(output["date"]).dt.date
        return output
