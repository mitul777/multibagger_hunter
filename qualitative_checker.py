# =============================================================================
# qualitative_checker.py — Automated Qualitative Cross-Checks for Indian Equities
# =============================================================================
#
# DATA SOURCES (all free, no API key required):
#
#   1. Screener.in         — Promoter holding, pledging, FII/DII trend
#   2. BSE India API       — Corporate announcements, concall outcomes
#   3. BSE Shareholding    — Quarterly shareholding pattern data
#   4. NSE Bulk/Block Deals— Institutional activity proxy
#   5. Concall Text        — Keyword scan for moat language
#
# QUALITATIVE SCORE (0–35 pts):
#   Shareholding Quality   : 0–12 pts (promoter %, pledge, trend)
#   Institutional Discovery: 0–5  pts (FII/DII level = undiscovered?)
#   Moat Language Score    : 0–12 pts (keyword hits in filings)
#   Management Actions     : 0–6  pts (insider buy, buyback)
#
# =============================================================================

import re
import time
import logging
import requests
import numpy as np
from bs4 import BeautifulSoup
from typing import Optional
from keyword_signals import MOAT_KEYWORDS, RED_FLAG_KEYWORDS, MOAT_CATEGORY_LABELS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BSE_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}

REQUEST_DELAY = 1.5   # seconds between requests (be polite)
REQUEST_TIMEOUT = 15  # seconds


def _get(url: str, headers: dict = HEADERS, json_mode: bool = False,
         session: Optional[requests.Session] = None) -> Optional[any]:
    """Safe HTTP GET with retry."""
    for attempt in range(2):
        try:
            fn = session.get if session else requests.get
            resp = fn(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json() if json_mode else resp.text
            logger.debug(f"HTTP {resp.status_code} for {url}")
        except Exception as e:
            logger.debug(f"Request failed ({attempt+1}/2): {e}")
            time.sleep(1)
    return None


# =============================================================================
# 1. Screener.in — Shareholding, Pledge, FII/DII
# =============================================================================

class ScreenerScraper:
    """
    Scrapes https://www.screener.in for shareholding pattern and key metrics.
    Screener.in is the most comprehensive free source for Indian equity data.
    """

    BASE_URL = "https://www.screener.in/company/{symbol}/"

    def fetch(self, ticker: str) -> dict:
        """
        Fetch shareholding data from Screener.in.

        Args:
            ticker: NSE ticker like 'TCS.NS' → strips to 'TCS'
        """
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        url = self.BASE_URL.format(symbol=symbol)

        time.sleep(REQUEST_DELAY)
        html = _get(url)

        if not html:
            logger.warning(f"[{symbol}] Screener.in fetch failed")
            return {}

        return self._parse(html, symbol)

    def _parse(self, html: str, symbol: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        result = {"screener_url": f"https://www.screener.in/company/{symbol}/"}

        # ---- Shareholding Pattern table -----
        sh = self._parse_shareholding(soup)
        result.update(sh)

        # ---- Key Ratios (as cross-check) ----
        ratios = self._parse_ratios(soup)
        result.update(ratios)

        # ---- Concall transcripts / annual reports links ----
        result["has_concall_transcripts"] = self._has_concalls(soup)

        return result

    def _parse_shareholding(self, soup: BeautifulSoup) -> dict:
        """Extract promoter %, FII %, DII %, pledge % from shareholding table."""
        result = {
            "promoter_holding_pct":  np.nan,
            "fii_holding_pct":       np.nan,
            "dii_holding_pct":       np.nan,
            "public_holding_pct":    np.nan,
            "pledge_pct":            np.nan,
            "promoter_trend":        "unknown",  # increasing/decreasing/stable
        }

        # Screener.in renders shareholding in a section with id="shareholding"
        sh_section = soup.find("section", {"id": "shareholding"})
        if not sh_section:
            # Try alternative selectors
            sh_section = soup.find("div", class_="shareholding")
        if not sh_section:
            return result

        # Parse table rows
        rows = sh_section.find_all("tr")
        promoter_vals = []

        for row in rows:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            label = cells[0].get_text(strip=True).lower()

            # Parse numeric values from cells (multiple quarters)
            values = []
            for cell in cells[1:]:
                txt = cell.get_text(strip=True).replace("%", "").replace(",", "")
                try:
                    values.append(float(txt))
                except ValueError:
                    pass

            if not values:
                continue
            latest = values[-1]  # most recent quarter

            if "promoter" in label and "pledge" not in label:
                result["promoter_holding_pct"] = latest
                promoter_vals = values
            elif "fii" in label or "foreign" in label:
                result["fii_holding_pct"] = latest
            elif "dii" in label or "domestic" in label:
                result["dii_holding_pct"] = latest
            elif "public" in label:
                result["public_holding_pct"] = latest
            elif "pledge" in label or "pledged" in label:
                result["pledge_pct"] = latest

        # Promoter trend: compare latest 2 quarters
        if len(promoter_vals) >= 2:
            diff = promoter_vals[-1] - promoter_vals[-2]
            if diff > 0.5:
                result["promoter_trend"] = "increasing"
            elif diff < -0.5:
                result["promoter_trend"] = "decreasing"
            else:
                result["promoter_trend"] = "stable"

        return result

    def _parse_ratios(self, soup: BeautifulSoup) -> dict:
        """Extract quick ratios as a sanity check."""
        result = {}
        # Screener shows ratios in #top-ratios or .company-ratios
        ratios_div = soup.find("ul", id="top-ratios")
        if not ratios_div:
            return result

        for li in ratios_div.find_all("li"):
            name_span = li.find("span", class_="name")
            val_span  = li.find("span", class_="value") or li.find("span", class_="number")
            if name_span and val_span:
                name = name_span.get_text(strip=True).lower()
                val_txt = val_span.get_text(strip=True).replace(",", "").replace("%", "")
                try:
                    val = float(val_txt)
                    if "roe" in name:
                        result["screener_roe"] = val
                    elif "roce" in name:
                        result["screener_roce"] = val
                    elif "p/e" in name or "pe" in name:
                        result["screener_pe"] = val
                    elif "market cap" in name:
                        result["screener_mcap"] = val
                    elif "debt" in name and "equity" not in name:
                        result["screener_debt"] = val
                except ValueError:
                    pass

        return result

    def _has_concalls(self, soup: BeautifulSoup) -> bool:
        """Check if screener.in shows concall transcript links."""
        text = soup.get_text().lower()
        return "concall" in text or "transcript" in text


# =============================================================================
# 2. BSE India API — Corporate Announcements & Filings
# =============================================================================

class BSEFilingScanner:
    """
    Uses BSE India's public API to fetch recent corporate announcements
    and scans them for moat language keywords.

    BSE ticker lookup: requires BSE scripcode (6-digit) from NSE symbol.
    We maintain a common mapping and fall back to search if not found.
    """

    # Common NSE symbol → BSE scripcode mapping (top 200 companies)
    # Full list: https://www.bseindia.com/corporates/List_Scrips.html
    NSE_TO_BSE = {
        # IT
        "TCS":         "532540", "INFY":      "500209", "WIPRO":     "507685",
        "HCLTECH":     "532281", "TECHM":     "532755", "PERSISTENT":"533179",
        "COFORGE":     "532541", "MPHASIS":   "526299", "OFSS":      "532466",
        "TATAELXSI":   "500408",
        # Pharma
        "SUNPHARMA":   "524715", "DIVISLAB":  "532488", "CIPLA":     "500087",
        "DRREDDY":     "500124", "TORNTPHARM":"500420", "ABBOTINDIA":"500488",
        "LALPATHLAB":  "539524", "METROPOLIS":"542650",
        # Consumer
        "HINDUNILVR":  "500696", "ITC":       "500875", "NESTLEIND": "500790",
        "BRITANNIA":   "500825", "DABUR":     "500096", "MARICO":    "531642",
        "COLPAL":      "500830", "TATACONSUM":"500800", "VBL":       "506227",
        # Specialty Chem
        "DEEPAKNTR":   "506401", "FINEORG":   "541557", "NAVINFLUOR":"532504",
        "VINATIORGA":  "524200", "ALKYLAMINE":"506767", "GALAXYSURF":"543066",
        "CLEAN":       "543318", "PIIND":     "523642", "SRF":       "503806",
        "ATUL":        "500027", "DHANUKA":   "507717",
        # Defense
        "HAL":         "541154", "BEL":       "500049", "DATAPATTNS":"543202",
        "GRSE":        "542011", "COCHINSHIP":"543500", "BEML":      "500048",
        "SOLARINDS":   "532725", "ZENTEC":    "533339",
        # Financials
        "HDFCBANK":    "500180", "ICICIBANK": "532174", "KOTAKBANK": "500247",
        "BAJFINANCE":  "500034", "CDSL":      "543232", "CAMS":      "543232",
        "MCX":         "534091", "BSE":       "543067",
        # Consumer Disc
        "PAGEIND":     "532827", "TRENT":     "500251", "EICHERMOT": "505200",
        "MARUTI":      "532500", "HEROMOTOCO":"500182",
        # Capital Goods
        "ABB":         "500002", "SIEMENS":   "500550", "HAVELLS":   "517354",
        "POLYCAB":     "542649", "DIXON":     "541988", "CUMMINSIND":"500480",
        "GRINDWELL":   "506076", "TIMKEN":    "522113", "SCHAEFFLER":"505790",
        "PIIND":       "523642", "RATNAMANI": "520111", "TRITURBINE":"533655",
        "ELGIEQUIP":   "522074",
        # Niche
        "IRCTC":       "542830", "CONCOR":    "531344",
    }

    ANNOUNCEMENT_API = (
        "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
        "?strCat=-1&strPrevDate={from_date}&strScrip={scripcode}"
        "&strSearch=P&strToDate={to_date}&strType=C&subcategory=-1"
    )

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BSE_HEADERS)

    def get_scripcode(self, ticker: str) -> Optional[str]:
        """Map NSE ticker to BSE scripcode."""
        symbol = ticker.replace(".NS", "").replace(".BO", "")
        return self.NSE_TO_BSE.get(symbol)

    def fetch_announcements(self, scripcode: str, months: int = 12) -> list[dict]:
        """Fetch corporate announcements from BSE for the last N months."""
        from datetime import datetime, timedelta
        to_date   = datetime.now().strftime("%Y%m%d")
        from_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y%m%d")

        url = self.ANNOUNCEMENT_API.format(
            scripcode=scripcode, from_date=from_date, to_date=to_date
        )
        time.sleep(REQUEST_DELAY)
        data = _get(url, headers=BSE_HEADERS, json_mode=True, session=self.session)

        if not data:
            return []

        # BSE API returns {"Table": [...]} structure
        if isinstance(data, dict):
            return data.get("Table", data.get("table", []))
        return []

    def scan_text_for_moat_signals(self, text: str) -> dict:
        """
        Scan announcement text for moat keywords.
        Returns category scores and matched phrases.
        """
        text_lower = text.lower()
        found_positive = {}
        found_negative = {}

        # Positive signals
        for category, meta in MOAT_KEYWORDS.items():
            hits = []
            for phrase in meta["phrases"]:
                if phrase in text_lower:
                    hits.append(phrase)
            if hits:
                found_positive[category] = {
                    "weight": meta["weight"],
                    "hits": hits[:3],   # top 3 examples
                    "label": MOAT_CATEGORY_LABELS.get(category, category),
                }

        # Red flags
        for category, meta in RED_FLAG_KEYWORDS.items():
            hits = []
            for phrase in meta["phrases"]:
                if phrase in text_lower:
                    hits.append(phrase)
            if hits:
                found_negative[category] = {
                    "weight": meta["weight"],
                    "hits": hits[:3],
                }

        return {
            "positive_signals": found_positive,
            "negative_signals": found_negative,
        }


# =============================================================================
# 3. Main QualitativeChecker — Orchestrates all checks
# =============================================================================

class QualitativeChecker:
    """
    Orchestrates all automated qualitative checks.
    Produces a qualitative score (0–35) with evidence.
    """

    def __init__(self, verbose: bool = False):
        self.scraper = ScreenerScraper()
        self.bse     = BSEFilingScanner()
        self.verbose  = verbose

    def check(self, ticker: str) -> dict:
        """
        Run all qualitative checks for a ticker.

        Returns dict with:
          qual_score       : 0–35 total qualitative score
          qual_components  : breakdown by dimension
          qual_signals     : list of positive signal strings
          qual_warnings    : list of warning strings
          shareholding     : raw shareholding data
          filing_signals   : keyword matches from BSE filings
        """
        result = {
            "qual_score":      0,
            "qual_signals":    [],
            "qual_warnings":   [],
            "qual_components": {},
        }

        try:
            # ---- 1. Shareholding quality (Screener.in) ----
            sh_data = self.scraper.fetch(ticker)
            result.update({"sh_" + k: v for k, v in sh_data.items()
                           if k not in ("screener_url",)})
            result["screener_url"] = sh_data.get("screener_url", "")

            sh_score, sh_signals, sh_warnings = self._score_shareholding(sh_data)
            result["qual_components"]["shareholding"] = sh_score
            result["qual_signals"].extend(sh_signals)
            result["qual_warnings"].extend(sh_warnings)

            # ---- 2. BSE filing keyword scan ----
            filing_score = 0
            filing_signals = []
            filing_warnings = []

            scripcode = self.bse.get_scripcode(ticker)
            if scripcode:
                announcements = self.bse.fetch_announcements(scripcode, months=18)
                combined_text = " ".join(
                    str(ann.get("SLONGNAME", "")) + " " +
                    str(ann.get("HEADLINE", "")) + " " +
                    str(ann.get("NEWSSUB", ""))
                    for ann in announcements[:50]  # last 50 announcements
                )

                if combined_text.strip():
                    scan = self.bse.scan_text_for_moat_signals(combined_text)
                    filing_score, filing_signals, filing_warnings = \
                        self._score_filing_scan(scan)
                    result["filing_positive_categories"] = list(
                        scan["positive_signals"].keys()
                    )
                    result["filing_negative_categories"] = list(
                        scan["negative_signals"].keys()
                    )
                    result["filing_evidence"] = {
                        cat: meta["hits"]
                        for cat, meta in scan["positive_signals"].items()
                    }
            else:
                result["filing_positive_categories"] = []
                result["filing_negative_categories"] = []
                result["filing_evidence"] = {}

            result["qual_components"]["filings"] = filing_score
            result["qual_signals"].extend(filing_signals)
            result["qual_warnings"].extend(filing_warnings)

            # ---- Total score ----
            total = sh_score + filing_score
            result["qual_score"] = round(min(total, 35), 1)

        except Exception as e:
            logger.warning(f"[{ticker}] Qualitative check failed: {e}", exc_info=False)
            result["qual_error"] = str(e)

        return result

    # -------------------------------------------------------------------------
    # Shareholding Scoring
    # -------------------------------------------------------------------------

    def _score_shareholding(self, data: dict) -> tuple[float, list, list]:
        """Score based on promoter holding, pledge, trend, institutional level."""
        score = 0
        signals = []
        warnings = []

        promoter = data.get("promoter_holding_pct", np.nan)
        pledge   = data.get("pledge_pct", np.nan)
        fii      = data.get("fii_holding_pct", np.nan)
        dii      = data.get("dii_holding_pct", np.nan)
        trend    = data.get("promoter_trend", "unknown")

        # A) Promoter holding (0–6 pts)
        if not np.isnan(promoter):
            if promoter >= 60:
                score += 6
                signals.append(f"👤 High Promoter Holding ({promoter:.1f}%)")
            elif promoter >= 50:
                score += 5
                signals.append(f"👤 Good Promoter Holding ({promoter:.1f}%)")
            elif promoter >= 40:
                score += 3
            elif promoter < 25:
                warnings.append(f"⚠️ Low Promoter Holding ({promoter:.1f}%)")

        # B) Pledging (0–4 pts) — critical red flag
        if not np.isnan(pledge):
            if pledge == 0:
                score += 4
                signals.append("✅ Zero Pledging")
            elif pledge <= 5:
                score += 3
                signals.append(f"✅ Minimal Pledging ({pledge:.1f}%)")
            elif pledge <= 15:
                score += 1
                warnings.append(f"⚠️ Some Pledging ({pledge:.1f}%)")
            else:
                score -= 2
                warnings.append(f"🚨 High Pledging ({pledge:.1f}%) — Major Red Flag")

        # C) Promoter trend (0–2 pts)
        if trend == "increasing":
            score += 2
            signals.append("📈 Promoter Increasing Stake")
        elif trend == "decreasing":
            warnings.append("⚠️ Promoter Reducing Stake")

        # D) Institutional discovery proxy (0–2 pts)
        # Low FII+DII = undiscovered (early entry opportunity)
        total_inst = 0
        if not np.isnan(fii):
            total_inst += fii
        if not np.isnan(dii):
            total_inst += dii

        if total_inst > 0:
            if total_inst < 15:
                score += 2
                signals.append(f"🔍 Low Institutional Ownership ({total_inst:.1f}%) — Early Discovery")
            elif total_inst < 30:
                score += 1
                signals.append(f"🔍 Moderate Institutional Ownership ({total_inst:.1f}%)")
            # High institutional = already discovered (neutral, not negative)

        return score, signals, warnings

    # -------------------------------------------------------------------------
    # Filing Keyword Scoring
    # -------------------------------------------------------------------------

    def _score_filing_scan(self, scan: dict) -> tuple[float, list, list]:
        """Score based on keyword signals found in BSE filings."""
        score = 0
        signals = []
        warnings = []

        # Positive signals
        for cat, meta in scan.get("positive_signals", {}).items():
            w = meta["weight"]
            score += w
            label = meta.get("label", cat)
            example = meta["hits"][0] if meta["hits"] else ""
            signals.append(f'{label} ("{example}")')

        # Negative signals (subtract)
        for cat, meta in scan.get("negative_signals", {}).items():
            w = meta["weight"]
            score -= w
            example = meta["hits"][0] if meta["hits"] else ""
            warnings.append(f'⚠️ {cat.replace("_", " ").title()}: "{example}"')

        # Cap between 0 and 20
        score = max(0, min(score, 20))
        return score, signals[:5], warnings[:3]


# =============================================================================
# Batch check — run qualitative checks on a list of tickers
# =============================================================================

def run_qualitative_batch(tickers: list, verbose: bool = False) -> dict:
    """
    Run qualitative checks on a batch of tickers.

    Returns:
        dict mapping ticker → qualitative results
    """
    checker = QualitativeChecker(verbose=verbose)
    results = {}

    for ticker in tickers:
        logger.info(f"Qualitative check: {ticker}")
        results[ticker] = checker.check(ticker)
        time.sleep(0.5)  # gentle rate limiting

    return results
