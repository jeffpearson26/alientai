from __future__ import annotations

import unittest

from compile_historical_news_features import news_features


class HistoricalNewsFeatureTests(unittest.TestCase):
    def test_excludes_future_article_and_uses_ticker_sentiment(self):
        payload = {
            "alientai_request": {"symbol": "ABC", "as_of_utc": "2024-01-10T21:00:00+00:00", "lookback_days": 14},
            "feed": [
                {"time_published": "20240110T200000", "overall_sentiment_score": -0.9,
                 "ticker_sentiment": [{"ticker": "ABC", "ticker_sentiment_score": "0.4", "relevance_score": "0.8"}]},
                {"time_published": "20240110T220000", "overall_sentiment_score": 0.9,
                 "ticker_sentiment": [{"ticker": "ABC", "ticker_sentiment_score": "0.9", "relevance_score": "1"}]},
            ],
        }
        result = news_features(payload)
        self.assertEqual(result["news_article_count"], 1)
        self.assertAlmostEqual(result["news_weighted_sentiment"], 0.4)
        self.assertEqual(result["news_future_articles_excluded"], 1)
        self.assertEqual(result["news_latest_age_hours"], 1.0)

    def test_missing_request_identity_fails_closed(self):
        self.assertIsNone(news_features({"alientai_request": {}, "feed": []}))

    def test_uses_overall_sentiment_when_symbol_detail_missing(self):
        payload = {
            "alientai_request": {"symbol": "ABC", "as_of_utc": "2024-01-10T21:00:00Z"},
            "feed": [{"time_published": "20240110T200000", "overall_sentiment_score": "-0.2"}],
        }
        result = news_features(payload)
        self.assertEqual(result["news_negative_article_count"], 1)
        self.assertAlmostEqual(result["news_weighted_sentiment"], -0.2)


if __name__ == "__main__":
    unittest.main()
