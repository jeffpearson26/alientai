import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

BUILD = "ALIENTAI_V2_DAILY_NEWS_SENTIMENT_LIBRARY_ALPHA_VANTAGE_V1"

ROOT = Path.cwd()
load_dotenv(ROOT / ".env")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def read_symbols(path: Path):
    symbols = []
    seen = set()

    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip().upper()
        if not s or s.startswith("#"):
            continue
        if "," in s:
            s = s.split(",", 1)[0].strip().upper()
        if s and s not in seen:
            seen.add(s)
            symbols.append(s)

    return symbols


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def yyyymmdd_thhmm(dt: datetime):
    return dt.strftime("%Y%m%dT%H%M")


def date_from_time_published(value: str):
    # Alpha Vantage usually returns time_published like 20260714T123000.
    if not value:
        return ""
    try:
        return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").date().isoformat()
    except Exception:
        try:
            return datetime.strptime(value[:13], "%Y%m%dT%H%M").date().isoformat()
        except Exception:
            return ""


def headline_contains_ticker(title: str, symbol: str):
    title = title or ""
    symbol = symbol.upper().strip()

    # Match plain ticker as its own token or $TICKER.
    # Examples matched: "NVDA", "$NVDA", "NVDA stock"
    pattern = rf"(?<![A-Z0-9])\$?{re.escape(symbol)}(?![A-Z0-9])"
    return bool(re.search(pattern, title.upper()))


def sentiment_bucket(score: float):
    if score >= 0.35:
        return "very_positive"
    if score >= 0.15:
        return "positive"
    if score <= -0.35:
        return "very_negative"
    if score <= -0.15:
        return "negative"
    return "neutral"


def extract_ticker_sentiment(article: dict, symbol: str):
    ticker_sentiment = article.get("ticker_sentiment") or []
    symbol = symbol.upper()

    for item in ticker_sentiment:
        ticker = str(item.get("ticker") or "").upper()
        if ticker == symbol:
            score = safe_float(item.get("ticker_sentiment_score"), 0.0)
            label = str(item.get("ticker_sentiment_label") or sentiment_bucket(score))
            relevance = safe_float(item.get("relevance_score"), 0.0)

            return {
                "ticker_sentiment_score": score,
                "ticker_sentiment_label": label,
                "ticker_relevance_score": relevance,
            }

    # Fallback to article-level sentiment if ticker-level sentiment is missing.
    score = safe_float(article.get("overall_sentiment_score"), 0.0)
    label = str(article.get("overall_sentiment_label") or sentiment_bucket(score))

    return {
        "ticker_sentiment_score": score,
        "ticker_sentiment_label": label,
        "ticker_relevance_score": 0.0,
    }


def fetch_alpha_vantage_news(symbol: str, api_key: str, start: datetime, end: datetime, limit: int):
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "time_from": yyyymmdd_thhmm(start),
        "time_to": yyyymmdd_thhmm(end),
        "limit": str(limit),
        "apikey": api_key,
    }

    url = "https://www.alphavantage.co/query?" + urlencode(params)

    r = requests.get(url, timeout=60)

    try:
        data = r.json()
    except Exception:
        return {
            "status": "error",
            "http_status": r.status_code,
            "message": r.text[:500],
            "feed": [],
        }

    if r.status_code != 200:
        return {
            "status": "error",
            "http_status": r.status_code,
            "message": json.dumps(data)[:500],
            "feed": [],
        }

    if "Note" in data:
        return {
            "status": "rate_limited",
            "http_status": r.status_code,
            "message": data.get("Note"),
            "feed": [],
        }

    if "Information" in data:
        return {
            "status": "info",
            "http_status": r.status_code,
            "message": data.get("Information"),
            "feed": [],
        }

    return {
        "status": "success",
        "http_status": r.status_code,
        "message": "",
        "feed": data.get("feed") or [],
    }


def main():
    parser = argparse.ArgumentParser(description="Build daily ticker-headline news sentiment library.")
    parser.add_argument("--symbols-file", required=True)
    parser.add_argument("--run-name", default="news_sentiment_v1")
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--limit-per-symbol", type=int, default=50)
    parser.add_argument("--delay", type=float, default=15.0)
    parser.add_argument("--headline-ticker-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    api_key = (
        os.getenv("ALPHA_VANTAGE_API_KEY")
        or os.getenv("ALPHAVANTAGE_API_KEY")
        or os.getenv("AV_API_KEY")
    )

    if not api_key:
        raise SystemExit("Missing ALPHA_VANTAGE_API_KEY in .env")

    symbols = read_symbols(Path(args.symbols_file))

    out_dir = ROOT / "data_v2" / "training_library" / "daily_news_sentiment_v1" / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_path = out_dir / "daily_news_sentiment_rows.jsonl"
    summary_csv_path = out_dir / "daily_news_sentiment_summary.csv"
    summary_json_path = out_dir / "daily_news_sentiment_summary.json"

    if rows_path.exists() and not args.overwrite:
        raise SystemExit(f"Output exists already. Use --overwrite to replace: {rows_path}")

    if args.overwrite and rows_path.exists():
        rows_path.unlink()

    end = datetime.now()
    start = end - timedelta(days=args.days_back)

    print("Build:", BUILD)
    print("Symbols file:", args.symbols_file)
    print("Symbols:", len(symbols))
    print("Output dir:", out_dir)
    print("Days back:", args.days_back)
    print("Limit per symbol:", args.limit_per_symbol)
    print("Headline ticker only:", args.headline_ticker_only)
    print("This does NOT touch V2 paper accounts.")
    print("")

    total_articles = 0
    total_kept = 0
    summary_rows = []

    with rows_path.open("w", encoding="utf-8") as out:
        for i, symbol in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] Fetching news for {symbol}...")

            result = fetch_alpha_vantage_news(
                symbol=symbol,
                api_key=api_key,
                start=start,
                end=end,
                limit=args.limit_per_symbol,
            )

            feed = result["feed"]
            articles_seen = len(feed)
            articles_kept = 0
            sentiment_sum = 0.0
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            headline_ticker_count = 0

            if result["status"] != "success":
                print(" ", result["status"], result["message"])
                summary_rows.append({
                    "symbol": symbol,
                    "status": result["status"],
                    "articles_seen": 0,
                    "articles_kept": 0,
                    "headline_ticker_count": 0,
                    "avg_sentiment": "",
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "message": result["message"],
                })
                if result["status"] == "rate_limited":
                    print("  Rate limited. Stopping early.")
                    break
                continue

            for article in feed:
                title = article.get("title") or ""
                url = article.get("url") or ""
                source = article.get("source") or ""
                time_published = article.get("time_published") or ""
                published_date = date_from_time_published(time_published)

                has_ticker_in_headline = headline_contains_ticker(title, symbol)

                if has_ticker_in_headline:
                    headline_ticker_count += 1

                if args.headline_ticker_only and not has_ticker_in_headline:
                    continue

                sent = extract_ticker_sentiment(article, symbol)
                score = sent["ticker_sentiment_score"]
                label = sent["ticker_sentiment_label"]

                row = {
                    "build": BUILD,
                    "created_at": now_iso(),
                    "symbol": symbol,
                    "published_date": published_date,
                    "time_published": time_published,
                    "source": source,
                    "title": title,
                    "url": url,
                    "summary": article.get("summary") or "",
                    "headline_contains_ticker": has_ticker_in_headline,
                    "overall_sentiment_score": safe_float(article.get("overall_sentiment_score"), 0.0),
                    "overall_sentiment_label": article.get("overall_sentiment_label") or "",
                    "ticker_sentiment_score": score,
                    "ticker_sentiment_label": label,
                    "ticker_relevance_score": sent["ticker_relevance_score"],
                    "topics": article.get("topics") or [],
                }

                out.write(json.dumps(row, separators=(",", ":")) + "\n")

                articles_kept += 1
                sentiment_sum += score

                bucket = sentiment_bucket(score)
                if "positive" in bucket:
                    positive_count += 1
                elif "negative" in bucket:
                    negative_count += 1
                else:
                    neutral_count += 1

            avg_sentiment = sentiment_sum / articles_kept if articles_kept else 0.0

            print(
                f"  seen={articles_seen} kept={articles_kept} "
                f"headline_ticker={headline_ticker_count} avg_sentiment={avg_sentiment:.4f}"
            )

            summary_rows.append({
                "symbol": symbol,
                "status": "success",
                "articles_seen": articles_seen,
                "articles_kept": articles_kept,
                "headline_ticker_count": headline_ticker_count,
                "avg_sentiment": round(avg_sentiment, 6),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "message": "",
            })

            total_articles += articles_seen
            total_kept += articles_kept

            if args.delay:
                time.sleep(args.delay)

    with summary_csv_path.open("w", encoding="utf-8", newline="") as f:
        fields = [
            "symbol",
            "status",
            "articles_seen",
            "articles_kept",
            "headline_ticker_count",
            "avg_sentiment",
            "positive_count",
            "negative_count",
            "neutral_count",
            "message",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    report = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "symbols_file": args.symbols_file,
        "symbols_seen": len(symbols),
        "days_back": args.days_back,
        "headline_ticker_only": args.headline_ticker_only,
        "total_articles_seen": total_articles,
        "total_articles_kept": total_kept,
        "output_dir": str(out_dir),
        "rows_path": str(rows_path),
        "summary_csv": str(summary_csv_path),
        "summary_json": str(summary_json_path),
    }

    summary_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
