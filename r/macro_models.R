# Panel regression models for macro sensitivity analysis
# BankLab Phase 3
#
# Run from project root: Rscript r/macro_models.R

cat("============================================================\n")
cat("BankLab: Macro Sensitivity Analysis (R)\n")
cat("============================================================\n\n")

# Load packages
suppressPackageStartupMessages({
  library(tidyverse)
  library(fixest)
  library(modelsummary)
  library(arrow)
})

# Source utilities
source("r/utils.R")

# Load data
cat("Loading data...\n")
df <- load_modeling_data("data/processed/modeling_dataset.parquet")
cat(sprintf("Loaded %d observations\n\n", nrow(df)))

# ============================================================
# Model 1: ROE on Macro Variables (Baseline)
# ============================================================

cat("Estimating ROE models...\n")

# Baseline with entity and time FE
m1_roe <- feols(
  roe ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# With controls
m2_roe <- feols(
  roe ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 +
    log_assets + equity_ratio |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# ============================================================
# Model 2: NIM on Macro Variables
# ============================================================

cat("Estimating NIM models...\n")

m1_nim <- feols(
  nim ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

m2_nim <- feols(
  nim ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 +
    log_assets + equity_ratio |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# ============================================================
# Model 3: Efficiency Ratio
# ============================================================

cat("Estimating Efficiency Ratio model...\n")

m1_eff <- feols(
  efficiency_ratio ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# ============================================================
# Model 4: Stock Returns
# ============================================================

cat("Estimating Stock Return model...\n")

m1_ret <- feols(
  quarterly_return ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# ============================================================
# Robustness: Alternative Lags
# ============================================================

cat("Estimating robustness models...\n")

# Contemporaneous
m_roe_lag0 <- feols(
  roe ~ fed_funds + term_spread + unemployment + gdp_growth |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# Lag 2
m_roe_lag2 <- feols(
  roe ~ fed_funds_lag2 + term_spread_lag2 + unemployment_lag2 + gdp_growth_lag2 |
    ticker + quarter_fe,
  data = df,
  vcov = "NW"
)

# ============================================================
# Robustness: Subsamples
# ============================================================

# Pre-COVID
df_pre_covid <- df %>% filter(year < 2020)

m_roe_pre <- feols(
  roe ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 |
    ticker + quarter_fe,
  data = df_pre_covid,
  vcov = "NW"
)

# Post-2015
df_post2015 <- df %>% filter(year >= 2015)

m_roe_post15 <- feols(
  roe ~ fed_funds_lag1 + term_spread_lag1 + unemployment_lag1 + gdp_growth_lag1 |
    ticker + quarter_fe,
  data = df_post2015,
  vcov = "NW"
)

# ============================================================
# Export Results
# ============================================================

cat("\nSaving model objects...\n")

# Main table
models_main <- list(
  "ROE (1)" = m1_roe,
  "ROE (2)" = m2_roe,
  "NIM (1)" = m1_nim,
  "NIM (2)" = m2_nim,
  "Efficiency" = m1_eff,
  "Return" = m1_ret
)

# Robustness table
models_robust <- list(
  "Lag 0" = m_roe_lag0,
  "Lag 1" = m1_roe,
  "Lag 2" = m_roe_lag2,
  "Pre-COVID" = m_roe_pre,
  "Post-2015" = m_roe_post15
)

# Save models for Quarto
saveRDS(models_main, "data/processed/models_main.rds")
saveRDS(models_robust, "data/processed/models_robust.rds")

# Print summary
cat("\n============================================================\n")
cat("Main Results Summary\n")
cat("============================================================\n")
print(summary(m2_roe))

cat("\n============================================================\n")
cat("R models estimated and saved.\n")
cat("  - data/processed/models_main.rds\n")
cat("  - data/processed/models_robust.rds\n")
cat("============================================================\n")
