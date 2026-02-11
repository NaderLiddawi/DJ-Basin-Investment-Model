"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Main Runner
===========
Execute this file to run the complete analysis.

Usage:
    python main.py

Output:
    - Console output with all analysis results
    - Charts saved to output directory
"""

import numpy as np
import os

# Import configuration
from config import (
    CO_INVEST_MM, TARGET_IRR, TARGET_ROI, NUM_SIMULATIONS,
    DECLINE_CURVE_PARAMS, NAV_BY_CATEGORY, TOP_2_OPERATOR_SHARE,
    RANDOM_SEED
)

# Import modules
from yield_curve import generate_hyperbolic_yield_curve
from price_simulation import simulate_commodity_prices, get_price_statistics
from risk_models import (
    get_timing_risk_statistics, 
    get_decline_curve_statistics
)
from cash_flows import (
    build_cash_flows, 
    calculate_irr, 
    calculate_roi, 
    calculate_payback
)
from analysis import (
    run_monte_carlo,
    get_percentile_input_ranges,
    run_scenario_analysis,
    run_breakeven_analysis,
    validate_timing_delays
)
from charts import generate_all_charts


def print_header(title, char='=', width=70):
    """Print formatted section header."""
    print(char * width)
    print(title)
    print(char * width)


def print_subheader(title, char='-', width=70):
    """Print formatted subsection header."""
    print(char * width)
    print(title)
    print(char * width)


def main():
    """Run the complete Fortitude Re analysis."""
    
    # Set random seed for reproducibility
    np.random.seed(RANDOM_SEED)
    
    # Get output directory (same as script location)
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print_header("FORTITUDE RE: DJ BASIN INVESTMENT MODEL")
    print()
    
    # ==========================================================================
    # SECTION 1: BASE CASE VALIDATION
    # ==========================================================================
    
    print("SECTION 1: BASE CASE VALIDATION")
    print_subheader("")
    
    # Generate base case yield curve
    base_yields = generate_hyperbolic_yield_curve()
    
    print(f"Reconstructed Yield Curve: {[f'{y:.1%}' for y in base_yields]}")
    print(f"10-Year Sum: {sum(base_yields):.2f}x  |  Average: {np.mean(base_yields):.1%}")
    
    # Calculate base case metrics
    base_price_factors = [1.0] * 10
    base_cfs = build_cash_flows(base_yields, base_price_factors)
    base_irr = calculate_irr(base_cfs)
    base_roi = calculate_roi(base_cfs)
    base_payback = calculate_payback(base_cfs)
    
    print(f"\nCo-Invest Perspective (${CO_INVEST_MM}MM):")
    print(f"  Base Case IRR:      {base_irr:.1%} (Deck Target: {TARGET_IRR:.1%})")
    print(f"  Base Case ROI:      {base_roi:.2f}x (Deck Target: {TARGET_ROI:.2f}x)")
    print(f"  Payback Period:     {base_payback:.1f} years (Deck: <5 years)")
    
    # ==========================================================================
    # TIMING DELAY VALIDATION
    # ==========================================================================
    
    print_subheader("\nTIMING DELAY VALIDATION (IRR should monotonically decrease):")
    
    passed, delay_results = validate_timing_delays()
    
    for result in delay_results:
        status = "✓" if result['valid'] else "✗ ERROR"
        print(f"  Delay {result['delay']:.2f}yr: IRR = {result['irr']:.1%} {status}")
    
    print(f"Validation: {'PASSED - IRR monotonically decreasing' if passed else 'FAILED'}")
    
    # ==========================================================================
    # SECTION 2: MONTE CARLO SIMULATION
    # ==========================================================================
    
    print_header(f"\nSECTION 2: MONTE CARLO RISK ANALYSIS ({NUM_SIMULATIONS} Simulations)")
    print_subheader("Simulating: Commodity prices + Timing delays + Decline curve steepening\n")
    
    # Run Monte Carlo
    mc_results = run_monte_carlo()
    
    # Price statistics
    price_stats = get_price_statistics(mc_results['price_sims'])
    print("Commodity Price Simulation Statistics:")
    print(f"  Oil Avg Factor:     {price_stats['oil']['mean']:.2f}x (std={price_stats['oil']['std']:.2f})")
    print(f"  Gas Avg Factor:     {price_stats['gas']['mean']:.2f}x (std={price_stats['gas']['std']:.2f})")
    print(f"  NGL Avg Factor:     {price_stats['ngl']['mean']:.2f}x (std={price_stats['ngl']['std']:.2f})")
    print(f"  Blended Avg:        {price_stats['blended']['mean']:.2f}x")
    
    # Timing statistics
    timing_stats = get_timing_risk_statistics(
        mc_results['sim_delays'], 
        mc_results['sim_max_dev_delays']
    )
    print(f"\nTiming Risk Statistics:")
    print(f"  Average Delay:      {timing_stats['avg_delay']:.2f} years")
    print(f"  Delay Std Dev:      {timing_stats['std_delay']:.2f} years")
    print(f"  Max Delay:          {timing_stats['max_delay']:.2f} years")
    print(f"  Avg Max Dev Delay:  {timing_stats['avg_max_dev_delay']:.2f} years")
    print(f"  % with >0.5yr Delay: {timing_stats['pct_over_half_year']:.1%}")
    print(f"  % with >1yr Delay:  {timing_stats['pct_over_one_year']:.1%}")
    
    # Decline curve statistics
    decline_stats = get_decline_curve_statistics(mc_results['sim_b_factors'])
    print(f"\nDecline Curve Risk Statistics:")
    print(f"  Average b-factor:   {decline_stats['avg_b_factor']:.2f} (base: {DECLINE_CURVE_PARAMS['base_b_factor']:.2f})")
    print(f"  b-factor Std Dev:   {decline_stats['std_b_factor']:.2f}")
    print(f"  % Steep Decline:    {decline_stats['pct_steep']:.1%} (b < 0.7)")
    print(f"  % Severe Steep:     {decline_stats['pct_severe']:.1%} (b < 0.5)")
    
    # Combined risk metrics
    sim_profits = mc_results['sim_profits']
    sim_irrs = mc_results['sim_irrs']
    
    prob_loss = np.mean(sim_profits < 0)
    losing_sims = sim_profits[sim_profits < 0]
    avg_loss = np.mean(losing_sims) if len(losing_sims) > 0 else 0
    p5_profit = np.percentile(sim_profits, 5)
    p1_profit = np.percentile(sim_profits, 1)
    
    print(f"\nCombined Risk Metrics:")
    print(f"  Probability of Loss:  {prob_loss:.1%}")
    print(f"  Avg Loss (if loss):   ${abs(avg_loss):.1f}MM")
    print(f"  P5 Profit Floor:      ${p5_profit:.1f}MM (5th percentile)")
    print(f"  P1 Profit Floor:      ${p1_profit:.1f}MM (1st percentile)")
    
    # Loss attribution
    risk_attr = mc_results['risk_attribution']
    total_losses = sum(risk_attr.values())
    if total_losses > 0:
        print(f"\nLoss Attribution (when losses occur):")
        print(f"  Price-driven:       {risk_attr['price']/total_losses:.1%}")
        print(f"  Timing-driven:      {risk_attr['timing']/total_losses:.1%}")
        print(f"  Decline-driven:     {risk_attr['decline']/total_losses:.1%}")
        print(f"  Combined factors:   {risk_attr['combined']/total_losses:.1%}")
        print(f"  Other/unexplained:  {risk_attr['other']/total_losses:.1%}")
    
    # ==========================================================================
    # PERCENTILE ANALYSIS
    # ==========================================================================
    
    percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    percentile_data = []
    
    print(f"\n" + "=" * 100)
    print("RETURN DISTRIBUTION WITH INPUT RANGES")
    print("-" * 100)
    print(f"{'Pctl':<6} {'IRR':>7} | {'Price Range':^16} | {'Delay Range':^16} | {'b-factor Range':^16} | {'n':>5}")
    print("-" * 100)
    
    for p in percentiles:
        data = get_percentile_input_ranges(
            p, sim_irrs, 
            mc_results['sim_prices'], 
            mc_results['sim_delays'], 
            mc_results['sim_b_factors']
        )
        percentile_data.append(data)
        
        label = f"P{p}"
        price_range = f"{data['price_min']:.2f}-{data['price_max']:.2f}x"
        delay_range = f"{data['delay_min']:.1f}-{data['delay_max']:.1f}yr"
        b_range = f"{data['b_min']:.2f}-{data['b_max']:.2f}"
        print(f"{label:<6} {data['irr']:>6.1%} | {price_range:^16} | {delay_range:^16} | {b_range:^16} | {data['n_sims']:>5}")
    
    print("-" * 100)
    print(f"Base Case: Price=1.00x, Delay=0.00yr, b=0.90 -> IRR={base_irr:.1%}")
    
    # Return distribution summary
    print(f"\nReturn Distribution:")
    print(f"  10th Percentile IRR:  {np.percentile(sim_irrs, 10):.1%}")
    print(f"  25th Percentile IRR:  {np.percentile(sim_irrs, 25):.1%}")
    print(f"  Median IRR:           {np.percentile(sim_irrs, 50):.1%}")
    print(f"  75th Percentile IRR:  {np.percentile(sim_irrs, 75):.1%}")
    print(f"  90th Percentile IRR:  {np.percentile(sim_irrs, 90):.1%}")
    
    # ==========================================================================
    # SECTION 3: SCENARIO ANALYSIS
    # ==========================================================================
    
    print_header("\nSECTION 3: SCENARIO ANALYSIS")
    
    scenarios = run_scenario_analysis(base_yields)
    
    # 3A: Price Scenarios
    print("\n3A. COMMODITY PRICE SCENARIOS (Base Decline Curve)")
    print(f"{'Scenario':<28} {'IRR':>8} {'ROI':>8} {'Payback':>10}")
    print("-" * 58)
    
    for name, results in scenarios['price_scenarios'].items():
        irr_str = f"{results['irr']:.1%}" if results['irr'] else "N/A"
        payback_str = f"{results['payback']:.1f}yr" if results['payback'] else ">10yr"
        print(f"{name:<28} {irr_str:>8} {results['roi']:>7.2f}x {payback_str:>10}")
    
    # 3B: Timing Scenarios
    print("\n3B. TIMING DELAY SCENARIOS (Strip Pricing)")
    print(f"{'Scenario':<28} {'IRR':>8} {'ROI':>8} {'Payback':>10}")
    print("-" * 58)
    
    for name, results in scenarios['timing_scenarios'].items():
        irr_str = f"{results['irr']:.1%}" if results['irr'] else "N/A"
        payback_str = f"{results['payback']:.1f}yr" if results['payback'] else ">10yr"
        print(f"{name:<28} {irr_str:>8} {results['roi']:>7.2f}x {payback_str:>10}")
    
    # 3C: Decline Curve Scenarios
    print("\n3C. DECLINE CURVE STEEPENING SCENARIOS (Strip Pricing)")
    print(f"{'Scenario':<28} {'b-factor':>10} {'IRR':>8} {'ROI':>8} {'10Y Sum':>10}")
    print("-" * 68)
    
    for name, results in scenarios['decline_scenarios'].items():
        irr_str = f"{results['irr']:.1%}" if results['irr'] else "N/A"
        print(f"{name:<28} {results['b_factor']:>10.2f} {irr_str:>8} {results['roi']:>7.2f}x {results['yield_sum']:>9.2f}x")
    
    # 3D: Combined Stress Scenarios
    print("\n3D. COMBINED STRESS SCENARIOS (Multiple Risk Factors)")
    print(f"{'Scenario':<35} {'IRR':>8} {'ROI':>8} {'Payback':>10}")
    print("-" * 65)
    
    for name, results in scenarios['combined_scenarios'].items():
        irr_str = f"{results['irr']:.1%}" if results['irr'] else "N/A"
        payback_str = f"{results['payback']:.1f}yr" if results['payback'] else ">10yr"
        print(f"{name:<35} {irr_str:>8} {results['roi']:>7.2f}x {payback_str:>10}")
    
    # ==========================================================================
    # SECTION 4: BREAKEVEN ANALYSIS
    # ==========================================================================
    
    print_header("\nSECTION 4: BREAKEVEN ANALYSIS")
    
    breakeven = run_breakeven_analysis(base_yields)
    
    print(f"Breakeven Price Factor: {breakeven['breakeven_factor']:.0%} of strip")
    print(f"At strip oil ~$70/bbl: Breakeven = ${breakeven['breakeven_price']:.0f}/bbl")
    print(f"10% IRR Floor Factor:   {breakeven['irr_10_floor_factor']:.0%} of strip (${breakeven['irr_10_floor_price']:.0f}/bbl)")
    
    # ==========================================================================
    # SECTION 5: KEY RISKS SUMMARY
    # ==========================================================================
    
    print_header("\nSECTION 5: KEY RISKS SUMMARY")
    
    print("""
STRUCTURAL RISKS:
1. Operator Concentration: Top 2 operators = 74% of NAV
   - Single operator failure significantly impacts returns

2. Undeveloped Reliance: 21% of ROI from highest-risk category
   - Requires commodity prices to justify drilling economics
   - Regulatory risk (Colorado 2,000' setback rules) affects APD/Undeveloped

3. Gas Exposure: 40% of reserves are natural gas
   - Gas prices uncorrelated with oil; basis differentials in DJ Basin
   - Current gas oversupply may persist

4. Terminal Value Sensitivity: ~8-10% of ROI depends on Year 10 environment
   - Highly dependent on commodity environment at exit
   - Mineral M&A multiples can compress in down markets

TIMING RISK:
- Development delays shift cash flows right, destroying IRR via time value
- Key sources: permitting, operator capital allocation, supply chain, price deferrals
- Risk concentrated in APD (40% delay prob) and Undeveloped (50% delay prob)

DECLINE CURVE RISK:
- DJ Basin wells may decline faster than type curves due to:
  * Parent-child well interference from infill drilling
  * Tighter spacing than reservoir can support
  * Reservoir pressure depletion
  * Completion quality variation
- Industry data shows ~20-30% of wells underperform type curves
""")
    
    # ==========================================================================
    # SECTION 6: GENERATE CHARTS
    # ==========================================================================
    
    print_header("SECTION 6: GENERATING CHARTS...")
    
    # Build sensitivity data for tornado chart
    sensitivities = []
    for name, results in [
        ('Price -30%', scenarios['price_scenarios']['Severe Stress (-30%)']),
        ('Price -15%', scenarios['price_scenarios']['Mild Stress (-15%)']),
        ('1-Year Delay', scenarios['timing_scenarios']['1-Year Delay']),
        ('2-Year Delay', scenarios['timing_scenarios']['2-Year Delay']),
        ('b-factor 0.6', scenarios['decline_scenarios']['Moderate Steepening']),
        ('b-factor 0.45', scenarios['decline_scenarios']['Severe Steepening']),
    ]:
        sensitivities.append((name, results['irr'] * 100 if results['irr'] else 0))
    
    # Generate all charts
    chart_paths = generate_all_charts(
        mc_results=mc_results,
        base_irr=base_irr,
        percentile_data=percentile_data,
        sensitivities=sensitivities,
        delay_validation=delay_results,
        output_dir=output_dir
    )
    
    # ==========================================================================
    # DONE
    # ==========================================================================
    
    print_header("\nEND OF ANALYSIS")
    print(f"\nCharts saved to: {output_dir}")


if __name__ == "__main__":
    main()
