from __future__ import annotations

"""Archive compact macroeconomic and commodity regime series from Alpha Vantage."""

import argparse
import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from alpha_vantage_http import get_alpha_vantage_response, redact_sensitive_text


ROOT = Path(__file__).resolve().parent


def requests_to_archive() -> List[Tuple[str, Dict[str, str]]]:
    requests_: List[Tuple[str, Dict[str, str]]] = [
        ("real_gdp_quarterly", {"function": "REAL_GDP", "interval": "quarterly"}),
        ("real_gdp_per_capita", {"function": "REAL_GDP_PER_CAPITA"}),
        ("federal_funds_rate_daily", {"function": "FEDERAL_FUNDS_RATE", "interval": "daily"}),
        ("cpi_monthly", {"function": "CPI", "interval": "monthly"}),
        ("inflation_annual", {"function": "INFLATION"}),
        ("retail_sales_monthly", {"function": "RETAIL_SALES"}),
        ("durable_goods_monthly", {"function": "DURABLES"}),
        ("unemployment_monthly", {"function": "UNEMPLOYMENT"}),
        ("nonfarm_payroll_monthly", {"function": "NONFARM_PAYROLL"}),
    ]
    for maturity in ("3month", "2year", "5year", "7year", "10year", "30year"):
        requests_.append((
            f"treasury_yield_{maturity}_daily",
            {"function": "TREASURY_YIELD", "interval": "daily", "maturity": maturity},
        ))
    for function in (
        "WTI", "BRENT", "NATURAL_GAS", "COPPER", "ALUMINUM", "WHEAT", "CORN",
        "COTTON", "SUGAR", "COFFEE", "ALL_COMMODITIES",
    ):
        requests_.append((function.casefold() + "_monthly", {"function": function, "interval": "monthly"}))
    return requests_


def safe_message(value: Any, api_key: str) -> str:
    return redact_sensitive_text(value or "request failed", api_key)


def fetch(params: Dict[str, str], api_key: str) -> bytes:
    response = get_alpha_vantage_response(params, api_key, timeout=90)
    content = response.content
    if not content.strip():
        raise ValueError("empty Alpha Vantage response")
    payload = response.json()
    message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if message:
        raise RuntimeError(message)
    return content


def write_gzip(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as handle:
        handle.write(content)
    temporary.replace(path)


def run(output: Path, api_key: str) -> Dict[str, Any]:
    collected_at = datetime.now(timezone.utc)
    day = collected_at.date().isoformat()
    manifest: Dict[str, Any] = {
        "status": "complete", "collected_at_utc": collected_at.isoformat(), "files": [],
    }
    for name, params in requests_to_archive():
        content = fetch(params, api_key)
        destination = output / day / f"{name}.json.gz"
        write_gzip(destination, content)
        manifest["files"].append({
            "name": name,
            "parameters": params,
            "path": str(destination),
            "bytes_uncompressed": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
        print(f"DONE {name}: {len(content)} bytes", flush=True)
    manifest_path = output / day / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = str(os.getenv("ALPHA_VANTAGE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY is required")
    try:
        result = run(args.output, api_key)
    except Exception as exc:
        raise RuntimeError(safe_message(exc, api_key)) from exc
    print(json.dumps({"status": result["status"], "files": len(result["files"])}, indent=2))


if __name__ == "__main__":
    main()
