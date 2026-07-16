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

BUILD = "ALIENTAI_V2_PREFERRED_NVIDIA_HALO_NEWS_SCAN_V1"

ROOT = Path.cwd()
load_dotenv(ROOT / ".env")


NVIDIA_PATTERN = re.compile(r"\b(NVDA|NVIDIA|NVIDEA)\b", re.IGNORECASE)


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
    pattern = rf"(?<![A-Z0-9])\$?{re.escape(symbol)}(?![A-Z0-9])"
    return bool(re.search(pattern, title.upper()))


def text_mentions_nvidia(text: str):
    return bool(NVIDIA_PATTERN.search(text or ""))


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
            return score, label, relevance

    score = safe_float(article.get("overall_sentiment_score"), 0.0)
    label = str(article.get("overall_sentiment_label") or sentiment_bucket(score))
    return score, label, 0.0


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
            "message": r.text[:500],
            "feed": [],
        }

    if "Note" in data:
        return {
            "status": "rate_limited",
            "message": data.get("Note"),
            "feed": [],
        }

    if "Information" in data:
        return {
            "status": "info",
            "message": data.get("Information"),
            "feed": [],
        }

    return {
        "status": "success",
        "message": "",
        "feed": data.get("feed") or [],
    }


def main():
    parser = argparse.ArgumentParser(description="Scan preferred symbols for Nvidia/NVDA co-mention news.")
    parser.add_argument("--symbols-file", default="preferred_stock_symbols.txt")
    parser.add_argument("--run-name", default="preferred_nvidia_halo_news_v1")
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--limit-per-symbol", type=int, default=50)
    parser.add_argument("--delay", type=float, default=15.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    api_key = (
        os.getenv("ALPHA_VANTAGE_API_KEY")
        or os.getenv("ALPHAVANTAGE_API_KEY")
        or os.getenv("AV_API_KEY")
    )

    if not api_key:
        raise SystemExit("Missing ALPHA_VANTAGE_API_KEY in .env")

    symbols_file = Path(args.symbols_file)
    if not symbols_file.exists():
        raise SystemExit(f"Missing symbols file: {symbols_file}")

    symbols = read_symbols(symbols_file)

    out_dir = ROOT / "data_v2" / "training_library" / "preferred_nvidia_halo_news_v1" / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_jsonl = out_dir / "preferred_nvidia_halo_news_rows.jsonl"
    rows_csv = out_dir / "preferred_nvidia_halo_news_rows.csv"
    summary_csv = out_dir / "preferred_nvidia_halo_news_summary.csv"
    summary_json = out_dir / "preferred_nvidia_halo_news_summary.json"

    if rows_jsonl.exists() and not args.overwrite:
        raise SystemExit(f"Output exists already. Use --overwrite: {rows_jsonl}")

    if args.overwrite:
        for p in [rows_jsonl, rows_csv, summary_csv, summary_json]:
            if p.exists():
                p.unlink()

    end = datetime.now()
    start = end - timedelta(days=args.days_back)

    print("Build:", BUILD)
    print("Symbols:", len(symbols))
    print("Output dir:", out_dir)
    print("Days back:", args.days_back)
    print("This scans for Nvidia/NVIDIA/NVDA co-mentions.")
    print("This does NOT touch V2 paper accounts.")
    print("")

    all_rows = []
    summary_rows = []

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Nvidia halo scan for {symbol}...")

        result = fetch_alpha_vantage_news(symbol, api_key, start, end, args.limit_per_symbol)

        if result["status"] != "success":
            print(" ", result["status"], result["message"])
            summary_rows.append({
                "symbol": symbol,
                "status": result["status"],
                "articles_seen": 0,
                "nvidia_mentions_kept": 0,
                "headline_nvidia_mentions": 0,
                "avg_ticker_sentiment": "",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "message": result["message"],
            })

            if result["status"] == "rate_limited":
                print("  Rate limited. Stopping early.")
                break

            continue

        feed = result["feed"]
        kept = 0
        headline_nvidia_count = 0
        sentiment_sum = 0.0
        positive = 0
        negative = 0
        neutral = 0

        for article in feed:
            title = article.get("title") or ""
            summary = article.get("summary") or ""
            combined = title + " " + summary

            headline_has_nvidia = text_mentions_nvidia(title)
            article_has_nvidia = text_mentions_nvidia(combined)

            if not article_has_nvidia:
                continue

            ticker_score, ticker_label, ticker_relevance = extract_ticker_sentiment(article, symbol)

            row = {
                "build": BUILD,
                "created_at": now_iso(),
                "symbol": symbol,
                "published_date": date_from_time_published(article.get("time_published") or ""),
                "time_published": article.get("time_published") or "",
                "source": article.get("source") or "",
                "title": title,
                "url": article.get("url") or "",
                "summary": summary,
                "headline_contains_symbol": headline_contains_ticker(title, symbol),
                "headline_mentions_nvidia": headline_has_nvidia,
                "article_mentions_nvidia": article_has_nvidia,
                "overall_sentiment_score": safe_float(article.get("overall_sentiment_score"), 0.0),
                "overall_sentiment_label": article.get("overall_sentiment_label") or "",
                "ticker_sentiment_score": ticker_score,
                "ticker_sentiment_label": ticker_label,
                "ticker_relevance_score": ticker_relevance,
                "nvidia_halo_signal": True,
            }

            all_rows.append(row)
            kept += 1
            sentiment_sum += ticker_score

            if headline_has_nvidia:
                headline_nvidia_count += 1

            bucket = sentiment_bucket(ticker_score)
            if "positive" in bucket:
                positive += 1
            elif "negative" in bucket:
                negative += 1
            else:
                neutral += 1

        avg_sentiment = sentiment_sum / kept if kept else 0.0

        print(
            f"  seen={len(feed)} nvidia_mentions={kept} "
            f"headline_nvidia={headline_nvidia_count} avg_sentiment={avg_sentiment:.4f}"
        )

        summary_rows.append({
            "symbol": symbol,
            "status": "success",
            "articles_seen": len(feed),
            "nvidia_mentions_kept": kept,
            "headline_nvidia_mentions": headline_nvidia_count,
            "avg_ticker_sentiment": round(avg_sentiment, 6),
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "message": "",
        })

        if args.delay:
            time.sleep(args.delay)

    with rows_jsonl.open("w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    row_fields = [
        "symbol",
        "published_date",
        "time_published",
        "source",
        "title",
        "url",
        "headline_contains_symbol",
        "headline_mentions_nvidia",
        "article_mentions_nvidia",
        "overall_sentiment_score",
        "overall_sentiment_label",
        "ticker_sentiment_score",
        "ticker_sentiment_label",
        "ticker_relevance_score",
        "nvidia_halo_signal",
    ]

    with rows_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row_fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in row_fields})

    summary_fields = [
        "symbol",
        "status",
        "articles_seen",
        "nvidia_mentions_kept",
        "headline_nvidia_mentions",
        "avg_ticker_sentiment",
        "positive_count",
        "negative_count",
        "neutral_count",
        "message",
    ]

    with summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)

    report = {
        "status": "complete",
        "finished_at": now_iso(),
        "build": BUILD,
        "symbols_file": str(symbols_file),
        "symbols_seen": len(symbols),
        "days_back": args.days_back,
        "total_nvidia_halo_rows": len(all_rows),
        "output_dir": str(out_dir),
        "rows_jsonl": str(rows_jsonl),
        "rows_csv": str(rows_csv),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
    }

    summary_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("")
    print("DONE")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
