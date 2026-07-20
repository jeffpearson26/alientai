from __future__ import annotations

import csv
import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from import_kaggle_analyst_ratings import (
    import_history,
    normalize_kaggle_row,
    parse_rating_headline,
    safe_timestamp,
)


class KaggleAnalystRatingsImporterTests(unittest.TestCase):
    def test_maintain_and_price_target_are_parsed(self):
        parsed = parse_rating_headline(
            "B of A Securities Maintains Neutral on Agilent Technologies, "
            "Raises Price Target to $88"
        )
        self.assertEqual(parsed["analyst_firm"], "B of A Securities")
        self.assertEqual(parsed["action"].casefold(), "maintains")
        self.assertEqual(parsed["new_rating"], "Neutral")
        self.assertEqual(parsed["new_price_target"], 88.0)
        self.assertEqual(parsed["parse_quality"], "action_and_new_rating")

    def test_downgrade_does_not_invent_prior_rating(self):
        parsed = parse_rating_headline(
            "Needham Downgrades Agilent Technologies to Hold, Announces $85 Price Target"
        )
        self.assertEqual(parsed["old_rating"], "")
        self.assertEqual(parsed["new_rating"], "Hold")
        self.assertEqual(parsed["new_price_target"], 85.0)

    def test_explicit_transition_preserves_both_labels(self):
        parsed = parse_rating_headline(
            "Example Research Upgrades Example Corp from Market Perform to Outperform"
        )
        self.assertEqual(parsed["old_rating"], "Market Perform")
        self.assertEqual(parsed["new_rating"], "Outperform")
        self.assertEqual(parsed["parse_quality"], "explicit_old_to_new")

    def test_pt_of_suffix_is_removed_from_rating(self):
        parsed = parse_rating_headline(
            "Goldman Sachs Upgrades Agilent Technologies From Neutral To Buy, "
            "Announces PT of $49"
        )
        self.assertEqual(parsed["old_rating"], "Neutral")
        self.assertEqual(parsed["new_rating"], "Buy")
        self.assertEqual(parsed["new_price_target"], 49.0)

    def test_price_target_only_change_is_not_a_rating_transition(self):
        self.assertIsNone(
            parse_rating_headline(
                "J.P. Morgan Upgrades Agilent Technologies From $40 To $46"
            )
        )

    def test_credit_rating_and_outlook_change_is_rejected(self):
        self.assertIsNone(
            parse_rating_headline("S&P Upgrades Asbury Auto from BB to BB+; Outlook Stable")
        )
        self.assertIsNone(
            parse_rating_headline("Moody's Downgrades Example Corp to Baa3")
        )

    def test_generic_roundup_is_rejected(self):
        self.assertIsNone(parse_rating_headline("Benzinga's Top Upgrades, Downgrades For Today"))
        self.assertIsNone(parse_rating_headline("10 Biggest Price Target Changes For Friday"))

    def test_date_only_timestamp_is_delayed_past_next_day(self):
        timestamp, policy = safe_timestamp("2020-05-22")
        self.assertEqual(timestamp, "2020-05-23T23:59:59Z")
        self.assertEqual(policy, "date_only_next_calendar_day_end")

    def test_offset_timestamp_is_converted_to_utc(self):
        timestamp, policy = safe_timestamp("2020-05-22 11:38:00-04:00")
        self.assertEqual(timestamp, "2020-05-22T15:38:00Z")
        self.assertEqual(policy, "source_offset_timestamp")

    def test_naive_timestamp_fails_closed(self):
        with self.assertRaises(ValueError):
            safe_timestamp("2020-05-22 11:38:00")

    def test_normalized_row_is_provenance_tagged(self):
        row = normalize_kaggle_row(
            {
                "": "4",
                "title": "B of A Securities Maintains Neutral on Agilent Technologies, "
                "Raises Price Target to $88",
                "date": "2020-05-22 11:38:00-04:00",
                "stock": "A",
            }
        )
        self.assertEqual(row["provider"], "KAGGLE_BENZINGA_HEADLINE")
        self.assertTrue(row["raw_payload"]["unofficial_derived_source"])
        self.assertFalse(row["raw_payload"]["prior_rating_inferred"])
        self.assertEqual(row["announcement_timestamp_utc"], "2020-05-22T15:38:00Z")

    def test_streaming_import_is_compressed_deduplicated_and_filterable(self):
        rows = [
            {
                "": "1",
                "title": "Firm One Upgrades Example Corp from Hold to Buy",
                "date": "2020-05-22 08:00:00-04:00",
                "stock": "XYZ",
            },
            {
                "": "1",
                "title": "Firm One Upgrades Example Corp from Hold to Buy",
                "date": "2020-05-22 08:00:00-04:00",
                "stock": "XYZ",
            },
            {
                "": "2",
                "title": "Firm Two Maintains Neutral on Example Corp",
                "date": "2020-05-23 08:00:00-04:00",
                "stock": "XYZ",
            },
            {
                "": "3",
                "title": "Stocks That Hit 52-Week Highs On Friday",
                "date": "2020-05-23 08:00:00-04:00",
                "stock": "XYZ",
            },
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "analyst_ratings_processed.csv"
            output = Path(directory) / "events.jsonl.gz"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["", "title", "date", "stock"])
                writer.writeheader()
                writer.writerows(rows)
            manifest = import_history(
                source,
                output,
                require_explicit_old_rating=True,
            )
            with gzip.open(output, "rt", encoding="utf-8") as handle:
                documents = [json.loads(line) for line in handle]
        self.assertEqual(len(documents), 1)
        self.assertEqual(manifest["counts"]["accepted"], 1)
        self.assertEqual(manifest["counts"]["rejected_semantic_duplicate"], 1)
        self.assertEqual(manifest["counts"]["rejected_missing_explicit_old_rating"], 1)
        self.assertEqual(manifest["counts"]["rejected_not_single_rating_event"], 1)

    def test_semantic_duplicate_keeps_earliest_time_and_merges_target(self):
        rows = [
            {
                "": "late",
                "title": "Firm One Maintains Buy on Example Corp, Raises Price Target to $50",
                "date": "2020-05-22 10:00:00-04:00",
                "stock": "XYZ",
            },
            {
                "": "early",
                "title": "Firm One Maintains Buy on Example Corp",
                "date": "2020-05-22 08:00:00-04:00",
                "stock": "XYZ",
            },
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "analyst_ratings_processed.csv"
            output = Path(directory) / "events.jsonl.gz"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["", "title", "date", "stock"])
                writer.writeheader()
                writer.writerows(rows)
            manifest = import_history(source, output)
            with gzip.open(output, "rt", encoding="utf-8") as handle:
                row = json.loads(handle.readline())["normalized"]
        self.assertEqual(manifest["counts"]["accepted"], 1)
        self.assertEqual(row["announcement_timestamp_utc"], "2020-05-22T12:00:00Z")
        self.assertEqual(row["new_price_target"], 50.0)
        self.assertEqual(row["raw_payload"]["semantic_duplicate_count"], 2)

    def test_truncated_source_fails_closed_without_output(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "analyst_ratings_processed.csv"
            output = Path(directory) / "events.jsonl.gz"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["", "title", "date", "stock"])
                writer.writeheader()
                writer.writerow(
                    {
                        "": "1",
                        "title": "Firm One Upgrades Example Corp from Hold to Buy",
                        "date": "2020-05-22 08:00:00-04:00",
                        "stock": "XYZ",
                    }
                )
            with self.assertRaisesRegex(RuntimeError, "source appears truncated"):
                import_history(source, output, minimum_source_rows=2)
            manifest = json.loads(
                output.with_name(output.name + ".manifest.json").read_text(encoding="utf-8")
            )
        self.assertFalse(output.exists())
        self.assertEqual(manifest["status"], "failed_closed")


if __name__ == "__main__":
    unittest.main()
