import unittest
from build_finra_short_interest_features import build
class FinraFeatureTests(unittest.TestCase):
 def test_uses_only_prior_publication(self):
  rows=build([{'symbol':'A','market_date':'2026-01-10'}],[{'symbol':'A','available_at_utc':'2026-01-11T23:59:59Z','settlement_date':'2025-12-31','short_interest_shares':1},{'symbol':'A','available_at_utc':'2026-01-09T23:59:59Z','settlement_date':'2025-12-15','short_interest_shares':2}])
  self.assertEqual(rows[0]['short_interest_shares'],2)
if __name__=='__main__':unittest.main()
