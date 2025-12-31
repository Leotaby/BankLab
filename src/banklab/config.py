"""Centralized configuration for BankLab."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """BankLab configuration."""

    # Target tickers for v1
    tickers: list[str] = field(default_factory=lambda: ["JPM", "MS"])

    # Data directories
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("BANKLAB_DATA_DIR", "data")))

    # SEC settings
    sec_user_agent: str = "BankLab Research (contact@example.com)"
    sec_rate_limit: float = 0.1  # seconds between requests (10 req/sec max)

    # FRED settings
    fred_api_key: str = field(default_factory=lambda: os.getenv("FRED_API_KEY", ""))
    fred_series: list[str] = field(
        default_factory=lambda: [
            "DFF",  # Federal Funds Rate
            "DGS10",  # 10-Year Treasury
            "DGS2",  # 2-Year Treasury
            "GDPC1",  # Real GDP
            "UNRATE",  # Unemployment Rate
            "CPIAUCSL",  # CPI
        ]
    )

    @property
    def raw_dir(self) -> Path:
        """Raw data directory."""
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        """Processed data directory."""
        return self.data_dir / "processed"

    @property
    def manifest_path(self) -> Path:
        """Data manifest file path."""
        return self.data_dir / "data_manifest.yml"

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist."""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)


# Global default config
DEFAULT_CONFIG = Config()
