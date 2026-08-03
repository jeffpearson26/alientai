from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from summarize_prospective_programs import build_summary


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class ProspectiveProgramSummaryTests(unittest.TestCase):
    def test_missing_programs_remain_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = build_summary(
                Path(directory),
                datetime(2026, 8, 3, tzinfo=timezone.utc),
            )
        programs = {row["program"]: row for row in summary["programs"]}
        self.assertFalse(programs["ai_semiconductor_intraday"]["exists"])
        self.assertEqual(
            programs["ai_semiconductor_intraday"]["observations"], 0
        )
        self.assertEqual(
            programs["contextual_options_five_session"]["status"], "missing"
        )
        self.assertEqual(
            programs["ai_semiconductor_intraday_gate"]["status"], "missing"
        )
        self.assertFalse(
            programs["pick_competition_intraday_outcomes"]["exists"]
        )

    def test_counts_models_dates_statuses_and_participants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_jsonl(
                root / "nasdaq100_prospective/journal.jsonl",
                [
                    {
                        "model_id": "baseline",
                        "market_session_date": "2026-08-03",
                        "status": "pending",
                        "symbol": "AAA",
                    },
                    {
                        "model_id": "baseline",
                        "market_session_date": "2026-08-03",
                        "status": "pending",
                        "symbol": "BBB",
                    },
                ],
            )
            write_jsonl(
                root / "pick_competition_journal.jsonl",
                [
                    {
                        "participant": "Jeff",
                        "decision_date": "2026-08-03",
                        "pick_count": 2,
                        "picks": ["AAA", "BBB"],
                        "status": "frozen_pending",
                    }
                ],
            )
            write_jsonl(
                root / "pick_competition_intraday_outcomes.jsonl",
                [
                    {
                        "participant": "Jeff",
                        "decision_date": "2026-08-03",
                        "symbol": "AAA",
                        "horizon": "20m",
                        "status": "complete_unmanaged",
                    }
                ],
            )
            (root / "contextual_options_prospective_gate_2026-08-03.json").write_text(
                json.dumps(
                    {
                        "status": "RESEARCH_HOLD",
                        "completed_outcomes": 5,
                        "distinct_market_dates": 1,
                        "metrics": {
                            "signals": 5,
                            "mean_net_return_pct": 1.5,
                            "median_net_return_pct": 1.0,
                            "win_rate_after_cost": 0.6,
                        },
                        "rare_signal_gate": {
                            "failure_reasons": ["minimum sample"]
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "ai_semiconductor_intraday_gate_2026-08-03.json").write_text(
                json.dumps(
                    {
                        "decision_date": "2026-08-03",
                        "status": "FAILED_CLOSED",
                        "provider_status": "failed_closed",
                        "journal_written": False,
                        "outcome_written": False,
                        "reasons": ["realtime entitlement unavailable"],
                    }
                ),
                encoding="utf-8",
            )
            summary = build_summary(
                root,
                datetime(2026, 8, 3, tzinfo=timezone.utc),
            )
        programs = {row["program"]: row for row in summary["programs"]}
        nasdaq = programs["nasdaq100_five_session"]
        self.assertEqual(nasdaq["observations"], 2)
        self.assertEqual(nasdaq["unique_dates"], 1)
        self.assertEqual(nasdaq["model_counts"], {"baseline": 2})
        self.assertEqual(nasdaq["status_counts"], {"pending": 2})
        competition = programs["pick_competition"]
        self.assertEqual(
            competition["participants"]["Jeff"]["latest_picks"],
            ["AAA", "BBB"],
        )
        self.assertEqual(competition["unique_symbols"], 2)
        competition_outcomes = programs[
            "pick_competition_intraday_outcomes"
        ]
        self.assertEqual(competition_outcomes["observations"], 1)
        self.assertEqual(
            competition_outcomes["status_counts"],
            {"complete_unmanaged": 1},
        )
        contextual = programs["contextual_options_five_session"]
        self.assertEqual(contextual["completed_signals"], 5)
        self.assertEqual(contextual["distinct_decision_dates"], 1)
        self.assertEqual(contextual["failure_reasons"], ["minimum sample"])
        intraday_gate = programs["ai_semiconductor_intraday_gate"]
        self.assertEqual(intraday_gate["status"], "FAILED_CLOSED")
        self.assertFalse(intraday_gate["journal_written"])
        self.assertEqual(
            intraday_gate["reasons"],
            ["realtime entitlement unavailable"],
        )


if __name__ == "__main__":
    unittest.main()
