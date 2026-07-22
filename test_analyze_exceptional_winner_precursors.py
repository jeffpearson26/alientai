from __future__ import annotations

import unittest

from analyze_exceptional_winner_precursors import precursor_profile


class ExceptionalWinnerPrecursorTests(unittest.TestCase):
    def test_reports_group_medians(self):
        result = precursor_profile([
            {"study_label": 1, "alpha": 3.0}, {"study_label": 1, "alpha": 5.0},
            {"study_label": 0, "alpha": 1.0}, {"study_label": 0, "alpha": 2.0},
        ], ["alpha"])
        self.assertEqual(4.0, result[0]["winner_median"])
        self.assertEqual(1.5, result[0]["control_median"])

    def test_missing_values_are_excluded(self):
        result = precursor_profile([{"study_label": 1, "alpha": None}, {"study_label": 0, "alpha": 1}], ["alpha"])
        self.assertEqual([], result)


if __name__ == "__main__":
    unittest.main()
