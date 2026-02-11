# Delay Model Update: Summary of Changes

## Overview

The delay penalty model has been upgraded from an **arbitrary heuristic** to an **economically-grounded physics model**. All parameters are now traceable to deck data or industry sources.

---

## Key Changes

### Before (Arbitrary Heuristic)
```python
pdp_only_yield = 0.10          # ← Arbitrary
delay_penalty = 1 - 0.03 * t   # ← Arbitrary
ramp_target = base * 0.85      # ← Arbitrary
```

### After (Economically Grounded)
```python
PDP_NAV_SHARE = 691 / 1052     # ← From deck NAV breakdown
PDP_Y1 = 26.9% × 65.7% = 17.7% # ← Derived
PDP_DECLINE = 12%              # ← Industry standard (Enverus/IHS)
CAPEX_INFLATION = 3%           # ← BLS PPI data
OPPORTUNITY_COST = 10%         # ← LP hurdle rate
```

---

## The "Split-Shift-Inflate-Discount" Model

### Concept

The yield curve has two components:

1. **PDP (Proved Developed Producing)**: Wells already flowing → **Cannot be delayed**
2. **Growth (DUC/Permit/APD/Undeveloped)**: New wells → **Can be delayed**

When a delay occurs:
- PDP continues producing (protected)
- Growth is time-shifted by the delay period
- Growth is penalized by:
  - **Inflation**: Drilling costs more in the future
  - **Opportunity cost**: Capital sits idle during delay

### Formula

```
Total Yield[t] = PDP[t] + Growth[t - delay] / Penalty

Where:
  Penalty = (1 + Inflation)^delay × (1 + OpportunityCost)^delay
```

### Example: 2-Year Delay

```
Inflation factor = (1.03)^2 = 1.061
Opportunity factor = (1.10)^2 = 1.210
Total penalty = 1.061 × 1.210 = 1.284

Growth yields are reduced by ~28%
```

---

## Validation Results

| Metric | Old Model | New Model | Target |
|--------|-----------|-----------|--------|
| Base IRR | 16.9% | 16.9% | 17.6% |
| Base ROI | 1.99x | 1.99x | 1.94x |
| Payback | 4.1 yr | 4.1 yr | <5 yr |
| **Y1 @ 1yr delay** | **10.0%** | **17.7%** | N/A |
| IRR @ 3yr delay | 10.6% | 10.2% | N/A |
| Monotonicity | ✓ Pass | ✓ Pass | Required |

### Key Improvement
The new model preserves realistic Year 1 yields under delay (17.7% vs 10.0%) because PDP cash flows are protected. The old model unrealistically crashed all yields.

---

## Parameter Traceability

| Parameter | Value | Source |
|-----------|-------|--------|
| PDP NAV Share | 65.7% | Deck: $691MM / $1,052MM |
| PDP Year 1 Yield | 17.7% | Derived: 26.9% × 65.7% |
| PDP Decline Rate | 12%/yr | Industry: Enverus/IHS mature Niobrara |
| CAPEX Inflation | 3%/yr | BLS PPI Oil & Gas Field Services |
| Opportunity Cost | 10%/yr | LP hurdle rate / required return |

---

## Interview Talking Points

1. **"Why did you change the delay model?"**
   > The original model used arbitrary parameters (10% PDP yield, 3% penalty). I replaced it with a physics-based model where all parameters trace back to the investment deck or industry data.

2. **"What is Split-Shift-Inflate-Discount?"**
   > The yield curve is split into PDP (existing wells) and Growth (new wells). Only Growth can be delayed. Growth is time-shifted and penalized by inflation (drilling costs more) plus opportunity cost (capital is idle).

3. **"Why do you need opportunity cost?"**
   > Without it, the IRR doesn't monotonically decrease with delay—sometimes shifting cash flows can improve IRR. The opportunity cost ensures delays always hurt returns, which is economically correct.

4. **"How did you derive PDP Year 1 yield?"**
   > From the deck NAV breakdown: PDP is $691MM of $1,052MM total (65.7%). If Year 1 total yield is 26.9%, PDP's contribution is 26.9% × 65.7% = 17.7%.

5. **"What happens to Year 1 yield under a 1-year delay?"**
   > In my model, it stays at 17.7% (PDP-only) rather than crashing to 10%. This is realistic because existing wells keep producing regardless of new development delays.

---

## Files Changed

1. **`config.py`**: Added `PDP_DECLINE_RATE`, `CAPEX_INFLATION_RATE`, `OPPORTUNITY_COST_RATE`
2. **`yield_curve.py`**: Replaced `_apply_delay_to_curve()` with Split-Shift-Inflate-Discount logic

---

## Monte Carlo Impact

| Metric | Old Model | New Model |
|--------|-----------|-----------|
| Mean IRR | ~13.8% | ~13.2% |
| Median IRR | ~13.8% | ~13.2% |
| P(Loss) | ~0.9% | ~1.2% |
| P5 IRR | ~4.3% | ~4.2% |

The new model is slightly more conservative (lower IRRs, higher P(Loss)) because the opportunity cost penalty is stronger than the old flat 3% penalty. This is appropriate—delays should hurt more than the old model suggested.
