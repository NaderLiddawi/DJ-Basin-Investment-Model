"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Yield Curve Generation
======================
Generates cash flow yield curves using Arps hyperbolic decline.
Handles timing delays with economically-grounded Split-Shift-Inflate-Discount model.

CHANGELOG:
- Replaced arbitrary delay penalty with physics-based model
- PDP curve now derived from deck NAV proportions
- Growth component penalized by inflation + opportunity cost
- All parameters traceable to deck data or industry sources
"""

import numpy as np
from config import (
    YIELD_Y1, YIELD_Y2, YIELD_Y3, AVG_10Y_YIELD,
    DECLINE_CURVE_PARAMS, NAV_BY_CATEGORY, TOTAL_NAV_MM,
    PDP_DECLINE_RATE, CAPEX_INFLATION_RATE, OPPORTUNITY_COST_RATE
)

# Global variable to store base case yield sum for relative scaling
BASE_YIELD_SUM = None


def _generate_pdp_curve():
    """
    Generate PDP (Proved Developed Producing) yield curve.
    
    PDP wells are already flowing - their cash flows cannot be delayed.
    This curve represents the "floor" of cash flows during any delay scenario.
    
    Derivation:
        PDP_Y1 = Total_Y1 × (PDP_NAV / Total_NAV)
               = 26.9% × (691 / 1052)
               = 26.9% × 65.7%
               = 17.7%
    
    The PDP curve then declines using harmonic decline at industry-standard
    rates for mature DJ Basin wells (10-15% annual).
    
    Returns:
        numpy.ndarray: 10-year PDP yield curve
    """
    # Derive PDP Year 1 yield from deck NAV proportions
    pdp_nav_share = NAV_BY_CATEGORY['PDP'] / TOTAL_NAV_MM  # ~65.7%
    pdp_y1 = YIELD_Y1 * pdp_nav_share  # ~17.7%
    
    # Generate harmonic decline curve
    # Harmonic: q(t) = q0 / (1 + D*t)
    pdp_curve = np.array([
        pdp_y1 / (1 + PDP_DECLINE_RATE * t) 
        for t in range(10)
    ])
    
    return pdp_curve


def generate_hyperbolic_yield_curve(b_factor=None, Di=None, delay_years=0, calibrate_base=False):
    """
    Generate yield curve using Arps hyperbolic decline.
    
    The Arps hyperbolic decline formula:
        q(t) = q_i / (1 + b * D_i * t)^(1/b)
    
    Where:
        q_i = initial production rate
        D_i = initial decline rate (decimal/year)
        b = hyperbolic exponent (0=exponential, 1=harmonic, 0.3-1.2 typical for shale)
        t = time in years
    
    Args:
        b_factor: Hyperbolic exponent (lower = steeper decline). Default: 0.9
        Di: Initial decline rate. Default: 0.25
        delay_years: Development delay in years (supports fractional)
        calibrate_base: If True, calibrate to deck target; if False, use natural decline
    
    Returns:
        numpy.ndarray: 10-year yield curve as decimal yields
    """
    global BASE_YIELD_SUM
    
    # Use defaults if not specified
    if b_factor is None:
        b_factor = DECLINE_CURVE_PARAMS['base_b_factor']
    if Di is None:
        Di = DECLINE_CURVE_PARAMS['base_Di']

    # Years 1-3: Use explicit yields from deck
    base_yields = [YIELD_Y1, YIELD_Y2, YIELD_Y3]
    
    # Years 4-10: Generate using hyperbolic decline from Year 3
    q3 = YIELD_Y3
    tail_yields = []
    for t in range(1, 8):  # t=1 to 7 corresponds to Years 4-10
        yield_t = q3 / ((1 + b_factor * Di * t) ** (1 / b_factor))
        # Floor at 3%: Represents economic limit (wells shut-in below this)
        # This only activates in extreme scenarios (b < 0.2) outside normal sim range
        tail_yields.append(max(yield_t, 0.03))
    
    # Scaling logic: only calibrate base case to deck target
    is_base_case = (
        b_factor == DECLINE_CURVE_PARAMS['base_b_factor'] and 
        Di == DECLINE_CURVE_PARAMS['base_Di'] and 
        delay_years == 0
    )
    
    if is_base_case or calibrate_base:
        # Calibrate to deck's 1.86x (18.6% * 10) target
        target_sum = AVG_10Y_YIELD * 10  # 1.86
        known_sum = sum(base_yields)      # ~0.786
        remaining_target = target_sum - known_sum  # ~1.074
        
        tail_sum = sum(tail_yields)
        if tail_sum > 0:
            scale = remaining_target / tail_sum
            tail_yields = [y * scale for y in tail_yields]
        
        BASE_YIELD_SUM = sum(base_yields + tail_yields)
    
    base_curve = np.array(base_yields + tail_yields)
    
    # If no delay, return base curve
    if delay_years <= 0:
        return base_curve
    
    # Apply delay with economically-grounded model
    return _apply_delay_to_curve(base_curve, delay_years)


def _apply_delay_to_curve(base_curve, delay_years):
    """
    Apply delay using Volume-Weighted Interpolation (Preserves Mass).
    Prevents the 'Timing Cliff' where fractional delays wipe out Year 1.
    """
    # 1. SETUP PENALTIES
    inflation_factor = (1 + CAPEX_INFLATION_RATE) ** delay_years
    opportunity_factor = (1 + OPPORTUNITY_COST_RATE) ** delay_years
    total_growth_penalty = inflation_factor * opportunity_factor

    # 2. SEPARATE CURVES
    pdp_curve = _generate_pdp_curve()
    pdp_curve = np.minimum(pdp_curve, base_curve)
    growth_curve_base = base_curve - pdp_curve

    # 3. APPLY SHIFT TO GROWTH (Volume Interpolation)
    delayed_growth = np.zeros(10)

    full_years = int(delay_years)
    frac_delay = delay_years - full_years

    # We shift the array right by 'delay_years'
    # Logic: New_Year[i] gets (1-frac) from Old_Year[i] and (frac) from Old_Year[i-1]

    for i in range(10):
        # Contribution from the "Current" overlapping year
        # If delayed 0.25 years, Year 0 gets 75% of Original Year 0
        idx_primary = i - full_years

        # Contribution from the "Previous" overlapping year (the spillover)
        # If delayed 0.25 years, Year 1 gets 25% of Original Year 0 + 75% of Original Year 1
        idx_residue = i - full_years - 1

        val_primary = 0.0
        val_residue = 0.0

        if 0 <= idx_primary < 10:
            val_primary = growth_curve_base[idx_primary] * (1 - frac_delay)

        if 0 <= idx_residue < 10:
            val_residue = growth_curve_base[idx_residue] * frac_delay

        # Sum components and apply penalty
        delayed_growth[i] = (val_primary + val_residue) / total_growth_penalty

    # 4. RECOMBINE
    return pdp_curve + delayed_growth


def get_base_yield_sum():
    """Return the base case yield sum (for reference)."""
    return BASE_YIELD_SUM


def get_pdp_curve():
    """
    Return the PDP curve for external analysis/charting.
    
    Returns:
        numpy.ndarray: 10-year PDP yield curve
    """
    return _generate_pdp_curve()


def get_delay_model_parameters():
    """
    Return delay model parameters for documentation/audit trail.
    
    Returns:
        dict: All parameters used in delay model with sources
    """
    pdp_nav_share = NAV_BY_CATEGORY['PDP'] / TOTAL_NAV_MM
    
    return {
        'pdp_nav_share': pdp_nav_share,
        'pdp_y1_derived': YIELD_Y1 * pdp_nav_share,
        'pdp_decline_rate': PDP_DECLINE_RATE,
        'capex_inflation_rate': CAPEX_INFLATION_RATE,
        'opportunity_cost_rate': OPPORTUNITY_COST_RATE,
        'sources': {
            'pdp_nav_share': 'Deck NAV breakdown: $691MM PDP / $1,052MM Total',
            'pdp_decline_rate': 'Industry standard: Enverus/IHS mature Niobrara 10-15%',
            'capex_inflation_rate': 'BLS PPI Oil & Gas Field Services: 2-4% historical',
            'opportunity_cost_rate': 'LP hurdle rate / required return expectation'
        }
    }
