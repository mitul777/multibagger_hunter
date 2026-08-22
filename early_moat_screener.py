#!/usr/bin/env python3
# =============================================================================
# early_moat_screener.py — Entry Point for Mid/Small Cap Early Moat Detection
# =============================================================================
# Usage:
#   python early_moat_screener.py                          # full midsmall universe
#   python early_moat_screener.py --sector "Specialty Chemicals"
#   python early_moat_screener.py --sector "Defense & Aerospace"
#   python early_moat_screener.py --tickers DEEPAKNTR.NS VINATI.NS FINEORG.NS
#   python early_moat_screener.py --top 20 --min-score 55
#   python early_moat_screener.py --max-mcap 5000         # pure smallcap only
# =============================================================================
#
# SCORING MODEL (different from large-cap screener):
#
#   Standard Moat Score   : 60 pts  (reduced — absolute levels less reliable)
#   Trajectory Score      : 40 pts  (new — direction is everything for early stage)
#   ─────────────────────────────────
#   Total                 : 100 pts
#
# CATEGORIES:
#   ≥ 75  →  🔥 Early Compounder  (high conviction early moat)
#   ≥ 55  →  🌱 Emerging Moat     (worth deep-diving)
#   ≥ 40  →  👀 Watch Closely     (trajectory positive, wait for confirmation)
#   < 40  →  ❌ Not Yet
# =============================================================================

import argparse
import logging
import sys
import time
import math
import os
import numpy as np
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from datetime import datetime

from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from moat_scorer import MoatScorer
from trajectory_analyzer import TrajectoryAnalyzer
from midsmall_universe import (
    MIDSMALL_UNIVERSE, ALL_MIDSMALL_STOCKS, MIDSMALL_HARD_FILTERS,
    SECTOR_MOAT_TYPE
)

console = Console()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("early_moat_screener.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# =============================================================================
# Utility Helpers (defined early — used throughout)
# =============================================================================

def _fmt_pct(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    return f"{val:.1f}%"

def _fmt_ratio(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    return f"{val:.2f}x"

def _fmt_delta(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}ppts"

def _trunc(s: str, n: int) -> str:
    return s[:n] + "…" if len(s) > n else s


# =============================================================================
# Argument Parser
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Early Moat Screener — Find tomorrow's compounders in midcap/smallcap"
    )
    parser.add_argument("--tickers",    nargs="+", metavar="TICKER",
                        help="Custom NSE tickers to screen")
    parser.add_argument("--sector",     type=str, default=None,
                        help=f"Sector filter. Options: {list(MIDSMALL_UNIVERSE.keys())}")
    parser.add_argument("--top",        type=int, default=20,
                        help="Number of top results to show (default: 20)")
    parser.add_argument("--min-score",  type=float, default=0.0)
    parser.add_argument("--max-mcap",   type=float, default=None,
                        help="Maximum market cap in Cr (e.g. 5000 for pure smallcap)")
    parser.add_argument("--min-mcap",   type=float, default=None,
                        help="Minimum market cap in Cr (e.g. 500)")
    parser.add_argument("--no-filter",  action="store_true",
                        help="Skip hard filters")
    return parser.parse_args()


# =============================================================================
# Composite Early Moat Score (60% standard + 40% trajectory)
# =============================================================================

def compute_early_moat_score(scored: dict) -> dict:
    """
    Combine the standard moat score and trajectory score into a single
    early-moat composite score.

    Standard score (from MoatScorer) out of 100 → scaled to 60
    Trajectory score (from TrajectoryAnalyzer) out of 40 → kept as-is
    """
    std_score  = scored.get("score_total", 0)
    traj_score = scored.get("trajectory_score", 0)

    # Scale standard score to 60pts
    std_scaled = std_score * 0.60

    composite = std_scaled + traj_score
    scored["early_moat_score"] = round(min(composite, 100), 1)
    scored["std_score_contribution"]  = round(std_scaled, 1)
    scored["traj_score_contribution"] = round(traj_score, 1)
    scored["early_moat_label"]        = _early_label(scored["early_moat_score"])
    return scored


def _early_label(score: float) -> str:
    if score >= 75:
        return "🔥 Early Compounder"
    elif score >= 55:
        return "🌱 Emerging Moat"
    elif score >= 40:
        return "👀 Watch Closely"
    else:
        return "❌ Not Yet"


# =============================================================================
# Hard Filters for Midcap / Smallcap
# =============================================================================

def passes_filters(metrics: dict, args) -> tuple[bool, str]:
    f = MIDSMALL_HARD_FILTERS

    mc = metrics.get("market_cap_cr", np.nan)
    if not np.isnan(mc):
        if mc < f["min_market_cap_cr"]:
            return False, f"Too small (₹{mc:.0f}Cr < ₹{f['min_market_cap_cr']}Cr)"
        if mc > f["max_market_cap_cr"]:
            return False, f"Too large (₹{mc:.0f}Cr > ₹{f['max_market_cap_cr']}Cr)"

    # Override with CLI args
    if args.max_mcap and not np.isnan(mc) and mc > args.max_mcap:
        return False, f"Above max mcap filter (₹{mc:.0f}Cr)"
    if args.min_mcap and not np.isnan(mc) and mc < args.min_mcap:
        return False, f"Below min mcap filter (₹{mc:.0f}Cr)"

    de = metrics.get("debt_equity_latest", np.nan)
    if not np.isnan(de) and de > f["max_debt_equity"]:
        return False, f"High D/E ({de:.1f})"

    n_yrs = metrics.get("n_years", 0)
    if n_yrs < f["min_years_data"]:
        return False, f"Too little data ({n_yrs} yrs)"

    return True, ""


# =============================================================================
# Display
# =============================================================================

def print_results(results: list, top_n: int) -> None:
    top = sorted(results, key=lambda x: x.get("early_moat_score", 0), reverse=True)[:top_n]

    table = Table(
        title=f"\n🔥 Top {top_n} Early Moat Candidates — Mid & Small Cap",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    cols = [
        ("#",             "right"),
        ("Ticker",        "left"),
        ("Company",       "left"),
        ("Sector",        "left"),
        ("Score",         "right"),
        ("Label",         "left"),
        ("ROCE Traj",     "right"),
        ("OM Δ",          "right"),
        ("Rev CAGR",      "right"),
        ("D/E",           "right"),
        ("MCap Cr",       "right"),
        ("🔑 Key Signals", "left"),
    ]
    for name, justify in cols:
        table.add_column(name, justify=justify)

    for rank, row in enumerate(top, 1):
        all_signals = (
            row.get("trajectory_signals", [])[:2] +
            row.get("moat_signals", [])[:1]
        )
        signals_str = "; ".join(all_signals[:2])

        roce_delta = row.get("roce_traj_delta", np.nan)
        om_delta   = row.get("om_traj_delta", np.nan)
        cagr_3y    = row.get("rev_cagr_3y_traj", np.nan)
        mc         = row.get("market_cap_cr", np.nan)

        score = row.get("early_moat_score", 0)
        color = "red" if score >= 75 else "yellow" if score >= 55 else "white"

        table.add_row(
            str(rank),
            str(row.get("ticker", "")),
            _trunc(str(row.get("name", "")), 26),
            _trunc(str(row.get("sector", "")), 22),
            f"[bold {color}]{score:.1f}[/bold {color}]",
            str(row.get("early_moat_label", "")),
            _fmt_delta(roce_delta),
            _fmt_delta(om_delta),
            _fmt_pct(cagr_3y),
            _fmt_ratio(row.get("debt_equity_latest")),
            f"₹{mc:,.0f}" if not np.isnan(mc) else "—",
            signals_str,
        )

    console.print(table)


def print_summary(results: list) -> None:
    sorted_r = sorted(results, key=lambda x: x.get("early_moat_score", 0), reverse=True)

    console.print("\n[bold magenta]━━━  EARLY MOAT SCREENING SUMMARY  ━━━[/bold magenta]")
    console.print(f"  Total companies scored  : {len(results)}")

    ec  = sum(1 for r in results if r.get("early_moat_score", 0) >= 75)
    em  = sum(1 for r in results if 55 <= r.get("early_moat_score", 0) < 75)
    wc  = sum(1 for r in results if 40 <= r.get("early_moat_score", 0) < 55)
    no  = sum(1 for r in results if r.get("early_moat_score", 0) < 40)

    console.print(f"  🔥 Early Compounder (≥75): {ec}")
    console.print(f"  🌱 Emerging Moat    (≥55): {em}")
    console.print(f"  👀 Watch Closely    (≥40): {wc}")
    console.print(f"  ❌ Not Yet          (<40): {no}")

    console.print("\n[bold magenta]━━━  TOP 5 EARLY COMPOUNDERS  ━━━[/bold magenta]")
    for rank, r in enumerate(sorted_r[:5], 1):
        signals = "; ".join((r.get("trajectory_signals", []) +
                             r.get("moat_signals", []))[:3])
        console.print(
            f"  {rank}. [bold]{r.get('ticker',''):<18}[/bold] "
            f"Score: [bold yellow]{r.get('early_moat_score',0):.1f}[/bold yellow]  "
            f"{r.get('early_moat_label','')}  |  {signals}"
        )


def save_reports(results: list, top_n: int, output_dir: str = "output") -> None:
    """Save Excel and HTML reports."""
    import pandas as pd
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    sorted_r = sorted(results, key=lambda x: x.get("early_moat_score", 0), reverse=True)
    df = pd.DataFrame(sorted_r)

    # --- Excel ---
    display_cols = [
        "ticker", "name", "sector", "industry",
        "early_moat_score", "early_moat_label",
        "std_score_contribution", "traj_score_contribution",
        "score_total", "trajectory_score",
        "market_cap_cr", "current_price",
        # Trajectory
        "roce_traj_delta", "om_traj_delta", "rev_cagr_3y_traj", "rev_yoy_latest",
        "rev_is_accelerating", "is_self_funding", "om_at_peak",
        "roce_traj_latest", "de_traj_delta",
        # Standard
        "roce_avg", "gross_margin_avg", "op_margin_avg", "net_margin_latest",
        "rev_cagr", "eps_cagr", "debt_equity_latest", "cfo_pat_avg",
        "fcf_conversion_avg", "interest_coverage_avg", "net_cash_cr",
        "pe_ratio", "pb_ratio", "ev_ebitda",
    ]
    cols = [c for c in display_cols if c in df.columns]
    export_df = df[cols].copy()
    for c in export_df.select_dtypes(include=[float]).columns:
        export_df[c] = export_df[c].round(2)

    xl_path = os.path.join(output_dir, f"early_moat_{ts}.xlsx")
    export_df.to_excel(xl_path, index=False)
    console.print(f"\n  📊 Excel  → {xl_path}")

    # --- HTML ---
    rows_html = ""
    for rank, row in enumerate(sorted_r[:top_n], 1):
        label = row.get("early_moat_label", "")
        row_class = (
            "compounder" if "Compounder" in str(label) else
            "emerging"   if "Emerging"   in str(label) else
            "watch"      if "Watch"       in str(label) else "none"
        )
        traj_sigs = "<br>".join(row.get("trajectory_signals", [])[:3])
        warnings  = "<br>".join(row.get("trajectory_warnings", [])[:2])
        mc  = row.get("market_cap_cr", np.nan)
        mc_str = f"₹{mc:,.0f} Cr" if not (isinstance(mc, float) and math.isnan(mc)) else "—"

        rows_html += f"""
        <tr class="{row_class}">
          <td><b>{rank}</b></td>
          <td><code>{row.get('ticker','')}</code></td>
          <td>{_trunc(str(row.get('name','')), 35)}</td>
          <td>{_trunc(str(row.get('sector','')), 28)}</td>
          <td><b>{row.get('early_moat_score',0):.1f}</b></td>
          <td>{label}</td>
          <td>{_fmt_delta(row.get('roce_traj_delta'))}</td>
          <td>{_fmt_delta(row.get('om_traj_delta'))}</td>
          <td>{_fmt_pct(row.get('rev_cagr_3y_traj'))}</td>
          <td>{_fmt_ratio(row.get('debt_equity_latest'))}</td>
          <td>{mc_str}</td>
          <td class="signals">{traj_sigs}</td>
          <td class="warn">{warnings}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Early Moat Screener — {ts}</title>
<style>
  body  {{ font-family:'Segoe UI',sans-serif; background:#0d1117; color:#c9d1d9; margin:20px; }}
  h1    {{ color:#f78166; border-bottom:2px solid #30363d; padding-bottom:10px; }}
  h2    {{ color:#ff7b72; }}
  .meta {{ color:#8b949e; font-size:.85em; margin-bottom:20px; }}
  table {{ border-collapse:collapse; width:100%; font-size:.82em; }}
  th    {{ background:#6e40c9; color:#fff; padding:8px 10px; text-align:left; position:sticky; top:0; }}
  td    {{ padding:5px 9px; border-bottom:1px solid #21262d; vertical-align:top; }}
  tr.compounder {{ background:#1a0a1e; }}
  tr.emerging   {{ background:#12180a; }}
  tr.watch      {{ background:#0a1222; }}
  tr:hover      {{ background:#161b22 !important; }}
  code   {{ background:#21262d; padding:2px 6px; border-radius:4px; color:#79c0ff; }}
  .signals {{ font-size:.78em; color:#7ee787; max-width:260px; }}
  .warn    {{ font-size:.78em; color:#f78166; max-width:200px; }}
  .framework {{ max-width:700px; background:#161b22; border:1px solid #30363d; border-radius:8px; padding:16px; margin:20px 0; }}
</style>
</head>
<body>
<h1>🔥 Early Moat Screener — Mid & Small Cap Compounders</h1>
<div class="meta">
  Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} &nbsp;|&nbsp;
  Universe: NSE Mid+Small Cap &nbsp;|&nbsp;
  Total screened: {len(results)} stocks
</div>

<div class="framework">
  <b>Scoring: Standard Moat (60pts × 0.6) + Trajectory (40pts) = 100pts</b><br><br>
  🔥 Early Compounder ≥75 &nbsp;|&nbsp; 🌱 Emerging Moat ≥55 &nbsp;|&nbsp; 👀 Watch ≥40
  <br><br>
  <b>Trajectory signals:</b> ROCE improving · Margins expanding · Revenue accelerating ·
  Self-funding capex · Pricing power test passed
</div>

<h2>Top {top_n} Early Moat Candidates</h2>
<table>
  <thead>
    <tr>
      <th>#</th><th>Ticker</th><th>Company</th><th>Sector</th>
      <th>Score</th><th>Label</th>
      <th>ROCE Δ</th><th>OM Δ</th><th>Rev CAGR%</th>
      <th>D/E</th><th>Market Cap</th>
      <th>🔑 Trajectory Signals</th><th>⚠️ Warnings</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<div class="meta" style="margin-top:30px;">
  ⚠️ Research tool only. Not financial advice. Verify with primary sources before investing.
</div>
</body>
</html>"""

    html_path = os.path.join(output_dir, f"early_moat_{ts}.html")
    with open(html_path, "w") as f:
        f.write(html)
    console.print(f"  🌐 HTML   → {html_path}")


# =============================================================================
# Main Pipeline
# =============================================================================

def run(args):
    console.print(Panel.fit(
        "[bold magenta]🔥  Early Moat Screener — Mid & Small Cap[/bold magenta]\n"
        "[dim]Find tomorrow's compounders before the market does[/dim]",
        border_style="magenta"
    ))

    # Select universe
    if args.tickers:
        tickers = args.tickers
        console.print(f"[cyan]Custom tickers: {len(tickers)}[/cyan]")
    elif args.sector:
        if args.sector not in MIDSMALL_UNIVERSE:
            console.print(f"[red]Unknown sector. Options:\n{list(MIDSMALL_UNIVERSE.keys())}[/red]")
            sys.exit(1)
        tickers = MIDSMALL_UNIVERSE[args.sector]
        moat_type = SECTOR_MOAT_TYPE.get(args.sector, "")
        console.print(f"[cyan]Sector: {args.sector} | Moat Type: {moat_type} | {len(tickers)} stocks[/cyan]")
    else:
        tickers = ALL_MIDSMALL_STOCKS
        console.print(f"[cyan]Full mid/smallcap universe: {len(tickers)} tickers[/cyan]")

    fetcher  = DataFetcher()
    calc     = MetricsCalculator()
    scorer   = MoatScorer()
    traj     = TrajectoryAnalyzer()

    results  = []
    skipped  = []
    failed   = []

    console.print(f"\n[bold]Fetching & analyzing... (may take a few minutes)[/bold]\n")
    start = time.time()

    for ticker in tqdm(tickers, desc="Screening", unit="stock", colour="magenta"):
        try:
            data = fetcher.fetch(ticker)
            if data is None:
                failed.append(ticker)
                continue

            # Standard metrics
            metrics = calc.compute(data)

            # Hard filters
            if not args.no_filter:
                ok, reason = passes_filters(metrics, args)
                if not ok:
                    skipped.append((ticker, reason))
                    continue

            # Standard moat score
            scored = scorer.score(metrics)

            # Trajectory analysis (the early-moat layer)
            scored = traj.analyze(data, scored)

            # Composite early moat score
            scored = compute_early_moat_score(scored)

            if scored["early_moat_score"] >= args.min_score:
                results.append(scored)

        except Exception as e:
            failed.append(ticker)
            logging.warning(f"[{ticker}] Error: {e}", exc_info=False)

    elapsed = time.time() - start
    console.print(f"\n[dim]Completed {elapsed:.1f}s | Scored: {len(results)} | "
                  f"Filtered: {len(skipped)} | Failed: {len(failed)}[/dim]")

    if failed:
        console.print(f"[yellow]⚠ Failed tickers: {', '.join(failed[:8])}"
                      f"{'...' if len(failed) > 8 else ''}[/yellow]")

    if not results:
        console.print("[red]No results. Try --no-filter or add more tickers.[/red]")
        return

    print_results(results, args.top)
    print_summary(results)
    save_reports(results, args.top)


if __name__ == "__main__":
    args = parse_args()
    run(args)
