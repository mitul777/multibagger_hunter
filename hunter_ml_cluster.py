#!/usr/bin/env python3
# =============================================================================
# hunter_ml_cluster.py — Setup 3: Unsupervised ML Clustering (Anomaly Detection)
# =============================================================================
# Feeds the entire smallcap universe into a K-Means clustering algorithm to
# find the mathematical cluster of companies behaving like "Undervalued Growth".
# =============================================================================

import os
import pandas as pd
import numpy as np
from rich.console import Console
from rich.progress import track
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

import requests_cache
requests_cache.install_cache('market_data_cache', expire_after=86400)

from data_fetcher import DataFetcher
from metrics_calculator import MetricsCalculator
from trajectory_analyzer import TrajectoryAnalyzer
from qualitative_checker import QualitativeChecker
from multibagger_hunter import fetch_nse_master_list, get_market_cap_cr

console = Console()

def run_ml_clustering():
    console.print("[bold magenta]🤖 Running Unsupervised ML (K-Means Clustering)[/bold magenta]")
    
    all_tickers = fetch_nse_master_list()
    if not all_tickers: return

    fetcher = DataFetcher()
    calc = MetricsCalculator()
    traj = TrajectoryAnalyzer()
    qual = QualitativeChecker()
    
    raw_data = []
    
    for ticker in track(all_tickers, description="Gathering Unfiltered Market Data..."):
        try:
            mcap = get_market_cap_cr(ticker)
            if mcap == 0 or mcap > 7500:
                continue
                
            data = fetcher.fetch(ticker)
            if not data: continue
                
            metrics = calc.compute(data)
            scored = traj.analyze(data, metrics)
            t_score = scored.get("trajectory_score", 0)
            
            qual_data = qual.check(ticker)
            pe = qual_data.get("sh_screener_pe", np.nan)
            ni_cagr = scored.get("ni_cagr_3y", np.nan)
            peg = (pe / ni_cagr) if (not pd.isna(pe) and not pd.isna(ni_cagr) and ni_cagr > 0) else np.nan
            
            row = {
                "ticker": ticker,
                "trajectory_score": t_score,
                "PEG_Ratio": peg,
                "roce_avg": scored.get("roce_avg", np.nan),
                "promoter_holding": qual_data.get("sh_promoter_holding_pct", 0.0)
            }
            raw_data.append(row)
        except Exception:
            pass

    df = pd.DataFrame(raw_data)
    if df.empty: return
    
    # 1. Clean Data for ML Model
    df = df.dropna(subset=['trajectory_score', 'PEG_Ratio', 'roce_avg'])
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    
    features = ['trajectory_score', 'PEG_Ratio', 'roce_avg', 'promoter_holding']
    X = df[features].copy()
    
    # 2. Scale Features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 3. Run K-Means Clustering (Find 5 distinct profiles of companies)
    console.print("Running KMeans to find the 'Golden Cluster'...")
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df['Cluster'] = kmeans.fit_predict(X_scaled)
    
    # 4. Identify the "Golden Cluster" (Highest Trajectory + Lowest PEG)
    cluster_stats = df.groupby('Cluster')[features].mean()
    
    # We want max Trajectory, max ROCE, max Promoter, min PEG.
    # Let's create a simple score just to identify which cluster is best
    cluster_scores = (
        cluster_stats['trajectory_score'] + 
        cluster_stats['roce_avg'] + 
        (cluster_stats['promoter_holding'] / 2) - 
        (cluster_stats['PEG_Ratio'] * 20)  # Heavily penalize high average PEG
    )
    
    golden_cluster_id = cluster_scores.idxmax()
    
    console.print(f"\n[bold green]Identified Cluster {golden_cluster_id} as the Undervalued Growth Anomaly.[/bold green]")
    console.print(cluster_stats.loc[golden_cluster_id])
    
    # 5. Filter and Export only stocks in the Golden Cluster
    golden_stocks = df[df['Cluster'] == golden_cluster_id].copy()
    
    # Sort them by proximity to cluster center (or just by Trajectory within the cluster)
    golden_stocks = golden_stocks.sort_values(by='trajectory_score', ascending=False)
    
    os.makedirs("output", exist_ok=True)
    golden_stocks.to_excel("output/ml_cluster_candidates.xlsx", index=False)
    
    console.print(f"\n✅ ML Clustering Complete! Found {len(golden_stocks)} stocks belonging to the Golden Cluster.")
    console.print("Top 5 anomalies in this cluster:")
    console.print(golden_stocks[['ticker', 'trajectory_score', 'PEG_Ratio', 'roce_avg']].head(5).to_string())

if __name__ == "__main__":
    run_ml_clustering()
