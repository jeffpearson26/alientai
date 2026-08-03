from __future__ import annotations

"""Attach timestamped target-specific Alpha Vantage news context."""

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


TOPICS = ("earnings", "technology", "financial_markets", "manufacturing")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _av_timestamp(value: Any) -> datetime:
    return datetime.strptime(str(value), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def news_features(
    payload: Mapping[str, Any],
    symbol: str,
    as_of_utc: str,
) -> dict[str, Any]:
    cutoff = datetime.fromisoformat(as_of_utc.replace("Z", "+00:00"))
    articles: dict[tuple[str, str], dict[str, Any]] = {}
    for article in payload.get("feed") or []:
        try:
            published = _av_timestamp(article.get("time_published"))
        except (TypeError, ValueError):
            continue
        if published > cutoff:
            continue
        ticker = next(
            (
                item for item in article.get("ticker_sentiment") or []
                if str(item.get("ticker") or "").upper() == symbol.upper()
            ),
            None,
        )
        if not ticker:
            continue
        key = (
            str(article.get("time_published") or ""),
            str(article.get("url") or article.get("title") or "").strip().lower(),
        )
        topics = {
            str(item.get("topic") or "").lower(): float(item.get("relevance_score") or 0.0)
            for item in article.get("topics") or []
        }
        articles[key] = {
            "published": published,
            "sentiment": float(ticker.get("ticker_sentiment_score") or 0.0),
            "relevance": float(ticker.get("relevance_score") or 0.0),
            "source": str(article.get("source_domain") or article.get("source") or "").lower(),
            "topics": topics,
        }
    result: dict[str, Any] = {"narrative_news_available": True}
    values = list(articles.values())
    for days in (1, 5, 14):
        recent = [
            item for item in values
            if 0 <= (cutoff - item["published"]).total_seconds() <= days * 86400
        ]
        weights = np.asarray([item["relevance"] for item in recent], dtype=float)
        sentiments = np.asarray([item["sentiment"] for item in recent], dtype=float)
        weighted = (
            float(np.average(sentiments, weights=weights))
            if len(recent) and float(np.sum(weights)) > 0
            else 0.0
        )
        prefix = f"narrative_news_{days}d"
        result.update({
            f"{prefix}_article_count": len(recent),
            f"{prefix}_source_count": len({item["source"] for item in recent if item["source"]}),
            f"{prefix}_weighted_sentiment": weighted,
            f"{prefix}_positive_count": sum(item["sentiment"] >= 0.15 for item in recent),
            f"{prefix}_negative_count": sum(item["sentiment"] <= -0.15 for item in recent),
            f"{prefix}_mean_relevance": float(np.mean(weights)) if len(recent) else 0.0,
        })
        for topic in TOPICS:
            result[f"{prefix}_topic_{topic}_max_relevance"] = max(
                (item["topics"].get(topic, 0.0) for item in recent),
                default=0.0,
            )
    result["narrative_news_latest_age_hours"] = min(
        ((cutoff - item["published"]).total_seconds() / 3600 for item in values),
        default=0.0,
    )
    result["narrative_news_target_article_count_total"] = len(values)
    return result


def load_payload(root: Path, symbol: str, market_date: str) -> Mapping[str, Any]:
    matches = list((root / market_date[:4] / market_date).glob(f"{symbol}_*.json.gz"))
    if len(matches) != 1:
        raise ValueError(f"expected one news payload for {symbol}|{market_date}, got {len(matches)}")
    with gzip.open(matches[0], "rt", encoding="utf-8") as handle:
        return json.load(handle)


def attach_news(
    panel_rows: Iterable[Mapping[str, Any]],
    news_root: Path,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for source in panel_rows:
        symbol = str(source.get("symbol") or "").upper()
        market_date = str(source.get("market_date") or "")[:10]
        key = (symbol, market_date)
        if not all(key) or key in seen:
            raise ValueError(f"invalid or duplicate panel key: {key}")
        seen.add(key)
        as_of = str(source.get("as_of_utc") or "")
        if not as_of:
            raise ValueError(f"missing as_of_utc for {symbol}|{market_date}")
        row = dict(source)
        row.update(news_features(load_payload(news_root, symbol, market_date), symbol, as_of))
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--news-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = attach_news(read_jsonl(args.panel), args.news_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "execution_enabled": False,
        "rows": len(rows),
        "available_rows": sum(row["narrative_news_available"] for row in rows),
        "rows_with_target_news_5d": sum(row["narrative_news_5d_article_count"] > 0 for row in rows),
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
