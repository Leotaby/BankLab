"""Bank KPI calculation functions.

All KPI functions are implemented as pure functions that take pandas Series
or scalar values and return calculated metrics. This design enables:
- Easy unit testing with toy data
- Vectorized application across DataFrames
- Clear documentation of formulas

Naming Convention
-----------------
- All inputs should be passed as keyword arguments for clarity
- Functions handle None/NaN gracefully, returning NaN
- Annualization is handled explicitly where applicable
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class KPIDefinition:
    """Metadata for a KPI."""

    name: str
    display_name: str
    category: str
    formula: str
    unit: str  # 'ratio', 'percent', 'currency', 'multiple'
    description: str
    inputs: list[str]  # Required line items


# =============================================================================
# PROFITABILITY KPIS
# =============================================================================


def return_on_equity(
    net_income: float | pd.Series,
    total_equity: float | pd.Series,
    annualize: bool = True,
    periods_per_year: int = 4,
) -> float | pd.Series:
    """Calculate Return on Equity (ROE).

    Formula: Net Income / Average Shareholders' Equity

    For quarterly data, we annualize by multiplying by periods_per_year.
    Uses point-in-time equity (for average, caller should provide avg).

    Args:
        net_income: Net income for the period (flow)
        total_equity: Shareholders' equity (stock, period-end or average)
        annualize: Whether to annualize quarterly figures
        periods_per_year: Number of periods in a year (4 for quarterly)

    Returns:
        ROE as a decimal (0.15 = 15%)

    Example:
        >>> return_on_equity(net_income=5_000, total_equity=50_000, annualize=False)
        0.1
    """
    if _is_invalid(net_income) or _is_invalid(total_equity):
        return np.nan

    if _is_zero(total_equity):
        return np.nan

    roe = net_income / total_equity

    if annualize:
        roe = roe * periods_per_year

    return roe


def return_on_assets(
    net_income: float | pd.Series,
    total_assets: float | pd.Series,
    annualize: bool = True,
    periods_per_year: int = 4,
) -> float | pd.Series:
    """Calculate Return on Assets (ROA).

    Formula: Net Income / Average Total Assets

    Args:
        net_income: Net income for the period
        total_assets: Total assets (period-end or average)
        annualize: Whether to annualize quarterly figures
        periods_per_year: Number of periods in a year

    Returns:
        ROA as a decimal (0.01 = 1%)

    Example:
        >>> return_on_assets(net_income=5_000, total_assets=500_000, annualize=False)
        0.01
    """
    if _is_invalid(net_income) or _is_invalid(total_assets):
        return np.nan

    if _is_zero(total_assets):
        return np.nan

    roa = net_income / total_assets

    if annualize:
        roa = roa * periods_per_year

    return roa


def net_interest_margin(
    net_interest_income: float | pd.Series,
    total_assets: float | pd.Series,
    annualize: bool = True,
    periods_per_year: int = 4,
) -> float | pd.Series:
    """Calculate Net Interest Margin (NIM).

    Formula: Net Interest Income / Average Earning Assets

    Note: Ideally uses average earning assets, but we approximate with total
    assets if earning assets not available.

    Args:
        net_interest_income: Interest income minus interest expense
        total_assets: Total assets (proxy for earning assets)
        annualize: Whether to annualize quarterly figures
        periods_per_year: Number of periods in a year

    Returns:
        NIM as a decimal (0.03 = 3%)

    Example:
        >>> net_interest_margin(net_interest_income=3_000, total_assets=400_000, annualize=False)
        0.0075
    """
    if _is_invalid(net_interest_income) or _is_invalid(total_assets):
        return np.nan

    if _is_zero(total_assets):
        return np.nan

    nim = net_interest_income / total_assets

    if annualize:
        nim = nim * periods_per_year

    return nim


def efficiency_ratio(
    noninterest_expense: float | pd.Series,
    total_revenue: float | pd.Series,
) -> float | pd.Series:
    """Calculate Efficiency Ratio.

    Formula: Non-Interest Expense / Total Revenue

    Lower is better. Measures operating efficiency.

    Args:
        noninterest_expense: Operating expenses (non-interest)
        total_revenue: Total revenue (NII + non-interest income)

    Returns:
        Efficiency ratio as a decimal (0.60 = 60%)

    Example:
        >>> efficiency_ratio(noninterest_expense=6_000, total_revenue=10_000)
        0.6
    """
    if _is_invalid(noninterest_expense) or _is_invalid(total_revenue):
        return np.nan

    if _is_zero(total_revenue):
        return np.nan

    return noninterest_expense / total_revenue


def pre_provision_net_revenue(
    net_interest_income: float | pd.Series,
    noninterest_income: float | pd.Series,
    noninterest_expense: float | pd.Series,
) -> float | pd.Series:
    """Calculate Pre-Provision Net Revenue (PPNR).

    Formula: Net Interest Income + Non-Interest Income - Non-Interest Expense

    Key metric for bank earnings power before credit costs.

    Args:
        net_interest_income: Net interest income
        noninterest_income: Fee and other income
        noninterest_expense: Operating expenses

    Returns:
        PPNR in currency units

    Example:
        >>> pre_provision_net_revenue(
        ...     net_interest_income=5_000,
        ...     noninterest_income=3_000,
        ...     noninterest_expense=4_000
        ... )
        4000
    """
    nii = 0 if _is_invalid(net_interest_income) else net_interest_income
    non_int_inc = 0 if _is_invalid(noninterest_income) else noninterest_income
    non_int_exp = 0 if _is_invalid(noninterest_expense) else noninterest_expense

    return nii + non_int_inc - non_int_exp


# =============================================================================
# VALUATION KPIS
# =============================================================================


def earnings_per_share(
    net_income: float | pd.Series,
    shares_outstanding: float | pd.Series,
) -> float | pd.Series:
    """Calculate Earnings Per Share (EPS).

    Formula: Net Income / Weighted Average Shares Outstanding

    Args:
        net_income: Net income attributable to common
        shares_outstanding: Weighted average shares (basic or diluted)

    Returns:
        EPS in currency per share

    Example:
        >>> earnings_per_share(net_income=1_000_000, shares_outstanding=100_000)
        10.0
    """
    if _is_invalid(net_income) or _is_invalid(shares_outstanding):
        return np.nan

    if _is_zero(shares_outstanding):
        return np.nan

    return net_income / shares_outstanding


def book_value_per_share(
    total_equity: float | pd.Series,
    shares_outstanding: float | pd.Series,
) -> float | pd.Series:
    """Calculate Book Value Per Share (BVPS).

    Formula: Total Shareholders' Equity / Shares Outstanding

    Args:
        total_equity: Total shareholders' equity
        shares_outstanding: Common shares outstanding

    Returns:
        BVPS in currency per share

    Example:
        >>> book_value_per_share(total_equity=5_000_000, shares_outstanding=100_000)
        50.0
    """
    if _is_invalid(total_equity) or _is_invalid(shares_outstanding):
        return np.nan

    if _is_zero(shares_outstanding):
        return np.nan

    return total_equity / shares_outstanding


def tangible_book_value_per_share(
    total_equity: float | pd.Series,
    goodwill: float | pd.Series,
    intangible_assets: float | pd.Series,
    shares_outstanding: float | pd.Series,
) -> float | pd.Series:
    """Calculate Tangible Book Value Per Share (TBVPS).

    Formula: (Total Equity - Goodwill - Intangibles) / Shares Outstanding

    More conservative measure excluding acquisition premiums.

    Args:
        total_equity: Total shareholders' equity
        goodwill: Goodwill from acquisitions
        intangible_assets: Other intangible assets
        shares_outstanding: Common shares outstanding

    Returns:
        TBVPS in currency per share

    Example:
        >>> tangible_book_value_per_share(
        ...     total_equity=5_000_000,
        ...     goodwill=500_000,
        ...     intangible_assets=200_000,
        ...     shares_outstanding=100_000
        ... )
        43.0
    """
    if _is_invalid(total_equity) or _is_invalid(shares_outstanding):
        return np.nan

    if _is_zero(shares_outstanding):
        return np.nan

    gw = 0 if _is_invalid(goodwill) else goodwill
    intang = 0 if _is_invalid(intangible_assets) else intangible_assets

    tangible_equity = total_equity - gw - intang
    return tangible_equity / shares_outstanding


def price_to_book(
    stock_price: float | pd.Series,
    book_value_per_share: float | pd.Series,
) -> float | pd.Series:
    """Calculate Price-to-Book Ratio (P/B).

    Formula: Stock Price / Book Value Per Share

    Args:
        stock_price: Current stock price
        book_value_per_share: BVPS

    Returns:
        P/B multiple

    Example:
        >>> price_to_book(stock_price=75.0, book_value_per_share=50.0)
        1.5
    """
    if _is_invalid(stock_price) or _is_invalid(book_value_per_share):
        return np.nan

    if _is_zero(book_value_per_share):
        return np.nan

    return stock_price / book_value_per_share


def price_to_earnings(
    stock_price: float | pd.Series,
    eps_ttm: float | pd.Series,
) -> float | pd.Series:
    """Calculate Price-to-Earnings Ratio (P/E).

    Formula: Stock Price / Trailing Twelve Month EPS

    Args:
        stock_price: Current stock price
        eps_ttm: Trailing 12-month earnings per share

    Returns:
        P/E multiple

    Example:
        >>> price_to_earnings(stock_price=100.0, eps_ttm=10.0)
        10.0
    """
    if _is_invalid(stock_price) or _is_invalid(eps_ttm):
        return np.nan

    if _is_zero(eps_ttm):
        return np.nan

    return stock_price / eps_ttm


def price_to_tangible_book(
    stock_price: float | pd.Series,
    tangible_book_value_per_share: float | pd.Series,
) -> float | pd.Series:
    """Calculate Price-to-Tangible Book Ratio (P/TBV).

    Formula: Stock Price / Tangible Book Value Per Share

    Args:
        stock_price: Current stock price
        tangible_book_value_per_share: TBVPS

    Returns:
        P/TBV multiple
    """
    if _is_invalid(stock_price) or _is_invalid(tangible_book_value_per_share):
        return np.nan

    if _is_zero(tangible_book_value_per_share):
        return np.nan

    return stock_price / tangible_book_value_per_share


# =============================================================================
# CAPITAL & LEVERAGE KPIS
# =============================================================================


def equity_to_assets(
    total_equity: float | pd.Series,
    total_assets: float | pd.Series,
) -> float | pd.Series:
    """Calculate Equity-to-Assets Ratio.

    Formula: Total Equity / Total Assets

    Basic capital adequacy measure.

    Args:
        total_equity: Total shareholders' equity
        total_assets: Total assets

    Returns:
        Ratio as decimal (0.10 = 10%)

    Example:
        >>> equity_to_assets(total_equity=50_000, total_assets=500_000)
        0.1
    """
    if _is_invalid(total_equity) or _is_invalid(total_assets):
        return np.nan

    if _is_zero(total_assets):
        return np.nan

    return total_equity / total_assets


def tangible_equity_ratio(
    total_equity: float | pd.Series,
    goodwill: float | pd.Series,
    intangible_assets: float | pd.Series,
    total_assets: float | pd.Series,
) -> float | pd.Series:
    """Calculate Tangible Common Equity Ratio (TCE).

    Formula: (Equity - Goodwill - Intangibles) / (Assets - Goodwill - Intangibles)

    Conservative capital measure used in stress testing.

    Args:
        total_equity: Total shareholders' equity
        goodwill: Goodwill
        intangible_assets: Other intangibles
        total_assets: Total assets

    Returns:
        TCE ratio as decimal
    """
    if _is_invalid(total_equity) or _is_invalid(total_assets):
        return np.nan

    gw = 0 if _is_invalid(goodwill) else goodwill
    intang = 0 if _is_invalid(intangible_assets) else intangible_assets

    tangible_equity = total_equity - gw - intang
    tangible_assets = total_assets - gw - intang

    if _is_zero(tangible_assets):
        return np.nan

    return tangible_equity / tangible_assets


def leverage_ratio(
    total_assets: float | pd.Series,
    total_equity: float | pd.Series,
) -> float | pd.Series:
    """Calculate Leverage Ratio (Assets/Equity).

    Formula: Total Assets / Total Equity

    Higher = more leveraged.

    Args:
        total_assets: Total assets
        total_equity: Total shareholders' equity

    Returns:
        Leverage multiple

    Example:
        >>> leverage_ratio(total_assets=500_000, total_equity=50_000)
        10.0
    """
    if _is_invalid(total_assets) or _is_invalid(total_equity):
        return np.nan

    if _is_zero(total_equity):
        return np.nan

    return total_assets / total_equity


# =============================================================================
# ASSET QUALITY KPIS
# =============================================================================


def allowance_coverage_ratio(
    allowance_for_loan_losses: float | pd.Series,
    loans_net: float | pd.Series,
) -> float | pd.Series:
    """Calculate Allowance Coverage Ratio.

    Formula: Allowance for Loan Losses / Net Loans

    Higher indicates more conservative provisioning.

    Args:
        allowance_for_loan_losses: ALLL reserve balance
        loans_net: Net loans (after ALLL)

    Returns:
        Coverage ratio as decimal
    """
    if _is_invalid(allowance_for_loan_losses) or _is_invalid(loans_net):
        return np.nan

    if _is_zero(loans_net):
        return np.nan

    # Gross loans = net + allowance
    gross_loans = loans_net + allowance_for_loan_losses

    if _is_zero(gross_loans):
        return np.nan

    return allowance_for_loan_losses / gross_loans


def net_charge_off_ratio(
    provision_for_credit_losses: float | pd.Series,
    loans_net: float | pd.Series,
    annualize: bool = True,
    periods_per_year: int = 4,
) -> float | pd.Series:
    """Calculate Net Charge-Off Ratio (approximation).

    Formula: Provision for Credit Losses / Average Loans

    Note: This is a proxy using provision; actual NCOs require additional data.

    Args:
        provision_for_credit_losses: Credit loss provision (flow)
        loans_net: Net loans (stock)
        annualize: Whether to annualize
        periods_per_year: Periods per year

    Returns:
        NCO ratio as decimal
    """
    if _is_invalid(provision_for_credit_losses) or _is_invalid(loans_net):
        return np.nan

    if _is_zero(loans_net):
        return np.nan

    ratio = provision_for_credit_losses / loans_net

    if annualize:
        ratio = ratio * periods_per_year

    return ratio


# =============================================================================
# LIQUIDITY KPIS
# =============================================================================


def loan_to_deposit_ratio(
    loans_net: float | pd.Series,
    total_deposits: float | pd.Series,
) -> float | pd.Series:
    """Calculate Loan-to-Deposit Ratio (LDR).

    Formula: Net Loans / Total Deposits

    Higher indicates more aggressive lending relative to deposit base.

    Args:
        loans_net: Net loans
        total_deposits: Customer deposits

    Returns:
        LDR as decimal (0.80 = 80%)

    Example:
        >>> loan_to_deposit_ratio(loans_net=80_000, total_deposits=100_000)
        0.8
    """
    if _is_invalid(loans_net) or _is_invalid(total_deposits):
        return np.nan

    if _is_zero(total_deposits):
        return np.nan

    return loans_net / total_deposits


# =============================================================================
# GROWTH KPIS
# =============================================================================


def yoy_growth(
    current_value: float | pd.Series,
    prior_year_value: float | pd.Series,
) -> float | pd.Series:
    """Calculate Year-over-Year Growth Rate.

    Formula: (Current - Prior Year) / Prior Year

    Args:
        current_value: Current period value
        prior_year_value: Same period, prior year value

    Returns:
        Growth rate as decimal (0.10 = 10% growth)

    Example:
        >>> yoy_growth(current_value=110, prior_year_value=100)
        0.1
    """
    if _is_invalid(current_value) or _is_invalid(prior_year_value):
        return np.nan

    if _is_zero(prior_year_value):
        return np.nan

    return (current_value - prior_year_value) / abs(prior_year_value)


def qoq_growth(
    current_value: float | pd.Series,
    prior_quarter_value: float | pd.Series,
) -> float | pd.Series:
    """Calculate Quarter-over-Quarter Growth Rate.

    Formula: (Current - Prior Quarter) / Prior Quarter

    Args:
        current_value: Current quarter value
        prior_quarter_value: Prior quarter value

    Returns:
        Growth rate as decimal
    """
    if _is_invalid(current_value) or _is_invalid(prior_quarter_value):
        return np.nan

    if _is_zero(prior_quarter_value):
        return np.nan

    return (current_value - prior_quarter_value) / abs(prior_quarter_value)


# =============================================================================
# KPI DEFINITIONS REGISTRY
# =============================================================================

KPI_DEFINITIONS: dict[str, KPIDefinition] = {
    "roe": KPIDefinition(
        name="roe",
        display_name="Return on Equity",
        category="profitability",
        formula="Net Income / Shareholders' Equity (annualized)",
        unit="percent",
        description="Measures profitability relative to shareholder investment",
        inputs=["net_income", "total_equity"],
    ),
    "roa": KPIDefinition(
        name="roa",
        display_name="Return on Assets",
        category="profitability",
        formula="Net Income / Total Assets (annualized)",
        unit="percent",
        description="Measures profitability relative to asset base",
        inputs=["net_income", "total_assets"],
    ),
    "nim": KPIDefinition(
        name="nim",
        display_name="Net Interest Margin",
        category="profitability",
        formula="Net Interest Income / Total Assets (annualized)",
        unit="percent",
        description="Spread earned on interest-bearing assets",
        inputs=["net_interest_income", "total_assets"],
    ),
    "efficiency_ratio": KPIDefinition(
        name="efficiency_ratio",
        display_name="Efficiency Ratio",
        category="profitability",
        formula="Non-Interest Expense / Total Revenue",
        unit="percent",
        description="Operating costs as % of revenue (lower is better)",
        inputs=["noninterest_expense", "total_revenue"],
    ),
    "ppnr": KPIDefinition(
        name="ppnr",
        display_name="Pre-Provision Net Revenue",
        category="profitability",
        formula="NII + Non-Int Income - Non-Int Expense",
        unit="currency",
        description="Earnings power before credit costs",
        inputs=["net_interest_income", "noninterest_income", "noninterest_expense"],
    ),
    "eps": KPIDefinition(
        name="eps",
        display_name="Earnings Per Share",
        category="valuation",
        formula="Net Income / Shares Outstanding",
        unit="currency",
        description="Net income per common share",
        inputs=["net_income", "shares_outstanding"],
    ),
    "bvps": KPIDefinition(
        name="bvps",
        display_name="Book Value Per Share",
        category="valuation",
        formula="Total Equity / Shares Outstanding",
        unit="currency",
        description="Accounting value per share",
        inputs=["total_equity", "shares_outstanding"],
    ),
    "tbvps": KPIDefinition(
        name="tbvps",
        display_name="Tangible Book Value Per Share",
        category="valuation",
        formula="(Equity - Goodwill - Intangibles) / Shares",
        unit="currency",
        description="Conservative book value excluding intangibles",
        inputs=["total_equity", "goodwill", "intangible_assets", "shares_outstanding"],
    ),
    "equity_to_assets": KPIDefinition(
        name="equity_to_assets",
        display_name="Equity to Assets",
        category="capital",
        formula="Total Equity / Total Assets",
        unit="percent",
        description="Basic capital adequacy measure",
        inputs=["total_equity", "total_assets"],
    ),
    "tce_ratio": KPIDefinition(
        name="tce_ratio",
        display_name="Tangible Common Equity Ratio",
        category="capital",
        formula="Tangible Equity / Tangible Assets",
        unit="percent",
        description="Conservative capital ratio",
        inputs=["total_equity", "goodwill", "intangible_assets", "total_assets"],
    ),
    "leverage": KPIDefinition(
        name="leverage",
        display_name="Leverage Ratio",
        category="capital",
        formula="Total Assets / Total Equity",
        unit="multiple",
        description="Financial leverage multiple",
        inputs=["total_assets", "total_equity"],
    ),
    "ldr": KPIDefinition(
        name="ldr",
        display_name="Loan-to-Deposit Ratio",
        category="liquidity",
        formula="Net Loans / Total Deposits",
        unit="percent",
        description="Lending intensity relative to deposit funding",
        inputs=["loans_net", "total_deposits"],
    ),
    "allowance_coverage": KPIDefinition(
        name="allowance_coverage",
        display_name="Allowance Coverage",
        category="asset_quality",
        formula="ALLL / Gross Loans",
        unit="percent",
        description="Reserve coverage of loan portfolio",
        inputs=["allowance_for_loan_losses", "loans_net"],
    ),
}


# =============================================================================
# AGGREGATOR FUNCTION
# =============================================================================


def calculate_all_kpis(row: pd.Series) -> dict[str, float]:
    """Calculate all KPIs for a single observation.

    Args:
        row: Series containing line item values (from wide-format fundamentals)

    Returns:
        Dictionary of KPI name -> value
    """

    def get(col: str) -> float:
        return row.get(col, np.nan)

    kpis = {}

    # Profitability
    kpis["roe"] = return_on_equity(
        net_income=get("net_income"),
        total_equity=get("total_equity"),
    )
    kpis["roa"] = return_on_assets(
        net_income=get("net_income"),
        total_assets=get("total_assets"),
    )
    kpis["nim"] = net_interest_margin(
        net_interest_income=get("net_interest_income"),
        total_assets=get("total_assets"),
    )
    kpis["efficiency_ratio"] = efficiency_ratio(
        noninterest_expense=get("noninterest_expense"),
        total_revenue=get("total_revenue"),
    )
    kpis["ppnr"] = pre_provision_net_revenue(
        net_interest_income=get("net_interest_income"),
        noninterest_income=get("noninterest_income"),
        noninterest_expense=get("noninterest_expense"),
    )

    # Valuation (per-share)
    shares = get("shares_outstanding") or get("weighted_avg_shares_basic")
    kpis["eps"] = earnings_per_share(
        net_income=get("net_income"),
        shares_outstanding=shares,
    )
    kpis["bvps"] = book_value_per_share(
        total_equity=get("total_equity"),
        shares_outstanding=shares,
    )
    kpis["tbvps"] = tangible_book_value_per_share(
        total_equity=get("total_equity"),
        goodwill=get("goodwill"),
        intangible_assets=get("intangible_assets"),
        shares_outstanding=shares,
    )

    # Capital
    kpis["equity_to_assets"] = equity_to_assets(
        total_equity=get("total_equity"),
        total_assets=get("total_assets"),
    )
    kpis["tce_ratio"] = tangible_equity_ratio(
        total_equity=get("total_equity"),
        goodwill=get("goodwill"),
        intangible_assets=get("intangible_assets"),
        total_assets=get("total_assets"),
    )
    kpis["leverage"] = leverage_ratio(
        total_assets=get("total_assets"),
        total_equity=get("total_equity"),
    )

    # Liquidity
    kpis["ldr"] = loan_to_deposit_ratio(
        loans_net=get("loans_net"),
        total_deposits=get("total_deposits"),
    )

    # Asset Quality
    kpis["allowance_coverage"] = allowance_coverage_ratio(
        allowance_for_loan_losses=get("allowance_for_loan_losses"),
        loans_net=get("loans_net"),
    )

    return kpis


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _is_invalid(value) -> bool:
    """Check if value is None, NaN, or invalid."""
    if value is None:
        return True
    if isinstance(value, (int, float)):
        return pd.isna(value)
    if isinstance(value, pd.Series):
        return False  # Let pandas handle Series
    return True


def _is_zero(value) -> bool:
    """Check if value is zero or close to zero."""
    if _is_invalid(value):
        return False
    if isinstance(value, (int, float)):
        return abs(value) < 1e-10
    return False
