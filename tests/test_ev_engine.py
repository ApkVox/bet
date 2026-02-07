import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.EVEngine.ev_calculator import calculate_ev, EVResult

class TestEVCalculator(unittest.TestCase):
    
    def test_positive_ev(self):
        # 55% prob, 2.00 odds => EV = 0.10 (10%)
        result = calculate_ev(0.55, 2.00)
        self.assertAlmostEqual(result.ev, 0.10)
        self.assertTrue(result.is_value_bet)

    def test_negative_ev(self):
        # 45% prob, 2.00 odds => EV = -0.10 (-10%)
        result = calculate_ev(0.45, 2.00)
        self.assertAlmostEqual(result.ev, -0.10)
        self.assertFalse(result.is_value_bet)

    def test_neutral_ev(self):
        # 50% prob, 2.00 odds => EV = 0.00
        result = calculate_ev(0.50, 2.00)
        self.assertAlmostEqual(result.ev, 0.00)
        self.assertFalse(result.is_value_bet) # STRICT > 0

    def test_high_odds_value(self):
        # 30% prob, 4.00 odds => EV = (0.3 * 4) - 1 = 1.2 - 1 = 0.2
        result = calculate_ev(0.30, 4.00)
        self.assertAlmostEqual(result.ev, 0.20)
        self.assertTrue(result.is_value_bet)

    def test_invalid_probability(self):
        with self.assertRaises(ValueError):
            calculate_ev(1.5, 2.0)
        with self.assertRaises(ValueError):
            calculate_ev(-0.1, 2.0)

    def test_invalid_odds(self):
        with self.assertRaises(ValueError):
            calculate_ev(0.5, 1.0) # Odds must be > 1
        with self.assertRaises(ValueError):
            calculate_ev(0.5, 0.9)

if __name__ == '__main__':
    unittest.main()
