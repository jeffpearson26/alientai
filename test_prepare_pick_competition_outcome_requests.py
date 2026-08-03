from __future__ import annotations

import unittest

from prepare_pick_competition_outcome_requests import frozen_symbols


def submission(participant: str, picks: list[str]) -> dict:
    return {
        "round_id": "r1",
        "participant": participant,
        "decision_date": "2026-08-03",
        "picks": picks,
        "pick_count": len(picks),
        "status": "frozen_pending",
        "research_only": True,
        "execution_decision": "AVOID",
    }


class PickCompetitionOutcomeRequestTests(unittest.TestCase):
    def test_derives_sorted_unique_union(self) -> None:
        result = frozen_symbols(
            [
                submission("Jeff", ["MU", "AMD"]),
                submission("Claude", ["AMD", "AMGN"]),
            ],
            "2026-08-03",
        )
        self.assertEqual(result, ["AMD", "AMGN", "MU"])

    def test_rejects_non_frozen_submission(self) -> None:
        row = submission("Jeff", ["MU"])
        row["status"] = "complete"
        with self.assertRaisesRegex(ValueError, "not frozen pending"):
            frozen_symbols([row], "2026-08-03")

    def test_rejects_inconsistent_pick_count(self) -> None:
        row = submission("Jeff", ["MU"])
        row["pick_count"] = 2
        with self.assertRaisesRegex(ValueError, "pick count"):
            frozen_symbols([row], "2026-08-03")

    def test_rejects_missing_decision_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "no competition"):
            frozen_symbols(
                [submission("Jeff", ["MU"])],
                "2026-08-04",
            )


if __name__ == "__main__":
    unittest.main()
