import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from recommendations import select_picks


def pred(mid, winner, home, odds_home, odds_away, **kw):
    return {"match_id": mid, "home_team": home, "away_team": "X", "winner": winner,
            "odds_home": odds_home, "odds_away": odds_away, **kw}


class TestSelectPicks(unittest.TestCase):

    def test_el_mas_probable_sobre_el_umbral(self):
        preds = [
            pred("a", "A", "A", 1.20, 4.80),               # local 79%
            pred("b", "X", "B", 6.05, 1.143),              # visitante 84%
            pred("c", "C", "C", 1.25, 4.16),               # local 77%
            pred("g", "G", "G", 1.35, 3.35),               # local 71%: bajo el 75%
            pred("d", "D", "D", 1.885, 1.935),             # 50%: fuera
            pred("e", "E", "E", None, 2.0),                # sin cuota: fuera
            pred("f", "F", "F", 1.05, 9.0, warning_level="HIGH"),  # aviso alto: fuera
        ]
        picks = select_picks(preds)
        self.assertEqual([p["match_id"] for p in picks], ["b"])
        self.assertAlmostEqual(picks[0]["market_prob"], 84.1, places=1)

    def test_un_solo_pick_o_ninguno(self):
        self.assertEqual(len(select_picks([pred("a", "A", "A", 1.20, 4.80), pred("d", "D", "D", 1.9, 1.9)])), 1)
        self.assertEqual(select_picks([pred("d", "D", "D", 1.9, 1.9)]), [])
        self.assertEqual(select_picks([pred("g", "G", "G", 1.35, 3.35)]), [])


if __name__ == "__main__":
    unittest.main()
