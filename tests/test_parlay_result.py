import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from history_db import parlay_result

PICKS = [{"match_id": "a", "pick": "X"}, {"match_id": "b", "pick": "Y"}]


class TestParlayResult(unittest.TestCase):
    def test_parlay_result(self):
        self.assertEqual(parlay_result(PICKS, {"a": "X", "b": "Y"}), "win")
        self.assertEqual(parlay_result(PICKS, {"a": "Z"}), "loss")  # una pierna perdida basta
        self.assertIsNone(parlay_result(PICKS, {"a": "X"}))  # falta un marcador
        self.assertIsNone(parlay_result([], {}))


if __name__ == "__main__":
    unittest.main()
