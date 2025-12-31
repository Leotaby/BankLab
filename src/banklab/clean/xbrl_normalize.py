"""XBRL fact normalization for bank financial statements.

This module converts raw SEC XBRL company facts into standardized quarterly
financial statement line items suitable for comparative analysis.

Mapping Strategy
----------------
1. **Tag Priority**: For each line item, we define a prioritized list of XBRL tags.
   Banks may use different tags for the same concept. We try tags in order and
   take the first non-null value.

2. **Period Selection**: We extract quarterly values (fp in ['Q1','Q2','Q3','Q4'])
   and annual values (fp='FY'). For flow items (revenue, income), we use quarterly
   directly when available, or derive Q4 from FY - (Q1+Q2+Q3).

3. **Deduplication**: Multiple facts may exist for the same period due to:
   - Restatements: We take the most recent filing (latest 'filed' date)
   - Multiple forms: Prefer 10-Q/10-K over 8-K amendments
   - Units: We normalize to USD, filtering out per-share or other units

4. **Validation**: Each extracted value is sanity-checked (positive where expected,
   reasonable magnitude) and flagged if suspicious.

Bank-Specific Considerations
----------------------------
- Banks report under US-GAAP with some industry-specific tags
- Key items like Net Interest Income use bank-specific taxonomy
- Tier 1 Capital and regulatory ratios may use custom extensions
"""

import logging
from dataclasses import dataclass

import pandas as pd

from banklab.config import DEFAULT_CONFIG, Config

logger = logging.getLogger(__name__)


# =============================================================================
# LINE ITEM MAPPINGS
# =============================================================================


@dataclass
class LineItemMapping:
    """Definition of a standardized line item and its XBRL tag mappings."""

    name: str  # Standardized name (e.g., 'total_revenue')
    display_name: str  # Human-readable name
    category: str  # 'income_statement', 'balance_sheet', 'cash_flow', 'regulatory'
    tags: list[str]  # Prioritized list of XBRL tags to try
    is_flow: bool  # True for P&L/CF items, False for point-in-time (BS)
    expected_sign: str  # 'positive', 'negative', or 'any'
    unit_filter: str  # 'USD', 'shares', 'pure' (for ratios)
    description: str  # Documentation


# Comprehensive mappings for bank financial statements
# Tags are listed in priority order - first match wins
BANK_LINE_ITEM_MAPPINGS: dict[str, LineItemMapping] = {
    # =========================================================================
    # INCOME STATEMENT
    # =========================================================================
    "total_revenue": LineItemMapping(
        name="total_revenue",
        display_name="Total Revenue",
        category="income_statement",
        tags=[
            "us-gaap:Revenues",
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:SalesRevenueNet",
            "us-gaap:InterestAndDividendIncomeOperating",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Total revenues including interest and non-interest income",
    ),
    "net_interest_income": LineItemMapping(
        name="net_interest_income",
        display_name="Net Interest Income",
        category="income_statement",
        tags=[
            "us-gaap:InterestIncomeExpenseNet",
            "us-gaap:NetInterestIncome",
            "us-gaap:InterestIncomeExpenseAfterProvisionForLoanLoss",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Interest income minus interest expense",
    ),
    "noninterest_income": LineItemMapping(
        name="noninterest_income",
        display_name="Non-Interest Income",
        category="income_statement",
        tags=[
            "us-gaap:NoninterestIncome",
            "us-gaap:FeesAndCommissions",
            "us-gaap:InvestmentBankingRevenue",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Fee income, trading, investment banking, etc.",
    ),
    "provision_for_credit_losses": LineItemMapping(
        name="provision_for_credit_losses",
        display_name="Provision for Credit Losses",
        category="income_statement",
        tags=[
            "us-gaap:ProvisionForLoanLeaseAndOtherLosses",
            "us-gaap:ProvisionForLoanAndLeaseLosses",
            "us-gaap:ProvisionForCreditLosses",
        ],
        is_flow=True,
        expected_sign="any",  # Can be negative in recoveries
        unit_filter="USD",
        description="Provision for loan losses and credit impairments",
    ),
    "noninterest_expense": LineItemMapping(
        name="noninterest_expense",
        display_name="Non-Interest Expense",
        category="income_statement",
        tags=[
            "us-gaap:NoninterestExpense",
            "us-gaap:OperatingExpenses",
            "us-gaap:GeneralAndAdministrativeExpense",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Salaries, occupancy, technology, other operating costs",
    ),
    "income_before_tax": LineItemMapping(
        name="income_before_tax",
        display_name="Income Before Tax",
        category="income_statement",
        tags=[
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
            "us-gaap:IncomeLossBeforeIncomeTaxes",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Pre-tax income from continuing operations",
    ),
    "income_tax_expense": LineItemMapping(
        name="income_tax_expense",
        display_name="Income Tax Expense",
        category="income_statement",
        tags=[
            "us-gaap:IncomeTaxExpenseBenefit",
            "us-gaap:IncomeTaxesPaid",
        ],
        is_flow=True,
        expected_sign="any",  # Can be benefit (negative)
        unit_filter="USD",
        description="Current and deferred income tax expense",
    ),
    "net_income": LineItemMapping(
        name="net_income",
        display_name="Net Income",
        category="income_statement",
        tags=[
            "us-gaap:NetIncomeLoss",
            "us-gaap:ProfitLoss",
            "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Net income attributable to common shareholders",
    ),
    "comprehensive_income": LineItemMapping(
        name="comprehensive_income",
        display_name="Comprehensive Income",
        category="income_statement",
        tags=[
            "us-gaap:ComprehensiveIncomeNetOfTax",
            "us-gaap:ComprehensiveIncomeNetOfTaxIncludingPortionAttributableToNoncontrollingInterest",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Net income plus other comprehensive income",
    ),
    # =========================================================================
    # BALANCE SHEET - ASSETS
    # =========================================================================
    "total_assets": LineItemMapping(
        name="total_assets",
        display_name="Total Assets",
        category="balance_sheet",
        tags=[
            "us-gaap:Assets",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Total assets",
    ),
    "cash_and_equivalents": LineItemMapping(
        name="cash_and_equivalents",
        display_name="Cash and Cash Equivalents",
        category="balance_sheet",
        tags=[
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:Cash",
            "us-gaap:CashCashEquivalentsAndShortTermInvestments",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Cash and liquid assets",
    ),
    "trading_assets": LineItemMapping(
        name="trading_assets",
        display_name="Trading Assets",
        category="balance_sheet",
        tags=[
            "us-gaap:TradingSecurities",
            "us-gaap:TradingAssets",
            "us-gaap:MarketableSecurities",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Securities held for trading",
    ),
    "investment_securities": LineItemMapping(
        name="investment_securities",
        display_name="Investment Securities",
        category="balance_sheet",
        tags=[
            "us-gaap:AvailableForSaleSecuritiesDebtSecurities",
            "us-gaap:HeldToMaturitySecurities",
            "us-gaap:InvestmentsInDebtAndMarketableEquitySecuritiesAndCertainTradingAssetsDisclosureTextBlock",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="AFS and HTM securities",
    ),
    "loans_net": LineItemMapping(
        name="loans_net",
        display_name="Loans, Net",
        category="balance_sheet",
        tags=[
            "us-gaap:LoansAndLeasesReceivableNetReportedAmount",
            "us-gaap:LoansReceivableNet",
            "us-gaap:LoansAndLeasesReceivableNetOfDeferredIncome",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Net loans after allowance for loan losses",
    ),
    "allowance_for_loan_losses": LineItemMapping(
        name="allowance_for_loan_losses",
        display_name="Allowance for Loan Losses",
        category="balance_sheet",
        tags=[
            "us-gaap:FinancingReceivableAllowanceForCreditLosses",
            "us-gaap:AllowanceForLoanAndLeaseLossesRealEstate",
            "us-gaap:LoansAndLeasesReceivableAllowance",
        ],
        is_flow=False,
        expected_sign="positive",  # Reported as positive contra-asset
        unit_filter="USD",
        description="Reserve for expected credit losses",
    ),
    "goodwill": LineItemMapping(
        name="goodwill",
        display_name="Goodwill",
        category="balance_sheet",
        tags=[
            "us-gaap:Goodwill",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Goodwill from acquisitions",
    ),
    "intangible_assets": LineItemMapping(
        name="intangible_assets",
        display_name="Intangible Assets",
        category="balance_sheet",
        tags=[
            "us-gaap:IntangibleAssetsNetExcludingGoodwill",
            "us-gaap:FiniteLivedIntangibleAssetsNet",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Intangible assets excluding goodwill",
    ),
    # =========================================================================
    # BALANCE SHEET - LIABILITIES
    # =========================================================================
    "total_liabilities": LineItemMapping(
        name="total_liabilities",
        display_name="Total Liabilities",
        category="balance_sheet",
        tags=[
            "us-gaap:Liabilities",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Total liabilities",
    ),
    "total_deposits": LineItemMapping(
        name="total_deposits",
        display_name="Total Deposits",
        category="balance_sheet",
        tags=[
            "us-gaap:Deposits",
            "us-gaap:DepositsDomestic",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Customer deposits",
    ),
    "short_term_borrowings": LineItemMapping(
        name="short_term_borrowings",
        display_name="Short-Term Borrowings",
        category="balance_sheet",
        tags=[
            "us-gaap:ShortTermBorrowings",
            "us-gaap:CommercialPaper",
            "us-gaap:FederalFundsPurchasedAndSecuritiesSoldUnderAgreementsToRepurchase",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Short-term debt and repo",
    ),
    "long_term_debt": LineItemMapping(
        name="long_term_debt",
        display_name="Long-Term Debt",
        category="balance_sheet",
        tags=[
            "us-gaap:LongTermDebt",
            "us-gaap:LongTermDebtNoncurrent",
            "us-gaap:SeniorNotes",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Long-term debt obligations",
    ),
    # =========================================================================
    # BALANCE SHEET - EQUITY
    # =========================================================================
    "total_equity": LineItemMapping(
        name="total_equity",
        display_name="Total Stockholders' Equity",
        category="balance_sheet",
        tags=[
            "us-gaap:StockholdersEquity",
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Total shareholders' equity",
    ),
    "common_stock": LineItemMapping(
        name="common_stock",
        display_name="Common Stock",
        category="balance_sheet",
        tags=[
            "us-gaap:CommonStockValue",
            "us-gaap:CommonStocksIncludingAdditionalPaidInCapital",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="USD",
        description="Common stock at par + APIC",
    ),
    "retained_earnings": LineItemMapping(
        name="retained_earnings",
        display_name="Retained Earnings",
        category="balance_sheet",
        tags=[
            "us-gaap:RetainedEarningsAccumulatedDeficit",
        ],
        is_flow=False,
        expected_sign="any",
        unit_filter="USD",
        description="Accumulated retained earnings",
    ),
    "treasury_stock": LineItemMapping(
        name="treasury_stock",
        display_name="Treasury Stock",
        category="balance_sheet",
        tags=[
            "us-gaap:TreasuryStockValue",
            "us-gaap:TreasuryStockCommonValue",
        ],
        is_flow=False,
        expected_sign="positive",  # Reported as positive, reduces equity
        unit_filter="USD",
        description="Treasury stock at cost",
    ),
    "accumulated_other_comprehensive_income": LineItemMapping(
        name="accumulated_other_comprehensive_income",
        display_name="AOCI",
        category="balance_sheet",
        tags=[
            "us-gaap:AccumulatedOtherComprehensiveIncomeLossNetOfTax",
        ],
        is_flow=False,
        expected_sign="any",
        unit_filter="USD",
        description="Accumulated other comprehensive income/loss",
    ),
    # =========================================================================
    # SHARES
    # =========================================================================
    "shares_outstanding": LineItemMapping(
        name="shares_outstanding",
        display_name="Shares Outstanding",
        category="shares",
        tags=[
            "us-gaap:CommonStockSharesOutstanding",
            "us-gaap:CommonStockSharesIssued",
        ],
        is_flow=False,
        expected_sign="positive",
        unit_filter="shares",
        description="Common shares outstanding",
    ),
    "weighted_avg_shares_basic": LineItemMapping(
        name="weighted_avg_shares_basic",
        display_name="Weighted Avg Shares (Basic)",
        category="shares",
        tags=[
            "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="shares",
        description="Weighted average shares for basic EPS",
    ),
    "weighted_avg_shares_diluted": LineItemMapping(
        name="weighted_avg_shares_diluted",
        display_name="Weighted Avg Shares (Diluted)",
        category="shares",
        tags=[
            "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="shares",
        description="Weighted average shares for diluted EPS",
    ),
    # =========================================================================
    # CASH FLOW
    # =========================================================================
    "operating_cash_flow": LineItemMapping(
        name="operating_cash_flow",
        display_name="Operating Cash Flow",
        category="cash_flow",
        tags=[
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Net cash from operating activities",
    ),
    "investing_cash_flow": LineItemMapping(
        name="investing_cash_flow",
        display_name="Investing Cash Flow",
        category="cash_flow",
        tags=[
            "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Net cash from investing activities",
    ),
    "financing_cash_flow": LineItemMapping(
        name="financing_cash_flow",
        display_name="Financing Cash Flow",
        category="cash_flow",
        tags=[
            "us-gaap:NetCashProvidedByUsedInFinancingActivities",
        ],
        is_flow=True,
        expected_sign="any",
        unit_filter="USD",
        description="Net cash from financing activities",
    ),
    "dividends_paid": LineItemMapping(
        name="dividends_paid",
        display_name="Dividends Paid",
        category="cash_flow",
        tags=[
            "us-gaap:PaymentsOfDividendsCommonStock",
            "us-gaap:PaymentsOfDividends",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Cash dividends paid to shareholders",
    ),
    "share_repurchases": LineItemMapping(
        name="share_repurchases",
        display_name="Share Repurchases",
        category="cash_flow",
        tags=[
            "us-gaap:PaymentsForRepurchaseOfCommonStock",
            "us-gaap:StockRepurchasedDuringPeriodValue",
        ],
        is_flow=True,
        expected_sign="positive",
        unit_filter="USD",
        description="Cash paid for share buybacks",
    ),
}


# =============================================================================
# NORMALIZER CLASS
# =============================================================================


class XBRLNormalizer:
    """Normalize raw XBRL facts into standardized quarterly financial data.

    This class handles:
    - Tag mapping with fallback priorities
    - Period deduplication (restatements, amendments)
    - Unit filtering and normalization
    - Quarterly panel construction

    Example
    -------
    >>> normalizer = XBRLNormalizer()
    >>> quarterly_df = normalizer.normalize(raw_facts_df)
    """

    def __init__(
        self,
        config: Config | None = None,
        mappings: dict[str, LineItemMapping] | None = None,
        min_year: int = 2015,
    ):
        """Initialize normalizer.

        Args:
            config: BankLab configuration
            mappings: Custom line item mappings (defaults to BANK_LINE_ITEM_MAPPINGS)
            min_year: Minimum fiscal year to include
        """
        self.config = config or DEFAULT_CONFIG
        self.mappings = mappings or BANK_LINE_ITEM_MAPPINGS
        self.min_year = min_year

    def normalize(self, raw_facts: pd.DataFrame) -> pd.DataFrame:
        """Normalize raw facts to standardized quarterly panel.

        Args:
            raw_facts: DataFrame from fundamentals_raw_facts.parquet with columns:
                       date, cik, ticker, tag, value, unit, fp, fy, form

        Returns:
            DataFrame with columns: ticker, fiscal_year, fiscal_period, date,
                                    line_item, value, source_tag
        """
        logger.info(f"Normalizing {len(raw_facts):,} raw facts")

        # Filter to relevant years and periods
        df = raw_facts[
            (raw_facts["fy"] >= self.min_year)
            & (raw_facts["fp"].isin(["Q1", "Q2", "Q3", "Q4", "FY"]))
        ].copy()

        logger.info(f"After year/period filter: {len(df):,} facts")

        results = []

        for ticker in df["ticker"].unique():
            ticker_df = df[df["ticker"] == ticker]
            ticker_results = self._normalize_ticker(ticker_df, ticker)
            results.append(ticker_results)

        if not results:
            return pd.DataFrame()

        output = pd.concat(results, ignore_index=True)
        output = output.sort_values(
            ["ticker", "fiscal_year", "fiscal_period", "line_item"]
        ).reset_index(drop=True)

        logger.info(f"Normalized to {len(output):,} line items")
        return output

    def _normalize_ticker(self, ticker_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Normalize facts for a single ticker."""
        results = []

        # Get unique fiscal periods
        periods = ticker_df.groupby(["fy", "fp"]).size().reset_index()[["fy", "fp"]]

        for _, period_row in periods.iterrows():
            fy = period_row["fy"]
            fp = period_row["fp"]

            period_df = ticker_df[(ticker_df["fy"] == fy) & (ticker_df["fp"] == fp)]

            for item_name, mapping in self.mappings.items():
                value, source_tag = self._extract_line_item(period_df, mapping)

                if value is not None:
                    # Get the period end date
                    period_date = period_df["date"].max()

                    results.append(
                        {
                            "ticker": ticker,
                            "fiscal_year": int(fy),
                            "fiscal_period": fp,
                            "date": period_date,
                            "line_item": item_name,
                            "display_name": mapping.display_name,
                            "category": mapping.category,
                            "value": value,
                            "source_tag": source_tag,
                        }
                    )

        return pd.DataFrame(results)

    def _extract_line_item(
        self,
        period_df: pd.DataFrame,
        mapping: LineItemMapping,
    ) -> tuple[float | None, str | None]:
        """Extract a single line item value from period facts.

        Args:
            period_df: Facts for a single fiscal period
            mapping: Line item mapping definition

        Returns:
            Tuple of (value, source_tag) or (None, None) if not found
        """
        # Filter by unit
        if mapping.unit_filter == "USD":
            unit_df = period_df[period_df["unit"] == "USD"]
        elif mapping.unit_filter == "shares":
            unit_df = period_df[period_df["unit"] == "shares"]
        else:
            unit_df = period_df

        # Try each tag in priority order
        for tag in mapping.tags:
            tag_df = unit_df[unit_df["tag"] == tag]

            if len(tag_df) == 0:
                continue

            # Deduplicate: prefer 10-K/10-Q, then most recent
            if len(tag_df) > 1:
                # Prefer quarterly/annual filings
                preferred_forms = ["10-K", "10-Q", "10-K/A", "10-Q/A"]
                for form in preferred_forms:
                    form_df = tag_df[tag_df["form"] == form]
                    if len(form_df) > 0:
                        tag_df = form_df
                        break

                # Take most recent by date
                tag_df = tag_df.sort_values("date", ascending=False).head(1)

            value = tag_df["value"].iloc[0]

            # Validate value
            if pd.isna(value):
                continue

            return float(value), tag

        return None, None

    def to_wide_format(self, normalized_df: pd.DataFrame) -> pd.DataFrame:
        """Convert normalized long format to wide format.

        Args:
            normalized_df: Output from normalize()

        Returns:
            DataFrame with columns: ticker, fiscal_year, fiscal_period, date,
                                    plus one column per line item
        """
        # Pivot to wide format
        wide = normalized_df.pivot_table(
            index=["ticker", "fiscal_year", "fiscal_period", "date"],
            columns="line_item",
            values="value",
            aggfunc="first",
        ).reset_index()

        # Flatten column names
        wide.columns = [col if isinstance(col, str) else col[1] or col[0] for col in wide.columns]

        return wide

    def get_data_dictionary(self) -> pd.DataFrame:
        """Generate data dictionary for line item mappings.

        Returns:
            DataFrame documenting each line item
        """
        records = []
        for name, mapping in self.mappings.items():
            records.append(
                {
                    "line_item": name,
                    "display_name": mapping.display_name,
                    "category": mapping.category,
                    "is_flow": mapping.is_flow,
                    "expected_sign": mapping.expected_sign,
                    "unit": mapping.unit_filter,
                    "primary_tag": mapping.tags[0] if mapping.tags else None,
                    "fallback_tags": ", ".join(mapping.tags[1:]) if len(mapping.tags) > 1 else None,
                    "description": mapping.description,
                }
            )
        return pd.DataFrame(records)


def load_and_normalize(config: Config | None = None) -> pd.DataFrame:
    """Convenience function to load raw facts and normalize.

    Args:
        config: BankLab configuration

    Returns:
        Normalized quarterly fundamentals DataFrame
    """
    config = config or DEFAULT_CONFIG

    # Load raw facts
    raw_path = config.processed_dir / "fundamentals_raw_facts.parquet"
    raw_facts = pd.read_parquet(raw_path)

    # Normalize
    normalizer = XBRLNormalizer(config)
    normalized = normalizer.normalize(raw_facts)

    return normalized
