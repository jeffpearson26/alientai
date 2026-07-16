import json
from pathlib import Path
from datetime import datetime

BUILD = "ALIENTAI_V2_ENGINE_ACCOUNTS_V1"

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data_v2"
OUT_DIR = DATA_DIR / "engine_accounts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAIN_ACCOUNT_PATH = DATA_DIR / "v2_paper_account.json"
SUMMARY_PATH = OUT_DIR / "engine_accounts_summary.json"

DEFAULT_ENGINE_STARTING_BALANCE = 10000.0

KNOWN_ENGINES = [
    "prediction_friday",
    "prediction_20day",
    "momentum_5min",
    "similarity_engine",
    "transformer_20day",
    "options_research",
    "unknown_engine",
]


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def normalize_engine_id(value):
    engine = str(value or "").strip()
    if not engine:
        return "unknown_engine"
    return engine


def infer_engine_id_from_row(row):
    """
    Better engine attribution for old positions/trades that were saved before
    every paper position had a clean engine_id.

    Rules:
    - Explicit engine_id wins.
    - Known strategy source wins.
    - Blank engine + 20-day horizon -> prediction_20day.
    - Blank engine + 5-day horizon -> prediction_friday.
    - Blank engine + 1-day horizon -> similarity_engine.
    - Build/app runner labels are not real engines unless no better clue exists.
    """
    explicit = str(row.get("engine_id") or row.get("engine") or "").strip()
    if explicit:
        return explicit

    source = str(row.get("source") or "").strip()

    known_sources = {
        "prediction_friday",
        "prediction_20day",
        "momentum_5min",
        "similarity_engine",
        "transformer_20day",
        "options_research",
    }

    if source in known_sources:
        return source

    horizon = safe_float(
        row.get("prediction_horizon_days")
        or row.get("horizon_days")
        or row.get("prediction_days"),
        0.0,
    )

    min_hold = safe_float(row.get("minimum_hold_minutes") or row.get("min_hold_minutes"), 0.0)

    # 20 trading days in the current V2 system is stored as 28800 minutes.
    if abs(horizon - 20.0) < 0.01 or min_hold >= 20000:
        return "prediction_20day"

    if abs(horizon - 5.0) < 0.01:
        return "prediction_friday"

    if abs(horizon - 1.0) < 0.01:
        return "similarity_engine"

    if source and not source.startswith("ALIENTAI_V2_PAPER_ENGINE_DIRECT_RUNNER"):
        return source

    return "unknown_engine"


def normalize_positions(raw_positions):
    """
    Supports both common shapes:
    1. open_positions is a dict: {"AAPL": {...}}
    2. open_positions is a list: [{...}, {...}]
    """
    if isinstance(raw_positions, dict):
        output = []
        for symbol, pos in raw_positions.items():
            if isinstance(pos, dict):
                row = dict(pos)
                row.setdefault("symbol", symbol)
                output.append(row)
        return output

    if isinstance(raw_positions, list):
        return [p for p in raw_positions if isinstance(p, dict)]

    return []


def normalize_closed_trades(raw_trades):
    if isinstance(raw_trades, list):
        return [t for t in raw_trades if isinstance(t, dict)]
    return []


def position_market_value(pos):
    shares = safe_float(pos.get("shares"), 0.0)
    last = safe_float(
        pos.get("last_price")
        or pos.get("last")
        or pos.get("price")
        or pos.get("current_price")
        or pos.get("entry_price"),
        0.0,
    )
    return round(shares * last, 4)


def position_cost(pos):
    explicit_cost = pos.get("cost")
    if explicit_cost is not None:
        return safe_float(explicit_cost, 0.0)

    shares = safe_float(pos.get("shares"), 0.0)
    entry = safe_float(pos.get("entry_price") or pos.get("entry") or pos.get("avg_entry_price"), 0.0)
    return round(shares * entry, 4)


def position_unrealized_pnl(pos):
    if pos.get("unrealized_pnl") is not None:
        return safe_float(pos.get("unrealized_pnl"), 0.0)

    return round(position_market_value(pos) - position_cost(pos), 4)


def trade_pnl(trade):
    return safe_float(trade.get("pnl") or trade.get("profit") or trade.get("realized_pnl"), 0.0)


def build_engine_accounts():
    main_account = load_json(MAIN_ACCOUNT_PATH, {})

    raw_open_positions = (
        main_account.get("open_positions")
        or main_account.get("positions")
        or main_account.get("open")
        or {}
    )

    raw_closed_trades = (
        main_account.get("closed_trades")
        or main_account.get("trades")
        or main_account.get("closed")
        or []
    )

    open_positions = normalize_positions(raw_open_positions)
    closed_trades = normalize_closed_trades(raw_closed_trades)

    engine_accounts = {}

    for engine in KNOWN_ENGINES:
        engine_accounts[engine] = {
            "build": BUILD,
            "engine_id": engine,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "starting_balance": DEFAULT_ENGINE_STARTING_BALANCE,
            "cash": DEFAULT_ENGINE_STARTING_BALANCE,
            "open_positions": [],
            "closed_trades": [],
            "open_position_value": 0.0,
            "open_position_cost": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "account_value": DEFAULT_ENGINE_STARTING_BALANCE,
            "total_pnl": 0.0,
            "total_pnl_pct": 0.0,
            "open_positions_count": 0,
            "closed_trades_count": 0,
            "winning_closed_trades": 0,
            "losing_closed_trades": 0,
            "closed_win_rate_pct": 0.0,
            "average_closed_win": 0.0,
            "average_closed_loss": 0.0,
            "profit_factor": None,
            "note": "Research-only reconstructed engine account from shared V2 paper account. This does not place trades.",
        }

    # Put current open positions into their engine buckets.
    for pos in open_positions:
        engine = infer_engine_id_from_row(pos)
        if engine not in engine_accounts:
            engine_accounts[engine] = {
                "build": BUILD,
                "engine_id": engine,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "starting_balance": DEFAULT_ENGINE_STARTING_BALANCE,
                "cash": DEFAULT_ENGINE_STARTING_BALANCE,
                "open_positions": [],
                "closed_trades": [],
                "open_position_value": 0.0,
                "open_position_cost": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "account_value": DEFAULT_ENGINE_STARTING_BALANCE,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "open_positions_count": 0,
                "closed_trades_count": 0,
                "winning_closed_trades": 0,
                "losing_closed_trades": 0,
                "closed_win_rate_pct": 0.0,
                "average_closed_win": 0.0,
                "average_closed_loss": 0.0,
                "profit_factor": None,
                "note": "Research-only reconstructed engine account from shared V2 paper account. This does not place trades.",
            }

        enriched = dict(pos)
        enriched["engine_account_value"] = position_market_value(pos)
        enriched["engine_account_cost"] = position_cost(pos)
        enriched["engine_account_unrealized_pnl"] = position_unrealized_pnl(pos)

        engine_accounts[engine]["open_positions"].append(enriched)

    # Put closed trades into their engine buckets.
    for trade in closed_trades:
        engine = infer_engine_id_from_row(trade)
        if engine not in engine_accounts:
            engine_accounts[engine] = {
                "build": BUILD,
                "engine_id": engine,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "starting_balance": DEFAULT_ENGINE_STARTING_BALANCE,
                "cash": DEFAULT_ENGINE_STARTING_BALANCE,
                "open_positions": [],
                "closed_trades": [],
                "open_position_value": 0.0,
                "open_position_cost": 0.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "account_value": DEFAULT_ENGINE_STARTING_BALANCE,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "open_positions_count": 0,
                "closed_trades_count": 0,
                "winning_closed_trades": 0,
                "losing_closed_trades": 0,
                "closed_win_rate_pct": 0.0,
                "average_closed_win": 0.0,
                "average_closed_loss": 0.0,
                "profit_factor": None,
                "note": "Research-only reconstructed engine account from shared V2 paper account. This does not place trades.",
            }

        engine_accounts[engine]["closed_trades"].append(dict(trade))

    # Calculate stats.
    summary_rows = []

    for engine, acct in engine_accounts.items():
        open_value = sum(position_market_value(p) for p in acct["open_positions"])
        open_cost = sum(position_cost(p) for p in acct["open_positions"])
        unrealized = sum(position_unrealized_pnl(p) for p in acct["open_positions"])
        realized = sum(trade_pnl(t) for t in acct["closed_trades"])

        closed_pnls = [trade_pnl(t) for t in acct["closed_trades"]]
        wins = [x for x in closed_pnls if x > 0]
        losses = [x for x in closed_pnls if x < 0]

        gross_win = sum(wins)
        gross_loss = abs(sum(losses))

        acct["open_position_value"] = round(open_value, 4)
        acct["open_position_cost"] = round(open_cost, 4)
        acct["unrealized_pnl"] = round(unrealized, 4)
        acct["realized_pnl"] = round(realized, 4)

        # This is a reconstructed research account.
        # We treat open position cost as committed capital and leave the rest as simulated cash.
        acct["cash"] = round(DEFAULT_ENGINE_STARTING_BALANCE - open_cost + realized, 4)
        acct["account_value"] = round(acct["cash"] + open_value, 4)
        acct["total_pnl"] = round(acct["account_value"] - DEFAULT_ENGINE_STARTING_BALANCE, 4)
        acct["total_pnl_pct"] = round((acct["total_pnl"] / DEFAULT_ENGINE_STARTING_BALANCE) * 100.0, 4)

        acct["open_positions_count"] = len(acct["open_positions"])
        acct["closed_trades_count"] = len(acct["closed_trades"])
        acct["winning_closed_trades"] = len(wins)
        acct["losing_closed_trades"] = len(losses)
        acct["closed_win_rate_pct"] = round((len(wins) / len(closed_pnls)) * 100.0, 4) if closed_pnls else 0.0
        acct["average_closed_win"] = round(gross_win / len(wins), 4) if wins else 0.0
        acct["average_closed_loss"] = round(sum(losses) / len(losses), 4) if losses else 0.0
        acct["profit_factor"] = round(gross_win / gross_loss, 4) if gross_loss else None

        out_path = OUT_DIR / f"{engine}_account.json"
        out_path.write_text(json.dumps(acct, indent=2), encoding="utf-8")

        summary_rows.append({
            "engine_id": engine,
            "account_value": acct["account_value"],
            "total_pnl": acct["total_pnl"],
            "total_pnl_pct": acct["total_pnl_pct"],
            "realized_pnl": acct["realized_pnl"],
            "unrealized_pnl": acct["unrealized_pnl"],
            "open_positions_count": acct["open_positions_count"],
            "closed_trades_count": acct["closed_trades_count"],
            "closed_win_rate_pct": acct["closed_win_rate_pct"],
            "profit_factor": acct["profit_factor"],
        })

    summary_rows.sort(key=lambda r: safe_float(r.get("total_pnl_pct")), reverse=True)

    summary = {
        "build": BUILD,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_account": str(MAIN_ACCOUNT_PATH),
        "engine_count": len(summary_rows),
        "engines": summary_rows,
        "note": "Research-only engine account reconstruction. Existing shared V2 paper account is unchanged.",
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


def main():
    build_engine_accounts()


if __name__ == "__main__":
    main()
