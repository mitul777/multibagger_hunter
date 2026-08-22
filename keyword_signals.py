# =============================================================================
# keyword_signals.py — Moat Language Dictionary for Concall / Filing Analysis
# =============================================================================
# When companies talk about their moat, specific language patterns emerge.
# This module defines those patterns and their weights.
# =============================================================================

# ---------------------------------------------------------------------------
# POSITIVE moat signals — language that indicates a durable advantage
# ---------------------------------------------------------------------------

MOAT_KEYWORDS = {

    # ---- Pricing Power -------------------------------------------------------
    "pricing_power": {
        "weight": 3,
        "phrases": [
            "price increase", "price hike", "price revision", "pricing power",
            "pass through", "pass-through", "pass on the cost",
            "premium pricing", "premium product", "value pricing",
            "realisation increase", "higher realisations",
            "customers accepted", "no pushback on pricing",
        ],
    },

    # ---- Switching Costs / Sticky Customers ----------------------------------
    "switching_costs": {
        "weight": 4,
        "phrases": [
            "switching cost", "switching costs", "long-term contract",
            "multi-year contract", "multi year agreement", "3-year contract",
            "5-year contract", "sole supplier", "sole source",
            "preferred supplier", "preferred vendor", "approved vendor",
            "qualified supplier", "vendor qualification",
            "mission critical", "mission-critical",
            "integrated into customer", "embedded in",
            "difficult to replace", "no substitute",
            "captive customer", "repeat orders", "repeat business",
            "renewal rate", "retention rate", "customer stickiness",
        ],
    },

    # ---- Order Book / Revenue Visibility ------------------------------------
    "order_book": {
        "weight": 2,
        "phrases": [
            "order book", "order backlog", "order intake", "order inflow",
            "outstanding orders", "strong pipeline", "robust pipeline",
            "order visibility", "revenue visibility", "executable backlog",
            "bid pipeline", "enquiry pipeline", "tendering pipeline",
            "L1 position", "lowest bidder",
        ],
    },

    # ---- Market Dominance / Leadership ---------------------------------------
    "market_leadership": {
        "weight": 3,
        "phrases": [
            "market leader", "market leadership", "number one", "#1",
            "market share gain", "gaining market share",
            "dominant player", "market dominant",
            "60% market share", "70% market share", "80% market share",
            "50% market share", "largest player", "largest manufacturer",
            "category leader", "category creator",
        ],
    },

    # ---- Technology / IP / Barrier to Entry ---------------------------------
    "technology_moat": {
        "weight": 3,
        "phrases": [
            "proprietary technology", "proprietary process",
            "patent", "patented", "trade secret",
            "know-how", "process know-how", "technology advantage",
            "technology barrier", "entry barrier", "high barrier",
            "difficult to replicate", "hard to replicate",
            "reverse engineer", "regulatory approval",
            "qualification process", "qualification barrier",
            "niche chemistry", "specialty chemistry",
        ],
    },

    # ---- Capacity / Scale Moat -----------------------------------------------
    "scale_moat": {
        "weight": 2,
        "phrases": [
            "backward integration", "backward integrated",
            "forward integration", "vertical integration",
            "economies of scale", "scale advantage",
            "capacity expansion", "brownfield expansion",
            "debottlenecking", "cost advantage",
            "largest capacity", "world-scale plant",
        ],
    },

    # ---- Export / Global Footprint ------------------------------------------
    "global_reach": {
        "weight": 2,
        "phrases": [
            "export growth", "increasing exports", "export market",
            "global customer", "multinational customer", "MNC customer",
            "regulated market", "FDA approved", "USFDA",
            "EU GMP", "EDQM", "Japan approval", "global supply",
            "import substitute", "import substitution",
        ],
    },

    # ---- Promoter / Management Confidence -----------------------------------
    "management_confidence": {
        "weight": 2,
        "phrases": [
            "promoter buying", "insider purchase", "open market purchase",
            "buyback", "buy back shares",
            "increasing promoter stake", "promoter increased",
            "confident of growth", "strong visibility",
            "guidance maintained", "guidance upgraded",
        ],
    },
}

# ---------------------------------------------------------------------------
# NEGATIVE signals — language that indicates moat weakness or concern
# ---------------------------------------------------------------------------

RED_FLAG_KEYWORDS = {

    # ---- Competitive Pressure ------------------------------------------------
    "competition": {
        "weight": 3,
        "phrases": [
            "pricing pressure", "price pressure", "competitive pressure",
            "competition increased", "intense competition",
            "market share loss", "losing market share",
            "new entrant", "new competition", "cheaper alternative",
            "commoditised", "commoditized", "commodity business",
        ],
    },

    # ---- Margin Stress -------------------------------------------------------
    "margin_stress": {
        "weight": 2,
        "phrases": [
            "margin pressure", "margin compression", "lower margins",
            "input cost increase", "raw material pressure",
            "unable to pass on", "unable to take price increase",
            "demand weakness", "volume decline", "volume pressure",
        ],
    },

    # ---- Financial Risk ------------------------------------------------------
    "financial_risk": {
        "weight": 3,
        "phrases": [
            "debt increased", "leverage increased", "stressed balance sheet",
            "promoter pledging", "pledge increased", "shares pledged",
            "working capital stressed", "receivables high",
            "cash flow negative", "FCF negative",
            "going concern", "restructuring",
        ],
    },

    # ---- Execution Risk ------------------------------------------------------
    "execution_risk": {
        "weight": 2,
        "phrases": [
            "delayed execution", "project delay", "cost overrun",
            "order cancellation", "order deferral",
            "management change", "promoter exit",
            "guidance missed", "guidance cut",
            "disappointed", "challenges in",
        ],
    },
}

# ---------------------------------------------------------------------------
# Moat category → qualitative label
# ---------------------------------------------------------------------------

MOAT_CATEGORY_LABELS = {
    "pricing_power":       "💰 Pricing Power",
    "switching_costs":     "🔒 High Switching Costs",
    "order_book":          "📋 Revenue Visibility",
    "market_leadership":   "👑 Market Dominance",
    "technology_moat":     "⚗️ Technology Barrier",
    "scale_moat":          "🏭 Scale Advantage",
    "global_reach":        "🌍 Global / Export Moat",
    "management_confidence": "👔 Management Conviction",
}
