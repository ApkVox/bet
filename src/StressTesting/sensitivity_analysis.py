
"""
Sensitivity Analysis Engine
===========================
Runs Monte Carlo simulations across multiple parameter sets to stress test the strategy
under adverse conditions (model bias, different Kelly fractions, EV thresholds).
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

# Project path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import refactored runner
from src.StressTesting.monte_carlo import run_single_season, GAMES_PER_SEASON

POOL_FILE = Path(__file__).parent / "simulation_pool.csv"
OUTPUT_DIR = Path(__file__).parents[2] / "validation_results" / "sensitivity"

def run_scenario(scenario_name, params, n_sims=500):
    """Run a batch of simulations for a specific scenario."""
    print(f"\n[SCENARIO] {scenario_name}")
    print(f"Params: {params}")
    
    # Load data
    pool_df = pd.read_csv(POOL_FILE)
    pool_records = pool_df.to_dict('records')
    
    # Prepare tasks
    tasks = []
    np.random.seed(42) 
    
    for _ in range(n_sims):
        sample_indices = np.random.randint(0, len(pool_records), size=GAMES_PER_SEASON)
        sample = [pool_records[i] for i in sample_indices]
        tasks.append((sample, params))
        
    # Run
    max_workers = max(1, multiprocessing.cpu_count() - 1)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(run_single_season, tasks), total=n_sims, desc=scenario_name, leave=False))
        
    df = pd.DataFrame(results)
    
    return {
        "scenario": scenario_name,
        "ruin_prob": df['bankrupt'].mean(),
        "median_roi": df['final_roi'].median(),
        "avg_drawdown": df['max_drawdown'].mean(),
        "worst_drawdown": df['max_drawdown'].max(),
        "p99_drawdown": np.percentile(df['max_drawdown'], 99),
        "avg_bets": df['total_bets'].mean()
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    scenarios = [
        # 1. Kelly Sensitivity
        ("Kelly 0.10 (Conservative)", {"fractional_kelly": 0.10}),
        ("Kelly 0.25 (Standard)",     {"fractional_kelly": 0.25}),
        ("Kelly 0.50 (Aggressive)",   {"fractional_kelly": 0.50}),
        
        # 2. Model Calibration Bias (Stress Test)
        ("Bias -5% (Overestimation)", {"prob_bias": -0.05, "fractional_kelly": 0.25}),
        ("Bias +5% (Underestimation)",{"prob_bias": 0.05, "fractional_kelly": 0.25}),
        ("Bias -10% (Severe Error)",  {"prob_bias": -0.10, "fractional_kelly": 0.25}),
        
        # 3. EV Threshold Sensitivity
        ("High Selectivity (EV>5%)",  {"min_ev": 0.05, "fractional_kelly": 0.25}),
        ("Low Selectivity (EV>1%)",   {"min_ev": 0.01, "fractional_kelly": 0.25}),
    ]
    
    summary = []
    for name, params in scenarios:
        metrics = run_scenario(name, params, n_sims=500) # 500 sims per scenario for speed
        summary.append(metrics)
        
    # Generate Report
    report_df = pd.DataFrame(summary)
    report_path = OUTPUT_DIR / "sensitivity_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 🌪️ Sensitivity Analysis Report\n\n")
        f.write("| Scenario | Ruin % | Median ROI | Avg DD | 99% DD | Avg Bets |\n")
        f.write("|----------|--------|------------|--------|--------|----------|\n")
        for _, row in report_df.iterrows():
            f.write(f"| {row['scenario']} | {row['ruin_prob']:.1%} | {row['median_roi']:+.1%} | {row['avg_drawdown']:.1%} | {row['p99_drawdown']:.1%} | {int(row['avg_bets'])} |\n")
            
    print(f"\nReport saved to {report_path}")
    print(report_df.to_string())

if __name__ == "__main__":
    main()
