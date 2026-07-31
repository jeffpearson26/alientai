from __future__ import annotations

"""Build an Alpha-Vantage-labelled AI/semiconductor catalyst research panel."""

import argparse
import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


ALIASES = {
    "AMAT": ("AMAT", "Applied Materials"),
    "AMD": ("AMD", "Advanced Micro Devices"),
    "AMZN": ("AMZN", "Amazon"),
    "ANET": ("ANET", "Arista Networks"),
    "AVGO": ("AVGO", "Broadcom"),
    "CDNS": ("CDNS", "Cadence Design"),
    "GOOGL": ("GOOGL", "Google", "Alphabet"),
    "KLAC": ("KLAC", "KLA Corp", "KLA Corporation"),
    "LRCX": ("LRCX", "Lam Research"),
    "META": ("META", "Meta Platforms"),
    "MSFT": ("MSFT", "Microsoft"),
    "MU": ("MU", "Micron"),
    "NVDA": ("NVDA", "Nvidia"),
    "ORCL": ("ORCL", "Oracle"),
    "PLTR": ("PLTR", "Palantir"),
    "SMCI": ("SMCI", "Super Micro"),
    "SNPS": ("SNPS", "Synopsys"),
}
RATING_WORDS = (
    "buy", "outperform", "overweight", "positive", "neutral", "hold",
    "market perform", "sell", "underperform", "underweight", "negative",
)
CLAUSE_SPLIT = re.compile(r"\s*(?:[;|]|\s[-–—]\s)\s*")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def row_key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("symbol") or "").upper(), str(row.get("market_date") or "")[:10]


def unique_index(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if not all(key) or key in result:
            raise ValueError(f"invalid or duplicate key: {key}")
        result[key] = row
    return result


def combine_base_options_calls(
    base_rows: Iterable[Mapping[str, Any]],
    option_rows: Iterable[Mapping[str, Any]],
    call_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    base, options, calls = unique_index(base_rows), unique_index(option_rows), unique_index(call_rows)
    missing_base, missing_calls = set(options) - set(base), set(options) - set(calls)
    if missing_base or missing_calls:
        raise ValueError(
            f"options require exact base/call matches; missing base={len(missing_base)}, calls={len(missing_calls)}"
        )
    output = []
    for key in sorted(options, key=lambda value: (value[1], value[0])):
        row, option, call = dict(base[key]), options[key], calls[key]
        row.update(option)
        row.update({f"model_option_{name[7:]}": value for name, value in option.items() if name.startswith("option_")})
        row.update({f"model_call_{name[5:]}": value for name, value in call.items() if name.startswith("call_")})
        output.append(row)
    return output


def analyst_action_from_title(title: str, symbol: str) -> int:
    """Return +1/-1 only for an explicit, target-specific rating action."""
    aliases = ALIASES.get(symbol.upper(), (symbol.upper(),))
    alias_pattern = "|".join(rf"\b{re.escape(alias)}\b" for alias in aliases)
    rating_pattern = "|".join(re.escape(word) for word in RATING_WORDS)
    for clause in CLAUSE_SPLIT.split(title):
        if not re.search(alias_pattern, clause, re.IGNORECASE):
            continue
        upgrade = re.search(r"\b(?:upgrades?|upgraded|raised)\b", clause, re.IGNORECASE)
        downgrade = re.search(r"\b(?:downgrades?|downgraded|lowered)\b", clause, re.IGNORECASE)
        rating_context = re.search(
            rf"\b(?:analyst|broker|rating|rated|initiated|reiterated|price target|{rating_pattern})\b",
            clause,
            re.IGNORECASE,
        )
        if rating_context and bool(upgrade) != bool(downgrade):
            return 1 if upgrade else -1
    return 0


def parse_av_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def analyst_proxy_features(payload: Mapping[str, Any], symbol: str, as_of: datetime) -> dict[str, Any]:
    events: dict[tuple[str, str], tuple[datetime, int]] = {}
    for article in payload.get("feed") or []:
        published_raw, title = str(article.get("time_published") or ""), str(article.get("title") or "")
        try:
            published = parse_av_time(published_raw)
        except ValueError:
            continue
        if published > as_of:
            continue
        action = analyst_action_from_title(title, symbol)
        if action:
            events[(published_raw, " ".join(title.lower().split()))] = (published, action)
    values = list(events.values())
    result: dict[str, Any] = {
        "analyst_proxy_available": True,
        "analyst_proxy_event_count_14d": len(values),
        "analyst_proxy_net_action_14d": sum(action for _, action in values),
    }
    for days in (1, 5):
        recent = [action for published, action in values if 0 <= (as_of - published).total_seconds() <= days * 86400]
        result[f"analyst_proxy_upgrade_count_{days}d"] = sum(action > 0 for action in recent)
        result[f"analyst_proxy_downgrade_count_{days}d"] = sum(action < 0 for action in recent)
        result[f"analyst_proxy_net_action_{days}d"] = sum(recent)
    result["analyst_proxy_latest_age_hours"] = (
        min((as_of - published).total_seconds() / 3600 for published, _ in values) if values else None
    )
    return result


def load_daily(path: Path) -> list[tuple[str, float, float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    series = payload.get("Time Series (Daily)") or {}
    return sorted(
        (day, float(values["1. open"]), float(values["4. close"]))
        for day, values in series.items()
    )


def executable_label(daily: list[tuple[str, float, float]], market_date: str) -> dict[str, Any] | None:
    dates = [row[0] for row in daily]
    if market_date not in dates:
        return None
    index = dates.index(market_date)
    if index + 5 >= len(daily):
        return None
    entry_day, entry_open, _ = daily[index + 1]
    exit_day, _, exit_close = daily[index + 5]
    return {
        "label_entry_market_date": entry_day,
        "label_exit_market_date": exit_day,
        "label_entry_next_open": entry_open,
        "label_exit_fifth_close": exit_close,
        "label_forward_return_5d_av_pct": (exit_close / entry_open - 1.0) * 100.0,
        "label_forward_return_5d_av_net_pct": (exit_close / entry_open - 1.0) * 100.0 - 0.25,
    }


def load_news(news_root: Path, symbol: str, market_date: str) -> Mapping[str, Any]:
    matches = list((news_root / market_date[:4] / market_date).glob(f"{symbol}_*.json.gz"))
    if len(matches) != 1:
        raise ValueError(f"expected one Alpha Vantage news payload for {symbol}|{market_date}, got {len(matches)}")
    with gzip.open(matches[0], "rt", encoding="utf-8") as handle:
        return json.load(handle)


def build_panel(
    combined_rows: Iterable[Mapping[str, Any]],
    premarket_rows: Iterable[Mapping[str, Any]],
    symbols: set[str],
    news_root: Path,
    daily_root: Path,
) -> list[dict[str, Any]]:
    base = {key: value for key, value in unique_index(combined_rows).items() if key[0] in symbols}
    premarket = unique_index(premarket_rows)
    daily = {symbol: load_daily(daily_root / f"{symbol}_daily.json") for symbol in symbols}
    output: list[dict[str, Any]] = []
    for key in sorted(base, key=lambda value: (value[1], value[0])):
        if key not in premarket:
            raise ValueError(f"missing exact premarket match: {key[0]}|{key[1]}")
        label = executable_label(daily[key[0]], key[1])
        if not label:
            continue
        raw, pm = dict(base[key]), premarket[key]
        payload = load_news(news_root, *key)
        as_of = datetime.fromisoformat(str(raw["as_of_utc"]).replace("Z", "+00:00"))
        raw.update({
            **{f"model_{name}": value for name, value in pm.items() if name.startswith("premarket_")},
            **{f"model_{name}": value for name, value in analyst_proxy_features(payload, key[0], as_of).items()},
            **label,
            "label_source": "Alpha Vantage TIME_SERIES_DAILY",
            "label_contract": "decision after close; next-session open entry; fifth subsequent session close exit",
            "round_trip_cost_pct": 0.25,
            "research_only": True,
            "execution_enabled": False,
        })
        output.append(raw)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-panel", type=Path, required=True)
    parser.add_argument("--options", type=Path)
    parser.add_argument("--call-history", type=Path)
    parser.add_argument("--premarket", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, required=True)
    parser.add_argument("--news-root", type=Path, required=True)
    parser.add_argument("--daily-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    symbols = {
        line.strip().upper() for line in args.symbols_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    combined = read_jsonl(args.combined_panel)
    if bool(args.options) != bool(args.call_history):
        raise ValueError("--options and --call-history must be supplied together")
    if args.options:
        combined = combine_base_options_calls(
            combined, read_jsonl(args.options), read_jsonl(args.call_history)
        )
    rows = build_panel(combined, read_jsonl(args.premarket), symbols, args.news_root, args.daily_root)
    if len({row["market_date"] for row in rows}) < 30:
        raise ValueError("fewer than 30 labelled market dates; refusing to build")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "research_only": True,
        "rows": len(rows),
        "symbols": len({row["symbol"] for row in rows}),
        "dates": len({row["market_date"] for row in rows}),
        "first_date": min(row["market_date"] for row in rows),
        "last_date": max(row["market_date"] for row in rows),
        "analyst_proxy_event_rows": sum(row["model_analyst_proxy_event_count_14d"] > 0 for row in rows),
    }, indent=2))


if __name__ == "__main__":
    main()
