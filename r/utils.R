# Utility functions for macro sensitivity analysis
# BankLab Phase 3

library(tidyverse)
library(fixest)
library(modelsummary)

#' Load modeling dataset
load_modeling_data <- function(path = "data/processed/modeling_dataset.parquet") {
  arrow::read_parquet(path) %>%
    mutate(
      ticker = as.factor(ticker),
      fiscal_period = as.factor(fiscal_period),
      quarter_fe = as.factor(quarter_fe)
    )
}

#' Standardize variables (z-score)
standardize <- function(x) {
  (x - mean(x, na.rm = TRUE)) / sd(x, na.rm = TRUE)
}

#' Format coefficient for display
format_coef <- function(coef, se, stars = TRUE) {
  pval <- 2 * pnorm(-abs(coef / se))
  star <- case_when(
    pval < 0.01 ~ "***",
    pval < 0.05 ~ "**",
    pval < 0.10 ~ "*",
    TRUE ~ ""
  )
  if (stars) {
    sprintf("%.3f%s\n(%.3f)", coef, star, se)
  } else {
    sprintf("%.3f\n(%.3f)", coef, se)
  }
}

#' Create coefficient plot
coef_plot <- function(models, coefs, title = "Coefficient Estimates") {
  modelplot(
    models,
    coef_map = coefs,
    conf_level = 0.95
  ) +
    geom_vline(xintercept = 0, linetype = "dashed", color = "gray50") +
    labs(title = title) +
    theme_minimal() +
    theme(legend.position = "bottom")
}

#' Summary statistics table
summary_stats <- function(df, vars) {
  df %>%
    select(all_of(vars)) %>%
    pivot_longer(everything(), names_to = "Variable", values_to = "Value") %>%
    group_by(Variable) %>%
    summarise(
      N = sum(!is.na(Value)),
      Mean = mean(Value, na.rm = TRUE),
      SD = sd(Value, na.rm = TRUE),
      Min = min(Value, na.rm = TRUE),
      Max = max(Value, na.rm = TRUE),
      .groups = "drop"
    )
}
