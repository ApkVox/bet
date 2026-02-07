import unittest
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.BankrollEngine.manager import BankrollManager
from src.BankrollEngine.models import BankrollState

# Temporary DB for testing
TEST_DB = "test_bankroll.sqlite"

class TestBankrollManager(unittest.TestCase):
    def setUp(self):
        import uuid
        self.test_db = f"test_bankroll_{uuid.uuid4().hex}.sqlite"
        self.manager = BankrollManager(db_path=self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                print(f"Warning: Could not remove {self.test_db}")
                pass

    def test_initialization(self):
        state = self.manager.get_state()
        self.assertEqual(state.current_units, 100.0)
        self.assertEqual(state.initial_units, 100.0)
        self.assertEqual(state.max_drawdown, 0.0)

    def test_update_win(self):
        self.manager.update_bankroll(result="WIN", stake_units=1.0, profit_units=1.0, note="Test Win")
        state = self.manager.get_state()
        self.assertEqual(state.current_units, 101.0)
        self.assertEqual(state.peak_units, 101.0)

    def test_update_loss(self):
        self.manager.update_bankroll(result="LOSS", stake_units=1.0, note="Test Loss")
        state = self.manager.get_state()
        self.assertEqual(state.current_units, 99.0)
        self.assertEqual(state.peak_units, 100.0)
        # Drawdown (100 - 99) / 100 = 1%
        self.assertAlmostEqual(state.max_drawdown, 0.01, places=4)

    def test_reset(self):
        self.manager.update_bankroll(result="LOSS", stake_units=10.0)
        self.assertEqual(self.manager.get_state().current_units, 90.0)
        
        self.manager.reset(initial_units=500.0)
        state = self.manager.get_state()
        self.assertEqual(state.current_units, 500.0)
        self.assertEqual(state.initial_units, 500.0)
        self.assertEqual(state.max_drawdown, 0.0)

if __name__ == '__main__':
    unittest.main()

