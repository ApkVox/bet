"""
Monte Carlo Stress Test Engine
==============================
Simulates thousands of seasons to evaluate bankroll stability and growth.
Uses:
- EV Engine (Value detection)
- Risk Filter (Validation)
- Stake Engine (Kelly sizing)
- In-memory Bankroll tracking (for speed)
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

from src.EVEngine.ev_calculator import calculate_ev
from src.RiskFilter.filter import RiskFilter, SeasonPhase
from src.StakeEngine.calculator import calculate_stake
from src.StakeEngine import config as stake_config
from src.RiskFilter import config as risk_config

# Configuration
N_SIMULATIONS = 10000
GAMES_PER_SEASON = 1230 # Full NBA regular season
INITIAL_BANKROLL = 100.0
RUIN_THRESHOLD = 10.0 # Considered "broke" if below 10 units

POOL_FILE = Path(__file__).parent / "simulation_pool.csv"
OUTPUT_DIR = Path(__file__).parents[2] / "validation_results" / "monte_carlo"

def run_single_season(args):
    """
    Simulate one season (1230 games).
    Args is a tuple/dict containing: (pool_sample, params)
    Returns: {final_roi, max_drawdown, bankrupt, total_bets}
    """
    pool_sample, params = args
    
    # Default parameters if not provided
    fractional_kelly = params.get('fractional_kelly', 0.25)
    prob_bias = params.get('prob_bias', 0.0) # e.g. -0.05 for 5% overestimation of true prob
    ev_threshold = params.get('min_ev', 0.03) # Default from config
    
    bankroll = INITIAL_BANKROLL
    peak_bankroll = INITIAL_BANKROLL
    max_drawdown = 0.0
    total_bets = 0
    
    # Initialize engines
    risk_filter = RiskFilter(min_ev=ev_threshold)
    
    indices = np.arange(len(pool_sample))
    
    for i, row in enumerate(pool_sample):
        if bankroll < RUIN_THRESHOLD:
            return {
                "final_roi": -1.0, 
                "max_drawdown": 1.0, 
                "bankrupt": True,
                "total_bets": total_bets,
                "final_bankroll": bankroll
            }
            
        progress_pct = i / GAMES_PER_SEASON
        if progress_pct < 0.25: phase = SeasonPhase.EARLY
        elif progress_pct < 0.60: phase = SeasonPhase.MID
        elif progress_pct < 0.75: phase = SeasonPhase.PRE_DEADLINE
        else: phase = SeasonPhase.LATE
        
        # Check Home Bet
        p_model = row["prob_home"]
        odds_home = row["odds_home"]
        
        # Simulate biases:
        # If prob_bias is negative (e.g. -0.05), it means our model OVERESTIMATES.
        # So the "True" probability (which decides the outcome) is lower.
        # Wait, the pool (row['outcome_home']) is fixed based on historical data.
        # The pool row already has 'outcome_home' derived from the actual game.
        # So we can't change the outcome probability because the outcome is binary and fixed in history.
        
        # However, we can simulate that the Model *thinks* P is higher/lower than it is.
        # In this simulation, 'p_model' is what the RiskFilter/StakeEngine sees.
        # The Outcome is fixed.
        # If we want to simulate "Model is Wrong", we adjust p_model passed to engines,
        # but the outcome remains tied to the original data (which implies the original p_model was somewhat accurate).
        
        # Actually, a better way to test "Model Overestimation" is:
        # The engine SEES (P + bias). The outcome occurs as per reality.
        # So if bias=+0.05, we bet thinking P=0.60, but reality (outcome) reflects P=0.55.
        
        p_seen = np.clip(p_model + prob_bias, 0.01, 0.99)
        
        # Calculate EV using SEEN probability
        ev_seen = (p_seen * odds_home) - 1
        
        # Risk Filter acts on SEEN data
        risk_decision = risk_filter.validate(p_seen, ev_seen, phase)
        
        if risk_decision.allowed:
            # Calculate Stake using SEEN data
            stake_res = calculate_stake(
                p_seen, odds_home, bankroll, 
                fractional_kelly=fractional_kelly, 
                aggressiveness=risk_decision.aggressiveness
            )
            
            stake = stake_res.recommended_stake
            
            if stake > 0:
                total_bets += 1
                # Resolve using FIXED outcome from history
                if row["outcome_home"] == 1:
                    profit = stake * (odds_home - 1)
                    bankroll += profit
                else:
                    bankroll -= stake
                
                # Update metrics
                if bankroll > peak_bankroll:
                    peak_bankroll = bankroll
                
                dd = (peak_bankroll - bankroll) / peak_bankroll
                if dd > max_drawdown:
                    max_drawdown = dd
                    
    # End of season
    roi = (bankroll - INITIAL_BANKROLL) / INITIAL_BANKROLL
    
    return {
        "final_roi": roi,
        "max_drawdown": max_drawdown,
        "bankrupt": False,
        "total_bets": total_bets,
        "final_bankroll": bankroll
    }

def main():
    print(f"Loading pool from {POOL_FILE}...")
    pool_df = pd.read_csv(POOL_FILE)
    pool_records = pool_df.to_dict('records')
    
    print(f"Starting {N_SIMULATIONS} simulations (Monte Carlo)...")
    
    # Prepare tasks: random samples of the pool
    tasks = []
    np.random.seed(42) # Reproducibility
    
    for _ in range(N_SIMULATIONS):
        # Sample with replacement
        sample_indices = np.random.randint(0, len(pool_records), size=GAMES_PER_SEASON)
        sample = [pool_records[i] for i in sample_indices]
        tasks.append(sample)
    
    # Run in parallel
    results = []
    # For large N, use ProcessPool. For Debug N=100, linear is fine.
    # Using 80% of CPU
    max_workers = max(1, multiprocessing.cpu_count() - 1)
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(run_single_season, tasks), total=N_SIMULATIONS))
        
    # Analyze
    df_results = pd.DataFrame(results)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_results.to_csv(OUTPUT_DIR / "monte_carlo_results.csv", index=False)
    
    # Aggregate Metrics
    p5_roi = np.percentile(df_results["final_roi"], 5)
    median_roi = np.median(df_results["final_roi"])
    p95_roi = np.percentile(df_results["final_roi"], 95)
    
    mean_drawdown = df_results["max_drawdown"].mean()
    p99_drawdown = np.percentile(df_results["max_drawdown"], 99)
    
    ruin_prob = df_results["bankrupt"].mean()
    
    # Report
    summary = []
    summary.append(f"# Monte Carlo Stress Test Results (N={N_SIMULATIONS})")
    summary.append(f"**Strategy:** Fractional Kelly (0.25) | **Starts:** {INITIAL_BANKROLL}U")
    summary.append("\n## Key Metrics")
    summary.append(f"- **Risk of Ruin:** {ruin_prob:.2%} (Bankroll < {RUIN_THRESHOLD}U)")
    summary.append(f"- **Median ROI:** {median_roi:+.1%} per season")
    summary.append(f"- **95% CI ROI:** [{p5_roi:+.1%}, {p95_roi:+.1%}]")
    summary.append(f"- **Avg Max Drawdown:** {mean_drawdown:.1%}")
    summary.append(f"- **Worst Case Drawdown (99th):** {p99_drawdown:.1%}")
    
    summary_path = OUTPUT_DIR / "simulation_summary.md"
    with open(summary_path, "w") as f:
        f.write("\n".join(summary))
        
    print(f"\nSaved results to {OUTPUT_DIR}")
    
    # Safe print for console
    print("\n# Monte Carlo Stress Test Results")
    print("\n".join(summary[1:]))

if __name__ == "__main__":
    main()
