# =============================================================================
# config.py — Universe & Thresholds for Indian Equity Moat Screener
# =============================================================================
# Data Source  : Yahoo Finance (yfinance) — NSE tickers with .NS suffix
# Coverage     : ~150 stocks across Nifty 500 universe
# =============================================================================

# ---------------------------------------------------------------------------
# Stock Universe — NSE tickers (.NS suffix)
# ---------------------------------------------------------------------------
STOCK_UNIVERSE = {
    "Financials": [
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "AXISBANK.NS",
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIGI.NS",
        "CHOLAFIN.NS", "MUTHOOTFIN.NS", "SUNDARMFIN.NS", "CAMS.NS", "CDSL.NS",
        "MCX.NS", "BSE.NS",
    ],
    "Information Technology": [
        "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS",
        "LTIMINDLTD.NS", "MPHASIS.NS", "PERSISTENT.NS", "COFORGE.NS", "KPITTECH.NS",
        "TATAELXSI.NS", "OFSS.NS", "MASTEK.NS",
    ],
    "Consumer Staples": [
        "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
        "MARICO.NS", "COLPAL.NS", "GODREJCP.NS", "TATACONSUM.NS", "EMAMILTD.NS",
        "VBL.NS", "RADICO.NS",
    ],
    "Consumer Discretionary": [
        "MARUTI.NS", "TITAN.NS", "TRENT.NS", "PAGEIND.NS", "RELAXO.NS",
        "DMART.NS", "IRCTC.NS",
    ],
    "Healthcare & Pharma": [
        "SUNPHARMA.NS", "DIVISLAB.NS", "CIPLA.NS", "DRREDDY.NS", "BIOCON.NS",
        "TORNTPHARM.NS", "ALKEM.NS", "IPCALAB.NS", "LALPATHLAB.NS", "METROPOLIS.NS",
        "ABBOTINDIA.NS", "PFIZER.NS", "SANOFI.NS", "GLAXO.NS",
    ],
    "Automobiles": [
        "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "TVSMOTOR.NS",
        "TATAMOTORS.NS", "M&M.NS", "BOSCHLTD.NS", "MOTHERSON.NS",
        "BALKRISIND.NS", "MRF.NS",
    ],
    "Capital Goods & Industrials": [
        "ABB.NS", "SIEMENS.NS", "HAVELLS.NS", "POLYCAB.NS", "DIXON.NS",
        "CUMMINSIND.NS", "THERMAX.NS", "VOLTAS.NS", "BHEL.NS",
        "GRINDWELL.NS", "TIMKEN.NS", "SCHAEFFLER.NS",
    ],
    "Chemicals & Materials": [
        "PIDILITIND.NS", "ASIANPAINT.NS", "BERGEPAINT.NS", "ASTRAL.NS",
        "SUPREMEIND.NS", "APLAPOLLO.NS", "SRF.NS", "AAVAS.NS",
        "FINPIPE.NS", "GALAXYSURF.NS",
    ],
    "Specialty & Niche": [
        "UNITDSPR.NS", "HONAUT.NS",
        "3MINDIA.NS", "WHIRLPOOL.NS",
    ],
    "Energy & Utilities": [
        "POWERGRID.NS", "NTPC.NS", "TATAPOWER.NS", "RELIANCE.NS",
    ],
    "Telecom": [
        "BHARTIARTL.NS",
    ],
    "Cement": [
        "ULTRACEMCO.NS", "AMBUJACEM.NS",
    ],
    "Conglomerates & Infra": [
        "LT.NS", "ADANIPORTS.NS",
    ],
}

# Flat universe list
ALL_STOCKS = [ticker for sector_list in STOCK_UNIVERSE.values() for ticker in sector_list]

# ---------------------------------------------------------------------------
# Scoring Thresholds — Calibrated for Indian Market Conditions
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # --- Moat Indicators (40 points total) ---
    "roce": {
        "excellent": 25.0,   # >= 25% ROCE → full points
        "good":      18.0,   # >= 18% ROCE → partial points
        "minimum":   12.0,   # >= 12% ROCE → entry level
        "weight":    15,     # max points
    },
    "roce_consistency": {
        "low_cv":    0.15,   # Coefficient of variation < 15% → consistent
        "med_cv":    0.30,   # < 30% → somewhat consistent
        "weight":    10,
    },
    "gross_margin": {
        "excellent": 50.0,   # >= 50% → exceptional pricing power
        "good":      35.0,   # >= 35% → good
        "minimum":   20.0,   # >= 20% → acceptable
        "weight":    10,
    },
    "fcf_conversion": {
        "excellent": 0.90,   # FCF/Net Income >= 90% → excellent cash earnings
        "good":      0.70,   # >= 70%
        "minimum":   0.50,   # >= 50%
        "weight":    5,
    },

    # --- Quality Indicators (25 points total) ---
    "debt_equity": {
        "excellent": 0.10,   # D/E < 0.1 → virtually debt-free
        "good":      0.50,   # D/E < 0.5
        "maximum":   1.50,   # D/E > 1.5 → penalised
        "weight":    10,
    },
    "cfo_pat": {
        "excellent": 1.00,   # CFO/PAT > 1.0 → high earnings quality
        "good":      0.80,
        "minimum":   0.60,
        "weight":    10,
    },
    "interest_coverage": {
        "excellent": 20.0,   # EBIT/Interest > 20x → very safe
        "good":      10.0,
        "minimum":   5.0,
        "weight":    5,
    },

    # --- Growth Indicators (25 points total) ---
    "revenue_cagr": {
        "excellent": 18.0,   # > 18% CAGR — high growth
        "good":      12.0,   # > 12% CAGR
        "minimum":    8.0,   # > 8% CAGR
        "weight":    15,
    },
    "eps_cagr": {
        "excellent": 20.0,
        "good":      12.0,
        "minimum":    8.0,
        "weight":    10,
    },

    # --- Efficiency Indicators (10 points total) ---
    "asset_turnover": {
        "excellent": 1.20,   # Higher is better for non-financial companies
        "good":      0.80,
        "minimum":   0.50,
        "weight":    5,
    },
    "operating_leverage": {
        "weight":    5,      # Operating margin expansion over years
    },
}

# ---------------------------------------------------------------------------
# Scoring Weights Summary
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "moat":       40,   # ROCE, consistency, margins, FCF
    "quality":    25,   # Debt, CFO quality, coverage
    "growth":     25,   # Revenue & EPS CAGR
    "efficiency": 10,   # Turnover, operating leverage
    # Total      100
}

# ---------------------------------------------------------------------------
# Screen Filters — Pre-screen before scoring (hard cutoffs)
# ---------------------------------------------------------------------------
HARD_FILTERS = {
    "min_market_cap_cr": 1000,    # Minimum ₹1,000 Cr market cap
    "min_revenue_cr":     200,    # Minimum ₹200 Cr revenue
    "max_debt_equity":    3.0,    # D/E < 3 (excludes heavily leveraged)
    "min_roce_pct":       10.0,   # At least 10% ROCE
    "min_years_data":      2,     # At least 2 years of financial history
}

# ---------------------------------------------------------------------------
# Output Settings
# ---------------------------------------------------------------------------
OUTPUT = {
    "top_n_display":       25,    # Top N companies to display
    "excel_output":       True,
    "html_output":        True,
    "output_dir":         "output",
    "score_thresholds": {
        "strong_moat":    70,     # Score >= 70 → Strong Moat
        "emerging_moat":  50,     # Score >= 50 → Emerging Moat
        "watchlist":      35,     # Score >= 35 → Watchlist
    },
}

# ---------------------------------------------------------------------------
# Sector Classification (for relative scoring context)
# ---------------------------------------------------------------------------
# High-margin sectors where gross margin thresholds differ
HIGH_MARGIN_SECTORS = {
    "Information Technology", "Healthcare & Pharma", "Financials",
    "Consumer Staples", "Specialty & Niche"
}

# Capital-intensive sectors (lower asset turnover expected)
CAPITAL_INTENSIVE_SECTORS = {
    "Energy & Utilities", "Cement", "Conglomerates & Infra", "Automobiles"
}
