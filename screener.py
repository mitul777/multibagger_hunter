#!/usr/bin/env python3
# =============================================================================
# screener.py — Main Entry Point for Indian Equity Moat Screener
# =============================================================================
# Usage:
#   python screener.py                     # screen full universe
#   python screener.py --sector "IT"       # filter by sector
#   python screener.py --tickers TCS.NS INFY.NS   # custom tickers
#   python screener.py --top 10            # show top N
#   python screener.py --min-score 60      # filter by minimum score
# =============================================================================

import argparse
import logging
import sys
import time
from tqdm import tqdm
from rich.console import Console
from rich.panel import Panel

from config import STOCK_UNIVERSE, ALL_STOCKS, HARD_FILTERS, OUTPUT
from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from moat_scorer import MoatScorer
from report_generator import ReportGenerator

console = Console()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("screener.log"), logging.StreamHandler(sys.stdout)],
)
# Suppress yfinance noise
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Indian Equity Moat Screener — Identify companies with durable competitive advantages"
    )
    parser.add_argument(
        "--tickers", nargs="+", metavar="TICKER",
        help="Custom list of NSE tickers (e.g. TCS.NS INFY.NS)"
    )
    parser.add_argument(
        "--sector", type=str, default=None,
        help=f"Filter to a specific sector. Options: {list(STOCK_UNIVERSE.keys())}"
    )
    parser.add_argument(
        "--top", type=int, default=OUTPUT["top_n_display"],
        help="Number of top results to display (default: 25)"
    )
    parser.add_argument(
        "--min-score", type=float, default=0.0,
        help="Minimum total score to include in results (default: 0)"
    )
    parser.add_argument(
        "--no-hard-filter", action="store_true",
        help="Disable hard pre-screening filters"
    )
    return parser.parse_args()


def get_ticker_list(args) -> list[str]:
    """Determine which tickers to screen."""
    if args.tickers:
        tickers = args.tickers
        console.print(f"[cyan]Screening {len(tickers)} custom tickers...[/cyan]")
    elif args.sector:
        sector = args.sector
        if sector not in STOCK_UNIVERSE:
            console.print(f"[red]Sector '{sector}' not found.[/red]")
            console.print(f"Available: {list(STOCK_UNIVERSE.keys())}")
            sys.exit(1)
        tickers = STOCK_UNIVERSE[sector]
        console.print(f"[cyan]Screening {len(tickers)} tickers in '{sector}' sector...[/cyan]")
    else:
        tickers = ALL_STOCKS
        console.print(f"[cyan]Screening full universe: {len(tickers)} tickers...[/cyan]")

    return tickers


def passes_hard_filters(metrics: dict) -> tuple[bool, str]:
    """
    Apply hard-cutoff filters before scoring.
    Returns (passes, reason_if_fails).
    """
    f = HARD_FILTERS

    mc = metrics.get("market_cap_cr")
    if mc is not None and mc == mc and mc < f["min_market_cap_cr"]:
        return False, f"Market cap ₹{mc:.0f}Cr < ₹{f['min_market_cap_cr']}Cr"

    de = metrics.get("debt_equity_latest")
    if de is not None and de == de and de > f["max_debt_equity"]:
        return False, f"D/E {de:.1f} > {f['max_debt_equity']}"

    roce = metrics.get("roce_avg")
    if roce is not None and roce == roce and roce < f["min_roce_pct"]:
        return False, f"ROCE {roce:.1f}% < {f['min_roce_pct']}%"

    n_years = metrics.get("n_years", 0)
    if n_years < f["min_years_data"]:
        return False, f"Insufficient data ({n_years} years)"

    return True, ""


def run_screener(args):
    """Main screening pipeline."""
    console.print(Panel.fit(
        "[bold cyan]🏰  Indian Equity Moat Screener[/bold cyan]\n"
        "[dim]Identifies companies with durable competitive advantages[/dim]",
        border_style="cyan"
    ))

    tickers   = get_ticker_list(args)
    fetcher   = DataFetcher()
    calc      = MetricsCalculator()
    scorer    = MoatScorer()
    reporter  = ReportGenerator(output_dir=OUTPUT["output_dir"])

    results   = []
    skipped   = []
    failed    = []

    console.print(f"\n[bold]Fetching financial data...[/bold] (this may take a few minutes)\n")
    start_time = time.time()

    for ticker in tqdm(tickers, desc="Screening", unit="stock", colour="cyan"):
        try:
            # 1. Fetch data
            data = fetcher.fetch(ticker)
            if data is None:
                failed.append(ticker)
                continue

            # 2. Compute metrics
            metrics = calc.compute(data)

            # 3. Hard filter
            if not args.no_hard_filter:
                passes, reason = passes_hard_filters(metrics)
                if not passes:
                    skipped.append((ticker, reason))
                    continue

            # 4. Score
            scored = scorer.score(metrics)

            # 5. Apply min-score filter
            if scored["score_total"] >= args.min_score:
                results.append(scored)

        except Exception as e:
            failed.append(ticker)
            logging.warning(f"[{ticker}] Unexpected error: {e}", exc_info=False)

    elapsed = time.time() - start_time

    console.print(f"\n[dim]Completed in {elapsed:.1f}s | "
                  f"Scored: {len(results)} | "
                  f"Filtered: {len(skipped)} | "
                  f"Failed: {len(failed)}[/dim]\n")

    if failed:
        console.print(f"[yellow]⚠ Could not fetch data for: {', '.join(failed[:10])}"
                      f"{'...' if len(failed) > 10 else ''}[/yellow]")

    if not results:
        console.print("[red]No companies passed the screening criteria.[/red]")
        console.print("[dim]Try --no-hard-filter or --min-score 0 to relax filters.[/dim]")
        return

    # 5. Generate reports
    OUTPUT["top_n_display"] = args.top
    reporter.generate(results)


if __name__ == "__main__":
    args = parse_args()
    run_screener(args)
