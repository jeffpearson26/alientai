import unittest

from alientai_v2.research.score_calibration import (
    calibrated_probability,
    fit_isotonic,
    percentile_rank,
)


class ScoreCalibrationTests(unittest.TestCase):
    def test_isotonic_predictions_are_monotonic(self):
        blocks = fit_isotonic([0.1, 0.2, 0.3, 0.4], [0, 1, 0, 1])
        predictions = [
            calibrated_probability(score, blocks)
            for score in (0.1, 0.2, 0.3, 0.4)
        ]
        self.assertEqual(predictions, sorted(predictions))

    def test_duplicate_scores_are_pooled(self):
        blocks = fit_isotonic([0.1, 0.1, 0.2], [0, 1, 1])
        self.assertEqual(calibrated_probability(0.1, blocks), 0.5)

    def test_percentile_rank_is_bounded_one_to_one_hundred(self):
        reference = [0.1, 0.2, 0.3, 0.4]
        self.assertEqual(percentile_rank(-1.0, reference), 1)
        self.assertEqual(percentile_rank(1.0, reference), 100)
        self.assertEqual(percentile_rank(0.2, reference), 50)

    def test_empty_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            fit_isotonic([], [])
        with self.assertRaises(ValueError):
            percentile_rank(0.5, [])


if __name__ == "__main__":
    unittest.main()
