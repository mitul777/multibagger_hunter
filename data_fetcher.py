# =============================================================================
# data_fetcher.py — Fetch Financial Data for Indian Equities via yfinance
# =============================================================================

import yfinance as yf
import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches financial data for NSE-listed companies using yfinance.

    All monetary values are in the currency reported by Yahoo Finance
    (typically INR for Indian companies). Market cap is in INR.
    """

    def __init__(self, period: str = "5y"):
        """
        Args:
            period: Historical data period ('3y', '5y', '10y')
        """
        self.period = period
        self._cache: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, ticker: str) -> Optional[dict]:
        """
        Fetch all required financial data for a single ticker.

        Returns:
            dict with keys: info, income_stmt, balance_sheet, cashflow,
            price_history, or None if data is unavailable.
        """
        if ticker in self._cache:
            return self._cache[ticker]

        try:
            yf_ticker = yf.Ticker(ticker)
            data = self._extract_all(yf_ticker, ticker)
            self._cache[ticker] = data
            return data
        except Exception as e:
            logger.warning(f"[{ticker}] Failed to fetch data: {e}")
            return None

    # ------------------------------------------------------------------
    # Internal Extraction
    # ------------------------------------------------------------------

    def _extract_all(self, yf_ticker: yf.Ticker, ticker: str) -> Optional[dict]:
        """Extract and standardise all financial tables."""
        try:
            info = yf_ticker.info or {}
        except Exception:
            info = {}

        # Core financial statements (annual)
        income_stmt    = self._safe_fetch(yf_ticker, "financials")
        balance_sheet  = self._safe_fetch(yf_ticker, "balance_sheet")
        cashflow       = self._safe_fetch(yf_ticker, "cashflow")

        # Check we have at least some data
        if income_stmt is None and balance_sheet is None:
            logger.debug(f"[{ticker}] No financial statements found.")
            return None

        return {
            "ticker":        ticker,
            "info":          info,
            "income_stmt":   income_stmt,
            "balance_sheet": balance_sheet,
            "cashflow":      cashflow,
        }

    def _safe_fetch(self, yf_ticker: yf.Ticker, attr: str) -> Optional[pd.DataFrame]:
        """Safely fetch a yfinance attribute, returning None on error."""
        try:
            df = getattr(yf_ticker, attr)
            if df is None or df.empty:
                return None
            # Sort columns oldest → newest (some tickers return reverse order)
            return df.sort_index(axis=1)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Data Extraction Helpers (for use by MetricsCalculator)
    # ------------------------------------------------------------------

    @staticmethod
    def get_row(df: pd.DataFrame, *possible_keys: str) -> pd.Series:
        """
        Try multiple possible row labels and return the first match.
        Handles yfinance inconsistencies across different stock types.
        """
        if df is None:
            return pd.Series(dtype=float)
        for key in possible_keys:
            if key in df.index:
                return df.loc[key].astype(float)
        return pd.Series(dtype=float)

    @staticmethod
    def latest_n(series: pd.Series, n: int = 3) -> pd.Series:
        """Return the latest n non-null values from a series (sorted old→new)."""
        cleaned = series.dropna()
        if len(cleaned) == 0:
            return pd.Series(dtype=float)
        return cleaned.iloc[-n:]

    @staticmethod
    def safe_div(numerator: float, denominator: float,
                 default: float = np.nan) -> float:
        """Safe division that returns default on zero/NaN denominator."""
        if pd.isna(denominator) or denominator == 0:
            return default
        if pd.isna(numerator):
            return default
        return numerator / denominator

    @staticmethod
    def cagr(start: float, end: float, years: int) -> float:
        """Compute Compound Annual Growth Rate (as %)."""
        if pd.isna(start) or pd.isna(end) or years <= 0:
            return np.nan
        if start <= 0 or end <= 0:
            return np.nan
        return ((end / start) ** (1 / years) - 1) * 100

    @staticmethod
    def info_val(info: dict, *keys, default=np.nan):
        """Safely extract a value from yfinance info dict."""
        for key in keys:
            val = info.get(key)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return val
        return default
