"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Cash Flow Functions
===================
Builds cash flows and calculates investment metrics (IRR, ROI, payback).
"""

import numpy as np
from config import (
    CO_INVEST_MM, CO_INVEST_SHARE, GA_RATE,
    TOTAL_NAV_MM, REMAINING_RESERVES_PCT
)


def estimate_terminal_value(year_10_price_factor, remaining_reserves_pct=None):
    """
    Estimate Year 10 exit value based on remaining reserves and price environment.
    
    Terminal value is sensitive to:
    1. Commodity price environment at exit
    2. Remaining reserve quantity
    3. M&A market conditions (proxied by NAV multiple)
    
    Args:
        year_10_price_factor: Price factor in Year 10 (1.0 = strip)
        remaining_reserves_pct: Fraction of reserves remaining (default: 15%)
    
    Returns:
        float: Terminal value attributable to co-investor ($MM)
    """
    if remaining_reserves_pct is None:
        remaining_reserves_pct = REMAINING_RESERVES_PCT
    
    remaining_nav = TOTAL_NAV_MM * remaining_reserves_pct
    
    # NAV multiple depends on price environment
    if year_10_price_factor >= 0.9:
        nav_multiple = 0.90
    elif year_10_price_factor >= 0.7:
        nav_multiple = 0.70
    elif year_10_price_factor >= 0.5:
        nav_multiple = 0.50
    else:
        nav_multiple = 0.30

    terminal_value = remaining_nav * nav_multiple * year_10_price_factor
    return terminal_value * CO_INVEST_SHARE


def build_cash_flows(yield_curve, price_factors_by_year, include_ga=True):
    """
    Build cash flow series from yield curve and price factors.
    
    Cash flow calculation:
        Year 0: -Investment
        Years 1-9: Investment × Yield × Price Factor - G&A
        Year 10: Same as above + Terminal Value
    
    Args:
        yield_curve: 10-element array of annual yields (decimal)
        price_factors_by_year: 10-element array of price factors
        include_ga: If True, deduct 75 bps G&A annually
    
    Returns:
        list: 11-element cash flow series [Year 0, Year 1, ..., Year 10]
    """
    cfs = [-CO_INVEST_MM]  # Year 0 investment

    for year, (base_yield, price_factor) in enumerate(zip(yield_curve, price_factors_by_year)):
        # Annual cash flow = Investment × Yield × Price
        annual_cf = CO_INVEST_MM * base_yield * price_factor
        
        # Deduct G&A costs
        if include_ga:
            annual_cf -= CO_INVEST_MM * GA_RATE
        
        # Add terminal value in Year 10
        if year == 9:
            annual_cf += estimate_terminal_value(price_factor)
        
        cfs.append(annual_cf)

    return cfs


def calculate_irr(cfs, max_iterations=100, tolerance=1e-8):
    """
    Calculate Internal Rate of Return using Newton-Raphson method.
    
    IRR is the discount rate that makes NPV = 0:
        Σ(CF_t / (1 + IRR)^t) = 0
    
    Args:
        cfs: Cash flow series starting with Year 0
        max_iterations: Maximum Newton-Raphson iterations
        tolerance: Convergence tolerance
    
    Returns:
        float: IRR as decimal (e.g., 0.169 = 16.9%), or None if no convergence
    """
    def npv(rate, cfs):
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cfs))

    def npv_derivative(rate, cfs):
        return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cfs))

    # Initial guess
    rate = 0.10
    
    for _ in range(max_iterations):
        f = npv(rate, cfs)
        f_prime = npv_derivative(rate, cfs)
        
        if abs(f_prime) < 1e-10:
            break
        
        new_rate = rate - f / f_prime
        
        if abs(new_rate - rate) < tolerance:
            return new_rate
        
        rate = new_rate

    # Return rate if reasonable, else None
    return rate if -0.99 < rate < 2.0 else None


def calculate_roi(cfs):
    """
    Calculate Return on Investment (Multiple of Invested Capital).
    
    ROI = Total Returns / Initial Investment
    
    Args:
        cfs: Cash flow series starting with Year 0
    
    Returns:
        float: ROI multiple (e.g., 1.99 = 1.99x)
    """
    return sum(cfs[1:]) / abs(cfs[0])


def calculate_payback(cfs):
    """
    Calculate payback period with interpolation.
    
    Payback is the time until cumulative cash flows turn positive.
    
    Args:
        cfs: Cash flow series starting with Year 0
    
    Returns:
        float: Payback period in years, or None if never recovered
    """
    cumulative = np.cumsum(cfs)
    
    for t in range(1, len(cumulative)):
        if cumulative[t] >= 0:
            # Interpolate within the year
            fraction = -cumulative[t-1] / cfs[t]
            return (t - 1) + fraction
    
    return None  # Never recovered within period


def calculate_npv(cfs, discount_rate):
    """
    Calculate Net Present Value at given discount rate.
    
    Args:
        cfs: Cash flow series starting with Year 0
        discount_rate: Discount rate as decimal
    
    Returns:
        float: NPV in $MM
    """
    return sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(cfs))
