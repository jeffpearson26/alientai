from __future__ import annotations

"""Audit the exact source subset for the frozen AI/semiconductor H05 setup model."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from alientai_v2.research.ai_semiconductor_setup_barrier_h05 import load_rows


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_CONTRACT_20260825.json"
DEFAULT_OUTPUT = ROOT / "AI_SEMICONDUCTOR_SETUP_BARRIER_H05_SOURCE_AUDIT_20260825.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def audit(contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source = resolve(str(contract["source_archive"]))
    manifest_path = source / "manifest.json"
    universe_path = resolve(str(contract["universe_file"]))
    errors: list[str] = []
    if sha256(manifest_path) != str(contract["source_archive_manifest_sha256"]):
        errors.append("source manifest hash mismatch")
    if sha256(universe_path) != str(contract["universe_sha256"]):
        errors.append("universe hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("function") != contract["source_endpoint"]:
        errors.append("source endpoint mismatch")
    if manifest.get("status") != "COMPLETE_WITH_RETRYABLE_FAILURES":
        errors.append("preserved broad source manifest terminal state changed")
    completed = manifest.get("completed") or {}
    if not isinstance(completed, dict):
        errors.append("source manifest completed map is invalid")
        completed = {}
    candidates = [
        line.strip()
        for line in universe_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if candidates != contract["candidate_symbols"]:
        errors.append("candidate universe order or identity mismatch")
    required = candidates + list(contract["context_symbols"])
    if len(required) != len(set(required)):
        errors.append("required symbols are not unique")
    files: dict[str, Any] = {}
    for symbol in required:
        if symbol not in completed:
            errors.append(f"symbol is not complete in frozen manifest: {symbol}")
        path = source / f"{symbol}_daily.json"
        if not path.exists():
            errors.append(f"source file is missing: {symbol}")
            continue
        try:
            rows = load_rows(path)
        except Exception as exc:  # fail closed with a redacted structural message
            errors.append(f"source rows cannot be parsed: {symbol}: {type(exc).__name__}")
            continue
        dates = [str(row["date"]) for row in rows]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            errors.append(f"source dates are not unique and increasing: {symbol}")
        if not rows or dates[-1] != contract["required_latest_source_date"]:
            errors.append(f"source latest date mismatch: {symbol}")
        if any(
            float(row[field]) <= 0
            for row in rows
            for field in ("open", "high", "low", "close")
        ):
            errors.append(f"nonpositive adjusted OHLC: {symbol}")
        files[symbol] = {
            "path": str(path),
            "sha256": sha256(path),
            "rows": len(rows),
            "first_date": dates[0] if dates else None,
            "latest_date": dates[-1] if dates else None,
        }
    unrelated_failures = sorted((manifest.get("failed") or {}).keys())
    if any(symbol in required for symbol in unrelated_failures):
        errors.append("required subset intersects broad archive failures")
    return {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "research_only": True,
        "execution_enabled": False,
        "provider_contacted": False,
        "orders_created": False,
        "contract_id": contract["contract_id"],
        "contract_sha256": sha256(contract_path),
        "source_manifest_status_preserved": manifest.get("status"),
        "source_manifest_sha256": sha256(manifest_path),
        "required_symbols": required,
        "required_symbol_count": len(required),
        "required_latest_source_date": contract["required_latest_source_date"],
        "volatility_context_is_proxy": True,
        "volatility_context_symbol": "VIXY",
        "volatility_level_feature_permitted": False,
        "unrelated_broad_archive_failures_preserved": unrelated_failures,
        "files": files,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit(args.contract)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
