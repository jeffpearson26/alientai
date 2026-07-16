from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


ENGINE_ID = "options_research"
BUILD = "ALIENTAI_V2_OPTIONS_RESEARCH_ENGINE_V1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOKEN_PATH = PROJECT_ROOT / "token.json"
DATA_DIR = PROJECT_ROOT / "data_v2"
OUT_DIR = DATA_DIR / "options_research"
RAW_DIR = OUT_DIR / "raw_chains"
PARSED_DIR = OUT_DIR / "parsed_chains"

SCHWAB_CHAIN_URL = "https://api.schwabapi.com/marketdata/v1/chains"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def load_token() -> Dict[str, Any]:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(f"Missing token file: {TOKEN_PATH}")

    token = json.loads(TOKEN_PATH.read_text(encoding="utf-8-sig"))

    if not isinstance(token, dict):
        raise RuntimeError("token.json did not contain a JSON object.")

    access_token = str(token.get("access_token") or "").strip()

    if not access_token:
        raise RuntimeError("token.json has no access_token. Refresh Schwab token first.")

    return token


def schwab_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    token = load_token()
    access_token = str(token.get("access_token") or "").strip()

    query = urllib.parse.urlencode({
        k: v
        for k, v in params.items()
        if v is not None and v != ""
    })

    req = urllib.request.Request(
        url + "?" + query,
        method="GET",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body)

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            raise RuntimeError("Schwab HTTP 401 unauthorized. Refresh Schwab token first.") from exc
        raise RuntimeError(f"Schwab HTTP {exc.code}: {body[:1000]}") from exc


def date_key_to_date(exp_key: str) -> Optional[date]:
    try:
        main = str(exp_key).split(":", 1)[0]
        return datetime.strptime(main, "%Y-%m-%d").date()
    except Exception:
        return None


def contract_symbol(contract: Dict[str, Any]) -> str:
    for key in ["symbol", "optionSymbol", "putCallSymbol"]:
        value = contract.get(key)
        if value:
            return str(value)
    return ""


def contract_mark(contract: Dict[str, Any]) -> float:
    mark = safe_float(contract.get("mark"), 0.0)
    if mark > 0:
        return mark

    bid = safe_float(contract.get("bid"), 0.0)
    ask = safe_float(contract.get("ask"), 0.0)

    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0

    return max(bid, ask, 0.0)


def spread_pct(contract: Dict[str, Any]) -> float:
    bid = safe_float(contract.get("bid"), 0.0)
    ask = safe_float(contract.get("ask"), 0.0)
    mark = contract_mark(contract)

    if bid <= 0 or ask <= 0 or mark <= 0:
        return 999.0

    return ((ask - bid) / mark) * 100.0


def intrinsic_value(contract_type: str, underlying_price: float, strike: float) -> float:
    if contract_type.upper() == "CALL":
        return max(0.0, underlying_price - strike)
    return max(0.0, strike - underlying_price)


def option_score(row: Dict[str, Any]) -> float:
    score = 0.0

    spread = safe_float(row.get("spread_pct"), 999.0)
    open_interest = safe_int(row.get("open_interest"), 0)
    volume = safe_int(row.get("volume"), 0)
    delta = abs(safe_float(row.get("delta"), 0.0))
    moneyness = safe_float(row.get("moneyness_pct"), 0.0)
    dte = safe_int(row.get("dte"), 0)
    mark = safe_float(row.get("mark"), 0.0)

    if spread <= 5:
        score += 20
    elif spread <= 10:
        score += 15
    elif spread <= 15:
        score += 10
    elif spread <= 20:
        score += 5

    if open_interest > 0:
        score += min(20.0, math.log10(open_interest + 1) * 5.0)

    if volume > 0:
        score += min(10.0, math.log10(volume + 1) * 4.0)

    # Prefer useful long-call deltas, not lottery tickets and not too stock-like.
    if 0.40 <= delta <= 0.65:
        score += 20
    elif 0.30 <= delta < 0.40:
        score += 12
    elif 0.65 < delta <= 0.75:
        score += 8

    # Prefer near-the-money to slightly OTM calls.
    if -3 <= moneyness <= 8:
        score += 15
    elif -8 <= moneyness <= 12:
        score += 8

    # Prefer enough time, but not too far out for first research.
    if 21 <= dte <= 45:
        score += 10
    elif 14 <= dte < 21:
        score += 6

    # Prefer contracts that fit a paper research account.
    estimated_cost = mark * 100.0
    if estimated_cost <= 250:
        score += 10
    elif estimated_cost <= 500:
        score += 6
    elif estimated_cost <= 800:
        score += 3

    return round(score, 4)


def parse_chain(
    chain: Dict[str, Any],
    contract_type: str,
    min_dte: int,
    max_dte: int,
    max_spread_pct: float,
    max_contract_price: float,
) -> List[Dict[str, Any]]:
    contract_type = contract_type.upper()

    underlying_price = safe_float(
        chain.get("underlyingPrice")
        or chain.get("underlying", {}).get("last")
        or chain.get("underlying", {}).get("mark")
        or chain.get("underlying", {}).get("close")
        or 0.0,
        0.0,
    )

    if contract_type == "CALL":
        exp_map = chain.get("callExpDateMap") or {}
    else:
        exp_map = chain.get("putExpDateMap") or {}

    today = date.today()
    rows: List[Dict[str, Any]] = []

    if not isinstance(exp_map, dict):
        return rows

    for exp_key, strike_map in exp_map.items():
        exp_date = date_key_to_date(exp_key)
        if not exp_date:
            continue

        dte = (exp_date - today).days

        if dte < min_dte or dte > max_dte:
            continue

        if not isinstance(strike_map, dict):
            continue

        for strike_key, contracts in strike_map.items():
            strike = safe_float(strike_key, 0.0)

            if not isinstance(contracts, list):
                continue

            for contract in contracts:
                if not isinstance(contract, dict):
                    continue

                bid = safe_float(contract.get("bid"), 0.0)
                ask = safe_float(contract.get("ask"), 0.0)
                mark = contract_mark(contract)
                spr = spread_pct(contract)
                volume = safe_int(contract.get("totalVolume") or contract.get("volume"), 0)
                open_interest = safe_int(contract.get("openInterest"), 0)
                delta = safe_float(contract.get("delta"), 0.0)
                gamma = safe_float(contract.get("gamma"), 0.0)
                theta = safe_float(contract.get("theta"), 0.0)
                vega = safe_float(contract.get("vega"), 0.0)
                implied_vol = safe_float(contract.get("volatility") or contract.get("impliedVolatility"), 0.0)

                intrinsic = intrinsic_value(contract_type, underlying_price, strike)
                extrinsic = max(0.0, mark - intrinsic)

                if underlying_price > 0:
                    moneyness_pct = ((strike - underlying_price) / underlying_price) * 100.0
                else:
                    moneyness_pct = 0.0

                research_pass = (
                    mark > 0
                    and mark <= max_contract_price
                    and spr <= max_spread_pct
                    and open_interest >= 1
                )

                row = {
                    "engine_id": ENGINE_ID,
                    "underlying_symbol": str(chain.get("symbol") or "").upper(),
                    "underlying_price": round(underlying_price, 4),
                    "contract_type": contract_type,
                    "expiration": exp_date.isoformat(),
                    "dte": dte,
                    "strike": strike,
                    "option_symbol": contract_symbol(contract),
                    "description": contract.get("description"),
                    "bid": bid,
                    "ask": ask,
                    "mark": round(mark, 4),
                    "estimated_contract_cost": round(mark * 100.0, 2),
                    "spread_pct": round(spr, 4),
                    "volume": volume,
                    "open_interest": open_interest,
                    "delta": delta,
                    "gamma": gamma,
                    "theta": theta,
                    "vega": vega,
                    "implied_volatility": implied_vol,
                    "intrinsic_value": round(intrinsic, 4),
                    "extrinsic_value": round(extrinsic, 4),
                    "moneyness_pct": round(moneyness_pct, 4),
                    "research_pass": research_pass,
                }

                row["research_score"] = option_score(row)
                rows.append(row)

    rows.sort(key=lambda r: safe_float(r.get("research_score"), 0.0), reverse=True)
    return rows


def fetch_chain(symbol: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    contract_type = str(settings.get("options_research_contract_type", "CALL")).upper()
    min_dte = safe_int(settings.get("options_research_min_dte"), 14)
    max_dte = safe_int(settings.get("options_research_max_dte"), 45)

    from_date = date.today() + timedelta(days=min_dte)
    to_date = date.today() + timedelta(days=max_dte)

    params = {
        "symbol": symbol.upper().strip(),
        "contractType": contract_type,
        "strikeCount": safe_int(settings.get("options_research_strike_count"), 20),
        "includeQuotes": "FALSE",
        "strategy": "SINGLE",
        "fromDate": from_date.isoformat(),
        "toDate": to_date.isoformat(),
    }

    return schwab_get_json(SCHWAB_CHAIN_URL, params=params)


def selected_underlyings(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[str]:
    configured = settings.get("options_research_symbols")

    if isinstance(configured, list) and configured:
        symbols = [str(s).upper().strip() for s in configured if str(s).strip()]
    else:
        # Good starter basket from our tests.
        symbols = ["MARA", "RIVN", "PLTR", "SOXL"]

    max_symbols = safe_int(settings.get("options_research_max_symbols_per_scan"), 4)
    symbols = list(dict.fromkeys(symbols))

    if max_symbols > 0:
        symbols = symbols[:max_symbols]

    return symbols


def scan(quotes: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not bool(settings.get("options_research_enabled", False)):
        return []

    contract_type = str(settings.get("options_research_contract_type", "CALL")).upper()
    min_dte = safe_int(settings.get("options_research_min_dte"), 14)
    max_dte = safe_int(settings.get("options_research_max_dte"), 45)
    max_spread_pct = safe_float(settings.get("options_research_max_spread_pct"), 20.0)
    max_contract_price = safe_float(settings.get("options_research_max_contract_price"), 8.0)
    max_contracts_per_symbol = safe_int(settings.get("options_research_max_contracts_per_symbol"), 3)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    output_rows: List[Dict[str, Any]] = []

    for symbol in selected_underlyings(quotes, settings):
        try:
            chain = fetch_chain(symbol, settings)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_path = RAW_DIR / f"{symbol}_{contract_type}_{timestamp}_engine_raw.json"
            raw_path.write_text(json.dumps(chain, indent=2), encoding="utf-8")

            rows = parse_chain(
                chain=chain,
                contract_type=contract_type,
                min_dte=min_dte,
                max_dte=max_dte,
                max_spread_pct=max_spread_pct,
                max_contract_price=max_contract_price,
            )

            pass_rows = [r for r in rows if r.get("research_pass")]
            best_rows = pass_rows[:max_contracts_per_symbol] if pass_rows else rows[:max_contracts_per_symbol]

            for row in best_rows:
                decision = "OPTIONS_RESEARCH_PASS" if row.get("research_pass") else "OPTIONS_RESEARCH_WATCH"

                # Make rows compatible with V2 candidate tables.
                row["symbol"] = row.get("underlying_symbol")
                row["option_contract_symbol"] = row.get("option_symbol")
                row["decision"] = decision
                row["score"] = row.get("research_score")
                row["price"] = row.get("mark")
                row["source"] = ENGINE_ID
                row["side"] = "LONG_CALL"
                row["reason"] = (
                    f"Options research only. {row.get('contract_type')} "
                    f"{row.get('expiration')} strike {row.get('strike')} "
                    f"mark {row.get('mark')} spread {row.get('spread_pct')}% "
                    f"OI {row.get('open_interest')} delta {row.get('delta')}."
                )
                row["paper_trade_allowed"] = False
                row["live_trade_allowed"] = False
                row["research_only"] = True

                output_rows.append(row)

        except Exception as exc:
            output_rows.append({
                "engine_id": ENGINE_ID,
                "symbol": symbol,
                "decision": "OPTIONS_RESEARCH_ERROR",
                "score": 0.0,
                "price": 0.0,
                "source": ENGINE_ID,
                "side": "LONG_CALL",
                "reason": f"Options research error for {symbol}: {exc}",
                "paper_trade_allowed": False,
                "live_trade_allowed": False,
                "research_only": True,
            })

    output_rows.sort(key=lambda r: safe_float(r.get("score"), 0.0), reverse=True)
    return output_rows
