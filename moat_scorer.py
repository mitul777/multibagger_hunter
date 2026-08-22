# =============================================================================
# moat_scorer.py — Score Companies on Moat Strength (0–100)
# =============================================================================
# Scoring Dimensions:
#   Moat      (40 pts): ROCE level, ROCE consistency, Gross Margin, FCF quality
#   Quality   (25 pts): Debt/Equity, CFO/PAT, Interest Coverage
#   Growth    (25 pts): Revenue CAGR, EPS/NI CAGR
#   Efficiency(10 pts): Asset Turnover, Operating Leverage
# =============================================================================

import numpy as np
from config import THRESHOLDS, OUTPUT


class MoatScorer:
    """
    Scores a company on a 0–100 scale based on moat quality indicators.
    Designed for Indian equities — thresholds calibrated accordingly.
    """

    def score(self, metrics: dict) -> dict:
        """
        Compute full score for a company.

        Returns:
            metrics dict enriched with score fields.
        """
        m = metrics

        moat_score  = self._score_moat(m)
        qual_score  = self._score_quality(m)
        growth_score = self._score_growth(m)
        eff_score   = self._score_efficiency(m)

        total = round(moat_score + qual_score + growth_score + eff_score, 1)

        m["score_moat"]       = round(moat_score, 1)
        m["score_quality"]    = round(qual_score, 1)
        m["score_growth"]     = round(growth_score, 1)
        m["score_efficiency"] = round(eff_score, 1)
        m["score_total"]      = total
        m["moat_label"]       = self._label(total)
        m["moat_signals"]     = self._describe_signals(m)

        return m

    # -------------------------------------------------------------------------
    # 1. MOAT Score (40 points)
    # -------------------------------------------------------------------------

    def _score_moat(self, m: dict) -> float:
        score = 0.0
        t = THRESHOLDS

        # A) ROCE Average (15 points)
        roce = m.get("roce_avg", np.nan)
        if not np.isnan(roce):
            cfg = t["roce"]
            if roce >= cfg["excellent"]:
                score += cfg["weight"]                              # 15 pts
            elif roce >= cfg["good"]:
                score += cfg["weight"] * 0.75                      # 11.25 pts
            elif roce >= cfg["minimum"]:
                score += cfg["weight"] * 0.45                      # 6.75 pts

        # B) ROCE Consistency — low CV is good (10 points)
        roce_cv = m.get("roce_cv", np.nan)
        if not np.isnan(roce_cv):
            cfg = t["roce_consistency"]
            if roce_cv < cfg["low_cv"]:
                score += cfg["weight"]                              # 10 pts
            elif roce_cv < cfg["med_cv"]:
                score += cfg["weight"] * 0.60                      # 6 pts
            else:
                score += cfg["weight"] * 0.20                      # 2 pts

        # Bonus: ROCE trend is positive (improving moat)
        if not np.isnan(m.get("roce_trend", np.nan)) and m["roce_trend"] > 0:
            score += 2.0  # bonus

        # C) Gross Margin Average (10 points)
        gm = m.get("gross_margin_avg", np.nan)
        if not np.isnan(gm):
            cfg = t["gross_margin"]
            if gm >= cfg["excellent"]:
                score += cfg["weight"]                              # 10 pts
            elif gm >= cfg["good"]:
                score += cfg["weight"] * 0.65                      # 6.5 pts
            elif gm >= cfg["minimum"]:
                score += cfg["weight"] * 0.35                      # 3.5 pts

        # Bonus: Gross margin stability (low CV)
        gm_cv = m.get("gross_margin_cv", np.nan)
        if not np.isnan(gm_cv) and gm_cv < 0.10:
            score += 1.5  # very stable margins bonus

        # D) FCF Conversion (5 points)
        fcf_conv = m.get("fcf_conversion_avg", np.nan)
        if not np.isnan(fcf_conv):
            cfg = t["fcf_conversion"]
            if fcf_conv >= cfg["excellent"]:
                score += cfg["weight"]                              # 5 pts
            elif fcf_conv >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif fcf_conv >= cfg["minimum"]:
                score += cfg["weight"] * 0.30

        # Cap at 40
        return min(score, 40.0)

    # -------------------------------------------------------------------------
    # 2. QUALITY Score (25 points)
    # -------------------------------------------------------------------------

    def _score_quality(self, m: dict) -> float:
        score = 0.0
        t = THRESHOLDS

        # A) Debt/Equity — lower is better (10 points)
        de = m.get("debt_equity_latest", np.nan)
        if not np.isnan(de):
            cfg = t["debt_equity"]
            if de <= cfg["excellent"]:
                score += cfg["weight"]                              # 10 pts
            elif de <= cfg["good"]:
                score += cfg["weight"] * 0.70
            elif de <= 1.0:
                score += cfg["weight"] * 0.40
            elif de <= cfg["maximum"]:
                score += cfg["weight"] * 0.15
            # > 1.5: 0 points

        # Net cash bonus
        net_cash = m.get("net_cash_cr", np.nan)
        if not np.isnan(net_cash) and net_cash > 0:
            score += 2.0  # net cash positive company bonus

        # B) CFO/PAT ratio — earnings quality (10 points)
        cfo_pat = m.get("cfo_pat_avg", np.nan)
        if not np.isnan(cfo_pat):
            cfg = t["cfo_pat"]
            if cfo_pat >= cfg["excellent"]:
                score += cfg["weight"]
            elif cfo_pat >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif cfo_pat >= cfg["minimum"]:
                score += cfg["weight"] * 0.30

        # C) Interest Coverage (5 points)
        ic = m.get("interest_coverage_avg", np.nan)
        if not np.isnan(ic):
            cfg = t["interest_coverage"]
            if ic >= cfg["excellent"]:
                score += cfg["weight"]
            elif ic >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif ic >= cfg["minimum"]:
                score += cfg["weight"] * 0.30

        # Cap at 25
        return min(score, 25.0)

    # -------------------------------------------------------------------------
    # 3. GROWTH Score (25 points)
    # -------------------------------------------------------------------------

    def _score_growth(self, m: dict) -> float:
        score = 0.0
        t = THRESHOLDS

        # A) Revenue CAGR (15 points)
        rev_cagr = m.get("rev_cagr", np.nan)
        if not np.isnan(rev_cagr):
            cfg = t["revenue_cagr"]
            if rev_cagr >= cfg["excellent"]:
                score += cfg["weight"]
            elif rev_cagr >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif rev_cagr >= cfg["minimum"]:
                score += cfg["weight"] * 0.35
            # Negative or near-zero: 0

        # B) EPS / Net Income CAGR (10 points)
        eps_cagr = m.get("eps_cagr", np.nan)
        if not np.isnan(eps_cagr):
            cfg = t["eps_cagr"]
            if eps_cagr >= cfg["excellent"]:
                score += cfg["weight"]
            elif eps_cagr >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif eps_cagr >= cfg["minimum"]:
                score += cfg["weight"] * 0.35

        # Quality-of-growth bonus: EPS growing faster than revenue = margin expansion
        if (not np.isnan(rev_cagr) and not np.isnan(eps_cagr)
                and eps_cagr > rev_cagr and eps_cagr > 0):
            score += 1.5

        # Cap at 25
        return min(score, 25.0)

    # -------------------------------------------------------------------------
    # 4. EFFICIENCY Score (10 points)
    # -------------------------------------------------------------------------

    def _score_efficiency(self, m: dict) -> float:
        score = 0.0
        t = THRESHOLDS

        # A) Asset Turnover (5 points)
        at = m.get("asset_turnover_avg", np.nan)
        if not np.isnan(at):
            cfg = t["asset_turnover"]
            if at >= cfg["excellent"]:
                score += cfg["weight"]
            elif at >= cfg["good"]:
                score += cfg["weight"] * 0.65
            elif at >= cfg["minimum"]:
                score += cfg["weight"] * 0.30

        # B) Operating Leverage — >1 suggests fixed-cost leverage (5 points)
        op_lev = m.get("operating_leverage", np.nan)
        if not np.isnan(op_lev):
            if op_lev > 1.5:
                score += t["operating_leverage"]["weight"]          # 5 pts
            elif op_lev > 1.0:
                score += t["operating_leverage"]["weight"] * 0.55
            elif op_lev > 0:
                score += t["operating_leverage"]["weight"] * 0.20

        # Cap at 10
        return min(score, 10.0)

    # -------------------------------------------------------------------------
    # Labeling
    # -------------------------------------------------------------------------

    @staticmethod
    def _label(score: float) -> str:
        thresholds = OUTPUT["score_thresholds"]
        if score >= thresholds["strong_moat"]:
            return "🏰 Strong Moat"
        elif score >= thresholds["emerging_moat"]:
            return "🌱 Emerging Moat"
        elif score >= thresholds["watchlist"]:
            return "👀 Watchlist"
        else:
            return "❌ No Moat"

    # -------------------------------------------------------------------------
    # Signal Description — Human-readable moat signals
    # -------------------------------------------------------------------------

    @staticmethod
    def _describe_signals(m: dict) -> list[str]:
        """Return list of key positive moat signals found."""
        signals = []

        roce = m.get("roce_avg", np.nan)
        if not np.isnan(roce) and roce >= 20:
            signals.append(f"High ROCE ({roce:.1f}%)")

        gm = m.get("gross_margin_avg", np.nan)
        if not np.isnan(gm) and gm >= 35:
            signals.append(f"Strong Gross Margins ({gm:.1f}%)")

        gm_cv = m.get("gross_margin_cv", np.nan)
        if not np.isnan(gm_cv) and gm_cv < 0.10:
            signals.append("Very Stable Margins")

        de = m.get("debt_equity_latest", np.nan)
        if not np.isnan(de) and de < 0.1:
            signals.append("Virtually Debt-Free")

        net_cash = m.get("net_cash_cr", np.nan)
        if not np.isnan(net_cash) and net_cash > 500:
            signals.append(f"Net Cash ₹{net_cash:.0f} Cr")

        fcf = m.get("fcf_conversion_avg", np.nan)
        if not np.isnan(fcf) and fcf >= 0.85:
            signals.append(f"High FCF Conversion ({fcf:.0%})")

        rev = m.get("rev_cagr", np.nan)
        if not np.isnan(rev) and rev >= 15:
            signals.append(f"Strong Revenue Growth ({rev:.1f}% CAGR)")

        om_trend = m.get("op_margin_trend", np.nan)
        if not np.isnan(om_trend) and om_trend > 0.5:
            signals.append("Expanding Operating Margins")

        ic = m.get("interest_coverage_avg", 0)
        if ic >= 20:
            signals.append(f"Excellent Interest Coverage ({ic:.0f}x)")

        cfo_pat = m.get("cfo_pat_avg", np.nan)
        if not np.isnan(cfo_pat) and cfo_pat >= 1.0:
            signals.append("High Earnings Quality (CFO > PAT)")

        return signals
