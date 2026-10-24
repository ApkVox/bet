import unittest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from unittest import mock

import generate_daily_job as job
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

    def test_sync_corta_en_dia_sin_marcadores(self):
        # 22 sin marcadores (Oddstrader caído): no debe guardar el 23 o quedaría un hueco
        fake = {'2026-10-21': [{'home_team': 'Boston Celtics', 'away_team': 'New York Knicks',
                                'home_score': 110, 'away_score': 100}],
                '2026-10-22': [{'home_team': 'Miami Heat', 'away_team': 'Detroit Pistons',
                                'home_score': None, 'away_score': None}],
                '2026-10-23': [{'home_team': 'Utah Jazz', 'away_team': 'Phoenix Suns',
                                'home_score': 99, 'away_score': 98}]}
        saved = []
        with mock.patch.object(job.sbrscrape, 'Scoreboard', lambda sport, date: mock.Mock(games=fake.get(date, []))), \
             mock.patch.object(job.history_db, 'get_game_results', lambda: [{'date': '2026-10-20'}]), \
             mock.patch.object(job.history_db, 'save_game_results', lambda rows: saved.extend(rows) or True), \
             mock.patch.object(job.time, 'sleep', lambda s: None):
            self.assertEqual(job.sync_game_results(until='2026-10-23'), 1)
        self.assertEqual([r['date'] for r in saved], ['2026-10-21'])

    def test_califica_con_nba_games_del_mismo_dia(self):
        # Serie de playoffs: el juego 2 (20) no debe calificar el juego 1 (18)
        games = [{'date': '2026-04-18', 'home': 'New York Knicks', 'away': 'Atlanta Hawks', 'home_score': 113, 'away_score': 102},
                 {'date': '2026-04-20', 'home': 'New York Knicks', 'away': 'Atlanta Hawks', 'home_score': 106, 'away_score': 107},
                 {'date': '2026-04-18', 'home': 'LA Clippers', 'away': 'Utah Jazz', 'home_score': 90, 'away_score': 95}]
        self.assertEqual(job.history_db.game_winners(games, {'2026-04-18'}), {'2026-04-18': {
            '2026-04-18_Atlanta_Hawks_New_York_Knicks': 'New York Knicks',
            '2026-04-18_Utah_Jazz_LA_Clippers': 'Utah Jazz'}})


if __name__ == '__main__':
    unittest.main()
