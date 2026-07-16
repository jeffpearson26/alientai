from pathlib import Path

path = Path("upload_v2_daily_candles_to_supabase.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("upload_v2_daily_candles_to_supabase_BACKUP_BEFORE_SP500_DATETIME_MS_FIX.py")
backup.write_text(text, encoding="utf-8")

# 1) Add timezone import if needed.
if "from datetime import datetime, timezone" not in text:
    text = text.replace("from datetime import datetime", "from datetime import datetime, timezone")

# 2) Add helper function after safe_int.
marker = '''def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default
'''

helper = '''def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def datetime_ms_from_row(raw: Dict[str, Any]) -> Tuple[int, str]:
    """
    Accept both uploader-native rows with datetime_ms/datetime_utc
    and Schwab daily CSV rows with date/datetime columns.

    S&P downloader CSV format:
      symbol,schwab_symbol,date,datetime,open,high,low,close,volume
    """
    existing_ms = safe_int(raw.get("datetime_ms"), 0)
    existing_utc = str(raw.get("datetime_utc") or "").strip()

    if existing_ms > 0:
        return existing_ms, existing_utc

    dt_text = str(
        raw.get("datetime")
        or raw.get("datetime_utc")
        or raw.get("date")
        or raw.get("timestamp")
        or ""
    ).strip()

    if not dt_text:
        return 0, ""

    try:
        # Handle Schwab-style ISO without timezone:
        # 2006-07-09T22:00:00
        clean = dt_text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)

        # If timezone missing, treat it as UTC for research consistency.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt_utc = dt.astimezone(timezone.utc)
        ms = int(dt_utc.timestamp() * 1000)
        return ms, dt_utc.isoformat()

    except Exception:
        # Last fallback: date only, e.g. 2006-07-09
        try:
            date_text = str(raw.get("date") or "").strip()
            if not date_text:
                return 0, ""

            dt = datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
            ms = int(dt.timestamp() * 1000)
            return ms, dt.isoformat()
        except Exception:
            return 0, ""
'''

if marker not in text:
    raise SystemExit("Could not find safe_int block. Paste the top of upload_v2_daily_candles_to_supabase.py.")
text = text.replace(marker, helper, 1)

# 3) Replace datetime_ms line with flexible parser.
old = '''            datetime_ms = safe_int(raw.get("datetime_ms"), 0)

            if not symbol or datetime_ms <= 0:
                continue

            row = {
                "symbol": symbol,
                "timeframe": "1d",
                "datetime_ms": datetime_ms,
                "datetime_utc": str(raw.get("datetime_utc") or ""),
                "date": str(raw.get("date") or ""),
                "open": safe_float(raw.get("open"), 0.0),
                "high": safe_float(raw.get("high"), 0.0),
                "low": safe_float(raw.get("low"), 0.0),
                "close": safe_float(raw.get("close"), 0.0),
                "volume": safe_int(raw.get("volume"), 0),
                "source": "schwab",
            }
'''

new = '''            datetime_ms, datetime_utc = datetime_ms_from_row(raw)

            if not symbol or datetime_ms <= 0:
                continue

            row = {
                "symbol": symbol,
                "timeframe": "1d",
                "datetime_ms": datetime_ms,
                "datetime_utc": datetime_utc,
                "date": str(raw.get("date") or str(datetime_utc)[:10]),
                "open": safe_float(raw.get("open"), 0.0),
                "high": safe_float(raw.get("high"), 0.0),
                "low": safe_float(raw.get("low"), 0.0),
                "close": safe_float(raw.get("close"), 0.0),
                "volume": safe_int(raw.get("volume"), 0),
                "source": "schwab",
            }
'''

if old not in text:
    raise SystemExit("Could not find row parser block. No changes made.")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

print("Patched uploader to compute datetime_ms from date/datetime columns.")
print("Backup:", backup)
