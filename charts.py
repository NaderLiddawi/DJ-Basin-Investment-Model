"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Chart Generation
================
Creates all visualization charts for the analysis.
"""

import numpy as np
import matplotlib.pyplot as plt
import os


def setup_plot_style():
    """Configure matplotlib style for all charts."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'


def create_irr_distribution_chart(sim_irrs, base_irr, output_dir):
    """
    Create IRR distribution histogram.
    
    Args:
        sim_irrs: Array of simulated IRRs
        base_irr: Base case IRR for reference line
        output_dir: Directory to save chart
    
    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(sim_irrs * 100, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
    ax.axvline(np.median(sim_irrs) * 100, color='red', linestyle='--', 
               linewidth=2, label=f'Median: {np.median(sim_irrs):.1%}')
    ax.axvline(base_irr * 100, color='green', linestyle='-', 
               linewidth=2, label=f'Base Case: {base_irr:.1%}')
    ax.axvline(0, color='black', linestyle=':', linewidth=1.5, label='Breakeven (0%)')
    
    ax.set_xlabel('IRR (%)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Monte Carlo IRR Distribution (50,000 Simulations)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.set_xlim(-30, 40)
    
    path = os.path.join(output_dir, 'chart_1_irr_distribution.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return path


def create_percentile_chart(percentile_data, base_irr, output_dir):
    """
    Create percentile bar chart with input drivers.
    
    Args:
        percentile_data: List of dicts from get_percentile_input_ranges()
        base_irr: Base case IRR
        output_dir: Directory to save chart
    
    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    pct_labels = ['P1', 'P5', 'P10', 'P25', 'P50', 'P75', 'P90', 'P95', 'P99']
    irr_values = [d['irr'] * 100 for d in percentile_data]
    colors = ['#d62728' if v < 0 else '#2ca02c' if v > 15 else '#1f77b4' for v in irr_values]
    
    bars = ax.bar(pct_labels, irr_values, color=colors, edgecolor='white', linewidth=1.5)
    ax.axhline(0, color='black', linestyle='-', linewidth=1)
    ax.axhline(base_irr * 100, color='green', linestyle='--', 
               linewidth=1.5, label=f'Base Case: {base_irr:.1%}')
    
    # Annotate bars with input drivers
    for bar, data in zip(bars, percentile_data):
        height = bar.get_height()
        label = f"P:{data['price_avg']:.2f}x\nb:{data['b_avg']:.2f}"
        y_offset = 2 if height >= 0 else -6
        ax.annotate(label, xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, y_offset), textcoords='offset points',
                    ha='center', va='bottom' if height >= 0 else 'top', fontsize=8)
    
    ax.set_xlabel('Percentile', fontsize=12)
    ax.set_ylabel('IRR (%)', fontsize=12)
    ax.set_title('IRR Percentiles with Average Input Drivers', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left')
    ax.set_ylim(-15, 35)
    
    path = os.path.join(output_dir, 'chart_2_percentile_inputs.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return path


def create_sensitivity_tornado(sensitivities, base_irr, output_dir):
    """
    Create sensitivity tornado chart.
    
    Args:
        sensitivities: List of (name, irr_value) tuples
        base_irr: Base case IRR
        output_dir: Directory to save chart
    
    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    labels = [s[0] for s in sensitivities]
    low_vals = [s[1] for s in sensitivities]
    base_val = base_irr * 100
    y_pos = np.arange(len(labels))
    
    ax.barh(y_pos, [l - base_val for l in low_vals], left=base_val, 
            color='#d62728', height=0.6, label='Stress Impact')
    ax.axvline(base_val, color='green', linestyle='--', 
               linewidth=2, label=f'Base Case: {base_val:.1f}%')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel('IRR (%)', fontsize=12)
    ax.set_title('Sensitivity Analysis: IRR Impact by Risk Factor', fontsize=14, fontweight='bold')
    ax.legend(loc='lower left')
    ax.set_xlim(0, 20)
    
    path = os.path.join(output_dir, 'chart_3_sensitivity_tornado.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return path


def create_price_vs_irr_scatter(sim_prices, sim_irrs, sim_b_factors, output_dir):
    """
    Create scatter plot of price vs IRR, colored by b-factor.
    
    Args:
        sim_prices: Array of average prices
        sim_irrs: Array of IRRs
        sim_b_factors: Array of b-factors (for coloring)
        output_dir: Directory to save chart
    
    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Sample for performance
    sample_size = min(5000, len(sim_irrs))
    sample_idx = np.random.choice(len(sim_irrs), size=sample_size, replace=False)
    
    scatter = ax.scatter(sim_prices[sample_idx], sim_irrs[sample_idx] * 100,
                         c=sim_b_factors[sample_idx], cmap='RdYlGn', alpha=0.5, s=10)
    
    ax.axhline(0, color='black', linestyle=':', linewidth=1)
    ax.axvline(1.0, color='green', linestyle='--', linewidth=1, label='Strip Price')
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('b-factor (Decline Curve)', fontsize=10)
    
    ax.set_xlabel('Blended Price Factor (1.0 = Strip)', fontsize=12)
    ax.set_ylabel('IRR (%)', fontsize=12)
    ax.set_title('IRR vs. Price Factor (Color = Decline Curve)', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    
    path = os.path.join(output_dir, 'chart_4_price_vs_irr.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return path


def create_cumulative_distribution(sim_irrs, base_irr, prob_loss, output_dir):
    """
    Create cumulative distribution function chart.
    
    Args:
        sim_irrs: Array of IRRs
        base_irr: Base case IRR
        prob_loss: Probability of loss
        output_dir: Directory to save chart
    
    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    sorted_irrs = np.sort(sim_irrs) * 100
    cumulative = np.arange(1, len(sorted_irrs) + 1) / len(sorted_irrs)
    
    ax.plot(sorted_irrs, cumulative * 100, color='steelblue', linewidth=2)
    ax.axvline(0, color='red', linestyle='--', linewidth=1.5, 
               label=f'Breakeven (P(loss)={prob_loss:.1%})')
    ax.axvline(base_irr * 100, color='green', linestyle='--', 
               linewidth=1.5, label=f'Base Case: {base_irr:.1%}')
    ax.axhline(50, color='gray', linestyle=':', linewidth=1)
    
    # Shade loss region
    ax.fill_between(sorted_irrs, 0, cumulative * 100, 
                    where=(sorted_irrs < 0), alpha=0.3, color='red')
    
    ax.set_xlabel('IRR (%)', fontsize=12)
    ax.set_ylabel('Cumulative Probability (%)', fontsize=12)
    ax.set_title('Cumulative Distribution: Probability of Achieving IRR', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.set_xlim(-30, 40)
    ax.set_ylim(0, 100)
    
    path = os.path.join(output_dir, 'chart_5_cumulative_distribution.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return path


def create_yield_curve_chart(yield_curve, output_dir):
    """
    Create base yield curve visualization.

    Args:
        yield_curve: 10-element array of annual yields (decimal)
        output_dir: Directory to save chart

    Returns:
        str: Path to saved chart
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    years = np.arange(1, 11)
    yields_pct = yield_curve * 100

    # Bar chart for yields
    bars = ax.bar(years, yields_pct, color='steelblue', edgecolor='white',
                  alpha=0.8, width=0.7)

    # Add value labels on bars
    for bar, yld in zip(bars, yields_pct):
        ax.annotate(f'{yld:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Add average line
    avg_yield = np.mean(yield_curve) * 100
    ax.axhline(avg_yield, color='red', linestyle='--', linewidth=2,
               label=f'10-Year Average: {avg_yield:.1f}%')

    # Add cumulative annotation
    cumulative = np.cumsum(yield_curve) * 100
    ax2 = ax.twinx()
    ax2.plot(years, cumulative, color='green', marker='o', linewidth=2,
             markersize=6, label='Cumulative Yield')
    ax2.set_ylabel('Cumulative Yield (%)', fontsize=11, color='green')
    ax2.tick_params(axis='y', labelcolor='green')
    ax2.set_ylim(0, 200)

    # Formatting
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Annual Yield (%)', fontsize=12)
    ax.set_title('Base Case Yield Curve (Arps Hyperbolic Decline)',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(years)
    ax.set_ylim(0, 35)
    ax.legend(loc='upper right')
    ax2.legend(loc='center right')

    # Add total sum annotation
    total_sum = np.sum(yield_curve)
    ax.annotate(f'10-Year Sum: {total_sum:.2f}x',
                xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=11, fontweight='bold', va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    path = os.path.join(output_dir, 'chart_6_yield_curve.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    return path


def generate_all_charts(mc_results, base_irr, percentile_data, sensitivities, base_yields, output_dir):
    """
    Generate all charts and save to output directory.
    
    Args:
        mc_results: Monte Carlo simulation results dict
        base_irr: Base case IRR
        percentile_data: List of percentile analysis dicts
        sensitivities: List of sensitivity (name, irr) tuples
        base_yields: Base Yield Curve (18.6% average annual assumption from Deck)
        output_dir: Directory to save charts
    
    Returns:
        list: Paths to all saved charts
    """
    setup_plot_style()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    paths = []
    
    # Chart 1: IRR Distribution
    path = create_irr_distribution_chart(mc_results['sim_irrs'], base_irr, output_dir)
    paths.append(path)
    print(f"  Saved: {path}")
    
    # Chart 2: Percentile Chart
    path = create_percentile_chart(percentile_data, base_irr, output_dir)
    paths.append(path)
    print(f"  Saved: {path}")
    
    # Chart 3: Sensitivity Tornado
    path = create_sensitivity_tornado(sensitivities, base_irr, output_dir)
    paths.append(path)
    print(f"  Saved: {path}")
    
    # Chart 4: Price vs IRR Scatter
    path = create_price_vs_irr_scatter(
        mc_results['sim_prices'], 
        mc_results['sim_irrs'], 
        mc_results['sim_b_factors'],
        output_dir
    )
    paths.append(path)
    print(f"  Saved: {path}")
    
    # Chart 5: Cumulative Distribution
    prob_loss = np.mean(mc_results['sim_profits'] < 0)
    path = create_cumulative_distribution(mc_results['sim_irrs'], base_irr, prob_loss, output_dir)
    paths.append(path)
    print(f"  Saved: {path}")

    # Chart 6: Yield Curve Chart
    path = create_yield_curve_chart(base_yields, output_dir)
    paths.append(path)
    print(f"  Saved: {path}")


    return paths
