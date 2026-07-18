import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("START_OVERNIGHT_TRAINING_QUEUE.ps1").read_text(encoding="utf-8")


class OvernightTrainingQueueTests(unittest.TestCase):
    def test_waits_for_current_transformer(self):
        self.assertIn("CurrentTransformerReport", SCRIPT)
        self.assertIn("Start-Sleep -Seconds 60", SCRIPT)
        self.assertIn("maximumWaitHours = 8", SCRIPT)

    def test_detects_current_transformer_failure(self):
        self.assertIn("Test-CurrentTransformerFailure", SCRIPT)
        self.assertIn("Traceback", SCRIPT)
        self.assertIn("Queue stopped before starting another job", SCRIPT)

    def test_jobs_are_sequential(self):
        self.assertIn("foreach ($job in $jobs)", SCRIPT)
        self.assertNotIn("Start-Job", SCRIPT)
        self.assertNotIn("ForEach-Object -Parallel", SCRIPT)

    def test_outputs_are_isolated(self):
        expected = (
            "lightgbm_5day_sp500_target_2pct_training",
            "lightgbm_5day_sp500_target_3pct_training",
            "lightgbm_5day_russell2000_target_2pct_training",
        )
        for directory in expected:
            self.assertIn(directory, SCRIPT)

    def test_russell_uses_more_conservative_cost(self):
        russell = SCRIPT.split('Name = "Russell 2000', 1)[1]
        self.assertIn('"--round-trip-cost-pct", "0.35"', russell)

    def test_fail_closed_checks_exit_and_report(self):
        self.assertIn("if ($exitCode -ne 0)", SCRIPT)
        self.assertIn("without creating its expected report", SCRIPT)
        self.assertIn('status = "failed_closed"', SCRIPT)

    def test_native_stderr_is_captured_without_truncating_traceback(self):
        self.assertIn('$ErrorActionPreference = "Continue"', SCRIPT)
        self.assertIn("$previousErrorActionPreference", SCRIPT)
        self.assertIn("$exitCode = $LASTEXITCODE", SCRIPT)

    def test_jobs_request_resilient_symbol_fetches(self):
        self.assertIn('"--fetch-attempts", "4"', SCRIPT)
        self.assertIn('"--fetch-retry-delay", "2.0"', SCRIPT)


if __name__ == "__main__":
    unittest.main()
