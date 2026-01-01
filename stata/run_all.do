/*==============================================================================
    BankLab: Macro Sensitivity Analysis
    Master Do-File
    
    Author: Hatef Tabbakhian
    Date: 2025
    
    This file runs all Stata analyses and exports LaTeX tables.
    Run from project root: stata -b do stata/run_all.do
==============================================================================*/

clear all
set more off
set matsize 10000

* Set paths
global PROJECT_ROOT "."
global DATA "$PROJECT_ROOT/data/processed"
global EXHIBITS "$PROJECT_ROOT/reports/exhibits"

* Create exhibits directory if needed
capture mkdir "$EXHIBITS"

* Log file
log using "$PROJECT_ROOT/stata/run_all.log", replace

di "============================================================"
di "BankLab Stata Analysis"
di "Started: $S_DATE $S_TIME"
di "============================================================"

* Run component do-files
do "$PROJECT_ROOT/stata/01_data_prep.do"
do "$PROJECT_ROOT/stata/02_panel_regs.do"
do "$PROJECT_ROOT/stata/03_robustness.do"

di "============================================================"
di "Analysis Complete: $S_DATE $S_TIME"
di "============================================================"

log close
