import unittest
from create_lightgbm_5day_shadow_snapshot import record
class LightGBMShadowSnapshotTests(unittest.TestCase):
 def test_record_is_never_an_execution_decision(self):
  row=record("AAPL","2026-07-21",0.55)
  self.assertEqual(row["decision"],"SHADOW_JOURNAL_ONLY"); self.assertFalse(row["execution_enabled"]); self.assertTrue(row["research_only"])
  self.assertEqual(row["outcome_not_due_before"],"2026-07-30")
if __name__=="__main__": unittest.main()
