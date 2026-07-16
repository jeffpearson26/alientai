import os
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from supabase import create_client

BUILD = "ALIENTAI_V2_SIMILARITY_PERCENTILE_SANDBOX_SCAN_ONCE_BUYER_V1"

PROJECT_ROOT = Path.cwd()
load_dotenv(PROJECT_ROOT / ".env")

ACCOUNT_PATH = PROJECT_ROOT / "data_v2" / "similarity_percentile_sandbox" / "similarity_percentile_sandbox_account.json"
MODEL_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_model.json"
ALLOWED_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_allowed_symbols.txt"
THRESHOLDS_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_thresholds.json"
TOKEN_PATH = PROJECT_ROOT / "old_system_reference" / "token.json"

SUPABASE_TABLE = "v2_daily_candles"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def clamp(value, low, high):
    return max(low, min(high, value))


def sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values, period):
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = []
    e = values[0]
    for v in values:
        e = (v * alpha) + (e * (1.0 - alpha))
        out.append(e)
    return out


def rsi(values, period=14):
    if len(values) <= period:
        return 50.0

    gains = []
    losses = []

    recent = values[-(period + 1):]
    for i in range(1, len(recent)):
        change = recent[i] - recent[i - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(candles, period=14):
    if len(candles) <= period:
        return 0.0

    recent = candles[-(period + 1):]
    trs = []

    for i in range(1, len(recent)):
        high = safe_float(recent[i].get("high"))
        low = safe_float(recent[i].get("low"))
        prev_close = safe_float(recent[i - 1].get("close"))

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        trs.append(tr)

    return sum(trs) / len(trs) if trs else 0.0


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_allowed_symbols():
    if not ALLOWED_PATH.exists():
        raise SystemExit(f"Missing allowed symbols file: {ALLOWED_PATH}")

    symbols = []
    seen = set()

    for line in ALLOWED_PATH.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip().upper()
        if s and s not in seen:
            seen.add(s)
            symbols.append(s)

    if not symbols:
        raise SystemExit("Allowed symbols file is empty.")

    return symbols



def load_percentile_thresholds():
    if not THRESHOLDS_PATH.exists():
        raise SystemExit(f"Missing percentile thresholds file: {THRESHOLDS_PATH}")

    payload = load_json(THRESHOLDS_PATH)
    symbols = payload.get("symbols", {})

    if not symbols:
        raise SystemExit("Percentile threshold file has no symbols.")

    return payload


def load_schwab_access_token():
    if not TOKEN_PATH.exists():
        raise SystemExit(f"Missing Schwab token file: {TOKEN_PATH}")

    token = load_json(TOKEN_PATH)
    access_token = token.get("access_token")

    if not access_token and isinstance(token.get("token"), dict):
        access_token = token["token"].get("access_token")

    if not access_token:
        raise SystemExit("No access_token found in old_system_reference/token.json")

    return access_token


def get_schwab_quotes(symbols):
    access_token = load_schwab_access_token()

    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
    }

    url = "https://api.schwabapi.com/marketdata/v1/quotes"

    r = requests.get(
        url,
        params={"symbols": ",".join(symbols)},
        headers=headers,
        timeout=60,
    )

    if r.status_code != 200:
        print("Schwab quote request failed.")
        print("HTTP status:", r.status_code)
        print(r.text[:1000])
        raise SystemExit("Schwab quotes failed. Reauthorize Schwab if status is 401.")

    return r.json()


def quote_last_price(quote_obj):
    if not isinstance(quote_obj, dict):
        return 0.0

    # Schwab quote objects vary depending on asset type and endpoint shape.
    for section in ["quote", "regular", "extended", "reference"]:
        obj = quote_obj.get(section)
        if isinstance(obj, dict):
            for key in ["lastPrice", "mark", "closePrice"]:
                v = safe_float(obj.get(key), 0.0)
                if v > 0:
                    return v

    for key in ["lastPrice", "mark", "closePrice"]:
        v = safe_float(quote_obj.get(key), 0.0)
        if v > 0:
            return v

    return 0.0


def supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    )

    if not url or not key:
        raise SystemExit("Missing Supabase URL/key in .env")

    return create_client(url, key)


def fetch_daily_candles(sb, symbol, limit=260):
    # Try datetime_ms first.
    try:
        result = (
            sb.table(SUPABASE_TABLE)
            .select("*")
            .eq("symbol", symbol)
            .order("datetime_ms", desc=True)
            .limit(limit * 2)
            .execute()
        )
        rows = result.data or []
    except Exception:
        result = (
            sb.table(SUPABASE_TABLE)
            .select("*")
            .eq("symbol", symbol)
            .order("date", desc=True)
            .limit(limit * 2)
            .execute()
        )
        rows = result.data or []

    # De-duplicate by date. Supabase may contain duplicate uploads.
    by_date = {}
    for row in rows:
        date = str(row.get("date") or "")
        if not date:
            ms = row.get("datetime_ms")
            if ms:
                try:
                    date = datetime.fromtimestamp(int(ms) / 1000).date().isoformat()
                except Exception:
                    date = ""
        if not date:
            continue
        by_date[date] = row

    clean = list(by_date.values())

    def sort_key(row):
        return str(row.get("date") or row.get("datetime") or row.get("datetime_ms") or "")

    clean.sort(key=sort_key)

    return clean[-limit:]


def build_latest_feature_row(symbol, candles):
    if len(candles) < 220:
        return None, f"too_few_candles: {len(candles)}"

    closes = [safe_float(c.get("close")) for c in candles]
    highs = [safe_float(c.get("high")) for c in candles]
    lows = [safe_float(c.get("low")) for c in candles]
    volumes = [safe_float(c.get("volume")) for c in candles]

    latest = candles[-1]
    prev = candles[-2]

    close = closes[-1]
    open_ = safe_float(latest.get("open"))
    high = safe_float(latest.get("high"))
    low = safe_float(latest.get("low"))
    volume = safe_float(latest.get("volume"))
    prev_close = closes[-2]

    if close <= 0 or open_ <= 0 or prev_close <= 0:
        return None, "bad_latest_price_data"

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    volume_sma20 = sma(volumes, 20)

    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    macd_line_series = [a - b for a, b in zip(ema12, ema26)]
    signal_series = ema_series(macd_line_series, 9)

    macd_line = macd_line_series[-1] if macd_line_series else 0.0
    macd_signal = signal_series[-1] if signal_series else 0.0
    macd_hist = macd_line - macd_signal

    atr14 = atr(candles, 14)

    high20 = max(highs[-20:])
    low20 = min(lows[-20:])
    high60 = max(highs[-60:])
    low60 = min(lows[-60:])

    def ret(period):
        if len(closes) <= period or closes[-period - 1] <= 0:
            return 0.0
        return ((close - closes[-period - 1]) / closes[-period - 1]) * 100.0

    row = {
        "symbol": symbol,
        "date": str(latest.get("date") or ""),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,

        "return_1d_pct": ret(1),
        "return_5d_pct": ret(5),
        "return_20d_pct": ret(20),
        "return_60d_pct": ret(60),

        "range_pct": ((high - low) / close) * 100.0 if close else 0.0,
        "body_pct": ((close - open_) / open_) * 100.0 if open_ else 0.0,
        "gap_pct": ((open_ - prev_close) / prev_close) * 100.0 if prev_close else 0.0,

        "volume_sma20": volume_sma20 or 0.0,
        "volume_ratio_20d": (volume / volume_sma20) if volume_sma20 else 0.0,

        "sma20": sma20 or 0.0,
        "sma50": sma50 or 0.0,
        "sma200": sma200 or 0.0,

        "close_vs_sma20_pct": ((close - sma20) / sma20) * 100.0 if sma20 else 0.0,
        "close_vs_sma50_pct": ((close - sma50) / sma50) * 100.0 if sma50 else 0.0,
        "close_vs_sma200_pct": ((close - sma200) / sma200) * 100.0 if sma200 else 0.0,

        "rsi14": rsi(closes, 14),
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,

        "atr14": atr14,
        "atr14_pct": (atr14 / close) * 100.0 if close else 0.0,

        "distance_from_20d_high_pct": ((close - high20) / high20) * 100.0 if high20 else 0.0,
        "distance_from_20d_low_pct": ((close - low20) / low20) * 100.0 if low20 else 0.0,
        "distance_from_60d_high_pct": ((close - high60) / high60) * 100.0 if high60 else 0.0,
        "distance_from_60d_low_pct": ((close - low60) / low60) * 100.0 if low60 else 0.0,
    }

    return row, "ok"


def zscore(values, scaler):
    means = scaler["mean"]
    stds = scaler["std"]
    return [(values[i] - means[i]) / stds[i] for i in range(len(values))]


def distance(a, b):
    total = 0.0
    for x, y in zip(a, b):
        d = x - y
        total += d * d
    return math.sqrt(total / max(len(a), 1))


def blend(a, b, weight_a):
    weight_b = 1.0 - weight_a
    return [(a[i] * weight_a) + (b[i] * weight_b) for i in range(len(a))]


def score_similarity(row, model):
    features = model["features"]
    scaler = model["scaler"]
    prototypes = model["prototypes"]
    symbol = row["symbol"]

    values = [safe_float(row.get(k), 0.0) for k in features]
    z = zscore(values, scaler)

    global_win = prototypes["global"]["win_centroid"]
    global_loss = prototypes["global"]["loss_centroid"]

    win_centroid = global_win
    loss_centroid = global_loss
    source = "global"

    sp = prototypes["symbols"].get(symbol)
    min_symbol_proto_rows = int(model.get("settings", {}).get("min_symbol_proto_rows", 30))

    if sp and sp.get("win_count", 0) >= min_symbol_proto_rows and sp.get("loss_count", 0) >= min_symbol_proto_rows:
        win_centroid = blend(sp["win_centroid"], global_win, 0.70)
        loss_centroid = blend(sp["loss_centroid"], global_loss, 0.70)
        source = "symbol_blended"

    d_win = distance(z, win_centroid)
    d_loss = distance(z, loss_centroid)
    edge = d_loss - d_win
    score = clamp(50.0 + edge * 18.0, 0.0, 100.0)

    return {
        "score": score,
        "edge": edge,
        "distance_to_winner": d_win,
        "distance_to_loser": d_loss,
        "prototype_source": source,
    }


def recompute_account(account, quotes):
    open_value = 0.0
    unrealized = 0.0

    for symbol, pos in account.get("open_positions", {}).items():
        q = quotes.get(symbol, {})
        last = quote_last_price(q)
        if last <= 0:
            last = safe_float(pos.get("last_price"), safe_float(pos.get("entry_price"), 0.0))

        shares = int(pos.get("shares") or 0)
        entry = safe_float(pos.get("entry_price"), 0.0)
        cost = safe_float(pos.get("cost"), entry * shares)

        value = last * shares
        pnl = value - cost

        pos["last_price"] = round(last, 4)
        pos["market_value"] = round(value, 2)
        pos["unrealized_pnl"] = round(pnl, 2)
        pos["unrealized_pnl_pct"] = round((pnl / cost) * 100.0, 4) if cost else 0.0
        pos["last_mark_time"] = now_iso()

        open_value += value
        unrealized += pnl

    cash = safe_float(account.get("cash"), 0.0)
    account_value = cash + open_value
    starting = safe_float(account.get("starting_balance"), 10000.0)
    realized = safe_float(account.get("realized_pnl"), 0.0)
    total_pnl = account_value - starting

    account["open_position_value"] = round(open_value, 2)
    account["unrealized_pnl"] = round(unrealized, 2)
    account["account_value"] = round(account_value, 2)
    account["total_pnl"] = round(total_pnl, 2)
    account["total_pnl_pct"] = round((total_pnl / starting) * 100.0, 4) if starting else 0.0
    account["updated_at"] = now_iso()


def main():
    if not ACCOUNT_PATH.exists():
        raise SystemExit("Missing sandbox account. Run init_similarity_engine_sandbox_account.py first.")

    if not MODEL_PATH.exists():
        raise SystemExit(f"Missing similarity model: {MODEL_PATH}")

    account = load_json(ACCOUNT_PATH)
    model = load_json(MODEL_PATH)
    allowed_symbols = read_allowed_symbols()
    threshold_payload = load_percentile_thresholds()
    percentile_thresholds = threshold_payload.get("symbols", {})

    if account.get("real_trading_enabled") is True:
        raise SystemExit("Safety stop: real_trading_enabled is True. Refusing to run.")

    if account.get("main_v2_buying_enabled") is True:
        raise SystemExit("Safety stop: main_v2_buying_enabled is True. Refusing to run.")

    default_score_threshold = safe_float(account.get("fallback_score_threshold"), 51.5)
    max_position_dollars = safe_float(account.get("max_position_dollars"), 500.0)
    max_open_positions = int(account.get("max_open_positions") or 9)
    min_hold_days = int(account.get("min_hold_days") or 20)

    open_positions = account.setdefault("open_positions", {})
    actions = account.setdefault("actions", [])

    print("Build:", BUILD)
    print("Allowed symbols:", ", ".join(allowed_symbols))
    print("Threshold mode: symbol-specific top10 percentile threshold")
    print("Max position dollars:", max_position_dollars)
    print("Max open positions:", max_open_positions)
    print("This is PAPER ONLY, percentile-calibrated, and does NOT touch main V2.")
    print("")

    sb = supabase_client()

    quotes = get_schwab_quotes(allowed_symbols)
    recompute_account(account, quotes)

    candidates = []

    for symbol in allowed_symbols:
        if symbol in open_positions:
            candidates.append({
                "symbol": symbol,
                "status": "SKIP_ALREADY_OPEN",
            })
            continue

        candles = fetch_daily_candles(sb, symbol, limit=260)
        feature_row, feature_status = build_latest_feature_row(symbol, candles)

        if feature_status != "ok":
            candidates.append({
                "symbol": symbol,
                "status": "SKIP_FEATURES",
                "reason": feature_status,
            })
            continue

        score_info = score_similarity(feature_row, model)
        score = score_info["score"]
        symbol_threshold_data = percentile_thresholds.get(symbol, {})
        symbol_threshold = safe_float(symbol_threshold_data.get("top10_score_threshold"), default_score_threshold)

        q = quotes.get(symbol, {})
        last_price = quote_last_price(q)

        if last_price <= 0:
            candidates.append({
                "symbol": symbol,
                "status": "SKIP_NO_QUOTE",
                "score": round(score, 4),
            })
            continue

        candidates.append({
            "symbol": symbol,
            "status": "CANDIDATE" if score >= symbol_threshold else "WATCH",
            "score": round(score, 4),
            "symbol_threshold": round(symbol_threshold, 6),
            "below_threshold": round(symbol_threshold - score, 6),
            "last_price": round(last_price, 4),
            "feature_date": feature_row.get("date"),
            "edge": round(score_info["edge"], 6),
            "prototype_source": score_info["prototype_source"],
        })

    # Highest score first.
    buyable = [
        c for c in candidates
        if c.get("status") == "CANDIDATE"
    ]
    buyable.sort(key=lambda x: x.get("score", 0), reverse=True)

    buys = []

    for c in buyable:
        if len(open_positions) >= max_open_positions:
            c["buy_result"] = "SKIP_MAX_OPEN_POSITIONS"
            continue

        cash = safe_float(account.get("cash"), 0.0)
        symbol = c["symbol"]
        price = safe_float(c.get("last_price"), 0.0)

        if price <= 0:
            c["buy_result"] = "SKIP_BAD_PRICE"
            continue

        shares = int(max_position_dollars // price)

        if shares < 1:
            c["buy_result"] = "SKIP_PRICE_ABOVE_MAX_POSITION"
            continue

        cost = round(shares * price, 2)

        if cost > cash:
            c["buy_result"] = "SKIP_NOT_ENOUGH_CASH"
            continue

        entry_time = now_iso()
        min_hold_until = (datetime.now() + timedelta(days=min_hold_days)).isoformat(timespec="seconds")

        position = {
            "symbol": symbol,
            "engine_id": "similarity_engine_sandbox",
            "side": "LONG",
            "shares": shares,
            "entry_price": round(price, 4),
            "last_price": round(price, 4),
            "cost": cost,
            "market_value": cost,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "entry_time": entry_time,
            "min_hold_days": min_hold_days,
            "min_hold_until": min_hold_until,
            "sell_lock": "LOCKED",
            "similarity_score": c.get("score"),
            "feature_date": c.get("feature_date"),
            "prototype_source": c.get("prototype_source"),
            "paper_only": True,
            "real_trade": False,
        }

        open_positions[symbol] = position
        account["cash"] = round(cash - cost, 2)

        action = {
            "time": entry_time,
            "action": "BUY_SIMILARITY_SANDBOX_PAPER",
            "symbol": symbol,
            "shares": shares,
            "price": round(price, 4),
            "cost": cost,
            "score": c.get("score"),
            "reason": "Similarity percentile sandbox score met symbol-specific threshold.",
            "paper_only": True,
            "real_trade": False,
        }

        actions.append(action)
        buys.append(action)
        c["buy_result"] = "BOUGHT"

    quotes_after = get_schwab_quotes(list(open_positions.keys()) or allowed_symbols)
    recompute_account(account, quotes_after)

    account["last_scan"] = {
        "time": now_iso(),
        "build": BUILD,
        "threshold_mode": "symbol_specific_top10_score_threshold",
        "thresholds_path": str(THRESHOLDS_PATH),
        "candidates": candidates,
        "buys": buys,
    }

    save_json(ACCOUNT_PATH, account)

    print("SCAN RESULTS")
    print("-" * 100)

    for c in candidates:
        print(
            c.get("symbol"),
            c.get("status"),
            "score=", c.get("score", ""),
            "threshold=", c.get("symbol_threshold", ""),
            "below=", c.get("below_threshold", ""),
            "last=", c.get("last_price", ""),
            "result=", c.get("buy_result", ""),
            "reason=", c.get("reason", ""),
        )

    print("")
    print("BUYS")
    print("-" * 100)
    if not buys:
        print("No paper buys this scan.")
    else:
        for b in buys:
            print(
                b["symbol"],
                "shares=", b["shares"],
                "price=", b["price"],
                "cost=", b["cost"],
                "score=", b["score"],
            )

    print("")
    print("ACCOUNT")
    print("-" * 100)
    print("Cash:          ${:,.2f}".format(account["cash"]))
    print("Open value:    ${:,.2f}".format(account["open_position_value"]))
    print("Account value: ${:,.2f}".format(account["account_value"]))
    print("Open positions:", len(account.get("open_positions", {})))
    print("")
    print("Account saved:", ACCOUNT_PATH)


if __name__ == "__main__":
    main()
