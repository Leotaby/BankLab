/*==============================================================================
    03_robustness.do
    Robustness checks and diagnostics
==============================================================================*/

use "$DATA/modeling_dataset_stata.dta", clear

di "============================================================"
di "Robustness Checks"
di "============================================================"

* -----------------------------------------------------------------------------
* Alternative Lag Specifications
* -----------------------------------------------------------------------------

* Contemporaneous (Lag 0)
xtreg roe fed_funds term_spread unemployment gdp_growth ///
    i.quarter_fe, fe vce(robust)
estimates store m_lag0

* Lag 1 (baseline)
xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m_lag1

* Lag 2
xtreg roe fed_funds_lag2 term_spread_lag2 unemployment_lag2 gdp_growth_lag2 ///
    i.quarter_fe, fe vce(robust)
estimates store m_lag2

* -----------------------------------------------------------------------------
* Subsample Analysis
* -----------------------------------------------------------------------------

* Pre-COVID (before 2020)
preserve
keep if fiscal_year < 2020
xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m_precovid
restore

* Post-2015
preserve
keep if fiscal_year >= 2015
xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, fe vce(robust)
estimates store m_post2015
restore

* -----------------------------------------------------------------------------
* HAC Standard Errors (Panel-Corrected)
* -----------------------------------------------------------------------------

xtpcse roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    i.quarter_fe, correlation(ar1) hetonly
estimates store m_pcse

* -----------------------------------------------------------------------------
* Export Robustness Table
* -----------------------------------------------------------------------------

esttab m_lag0 m_lag1 m_lag2 m_precovid m_post2015 ///
    using "$EXHIBITS/table_robustness.tex", replace ///
    label booktabs ///
    title("Robustness Checks: ROE Models") ///
    mtitles("Lag 0" "Lag 1" "Lag 2" "Pre-COVID" "Post-2015") ///
    keep(fed_funds* term_spread* unemployment* gdp_growth*) ///
    stats(N r2_w, labels("Observations" "Within R²") fmt(%9.0fc %9.3f)) ///
    star(* 0.10 ** 0.05 *** 0.01) ///
    se(%9.3f) b(%9.3f) ///
    addnotes("Robust standard errors in parentheses." ///
             "Bank and quarter fixed effects included.")

* -----------------------------------------------------------------------------
* Diagnostic Tests
* -----------------------------------------------------------------------------

di "============================================================"
di "Diagnostic Tests"
di "============================================================"

* Hausman Test (FE vs RE)
quietly xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1, fe
estimates store fe_model
quietly xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1, re
estimates store re_model
hausman fe_model re_model

* Wooldridge test for serial correlation
xtserial roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1

* Modified Wald test for groupwise heteroskedasticity
quietly xtreg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1, fe
xttest3

* VIF (run OLS for VIF)
quietly reg roe fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1
vif

* Export diagnostics summary
file open diagfile using "$EXHIBITS/diagnostics.txt", write replace
file write diagfile "Diagnostic Tests for ROE Model" _n
file write diagfile "===============================" _n _n
file write diagfile "See Stata log for full output." _n
file write diagfile "Tests performed:" _n
file write diagfile "  - Hausman test (FE vs RE)" _n
file write diagfile "  - Wooldridge serial correlation test" _n
file write diagfile "  - Modified Wald heteroskedasticity test" _n
file write diagfile "  - VIF for multicollinearity" _n
file close diagfile

di "Robustness checks complete."
