/*==============================================================================
    01_data_prep.do
    Load and prepare data for analysis
==============================================================================*/

di "Loading modeling dataset..."

* Import CSV (Stata can't read parquet directly without plugins)
import delimited "$DATA/modeling_dataset.csv", clear

* Convert string dates
gen date_stata = date(date, "YMD")
format date_stata %td

* Create panel identifiers
encode ticker, gen(bank_id)
gen time_id = yq(fiscal_year, quarter)
format time_id %tq

* Declare panel
xtset bank_id time_id

* Label variables
label variable roe "Return on Equity"
label variable roa "Return on Assets"
label variable nim "Net Interest Margin"
label variable efficiency_ratio "Efficiency Ratio"
label variable fed_funds_lag1 "Fed Funds Rate (t-1)"
label variable term_spread_lag1 "Term Spread (t-1)"
label variable unemployment_lag1 "Unemployment Rate (t-1)"
label variable gdp_growth_lag1 "GDP Growth (t-1)"
label variable log_assets "Log(Total Assets)"
label variable equity_ratio "Equity / Assets"

* Summary statistics
summarize roe roa nim efficiency_ratio ///
    fed_funds_lag1 term_spread_lag1 unemployment_lag1 gdp_growth_lag1 ///
    log_assets equity_ratio

* Save prepared data
save "$DATA/modeling_dataset_stata.dta", replace

di "Data preparation complete. N = `c(N)' observations."
