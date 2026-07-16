from __future__ import annotations

import argparse
import csv
import json
import math
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


BUILD = "ALIENTAI_V2_SCHWAB_OPTION_CHAIN_TESTER_V1"

PROJECT_ROOT = Path(__file__).resolve().parent
TOKEN_PATH = PROJECT_ROOT / "token.json"
OUT_DIR = PROJECT_ROOT / "data_v2" / "options_research"
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

    full_url = url + "?" + query

    req = urllib.request.Request(
        full_url,
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
    """
    Schwab option maps usually use keys like:
      2026-08-21:43
    where the part before ':' is expiration date.
    """
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

                # Basic research filter. We still save all rows, but mark pass/fail.
                research_pass = (
                    mark > 0
                    and mark <= max_contract_price
                    and spr <= max_spread_pct
                    and open_interest >= 1
                )

                score = 0.0

                if research_pass:
                    score += 30.0

                if open_interest > 0:
                    score += min(20.0, math.log10(open_interest + 1) * 6.0)

                if volume > 0:
                    score += min(15.0, math.log10(volume + 1) * 5.0)

                if spr < 10:
                    score += 15.0
                elif spr < 15:
                    score += 10.0
                elif spr < 25:
                    score += 4.0

                # Near-the-money preference.
                if underlying_price > 0:
                    moneyness_pct = ((strike - underlying_price) / underlying_price) * 100.0
                    if contract_type == "CALL" and -5.0 <= moneyness_pct <= 10.0:
                        score += 20.0
                    elif contract_type == "PUT" and -10.0 <= moneyness_pct <= 5.0:
                        score += 20.0
                else:
                    moneyness_pct = 0.0

                rows.append({
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
                    "research_score": round(score, 4),
                })

    rows.sort(
        key=lambda r: (
            bool(r.get("research_pass")),
            safe_float(r.get("research_score"), 0.0),
            -safe_float(r.get("spread_pct"), 999.0),
            safe_int(r.get("open_interest"), 0),
            safe_int(r.get("volume"), 0),
        ),
        reverse=True,
    )

    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "underlying_symbol",
        "underlying_price",
        "contract_type",
        "expiration",
        "dte",
        "strike",
        "option_symbol",
        "description",
        "bid",
        "ask",
        "mark",
        "spread_pct",
        "volume",
        "open_interest",
        "delta",
        "gamma",
        "theta",
        "vega",
        "implied_volatility",
        "intrinsic_value",
        "extrinsic_value",
        "moneyness_pct",
        "research_pass",
        "research_score",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--contract-type", default="CALL", choices=["CALL", "PUT"])
    parser.add_argument("--min-dte", type=int, default=14)
    parser.add_argument("--max-dte", type=int, default=45)
    parser.add_argument("--max-spread-pct", type=float, default=15.0)
    parser.add_argument("--max-contract-price", type=float, default=8.0)
    parser.add_argument("--strike-count", type=int, default=20)
    parser.add_argument("--include-quotes", action="store_true")
    args = parser.parse_args()

    symbol = args.symbol.upper().strip()
    contract_type = args.contract_type.upper().strip()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    from_date = date.today() + timedelta(days=args.min_dte)
    to_date = date.today() + timedelta(days=args.max_dte)

    params = {
        "symbol": symbol,
        "contractType": contract_type,
        "strikeCount": args.strike_count,
        "includeQuotes": "TRUE" if args.include_quotes else "FALSE",
        "strategy": "SINGLE",
        "fromDate": from_date.isoformat(),
        "toDate": to_date.isoformat(),
    }

    print(f"Build: {BUILD}")
    print(f"Symbol: {symbol}")
    print(f"Contract type: {contract_type}")
    print(f"DTE range: {args.min_dte} -> {args.max_dte}")
    print(f"Date range: {from_date.isoformat()} -> {to_date.isoformat()}")
    print(f"Max spread pct: {args.max_spread_pct}")
    print(f"Max contract price: {args.max_contract_price}")
    print("This does NOT trade. Research only.")
    print("")

    chain = schwab_get_json(SCHWAB_CHAIN_URL, params=params)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"{symbol}_{contract_type}_{timestamp}_raw.json"
    raw_path.write_text(json.dumps(chain, indent=2), encoding="utf-8")

    rows = parse_chain(
        chain=chain,
        contract_type=contract_type,
        min_dte=args.min_dte,
        max_dte=args.max_dte,
        max_spread_pct=args.max_spread_pct,
        max_contract_price=args.max_contract_price,
    )

    csv_path = PARSED_DIR / f"{symbol}_{contract_type}_{timestamp}_parsed.csv"
    write_csv(csv_path, rows)

    pass_rows = [r for r in rows if r.get("research_pass")]

    print("DONE")
    print(json.dumps({
        "status": "complete",
        "symbol": symbol,
        "contract_type": contract_type,
        "underlying_price": chain.get("underlyingPrice"),
        "raw_path": str(raw_path),
        "parsed_csv": str(csv_path),
        "contracts_parsed": len(rows),
        "research_pass": len(pass_rows),
    }, indent=2))

    print("")
    print("Top research contracts:")
    for row in rows[:15]:
        print({
            "option_symbol": row.get("option_symbol"),
            "expiration": row.get("expiration"),
            "dte": row.get("dte"),
            "strike": row.get("strike"),
            "mark": row.get("mark"),
            "spread_pct": row.get("spread_pct"),
            "volume": row.get("volume"),
            "open_interest": row.get("open_interest"),
            "delta": row.get("delta"),
            "research_pass": row.get("research_pass"),
            "research_score": row.get("research_score"),
        })


if __name__ == "__main__":
    main()
