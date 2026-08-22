#!/usr/bin/env python3
# =============================================================================
# deep_dive.py — Full 3-Layer Analysis on a Shortlist of Companies
# =============================================================================
# Runs: Quantitative → Trajectory → Qualitative on a targeted list
#
# Usage:
#   python deep_dive.py ZENTEC.NS GRSE.NS DATAPATTNS.NS ATUL.NS DHANUKA.NS
#   python deep_dive.py --from-file watchlist.txt
#   python deep_dive.py --sector "Defense & Aerospace" --min-score 55
#
# Output: Rich console report + Excel with all three scoring layers
# =============================================================================

import argparse
import sys
import time
import os
import math
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import box

from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from moat_scorer import MoatScorer
from trajectory_analyzer import TrajectoryAnalyzer
from qualitative_checker import QualitativeChecker
from early_moat_screener import compute_early_moat_score, _trunc, _fmt_pct, _fmt_ratio
from midsmall_universe import MIDSMALL_UNIVERSE

console = Console()

logging.basicConfig(level=logging.WARNING,
                    handlers=[logging.FileHandler("deep_dive.log")])
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deep Dive — Full 3-Layer Analysis (Quant + Trajectory + Qualitative)"
    )
    parser.add_argument("tickers", nargs="*",
                        help="NSE tickers to analyse")
    parser.add_argument("--from-file", type=str,
                        help="File with one NSE ticker per line")
    parser.add_argument("--sector", type=str,
                        help="Start from a sector's universe (applies --min-score filter)")
    parser.add_argument("--min-score", type=float, default=0,
                        help="Pre-filter: only deep-dive on companies with early-moat score >= N")
    parser.add_argument("--skip-qual", action="store_true",
                        help="Skip qualitative checks (faster, no scraping)")
    return parser.parse_args()


def get_tickers(args) -> list:
    tickers = list(args.tickers or [])

    if args.from_file:
        with open(args.from_file) as f:
            tickers += [line.strip() for line in f if line.strip()
                        and not line.startswith("#")]

    if args.sector and args.sector in MIDSMALL_UNIVERSE:
        tickers += MIDSMALL_UNIVERSE[args.sector]

    # Deduplicate
    seen = set()
    return [t for t in tickers if not (t in seen or seen.add(t))]


def run_layer1_2(tickers: list, min_score: float) -> list:
    """Run quantitative + trajectory layers. Return scored list."""
    fetcher = DataFetcher()
    calc    = MetricsCalculator()
    scorer  = MoatScorer()
    traj    = TrajectoryAnalyzer()

    results = []
    console.print(f"\n[cyan]Layer 1 & 2: Quantitative + Trajectory ({len(tickers)} tickers)[/cyan]")

    for ticker in track(tickers, description="Scoring...", console=console):
        try:
            data = fetcher.fetch(ticker)
            if not data:
                continue
            metrics = calc.compute(data)
            scored  = scorer.score(metrics)
            scored  = traj.analyze(data, scored)
            scored  = compute_early_moat_score(scored)

            if scored["early_moat_score"] >= min_score:
                results.append(scored)
        except Exception as e:
            logging.warning(f"[{ticker}] L1/L2 error: {e}")

    return sorted(results, key=lambda x: x.get("early_moat_score", 0), reverse=True)


def run_layer3(results: list, skip: bool) -> list:
    """Run qualitative checks on the scored list."""
    if skip:
        console.print("\n[dim]Skipping qualitative layer (--skip-qual)[/dim]")
        for r in results:
            r["qual_score"] = np.nan
        return results

    checker = QualitativeChecker()
    console.print(f"\n[magenta]Layer 3: Qualitative Checks ({len(results)} companies)[/magenta]")
    console.print("[dim]  Fetching from Screener.in and BSE API — be patient...[/dim]\n")

    for r in track(results, description="Qual checking...", console=console):
        ticker = r.get("ticker", "")
        try:
            qual = checker.check(ticker)
            r.update(qual)
        except Exception as e:
            logging.warning(f"[{ticker}] L3 error: {e}")
            r["qual_score"] = 0
        time.sleep(0.5)

    return results


def compute_composite(results: list) -> list:
    """Compute final composite score = early moat (70%) + qual (30%)."""
    for r in results:
        early = r.get("early_moat_score", 0)
        qual  = r.get("qual_score", np.nan)

        if not np.isnan(qual):
            # Scale qual to 30pts, early moat to 70pts
            composite = early * 0.70 + (qual / 35) * 30
        else:
            composite = early  # no qual data

        r["composite_score"] = round(composite, 1)
        r["composite_label"] = _composite_label(composite)

    return sorted(results, key=lambda x: x.get("composite_score", 0), reverse=True)


def _composite_label(score: float) -> str:
    if score >= 80:
        return "🏆 CONVICTION BUY"
    elif score >= 65:
        return "🔥 Early Compounder"
    elif score >= 50:
        return "🌱 Emerging Moat"
    elif score >= 38:
        return "👀 Watch Closely"
    else:
        return "❌ Not Yet"


def print_deep_dive_report(results: list) -> None:
    """Print the full 3-layer report."""

    # Summary table
    table = Table(
        title="\n🔬 Deep Dive — 3-Layer Analysis",
        box=box.ROUNDED, show_lines=True,
        header_style="bold green",
    )
    for col, justify in [
        ("#", "right"), ("Ticker", "left"), ("Company", "left"),
        ("Composite", "right"), ("Label", "left"),
        ("L1+L2\nEarly Moat", "right"), ("L3\nQual", "right"),
        ("Promoter%", "right"), ("Pledge%", "right"),
        ("Promoter\nTrend", "left"), ("Institutional\nOwn%", "right"),
        ("Filing Signals", "left"),
    ]:
        table.add_column(col, justify=justify)

    for rank, r in enumerate(results, 1):
        fii = r.get("sh_fii_holding_pct", np.nan)
        dii = r.get("sh_dii_holding_pct", np.nan)
        inst = (fii if not np.isnan(fii) else 0) + (dii if not np.isnan(dii) else 0)

        filing_cats = r.get("filing_positive_categories", [])
        filing_str  = ", ".join(
            c.replace("_", " ").title() for c in filing_cats[:3]
        ) or "—"

        comp = r.get("composite_score", 0)
        color = "green" if comp >= 65 else "yellow" if comp >= 50 else "white"

        prom  = r.get("sh_promoter_holding_pct", np.nan)
        pledge = r.get("sh_pledge_pct", np.nan)
        trend  = r.get("sh_promoter_trend", "—")

        table.add_row(
            str(rank),
            str(r.get("ticker", "")),
            _trunc(str(r.get("name", "")), 24),
            f"[bold {color}]{comp:.1f}[/bold {color}]",
            str(r.get("composite_label", "")),
            f"{r.get('early_moat_score', 0):.1f}",
            f"{r.get('qual_score', 0):.1f}" if not np.isnan(r.get("qual_score", np.nan)) else "—",
            _fmt_pct(prom),
            f"{pledge:.1f}%" if not np.isnan(pledge) else "—",
            _trend_icon(trend),
            f"{inst:.1f}%" if inst > 0 else "—",
            filing_str,
        )

    console.print(table)

    # Detailed cards for top 5
    console.print("\n[bold green]━━━  TOP 5 — DETAILED SIGNALS  ━━━[/bold green]")
    for r in results[:5]:
        _print_company_card(r)


def _print_company_card(r: dict) -> None:
    """Print a detailed card for one company."""
    ticker = r.get("ticker", "")
    name   = r.get("name", ticker)
    comp   = r.get("composite_score", 0)

    console.print(f"\n  [bold]{ticker}[/bold] — {name}  "
                  f"[bold yellow]Score: {comp:.1f}[/bold yellow]  "
                  f"{r.get('composite_label', '')}")

    # Quantitative highlights
    roce = r.get("roce_avg", np.nan)
    gm   = r.get("gross_margin_avg", np.nan)
    rev_cagr = r.get("rev_cagr", np.nan)
    de   = r.get("debt_equity_latest", np.nan)
    console.print(
        f"  [dim]ROCE: {_fmt_pct(roce)} | GM: {_fmt_pct(gm)} | "
        f"Rev CAGR: {_fmt_pct(rev_cagr)} | D/E: {_fmt_ratio(de)}[/dim]"
    )

    # Trajectory signals
    traj_sigs = r.get("trajectory_signals", [])
    if traj_sigs:
        console.print(f"  [cyan]Trajectory: {' · '.join(traj_sigs[:4])}[/cyan]")

    # Qualitative signals
    qual_sigs = r.get("qual_signals", [])
    if qual_sigs:
        console.print(f"  [green]Qualitative: {' · '.join(qual_sigs[:4])}[/green]")

    # Warnings
    warnings = r.get("qual_warnings", []) + r.get("trajectory_warnings", [])
    if warnings:
        console.print(f"  [red]Warnings: {' · '.join(warnings[:3])}[/red]")

    # Evidence from filings
    evidence = r.get("filing_evidence", {})
    for cat, phrases in list(evidence.items())[:2]:
        console.print(f"  [dim]  BSE filing ─ {cat}: \"{phrases[0]}\"[/dim]")

    # Screener link
    screener_url = r.get("screener_url", "")
    if screener_url:
        console.print(f"  [blue underline]{screener_url}[/blue underline]")


def _trend_icon(trend: str) -> str:
    return {"increasing": "📈 Rising", "decreasing": "📉 Falling",
            "stable": "➡️ Stable"}.get(trend, "—")


def save_excel(results: list, output_dir: str = "output") -> None:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.join(output_dir, f"deep_dive_{ts}.xlsx")

    display_cols = [
        "ticker", "name", "sector", "composite_score", "composite_label",
        "early_moat_score", "qual_score",
        "score_total", "trajectory_score",
        # Shareholding
        "sh_promoter_holding_pct", "sh_pledge_pct",
        "sh_fii_holding_pct", "sh_dii_holding_pct", "sh_promoter_trend",
        # Filing
        "filing_positive_categories", "filing_negative_categories",
        # Trajectory
        "roce_traj_delta", "om_traj_delta", "rev_cagr_3y_traj",
        "rev_is_accelerating", "is_self_funding", "om_at_peak",
        # Quant
        "roce_avg", "gross_margin_avg", "op_margin_avg", "rev_cagr",
        "debt_equity_latest", "cfo_pat_avg", "fcf_conversion_avg",
        "market_cap_cr", "current_price", "pe_ratio", "pb_ratio",
        # Signals
        "screener_url",
    ]

    df = pd.DataFrame(results)
    cols = [c for c in display_cols if c in df.columns]
    export = df[cols].copy()

    # Flatten lists for Excel
    for col in ["filing_positive_categories", "filing_negative_categories"]:
        if col in export.columns:
            export[col] = export[col].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )

    for col in export.select_dtypes(include=[float]).columns:
        export[col] = export[col].round(2)

    export.to_excel(path, index=False)
    console.print(f"\n  📊 Excel → {path}")


def main():
    args = parse_args()
    tickers = get_tickers(args)

    if not tickers:
        console.print("[red]No tickers specified. Use: python deep_dive.py TCS.NS INFY.NS[/red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold green]🔬  Deep Dive Analysis[/bold green]\n"
        f"[dim]{len(tickers)} companies · 3 layers: Quant → Trajectory → Qualitative[/dim]",
        border_style="green"
    ))

    # Layer 1+2: Quantitative + Trajectory
    results = run_layer1_2(tickers, args.min_score)

    if not results:
        console.print("[red]No companies passed quantitative filters.[/red]")
        return

    console.print(f"\n[cyan]{len(results)} companies passed quant filter — running qualitative layer[/cyan]")

    # Layer 3: Qualitative
    results = run_layer3(results, args.skip_qual)

    # Composite score
    results = compute_composite(results)

    # Display
    print_deep_dive_report(results)

    # Save
    save_excel(results)


if __name__ == "__main__":
    main()
