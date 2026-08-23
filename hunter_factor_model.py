#!/usr/bin/env python3
# =============================================================================
# hunter_factor_model.py — Setup 1: Dynamic Cross-Sectional Factor Model
# =============================================================================
# Scans the entire smallcap universe but sets ZERO hard rules.
# Instead, grades every company on a curve (Z-Score) for Trajectory, Valuation,
# and Ownership. Ranks them by their combined percentile strength.
# =============================================================================

import os
import time
import glob
import argparse
import pandas as pd
import numpy as np
from rich.console import Console
from rich.progress import track
from sklearn.preprocessing import StandardScaler

import requests_cache
requests_cache.install_cache('market_data_cache', expire_after=86400)

from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from trajectory_analyzer import TrajectoryAnalyzer
from qualitative_checker import QualitativeChecker
from multibagger_hunter import fetch_nse_master_list, get_market_cap_cr

console = Console()

def gather_data(start_idx: int = 0, end_idx: int = None):
    console.print(f"[bold cyan]📥 Gathering Market Data (Chunk {start_idx} to {end_idx})[/bold cyan]")
    
    all_tickers = fetch_nse_master_list()
    if not all_tickers: return

    if end_idx is None:
        end_idx = len(all_tickers)
        
    chunk_tickers = all_tickers[start_idx:end_idx]

    fetcher = DataFetcher()
    calc = MetricsCalculator()
    traj = TrajectoryAnalyzer()
    qual = QualitativeChecker()
    
    raw_data = []
    
    for ticker in track(chunk_tickers, description="Gathering Unfiltered Market Data..."):
        try:
            mcap = get_market_cap_cr(ticker)
            if mcap == 0 or mcap > 7500: # Only hard rule: Must be a smallcap
                continue
                
            data = fetcher.fetch(ticker)
            if not data: continue
                
            metrics = calc.compute(data)
            scored = traj.analyze(data, metrics)
            t_score = scored.get("trajectory_score", 0)
            
            qual_data = qual.check(ticker)
            
            fii = qual_data.get("sh_fii_holding_pct", 0.0)
            dii = qual_data.get("sh_dii_holding_pct", 0.0)
            total_inst = (fii if not pd.isna(fii) else 0.0) + (dii if not pd.isna(dii) else 0.0)
            promoter = qual_data.get("sh_promoter_holding_pct", 0.0)
            pledge = qual_data.get("sh_pledge_pct", 0.0)
            pe = qual_data.get("sh_screener_pe", np.nan)
            
            ni_cagr = scored.get("ni_cagr_3y", np.nan)
            peg = (pe / ni_cagr) if (not pd.isna(pe) and not pd.isna(ni_cagr) and ni_cagr > 0) else np.nan
            
            row = {
                "ticker": ticker,
                "market_cap_cr": mcap,
                "trajectory_score": t_score,
                "PE_Ratio": pe,
                "PEG_Ratio": peg,
                "total_institutional": total_inst,
                "promoter_holding": promoter if not pd.isna(promoter) else 0.0,
                "pledge": pledge if not pd.isna(pledge) else 0.0,
                "roce_avg": scored.get("roce_avg", np.nan),
                "earnings_quality": metrics.get("earnings_quality", np.nan),
                "debt_to_equity": metrics.get("debt_to_equity", np.nan),
                "ev_to_ebitda": metrics.get("ev_to_ebitda", np.nan),
                "price_momentum": metrics.get("price_momentum", np.nan)
            }
            raw_data.append(row)
        except Exception:
            pass

    df = pd.DataFrame(raw_data)
    if not df.empty:
        os.makedirs("output", exist_ok=True)
        csv_path = f"output/raw_data_{start_idx}_{end_idx}.csv"
        df.to_csv(csv_path, index=False)
        console.print(f"✅ Chunk complete! Saved {len(df)} smallcaps to {csv_path}")

def score_factors():
    console.print("[bold cyan]📊 Running Cross-Sectional Factor Model (Z-Scores)[/bold cyan]")
    
    # 1. Merge all chunked data
    csv_files = glob.glob("output/raw_data_*.csv")
    if not csv_files:
        console.print("[red]No raw data CSVs found in output/. Run --gather first.[/red]")
        return
        
    df_list = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(df_list, ignore_index=True)
    
    if df.empty: return
    
    # 2. Clean Data (Drop missing critical metrics, fill others with median)
    df = df.dropna(subset=['trajectory_score', 'PE_Ratio'])
    df['PEG_Ratio'] = df['PEG_Ratio'].fillna(df['PEG_Ratio'].median())
    df['roce_avg'] = df['roce_avg'].fillna(df['roce_avg'].median())
    df['earnings_quality'] = df['earnings_quality'].fillna(df['earnings_quality'].median())
    df['debt_to_equity'] = df['debt_to_equity'].fillna(df['debt_to_equity'].median())
    df['ev_to_ebitda'] = df['ev_to_ebitda'].fillna(df['ev_to_ebitda'].median())
    df['price_momentum'] = df['price_momentum'].fillna(df['price_momentum'].median())
    
    # Replace any extreme inf values generated during math
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['trajectory_score'])
    df = df.fillna(df.median(numeric_only=True))
    
    # 3. Compute Z-Scores (StandardScaler calculates (X - Mean) / StdDev)
    scaler = StandardScaler()
    
    # Positive Factors (Higher is Better)
    df['Z_Trajectory'] = scaler.fit_transform(df[['trajectory_score']])
    df['Z_Promoter']   = scaler.fit_transform(df[['promoter_holding']])
    df['Z_ROCE']       = scaler.fit_transform(df[['roce_avg']])
    df['Z_EarnQual']   = scaler.fit_transform(df[['earnings_quality']])
    df['Z_Momentum']   = scaler.fit_transform(df[['price_momentum']])
    
    # Negative Factors (Lower is Better, so we invert them by multiplying by -1)
    df['Z_Valuation']  = scaler.fit_transform(df[['PEG_Ratio']]) * -1
    df['Z_EV_EBITDA']  = scaler.fit_transform(df[['ev_to_ebitda']]) * -1
    df['Z_Pledge']     = scaler.fit_transform(df[['pledge']]) * -1
    df['Z_InstHold']   = scaler.fit_transform(df[['total_institutional']]) * -1
    df['Z_Debt']       = scaler.fit_transform(df[['debt_to_equity']]) * -1
    
    # 4. Calculate Final Composite Score
    # We give 3x weight to Trajectory, 3x to Valuation, and weigh everything else
    df['Composite_Factor_Score'] = (
        (df['Z_Trajectory'] * 3) + 
        (df['Z_Valuation'] * 2) + 
        (df['Z_EV_EBITDA'] * 1) + 
        (df['Z_EarnQual'] * 2) + 
        (df['Z_Momentum'] * 2) + 
        (df['Z_Debt'] * 1) + 
        df['Z_Promoter'] + 
        df['Z_ROCE'] + 
        df['Z_Pledge'] + 
        df['Z_InstHold']
    )
    
    # 5. Sort and Export
    df = df.sort_values(by='Composite_Factor_Score', ascending=False)
    
    out_path = "output/factor_model_candidates.xlsx"
    df.to_excel(out_path, index=False)
    
    console.print("\n[bold green]✅ Factor Model Complete![/bold green]")
    console.print(f"Scored {len(df)} smallcaps purely on cross-sectional Z-Scores.")
    console.print("Top 5 Stocks by Pure Statistical Factor Ranking:")
    console.print(df[['ticker', 'trajectory_score', 'PEG_Ratio', 'Composite_Factor_Score']].head(5).to_string())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-Sectional Factor Model pipeline")
    parser.add_argument("--gather", action="store_true", help="Fetch market data for a chunk of tickers")
    parser.add_argument("--score", action="store_true", help="Combine raw chunks and run factor scoring")
    parser.add_argument("--start", type=int, default=0, help="Start index for gathering")
    parser.add_argument("--end", type=int, default=None, help="End index for gathering")
    args = parser.parse_args()

    if args.gather:
        gather_data(args.start, args.end)
    elif args.score:
        score_factors()
    else:
        # Default behavior: run everything (for backward compatibility)
        gather_data()
        score_factors()
