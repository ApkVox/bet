
"""
Verification for RiskGuard Service (Phase 5)
============================================
Checks if Hard Rules are enforced:
1. PAUSED Status -> BLOCK
2. Early Season -> BLOCK
3. Normal Season -> ALLOW (if valid)
"""
import sys
import os
from datetime import datetime
from pathlib import Path

# Fix paths
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.Services.risk_guard import get_risk_guard
from src.BankrollEngine.service import get_bankroll_service

def verify_risk_guard():
    # Setup test DB
    test_db = Path("Data/Test_RiskGuard.sqlite")
    if test_db.exists():
        os.remove(test_db)
        
    # Init Services
    bs = get_bankroll_service()
    bs.db_path = test_db
    bs._initialized = False
    bs.__init__(db_path=str(test_db))
    
    rg = get_risk_guard()
    
    print("\n[TEST 1] Early Season Block (Oct 15)")
    # Even with high prob/ev, should block
    d1 = datetime(2025, 10, 15)
    decision = rg.validate_bet(0.70, 0.10, d1)
    print(f"Date: {d1.date()} | Allowed: {decision.allowed} | Reason: {decision.reasons}")
    assert decision.allowed == False
    assert "HARD RULE" in decision.reasons[0]
    
    print("\n[TEST 2] Mid Season Allow (Jan 15)")
    d2 = datetime(2026, 1, 15)
    decision = rg.validate_bet(0.70, 0.10, d2)
    print(f"Date: {d2.date()} | Allowed: {decision.allowed}")
    assert decision.allowed == True
    
    print("\n[TEST 3] Circuit Breaker (Paused Bankroll)")
    # Force pause bankroll
    # Lose 10 times
    for _ in range(10):
        bs.update_bankroll("LOSS", 1.0)
        
    print(f"Bankroll Status: {bs.operational_status}")
    assert bs.operational_status == "PAUSED"
    
    # Try mid season bet again
    decision = rg.validate_bet(0.70, 0.10, d2)
    print(f"Date: {d2.date()} | Allowed: {decision.allowed} | Reason: {decision.reasons}")
    assert decision.allowed == False
    assert "CIRCUIT BREAKER" in decision.reasons[0]
    
    print("\n✅ RiskGuard Verification Passed!")
    
    # Cleanup
    if test_db.exists():
        try:
            os.remove(test_db)
        except:
            pass

if __name__ == "__main__":
    verify_risk_guard()
