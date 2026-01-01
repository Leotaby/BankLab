/*==============================================================================
    02_panel_regs.do
    Main panel regression analysis
==============================================================================*/

use "$DATA/modeling_dataset_stata.dta", clear

di "============================================================"
di "Main Panel Regressions"
di "============================================================"

* -----------------------------------------------------------------------------
* Model 1: ROE on Macro Variables
* -----------------------------------------------------------------------------

* Baseline with bank FE
xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m1_roe

* With controls
xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    log_assets equity_ratio i.quarter_fe, fe vce(robust)
estimates store m2_roe

* -----------------------------------------------------------------------------
* Model 2: NIM on Macro Variables
* -----------------------------------------------------------------------------

xtreg nim fed_funds_lag1 term_spread_lag1 unemployment_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m1_nim

xtreg nim fed_funds_lag1 term_spread_lag1 unemployment_lag1 ///
    log_assets equity_ratio i.quarter_fe, fe vce(robust)
estimates store m2_nim

* -----------------------------------------------------------------------------
* Model 3: Efficiency Ratio
* -----------------------------------------------------------------------------

xtreg efficiency_ratio fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m1_eff

* -----------------------------------------------------------------------------
* Model 4: Stock Returns
* -----------------------------------------------------------------------------

xtreg quarterly_return fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m1_ret

* -----------------------------------------------------------------------------
* Export Main Results Table
* -----------------------------------------------------------------------------

esttab m1_roe m2_roe m1_nim m2_nim m1_eff m1_ret ///
    using "$EXHIBITS/table_main_results.tex", replace ///
    label booktabs ///
    title("Macro Sensitivity of Bank KPIs") ///
    mtitles("ROE (1)" "ROE (2)" "NIM (1)" "NIM (2)" "Efficiency" "Return") ///
    keep(fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
         log_assets equity_ratio) ///
    stats(N r2_w r2_b, labels("Observations" "Within R²" "Between R²") fmt(%9.0fc %9.3f %9.3f)) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    se(%9.3f) b(%9.3f) ///
    addnotes("Robust standard errors in parentheses." ///
             "Bank and quarter fixed effects included.")

di "Main results exported to table_main_results.tex"
