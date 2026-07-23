import unittest
from datetime import date
from finra_short_interest_calendar import publication_date
class FinraCalendarTests(unittest.TestCase):
 def test_matches_official_2026_examples(self):
  self.assertEqual(publication_date(date(2026,1,15)),date(2026,1,27))
  self.assertEqual(publication_date(date(2026,3,31)),date(2026,4,10))
  self.assertEqual(publication_date(date(2026,6,30)),date(2026,7,10))
if __name__=='__main__':unittest.main()
