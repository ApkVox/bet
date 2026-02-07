
"""
Verification for BetPipeline (Phase 5)
======================================
Tests the full integration of the betting decision system.
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# Fix paths
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.Services.bet_pipeline import get_bet_pipeline
from src.BankrollEngine.service import get_bankroll_service

def verify_pipeline():
    # Setup test DBs
    test_db = Path("Data/Test_Pipeline.sqlite")
    if test_db.exists():
        os.remove(test_db)
        
    # Init Services
    bs = get_bankroll_service()
    bs.db_path = test_db
    bs._initialized = False
    bs.__init__(db_path=str(test_db))
    
    pipeline = get_bet_pipeline()
    
    print("\n[TEST 1] Valid Bet (Mid Season, High EV, High Prob)")
    # Date: Jan 15 (Mid Season)
    # Prob: 60%, Odds: 2.0 -> EV = 20%
    d1 = datetime(2026, 1, 15)
    
    res = pipeline.process_bet("GAME_001", 0.60, 2.00, d1)
    print(f"Decision: {res.decision} | Logic: {res.reason}")
    print(f"Stake: {res.stake_units}U | Status: {bs.operational_status}")
    
    assert res.decision == "BET"
    assert res.stake_units > 0
    assert "Approved" in res.reason
    
    print("\n[TEST 2] Low EV (Blocked by EV Engine)")
    # Prob: 51%, Odds: 1.90 -> EV = -3%
    res = pipeline.process_bet("GAME_002", 0.51, 1.90, d1)
    print(f"Decision: {res.decision} | Logic: {res.reason}")
    
    assert res.decision == "PASS" # Not blocked, just passed due to negative value
    assert "Negative Value" in res.reason
    
    print("\n[TEST 3] Risk Guard Block (Early Season)")
    # Date: Oct 20 (banned)
    d2 = datetime(2025, 10, 20)
    res = pipeline.process_bet("GAME_003", 0.60, 2.00, d2)
    print(f"Decision: {res.decision} | Logic: {res.reason}")
    
    assert res.decision == "BLOCKED"
    assert "Early Season" in res.reason
    
    print("\n[TEST 4] Circuit Breaker (Bankroll Paused)")
    # Crash bankroll
    for _ in range(10):
        bs.update_bankroll("LOSS", 1.0)
        
    assert bs.operational_status == "PAUSED"
    
    # Try valid bet again
    res = pipeline.process_bet("GAME_004", 0.60, 2.00, d1)
    print(f"Decision: {res.decision} | Logic: {res.reason}")
    
    assert res.decision == "BLOCKED"
    assert "CIRCUIT BREAKER" in res.reason
    
    print("\n✅ BetPipeline Verified!")
    
    if test_db.exists():
        try:
            os.remove(test_db)
        except:
            pass

if __name__ == "__main__":
    verify_pipeline()
