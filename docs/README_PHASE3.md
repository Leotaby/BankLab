# BankLab Phase 3: Market Analytics & Macro Sensitivity

## Overview

Phase 3 adds:
1. **Market Analytics**: Returns, volatility, drawdowns, factor exposures
2. **Macro Sensitivity**: Panel econometrics linking bank KPIs to macro conditions

## Installation

### Python Dependencies
```bash
pip install -e ".[dev,analysis]"
```

### R Dependencies
```r
install.packages(c("tidyverse", "fixest", "modelsummary", "kableExtra", "arrow"))
```

### Stata
Stata must be installed separately. Required packages:
- `estout` (for `esttab`)
- `xtserial` (for serial correlation test)

Install in Stata:
```stata
ssc install estout
ssc install xtserial
```

## Usage

### Full Pipeline
```bash
make phase3
```

### Individual Steps

1. **Market Analytics** (Python):
```bash
make market
```
Outputs:
- `data/processed/returns_daily.parquet`
- `data/processed/returns_quarterly.parquet`
- `data/processed/factor_exposures.parquet`
- `data/processed/rolling_betas.parquet`

2. **Modeling Dataset**:
```bash
make modeling-data
```
Outputs:
- `data/processed/modeling_dataset.parquet`
- `data/processed/modeling_dataset.csv` (for Stata)

3. **R Models**:
```bash
make r-models
```
Outputs:
- `data/processed/models_main.rds`
- `data/processed/models_robust.rds`

4. **Stata Models** (run locally):
```bash
make stata-models
# Or manually:
cd stata && stata -b do run_all.do
```
Outputs:
- `reports/exhibits/table_main_results.tex`
- `reports/exhibits/table_robustness.tex`

5. **Reports**:
```bash
make reports-phase3
```
Outputs:
- `reports/market_analytics.html`
- `reports/macro_sensitivity.html`

## Econometric Design

### Dependent Variables
- ROE (Return on Equity)
- NIM (Net Interest Margin)
- Efficiency Ratio
- Quarterly Stock Return

### Macro Regressors
- Fed Funds Rate (monetary policy)
- Term Spread (yield curve slope)
- Unemployment (labor market)
- GDP Growth (economic activity)

### Model Specification
```
KPI_{i,t} = α_i + β'X_{t-1} + γ'Z_{i,t-1} + δ_q + ε_{i,t}
```
- α_i: Bank fixed effects
- X_{t-1}: Lagged macro variables
- Z_{i,t-1}: Controls (log assets, equity ratio)
- δ_q: Quarter fixed effects

### Robustness Checks
- Alternative lags (0, 1, 2 quarters)
- Subsamples (pre-COVID, post-2015)
- HAC standard errors (Newey-West)
- Diagnostic tests (Hausman, serial correlation, heteroskedasticity)

## Output Files

| File | Description |
|------|-------------|
| `returns_daily.parquet` | Daily returns with volatility and drawdowns |
| `returns_quarterly.parquet` | Quarterly aggregated returns |
| `factor_exposures.parquet` | CAPM and FF5 regression results |
| `rolling_betas.parquet` | Time-varying market betas |
| `modeling_dataset.parquet` | Panel dataset for econometrics |
| `models_main.rds` | R model objects (main results) |
| `models_robust.rds` | R model objects (robustness) |
| `table_main_results.tex` | Stata main results table |
| `table_robustness.tex` | Stata robustness table |

## Important Notes

### Causal Interpretation
Results are **descriptive correlations**, not causal estimates. Banks both respond to and influence macroeconomic conditions, creating endogeneity.

### Stata in CI
Stata cannot run in GitHub Actions. Run locally and commit outputs to `reports/exhibits/`.

## File Structure

```
src/banklab/
├── market/
│   ├── __init__.py
│   ├── returns.py
│   ├── factors.py
│   ├── event_study.py
│   └── pipeline.py
└── econometrics/
    ├── __init__.py
    └── modeling_dataset.py

r/
├── utils.R
└── macro_models.R

stata/
├── run_all.do
├── 01_data_prep.do
├── 02_panel_regs.do
└── 03_robustness.do

reports/
├── market_analytics.qmd
├── macro_sensitivity.qmd
└── exhibits/
    └── *.tex
```
