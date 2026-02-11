# Fortitude Re: DJ Basin Investment Model - Comprehensive Code Review

## Executive Summary

Your Monte Carlo risk model is **correctly implemented** and produces results that closely match the investment deck targets. The model demonstrates sophisticated handling of three key risk factors: commodity prices, development timing, and decline curve steepening.

| Metric | Your Model | Deck Target | Status |
|--------|------------|-------------|--------|
| Base IRR | 16.9% | 17.6% | ✓ Within 0.7% |
| Base ROI | 1.99x | 1.94x | ✓ Slightly higher |
| Payback | 4.1 years | <5 years | ✓ Meets target |
| Monte Carlo Median | 13.7% | N/A | ✓ Reasonable stress |

---

## Part 1: Analysis of the 3% Floor and Other "Arbitrary" Values

### The 3% Yield Floor (`yield_curve.py`, line 58)

```python
tail_yields.append(max(yield_t, 0.03))  # Floor at 3%
```

**When does it activate?**
Based on my testing, the 3% floor ONLY activates when:
- b-factor < 0.2 AND initial decline rate Di > 0.5
- This is **outside your Monte Carlo simulation range** (b clipped to [0.3, 1.2])

**Why is it there?**
1. **Physical constraint**: Producing wells never truly go to zero production
2. **PDP anchor**: Proved Developed Producing wells (66% of NAV) always contribute some minimum cash flow
3. **Economic reality**: Below ~3% annual yield, assets would be abandoned rather than operated

**Is it arbitrary?**
Somewhat, but it's a **reasonable engineering safeguard**. Alternative approaches:

```python
# Option 1: Link to economic limit (more rigorous)
MINIMUM_ECONOMIC_YIELD = operating_costs_per_well / asset_value  # ~2-4% typically

# Option 2: Asymptotic approach (smoother)
yield_t = max(yield_t, TERMINAL_YIELD * np.exp(-decay_rate * t))

# Option 3: Industry data calibration
# Use Enverus/IHS well decline databases to set basin-specific floors
```

**Recommendation**: Keep the 3% floor but document it as representing the "economic limit" below which wells would be shut in. This is defensible.

---

### The 10% PDP-Only Yield (`yield_curve.py`, line 106)

```python
pdp_only_yield = 0.10  # ~10% yield when only PDP producing
```

**Derivation check:**
- PDP = 66% of NAV ($691MM of $1,052MM)
- If PDP alone generates Y1 yield: 66% × 26.9% ≈ 17.7%
- The 10% is **conservative** (accounting for G&A drag and decline during delay)

**Improvement option:**
```python
# More rigorous derivation
pdp_only_yield = (NAV_BY_CATEGORY['PDP'] / TOTAL_NAV_MM) * YIELD_Y1 * 0.85  # 15% discount
# This gives ~15%, more generous than your 10%
```

**Verdict**: Your 10% is conservative but defensible. Consider making it configurable in `config.py`.

---

### The 3% Delay Penalty Rate (`config.py`, line 120)

```python
DELAY_PENALTY_RATE = 0.03  # 3% yield reduction per year of delay
```

**What it does:**
- Reduces cumulative yield by 3% for each year of delay
- At 3-year delay: yield × 0.91 (9% haircut)
- Floored at 0.75 (max 25% penalty)

**Economic justification:**
- Represents **opportunity cost of capital** during unproductive delay period
- Alternative: Use weighted-average cost of capital (WACC) or hurdle rate
- 3% is modest—many would use 5-10% (closer to discount rate)

**Improvement option:**
```python
# Link to required IRR
DELAY_PENALTY_RATE = TARGET_IRR * 0.2  # 20% of target IRR per year
# This gives 17.6% × 0.2 = 3.5%, close to your 3%
```

---

### Terminal Value NAV Multiples (`cash_flows.py`, lines 37-44)

```python
if year_10_price_factor >= 0.9:
    nav_multiple = 0.90
elif year_10_price_factor >= 0.7:
    nav_multiple = 0.70
# etc.
```

**Why stepped rather than continuous?**
- **M&A market cycles**: Mineral royalty transactions cluster at specific valuation bands
- During commodity downturns, buyers disappear entirely (not just price down)
- This "step function" captures market illiquidity

**Improvement option (continuous):**
```python
# Continuous approach
nav_multiple = 0.30 + 0.60 * min(1.0, year_10_price_factor)
# This ranges from 0.30 (at 0% strip) to 0.90 (at 100%+ strip)
```

**Verdict**: Your stepped approach is more realistic for M&A dynamics.

---

## Part 2: Model Correctness Verification

### ✓ Yield Curve Generation
- Years 1-3 correctly pulled from deck (26.9%, 26.6%, 25.1%)
- Years 4-10 correctly generated using Arps hyperbolic formula
- Calibration to 18.6% average (1.86x total) is correct

### ✓ Cash Flow Construction
- Year 0: -$195MM investment
- Years 1-10: Investment × Yield × Price - G&A
- Year 10 includes terminal value
- G&A of 75 bps correctly deducted

### ✓ IRR Calculation
- Newton-Raphson implementation is correct
- Convergence tolerance of 1e-8 is appropriate
- Bounds checking (-0.99 to 2.0) prevents divergence

### ✓ Monte Carlo Simulation
- Ornstein-Uhlenbeck price simulation correctly implements mean reversion
- Cholesky decomposition properly correlates oil/gas/NGL
- Timing delays weighted by return contribution (not NAV)—this is **correct** conceptually

### ⚠️ Minor Issue Found
In `analysis.py`, line 77:
```python
profit = sum(cfs)  # This is total undiscounted profit
```
This is fine for loss attribution, but note that `profit` here is nominal, not NPV. For risk metrics, this is acceptable since you're looking at absolute gains/losses.

---

## Part 3: Detailed Code Walkthrough (Interview Prep)

---

# FILE 1: `config.py` — The Configuration Hub

This file contains all hardcoded parameters and constants.

```python
"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Configuration and Constants
===========================
All input parameters from the investment deck.
"""
```

### Capital Structure (Lines 8-18)
```python
PURCHASE_PRICE_MM = 905.0    # $905MM total asset purchase price
DEBT_MM = 178.0              # $178MM debt financing
CLOSING_COSTS_MM = 5.0       # $5MM legal/transaction fees
POST_EFF_DATE_CF_MM = 22.0   # $22MM cash flows received after effective date but before close
TOTAL_EQUITY_MM = 710.0      # = 905 - 178 + 5 - 22 = $710MM total equity check
CO_INVEST_MM = 195.0         # Co-investor's equity commitment ($195MM)
CO_INVEST_SHARE = CO_INVEST_MM / TOTAL_EQUITY_MM  # ~27.5% ownership share
```
**Interview tip**: The co-invest share (27.5%) determines what portion of all cash flows go to the co-investor.

### G&A Rate (Lines 20-24)
```python
GA_RATE = 0.0075  # 75 basis points (0.75%) annual G&A charge
```
**Interview tip**: This is deducted from cash flows every year. Common in mineral rights management—covers accounting, land administration, legal review.

### NAV Breakdown (Lines 36-44)
```python
NAV_BY_CATEGORY = {
    'PDP': 691,         # 66% - Proven Developed Producing (wells already flowing)
    'DUC': 123,         # 11% - Drilled but Uncompleted (wells drilled, not fracked)
    'Permit': 39,       # 4%  - Permitted locations (regulatory approval obtained)
    'APD': 91,          # 9%  - Applications for Permit to Drill (in regulatory queue)
    'Undeveloped': 108  # 10% - Undrilled, unpermitted (highest risk)
}
```
**Interview tip**: The reserve categories represent a risk ladder. PDP is lowest risk (already producing), Undeveloped is highest (may never be drilled).

### Return Contribution Weights (Lines 50-56)
```python
RETURN_CONTRIBUTION = {
    'PDP': 1.0,         # PDP contributes 1.0x to return-weighted delay calculation
    'DUC': 0.2,         # DUC contributes 0.2x
    'Permit': 0.1,      # Permit contributes 0.1x
    'APD': 0.3,         # APD contributes 0.3x
    'Undeveloped': 0.4  # Undeveloped contributes 0.4x
}
```
**Interview tip**: These weights are from the deck's "Return by Category" chart. They weight delays by economic impact, not just NAV proportion.

### Decline Curve Parameters (Lines 107-114)
```python
DECLINE_CURVE_PARAMS = {
    'base_b_factor': 0.9,       # Hyperbolic exponent (higher = flatter decline)
    'stress_b_factor': 0.5,     # Used in scenario analysis
    'severe_b_factor': 0.3,     # Used in scenario analysis
    'b_factor_volatility': 0.12,# Standard deviation for Monte Carlo
    'base_Di': 0.25,            # Initial decline rate (25%/year)
    'Di_volatility': 0.05       # Standard deviation for Di
}
```
**Interview tip**: The Arps b-factor determines curve shape:
- b = 0: Exponential decline (steepest)
- b = 0.5: Moderate hyperbolic
- b = 1.0: Harmonic (flattest)
- DJ Basin Niobrara typically b = 0.8-1.1

### Price Simulation Parameters (Lines 127-138)
```python
PRICE_PARAMS = {
    'oil': {'mu': 1.0, 'theta': 0.3, 'sigma': 0.25, 'current': 1.0},
    'gas': {'mu': 1.0, 'theta': 0.5, 'sigma': 0.45, 'current': 1.0},
    'ngl': {'mu': 1.0, 'theta': 0.35, 'sigma': 0.30, 'current': 1.0}
}
```
**Interview tip**: Ornstein-Uhlenbeck parameters:
- `mu`: Long-term mean (1.0 = strip pricing)
- `theta`: Mean-reversion speed (higher = faster pull back to mean)
- `sigma`: Volatility (gas highest at 0.45—more volatile than oil)

---

# FILE 2: `yield_curve.py` — Generating Cash Flow Yields

This file creates the annual yield curve using Arps hyperbolic decline.

### Main Function: `generate_hyperbolic_yield_curve()` (Lines 20-87)

```python
def generate_hyperbolic_yield_curve(b_factor=None, Di=None, delay_years=0, calibrate_base=False):
```

**Step 1: Set defaults (Lines 44-48)**
```python
if b_factor is None:
    b_factor = DECLINE_CURVE_PARAMS['base_b_factor']  # 0.9
if Di is None:
    Di = DECLINE_CURVE_PARAMS['base_Di']  # 0.25
```

**Step 2: Use deck values for Years 1-3 (Lines 50-51)**
```python
base_yields = [YIELD_Y1, YIELD_Y2, YIELD_Y3]  # [0.269, 0.266, 0.251]
```
These come directly from the investment deck's projected yields.

**Step 3: Generate Years 4-10 using Arps formula (Lines 53-58)**
```python
q3 = YIELD_Y3  # Starting point: Year 3 yield (25.1%)
tail_yields = []
for t in range(1, 8):  # t=1 to 7 corresponds to Years 4-10
    yield_t = q3 / ((1 + b_factor * Di * t) ** (1 / b_factor))
    tail_yields.append(max(yield_t, 0.03))  # Floor at 3%
```

**The Arps Hyperbolic Decline Formula:**
```
q(t) = q_i / (1 + b × D_i × t)^(1/b)
```
Where:
- q_i = initial rate (Year 3 yield)
- b = hyperbolic exponent (0.9 base)
- D_i = initial decline rate (0.25)
- t = time in years from Year 3

**Example calculation (Year 4, t=1):**
```
q(1) = 0.251 / (1 + 0.9 × 0.25 × 1)^(1/0.9)
     = 0.251 / (1.225)^1.111
     = 0.251 / 1.253
     = 0.200 (20.0%)
```

**Step 4: Calibrate to deck target (Lines 60-78)**
```python
is_base_case = (
    b_factor == DECLINE_CURVE_PARAMS['base_b_factor'] and 
    Di == DECLINE_CURVE_PARAMS['base_Di'] and 
    delay_years == 0
)

if is_base_case or calibrate_base:
    target_sum = AVG_10Y_YIELD * 10  # 18.6% × 10 = 1.86x
    known_sum = sum(base_yields)      # 0.786 (Y1-Y3)
    remaining_target = target_sum - known_sum  # 1.074
    
    tail_sum = sum(tail_yields)
    scale = remaining_target / tail_sum
    tail_yields = [y * scale for y in tail_yields]  # Scale Y4-Y10 to hit target
```
This ensures the base case exactly matches the deck's 18.6% average yield.

### Delay Function: `_apply_delay_to_curve()` (Lines 90-147)

This handles development timing delays with three regimes:

**Regime 1: Full delay year (production_time <= -1.0)**
```python
delayed_curve[year] = pdp_only_yield  # 10% - only PDP producing
```

**Regime 2: Partial delay year (-1 < production_time < 0)**
```python
ramp_frac = production_time + 1.0  # Linear ramp from 0 to 1
ramp_target = base_curve[0] * 0.85  # 15% ramp-up penalty
delayed_curve[year] = pdp_only_yield + ramp_frac * (ramp_target - pdp_only_yield)
delayed_curve[year] *= delay_penalty  # Apply proportional penalty
```

**Regime 3: After delay (production_time >= 0)**
```python
idx_low = int(production_time)
idx_high = idx_low + 1
frac = production_time - idx_low
interpolated = base_curve[idx_low] * (1 - frac) + base_curve[idx_high] * frac
delayed_curve[year] = interpolated * delay_penalty
```
Uses linear interpolation to read from shifted base curve.

---

# FILE 3: `price_simulation.py` — Commodity Price Monte Carlo

Simulates correlated oil, gas, and NGL prices using the Ornstein-Uhlenbeck process.

### Main Function: `simulate_commodity_prices()` (Lines 12-95)

**Step 1: Cholesky decomposition for correlation (Lines 40-41)**
```python
corr = np.array(PRICE_CORRELATION)  # 3×3 correlation matrix
chol = np.linalg.cholesky(corr)      # Lower triangular decomposition
```
Cholesky lets us convert independent random draws to correlated draws.

**Step 2: For each simulation, evolve prices year by year (Lines 59-76)**
```python
for _ in range(years):
    z = np.random.normal(0, 1, 3)  # Independent standard normals
    corr_z = chol @ z               # Apply correlation structure
    
    for i, commodity in enumerate(['oil', 'gas', 'ngl']):
        p = PRICE_PARAMS[commodity]
        current_price = prices[commodity][-1]
        
        # Ornstein-Uhlenbeck dynamics
        drift = p['theta'] * (p['mu'] - current_price) * dt
        diffusion = p['sigma'] * np.sqrt(dt) * corr_z[i]
        
        new_price = max(0.2, current_price + drift + diffusion)  # Floor at 20%
        prices[commodity].append(new_price)
```

**The O-U Process:**
```
dP = θ(μ - P)dt + σdW
```
- `θ(μ - P)dt`: Drift term pulls price back toward mean μ
- `σdW`: Random shock term

**Interview tip**: O-U is better than geometric Brownian motion for commodities because it captures **mean reversion**—prices tend to return to equilibrium production costs.

**Step 3: Calculate blended price (Lines 78-86)**
```python
blended = (
    COMMODITY_MIX['oil'] * prices['oil'][t] +   # 32% oil
    COMMODITY_MIX['gas'] * prices['gas'][t] +   # 40% gas
    COMMODITY_MIX['ngl'] * prices['ngl'][t]     # 28% NGL
)
```
Blended price reflects the actual production mix of this DJ Basin asset.

---

# FILE 4: `risk_models.py` — Timing and Decline Risk Simulation

### Function: `simulate_timing_risk()` (Lines 15-56)

**Step 1: Draw delays for each reserve category (Lines 34-43)**
```python
for category, params in TIMING_RISK_PARAMS.items():
    if stochastic and np.random.random() < params['delay_prob']:
        if params['max_delay_years'] > 0:
            delay = np.random.uniform(0.25, params['max_delay_years'])
        else:
            delay = 0
    else:
        delay = 0
    category_delays[category] = delay
```
Each category has a probability of experiencing delay, drawn from uniform distribution.

**Step 2: Calculate return-weighted average delay (Lines 45-50)**
```python
total_contribution = sum(RETURN_CONTRIBUTION.values())  # 2.0
weighted_delay = sum(
    category_delays[cat] * RETURN_CONTRIBUTION[cat] / total_contribution
    for cat in category_delays
)
```
**Interview tip**: We weight by return contribution, not NAV, because delays in high-return categories hurt IRR more.

### Function: `simulate_decline_curve_risk()` (Lines 59-105)

```python
if stochastic:
    b_shock = np.random.normal(0, DECLINE_CURVE_PARAMS['b_factor_volatility'])
    b_factor = np.clip(base_b + b_shock, 0.3, 1.2)  # Clipped to realistic range
```
The b-factor is shocked with normal distribution and clipped to [0.3, 1.2].

---

# FILE 5: `cash_flows.py` — Financial Calculations

### Function: `estimate_terminal_value()` (Lines 15-47)

```python
remaining_nav = TOTAL_NAV_MM * remaining_reserves_pct  # ~15% of reserves left
# NAV multiple depends on price environment
if year_10_price_factor >= 0.9:
    nav_multiple = 0.90
# ... stepped multiples ...
terminal_value = remaining_nav * nav_multiple * year_10_price_factor
return terminal_value * CO_INVEST_SHARE  # Co-investor's share
```

### Function: `build_cash_flows()` (Lines 50-83)

```python
cfs = [-CO_INVEST_MM]  # Year 0: $195MM outflow

for year, (base_yield, price_factor) in enumerate(zip(yield_curve, price_factors_by_year)):
    annual_cf = CO_INVEST_MM * base_yield * price_factor  # Revenue
    
    if include_ga:
        annual_cf -= CO_INVEST_MM * GA_RATE  # Deduct 75 bps G&A
    
    if year == 9:  # Year 10
        annual_cf += estimate_terminal_value(price_factor)  # Add exit value
    
    cfs.append(annual_cf)
```

### Function: `calculate_irr()` (Lines 86-125)

Uses Newton-Raphson method to solve:
```
Σ(CF_t / (1 + IRR)^t) = 0
```

```python
def npv(rate, cfs):
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cfs))

def npv_derivative(rate, cfs):
    return sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cfs))

rate = 0.10  # Initial guess
for _ in range(max_iterations):
    f = npv(rate, cfs)
    f_prime = npv_derivative(rate, cfs)
    new_rate = rate - f / f_prime  # Newton-Raphson step
    if abs(new_rate - rate) < tolerance:
        return new_rate
    rate = new_rate
```

**Interview tip**: Newton-Raphson converges quadratically (error squares each iteration), much faster than bisection.

---

# FILE 6: `analysis.py` — Monte Carlo Engine

### Function: `run_monte_carlo()` (Lines 16-110)

**The main simulation loop (Lines 51-99):**
```python
for i in range(num_sims):
    # 1. Get price path for this simulation
    price_path = price_sims['blended_paths'][i]
    avg_price = price_sims['blended_avg'][i]
    
    # 2. Draw timing delay
    delay, _, max_dev_delay = simulate_timing_risk(stochastic=True)
    
    # 3. Draw decline curve parameters
    b_factor, Di, _ = simulate_decline_curve_risk(stochastic=True)
    
    # 4. Generate stressed yield curve
    stressed_yields = generate_hyperbolic_yield_curve(
        b_factor=b_factor, Di=Di, delay_years=delay
    )
    
    # 5. Build cash flows and calculate metrics
    cfs = build_cash_flows(stressed_yields, price_path)
    irr = calculate_irr(cfs)
    roi = calculate_roi(cfs)
    profit = sum(cfs)
```

### Loss Attribution (Lines 84-98)
```python
if profit < 0:
    factors = []
    if avg_price < 0.80:      factors.append('price')
    if delay > 0.3:           factors.append('timing')
    if b_factor < 0.70:       factors.append('decline')
    
    if len(factors) == 1:
        risk_attribution[factors[0]] += 1
    else:
        risk_attribution['combined'] += 1
```
Attributes losses to individual risk factors or "combined" if multiple.

---

# FILE 7: `main.py` — Orchestration

This is the runner script that:
1. Generates base case and validates against deck
2. Validates timing delay monotonicity
3. Runs 50,000 Monte Carlo simulations
4. Performs deterministic scenario analysis
5. Calculates breakeven prices
6. Generates all charts

**Key sections for interview:**

```python
# Section 1: Base Case Validation (Lines 62-82)
base_yields = generate_hyperbolic_yield_curve()
base_cfs = build_cash_flows(base_yields, [1.0] * 10)
base_irr = calculate_irr(base_cfs)

# Section 2: Monte Carlo (Lines 92-140)
mc_results = run_monte_carlo()
prob_loss = np.mean(sim_profits < 0)

# Section 3: Scenario Analysis (Lines 176-256)
scenarios = run_scenario_analysis(base_yields)

# Section 4: Breakeven (Lines 260-270)
breakeven = run_breakeven_analysis(base_yields)
```

---

# FILE 8: `charts.py` — Visualization

Creates six publication-quality charts using matplotlib.

### Chart 1: IRR Distribution Histogram (Lines 20-51)
```python
ax.hist(sim_irrs * 100, bins=50, color='steelblue', edgecolor='white', alpha=0.8)
ax.axvline(np.median(sim_irrs) * 100, color='red', linestyle='--', ...)
ax.axvline(base_irr * 100, color='green', linestyle='-', ...)
ax.axvline(0, color='black', linestyle=':', ...)  # Breakeven line
```
Shows the distribution of 50,000 IRR outcomes with median, base case, and breakeven reference lines.

### Chart 2: Percentile Bar Chart (Lines 54-96)
```python
colors = ['#d62728' if v < 0 else '#2ca02c' if v > 15 else '#1f77b4' for v in irr_values]
```
Color coding: Red for negative IRR, green for >15%, blue for moderate.
Each bar annotated with average input drivers (price, delay, b-factor).

### Chart 3: Sensitivity Tornado (Lines 99-134)
```python
ax.barh(y_pos, [l - base_val for l in low_vals], left=base_val, ...)
```
Horizontal bars showing IRR degradation from each stress scenario.

### Chart 4: Price vs IRR Scatter (Lines 137-174)
```python
scatter = ax.scatter(sim_prices[sample_idx], sim_irrs[sample_idx] * 100,
                     c=sim_b_factors[sample_idx], cmap='RdYlGn', alpha=0.5, s=10)
```
Plots 5,000 sampled simulations with color representing b-factor (red = steep decline, green = flat).

### Chart 5: Cumulative Distribution (Lines 177-217)
```python
sorted_irrs = np.sort(sim_irrs) * 100
cumulative = np.arange(1, len(sorted_irrs) + 1) / len(sorted_irrs)
ax.plot(sorted_irrs, cumulative * 100, color='steelblue', linewidth=2)
```
Shows probability of achieving various IRR thresholds. Red shading indicates loss region.

### Chart 6: Delay Impact (Lines 220-254)
```python
ax.plot(delays, irrs, 'o-', color='steelblue', linewidth=2, markersize=8)
```
Line plot showing IRR degradation as development delays increase from 0 to 3 years.

---

## Interview Q&A Preparation

**Q: Why use Ornstein-Uhlenbeck instead of GBM for prices?**
A: Commodities exhibit mean reversion—when prices spike above equilibrium production costs, supply increases and prices fall back. O-U captures this; GBM does not.

**Q: Why weight delays by return contribution rather than NAV?**
A: A delay in Undeveloped (10% NAV, 0.4x return contribution) hurts IRR more per dollar than a delay in PDP (66% NAV, 1.0x contribution). Return contribution better captures economic impact.

**Q: What's the biggest risk to this investment?**
A: Commodity prices. My model shows 0.884 correlation between price and IRR. A 30% price drop cuts IRR from 16.9% to 6.4%.

**Q: How confident are you in the 0.8% probability of loss?**
A: Moderately confident. The key assumptions are: (1) prices mean-revert to strip, (2) decline curves cluster around industry type curves, (3) delays are modest on average. If any assumption is violated (e.g., structural gas oversupply), P(loss) could be higher.

**Q: Explain the 3% yield floor.**
A: It's a safeguard against physically unrealistic results in extreme decline scenarios. In practice, it only activates when b < 0.2, which is outside the simulation range. Real wells always produce some minimum yield before being abandoned.

---

## Recommended Improvements (If Asked)

1. **Move all hard-coded values to config.py** (e.g., pdp_only_yield, ramp_target)
2. **Add regime-switching for price simulation** (bull/bear markets)
3. **Include gas basis differentials** (DJ Basin trades at discount to Henry Hub)
4. **Add operator default risk** (top 2 operators = 74% NAV)
5. **Sensitivity to inflation on operating costs**
