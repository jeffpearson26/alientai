from __future__ import annotations

"""Exact-key Nasdaq panel for technical, news, and unusual-call research."""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


NEWS_FIELDS = ("news_article_count", "news_weighted_sentiment", "news_positive_article_count", "news_negative_article_count", "news_latest_age_hours")
CALL_FIELDS = ("call_activity_history_count", "call_volume_open_interest_ratio", "call_volume_vs_prior_median", "call_volume_zscore", "call_volume_unusual")
OPTION_FIELDS = ("option_call_open_interest", "option_call_volume", "option_near_money_call_iv", "option_near_money_put_call_iv_skew", "option_put_call_open_interest_ratio", "option_put_call_volume_ratio", "option_volume_open_interest_ratio")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key(row: Mapping[str, Any], date_field: str) -> tuple[str, str]:
    symbol, day = str(row.get("symbol") or "").upper(), str(row.get(date_field) or "")[:10]
    if not symbol or not day:
        raise ValueError("each row requires symbol and date")
    return symbol, day


def unique_index(rows: Iterable[Mapping[str, Any]], date_field: str) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        row_key = key(row, date_field)
        if row_key in result:
            raise ValueError(f"duplicate key: {row_key[0]}|{row_key[1]}")
        result[row_key] = row
    return result


def numeric(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_panel(base_rows: Iterable[Mapping[str, Any]], news_rows: Iterable[Mapping[str, Any]], call_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    base = unique_index(base_rows, "market_date")
    news, calls = unique_index(news_rows, "as_of_utc"), unique_index(call_rows, "market_date")
    missing_news, missing_calls = set(base) - set(news), set(base) - set(calls)
    if missing_news or missing_calls:
        raise ValueError("every base key must have exact news and call-history matches")
    output = []
    for row_key in sorted(base, key=lambda value: (value[1], value[0])):
        raw, headline, call = dict(base[row_key]), news[row_key], calls[row_key]
        if headline.get("news_available") is not True:
            raise ValueError(f"news unavailable for {row_key[0]}|{row_key[1]}")
        output.append({
            **raw,
            **{f"model_news_{field[5:]}": numeric(headline.get(field)) for field in NEWS_FIELDS},
            **{f"model_call_{field[5:]}": numeric(call.get(field)) for field in CALL_FIELDS},
            **{f"model_option_{field[7:]}": numeric(raw.get(field)) for field in OPTION_FIELDS},
            "research_only": True,
            "execution_enabled": False,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--news", type=Path, required=True)
    parser.add_argument("--call-history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build_panel(read_jsonl(args.base), read_jsonl(args.news), read_jsonl(args.call_history))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"status": "complete", "research_only": True, "rows": len(rows), "dates": len({row['market_date'] for row in rows}), "unusual_calls": sum(bool(row['model_call_volume_unusual']) for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
