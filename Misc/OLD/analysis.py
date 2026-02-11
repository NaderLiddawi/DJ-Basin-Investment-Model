"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Analysis Functions
==================
Monte Carlo simulation, scenario analysis, and percentile analysis.
"""

import numpy as np
from config import CO_INVEST_MM, NUM_SIMULATIONS
from yield_curve import generate_hyperbolic_yield_curve
from price_simulation import simulate_commodity_prices
from risk_models import simulate_timing_risk, simulate_decline_curve_risk
from cash_flows import build_cash_flows, calculate_irr, calculate_roi, calculate_payback


def run_monte_carlo(num_sims=None, price_sims=None):
    """
    Run Monte Carlo simulation across price, timing, and decline curve risks.
    
    Args:
        num_sims: Number of simulations (default: from config)
        price_sims: Pre-simulated prices (if None, will simulate)
    
    Returns:
        dict: Simulation results containing:
            - sim_irrs: Array of IRRs
            - sim_rois: Array of ROIs
            - sim_profits: Array of total profits
            - sim_delays: Array of delays
            - sim_b_factors: Array of b-factors
            - sim_prices: Array of average prices
            - risk_attribution: Dict of loss causes
    """
    if num_sims is None:
        num_sims = NUM_SIMULATIONS
    
    # Simulate commodity prices if not provided
    if price_sims is None:
        price_sims = simulate_commodity_prices(years=10, sims=num_sims)
    
    # Storage arrays
    sim_irrs = []
    sim_rois = []
    sim_profits = []
    sim_delays = []
    sim_max_dev_delays = []
    sim_b_factors = []
    sim_prices = []
    risk_attribution = {'price': 0, 'timing': 0, 'decline': 0, 'combined': 0, 'other': 0}
    
    for i in range(num_sims):
        # Get price path for this simulation
        price_path = price_sims['blended_paths'][i]
        avg_price = price_sims['blended_avg'][i]
        sim_prices.append(avg_price)
        
        # Simulate timing delay
        delay, _, max_dev_delay = simulate_timing_risk(stochastic=True)
        sim_delays.append(delay)
        sim_max_dev_delays.append(max_dev_delay)
        
        # Simulate decline curve
        b_factor, Di, _ = simulate_decline_curve_risk(stochastic=True)
        sim_b_factors.append(b_factor)
        
        # Generate stressed yield curve
        stressed_yields = generate_hyperbolic_yield_curve(
            b_factor=b_factor,
            Di=Di,
            delay_years=delay
        )
        
        # Build cash flows and calculate metrics
        cfs = build_cash_flows(stressed_yields, price_path)
        irr = calculate_irr(cfs)
        roi = calculate_roi(cfs)
        profit = sum(cfs)
        
        sim_irrs.append(irr if irr else -1.0)
        sim_rois.append(roi)
        sim_profits.append(profit)
        
        # Attribute losses to risk factors
        if profit < 0:
            factors = []
            if avg_price < 0.80:
                factors.append('price')
            if delay > 0.3:
                factors.append('timing')
            if b_factor < 0.70:
                factors.append('decline')
            
            if len(factors) == 0:
                risk_attribution['other'] += 1
            elif len(factors) == 1:
                risk_attribution[factors[0]] += 1
            else:
                risk_attribution['combined'] += 1
    
    return {
        'sim_irrs': np.array(sim_irrs),
        'sim_rois': np.array(sim_rois),
        'sim_profits': np.array(sim_profits),
        'sim_delays': np.array(sim_delays),
        'sim_max_dev_delays': np.array(sim_max_dev_delays),
        'sim_b_factors': np.array(sim_b_factors),
        'sim_prices': np.array(sim_prices),
        'risk_attribution': risk_attribution,
        'price_sims': price_sims
    }


def get_percentile_input_ranges(percentile, sim_irrs, sim_prices, sim_delays, sim_b_factors, band_pct=2):
    """
    Get min/max range of inputs near each percentile.
    
    This reveals the diversity of input combinations that produce similar IRRs.
    
    Args:
        percentile: Target percentile (0-100)
        sim_irrs: Array of simulated IRRs
        sim_prices: Array of average prices
        sim_delays: Array of delays
        sim_b_factors: Array of b-factors
        band_pct: Percentile band width (±)
    
    Returns:
        dict: Statistics for simulations near the target percentile
    """
    target_irr = np.percentile(sim_irrs, percentile)
    
    # Find simulations within band
    lower_pct = max(0, percentile - band_pct)
    upper_pct = min(100, percentile + band_pct)
    lower_irr = np.percentile(sim_irrs, lower_pct)
    upper_irr = np.percentile(sim_irrs, upper_pct)
    
    mask = (sim_irrs >= lower_irr) & (sim_irrs <= upper_irr)
    
    if np.sum(mask) == 0:
        closest_idx = np.argmin(np.abs(sim_irrs - target_irr))
        mask = np.zeros(len(sim_irrs), dtype=bool)
        mask[closest_idx] = True
    
    return {
        'irr': target_irr,
        'price_min': np.min(sim_prices[mask]),
        'price_max': np.max(sim_prices[mask]),
        'price_avg': np.mean(sim_prices[mask]),
        'delay_min': np.min(sim_delays[mask]),
        'delay_max': np.max(sim_delays[mask]),
        'delay_avg': np.mean(sim_delays[mask]),
        'b_min': np.min(sim_b_factors[mask]),
        'b_max': np.max(sim_b_factors[mask]),
        'b_avg': np.mean(sim_b_factors[mask]),
        'n_sims': np.sum(mask)
    }


def run_scenario_analysis(base_yields):
    """
    Run deterministic scenario analysis for various stress cases.
    
    Args:
        base_yields: Base case yield curve
    
    Returns:
        dict: Results for each scenario category
    """
    results = {
        'price_scenarios': {},
        'timing_scenarios': {},
        'decline_scenarios': {},
        'combined_scenarios': {}
    }
    
    # Price scenarios
    price_scenarios = {
        'Strip (Base)':           [1.00] * 10,
        'Upside ($70/$3.25)':     [1.10] * 10,
        'Mild Stress (-15%)':     [0.85] * 10,
        'Severe Stress (-30%)':   [0.70] * 10,
        'Gas Collapse':           [1.0, 1.0, 0.8, 0.6, 0.6, 0.7, 0.8, 0.9, 1.0, 1.0],
        '2020-Style Crash':       [0.50, 0.60, 0.75, 0.85, 0.95, 1.0, 1.0, 1.0, 1.0, 1.0],
        'Sustained Low ($50/bbl)': [0.71] * 10,
    }
    
    for name, price_path in price_scenarios.items():
        cfs = build_cash_flows(base_yields, price_path)
        results['price_scenarios'][name] = {
            'irr': calculate_irr(cfs),
            'roi': calculate_roi(cfs),
            'payback': calculate_payback(cfs)
        }
    
    # Timing scenarios
    timing_scenarios = {
        'No Delay (Base)':        0,
        '3-Month Delay':          0.25,
        '6-Month Delay':          0.5,
        '1-Year Delay':           1,
        '2-Year Delay':           2,
        '3-Year Delay (Severe)':  3,
    }
    
    for name, delay in timing_scenarios.items():
        delayed_yields = generate_hyperbolic_yield_curve(delay_years=delay)
        cfs = build_cash_flows(delayed_yields, [1.0] * 10)
        results['timing_scenarios'][name] = {
            'irr': calculate_irr(cfs),
            'roi': calculate_roi(cfs),
            'payback': calculate_payback(cfs)
        }
    
    # Decline curve scenarios
    decline_scenarios = {
        'Type Curve (Base)':       (0.9, 0.25),
        'Slight Steepening':       (0.75, 0.28),
        'Moderate Steepening':     (0.6, 0.30),
        'Severe Steepening':       (0.45, 0.35),
        'Near-Exponential':        (0.3, 0.40),
        'Better Than Expected':    (1.1, 0.18),
    }
    
    for name, (b_factor, Di) in decline_scenarios.items():
        steep_yields = generate_hyperbolic_yield_curve(b_factor=b_factor, Di=Di)
        cfs = build_cash_flows(steep_yields, [1.0] * 10)
        results['decline_scenarios'][name] = {
            'irr': calculate_irr(cfs),
            'roi': calculate_roi(cfs),
            'yield_sum': sum(steep_yields),
            'b_factor': b_factor
        }
    
    # Combined stress scenarios
    combined_scenarios = {
        'Mild Price + Timing':            {'price': 0.85, 'delay': 1, 'b': 0.9},
        'Moderate Price + Steep Decline': {'price': 0.80, 'delay': 0, 'b': 0.6},
        'Price + Timing + Decline':       {'price': 0.80, 'delay': 1, 'b': 0.7},
        'Severe Combined Stress':         {'price': 0.70, 'delay': 2, 'b': 0.5},
        'Worst Case (All Risks)':         {'price': 0.60, 'delay': 2, 'b': 0.4},
        'Upside Combined':                {'price': 1.15, 'delay': 0, 'b': 1.0},
    }
    
    for name, params in combined_scenarios.items():
        combined_yields = generate_hyperbolic_yield_curve(
            b_factor=params['b'],
            delay_years=params['delay']
        )
        price_path = [params['price']] * 10
        cfs = build_cash_flows(combined_yields, price_path)
        results['combined_scenarios'][name] = {
            'irr': calculate_irr(cfs),
            'roi': calculate_roi(cfs),
            'payback': calculate_payback(cfs)
        }
    
    return results


def run_breakeven_analysis(base_yields):
    """
    Find breakeven price factors.
    
    Args:
        base_yields: Base case yield curve
    
    Returns:
        dict: Breakeven analysis results
    """
    results = {}
    
    # Find 0% IRR breakeven
    for factor in np.arange(1.0, 0.0, -0.01):
        cfs = build_cash_flows(base_yields, [factor] * 10)
        irr = calculate_irr(cfs)
        if irr is not None and irr < 0:
            results['breakeven_factor'] = factor + 0.01
            results['breakeven_price'] = 70 * (factor + 0.01)
            break
    
    # Find 10% IRR floor
    for factor in np.arange(1.0, 0.0, -0.01):
        cfs = build_cash_flows(base_yields, [factor] * 10)
        irr = calculate_irr(cfs)
        if irr is not None and irr < 0.10:
            results['irr_10_floor_factor'] = factor + 0.01
            results['irr_10_floor_price'] = 70 * (factor + 0.01)
            break
    
    return results


def validate_timing_delays():
    """
    Validate that timing delays produce monotonically decreasing IRR.
    
    Returns:
        tuple: (passed, results_list)
    """
    delays = [0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
    results = []
    prev_irr = None
    passed = True
    
    for d in delays:
        y = generate_hyperbolic_yield_curve(delay_years=d)
        cfs = build_cash_flows(y, [1.0] * 10)
        irr = calculate_irr(cfs)
        
        is_valid = (prev_irr is None or irr <= prev_irr + 0.001)
        if not is_valid:
            passed = False
        
        results.append({
            'delay': d,
            'irr': irr,
            'valid': is_valid
        })
        prev_irr = irr
    
    return passed, results
