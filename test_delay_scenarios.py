"""
DELAY SCENARIO TEST SCRIPT
"""

import sys
import os
import io
import contextlib
import numpy as np

# Add project path for imports
sys.path.insert(0, '/mnt/project')

# =============================================================================
# IMPORTS
# =============================================================================
from config import (
    CO_INVEST_MM,
    GA_RATE,
    NAV_BY_CATEGORY,
    TOTAL_NAV_MM,
    DECLINE_CURVE_PARAMS,
    NUM_SIMULATIONS,
    RANDOM_SEED,
)
from yield_curve import generate_hyperbolic_yield_curve
from commodity_price_simulation import simulate_commodity_prices
from cash_flows import (
    build_cash_flows,        # REUSED: No need to duplicate cash flow logic
    calculate_irr,
    calculate_roi,
    calculate_payback,
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def quiet_yield_curve(*args, **kwargs):
    """
    Generate yield curve without printing debug output.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return generate_hyperbolic_yield_curve(*args, **kwargs)

# =============================================================================
# CONSTANTS WITH CLEAR NAMING
# =============================================================================

# What percentage of NAV is already producing (no delay risk)?
PDP_SHARE = NAV_BY_CATEGORY["PDP"] / TOTAL_NAV_MM  # ~66%

# What percentage requires future development (subject to delay risk)?
NON_PDP_SHARE = 1 - PDP_SHARE  # ~34%

# =============================================================================
# DELAY FUNCTION 1: NON-PDP ONLY (CORRECT APPROACH)
# =============================================================================

def delay_non_pdp_yields(base_yields, delay_years):
    """
    Shift ONLY the Non-PDP portion of yields by a specified delay.

    HOW IT WORKS (Linear Interpolation):
    ------------------------------------
    For a 1.5-year delay:
    - Year 1's non-PDP production appears at Year 2.5
    - This is split: 50% in Year 2, 50% in Year 3

    Year 0: [NOTHING - production hasn't arrived yet]
    Year 1: [NOTHING - still waiting]
    Year 2: 50% of Year 1's production (arrived at 2.5, partially in Year 2)
    Year 3: 50% of Year 1 + 50% of Year 2
    ... and so on

    EDGE CASES:
    -----------
    - delay_years = 0     → Return original curve unchanged
    - delay_years >= 10   → All non-PDP lost; only PDP remains
    - delay_years = 9.5   → Only Year 1's production (partially) arrives at Year 10

    """
    yields = np.array(base_yields)

    # -------------------------------------------------------------------------
    # EDGE CASE: No delay → return original
    # -------------------------------------------------------------------------
    if delay_years <= 0:
        return yields.copy()

    # -------------------------------------------------------------------------
    # EDGE CASE: Delay exceeds horizon → all non-PDP is lost
    # -------------------------------------------------------------------------
    if delay_years >= 10:
        # Only PDP portion survives (66% of each year's yield)
        return yields * PDP_SHARE

    # -------------------------------------------------------------------------
    # SPLIT: Separate PDP (unaffected) from Non-PDP (to be delayed)
    # -------------------------------------------------------------------------
    pdp_yields = yields * PDP_SHARE           # These flow unchanged
    non_pdp_yields = yields * NON_PDP_SHARE   # These get shifted

    # -------------------------------------------------------------------------
    # DECOMPOSE DELAY: Integer years + Fractional year
    # -------------------------------------------------------------------------
    # Example: 1.5 years → whole_years=1, fractional_year=0.5
    whole_years = int(np.floor(delay_years))
    fractional_year = delay_years % 1

    # -------------------------------------------------------------------------
    # BUILD DELAYED NON-PDP CURVE
    # -------------------------------------------------------------------------
    delayed_non_pdp = np.zeros(10)

    '''
    target_year is the year on the delayed curve (0..9).
    
    source_year is the original year whose production is arriving (after shifting).
    '''
    for target_year in range(10):
        # Which source year's production arrives at this target year?
        source_year = target_year - whole_years

        # CASE 1: Target year is before any delayed production arrives
        if source_year < 0:
            delayed_non_pdp[target_year] = 0.0
            continue

        # CASE 2: First year receiving delayed production
        # Only partial contribution from source_year=0
        if source_year == 0:
            # Fraction (1 - fractional_year) of Year 0's production arrives
            fraction_arriving = 1.0 - fractional_year
            delayed_non_pdp[target_year] = non_pdp_yields[0] * fraction_arriving
            continue

        # CASE 3: Normal interpolation between two source years
        # Part of source_year arrives, plus spillover from (source_year - 1)
        current_year_contribution = 0.0
        previous_year_spillover = 0.0

        # Current source year's contribution (if within bounds)
        if source_year < len(non_pdp_yields):
            current_year_contribution = non_pdp_yields[source_year] * (1.0 - fractional_year)

        # Previous source year's spillover (if within bounds)
        if (source_year - 1) < len(non_pdp_yields):
            previous_year_spillover = non_pdp_yields[source_year - 1] * fractional_year

        delayed_non_pdp[target_year] = current_year_contribution + previous_year_spillover

    # -------------------------------------------------------------------------
    # COMBINE: PDP (unchanged) + Delayed Non-PDP
    # -------------------------------------------------------------------------
    return pdp_yields + delayed_non_pdp

# =============================================================================
# DELAY FUNCTION 2: ALL YIELDS (INCORRECT - FOR COMPARISON ONLY)
# =============================================================================

def delay_all_yields(base_yields, delay_years):
    """
    Shift the ENTIRE yield curve by a specified delay.

    - This approach incorrectly penalizes the producing asset base

    IMPLEMENTATION DETAILS:
    ----------------------
    - During delay period: Uses a 5% baseline yield (minimal ongoing production)
    - After delay: Applies yields with 85% ramp factor
    - These numbers are illustrative; they have no engineering basis

    """
    yields = np.array(base_yields)

    if delay_years <= 0:
        return yields.copy()

    if delay_years >= 10:
        # Economic floor: minimum viable yield
        return np.full(10, 0.03)

    # -------------------------------------------------------------------------
    # CONFIGURATION (Illustrative - not engineering-based)
    # -------------------------------------------------------------------------
    BASELINE_YIELD_DURING_DELAY = 0.05   # 5% - represents minimal ongoing activity
    POST_DELAY_EFFICIENCY_FACTOR = 0.85  # 85% - assumes some production loss

    whole_years = int(np.floor(delay_years))
    fractional_year = delay_years % 1

    delayed_yields = np.zeros(10)

    for target_year in range(10):
        # During full delay years: only baseline production
        if target_year < whole_years:
            delayed_yields[target_year] = BASELINE_YIELD_DURING_DELAY

        # Transition year: blend baseline with ramped production
        elif target_year == whole_years:
            ramped_first_year = yields[0] * POST_DELAY_EFFICIENCY_FACTOR
            delayed_yields[target_year] = (
                BASELINE_YIELD_DURING_DELAY * fractional_year +
                ramped_first_year * (1.0 - fractional_year)
            )

        # After delay: shifted and ramped production
        else:
            source_year = target_year - whole_years
            current_contribution = 0.0
            previous_spillover = 0.0

            if source_year < len(yields):
                current_contribution = yields[source_year] * POST_DELAY_EFFICIENCY_FACTOR * (1.0 - fractional_year)

            if (source_year - 1) >= 0 and (source_year - 1) < len(yields):
                previous_spillover = yields[source_year - 1] * POST_DELAY_EFFICIENCY_FACTOR * fractional_year

            delayed_yields[target_year] = current_contribution + previous_spillover

    return delayed_yields


# =============================================================================
# DELAY FUNCTION 3: UNIFORM YIELD HAIRCUT (ALTERNATIVE APPROACH)
# =============================================================================

def apply_yield_haircut(base_yields, haircut_percentage):
    """
    Apply a uniform percentage reduction to all yields.

    This is an ALTERNATIVE to explicit delays. Instead of modeling timing,
    it simply reduces expected production by a flat percentage.

    USE CASE:
    ---------
    - Quick sensitivity analysis: "What if we're 15% wrong on volumes?"
    - Equivalent to assuming some percentage of reserves never gets developed
    - Simpler than timing-based delays; captures volume risk, not timing risk

    RELATIONSHIP TO DISCOUNT RATES:
    ------------------------------
    A 15% yield haircut is roughly equivalent to adding ~2-3% to the discount
    rate, depending on the timing of cash flows.

    Parameters
    ----------
    base_yields : array-like
        10-element array of annual yields
    haircut_percentage : float
        Percentage to reduce yields (0.15 = 15% reduction)

    Returns
    -------
    numpy.ndarray
        Reduced yield curve
    """
    return np.array(base_yields) * (1.0 - haircut_percentage)


# =============================================================================
# MONTE CARLO SIMULATION WITH DELAYS
# =============================================================================

def run_monte_carlo_with_delay(
    delay_function,
    delay_parameter,
    num_simulations,
    price_simulations
):
    """
    Run Monte Carlo simulation with a specified delay transformation.

    WHAT THIS DOES:
    --------------
    1. For each simulation path:
       a. Draw a random b-factor (decline curve steepening)
       b. Generate base yield curve with that b-factor
       c. Apply the delay transformation to the yield curve
       d. Apply the corresponding price path
       e. Calculate IRR, profit, and payback

    2. Aggregate results across all simulations

    Parameters
    ----------
    delay_function : callable or None
        Function to transform yield curve (e.g., delay_non_pdp_yields)
        If None, uses unmodified base yields
    delay_parameter : float
        Parameter to pass to delay_function (e.g., years of delay)
    num_simulations : int
        Number of Monte Carlo paths
    price_simulations : dict
        Pre-simulated price paths from simulate_commodity_prices()

    Returns
    -------
    tuple of numpy.ndarray
        (irrs, profits, paybacks) - each of length num_simulations
    """
    irrs = []
    profits = []
    paybacks = []

    for sim_index in range(num_simulations):
        # ---------------------------------------------------------------------
        # STEP 1: Random decline curve (b-factor)
        # ---------------------------------------------------------------------
        b_factor_shock = np.random.normal(0, DECLINE_CURVE_PARAMS["b_factor_volatility"])
        b_factor = DECLINE_CURVE_PARAMS["base_b_factor"] + b_factor_shock
        b_factor = np.clip(b_factor, 0.3, 1.2)  # Physical bounds

        # ---------------------------------------------------------------------
        # STEP 2: Generate base yield curve
        # ---------------------------------------------------------------------
        base_yields = quiet_yield_curve(b_factor=b_factor)

        # ---------------------------------------------------------------------
        # STEP 3: Apply delay transformation (if any)
        # ---------------------------------------------------------------------
        if delay_function is not None:
            modified_yields = delay_function(base_yields, delay_parameter)
        else:
            modified_yields = base_yields

        # ---------------------------------------------------------------------
        # STEP 4: Get price path for this simulation
        # ---------------------------------------------------------------------
        price_path = price_simulations["blended_paths"][sim_index]

        # ---------------------------------------------------------------------
        # STEP 5: Build cash flows and calculate metrics
        # ---------------------------------------------------------------------
        cash_flows = build_cash_flows(modified_yields, price_path, include_ga=True)

        irr = calculate_irr(cash_flows)
        payback = calculate_payback(cash_flows)
        profit = sum(cash_flows)

        # Store results (handle None values)
        irrs.append(irr if irr is not None else -1.0)
        profits.append(profit)
        paybacks.append(payback if payback is not None else 99.0)  # 99 = never recovered

    return np.array(irrs), np.array(profits), np.array(paybacks)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def format_irr(value):
    """Format IRR for display."""
    if value is None or value <= -0.99:
        return "  N/A  "
    return f"{value:7.1%}"

def format_roi(value):
    """Format ROI for display."""
    if value is None:
        return " N/A  "
    return f"{value:6.2f}x"

def format_payback(value):
    """Format payback period for display."""
    if value is None or value >= 10:
        return " >10yr "
    return f"{value:6.1f}yr"


def print_table(headers, rows, title=None):
    """Print a formatted ASCII table."""
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        cells = [str(row[i]) for row in rows if i < len(row)]
        max_cell_width = max(len(cell) for cell in cells) if cells else 0
        col_widths.append(max(len(str(header)), max_cell_width) + 2)

    # Build separator line
    separator = "+" + "+".join("-" * w for w in col_widths) + "+"

    # Print title and header
    if title:
        print(f"\n{title}")
    print(separator)
    header_row = "|" + "|".join(f"{str(h):^{w}}" for h, w in zip(headers, col_widths)) + "|"
    print(header_row)
    print(separator)

    # Print data rows
    for row in rows:
        line = "|" + "|".join(f"{str(cell):^{w}}" for cell, w in zip(row, col_widths)) + "|"
        print(line)
    print(separator)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run comprehensive delay scenario analysis."""

    np.random.seed(RANDOM_SEED)

    # =========================================================================
    # HEADER
    # =========================================================================
    print("=" * 95)
    print("DELAY SCENARIO ANALYSIS (v3 - Educational/Sensitivity)")
    print("=" * 95)
    print()
    print("IMPORTANT: This analysis is for SENSITIVITY UNDERSTANDING only.")
    print("The deck's NAV ($1,052MM) already embeds timing risk via PV-10 to PV-20.")
    print("Adding explicit delays would DOUBLE-COUNT this risk.")
    print()
    print(f"Reserve Mix: PDP = {PDP_SHARE:.1%} (producing) | Non-PDP = {NON_PDP_SHARE:.1%} (development)")

    # =========================================================================
    # SECTION 1: DETERMINISTIC SCENARIOS
    # =========================================================================
    print("\n" + "=" * 95)
    print("SECTION 1: DETERMINISTIC SCENARIOS (Strip Pricing = 1.0x)")
    print("=" * 95)

    base_yields = quiet_yield_curve()
    strip_prices = [1.0] * 10  # 100% of strip for all years
    delay_values = [0.0, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 2.50, 3.00]

    # -------------------------------------------------------------------------
    # Table 1A: IRR Comparison
    # -------------------------------------------------------------------------
    scenarios = [
        ("Baseline (No Delay)", None),
        ("Non-PDP Only (Correct)", delay_non_pdp_yields),
        ("All Yields (Wrong)", delay_all_yields),
    ]

    for metric_name, calc_func, fmt_func in [
        ("IRR", calculate_irr, format_irr),
        ("Payback", calculate_payback, format_payback),
        ("ROI", calculate_roi, format_roi),
    ]:
        rows = []
        for scenario_name, delay_func in scenarios:
            row = [scenario_name]

            if delay_func is None:
                # Baseline: no delay, same value across all columns
                cfs = build_cash_flows(base_yields, strip_prices)
                val = fmt_func(calc_func(cfs))
                row.extend([val] * len(delay_values))
            else:
                # Apply delay for each delay value
                for delay in delay_values:
                    modified = delay_func(base_yields, delay)
                    cfs = build_cash_flows(modified, strip_prices)
                    row.append(fmt_func(calc_func(cfs)))

            rows.append(row)

        headers = ["Scenario"] + [f"{d:.2f}yr" for d in delay_values]
        print_table(headers, rows, title=f"[1] {metric_name} by Delay Duration")

    # -------------------------------------------------------------------------
    # Table 1D: Yield Haircut Alternative
    # -------------------------------------------------------------------------
    rows_haircut = []
    for haircut in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
        modified = apply_yield_haircut(base_yields, haircut)
        cfs = build_cash_flows(modified, strip_prices)
        rows_haircut.append([
            f"{int(haircut * 100):2d}%",
            format_irr(calculate_irr(cfs)),
            format_roi(calculate_roi(cfs)),
            format_payback(calculate_payback(cfs)),
            f"{sum(modified):.3f}x",
        ])

    print_table(
        ["Haircut", "IRR", "ROI", "Payback", "10Y Sum"],
        rows_haircut,
        title="[2] Yield Haircut Alternative (Volume Risk, Not Timing)"
    )

    # -------------------------------------------------------------------------
    # Table 1E: Detailed Non-PDP Analysis
    # -------------------------------------------------------------------------
    rows_detailed = []
    for delay in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
        modified = delay_non_pdp_yields(base_yields, delay)
        cfs = build_cash_flows(modified, strip_prices)
        rows_detailed.append([
            f"{delay:.1f}yr",
            "Non-PDP",
            format_irr(calculate_irr(cfs)),
            format_roi(calculate_roi(cfs)),
            format_payback(calculate_payback(cfs)),
            f"{modified[0]:.1%}",  # Year 1 yield
            f"{modified[9]:.1%}",  # Year 10 yield
            f"{sum(modified):.2f}x",
        ])

    print_table(
        ["Delay", "Method", "IRR", "ROI", "Payback", "Y1 Yld", "Y10 Yld", "Sum"],
        rows_detailed,
        title="[3] Non-PDP Delay: Yield Curve Evolution"
    )

    # =========================================================================
    # SECTION 2: MONTE CARLO SIMULATION
    # =========================================================================
    print("\n" + "=" * 95)
    print(f"SECTION 2: MONTE CARLO ({NUM_SIMULATIONS:,} Simulations)")
    print("=" * 95)

    print("\nSimulating commodity prices...")
    price_sims = simulate_commodity_prices(years=10, sims=NUM_SIMULATIONS)

    # Define scenarios to test
    mc_scenarios = [
        ("Baseline", None, 0.0),
        ("Non-PDP 0.5yr Delay", delay_non_pdp_yields, 0.5),
        ("Non-PDP 1.0yr Delay", delay_non_pdp_yields, 1.0),
        ("Non-PDP 1.5yr Delay", delay_non_pdp_yields, 1.5),
        ("Non-PDP 2.0yr Delay", delay_non_pdp_yields, 2.0),
        ("All Yields 1yr (Wrong)", delay_all_yields, 1.0),
        ("15% Yield Haircut", apply_yield_haircut, 0.15),
    ]

    results = {}
    for name, func, param in mc_scenarios:
        print(f"  Running: {name}...")
        irrs, profits, paybacks = run_monte_carlo_with_delay(func, param, NUM_SIMULATIONS, price_sims)
        results[name] = {"irrs": irrs, "profits": profits, "paybacks": paybacks}

    # -------------------------------------------------------------------------
    # Summary Statistics Table
    # -------------------------------------------------------------------------
    rows_summary = []
    for name, data in results.items():
        profits = data["profits"]
        paybacks = data["paybacks"]
        irrs = data["irrs"]

        loss_probability = np.mean(profits < 0)
        avg_loss_if_loss = abs(np.mean(profits[profits < 0])) if loss_probability > 0 else 0.0
        valid_paybacks = paybacks[paybacks < 99]

        rows_summary.append([
            name[:22],
            f"{loss_probability:6.1%}",
            f"${avg_loss_if_loss:5.1f}MM",
            f"{np.median(irrs):6.1%}",
            f"{np.median(valid_paybacks):5.1f}yr" if len(valid_paybacks) > 0 else ">10yr",
        ])

    print_table(
        ["Scenario", "P(Loss)", "Avg Loss", "Med IRR", "Med Payback"],
        rows_summary,
        title="[4] Monte Carlo Summary"
    )

    # -------------------------------------------------------------------------
    # IRR Percentile Distribution
    # -------------------------------------------------------------------------
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    rows_pctl = []

    for name, data in results.items():
        irrs = data["irrs"]
        pct_values = np.percentile(irrs, percentiles)
        rows_pctl.append([name[:18]] + [f"{p:5.1%}" for p in pct_values])

    print_table(
        ["Scenario"] + [f"P{p}" for p in percentiles],
        rows_pctl,
        title="[5] IRR Percentile Distribution"
    )



if __name__ == "__main__":
    main()