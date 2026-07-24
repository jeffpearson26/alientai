import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from evaluate_contextual_options_shadow_payload import evaluate
class ContextPayloadOutcomeTests(unittest.TestCase):
 def test_requires_research_only_payload(self):
  with self.assertRaises(ValueError): evaluate({"execution_enabled":True,"research_only":True},Path("."))
 def test_empty_payload_remains_nonexecuting(self):
  r=evaluate({"execution_enabled":False,"research_only":True,"candidates":[]},Path("."));self.assertEqual(r["completed"],0);self.assertFalse(r["execution_enabled"])
 def test_pending_payload_reports_interim_return_not_final_outcome(self):
  with TemporaryDirectory() as directory:
   root=Path(directory)
   (root / "ABC_schwab_1d_max.csv").write_text("date,close\n2026-07-21,100\n2026-07-22,102\n",encoding="utf-8")
   payload={"execution_enabled":False,"research_only":True,"candidates":[{"symbol":"ABC","market_date":"2026-07-21"}]}
   result=evaluate(payload,root)
   self.assertEqual(result["completed"],0)
   self.assertEqual(result["pending_records"][0]["observed_future_sessions"],1)
   self.assertEqual(result["pending_records"][0]["interim_session_returns_pct"],{"1":2.0})
if __name__=="__main__":unittest.main()
