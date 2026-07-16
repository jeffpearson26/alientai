from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


BUILD = "ALIENTAI_V2_MARK_OPEN_OPTIONS_FROM_SCHWAB_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
ACCOUNT_PATH = PROJECT_ROOT / "data_v2" / "v2_options_paper_account.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"

SCHWAB_CHAIN_URL = "https://api.schwabapi.com/marketdata/v1/chains"


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def normalize_contract(value: Any) -> str:
    return " ".join(str(value or "").upper().strip().split())


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} did not contain a JSON object.")
    return data


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_access_token() -> str:
    token = load_json(TOKEN_PATH)
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("token.json does not contain access_token. Refresh Schwab token first.")
    return str(access_token)


def schwab_get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    access_token = get_access_token()

    clean_params = {
        k: v for k, v in params.items()
        if v is not None and v != ""
    }

    full_url = url + "?" + urllib.parse.urlencode(clean_params)

    req = urllib.request.Request(
        full_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError("Schwab HTTP 401 unauthorized. Refresh Schwab token first.") from exc
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Schwab HTTP {exc.code}: {body[:1000]}") from exc


def flatten_chain(chain: Dict[str, Any], contract_type: str) -> List[Dict[str, Any]]:
    contract_type = contract_type.upper().strip()

    if contract_type == "PUT":
        maps = [chain.get("putExpDateMap", {})]
    else:
        maps = [chain.get("callExpDateMap", {})]

    out: List[Dict[str, Any]] = []

    for exp_map in maps:
        if not isinstance(exp_map, dict):
            continue

        for exp_key, strikes in exp_map.items():
            if not isinstance(strikes, dict):
                continue

            expiration = str(exp_key).split(":", 1)[0]
            dte = None
            if ":" in str(exp_key):
                try:
                    dte = int(str(exp_key).split(":", 1)[1])
                except Exception:
                    dte = None

            for strike_key, contracts in strikes.items():
                if not isinstance(contracts, list):
                    continue

                for c in contracts:
                    if not isinstance(c, dict):
                        continue

                    row = dict(c)
                    row["expiration"] = expiration
                    row["dte"] = dte
                    row["strike"] = safe_float(row.get("strikePrice") or strike_key, 0.0)

                    symbol = (
                        row.get("symbol")
                        or row.get("optionSymbol")
                        or row.get("option_symbol")
                    )
                    row["option_contract_symbol"] = symbol

                    bid = safe_float(row.get("bid"), 0.0)
                    ask = safe_float(row.get("ask"), 0.0)
                    mark = safe_float(row.get("mark"), 0.0)

                    if mark <= 0 and bid > 0 and ask > 0:
                        mark = round((bid + ask) / 2.0, 4)

                    row["mark"] = mark
                    out.append(row)

    return out


def fetch_chain_for_underlying(symbol: str, contract_type: str, from_date: str = "", to_date: str = "") -> List[Dict[str, Any]]:
    params = {
        "symbol": symbol,
        "contractType": contract_type.upper(),
        "strikeCount": 200,
        "includeQuotes": "TRUE",
        "strategy": "SINGLE",
    }

    if from_date:
        params["fromDate"] = from_date
    if to_date:
        params["toDate"] = to_date

    chain = schwab_get_json(SCHWAB_CHAIN_URL, params)
    return flatten_chain(chain, contract_type)


def mark_account() -> Dict[str, Any]:
    account = load_json(ACCOUNT_PATH)
    open_positions = account.get("open_option_positions", {})

    if not isinstance(open_positions, dict):
        raise RuntimeError("open_option_positions is not a dictionary.")

    updated_positions = 0
    not_found = []

    # Fetch each underlying once.
    underlyings = sorted({
        str(pos.get("underlying_symbol") or "").upper().strip()
        for pos in open_positions.values()
        if isinstance(pos, dict) and str(pos.get("underlying_symbol") or "").strip()
    })

    chain_rows_by_underlying: Dict[str, List[Dict[str, Any]]] = {}

    for underlying in underlyings:
        # Most of our research currently uses CALLs.
        chain_rows_by_underlying[underlying] = fetch_chain_for_underlying(underlying, "CALL")

    for pos_key, pos in open_positions.items():
        if not isinstance(pos, dict):
            continue

        underlying = str(pos.get("underlying_symbol") or "").upper().strip()
        contract_type = str(pos.get("contract_type") or "CALL").upper().strip()
        wanted_contract = normalize_contract(pos.get("option_contract_symbol") or pos_key)

        rows = chain_rows_by_underlying.get(underlying, [])

        match: Optional[Dict[str, Any]] = None
        for row in rows:
            row_contract = normalize_contract(
                row.get("option_contract_symbol")
                or row.get("symbol")
                or row.get("optionSymbol")
            )
            if row_contract == wanted_contract:
                match = row
                break

        if not match:
            not_found.append(wanted_contract)
            continue

        mark = safe_float(match.get("mark"), 0.0)
        bid = safe_float(match.get("bid"), 0.0)
        ask = safe_float(match.get("ask"), 0.0)

        if mark <= 0 and bid > 0 and ask > 0:
            mark = round((bid + ask) / 2.0, 4)

        if mark <= 0:
            not_found.append(wanted_contract)
            continue

        contracts = int(safe_float(pos.get("contracts"), 0))
        entry_cost = safe_float(pos.get("entry_cost"), 0.0)

        last_value = round(mark * 100.0 * contracts, 2)
        unrealized_pnl = round(last_value - entry_cost, 2)
        unrealized_pnl_pct = round((unrealized_pnl / entry_cost * 100.0), 4) if entry_cost > 0 else 0.0

        pos["last_mark"] = round(mark, 4)
        pos["last_value"] = last_value
        pos["unrealized_pnl"] = unrealized_pnl
        pos["unrealized_pnl_pct"] = unrealized_pnl_pct
        pos["last_mark_source"] = "schwab_option_chain"
        pos["last_mark_time"] = now_iso()
        pos["last_update"] = now_iso()

        pos["current_bid"] = bid
        pos["current_ask"] = ask
        pos["current_delta"] = safe_float(match.get("delta"), safe_float(pos.get("current_delta"), 0.0))
        pos["current_spread_pct"] = (
            round(((ask - bid) / ((ask + bid) / 2.0)) * 100.0, 4)
            if ask > 0 and bid > 0 and ask >= bid
            else safe_float(pos.get("current_spread_pct"), 0.0)
        )
        pos["current_open_interest"] = safe_float(match.get("openInterest"), safe_float(pos.get("open_interest_at_entry"), 0.0))
        pos["current_volume"] = safe_float(match.get("totalVolume") or match.get("volume"), 0.0)

        updated_positions += 1

    open_value = 0.0
    unrealized_total = 0.0

    for pos in open_positions.values():
        if not isinstance(pos, dict):
            continue
        open_value += safe_float(pos.get("last_value"), safe_float(pos.get("entry_cost"), 0.0))
        unrealized_total += safe_float(pos.get("unrealized_pnl"), 0.0)

    cash = safe_float(account.get("cash"), 0.0)
    realized = safe_float(account.get("realized_pnl"), 0.0)
    starting_balance = safe_float(account.get("starting_balance"), 1000.0)

    account["open_option_value"] = round(open_value, 2)
    account["unrealized_pnl"] = round(unrealized_total, 2)
    account["account_value"] = round(cash + open_value, 2)
    account["total_pnl"] = round(realized + unrealized_total, 2)
    account["total_pnl_pct"] = round((account["total_pnl"] / starting_balance * 100.0), 4) if starting_balance > 0 else 0.0
    account["updated_at"] = now_iso()

    save_json(ACCOUNT_PATH, account)

    return {
        "status": "success",
        "build": BUILD,
        "account_path": str(ACCOUNT_PATH),
        "underlyings_checked": underlyings,
        "open_positions": len(open_positions),
        "updated_positions": updated_positions,
        "not_found": not_found,
        "open_option_value": account["open_option_value"],
        "unrealized_pnl": account["unrealized_pnl"],
        "account_value": account["account_value"],
        "total_pnl": account["total_pnl"],
        "total_pnl_pct": account["total_pnl_pct"],
    }


def main() -> None:
    load_dotenv()
    result = mark_account()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
