# Manual Verification Checklist

This document provides a checklist for manually verifying BankLab's normalized financial data against official SEC filings.

## Purpose

Automated XBRL extraction can have edge cases. This checklist helps verify data quality by comparing key figures against the original 10-Q/10-K filings.

## Verification Process

### Step 1: Select Quarters to Verify

Choose 2 recent quarters for each bank:
- JPM: Q3 2024 and Q4 2023 (or most recent available)
- MS: Q3 2024 and Q4 2023 (or most recent available)

### Step 2: Locate Official Filings

1. Go to SEC EDGAR: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany
2. Search by ticker (JPM or MS)
3. Find the relevant 10-Q or 10-K filing
4. Open the filing and locate the financial statements

### Step 3: Compare Key Line Items

For each quarter, verify these items match within 0.1%:

#### Balance Sheet Items

| Line Item | BankLab Column | 10-Q Location | JPM Match? | MS Match? |
|-----------|----------------|---------------|------------|-----------|
| Total Assets | `total_assets` | Consolidated Balance Sheet | ☐ | ☐ |
| Total Liabilities | `total_liabilities` | Consolidated Balance Sheet | ☐ | ☐ |
| Total Equity | `total_equity` | Consolidated Balance Sheet | ☐ | ☐ |
| Total Deposits | `total_deposits` | Consolidated Balance Sheet | ☐ | ☐ |
| Loans, Net | `loans_net` | Consolidated Balance Sheet | ☐ | ☐ |

#### Income Statement Items

| Line Item | BankLab Column | 10-Q Location | JPM Match? | MS Match? |
|-----------|----------------|---------------|------------|-----------|
| Net Interest Income | `net_interest_income` | Consolidated Statement of Income | ☐ | ☐ |
| Non-Interest Income | `noninterest_income` | Consolidated Statement of Income | ☐ | ☐ |
| Non-Interest Expense | `noninterest_expense` | Consolidated Statement of Income | ☐ | ☐ |
| Net Income | `net_income` | Consolidated Statement of Income | ☐ | ☐ |

#### Per-Share Items

| Line Item | BankLab Column | 10-Q Location | JPM Match? | MS Match? |
|-----------|----------------|---------------|------------|-----------|
| Shares Outstanding | `shares_outstanding` | Notes or Cover Page | ☐ | ☐ |
| Basic EPS | Computed | EPS Note | ☐ | ☐ |

### Step 4: Verify KPI Calculations

Using the verified line items, manually calculate these KPIs:

| KPI | Formula | Expected | BankLab | Match? |
|-----|---------|----------|---------|--------|
| ROE (annualized) | (Net Income / Equity) × 4 | | | ☐ |
| ROA (annualized) | (Net Income / Assets) × 4 | | | ☐ |
| Equity/Assets | Equity / Assets | | | ☐ |
| Leverage | Assets / Equity | | | ☐ |

### Step 5: Document Discrepancies

For any mismatches > 1%, document:

1. **Item**: Which line item
2. **Period**: Fiscal year and period
3. **BankLab Value**: What we extracted
4. **Official Value**: What the filing shows
5. **Difference**: Absolute and percentage
6. **Root Cause**: (if identifiable)
   - Wrong XBRL tag used
   - Unit conversion issue
   - Period mismatch
   - Restatement not captured
   - Tag not reported by company

## Common Issues & Resolutions

### Issue: Missing Line Item

**Symptom**: Column has all NaN values for a ticker
**Likely Cause**: Company uses different XBRL tag
**Resolution**: Check raw facts for alternative tags, update mapping

### Issue: Value Off by Factor of 1000

**Symptom**: Values are 1000x too large or small
**Likely Cause**: Unit mismatch (thousands vs millions vs actual)
**Resolution**: Check unit field in raw facts, add unit conversion

### Issue: Different Value Than Filing

**Symptom**: Value doesn't match 10-Q exactly
**Likely Cause**: 
- Restatement in later filing
- Picked up 8-K instead of 10-Q
- Different fiscal period interpretation
**Resolution**: Check form type and filing date in raw facts

### Issue: Balance Sheet Doesn't Balance

**Symptom**: Assets ≠ Liabilities + Equity
**Likely Cause**: 
- Minority interest not included
- Different reporting entity scope
**Resolution**: Check for noncontrolling interest tags

## Verification Template

Copy this template for each verification session:

```
Verification Date: YYYY-MM-DD
Verified By: [Name]
Quarters Checked: Q_ 20__, Q_ 20__

JPM Results:
- Total Assets: ☐ Match / ☐ Discrepancy (notes: )
- Net Income: ☐ Match / ☐ Discrepancy (notes: )
- ROE Calculation: ☐ Match / ☐ Discrepancy (notes: )

MS Results:
- Total Assets: ☐ Match / ☐ Discrepancy (notes: )
- Net Income: ☐ Match / ☐ Discrepancy (notes: )
- ROE Calculation: ☐ Match / ☐ Discrepancy (notes: )

Overall Status: ☐ All Clear / ☐ Issues Found
Issues Logged: [Link to GitHub issues if any]
```

## Quarterly Verification Schedule

| Quarter | Target Verification Date | Verifier | Status |
|---------|--------------------------|----------|--------|
| Q4 2024 | After 10-K filing (~Feb) | TBD | Pending |
| Q1 2025 | After 10-Q filing (~May) | TBD | Pending |
| Q2 2025 | After 10-Q filing (~Aug) | TBD | Pending |
| Q3 2025 | After 10-Q filing (~Nov) | TBD | Pending |

## References

- JPM Investor Relations: https://www.jpmorganchase.com/ir
- MS Investor Relations: https://www.morganstanley.com/about-us-ir
- SEC EDGAR: https://www.sec.gov/edgar
- XBRL US: https://xbrl.us/
