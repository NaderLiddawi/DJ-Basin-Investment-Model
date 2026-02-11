# DJ Basin Co-Investment Analysis – Independent Quantitative Review

This repository contains a full end-to-end financial model and risk analysis framework for evaluating a **$195MM co-investment** opportunity in DJ Basin oil & gas mineral royalty assets (the “Asset”).

The purpose is to **independently validate** the underwriting presented in the diligence materials and to **stress-test the economics** using transparent, explainable quantitative methods that a reader can understand even without prior exposure to petroleum finance, stochastic processes, or numerical methods.

---

## WHAT THIS PROJECT DOES

It reconstructs a 10-year production/yield profile, converts it into co-investor cash flows, computes IRR/ROI/payback, then runs a 50,000-path Monte Carlo across price + decline-curve risk to quantify downside probability and return distribution.

---

# HIGH-LEVEL PIPELINE (SYSTEM VIEW)

```
Inputs (deck assumptions)
   ↓
Yield Curve (production decline / cash yield over time)
   ↓
Commodity Prices (stochastic, correlated, mean-reverting)
   ↓
Cash Flows (co-investor perspective, G&A, terminal value)
   ↓
Metrics (IRR / ROI / Payback / Breakeven)
   ↓
Risk Engine (Monte Carlo + scenarios + percentiles)
   ↓
Charts (distribution, tornado, CDF, scatter, yield visualization)
```

Each Python file owns one “layer” of this pipeline.

---

# FILE-BY-FILE: WHAT EACH MODULE DOES (AND WHY)

## `main.py` — Orchestrator / One-Run Execution
**Role:** Runs the entire analysis end-to-end in the correct order: base case → Monte Carlo → scenarios → breakeven → charts.

**Why it exists:** In real diligence work, you want a single command that produces a complete package of results and exhibits reproducible outputs.

Run:
```bash
python main.py
```

---

## `config.py` — Single Source of Truth for Assumptions
**Role:** Centralizes all key numerical inputs (capital structure, NAV mix, decline parameters, price process parameters, simulation settings).

**Why it exists:** Prevents “assumptions scattered everywhere,” which is one of the most common ways financial models become un-auditable.

---

## `yield_curve.py` — Reconstructs the 10-Year Yield Curve (Front-Loaded, Convex)
**Role:** Generates the 10-year **annual yield curve** that represents expected cash yield (as a fraction of invested capital) by year.

### What “front-loaded, convex yield curve” means (plain English)
A yield curve is “front-loaded” when **a large portion of total cash arrives early** (Years 1–3, 1–5). It is “convex” in the sense that **the timing is heavily weighted toward early years**, and then progressively decays. That matters because:

- Early cash has higher economic value than late cash (time value of money).
- Early cash makes **IRR more resilient** to late-life uncertainty (terminal value, long-run decline, far-out development timing).
- Early cash makes the investment behave somewhat like “return of capital first, upside later,” which is a classic downside-protection shape.

### Why Arps hyperbolic decline is used
Production declines for shale and tight formations are typically modeled using Arps decline families (exponential / hyperbolic / harmonic). Hyperbolic decline is widely used because it captures:

- Fast early decline (typical in shale)
- Slower tail decline over time
- A flexible “shape knob” via the **b-factor**

In this project, the curve is anchored to known Year 1–3 yields from the materials and then extended to Years 4–10 with hyperbolic decline, then scaled to match the 10-year average target.

---

## `commodity_price_simulation.py` — Prices via Mean Reversion + Correlation
**Role:** Simulates oil/gas/NGL price *factors* over 10 years across many paths.

### Why mean reversion (Ornstein–Uhlenbeck)?
Commodity prices tend to exhibit:
- Shocks (big moves)
- Cycles
- Reversion toward an economic range (cost curves, substitution, demand response)

A pure random walk implies prices can drift arbitrarily far forever with no pullback. Mean reversion is a more realistic long-horizon approximation for energy commodities, especially when you are evaluating a 10-year asset.

### Why Cholesky decomposition?
Oil, gas, and NGL prices are correlated. You need correlated random shocks to avoid unrealistic paths (e.g., oil crashing while NGL simultaneously spikes every time). Cholesky decomposition is a standard way to transform independent standard normal draws into correlated draws that match a specified correlation matrix.

---

## `stochastic_decline_curve.py` — Decline-Curve Steepening Risk (b-factor & Di)
**Role:** Randomly perturbs decline curve parameters to reflect uncertainty in how production decays versus expectations.

### “Steepening” in plain English
A “steeper” decline means production drops faster than expected—cash comes in earlier but may be lower total, and the tail cash flows weaken. In this model, steepening is represented primarily by a lower **b-factor** and changes in **Di**.

---

## `cash_flows.py` — Financial Engine (Cash Flows + IRR/ROI/Payback + Terminal Value)
**Role:** Converts yields + prices into dollar cash flows, then computes the core investment metrics.

This file is the core bridge from “resource economics” to “private equity style metrics.”

### A. Cash flow construction (what the model literally does)
Cash flows are built as:

- **Year 0:** initial co-investment outflow (negative cash flow)
- **Years 1–10:** annual cash inflows approximated by:
  - `Investment × Yield_t × PriceFactor_t`
  - minus `Investment × G&A_rate`
- **Year 10:** adds **terminal value** on top of Year 10 operating cash

This is the minimum viable structure needed to reproduce the deck-style underwriting: a yield profile + price sensitivity + end-of-horizon value.

---

## `analysis.py` — Risk Engine (Monte Carlo, Percentiles, Scenarios, Breakeven)
**Role:** Runs the Monte Carlo simulation and deterministic scenarios:
- price-only stresses
- decline-only stresses
- combined stresses
- breakeven calculations

It also computes:
- probability of loss
- average loss conditional on losing
- percentile bands (P1/P5/…/P99) and which input ranges drive them

---

## `charts.py` — Visualization Layer
**Role:** Produces charts that turn the Monte Carlo output into intuitive artifacts:
- IRR histogram
- CDF (probability of achieving a target IRR)
- tornado sensitivity (risk drivers)
- price vs IRR scatter (colored by b-factor)
- yield curve visualization (front-loaded shape)

---

## `test_delay_scenarios.py` — Timing Risk Experiments (Sensitivity / Educational)
**Role:** Tests “development delay” style timing shifts, with emphasis on the important idea:

- **PDP (producing) cash flows are not delayed the way non-producing inventory is.**

This module is explicitly framed as sensitivity/education because deck NAV values often already embed discounting/timing risk.

---

# CORE METRICS: HOW THEY ARE CALCULATED (AND WHY THEY MATTER)

## 1) IRR (Internal Rate of Return)
### Definition (plain English)
IRR is the single annualized rate that makes the **present value** of all cash flows equal zero. In other words, it is the rate where “what you paid” equals “what you got back,” after discounting.

### Mathematical definition (lightweight)
IRR solves for `r` such that:

\[
\sum_{t=0}^{T} \frac{CF_t}{(1+r)^t} = 0
\]

### Why IRR is strongly tied to early-year PDP production
In a front-loaded yield curve, early years contribute disproportionately to IRR because:
- The denominator `(1+r)^t` grows with time `t`.
- Cash in Year 1–3 is barely discounted compared to Year 8–10.
- Therefore, a large chunk of value is “locked in” early.

**Interpretation:** If PDP (producing reserves) drives a large share of near-term cash yield, then IRR becomes less sensitive to far-out uncertainties (terminal value, late development, long-run decline), and more sensitive to what affects early cash (commodity prices, near-term volumes, near-term costs).

This is exactly why “PDP-backed downside” is a meaningful economic statement: the early cash mechanically anchors the IRR.

### Why Newton’s Method is used to compute IRR
There is no closed-form algebraic solution for IRR for arbitrary cash flow sequences. Newton-Raphson is a standard root-finding method:
- Start with a guess for `r`
- Compute NPV at that `r`
- Update `r` using the derivative until NPV ≈ 0

Why it was chosen here:
- Fast convergence for well-behaved cash flows
- Standard in finance tooling
- Transparent to implement and audit

---

## 2) ROI (Return on Investment / MOIC)
### Definition (plain English)
ROI here is essentially “multiple of invested capital”: total dollars returned divided by dollars invested.

### Implementation
If Year 0 is `-Investment`, then:

- **Total distributions** = sum of Years 1–10 cash inflows
- **ROI multiple** = (Total distributions) / (Investment)

This is intuitive: ROI tells you “how many times your money you got back,” but **it does not penalize slow timing** the way IRR does.

---

## 3) Payback Period
### Definition (plain English)
Payback is the time when cumulative cash flows turn from negative to non-negative.

Implementation:
- Compute cumulative sum of cash flows across years.
- Identify first year where cumulative ≥ 0.
- Interpolate within the year to estimate a fractional year payback.

Payback is important because it is a **downside/timing risk metric**:
- Fast payback means capital is recovered early.
- It is highly aligned with “PDP-backed downside” because PDP cash arrives immediately.

---

# BREAKEVEN OIL: HOW THE MODEL COMPUTES IT

The model computes a **breakeven price factor**: the constant multiplier on strip pricing that results in approximately **0% IRR**.

Mechanically:
- Start at 1.00 (100% of strip)
- Step downward until IRR crosses 0
- Record the factor (e.g., ~0.54× strip)

Then it converts that factor to a dollar/bbl number using a stated “strip oil ≈ $70/bbl” mapping.

Interpretation:
- “Breakeven is 54% of strip” means: if the long-run realized pricing environment is roughly half of strip levels (holding everything else constant), the investment’s IRR falls to ~0.

Important nuance:
- This is a **model-internal translation**, not a claim about the exact futures curve.
- It is meant to anchor intuition: “how low could oil go for this to stop working?”

---

# MONTE CARLO RISK METRICS: PROBABILITY OF LOSS AND AVERAGE LOSS

## Probability of Loss
After each simulated path, the model computes total profit:

- `Profit = sum(CF_t)` across all years (including Year 0 negative investment)

Then:

- **Loss event** occurs when `Profit < 0`

Probability of loss is simply:

- `Prob(Loss) = (# paths with Profit < 0) / (Total paths)`

This is the cleanest definition of “chance of losing money” under the simulated risk model.

## Average Loss (Conditional on Losing)
Among only the paths that lose money (`Profit < 0`), compute:

- `AvgLoss = mean(Profit | Profit < 0)`

This answers a different question than probability:
- Not “how often do we lose?”
- But “if we lose, how bad is it on average?”

These two metrics should always be read together.

---

# TERMINAL VALUE: ASSUMPTIONS AND MECHANICS

Terminal value represents the value of remaining reserves / remaining NAV at the end of Year 10.

### What the model assumes structurally
1. There is some percentage of reserves still remaining at Year 10 (a remaining NAV fraction).
2. That remaining NAV is scaled by:
   - the Year 10 price environment (price factor)
   - a market multiple that reflects “market sentiment” (less than 1.0 in stress cases)

### Why a terminal value is needed
Without a terminal value, a minerals/royalty asset model can be biased downward because:
- These assets usually continue producing beyond 10 years.
- A 10-year truncation artificially throws away long-tail cash and residual value.

### What terminal value is **not**
It is not a liquidation value in the bankruptcy sense.
It is a simplified proxy for “what a buyer would pay in year 10 for the remaining reserves,” conditional on prices and market discounting.

### Important modeling implication
Because this deal is front-loaded, terminal value usually contributes less to IRR than early cash flows. But it can materially affect ROI and long-tail economics.

---

# ECONOMIC INTERPRETATION: PDP-BACKED DOWNSIDE PROTECTION

### What “PDP-backed downside” means in this model
PDP is producing today. Producing reserves contribute cash flows immediately.

When:
- a large share of NAV is PDP
- and the yield curve is front-loaded

Then:
- the investment tends to recover capital earlier
- IRR is less exposed to delays in undeveloped inventory conversion
- late-life uncertainties have lower weight in IRR math

This is not a slogan; it is a property of discounting + timing.

---

# RISK DRIVERS MODELED (AND HOW THEY ENTER)

## 1) Commodity Price Risk (Modeled)
- Simulated via mean-reverting stochastic processes
- Correlated across oil/gas/NGL via Cholesky
- Impacts every year’s cash flow multiplicatively through `PriceFactor_t`

This is typically the dominant driver because it directly scales revenue/cash.

## 2) Decline-Curve Steepening / Yield Curve Risk (Modeled)
- Simulated via shocks to b-factor and Di
- Converts into a different yield curve shape / tail

This represents “production underperforms type curve expectations.”

## 3) Development Timing / Delay Risk (Sensitivity, not base MC)
- Explored in `test_delay_scenarios.py`
- Distinguishes PDP (not delayed) vs non-PDP (delayed)

This is included as an analytical tool to understand timing sensitivity.

---

# THE ROLE OF HEDGING (CONCEPTUALLY)

Hedging is not explicitly optimized in the base code, but it is a key economic lever in a front-loaded cash profile.

### Why hedging matters most here
Because early-year cash flows dominate IRR, hedging early volumes can:
- protect downside in the most IRR-sensitive window
- reduce probability-of-loss paths that are driven by early price crashes
- trade some upside for significantly improved drawdown control

In other words: if the early-year distribution is “convex” to prices, hedging can flatten the left tail.

A natural extension of this repo is:
- add a hedge layer that fixes a fraction of early-year price factors at a floor or collar
- then rerun Monte Carlo to quantify reduction in Prob(Loss) and tail outcomes

---

# RISKS NOT MODELED (IMPORTANT LIMITATIONS)

This model is intentionally focused on the *big mechanical drivers* of returns. Several real-world risks are not explicitly quantified:

## Operator Concentration Risk
The diligence materials indicate high concentration in top operators. If one operator changes behavior (capital allocation, drilling pace, completion timing, cost discipline), realized cash flows can diverge meaningfully. This is not modeled as a stochastic “operator regime” process.

## Regulatory / Setback / Permitting Risk
Colorado setback and permitting outcomes can alter conversion rates for non-PDP inventory and long-run activity. This repo does not model:
- probabilistic permit conversion
- location-level attrition
- scenario weights for regulatory tightening

## Basis / Differential Risk
“Price factor” is treated as a clean multiplier. Real realizations include:
- basin differentials
- transport constraints
- basis widening under stress

## Cost Inflation / LOE / Tax Complexity
The model uses a simplified G&A assumption. Real minerals cash flows can be affected by:
- operator-level cost behavior affecting netbacks
- production taxes
- midstream and marketing effects

## Financing / Distribution Waterfall / Timing Mechanics
If distributions are delayed, escrowed, or managed with a different cadence than modeled, IRR can move. This repo treats annualized cash timing directly.

---

# HOW TO RUN (WINDOWS)

### 1) Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run the full analysis
```bash
python main.py
```

Charts are saved to the working directory (as printed in the console output).

---

# WHAT TO LOOK AT FIRST (RECOMMENDED READING ORDER)

If you’re new to the repo:

1. `main.py` (what runs)
2. `config.py` (what assumptions are)
3. `yield_curve.py` (why cash is front-loaded)
4. `cash_flows.py` (how IRR/ROI/payback are computed)
5. `analysis.py` (how the Monte Carlo is built)
6. `commodity_price_simulation.py` (why mean reversion + Cholesky)
7. `charts.py` (how results are presented)

---

# AUTHOR

Independent analysis by: **Nader Liddawi**
