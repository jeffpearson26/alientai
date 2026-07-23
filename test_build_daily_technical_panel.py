import unittest
from build_daily_technical_panel import snapshot_for_day

class TechnicalPanelTests(unittest.TestCase):
    def test_requires_requested_day_and_sixty_candles(self):
        rows=[{"datetime_utc":f"2026-01-{(i%28)+1:02d}T21:00:00+00:00","close":100+i,"high":101+i,"low":99+i,"volume":1000} for i in range(59)]
        self.assertIsNone(snapshot_for_day("X", rows, "2026-01-03"))

if __name__ == "__main__":
    unittest.main()
