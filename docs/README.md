# BankLab Documentation

## Data Sources

### SEC EDGAR

- **Ticker to CIK Mapping**: `https://www.sec.gov/files/company_tickers.json`
- **Filing Submissions**: `https://data.sec.gov/submissions/CIK##########.json`
- **Company Facts (XBRL)**: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

SEC EDGAR requires:
- Proper User-Agent header with contact information
- Rate limiting to max 10 requests/second
- See: https://www.sec.gov/os/accessing-edgar-data

### Market Data (Stooq)

Free daily OHLCV data:
- `https://stooq.com/q/d/l/?s={ticker}.us&i=d`

### Fama-French Factors

Daily 5-factor model data from Ken French's data library:
- `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip`

### FRED Macro Data

Federal Reserve Economic Data (requires free API key):
- `https://api.stlouisfed.org/fred/series/observations`
- Get API key: https://fred.stlouisfed.org/docs/api/api_key.html

## Output Schemas

All outputs are saved as parquet files in `data/processed/`.

### prices_daily.parquet

| Column | Type | Description |
|--------|------|-------------|
| date | date | Trading date |
| ticker | string | Stock ticker |
| close | float64 | Adjusted close price |
| ret | float64 | Simple daily return |

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
| date | date | End of month |
| series_id | string | FRED series ID |
| value | float64 | Observation value |

### fundamentals_raw_facts.parquet

| Column | Type | Description |
|--------|------|-------------|
| date | date | Period end date |
| cik | string | SEC CIK identifier |
| ticker | string | Stock ticker |
| tag | string | XBRL tag (taxonomy:tag) |
| value | float64 | Reported value |
| unit | string | Unit of measure |
| fp | string | Fiscal period |
| fy | int64 | Fiscal year |
| form | string | Filing form type |

## API Reference

See module docstrings for detailed API documentation:

```python
from banklab.ingest import SECLoader, MarketLoader, FactorsLoader, MacroLoader
from banklab.process import DataPipeline

# Example usage
loader = SECLoader()
facts = loader.get_company_facts("JPM")
```
