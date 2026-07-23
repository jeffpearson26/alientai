import unittest
from pathlib import Path
from evaluate_contextual_options_shadow_payload import evaluate
class ContextPayloadOutcomeTests(unittest.TestCase):
 def test_requires_research_only_payload(self):
  with self.assertRaises(ValueError): evaluate({"execution_enabled":True,"research_only":True},Path("."))
 def test_empty_payload_remains_nonexecuting(self):
  r=evaluate({"execution_enabled":False,"research_only":True,"candidates":[]},Path("."));self.assertEqual(r["completed"],0);self.assertFalse(r["execution_enabled"])
if __name__=="__main__":unittest.main()
