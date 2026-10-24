import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from generate_daily_job import results_from_games


class TestResultsFromGames(unittest.TestCase):

    def test_status_oddstrader_y_nombres_cortos(self):
        games = [
            # Estado de Oddstrader (no "Final"): debe guardarse
            {'home_team': 'Boston Celtics', 'away_team': 'New York Knicks', 'status': 'complete',
             'home_score': 110, 'away_score': 104, 'home_ml': {'fanduel': -150}, 'away_ml': {'fanduel': 130}},
            {'home_team': 'Los Angeles Clippers', 'away_team': 'Los Angeles Lakers', 'status': 'Final',
             'home_score': 99, 'away_score': 101},
            # Sin marcador (aplazado) y nombre corto duplicado: fuera
            {'home_team': 'Miami Heat', 'away_team': 'Detroit Pistons', 'status': 'scheduled',
             'home_score': 0, 'away_score': 0},
            {'home_team': 'Utah', 'away_team': 'L.A. Lakers', 'status': 'complete',
             'home_score': 100, 'away_score': 90},
        ]
        rows = results_from_games('2026-10-22', games)
        self.assertEqual([(r['home'], r['away']) for r in rows],
                         [('Boston Celtics', 'New York Knicks'), ('LA Clippers', 'Los Angeles Lakers')])
        self.assertEqual(rows[0]['home_score'], 110)

    def test_pretemporada(self):
        games = [{'home_team': 'Boston Celtics', 'away_team': 'New York Knicks',
                  'home_score': 110, 'away_score': 104}]
        self.assertEqual(results_from_games('2026-10-10', games), [])


if __name__ == '__main__':
    unittest.main()
