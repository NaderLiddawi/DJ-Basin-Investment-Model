"""
FORTITUDE RE: DJ BASIN INVESTMENT MODEL
Configuration and Constants
===========================
All input parameters from the investment deck.

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

# Each Category below is discounted at different percentages (for example PDP is at PV-10 and Undeveloped is at PV-20, etc.)
NAV_BY_CATEGORY = {
    'PDP': 691,         # 66% of NAV - Proven Developed Producing
    'DUC': 123,         # 11% - Drilled but Uncompleted
    'Permit': 39,       # 4% - Permitted locations
    'APD': 91,          # 9% - Applications for Permit to Drill
    'Undeveloped': 108  # 10% - Undrilled, unpermitted
}
TOTAL_NAV_MM = sum(NAV_BY_CATEGORY.values())  # $1,052MM

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

'''
D_i = 0.25 because at year 3, the decline rate is this:
    Year 1: Wells decline ~65%
    Year 2: Wells decline ~35%
    Year 3: Wells decline ~25%
'''

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

REMAINING_RESERVES_PCT = 0.15  # 15% of reserves remain at Year 10 (discounted lifetime value) after yield was taken from Year 10
