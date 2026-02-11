"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Risk Models
===========
Simulates timing delays and decline curve steepening risks.
"""

import numpy as np
from config import (
    TIMING_RISK_PARAMS, RETURN_CONTRIBUTION,
    DECLINE_CURVE_PARAMS
)


def simulate_timing_risk(stochastic=True):
    """
    Simulate development timing delays across reserve categories.
    
    Delays are weighted by return contribution (not NAV) to better
    reflect impact on IRR. PDP contributes most to returns but has
    zero delay risk since wells are already producing.
    
    Args:
        stochastic: If True, use random draws; if False, return zero delay
    
    Returns:
        tuple: (weighted_delay, category_delays, max_dev_delay)
            - weighted_delay: Return-contribution-weighted average delay
            - category_delays: Dict of delays by category
            - max_dev_delay: Maximum delay among development categories
    """
    category_delays = {}
    
    for category, params in TIMING_RISK_PARAMS.items():
        if stochastic and np.random.random() < params['delay_prob']:
            if params['max_delay_years'] > 0:
                # Uniform distribution from 3 months to max
                delay = np.random.uniform(0.25, params['max_delay_years'])
            else:
                delay = 0
        else:
            delay = 0
        category_delays[category] = delay
    
    # Weight by return contribution (not NAV)
    total_contribution = sum(RETURN_CONTRIBUTION.values())
    weighted_delay = sum(
        category_delays[cat] * RETURN_CONTRIBUTION[cat] / total_contribution
        for cat in category_delays
    )
    
    # Track max delay in development categories (for reporting)
    dev_categories = ['DUC', 'Permit', 'APD', 'Undeveloped']
    max_dev_delay = max(category_delays.get(cat, 0) for cat in dev_categories)
    
    return weighted_delay, category_delays, max_dev_delay


def simulate_decline_curve_risk(stochastic=True):
    """
    Simulate decline curve steepening risk.
    
    The b-factor (hyperbolic exponent) determines decline curve shape:
        b = 0: Exponential decline (steepest)
        b = 0.5: Moderate hyperbolic
        b = 1.0: Harmonic decline (flattest)
        b > 1.0: Flatter than harmonic
    
    DJ Basin Niobrara/Codell typically: b = 0.8-1.1
    
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


def get_timing_risk_statistics(sim_delays, sim_max_dev_delays):
    """
    Calculate summary statistics for timing risk simulations.
    
    Args:
        sim_delays: Array of weighted delays
        sim_max_dev_delays: Array of max development delays
    
    Returns:
        dict: Timing risk statistics
    """
    return {
        'avg_delay': np.mean(sim_delays),
        'std_delay': np.std(sim_delays),
        'max_delay': np.max(sim_delays),
        'avg_max_dev_delay': np.mean(sim_max_dev_delays),
        'pct_over_half_year': np.mean(sim_delays > 0.5),
        'pct_over_one_year': np.mean(sim_delays > 1.0)
    }


def get_decline_curve_statistics(sim_b_factors):
    """
    Calculate summary statistics for decline curve simulations.
    
    Args:
        sim_b_factors: Array of b-factors
    
    Returns:
        dict: Decline curve statistics
    """
    return {
        'avg_b_factor': np.mean(sim_b_factors),
        'std_b_factor': np.std(sim_b_factors),
        'pct_steep': np.mean(sim_b_factors < 0.7),
        'pct_severe': np.mean(sim_b_factors < 0.5)
    }
