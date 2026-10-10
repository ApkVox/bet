"""
===========================================
Unit Tests: Point-in-Time (sin fuga de información)
===========================================
Las features de un partido (Elo, forma, descanso) solo pueden depender de
partidos ANTERIORES. Un partido nunca puede "verse" a sí mismo.
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.Utils import elo  # noqa: E402


def games(rows):
    return pd.DataFrame(rows, columns=["date", "home", "away", "margin"])


class TestPointInTime(unittest.TestCase):
    def test_first_game_has_neutral_features(self):
        feats, _ = elo.replay(games([("2025-10-21", "A", "B", 10)]))
        row = feats.iloc[0]
        self.assertEqual(row.elo_diff, elo.HOME_ADV)  # ambos 1500, solo ventaja de local
        self.assertEqual((row.form_home, row.form_away), (0.0, 0.0))
        self.assertEqual((row.rest_home, row.rest_away), (elo.MAX_REST, elo.MAX_REST))

    def test_result_does_not_leak_into_its_own_features(self):
        win, _ = elo.replay(games([("2025-10-21", "A", "B", 30)]))
        loss, _ = elo.replay(games([("2025-10-21", "A", "B", -30)]))
        pd.testing.assert_frame_equal(win, loss)

    def test_previous_game_moves_features(self):
        feats, state = elo.replay(games([
            ("2025-10-21", "A", "B", 20),
            ("2025-10-23", "B", "A", -5),  # A gana otra vez, de visitante
        ]))
        second = feats.iloc[1]
        self.assertLess(second.elo_diff, elo.HOME_ADV)  # B (local) perdió el primero
        self.assertEqual((second.form_home, second.form_away), (-20.0, 20.0))
        self.assertEqual((second.rest_home, second.rest_away), (2.0, 2.0))
        self.assertGreater(state.elo["A"], state.elo["B"])

    def test_new_season_regresses_elo_to_mean(self):
        _, state = elo.replay(games([("2025-10-21", "A", "B", 40)]))
        before = state.elo["A"] - state.elo["B"]
        f = state.features("A", "B", "2026-10-20")
        self.assertAlmostEqual(f["elo_diff"] - elo.HOME_ADV, before * elo.CARRY)
        self.assertEqual(f["rest_home"], elo.MAX_REST)

    def test_aliases_and_market_blend(self):
        self.assertEqual(elo.normalize("Los Angeles Clippers"), "LA Clippers")
        self.assertAlmostEqual(float(elo.market_home_prob(-110, -110)), 0.5)
        self.assertTrue(pd.isna(float(elo.market_home_prob(50, -110))))  # cuota inválida
        self.assertAlmostEqual(float(elo.blend(0.7, float("nan"), 0.1)), 0.7)  # sin cuota -> modelo
        self.assertAlmostEqual(float(elo.blend(0.7, 0.6, 0.0)), 0.6)


if __name__ == "__main__":
    unittest.main()
