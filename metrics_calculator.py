# =============================================================================
# metrics_calculator.py — Compute All Financial Ratios & Moat Indicators
# =============================================================================
# Metrics computed per-company:
#   Profitability : Gross Margin, Operating Margin, Net Margin
#   Returns       : ROCE, ROE, ROIC proxy
#   Growth        : Revenue CAGR, EPS CAGR (3-year & 5-year)
#   Quality       : CFO/PAT, Debt/Equity, Interest Coverage
#   Efficiency    : Asset Turnover, Operating Leverage
#   Moat Signals  : Margin consistency, FCF conversion
# =============================================================================

import numpy as np
import pandas as pd
import logging
from typing import Optional
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

F = DataFetcher  # alias for static helpers


class MetricsCalculator:
    """
    Computes all financial metrics required for moat scoring.
    Handles missing / partial data gracefully.
    """

    def compute(self, data: dict) -> dict:
        """
        Compute all metrics for a single company.

        Args:
            data: Dict returned by DataFetcher.fetch()

        Returns:
            Dict of computed metrics (NaN where data is unavailable)
        """
        ticker = data.get("ticker", "UNKNOWN")
        info   = data.get("info", {})
        inc    = data.get("income_stmt")
        bs     = data.get("balance_sheet")
        cf     = data.get("cashflow")

        # -- Extract raw line items --
        revenue       = F.get_row(inc, "Total Revenue", "Revenue")
        gross_profit  = F.get_row(inc, "Gross Profit")
        ebit          = F.get_row(inc, "EBIT", "Operating Income",
                                        "Operating Income Or Loss")
        ebitda        = F.get_row(inc, "EBITDA", "Normalized EBITDA")
        net_income    = F.get_row(inc, "Net Income", "Net Income Common Stockholders",
                                        "Net Income From Continuing Operations")
        interest_exp  = F.get_row(inc, "Interest Expense", "Interest Expense Non Operating")
        tax_exp       = F.get_row(inc, "Tax Provision", "Income Tax Expense")

        total_assets  = F.get_row(bs, "Total Assets")
        total_equity  = F.get_row(bs, "Stockholders Equity", "Total Stockholder Equity",
                                        "Common Stock Equity")
        total_debt    = F.get_row(bs, "Long Term Debt", "Total Debt", "Long Term Debt And Capital Lease Obligation")
        short_debt    = F.get_row(bs, "Current Debt", "Short Long Term Debt",
                                        "Current Debt And Capital Lease Obligation")
        cash          = F.get_row(bs, "Cash And Cash Equivalents",
                                        "Cash Cash Equivalents And Short Term Investments")
        curr_assets   = F.get_row(bs, "Current Assets")
        curr_liab     = F.get_row(bs, "Current Liabilities")

        cfo           = F.get_row(cf, "Operating Cash Flow", "Total Cash From Operating Activities")
        capex         = F.get_row(cf, "Capital Expenditure", "Capital Expenditures",
                                        "Purchase Of Property Plant And Equipment")

        # -- Combine short + long term debt --
        combined_debt = self._combine_debt(total_debt, short_debt)

        # Number of available years
        n_years = len(revenue.dropna()) if revenue is not None else 0

        metrics = {
            "ticker":    ticker,
            "n_years":   n_years,
            "sector":    F.info_val(info, "sector", default="Unknown"),
            "industry":  F.info_val(info, "industry", default="Unknown"),
            "name":      info.get("longName", ticker),
            "market_cap_cr": self._market_cap_cr(info),
            "current_price": F.info_val(info, "currentPrice", "regularMarketPrice"),
        }

        # -- Profitability --
        metrics.update(self._profitability(revenue, gross_profit, ebit, net_income))

        # -- Returns --
        metrics.update(self._returns(ebit, total_assets, combined_debt,
                                     total_equity, interest_exp, net_income))

        # -- Growth --
        metrics.update(self._growth(revenue, net_income, info))

        # -- Quality --
        metrics.update(self._quality(net_income, cfo, capex, combined_debt,
                                     total_equity, ebit, interest_exp))

        # -- Efficiency --
        metrics.update(self._efficiency(revenue, total_assets, ebit))

        # -- Liquidity --
        metrics.update(self._liquidity(curr_assets, curr_liab, cash, combined_debt))

        return metrics

    # -------------------------------------------------------------------------
    # Profitability
    # -------------------------------------------------------------------------

    def _profitability(self, revenue, gross_profit, ebit, net_income) -> dict:
        """Compute margin metrics — latest year and historical averages."""
        out = {}

        def margin_series(numerator, denominator):
            num = F.latest_n(numerator, 5)
            den = F.latest_n(denominator, 5)
            return (num / den.reindex(num.index) * 100).dropna()

        gm_series  = margin_series(gross_profit, revenue)
        om_series  = margin_series(ebit, revenue)
        npm_series = margin_series(net_income, revenue)

        out["gross_margin_latest"]  = gm_series.iloc[-1]  if len(gm_series)  else np.nan
        out["op_margin_latest"]     = om_series.iloc[-1]  if len(om_series)  else np.nan
        out["net_margin_latest"]    = npm_series.iloc[-1] if len(npm_series) else np.nan

        out["gross_margin_avg"]     = gm_series.mean()    if len(gm_series)  else np.nan
        out["op_margin_avg"]        = om_series.mean()    if len(om_series)  else np.nan

        # Margin consistency: coefficient of variation (lower = more consistent)
        out["gross_margin_cv"]      = self._coeff_var(gm_series)
        out["op_margin_cv"]         = self._coeff_var(om_series)

        # Margin trend: positive slope = expanding margins (good moat signal)
        out["op_margin_trend"]      = self._trend(om_series)   # ppts per year
        out["gross_margin_trend"]   = self._trend(gm_series)

        return out

    # -------------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------------

    def _returns(self, ebit, total_assets, combined_debt,
                 total_equity, interest_exp, net_income) -> dict:
        """Compute ROCE, ROE, and ROIC proxy."""
        out = {}

        # ROCE = EBIT / (Total Assets − Current Liabilities proxy)
        # Simplified: EBIT / (Total Assets − Total Debt + Total Equity) ≈ Capital Employed
        roce_series = []
        for col in F.latest_n(ebit, 5).index:
            try:
                e    = float(ebit.get(col, np.nan))
                ta   = float(total_assets.get(col, np.nan))
                td   = float(combined_debt.get(col, np.nan) if combined_debt is not None else np.nan)
                te   = float(total_equity.get(col, np.nan))
                # Capital Employed = Total Assets - Current Liabilities
                # Approx: TA - (TA - TE - TD) = TE + TD
                capital_employed = te + td if not (np.isnan(te) or np.isnan(td)) else ta
                roce = F.safe_div(e, capital_employed) * 100
                roce_series.append(roce)
            except Exception:
                pass

        roce_s = pd.Series(roce_series).dropna()
        out["roce_latest"]          = roce_s.iloc[-1] if len(roce_s) else np.nan
        out["roce_avg"]             = roce_s.mean()   if len(roce_s) else np.nan
        out["roce_cv"]              = self._coeff_var(roce_s)
        out["roce_trend"]           = self._trend(roce_s)

        # ROE = Net Income / Total Equity (latest)
        roe_vals = []
        for col in F.latest_n(net_income, 5).index:
            try:
                ni = float(net_income.get(col, np.nan))
                te = float(total_equity.get(col, np.nan))
                roe_vals.append(F.safe_div(ni, te) * 100)
            except Exception:
                pass
        roe_s = pd.Series(roe_vals).dropna()
        out["roe_latest"]           = roe_s.iloc[-1] if len(roe_s) else np.nan
        out["roe_avg"]              = roe_s.mean()   if len(roe_s) else np.nan

        return out

    # -------------------------------------------------------------------------
    # Growth
    # -------------------------------------------------------------------------

    def _growth(self, revenue, net_income, info) -> dict:
        """Compute revenue and EPS CAGR over 3 and 5 year windows."""
        out = {}

        rev_clean = revenue.dropna()
        ni_clean  = net_income.dropna() if net_income is not None else pd.Series(dtype=float)

        for window in [3, 5]:
            if len(rev_clean) > window:
                out[f"rev_cagr_{window}y"] = F.cagr(
                    rev_clean.iloc[-(window + 1)],
                    rev_clean.iloc[-1],
                    window
                )
            else:
                out[f"rev_cagr_{window}y"] = np.nan

            if len(ni_clean) > window:
                out[f"ni_cagr_{window}y"] = F.cagr(
                    ni_clean.iloc[-(window + 1)],
                    ni_clean.iloc[-1],
                    window
                )
            else:
                out[f"ni_cagr_{window}y"] = np.nan

        # Use 3-year as primary if 5-year unavailable
        out["rev_cagr"] = out.get("rev_cagr_3y", np.nan) \
                          if not np.isnan(out.get("rev_cagr_3y", np.nan)) \
                          else out.get("rev_cagr_5y", np.nan)
        out["eps_cagr"] = out.get("ni_cagr_3y", np.nan) \
                          if not np.isnan(out.get("ni_cagr_3y", np.nan)) \
                          else out.get("ni_cagr_5y", np.nan)

        # EPS from info as fallback
        out["eps_ttm"]        = F.info_val(info, "trailingEps")
        out["pe_ratio"]       = F.info_val(info, "trailingPE")
        out["peg_ratio"]      = F.info_val(info, "pegRatio")
        out["pb_ratio"]       = F.info_val(info, "priceToBook")
        out["ev_ebitda"]      = F.info_val(info, "enterpriseToEbitda")

        return out

    # -------------------------------------------------------------------------
    # Quality
    # -------------------------------------------------------------------------

    def _quality(self, net_income, cfo, capex,
                 combined_debt, total_equity, ebit, interest_exp) -> dict:
        """Compute balance sheet quality and earnings quality metrics."""
        out = {}

        # FCF = CFO − Capex
        cfo_clean = F.latest_n(cfo, 5)   if cfo is not None else pd.Series(dtype=float)
        capex_clean = F.latest_n(capex, 5) if capex is not None else pd.Series(dtype=float)

        # Capex is reported as negative in yfinance cashflow — normalise
        capex_abs = capex_clean.abs()

        fcf_series = []
        for col in cfo_clean.index:
            c = float(cfo_clean.get(col, np.nan))
            x = float(capex_abs.get(col, np.nan)) if col in capex_abs.index else 0.0
            fcf_series.append(c - x if not np.isnan(c) else np.nan)
        fcf_s = pd.Series(fcf_series).dropna()

        # FCF/Net Income (earnings quality) — use latest 3 years average
        ni_clean = F.latest_n(net_income, 5) if net_income is not None else pd.Series(dtype=float)
        fcf_ni_vals = []
        for i, col in enumerate(cfo_clean.index):
            if i < len(fcf_series) and col in ni_clean.index:
                fcf = fcf_series[i]
                ni  = float(ni_clean.get(col, np.nan))
                if not np.isnan(fcf) and ni > 0:
                    fcf_ni_vals.append(fcf / ni)
        out["fcf_conversion_avg"] = np.mean(fcf_ni_vals) if fcf_ni_vals else np.nan
        out["fcf_latest"]         = fcf_s.iloc[-1] / 1e7 if len(fcf_s) else np.nan  # in Cr

        # CFO/Net Income — latest 3-year average
        cfo_ni_vals = []
        for col in cfo_clean.index:
            c  = float(cfo_clean.get(col, np.nan))
            ni = float(ni_clean.get(col, np.nan)) if col in ni_clean.index else np.nan
            if not np.isnan(c) and ni > 0:
                cfo_ni_vals.append(c / ni)
        out["cfo_pat_avg"] = np.mean(cfo_ni_vals) if cfo_ni_vals else np.nan

        # Debt/Equity — latest year
        de_vals = []
        eq_clean  = F.latest_n(total_equity, 5) if total_equity is not None else pd.Series(dtype=float)
        dbt_clean = F.latest_n(combined_debt, 5) if combined_debt is not None else pd.Series(dtype=float)
        for col in eq_clean.index:
            d = float(dbt_clean.get(col, np.nan)) if col in dbt_clean.index else 0.0
            e = float(eq_clean.get(col, np.nan))
            if not np.isnan(e) and e > 0:
                de_vals.append(d / e if not np.isnan(d) else 0.0)
        out["debt_equity_latest"] = de_vals[-1] if de_vals else np.nan
        out["debt_equity_avg"]    = np.mean(de_vals) if de_vals else np.nan

        # Interest Coverage = EBIT / Interest Expense
        ebit_clean    = F.latest_n(ebit, 5) if ebit is not None else pd.Series(dtype=float)
        int_clean     = F.latest_n(interest_exp, 5) if interest_exp is not None else pd.Series(dtype=float)
        ic_vals = []
        for col in ebit_clean.index:
            e = float(ebit_clean.get(col, np.nan))
            i = abs(float(int_clean.get(col, np.nan))) if col in int_clean.index else np.nan
            if not np.isnan(e) and not np.isnan(i) and i > 0:
                ic_vals.append(e / i)
        out["interest_coverage_avg"] = np.mean(ic_vals) if ic_vals else 999.0  # debt-free

        return out

    # -------------------------------------------------------------------------
    # Efficiency
    # -------------------------------------------------------------------------

    def _efficiency(self, revenue, total_assets, ebit) -> dict:
        """Compute asset turnover and operating leverage indicators."""
        out = {}

        rev_clean = F.latest_n(revenue, 5)      if revenue is not None else pd.Series(dtype=float)
        ta_clean  = F.latest_n(total_assets, 5) if total_assets is not None else pd.Series(dtype=float)
        om_series = []

        at_vals = []
        for col in rev_clean.index:
            r  = float(rev_clean.get(col, np.nan))
            ta = float(ta_clean.get(col, np.nan)) if col in ta_clean.index else np.nan
            if not np.isnan(r) and not np.isnan(ta) and ta > 0:
                at_vals.append(r / ta)

        out["asset_turnover_latest"] = at_vals[-1] if at_vals else np.nan
        out["asset_turnover_avg"]    = np.mean(at_vals) if at_vals else np.nan

        # Operating leverage: % change in EBIT / % change in Revenue
        # Positive and > 1 = good operating leverage
        ebit_clean = F.latest_n(ebit, 5) if ebit is not None else pd.Series(dtype=float)
        op_lev_vals = []
        rev_list  = rev_clean.values.tolist()
        ebit_list = [float(ebit_clean.get(c, np.nan)) for c in rev_clean.index]

        for i in range(1, len(rev_list)):
            dr = F.safe_div(rev_list[i] - rev_list[i-1], rev_list[i-1])
            de = F.safe_div(ebit_list[i] - ebit_list[i-1], abs(ebit_list[i-1]) + 1)
            if not np.isnan(dr) and not np.isnan(de) and dr != 0:
                op_lev_vals.append(de / dr)

        out["operating_leverage"]    = np.median(op_lev_vals) if op_lev_vals else np.nan

        return out

    # -------------------------------------------------------------------------
    # Liquidity
    # -------------------------------------------------------------------------

    def _liquidity(self, curr_assets, curr_liab, cash, combined_debt) -> dict:
        """Current ratio and net cash position."""
        out = {}

        ca_s  = F.latest_n(curr_assets, 1) if curr_assets is not None else pd.Series(dtype=float)
        cl_s  = F.latest_n(curr_liab, 1)   if curr_liab is not None else pd.Series(dtype=float)
        c_s   = F.latest_n(cash, 1)        if cash is not None else pd.Series(dtype=float)
        d_s   = F.latest_n(combined_debt, 1) if combined_debt is not None else pd.Series(dtype=float)

        ca  = float(ca_s.iloc[-1]) if len(ca_s) else np.nan
        cl  = float(cl_s.iloc[-1]) if len(cl_s) else np.nan
        c   = float(c_s.iloc[-1])  if len(c_s) else 0.0
        d   = float(d_s.iloc[-1])  if len(d_s) else 0.0

        out["current_ratio"]    = F.safe_div(ca, cl)
        out["net_cash_cr"]      = (c - d) / 1e7 if not np.isnan(c) else np.nan  # in Cr

        return out

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def _combine_debt(long_debt: pd.Series, short_debt: pd.Series) -> pd.Series:
        """Add long-term and short-term debt, filling NaN with 0."""
        if long_debt is None and short_debt is None:
            return pd.Series(dtype=float)
        if long_debt is None:
            return short_debt.fillna(0)
        if short_debt is None:
            return long_debt.fillna(0)
        return long_debt.fillna(0).add(short_debt.fillna(0), fill_value=0)

    @staticmethod
    def _coeff_var(series: pd.Series) -> float:
        """Coefficient of Variation = std / mean. Lower = more consistent."""
        s = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) < 2 or s.mean() == 0:
            return np.nan
        return float(abs(s.std() / s.mean()))

    @staticmethod
    def _trend(series: pd.Series) -> float:
        """
        Linear trend slope (units per year). Positive = improving.
        Uses simple OLS: slope = cov(x,y)/var(x).
        """
        s = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) < 2:
            return np.nan
        x = np.arange(len(s), dtype=float)
        y = s.values.astype(float)
        if np.std(x) == 0:
            return np.nan
        return float(np.polyfit(x, y, 1)[0])

    @staticmethod
    def _market_cap_cr(info: dict) -> float:
        """Return market cap in Crores (₹)."""
        mc = info.get("marketCap")
        if mc and not np.isnan(float(mc)):
            return float(mc) / 1e7  # 1 Crore = 10 million
        return np.nan
