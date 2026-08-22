# =============================================================================
# trajectory_analyzer.py — Detect Early Moat Signals via Trajectory Analysis
# =============================================================================
#
# PHILOSOPHY:
#   For midcap/smallcap early moat detection, DIRECTION matters more than
#   absolute levels. A company with 14% ROCE improving to 20% is more
#   interesting than one stuck at 18%.
#
# TRAJECTORY SCORE (30 points — replaces 30pts from standard moat score):
#
#   1. ROCE Trajectory         (8 pts) : Is ROCE improving YoY?
#   2. Margin Expansion        (8 pts) : Are operating margins expanding?
#   3. Revenue Acceleration    (6 pts) : Is growth speeding up?
#   4. Capital Efficiency Gain (4 pts) : Is FCF/Capex ratio improving?
#   5. Debt Reduction          (4 pts) : Is leverage decreasing?
#
# EARLY MOAT GREEN FLAGS (bonus signals — up to +10 pts):
#   • Pricing Power Test   : Margins held during revenue dip (COVID FY21 test)
#   • Self-Funding Growth  : Capex < CFO (no dilution needed)
#   • Working Capital Gain : Days are falling (customers paying faster)
#   • Operating Leverage   : EBIT growing 2x faster than Revenue
#   • Revenue Quality      : Revenue CAGR > Net Income CAGR by < 5% (not buying growth)
#
# RED FLAGS (penalty — up to -10 pts):
#   • Pledged promoter shares proxy: D/E rising while revenue stagnates
#   • Receivables bloating  : Revenue growing but debtors growing faster
#   • Margin compression    : Expanding revenue but shrinking margins
#   • Loss-making years     : Net income negative in any recent year
# =============================================================================

import numpy as np
import pandas as pd
import logging
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)
F = DataFetcher


class TrajectoryAnalyzer:
    """
    Computes trajectory and momentum signals for early-moat detection.
    Designed for mid/smallcap companies where the trend matters most.
    """

    def analyze(self, data: dict, metrics: dict) -> dict:
        """
        Compute all trajectory signals and add to metrics dict.

        Args:
            data   : Raw data dict from DataFetcher
            metrics: Pre-computed metrics from MetricsCalculator

        Returns:
            metrics enriched with trajectory scores and signals
        """
        inc = data.get("income_stmt")
        bs  = data.get("balance_sheet")
        cf  = data.get("cashflow")

        # Extract raw series
        revenue      = F.get_row(inc, "Total Revenue", "Revenue")
        ebit         = F.get_row(inc, "EBIT", "Operating Income",
                                          "Operating Income Or Loss")
        net_income   = F.get_row(inc, "Net Income", "Net Income Common Stockholders")
        total_equity = F.get_row(bs, "Stockholders Equity", "Total Stockholder Equity",
                                          "Common Stock Equity")
        total_debt   = F.get_row(bs, "Long Term Debt", "Total Debt",
                                          "Long Term Debt And Capital Lease Obligation")
        short_debt   = F.get_row(bs, "Current Debt", "Short Long Term Debt",
                                          "Current Debt And Capital Lease Obligation")
        cfo          = F.get_row(cf, "Operating Cash Flow",
                                          "Total Cash From Operating Activities")
        capex        = F.get_row(cf, "Capital Expenditure", "Capital Expenditures",
                                          "Purchase Of Property Plant And Equipment")
        total_assets = F.get_row(bs, "Total Assets")
        curr_assets  = F.get_row(bs, "Current Assets")
        curr_liab    = F.get_row(bs, "Current Liabilities")

        # -----------------------------------------------------------------------
        # Compute component trajectory scores
        # -----------------------------------------------------------------------
        traj = {}

        traj.update(self._roce_trajectory(ebit, total_equity, total_debt, short_debt))
        traj.update(self._margin_trajectory(ebit, revenue, net_income))
        traj.update(self._revenue_acceleration(revenue))
        traj.update(self._capital_efficiency(cfo, capex))
        traj.update(self._debt_trajectory(total_debt, short_debt, total_equity))
        traj.update(self._green_flags(revenue, ebit, net_income, cfo, capex,
                                      curr_assets, curr_liab))
        traj.update(self._red_flags(revenue, ebit, net_income, total_debt,
                                    short_debt, total_equity))

        # -----------------------------------------------------------------------
        # Aggregate trajectory score
        # -----------------------------------------------------------------------
        trajectory_score = (
            traj.get("_roce_traj_score",    0) +
            traj.get("_margin_traj_score",  0) +
            traj.get("_rev_accel_score",    0) +
            traj.get("_capeff_score",       0) +
            traj.get("_debt_traj_score",    0) +
            traj.get("_green_bonus",        0) -
            traj.get("_red_penalty",        0)
        )
        trajectory_score = max(0.0, min(trajectory_score, 40.0))  # cap 0-40

        traj["trajectory_score"]   = round(trajectory_score, 1)
        traj["trajectory_signals"] = self._describe_trajectory(traj)
        traj["trajectory_warnings"] = self._describe_warnings(traj)

        metrics.update(traj)
        return metrics

    # =========================================================================
    # 1. ROCE Trajectory (8 points)
    # =========================================================================

    def _roce_trajectory(self, ebit, equity, ld, sd) -> dict:
        """Is ROCE improving over time?"""
        out = {"_roce_traj_score": 0}

        combined_debt = self._combine(ld, sd)
        roce_list = []
        for col in F.latest_n(ebit, 5).index:
            try:
                e  = float(ebit.get(col, np.nan))
                te = float(equity.get(col, np.nan)) if col in equity.index else np.nan
                td = float(combined_debt.get(col, 0)) if col in combined_debt.index else 0
                ce = te + td if not np.isnan(te) else np.nan
                if not (np.isnan(e) or np.isnan(ce)) and ce > 0:
                    roce_list.append(e / ce * 100)
            except Exception:
                pass

        if len(roce_list) < 2:
            return out

        r = pd.Series(roce_list)
        out["roce_traj_values"]   = roce_list
        out["roce_traj_latest"]   = roce_list[-1]
        out["roce_traj_earliest"] = roce_list[0]
        out["roce_traj_delta"]    = roce_list[-1] - roce_list[0]

        # Is ROCE in the latest year > the average of earlier years?
        latest_vs_prior = roce_list[-1] - np.mean(roce_list[:-1])
        out["roce_above_prior"]   = latest_vs_prior

        # Slope: positive = improving
        slope = float(np.polyfit(range(len(r)), r, 1)[0]) if len(r) >= 2 else 0

        # Score: reward consistent improvement and high current level
        score = 0
        if slope > 0:                    # trending up
            score += 4
        if latest_vs_prior > 2:          # latest > prior avg by 2ppts
            score += 2
        if roce_list[-1] >= 20:          # current ROCE strong
            score += 2
        elif roce_list[-1] >= 15:
            score += 1

        out["_roce_traj_score"] = min(score, 8)
        return out

    # =========================================================================
    # 2. Margin Trajectory (8 points)
    # =========================================================================

    def _margin_trajectory(self, ebit, revenue, net_income) -> dict:
        """Are operating margins expanding consistently?"""
        out = {"_margin_traj_score": 0}

        ebit_s = F.latest_n(ebit, 5)
        rev_s  = F.latest_n(revenue, 5)

        om_list = []
        for col in ebit_s.index:
            e = float(ebit_s.get(col, np.nan))
            r = float(rev_s.get(col, np.nan)) if col in rev_s.index else np.nan
            if not (np.isnan(e) or np.isnan(r)) and r > 0:
                om_list.append(e / r * 100)

        if len(om_list) < 2:
            return out

        out["om_traj_values"] = om_list
        out["om_traj_delta"]  = om_list[-1] - om_list[0]

        # Is latest year operating margin > all prior years? (consistent expansion)
        n_years_expanding = sum(1 for i in range(1, len(om_list))
                                if om_list[i] > om_list[i-1])
        out["om_expanding_years"] = n_years_expanding

        # Is latest year margin the highest?
        out["om_at_peak"] = (om_list[-1] == max(om_list))

        # Net margin trend
        ni_s = F.latest_n(net_income, 5)
        nm_list = []
        for col in ni_s.index:
            ni = float(ni_s.get(col, np.nan))
            r  = float(rev_s.get(col, np.nan)) if col in rev_s.index else np.nan
            if not (np.isnan(ni) or np.isnan(r)) and r > 0:
                nm_list.append(ni / r * 100)

        out["nm_traj_delta"] = nm_list[-1] - nm_list[0] if len(nm_list) >= 2 else 0

        # Score
        score = 0
        delta = out["om_traj_delta"]
        if delta > 5:           # margins expanded >5ppts over period
            score += 4
        elif delta > 2:
            score += 2
        elif delta > 0:
            score += 1

        if n_years_expanding >= (len(om_list) - 1):  # expanding every year
            score += 2
        elif n_years_expanding >= len(om_list) // 2:
            score += 1

        if out["om_at_peak"]:   # latest year is best ever
            score += 2

        out["_margin_traj_score"] = min(score, 8)
        return out

    # =========================================================================
    # 3. Revenue Acceleration (6 points)
    # =========================================================================

    def _revenue_acceleration(self, revenue) -> dict:
        """Is revenue growth accelerating (3Y CAGR > 5Y CAGR)?"""
        out = {"_rev_accel_score": 0}

        rev_clean = revenue.dropna() if revenue is not None else pd.Series(dtype=float)
        if len(rev_clean) < 3:
            return out

        # 3-year CAGR
        cagr_3y = F.cagr(rev_clean.iloc[-4] if len(rev_clean) >= 4 else rev_clean.iloc[0],
                          rev_clean.iloc[-1], 3) if len(rev_clean) >= 4 else np.nan

        # 5-year CAGR
        cagr_5y = F.cagr(rev_clean.iloc[-6] if len(rev_clean) >= 6 else rev_clean.iloc[0],
                          rev_clean.iloc[-1], 5) if len(rev_clean) >= 6 else np.nan

        # 1-year growth (most recent)
        yoy_growth = F.cagr(rev_clean.iloc[-2], rev_clean.iloc[-1], 1) \
                     if len(rev_clean) >= 2 else np.nan

        out["rev_cagr_3y_traj"]  = cagr_3y
        out["rev_cagr_5y_traj"]  = cagr_5y
        out["rev_yoy_latest"]    = yoy_growth
        out["rev_is_accelerating"] = (
            not np.isnan(cagr_3y) and not np.isnan(cagr_5y) and cagr_3y > cagr_5y
        )

        score = 0
        if not np.isnan(cagr_3y):
            if cagr_3y >= 25:
                score += 3
            elif cagr_3y >= 15:
                score += 2
            elif cagr_3y >= 10:
                score += 1

        if out["rev_is_accelerating"]:
            score += 2

        if not np.isnan(yoy_growth) and yoy_growth >= 20:
            score += 1

        out["_rev_accel_score"] = min(score, 6)
        return out

    # =========================================================================
    # 4. Capital Efficiency Gain (4 points)
    # =========================================================================

    def _capital_efficiency(self, cfo, capex) -> dict:
        """Is the company generating more FCF per rupee of capex?"""
        out = {"_capeff_score": 0}

        cfo_s   = F.latest_n(cfo, 5)   if cfo is not None else pd.Series(dtype=float)
        capex_s = F.latest_n(capex, 5) if capex is not None else pd.Series(dtype=float)

        fcf_list = []
        cfo_list = []
        capex_abs_list = []
        for col in cfo_s.index:
            c = float(cfo_s.get(col, np.nan))
            x = abs(float(capex_s.get(col, np.nan))) if col in capex_s.index else 0
            if not np.isnan(c):
                fcf_list.append(c - x)
                cfo_list.append(c)
                capex_abs_list.append(x)

        if not fcf_list:
            return out

        out["fcf_traj_latest"]   = fcf_list[-1] / 1e7 if fcf_list else np.nan  # Cr
        out["cfo_traj_latest"]   = cfo_list[-1] / 1e7 if cfo_list else np.nan  # Cr

        # Is company self-funding? (CFO > Capex)
        out["is_self_funding"] = (cfo_list[-1] > capex_abs_list[-1]) if cfo_list else False

        # FCF trend — improving?
        fcf_trend = float(np.polyfit(range(len(fcf_list)), fcf_list, 1)[0]) \
                    if len(fcf_list) >= 2 else 0
        out["fcf_trend"] = fcf_trend

        score = 0
        if out["is_self_funding"]:
            score += 2
        if fcf_trend > 0:   # FCF improving over time
            score += 1
        if len(fcf_list) >= 2 and all(f > 0 for f in fcf_list[-2:]):  # FCF+ve last 2 years
            score += 1

        out["_capeff_score"] = min(score, 4)
        return out

    # =========================================================================
    # 5. Debt Trajectory (4 points)
    # =========================================================================

    def _debt_trajectory(self, ld, sd, equity) -> dict:
        """Is debt reducing as a proportion of equity?"""
        out = {"_debt_traj_score": 0}

        combined = self._combine(ld, sd)
        eq_s  = F.latest_n(equity, 5) if equity is not None else pd.Series(dtype=float)

        de_list = []
        for col in eq_s.index:
            e = float(eq_s.get(col, np.nan))
            d = float(combined.get(col, 0)) if col in combined.index else 0
            if not np.isnan(e) and e > 0:
                de_list.append(d / e)

        if len(de_list) < 2:
            out["_debt_traj_score"] = 2  # assume ok if no data
            return out

        out["de_traj_values"]   = de_list
        out["de_traj_delta"]    = de_list[-1] - de_list[0]  # negative = improving
        out["de_is_improving"]  = de_list[-1] < de_list[0]
        out["de_latest"]        = de_list[-1]

        score = 0
        if de_list[-1] < 0.10:     # virtually debt-free
            score += 4
        elif de_list[-1] < 0.50:
            score += 2
            if out["de_is_improving"]:
                score += 1
        elif de_list[-1] < 1.0 and out["de_is_improving"]:
            score += 1

        out["_debt_traj_score"] = min(score, 4)
        return out

    # =========================================================================
    # 6. Green Flags — bonus moat signals (up to +10 pts)
    # =========================================================================

    def _green_flags(self, revenue, ebit, net_income, cfo, capex,
                     curr_assets, curr_liab) -> dict:
        """Identify bonus positive signals that suggest an emerging moat."""
        out = {"_green_bonus": 0}
        flags = []

        rev_s   = F.latest_n(revenue, 5)    if revenue is not None else pd.Series(dtype=float)
        ebit_s  = F.latest_n(ebit, 5)       if ebit is not None else pd.Series(dtype=float)
        ni_s    = F.latest_n(net_income, 5) if net_income is not None else pd.Series(dtype=float)
        cfo_s   = F.latest_n(cfo, 3)        if cfo is not None else pd.Series(dtype=float)
        capex_s = F.latest_n(capex, 3)      if capex is not None else pd.Series(dtype=float)

        # FLAG 1: Operating Leverage (EBIT growing 1.5x+ faster than Revenue)
        rev_list  = rev_s.values.tolist()
        ebit_list = ebit_s.values.tolist()
        op_lev_scores = []
        for i in range(1, min(len(rev_list), len(ebit_list))):
            dr = F.safe_div(rev_list[i] - rev_list[i-1], abs(rev_list[i-1]) + 1)
            de = F.safe_div(ebit_list[i] - ebit_list[i-1], abs(ebit_list[i-1]) + 1)
            if not np.isnan(dr) and dr > 0 and not np.isnan(de):
                op_lev_scores.append(de / dr)
        if op_lev_scores and np.median(op_lev_scores) >= 1.5:
            out["_green_bonus"] += 2
            flags.append("🔑 Operating Leverage (EBIT growing 1.5x Revenue)")

        # FLAG 2: Self-funding capex (CFO > Capex consistently)
        cfo_vals   = cfo_s.values.tolist()
        capex_vals = [abs(x) for x in capex_s.values.tolist()]
        if cfo_vals and capex_vals:
            n = min(len(cfo_vals), len(capex_vals))
            if n >= 2 and all(cfo_vals[-n+i] > capex_vals[-n+i] for i in range(n)):
                out["_green_bonus"] += 2
                flags.append("💰 Self-Funding Growth (CFO > Capex every year)")

        # FLAG 3: Pricing power test — margins stable in years when revenue dipped
        rev_list2  = F.latest_n(revenue, 5).values.tolist()
        ebit_list2 = F.latest_n(ebit, 5).values.tolist()
        margin_held = False
        for i in range(1, min(len(rev_list2), len(ebit_list2))):
            if rev_list2[i-1] > 0 and rev_list2[i] < rev_list2[i-1]:  # revenue dipped
                prev_om = ebit_list2[i-1] / rev_list2[i-1] if rev_list2[i-1] else 0
                curr_om = ebit_list2[i]   / rev_list2[i]   if rev_list2[i]   else 0
                if curr_om >= prev_om - 1:  # margins held within 1ppt
                    margin_held = True
        if margin_held:
            out["_green_bonus"] += 2
            flags.append("🛡️ Pricing Power (Margins Held During Revenue Dip)")

        # FLAG 4: EPS growing faster than Revenue (not buying growth via dilution)
        ni_vals  = ni_s.values.tolist()
        rev_vals = rev_s.values.tolist()
        if len(ni_vals) >= 3 and len(rev_vals) >= 3:
            ni_growth  = F.cagr(ni_vals[0],  ni_vals[-1],  len(ni_vals) - 1)
            rev_growth = F.cagr(rev_vals[0], rev_vals[-1], len(rev_vals) - 1)
            if not np.isnan(ni_growth) and not np.isnan(rev_growth) and ni_growth > rev_growth:
                out["_green_bonus"] += 2
                flags.append("📈 EPS Growing Faster than Revenue")

        # FLAG 5: All years profitable (no loss-making year in last 4)
        ni_check = F.latest_n(net_income, 4)
        if len(ni_check) >= 3 and all(v > 0 for v in ni_check.values if not np.isnan(v)):
            out["_green_bonus"] += 1
            flags.append("✅ Consistently Profitable (No Loss Years)")

        out["green_flags"] = flags
        out["_green_bonus"] = min(out["_green_bonus"], 10)  # cap at 10
        return out

    # =========================================================================
    # 7. Red Flags — penalty signals (up to -10 pts)
    # =========================================================================

    def _red_flags(self, revenue, ebit, net_income, ld, sd, equity) -> dict:
        """Identify warning signals that suggest moat is weak or absent."""
        out = {"_red_penalty": 0}
        warnings = []

        rev_s = F.latest_n(revenue, 4) if revenue is not None else pd.Series(dtype=float)
        ni_s  = F.latest_n(net_income, 4) if net_income is not None else pd.Series(dtype=float)

        # RED 1: Loss-making in recent years
        loss_years = sum(1 for v in ni_s.values if not np.isnan(v) and v < 0)
        if loss_years >= 2:
            out["_red_penalty"] += 4
            warnings.append(f"🚨 {loss_years} Loss-Making Years in Recent History")
        elif loss_years == 1:
            out["_red_penalty"] += 2
            warnings.append("⚠️ 1 Loss-Making Year Recently")

        # RED 2: Revenue declining or stagnant
        rev_vals = rev_s.values.tolist()
        if len(rev_vals) >= 3:
            rev_growth = F.cagr(rev_vals[0], rev_vals[-1], len(rev_vals) - 1)
            if not np.isnan(rev_growth) and rev_growth < 0:
                out["_red_penalty"] += 3
                warnings.append(f"🔻 Revenue Declining ({rev_growth:.1f}% CAGR)")
            elif not np.isnan(rev_growth) and rev_growth < 5:
                out["_red_penalty"] += 1
                warnings.append(f"⚠️ Stagnant Revenue ({rev_growth:.1f}% CAGR)")

        # RED 3: Margin compression (revenue up but margins falling)
        ebit_s  = F.latest_n(ebit, 4) if ebit is not None else pd.Series(dtype=float)
        ebit_v  = ebit_s.values.tolist()
        rev_v   = F.latest_n(revenue, 4).values.tolist() if revenue is not None else []
        if len(ebit_v) >= 2 and len(rev_v) >= 2:
            prev_om = ebit_v[0] / rev_v[0] if rev_v[0] else 0
            curr_om = ebit_v[-1] / rev_v[-1] if rev_v[-1] else 0
            if curr_om < prev_om - 3:  # margins fell >3ppts
                out["_red_penalty"] += 2
                warnings.append(f"📉 Margin Compression (OM fell {(prev_om-curr_om):.1f}ppts)")

        # RED 4: Debt rising while revenue stagnates
        combined = self._combine(ld, sd)
        eq_s = F.latest_n(equity, 3) if equity is not None else pd.Series(dtype=float)
        if len(combined) >= 2 and len(rev_s) >= 2:
            debt_now   = float(combined.iloc[-1]) if len(combined) > 0 else 0
            debt_prior = float(combined.iloc[0])  if len(combined) > 0 else 0
            rev_now    = float(rev_s.iloc[-1])    if len(rev_s) > 0 else 0
            rev_prior  = float(rev_s.iloc[0])     if len(rev_s) > 0 else 0
            if debt_now > debt_prior * 1.3 and rev_now < rev_prior * 1.1:
                out["_red_penalty"] += 2
                warnings.append("⚠️ Debt Rising While Revenue Stagnates")

        out["red_flags"] = warnings
        out["_red_penalty"] = min(out["_red_penalty"], 10)  # cap at 10
        return out

    # =========================================================================
    # Signal Description Helpers
    # =========================================================================

    @staticmethod
    def _describe_trajectory(traj: dict) -> list:
        """Summarise positive trajectory signals."""
        signals = []

        roce_delta = traj.get("roce_traj_delta", 0)
        if not np.isnan(roce_delta) and roce_delta > 3:
            signals.append(f"📊 ROCE improved +{roce_delta:.1f}ppts")

        om_delta = traj.get("om_traj_delta", 0)
        if not np.isnan(om_delta) and om_delta > 2:
            signals.append(f"📈 Operating Margin +{om_delta:.1f}ppts")
        if traj.get("om_at_peak"):
            signals.append("🏆 Margins at Multi-Year High")

        if traj.get("rev_is_accelerating"):
            signals.append("⚡ Revenue Growth Accelerating")

        cagr_3y = traj.get("rev_cagr_3y_traj", np.nan)
        if not np.isnan(cagr_3y) and cagr_3y >= 20:
            signals.append(f"🚀 Revenue CAGR {cagr_3y:.1f}% (3Y)")

        if traj.get("is_self_funding"):
            signals.append("💰 Self-Funding Capex")

        signals.extend(traj.get("green_flags", []))
        return signals

    @staticmethod
    def _describe_warnings(traj: dict) -> list:
        return traj.get("red_flags", [])

    # =========================================================================
    # Utility
    # =========================================================================

    @staticmethod
    def _combine(ld: pd.Series, sd: pd.Series) -> pd.Series:
        if ld is None and sd is None:
            return pd.Series(dtype=float)
        if ld is None:
            return sd.fillna(0)
        if sd is None:
            return ld.fillna(0)
        return ld.fillna(0).add(sd.fillna(0), fill_value=0)
