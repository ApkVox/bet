import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.RiskFilter.filter import RiskFilter, SeasonPhase, RiskDecision

class TestRiskFilter(unittest.TestCase):
    
    def setUp(self):
        self.filter = RiskFilter(
            min_probability=0.55,
            min_ev=0.03,
            block_early_season=True,
            reduce_pre_deadline=True
        )

    def test_allowed_bet(self):
        # 60% prob, 5% EV, mid season -> ALLOWED
        result = self.filter.validate(0.60, 0.05, SeasonPhase.MID)
        self.assertTrue(result.allowed)
        self.assertEqual(result.aggressiveness, 1.0)

    def test_blocked_dead_zone(self):
        # 52% prob (dead zone) -> BLOCKED
        result = self.filter.validate(0.52, 0.10)
        self.assertFalse(result.allowed)
        self.assertIn("dead zone", result.reasons[0].lower())

    def test_blocked_low_probability(self):
        # 40% prob -> BLOCKED
        result = self.filter.validate(0.40, 0.10)
        self.assertFalse(result.allowed)
        self.assertTrue(any("probability" in r.lower() for r in result.reasons))

    def test_blocked_low_ev(self):
        # 60% prob, 1% EV -> BLOCKED
        result = self.filter.validate(0.60, 0.01)
        self.assertFalse(result.allowed)
        self.assertTrue(any("ev" in r.lower() for r in result.reasons))

    def test_blocked_negative_ev(self):
        # 60% prob, -5% EV -> BLOCKED
        result = self.filter.validate(0.60, -0.05)
        self.assertFalse(result.allowed)
        self.assertTrue(any("negative" in r.lower() for r in result.reasons))

    def test_blocked_early_season(self):
        # 60% prob, 5% EV, early season -> BLOCKED
        result = self.filter.validate(0.60, 0.05, SeasonPhase.EARLY)
        self.assertFalse(result.allowed)
        self.assertTrue(any("early season" in r.lower() for r in result.reasons))

    def test_reduced_pre_deadline(self):
        # 60% prob, 5% EV, pre deadline -> ALLOWED but reduced
        result = self.filter.validate(0.60, 0.05, SeasonPhase.PRE_DEADLINE)
        self.assertTrue(result.allowed)
        self.assertEqual(result.aggressiveness, 0.5)
        self.assertTrue(any("pre-trade" in r.lower() for r in result.reasons))

    def test_late_season_full_aggression(self):
        # 60% prob, 5% EV, late season -> ALLOWED full aggression
        result = self.filter.validate(0.60, 0.05, SeasonPhase.LATE)
        self.assertTrue(result.allowed)
        self.assertEqual(result.aggressiveness, 1.0)

if __name__ == '__main__':
    unittest.main()
