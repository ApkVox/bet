import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.StakeEngine.calculator import calculate_stake, calculate_kelly, StakeResult

class TestKellyCalculator(unittest.TestCase):
    
    def test_raw_kelly_positive_edge(self):
        # 60% prob, 2.0 odds => f* = (0.6*2 - 1) / (2 - 1) = 0.2 / 1 = 0.2
        kelly = calculate_kelly(0.60, 2.0)
        self.assertAlmostEqual(kelly, 0.20, places=4)

    def test_raw_kelly_no_edge(self):
        # 50% prob, 2.0 odds => f* = (0.5*2 - 1) / (2 - 1) = 0 / 1 = 0
        kelly = calculate_kelly(0.50, 2.0)
        self.assertAlmostEqual(kelly, 0.0, places=4)

    def test_raw_kelly_negative_edge(self):
        # 40% prob, 2.0 odds => f* = (0.4*2 - 1) / (2 - 1) = -0.2
        kelly = calculate_kelly(0.40, 2.0)
        self.assertAlmostEqual(kelly, -0.20, places=4)

    def test_stake_with_fractional_kelly(self):
        # 60% prob, 2.0 odds, 100 bankroll, 0.25 fractional
        # kelly = 0.20, fractional = 0.05, stake = 100 * 0.05 = 5.0
        result = calculate_stake(0.60, 2.0, bankroll=100.0, fractional_kelly=0.25)
        self.assertEqual(result.recommended_stake, 5.0)
        self.assertAlmostEqual(result.stake_percent, 0.05, places=4)
        self.assertFalse(result.was_capped)

    def test_stake_capped(self):
        # 80% prob, 2.0 odds, 100 bankroll
        # kelly = (0.8*2 - 1) / 1 = 0.6
        # fractional = 0.6 * 0.25 = 0.15 (15%)
        # But max is 5%, so capped
        result = calculate_stake(0.80, 2.0, bankroll=100.0, fractional_kelly=0.25, max_stake_percent=0.05)
        self.assertEqual(result.recommended_stake, 5.0)  # Capped at 5%
        self.assertTrue(result.was_capped)

    def test_stake_negative_kelly_zeroed(self):
        # 40% prob, 2.0 odds => negative Kelly => stake = 0
        result = calculate_stake(0.40, 2.0, bankroll=100.0)
        self.assertEqual(result.recommended_stake, 0.0)
        self.assertTrue(result.was_zeroed)

    def test_aggressiveness_modifier(self):
        # 60% prob, 2.0 odds, 100 bankroll, aggressiveness = 0.5
        # Base stake = 5.0, adjusted = 2.5
        result = calculate_stake(0.60, 2.0, bankroll=100.0, fractional_kelly=0.25, aggressiveness=0.5)
        self.assertEqual(result.recommended_stake, 2.5)

    def test_drawdown_scenario(self):
        # Simulate bankroll after losses
        # 60% prob, 2.0 odds, 50 bankroll (after 50% drawdown)
        result = calculate_stake(0.60, 2.0, bankroll=50.0, fractional_kelly=0.25)
        self.assertEqual(result.recommended_stake, 2.5)  # Stakes scale with bankroll

if __name__ == '__main__':
    unittest.main()
