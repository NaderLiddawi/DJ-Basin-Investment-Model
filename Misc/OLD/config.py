"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Configuration and Constants
===========================
All input parameters from the investment deck.

CHANGELOG:
- Updated delay penalty parameters to use economically-grounded model
- PDP parameters now derived from deck NAV breakdown
- Added opportunity cost rate for time-value-of-money penalty
"""

# ==============================================================================
# CAPITAL STRUCTURE
# ==============================================================================

PURCHASE_PRICE_MM = 905.0
DEBT_MM = 178.0
CLOSING_COSTS_MM = 5.0
POST_EFF_DATE_CF_MM = 22.0
TOTAL_EQUITY_MM = 710.0  # = 905 - 178 + 5 - 22
CO_INVEST_MM = 195.0
CO_INVEST_SHARE = CO_INVEST_MM / TOTAL_EQUITY_MM  # ~27.5%

# ==============================================================================
# G&A COSTS
# ==============================================================================

GA_RATE = 0.0075  # 75 bps of invested capital

# ==============================================================================
# TARGET RETURNS (From Deck)
# ==============================================================================

TARGET_IRR = 0.176  # 17.6%
TARGET_ROI = 1.94   # 1.94x

# ==============================================================================
# NAV BREAKDOWN BY RESERVE CATEGORY
# ==============================================================================

NAV_BY_CATEGORY = {
    'PDP': 691,         # 66% of NAV - Proven Developed Producing
    'DUC': 123,         # 11% - Drilled but Uncompleted
    'Permit': 39,       # 4% - Permitted locations
    'APD': 91,          # 9% - Applications for Permit to Drill
    'Undeveloped': 108  # 10% - Undrilled, unpermitted
}
TOTAL_NAV_MM = sum(NAV_BY_CATEGORY.values())  # $1,052MM

# ==============================================================================
# RETURN CONTRIBUTION BY CATEGORY
# ==============================================================================

RETURN_CONTRIBUTION = {
    'PDP': 1.0,
    'DUC': 0.2,
    'Permit': 0.1,
    'APD': 0.3,
    'Undeveloped': 0.4
}

# ==============================================================================
# COMMODITY MIX
# ==============================================================================

COMMODITY_MIX = {
    'oil': 0.32,
    'gas': 0.40,
    'ngl': 0.28
}

# ==============================================================================
# OPERATOR CONCENTRATION
# ==============================================================================

OPERATOR_AA_NAV_SHARE = 0.52
OPERATOR_BB_NAV_SHARE = 0.22
TOP_2_OPERATOR_SHARE = OPERATOR_AA_NAV_SHARE + OPERATOR_BB_NAV_SHARE  # 74%

# ==============================================================================
# YIELD DATA (From Projected Returns Summary)
# ==============================================================================

YIELD_Y1 = 0.269  # 26.9% (2025)
YIELD_Y2 = 0.266  # 26.6% (2026)
YIELD_Y3 = 0.251  # 25.1% (2027)
AVG_10Y_YIELD = 0.186  # 18.6% average

# ==============================================================================
# DOWNSIDE PROTECTION
# ==============================================================================

PDP_PV0_COVERAGE = 1.34  # 1.34x coverage

# ==============================================================================
# TIMING RISK PARAMETERS
# ==============================================================================

TIMING_RISK_PARAMS = {
    'PDP': {'delay_prob': 0.02, 'max_delay_years': 0},
    'DUC': {'delay_prob': 0.15, 'max_delay_years': 1},
    'Permit': {'delay_prob': 0.25, 'max_delay_years': 2},
    'APD': {'delay_prob': 0.40, 'max_delay_years': 3},
    'Undeveloped': {'delay_prob': 0.50, 'max_delay_years': 4}
}

# ==============================================================================
# DECLINE CURVE PARAMETERS
# ==============================================================================

DECLINE_CURVE_PARAMS = {
    'base_b_factor': 0.9,       # Hyperbolic exponent
    'stress_b_factor': 0.5,     # Steep decline scenario
    'severe_b_factor': 0.3,     # Near-exponential decline
    'b_factor_volatility': 0.12,  # Standard deviation
    'base_Di': 0.25,            # Initial decline rate (25%/year)
    'Di_volatility': 0.05       # Standard deviation
}

# ==============================================================================
# DELAY MODEL PARAMETERS (Economically Grounded)
# ==============================================================================
# 
# The delay model uses "Split-Shift-Inflate-Discount" logic:
#   1. PDP cash flows are protected (already producing, cannot be delayed)
#   2. Growth cash flows (DUC/Permit/APD/Undeveloped) are time-shifted
#   3. Growth suffers TWO penalties:
#      a) CAPEX inflation (drilling costs more in the future)
#      b) Opportunity cost (time-value of capital during delay)
#
# This ensures IRR decreases monotonically with delay (required for valid model).
# ==============================================================================

# PDP Decline Rate: Industry standard for mature DJ Basin wells
# Source: Enverus/IHS decline curve databases show 10-15% for mature Niobrara
PDP_DECLINE_RATE = 0.12  # 12% annual harmonic decline

# CAPEX Inflation Rate: Service cost escalation
# Source: BLS Producer Price Index for Oil & Gas Field Services (~2-4% historical)
CAPEX_INFLATION_RATE = 0.03  # 3% annual inflation

# Opportunity Cost Rate: Cost of capital during idle delay period
# Source: Aligned with LP hurdle rate / required return expectations
# This parameter ensures IRR monotonically decreases with delay
OPPORTUNITY_COST_RATE = 0.10  # 10% annual opportunity cost

# Legacy parameters (kept for backward compatibility, no longer used)
DELAY_PENALTY_RATE = 0.03  # DEPRECATED: Use CAPEX_INFLATION_RATE
DELAY_PENALTY_FLOOR = 0.75  # DEPRECATED: No longer needed

# ==============================================================================
# PRICE SIMULATION PARAMETERS (Ornstein-Uhlenbeck)
# ==============================================================================

PRICE_PARAMS = {
    'oil': {'mu': 1.0, 'theta': 0.3, 'sigma': 0.25, 'current': 1.0},
    'gas': {'mu': 1.0, 'theta': 0.5, 'sigma': 0.45, 'current': 1.0},
    'ngl': {'mu': 1.0, 'theta': 0.35, 'sigma': 0.30, 'current': 1.0}
}

# Correlation matrix [oil, gas, ngl]
PRICE_CORRELATION = [
    [1.0, 0.35, 0.75],
    [0.35, 1.0, 0.40],
    [0.75, 0.40, 1.0]
]

# ==============================================================================
# SIMULATION PARAMETERS
# ==============================================================================

NUM_SIMULATIONS = 50000
SIMULATION_YEARS = 10
RANDOM_SEED = 42

# ==============================================================================
# TERMINAL VALUE PARAMETERS
# ==============================================================================

REMAINING_RESERVES_PCT = 0.15  # 15% of reserves remain at Year 10
