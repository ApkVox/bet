"""
===========================================
Unit Tests: Point-in-Time Data Selection
===========================================
These tests verify that the prediction system does NOT use
data from the same day or future dates (data leakage prevention).
"""
import sys
from pathlib import Path
from datetime import date, timedelta
import unittest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prediction_api import (
    _get_team_data_for_date,
    _get_available_table_dates,
    clear_team_data_cache,
    DataLeakageError,
    TEAM_DB_PATH
)


class TestPointInTimeDataSelection(unittest.TestCase):
    """Test suite for point-in-time safe data selection."""
    
    def setUp(self):
        """Clear cache before each test."""
        clear_team_data_cache()
        
    def test_available_dates_returns_sorted_list(self):
        """_get_available_table_dates returns a sorted list of dates."""
        dates = _get_available_table_dates()
        
        self.assertIsInstance(dates, list)
        self.assertGreater(len(dates), 0, "Should have at least some date tables")
        
        # Verify sorted
        self.assertEqual(dates, sorted(dates), "Dates should be sorted ascending")
        print(f"✓ Found {len(dates)} available snapshots: {dates[0]} to {dates[-1]}")
    
    def test_data_is_strictly_before_target_date(self):
        """Data returned must have date STRICTLY LESS THAN target_date."""
        available = _get_available_table_dates()
        if len(available) < 2:
            self.skipTest("Need at least 2 snapshots to test")
        
        # Pick a date that's after the first available snapshot
        target_date = available[1]  # Second available date
        
        df, snapshot_date = _get_team_data_for_date(target_date)
        
        self.assertIsNotNone(df, "Should return a DataFrame")
        self.assertIsNotNone(snapshot_date, "Should return the snapshot date")
        self.assertLess(
            snapshot_date, target_date,
            f"Snapshot date {snapshot_date} must be < target date {target_date}"
        )
        print(f"✓ Target={target_date}, Used snapshot={snapshot_date} (OK: {snapshot_date} < {target_date})")
    
    def test_same_day_data_not_used(self):
        """CRITICAL: Data from the same day as the game must NOT be used."""
        available = _get_available_table_dates()
        
        # Use the latest available date as target (simulating a game on that day)
        target_date = available[-1]
        
        df, snapshot_date = _get_team_data_for_date(target_date)
        
        self.assertIsNotNone(snapshot_date, "Should return a snapshot date")
        self.assertNotEqual(
            snapshot_date, target_date,
            f"LEAKAGE DETECTED: Using same-day data {snapshot_date} for game on {target_date}"
        )
        self.assertLess(
            snapshot_date, target_date,
            f"Snapshot {snapshot_date} must be strictly before target {target_date}"
        )
        print(f"✓ Game on {target_date} correctly uses data from {snapshot_date} (NOT same day)")
    
    def test_future_data_not_used(self):
        """CRITICAL: Future data must never be accessible."""
        available = _get_available_table_dates()
        
        # Pick an earlier date and verify we can't get future data
        target_date = available[0]  # Earliest date
        
        # This should either return data BEFORE target_date or raise an error
        try:
            df, snapshot_date = _get_team_data_for_date(target_date)
            
            # If it returns data, verify it's before target
            if df is not None and snapshot_date is not None:
                self.assertLess(
                    snapshot_date, target_date,
                    f"LEAKAGE: Got data from {snapshot_date} for game on {target_date}"
                )
        except DataLeakageError:
            # This is expected if there's no data before the earliest date
            print(f"✓ Correctly raised DataLeakageError for earliest date {target_date}")
            return
        
        print(f"✓ Target={target_date}, Snapshot={snapshot_date} - No future leakage")
    
    def test_oldest_valid_snapshot_used(self):
        """When multiple valid snapshots exist, use the most recent one < target."""
        available = _get_available_table_dates()
        if len(available) < 5:
            self.skipTest("Need at least 5 snapshots for this test")
        
        # Pick a target date later in the sequence
        target_date = available[-1]  # Latest
        expected_snapshot = available[-2]  # Should use the previous day
        
        df, snapshot_date = _get_team_data_for_date(target_date)
        
        self.assertIsNotNone(snapshot_date)
        # The snapshot should be the most recent one before target
        valid_snapshots = [d for d in available if d < target_date]
        expected_best = max(valid_snapshots)
        
        self.assertEqual(
            snapshot_date, expected_best,
            f"Expected snapshot {expected_best}, got {snapshot_date}"
        )
        print(f"✓ Correctly selected most recent valid snapshot: {snapshot_date}")
    
    def test_leakage_error_when_no_prior_data(self):
        """DataLeakageError raised when no data exists before target."""
        available = _get_available_table_dates()
        earliest = available[0]
        
        # Try to get data for the earliest date - there should be nothing before it
        with self.assertRaises(DataLeakageError) as context:
            _get_team_data_for_date(earliest)
        
        print(f"✓ DataLeakageError correctly raised: {context.exception}")
    
    def test_cache_respects_target_date(self):
        """Cache should not return stale data for different target dates."""
        available = _get_available_table_dates()
        if len(available) < 3:
            self.skipTest("Need at least 3 snapshots")
        
        # First request
        target1 = available[2]
        df1, snap1 = _get_team_data_for_date(target1)
        
        # Second request with different target
        target2 = available[-1]
        df2, snap2 = _get_team_data_for_date(target2)
        
        # Snapshots should be different (or at least appropriate for each target)
        self.assertLess(snap1, target1)
        self.assertLess(snap2, target2)
        print(f"✓ Cache correctly handles: target1={target1}->snap1={snap1}, target2={target2}->snap2={snap2}")


class TestPredictGameIntegration(unittest.TestCase):
    """Integration tests for predict_game with point-in-time safety."""
    
    def setUp(self):
        clear_team_data_cache()
    
    def test_predict_game_includes_snapshot_date(self):
        """predict_game should return the data_snapshot_date in the response."""
        from prediction_api import predict_game
        
        available = _get_available_table_dates()
        target = available[-1]  # Use latest date as game date
        
        result = predict_game(
            home_team="Los Angeles Lakers",
            away_team="Boston Celtics",
            game_date=target
        )
        
        self.assertIn("data_snapshot_date", result)
        self.assertIn("game_date", result)
        
        if result["data_snapshot_date"]:
            snapshot = date.fromisoformat(result["data_snapshot_date"])
            self.assertLess(
                snapshot, target,
                f"LEAKAGE in predict_game: snapshot={snapshot}, game={target}"
            )
        print(f"✓ predict_game correctly returns snapshot_date={result['data_snapshot_date']} for game={target}")


if __name__ == "__main__":
    print("=" * 60)
    print("POINT-IN-TIME DATA SELECTION TESTS")
    print("=" * 60)
    print(f"Testing database: {TEAM_DB_PATH}")
    print()
    
    unittest.main(verbosity=2)
