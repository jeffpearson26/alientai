from __future__ import annotations

import unittest

from web.public_sections import performance_snapshot_html


class PublicSectionsTests(unittest.TestCase):
    def test_research_status_has_no_static_performance_claim(self):
        html = performance_snapshot_html()
        self.assertIn("Under Active Development", html)
        self.assertIn("Research in progress", html)
        self.assertNotIn("60.71%", html)
        self.assertNotIn("Graded Trades", html)


if __name__ == "__main__":
    unittest.main()
