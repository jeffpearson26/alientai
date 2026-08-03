from __future__ import annotations

import unittest

from build_prospective_event_requests import build_requests


class ProspectiveEventRequestTests(unittest.TestCase):
    def test_builds_exact_0925_eastern_requests(self) -> None:
        rows = build_requests(
            ["AMD", "NVDA"],
            "2026-08-03",
            "2026-08-03T13:25:00+00:00",
        )
        self.assertEqual([row["symbol"] for row in rows], ["AMD", "NVDA"])
        self.assertEqual(
            {row["as_of_utc"] for row in rows},
            {"2026-08-03T13:25:00+00:00"},
        )
        self.assertTrue(all(row["research_only"] for row in rows))

    def test_rejects_early_or_late_cutoff(self) -> None:
        for value in (
            "2026-08-03T13:20:00+00:00",
            "2026-08-03T13:30:00+00:00",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "09:25"):
                    build_requests(["AMD"], "2026-08-03", value)

    def test_rejects_naive_timestamp(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            build_requests(["AMD"], "2026-08-03", "2026-08-03T13:25:00")


if __name__ == "__main__":
    unittest.main()
