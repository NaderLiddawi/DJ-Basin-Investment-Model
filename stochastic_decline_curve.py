"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Risk Models
===========
Simulates decline curve steepening risk.
"""

import numpy as np
from config import DECLINE_CURVE_PARAMS


def simulate_decline_curve_risk(stochastic=True):
    """
    Simulate decline curve steepening risk.
    
    The b-factor (hyperbolic exponent) determines decline curve shape:
        b = 0: Exponential decline (steepest)
        b = 0.5: Moderate hyperbolic
        b = 1.0: Harmonic decline (flattest)
        b > 1.0: Flatter than harmonic
    
    DJ Basin typically: b = 0.8-1.1
    
    Args:
        stochastic: If True, use random draws; if False, return base case
    
    Returns:
        tuple: (b_factor, Di, curve_label)
            - b_factor: Hyperbolic exponent
            - Di: Initial decline rate
            - curve_label: Descriptive label for the curve type
    """
    base_b = DECLINE_CURVE_PARAMS['base_b_factor']
    base_Di = DECLINE_CURVE_PARAMS['base_Di']

    if stochastic:
        # Symmetric normal distribution around base case
        b_shock = np.random.normal(0, DECLINE_CURVE_PARAMS['b_factor_volatility'])
        b_factor = np.clip(base_b + b_shock, 0.3, 1.2)
        
        Di_shock = np.random.normal(0, DECLINE_CURVE_PARAMS['Di_volatility'])
        Di = np.clip(base_Di + Di_shock, 0.10, 0.45)

        # Classify the decline curve
        if b_factor < 0.5:
            curve_label = "Severe Steepening"
        elif b_factor < 0.7:
            curve_label = "Moderate Steepening"
        elif b_factor > 1.0:
            curve_label = "Flatter than Expected"
        else:
            curve_label = "Near Type Curve"
    else:
        b_factor = base_b
        Di = base_Di
        curve_label = "Base Case"

    return b_factor, Di, curve_label


def get_decline_curve_statistics(sim_b_factors):
    """
    Calculate summary statistics for decline curve simulations.
    """
    return {
        'avg_b_factor': np.mean(sim_b_factors),
        'std_b_factor': np.std(sim_b_factors),
        'pct_steep': np.mean(sim_b_factors < 0.7),
        'pct_severe': np.mean(sim_b_factors < 0.5)
    }
