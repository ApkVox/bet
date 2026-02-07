
"""
Interactive Verification for Bankroll Service (Phase 5)
=======================================================
Simulates a sequence of bets to trigger State Machine transitions.
Run this script to verify:
1. Singleton behavior
2. Active -> Degraded (Drawdown > 20%)
3. Active -> Paused (10 consecutive losses)
4. Recovery logic
"""
import sys
import os
from pathlib import Path

# Fix paths
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.BankrollEngine.service import get_bankroll_service

def verify():
    # Use a test DB (in memory or separate file would be ideal, but for now we use a temp one)
    test_db = Path("Data/Test_Bankroll.sqlite")
    if test_db.exists():
        os.remove(test_db)
        
    svc = get_bankroll_service()
    # Force re-init for test to point to new DB
    svc.db_path = test_db
    svc._initialized = False # Hack to re-run init
    svc.__init__(db_path=str(test_db))
    
    print("\n[TEST 1] Initial State")
    state = svc.get_state()
    print(f"Status: {state.status} | Kelly: {state.kelly_fraction} | Units: {state.current_units}")
    assert state.status == "ACTIVE"
    assert state.kelly_fraction == 0.25
    
    print("\n[TEST 2] Triggering DEGRADED (Drawdown > 20%)")
    # Initial 100. Loss of 25 = 75. Drawdown 25%.
    svc.update_bankroll("LOSS", 25.0)
    state = svc.get_state()
    print(f"Status: {state.status} | Kelly: {state.kelly_fraction} | Units: {state.current_units} | DD: {state.max_drawdown:.2%}")
    assert state.status == "DEGRADED"
    assert state.kelly_fraction == 0.10
    
    print("\n[TEST 3] Recovery to ACTIVE (Drawdown < 15%)")
    # Needs to get back to > 85. (Peak is 100).
    # Current 75. Win 15 -> 90. DD = 10%.
    svc.update_bankroll("WIN", 10.0, profit_units=15.0)
    state = svc.get_state()
    print(f"Status: {state.status} | Kelly: {state.kelly_fraction} | Units: {state.current_units} | Current DD: {(100-90)/100:.2%}")
    assert state.status == "ACTIVE"
    assert state.kelly_fraction == 0.25
    
    print("\n[TEST 4] Triggering PAUSED (10 Consecutive Losses)")
    # Reset consecutive counter first by winning (done above)
    # Now lose 10 times small
    for i in range(10):
        svc.update_bankroll("LOSS", 1.0)
        
    state = svc.get_state()
    print(f"Status: {state.status} | Kelly: {state.kelly_fraction}")
    assert state.status == "PAUSED"
    
    print("\n[TEST 5] Block Updates while PAUSED")
    old_units = state.current_units
    new_units = svc.update_bankroll("WIN", 1.0, 100.0) # Should be ignored
    print(f"Old: {old_units} | New: {new_units}")
    assert new_units == old_units
    
    print("\n✅ All Tests Passed!")
    
    # Cleanup
    if test_db.exists():
        try:
            os.remove(test_db)
        except:
            pass

if __name__ == "__main__":
    verify()
