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

def run_factor_model():
    console.print("[bold cyan]📊 Running Cross-Sectional Factor Model (Z-Scores)[/bold cyan]")
    
    all_tickers = fetch_nse_master_list()
    if not all_tickers: return

    # For testing, you can uncomment this to run fast
    # all_tickers = all_tickers[:100]

    fetcher = DataFetcher()
    calc = MetricsCalculator()
    traj = TrajectoryAnalyzer()
    qual = QualitativeChecker()
    
    raw_data = []
    
    for ticker in track(all_tickers, description="Gathering Unfiltered Market Data..."):
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
                "roce_avg": scored.get("roce_avg", np.nan)
            }
            raw_data.append(row)
        except Exception:
            pass

    df = pd.DataFrame(raw_data)
    if df.empty: return
    
    # 1. Clean Data (Drop missing critical metrics, fill others with median)
    df = df.dropna(subset=['trajectory_score', 'PE_Ratio'])
    df['PEG_Ratio'] = df['PEG_Ratio'].fillna(df['PEG_Ratio'].median())
    df['roce_avg'] = df['roce_avg'].fillna(df['roce_avg'].median())
    
    # 2. Compute Z-Scores (StandardScaler calculates (X - Mean) / StdDev)
    scaler = StandardScaler()
    
    # Positive Factors (Higher is Better)
    df['Z_Trajectory'] = scaler.fit_transform(df[['trajectory_score']])
    df['Z_Promoter']   = scaler.fit_transform(df[['promoter_holding']])
    df['Z_ROCE']       = scaler.fit_transform(df[['roce_avg']])
    
    # Negative Factors (Lower is Better, so we invert them by multiplying by -1)
    df['Z_Valuation']  = scaler.fit_transform(df[['PEG_Ratio']]) * -1
    df['Z_Pledge']     = scaler.fit_transform(df[['pledge']]) * -1
    df['Z_InstHold']   = scaler.fit_transform(df[['total_institutional']]) * -1
    
    # 3. Calculate Final Composite Score
    # We give 3x weight to Trajectory, 3x to Valuation, 1x to everything else
    df['Composite_Factor_Score'] = (
        (df['Z_Trajectory'] * 3) + 
        (df['Z_Valuation'] * 3) + 
        df['Z_Promoter'] + 
        df['Z_ROCE'] + 
        df['Z_Pledge'] + 
        df['Z_InstHold']
    )
    
    # 4. Sort and Export
    df = df.sort_values(by='Composite_Factor_Score', ascending=False)
    
    os.makedirs("output", exist_ok=True)
    df.to_excel("output/factor_model_candidates.xlsx", index=False)
    
    console.print("\n[bold green]✅ Factor Model Complete![/bold green]")
    console.print(f"Scored {len(df)} smallcaps purely on cross-sectional Z-Scores.")
    console.print("Top 5 Stocks by Pure Statistical Factor Ranking:")
    console.print(df[['ticker', 'trajectory_score', 'PEG_Ratio', 'Composite_Factor_Score']].head(5).to_string())

if __name__ == "__main__":
    run_factor_model()
