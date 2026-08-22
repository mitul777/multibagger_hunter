#!/usr/bin/env python3
# =============================================================================
# multibagger_hunter.py — Scans the ENTIRE NSE for Undiscovered Microcaps
# =============================================================================
# 1. Downloads the master list of all 2000+ NSE listed equities.
# 2. Filters for Market Cap < ₹7,500 Cr.
# 3. Requires Trajectory Score >= 25 (Fundamentals inflecting).
# 4. Requires Institutional Holding < 15% (Undiscovered).
# =============================================================================

import os
import io
import time
import requests
import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.progress import track
from rich.panel import Panel
from rich.table import Table

# Import our existing analytical engines
from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from trajectory_analyzer import TrajectoryAnalyzer
from qualitative_checker import QualitativeChecker

import requests_cache
# Install a global transparent cache. 
# ANY requests.get() made by yfinance, bs4, or our code will be cached in this SQLite DB for 24 hours.
requests_cache.install_cache('market_data_cache', expire_after=86400)

console = Console()

# Configuration Thresholds
MAX_MCAP_CR = 7500         # Must be a small/micro cap
MIN_TRAJECTORY_SCORE = 25  # Must have improving fundamentals
MAX_INSTITUTIONAL = 15.0   # Must be largely undiscovered by institutions
MIN_PROMOTER_HOLDING = 40.0 # Founders must have at least 40% skin in the game
MAX_PROMOTER_PLEDGE = 0.0   # Strictly 0% pledged shares allowed

def fetch_nse_master_list() -> list:
    """Downloads the master list of all equities directly from NSE."""
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/csv"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        
        # 'SYMBOL' is the column name in NSE's CSV
        symbols = df['SYMBOL'].dropna().tolist()
        # Append .NS for Yahoo Finance
        tickers = [f"{sym.strip()}.NS" for sym in symbols if sym.strip()]
        return tickers
    except Exception as e:
        console.print(f"[red]Failed to fetch NSE master list: {e}[/red]")
        return []

def get_market_cap_cr(ticker: str) -> float:
    """Fast check for market cap using yfinance info."""
    try:
        t = yf.Ticker(ticker)
        # Handle different key names yfinance uses
        mcap = t.info.get('marketCap', 0)
        if mcap == 0:
            mcap = t.info.get('enterpriseValue', 0)
        
        return mcap / 10_000_000  # Convert to Crores
    except:
        return 0.0

def hunt_multibaggers():
    console.print(Panel.fit(
        "[bold green]🎯 The Multibagger Hunter[/bold green]\n"
        "[dim]Scanning the entire NSE (2000+ stocks) for undiscovered, inflecting microcaps.[/dim]"
    ))

    # 1. Get entire universe
    with console.status("[bold cyan]Downloading NSE Master Equity List...[/bold cyan]"):
        all_tickers = fetch_nse_master_list()
    
    if not all_tickers:
        console.print("[red]Could not retrieve universe. Exiting.[/red]")
        return

    console.print(f"[green]Successfully loaded {len(all_tickers)} stocks from NSE.[/green]")
    
    # Optional: For testing purposes or to save time, we can limit the run.
    # To run on ALL stocks, remove the slice, but warn the user it takes ~1 hour.
    console.print("[yellow]Note: Scanning 2000+ stocks takes ~60 minutes. Running in background mode...[/yellow]")
    
    fetcher = DataFetcher()
    calc = MetricsCalculator()
    traj = TrajectoryAnalyzer()
    qual = QualitativeChecker()
    
    candidates = []
    
    # We will track progress via Rich. 
    # For a production run, you might want to chunk this.
    for ticker in track(all_tickers, description="Scanning NSE Universe..."):
        try:
            # Step A: Fast Pre-filter (Market Cap)
            mcap = get_market_cap_cr(ticker)
            if mcap == 0 or mcap > MAX_MCAP_CR:
                continue
                
            # Step B: Deep Financial Trajectory
            # Be polite to Yahoo Finance APIs
            time.sleep(0.5) 
            data = fetcher.fetch(ticker)
            if not data:
                continue
                
            metrics = calc.compute(data)
            scored = traj.analyze(data, metrics)
            t_score = scored.get("trajectory_score", 0)
            
            if t_score < MIN_TRAJECTORY_SCORE:
                continue
                
            # Step C: The "Undiscovered" Check (Screener.in scraping)
            time.sleep(1.0) # Be polite to Screener.in
            qual_data = qual.check(ticker)
            
            fii = qual_data.get("sh_fii_holding_pct", 0.0)
            dii = qual_data.get("sh_dii_holding_pct", 0.0)
            fii = fii if not pd.isna(fii) else 0.0
            dii = dii if not pd.isna(dii) else 0.0
            
            total_inst = fii + dii
            
            if total_inst > MAX_INSTITUTIONAL:
                continue
                
            promoter = qual_data.get("sh_promoter_holding_pct", 0.0)
            pledge = qual_data.get("sh_pledge_pct", 0.0)
            
            promoter = promoter if not pd.isna(promoter) else 0.0
            pledge = pledge if not pd.isna(pledge) else 0.0
            
            if promoter < MIN_PROMOTER_HOLDING:
                continue
                
            if pledge > MAX_PROMOTER_PLEDGE:
                continue
                
            # WE FOUND ONE!
            scored.update(qual_data)
            scored["market_cap_cr"] = mcap
            scored["total_institutional"] = total_inst
            
            candidates.append(scored)
            
            # Print dynamically as we find them
            console.print(f"[bold green]🔥 CANDIDATE FOUND: {ticker}[/bold green] | "
                          f"MCap: ₹{mcap:,.0f}Cr | Traj Score: {t_score} | "
                          f"Inst Hold: {total_inst:.1f}%")
            
        except Exception as e:
            # Silently skip errors on weird tickers to keep the loop moving
            pass

    # Save Results
    if candidates:
        df = pd.DataFrame(candidates)
        cols_to_export = [
            "ticker", "name", "market_cap_cr", "trajectory_score", 
            "total_institutional", "sh_promoter_holding_pct", "sh_pledge_pct",
            "roce_avg", "rev_cagr", "trajectory_signals"
        ]
        
        # Flatten signals list for excel
        if "trajectory_signals" in df.columns:
            df["trajectory_signals"] = df["trajectory_signals"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )
            
        existing_cols = [c for c in cols_to_export if c in df.columns]
        df_export = df[existing_cols].sort_values("trajectory_score", ascending=False)
        
        os.makedirs("output", exist_ok=True)
        out_path = "output/multibagger_candidates.xlsx"
        df_export.to_excel(out_path, index=False)
        console.print(f"\n[bold green]✅ Scan Complete! Found {len(candidates)} multibagger setups.[/bold green]")
        console.print(f"📊 Results saved to: {out_path}")
    else:
        console.print("\n[yellow]Scan Complete. No companies matched all strict multibagger criteria today.[/yellow]")

if __name__ == "__main__":
    hunt_multibaggers()
