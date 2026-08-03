import unittest

from build_ai_semiconductor_news_context import news_features


class NewsContextTests(unittest.TestCase):
    def test_future_and_other_ticker_articles_are_excluded(self):
        payload = {"feed": [
            {
                "time_published": "20260102T220000",
                "url": "future",
                "ticker_sentiment": [{"ticker": "AMD", "relevance_score": "1", "ticker_sentiment_score": "0.5"}],
            },
            {
                "time_published": "20260102T200000",
                "url": "other",
                "ticker_sentiment": [{"ticker": "NVDA", "relevance_score": "1", "ticker_sentiment_score": "0.5"}],
            },
        ]}
        result = news_features(payload, "AMD", "2026-01-02T21:00:00+00:00")
        self.assertEqual(result["narrative_news_1d_article_count"], 0)

    def test_target_sentiment_is_relevance_weighted_and_deduplicated(self):
        article = {
            "time_published": "20260102T200000",
            "url": "one",
            "source_domain": "example.com",
            "ticker_sentiment": [
                {"ticker": "AMD", "relevance_score": "1", "ticker_sentiment_score": "0.4"}
            ],
            "topics": [{"topic": "earnings", "relevance_score": "0.8"}],
        }
        payload = {"feed": [article, dict(article)]}
        result = news_features(payload, "AMD", "2026-01-02T21:00:00+00:00")
        self.assertEqual(result["narrative_news_1d_article_count"], 1)
        self.assertEqual(result["narrative_news_1d_source_count"], 1)
        self.assertAlmostEqual(result["narrative_news_1d_weighted_sentiment"], 0.4)
        self.assertAlmostEqual(result["narrative_news_1d_topic_earnings_max_relevance"], 0.8)


if __name__ == "__main__":
    unittest.main()
