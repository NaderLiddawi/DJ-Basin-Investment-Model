"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Price Simulation
================
Simulates commodity prices using mean-reverting Ornstein-Uhlenbeck process.
"""

import numpy as np
from config import PRICE_PARAMS, PRICE_CORRELATION, COMMODITY_MIX


def simulate_commodity_prices(years=10, sims=50000):
    """
    Simulate oil, gas, and NGL prices using mean-reverting O-U process.
    
    The Ornstein-Uhlenbeck process:
        dP_t = θ(μ - P_t)dt + σdW_t
    
    Where:
        θ = speed of mean reversion (higher = faster reversion)
        μ = long-term mean (1.0 = strip pricing)
        σ = volatility
        dW_t = Wiener process (random shock)
    
    Args:
        years: Number of years to simulate (default: 10)
        sims: Number of simulation paths (default: 50,000)
    
    Returns:
        dict: Contains:
            - 'oil': List of 10-year average oil price factors
            - 'gas': List of 10-year average gas price factors
            - 'ngl': List of 10-year average NGL price factors
            - 'blended_avg': List of 10-year average blended price factors
            - 'blended_paths': List of year-by-year blended price paths
    """
    dt = 1.0  # Annual time step
    
    # Cholesky decomposition for correlated random draws
    corr = np.array(PRICE_CORRELATION)
    chol = np.linalg.cholesky(corr)
    
    results = {
        'oil': [],
        'gas': [],
        'ngl': [],
        'blended_avg': [],
        'blended_paths': []
    }
    
    for _ in range(sims):
        # Initialize price paths at 1.0 (strip pricing)
        prices = {
            'oil': [1.0],
            'gas': [1.0],
            'ngl': [1.0]
        }
        
        # Simulate year-by-year prices
        for _ in range(years):
            # Draw correlated random shocks
            z = np.random.normal(0, 1, 3)
            corr_z = chol @ z
            
            # Update each commodity price
            for i, commodity in enumerate(['oil', 'gas', 'ngl']):
                p = PRICE_PARAMS[commodity]
                current_price = prices[commodity][-1]
                
                # O-U dynamics
                drift = p['theta'] * (p['mu'] - current_price) * dt
                diffusion = p['sigma'] * np.sqrt(dt) * corr_z[i]
                
                # Price floor at 0.2 (20% of strip)
                new_price = max(0.2, current_price + drift + diffusion)
                prices[commodity].append(new_price)
        
        # Calculate blended price path (weighted by commodity mix)
        blended_path = []
        for t in range(1, years + 1):
            blended = (
                COMMODITY_MIX['oil'] * prices['oil'][t] +
                COMMODITY_MIX['gas'] * prices['gas'][t] +
                COMMODITY_MIX['ngl'] * prices['ngl'][t]
            )
            blended_path.append(blended)
        
        # Store results
        results['oil'].append(np.mean(prices['oil'][1:]))
        results['gas'].append(np.mean(prices['gas'][1:]))
        results['ngl'].append(np.mean(prices['ngl'][1:]))
        results['blended_avg'].append(np.mean(blended_path))
        results['blended_paths'].append(blended_path)
    
    return results


def get_price_statistics(price_sims):
    """
    Calculate summary statistics for price simulations.
    
    Args:
        price_sims: Output from simulate_commodity_prices()
    
    Returns:
        dict: Statistics for each commodity
    """
    return {
        'oil': {
            'mean': np.mean(price_sims['oil']),
            'std': np.std(price_sims['oil']),
            'min': np.min(price_sims['oil']),
            'max': np.max(price_sims['oil'])
        },
        'gas': {
            'mean': np.mean(price_sims['gas']),
            'std': np.std(price_sims['gas']),
            'min': np.min(price_sims['gas']),
            'max': np.max(price_sims['gas'])
        },
        'ngl': {
            'mean': np.mean(price_sims['ngl']),
            'std': np.std(price_sims['ngl']),
            'min': np.min(price_sims['ngl']),
            'max': np.max(price_sims['ngl'])
        },
        'blended': {
            'mean': np.mean(price_sims['blended_avg']),
            'std': np.std(price_sims['blended_avg']),
            'min': np.min(price_sims['blended_avg']),
            'max': np.max(price_sims['blended_avg'])
        }
    }
