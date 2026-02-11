"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Yield Curve Generation
======================
Generates cash flow yield curves using Arps hyperbolic decline.
"""

import numpy as np
from config import (
    YIELD_Y1, YIELD_Y2, YIELD_Y3, AVG_10Y_YIELD,
    DECLINE_CURVE_PARAMS
)

# Global variable to store base case yield sum for relative scaling
BASE_YIELD_SUM = None


def generate_hyperbolic_yield_curve(b_factor=None, Di=None, calibrate_base=False):
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
        Di: Initial decline rate at Year 3 is about 0.25. It is about 0.6-0.8 for Year 0, but we will not use that since we are modeling the tail at Years 3-10
        calibrate_base: If True, calibrate to deck target; if False, use natural decline
    
    Returns:
        numpy.ndarray: 10-year yield curve as decimal yields
    """
    global BASE_YIELD_SUM
    
    # Use defaults if not specified
    if b_factor is None:
        b_factor = DECLINE_CURVE_PARAMS['base_b_factor']
    if Di is None:
        Di = DECLINE_CURVE_PARAMS['base_Di'] # 0.25 is about the shale decline rate at Year 3 (Year 0 decline rate is much higher but we will not use that since we are modeling the tail decline from Year 3)

    # Years 1-3: Use explicit yields from deck
    base_yields = [YIELD_Y1, YIELD_Y2, YIELD_Y3]


    # Years 4-10: Generate using hyperbolic decline from Year 3
    q3 = YIELD_Y3

    tail_yields = [] # Empty list to store yields for Years 4-10

    for t in range(1, 8):  # t=1 to 7 corresponds to Years 4-10
        yield_t = q3 / ((1 + b_factor * Di * t) ** (1 / b_factor))
        # Floor at 3%: Represents economic limit (wells shut-in below this)
        # This only activates in extreme scenarios (b < 0.2) outside normal simulation range
        tail_yields.append(max(yield_t, 0.03)) # list of 7 yields
    
    # Boolean scaling logic: only calibrate base case to deck target
    is_base_case = (
        b_factor == DECLINE_CURVE_PARAMS['base_b_factor'] and 
        Di == DECLINE_CURVE_PARAMS['base_Di']
    )
    
    if is_base_case or calibrate_base:
        # Calibrate to deck's 1.86x (18.6% * 10) target
        target_sum = AVG_10Y_YIELD * 10  # 18.6 * 10 = 1.86
        known_sum = sum(base_yields)      # ~0.786 (for Years 1-3)
        remaining_target = target_sum - known_sum  # ~1.074 (Difference between 1.86x and yields from known Year 1-3 )
        
        tail_sum = sum(tail_yields) # Sum of yields for Years 4-10 = 0.924

        if tail_sum > 0:
            scale = remaining_target / tail_sum  # (1.074 / 0.924 ) = 1.16
            print(f"[DEBUG] Yield Curve Scaling Factor: {scale:.4f}x from {remaining_target:.4f} divided by {tail_sum:.4f}")

            tail_yields = [y * scale for y in tail_yields]
        
        BASE_YIELD_SUM = sum(base_yields + tail_yields)
    
    return np.array(base_yields + tail_yields) # We later perturb and stress test around this 18.6%-average yield curve to add shocks/volatility on the curve (see stochastic_decline_curve.py)


def get_base_yield_sum():
    """Return the base case yield sum (for reference)."""
    return BASE_YIELD_SUM
