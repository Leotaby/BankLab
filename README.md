# BankLab: JPM vs Morgan Stanley Analytics Platform

[![CI](https://github.com/Leotaby/BankLab/actions/workflows/ci.yml/badge.svg)](https://github.com/Leotaby/BankLab/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A reproducible research platform for comparative analysis of JPMorgan Chase (JPM) and Morgan Stanley (MS) using public data sources.

## Overview

BankLab provides a clean, professional pipeline for:

- **Fundamentals**: SEC EDGAR XBRL company facts (10-K/10-Q filings)
- **Market Data**: Daily prices and returns from public sources
- **Factor Models**: Fama-French 5-factor daily returns
- **Macro Context**: FRED economic indicators

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Leotaby/BankLab.git
cd banklab
pip install -e ".[dev]"

# Set FRED API key (get free key at https://fred.stlouisfed.org/docs/api/api_key.html)
export FRED_API_KEY="your_key_here"

# Download and process all data
make data

# Run tests
make test

# Build full report
make report
```

## Data Sources

| Source | Description | Update Frequency |
|--------|-------------|------------------|
| SEC EDGAR | Company facts, filings metadata | Quarterly |
| Stooq | Daily stock prices | Daily |
| Fama-French | 5-factor model returns | Daily |
| FRED | Fed Funds Rate, Treasury yields, GDP | Various |

## Project Structure

```
banklab/
├── src/banklab/           # Main package
│   ├── ingest/            # Data downloaders
│   │   ├── sec.py         # SEC EDGAR API
│   │   ├── market.py      # Stock prices
│   │   ├── factors.py     # Fama-French factors
│   │   └── macro.py       # FRED macro series
│   ├── process/           # Data transformations
│   │   └── pipeline.py    # Processing pipeline
│   ├── utils/             # Shared utilities
│   │   ├── cache.py       # Caching + manifest
│   │   └── http.py        # Polite HTTP client
│   └── run.py             # CLI entry point
├── tests/                 # pytest test suite
├── data/
│   ├── raw/               # Cached downloads (gitignored)
│   └── processed/         # Output parquet files
├── notebooks/             # Jupyter analysis notebooks
├── docs/                  # Documentation
└── data_manifest.yml      # Data provenance log
```

## Output Schemas

### prices_daily.parquet
| Column | Type | Description |
|--------|------|-------------|
| date | date | Trading date |
| ticker | string | Stock ticker (JPM, MS) |
| close | float64 | Adjusted close price |
| ret | float64 | Daily return |

### factors_daily.parquet
| Column | Type | Description |
|--------|------|-------------|
| date | date | Trading date |
| mktrf | float64 | Market excess return |
| smb | float64 | Size factor |
| hml | float64 | Value factor |
| rmw | float64 | Profitability factor |
| cma | float64 | Investment factor |
| rf | float64 | Risk-free rate |

### macro_monthly.parquet
| Column | Type | Description |
|--------|------|-------------|
| date | date | Observation date |
| series_id | string | FRED series identifier |
| value | float64 | Observation value |

### fundamentals_raw_facts.parquet
| Column | Type | Description |
|--------|------|-------------|
| date | date | Filing/period end date |
| cik | string | SEC CIK identifier |
| ticker | string | Stock ticker |
| tag | string | XBRL taxonomy tag |
| value | float64 | Reported value |
| unit | string | Unit of measure |
| fp | string | Fiscal period (FY, Q1-Q4) |
| fy | int64 | Fiscal year |
| form | string | Filing form type |

## Makefile Commands

```bash
make data      # Download and process all data
make build     # Install package in dev mode
make test      # Run pytest suite
make lint      # Run ruff linter
make report    # Generate analysis report
make clean     # Remove cached data
make all       # Full pipeline: build → data → test → report
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FRED_API_KEY` | Yes | FRED API key for macro data |
| `BANKLAB_DATA_DIR` | No | Override default data directory |

### Rate Limiting

The SEC requires polite access with proper User-Agent headers. BankLab implements:
- 10 requests/second max to SEC EDGAR
- Exponential backoff on 429 responses
- Persistent caching to minimize repeated requests

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check src/ tests/

# Run tests with coverage
pytest --cov=banklab --cov-report=term-missing

# Format code
ruff format src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use this platform in research, please cite:

```bibtex
@software{banklab2025,
  author = {Leo Tabatabaei},
  title = {BankLab: JPM vs Morgan Stanley Analytics Platform},
  year = {2025},
  url = {https://github.com/Leotaby/BankLab}
}
```
