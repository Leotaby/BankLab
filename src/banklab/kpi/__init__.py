"""KPI calculation library for bank financial analysis."""

from banklab.kpi.kpi import (
    KPI_DEFINITIONS,
    # Asset Quality
    allowance_coverage_ratio,
    book_value_per_share,
    # Aggregator
    calculate_all_kpis,
    # Valuation
    earnings_per_share,
    efficiency_ratio,
    # Capital & Leverage
    equity_to_assets,
    leverage_ratio,
    # Liquidity
    loan_to_deposit_ratio,
    net_charge_off_ratio,
    net_interest_margin,
    pre_provision_net_revenue,
    price_to_book,
    price_to_earnings,
    price_to_tangible_book,
    qoq_growth,
    return_on_assets,
    # Profitability
    return_on_equity,
    tangible_book_value_per_share,
    tangible_equity_ratio,
    # Growth
    yoy_growth,
)

__all__ = [
    "return_on_equity",
    "return_on_assets",
    "net_interest_margin",
    "efficiency_ratio",
    "pre_provision_net_revenue",
    "earnings_per_share",
    "book_value_per_share",
    "tangible_book_value_per_share",
    "price_to_book",
    "price_to_earnings",
    "price_to_tangible_book",
    "equity_to_assets",
    "tangible_equity_ratio",
    "leverage_ratio",
    "allowance_coverage_ratio",
    "net_charge_off_ratio",
    "loan_to_deposit_ratio",
    "yoy_growth",
    "qoq_growth",
    "calculate_all_kpis",
    "KPI_DEFINITIONS",
]
