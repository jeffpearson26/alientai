from __future__ import annotations

"""Compile leakage-safe, point-in-time news features from archived AV responses."""

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for pattern in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(text.replace("Z", "+0000"), pattern)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def article_sentiment(article: Mapping[str, Any], symbol: str) -> tuple[float | None, float]:
    for row in article.get("ticker_sentiment") or []:
        if str(row.get("ticker") or "").strip().upper() == symbol:
            return number(row.get("ticker_sentiment_score")), number(row.get("relevance_score")) or 1.0
    return number(article.get("overall_sentiment_score")), 1.0


def news_features(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    request = payload.get("alientai_request") or {}
    symbol = str(request.get("symbol") or "").strip().upper()
    as_of = parse_utc(request.get("as_of_utc"))
    if not symbol or as_of is None:
        return None
    visible: list[tuple[datetime, float, float]] = []
    future_articles = 0
    for article in payload.get("feed") or []:
        published = parse_utc(article.get("time_published"))
        if published is None:
            continue
        if published > as_of:
            future_articles += 1
            continue
        sentiment, relevance = article_sentiment(article, symbol)
        if sentiment is not None:
            visible.append((published, sentiment, max(0.0, relevance)))
    weights = sum(item[2] for item in visible)
    weighted_sentiment = sum(item[1] * item[2] for item in visible) / weights if weights else None
    latest = max((item[0] for item in visible), default=None)
    return {
        "symbol": symbol,
        "as_of_utc": as_of.isoformat(),
        "news_request_lookback_days": request.get("lookback_days"),
        "news_available": True,
        "news_article_count": len(visible),
        "news_weighted_sentiment": weighted_sentiment,
        "news_positive_article_count": sum(item[1] > 0.05 for item in visible),
        "news_negative_article_count": sum(item[1] < -0.05 for item in visible),
        "news_latest_published_utc": latest.isoformat() if latest else None,
        "news_latest_age_hours": round((as_of - latest).total_seconds() / 3600, 6) if latest else None,
        "news_future_articles_excluded": future_articles,
        "source": "alpha_vantage_news_sentiment_archive",
    }


def read_payloads(root: Path) -> Iterable[Mapping[str, Any]]:
    for path in sorted(root.rglob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            yield json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [row for payload in read_payloads(args.archive) if (row := news_features(payload))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
