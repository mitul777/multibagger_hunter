#!/usr/bin/env python3
# =============================================================================
# hunter_ml_cluster.py — Setup 3: Unsupervised ML Clustering (Anomaly Detection)
# =============================================================================
# Feeds the entire smallcap universe into a K-Means clustering algorithm to
# find the mathematical cluster of companies behaving like "Undervalued Growth".
# =============================================================================

import os
import glob
import argparse
import pandas as pd
import numpy as np
from rich.console import Console
from rich.progress import track
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

console = Console()

def score_ml():
    console.print("[bold magenta]🤖 Running Unsupervised ML (K-Means Clustering)[/bold magenta]")
    
    csv_files = glob.glob("output/raw_data_*.csv")
    if not csv_files:
        console.print("[red]No raw data CSVs found. Run hunter_factor_model.py --gather first.[/red]")
        return
        
    df_list = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(df_list, ignore_index=True)
    if df.empty: return
    
    # 1. Clean Data for ML Model
    df = df.dropna(subset=['trajectory_score', 'PEG_Ratio', 'roce_avg'])
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # Fill remaining NaNs with median so KMeans doesn't crash
    df = df.fillna(df.median(numeric_only=True))
    
    features = [
        'trajectory_score', 'PEG_Ratio', 'roce_avg', 'promoter_holding',
        'earnings_quality', 'debt_to_equity', 'ev_to_ebitda', 'price_momentum'
    ]
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
    cluster_scores = (
        cluster_stats['trajectory_score'] + 
        cluster_stats['roce_avg'] + 
        (cluster_stats['promoter_holding'] / 2) - 
        (cluster_stats['PEG_Ratio'] * 20)
    )
    
    golden_cluster_id = cluster_scores.idxmax()
    
    console.print(f"\n[bold green]Identified Cluster {golden_cluster_id} as the Undervalued Growth Anomaly.[/bold green]")
    console.print(cluster_stats.loc[golden_cluster_id])
    
    # 5. Filter and Export only stocks in the Golden Cluster
    golden_stocks = df[df['Cluster'] == golden_cluster_id].copy()
    
    golden_stocks = golden_stocks.sort_values(by='trajectory_score', ascending=False)
    
    os.makedirs("output", exist_ok=True)
    golden_stocks.to_excel("output/ml_cluster_candidates.xlsx", index=False)
    
    console.print(f"\n✅ ML Clustering Complete! Found {len(golden_stocks)} stocks belonging to the Golden Cluster.")
    console.print("Top 5 anomalies in this cluster:")
    console.print(golden_stocks[['ticker', 'trajectory_score', 'PEG_Ratio', 'roce_avg']].head(5).to_string())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ML Clustering pipeline")
    parser.add_argument("--score", action="store_true", help="Run ML clustering on pre-gathered CSVs")
    args = parser.parse_args()
    
    score_ml()
