import unittest

import numpy as np

from build_selective_two_day_shadow_policy import freeze_policy


class TwoDayShadowPolicyTests(unittest.TestCase):
    def test_freezes_upper_validation_slice_without_execution(self):
        result = freeze_policy(np.arange(100, dtype=float), top_fraction=0.01)
        self.assertEqual(result["score_cutoff"], 99.0)
        self.assertFalse(result["execution_enabled"])
        self.assertIsNone(result["maximum_candidates"])

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            freeze_policy(np.asarray([]))
        with self.assertRaises(ValueError):
            freeze_policy(np.asarray([1.0]), top_fraction=1.0)


if __name__ == "__main__":
    unittest.main()
