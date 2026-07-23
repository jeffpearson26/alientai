import unittest
from pathlib import Path
from finra_short_interest_calendar import publication_date
class FinraBatchTests(unittest.TestCase):
 def test_filename_date_has_expected_publication(self):
  self.assertEqual(publication_date(__import__('datetime').date(2026,6,30)).isoformat(),'2026-07-10')
if __name__=='__main__':unittest.main()
