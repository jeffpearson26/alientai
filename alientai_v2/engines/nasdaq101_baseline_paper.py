from __future__ import annotations

"""Fail-closed paper adapter for the frozen Nasdaq-101 technical baseline."""

import hashlib
import json
import os
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_ID = "nasdaq100_complete_101_baseline_v1"
LOCKED_SCORE_CUTOFF = 0.20886314398519493
EXPECTED_MODEL_SHA256 = "5410de1e68f002ad46d3cb20f484753657a116f62c562aed8f515b7245b08b77"
EXPECTED_REPORT_SHA256 = "aca314e9b21f0d0b47f93314b460394f78b168f5733fa2f14a0924978e752d62"
EXPECTED_SYMBOLS_SHA256 = "d52cd998bea8b02b454fa6cbdad9ac42aa4f7a447a331c2f9a49fb43cf40e420"
EXPECTED_UNIVERSE_SIZE = 101
MAX_CANDIDATES = 5
DEFAULT_PYRAMID_INTERVAL_SECONDS = 5 * 60


def _avoid(reason: str) -> list[dict[str, Any]]:
    return [{
        "engine_id": POLICY_ID,
        "symbol": "",
        "side": "LONG",
        "score": 0.0,
        "decision": "AVOID",
        "price": 0.0,
        "reason": reason,
        "source": POLICY_ID,
        "paper_only": True,
        "live_trading_enabled": False,
    }]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_symbols() -> set[str]:
    path = PROJECT_ROOT / "nasdaq100_2026-06_symbols.txt"
    if _sha256(path) != EXPECTED_SYMBOLS_SHA256:
        raise ValueError("frozen Nasdaq-101 symbol file hash mismatch")
    values = {
        line.strip().upper()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if len(values) != EXPECTED_UNIVERSE_SIZE:
        raise ValueError("frozen Nasdaq-101 symbol count mismatch")
    return values


def payload_path(settings: dict[str, Any], today: str) -> Path:
    configured = str(settings.get("nasdaq101_baseline_paper_payload_path") or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    directory = (
        PROJECT_ROOT / "data_v2" / "rcef_research" / "nasdaq101_baseline_paper"
    )
    exact = directory / f"nasdaq101_baseline_paper_payload_{today}.json"
    available = sorted(directory.glob("nasdaq101_baseline_paper_payload_????-??-??.json"))
    return exact if exact.exists() else (available[-1] if available else exact)


def trend_state_path(settings: dict[str, Any]) -> Path:
    configured = str(settings.get("nasdaq101_baseline_trend_state_path") or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return PROJECT_ROOT / "data_v2" / "nasdaq101_baseline_paper_trend_state.json"


def paper_account_path(settings: dict[str, Any]) -> Path:
    configured = str(settings.get("nasdaq101_baseline_paper_account_path") or "").strip()
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return PROJECT_ROOT / "data_v2" / "v2_paper_account.json"


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _record_trends(
    quotes_by_symbol: dict[str, dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, bool]:
    """Record quote samples and require a strictly higher five-minute price."""
    now_epoch = time.time()
    interval = max(
        DEFAULT_PYRAMID_INTERVAL_SECONDS,
        int(settings.get("nasdaq101_baseline_pyramid_interval_seconds", DEFAULT_PYRAMID_INTERVAL_SECONDS)),
    )
    path = trend_state_path(settings)
    state = _load_object(path)
    samples_by_symbol = state.get("samples")
    if not isinstance(samples_by_symbol, dict):
        samples_by_symbol = {}
    trends: dict[str, bool] = {}
    for symbol, quote in quotes_by_symbol.items():
        try:
            price = float(quote.get("price") or quote.get("last_price") or quote.get("last") or 0.0)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        raw_samples = samples_by_symbol.get(symbol)
        samples = raw_samples if isinstance(raw_samples, list) else []
        samples = [
            sample for sample in samples
            if isinstance(sample, dict)
            and now_epoch - float(sample.get("observed_at_epoch") or 0.0) <= 60 * 60
        ]
        references = [
            sample for sample in samples
            if now_epoch - float(sample.get("observed_at_epoch") or 0.0) >= interval
        ]
        reference = max(
            references,
            key=lambda sample: float(sample.get("observed_at_epoch") or 0.0),
            default=None,
        )
        trends[symbol] = bool(
            reference is not None and price > float(reference.get("price") or 0.0)
        )
        samples.append({"observed_at_epoch": now_epoch, "price": price})
        samples_by_symbol[symbol] = samples[-61:]
    _atomic_json(path, {"updated_at_epoch": now_epoch, "samples": samples_by_symbol})
    return trends


def candidate_symbols(settings: dict[str, Any]) -> list[str]:
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    path = payload_path(settings, datetime.now(timezone).date().isoformat())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("policy_id") != POLICY_ID:
            return []
        return [
            str(row.get("symbol") or "").strip().upper()
            for row in payload.get("candidates") or []
            if str(row.get("symbol") or "").strip()
        ]
    except Exception:
        return []


def _validated_payload(path: Path, today: date, maximum_age: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    session_day = date.fromisoformat(str(payload.get("market_session_date") or ""))
    age = (today - session_day).days
    symbols = {str(value).strip().upper() for value in payload.get("training_universe_symbols") or []}
    expected_symbols = _canonical_symbols()
    cutoff = float(payload.get("locked_score_cutoff"))
    candidates = payload.get("candidates") or []
    identity_ok = (
        payload.get("status") == "paper_payload_ready"
        and payload.get("research_only") is True
        and payload.get("paper_only") is True
        and payload.get("live_trading_enabled") is False
        and payload.get("policy_id") == POLICY_ID
        and payload.get("source") == "schwab_daily_history"
        and payload.get("source_pure") is True
        and age in range(maximum_age + 1)
        and int(payload.get("training_universe_size") or 0) == EXPECTED_UNIVERSE_SIZE
        and int(payload.get("universe_rows") or 0) == EXPECTED_UNIVERSE_SIZE
        and symbols == expected_symbols
        and payload.get("symbols_sha256") == EXPECTED_SYMBOLS_SHA256
        and payload.get("model_sha256") == EXPECTED_MODEL_SHA256
        and payload.get("training_report_sha256") == EXPECTED_REPORT_SHA256
        and abs(cutoff - LOCKED_SCORE_CUTOFF) < 1e-15
        and isinstance(candidates, list)
        and len(candidates) <= MAX_CANDIDATES
    )
    if not identity_ok:
        raise ValueError("payload failed identity, source, freshness, or complete-101 checks")
    return payload


def scan(quotes: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    if settings.get("nasdaq101_baseline_paper_enabled") is not True:
        return _avoid("Nasdaq-101 baseline paper execution is disabled in settings.")
    timezone = ZoneInfo(str(settings.get("timezone") or "America/Los_Angeles"))
    today = datetime.now(timezone).date()
    path = payload_path(settings, today.isoformat())
    if not path.exists():
        return _avoid(f"No Nasdaq-101 baseline paper payload is available for {today.isoformat()}.")
    try:
        maximum_age = max(
            0,
            int(settings.get("nasdaq101_baseline_payload_max_calendar_age_days", 3)),
        )
        payload = _validated_payload(path, today, maximum_age)
    except Exception as exc:
        return _avoid(f"Nasdaq-101 baseline payload rejected: {exc}")

    quotes_by_symbol = {
        str(row.get("symbol") or "").strip().upper(): row
        for row in quotes
        if isinstance(row, dict)
    }
    trends = _record_trends(quotes_by_symbol, settings)
    account = _load_object(paper_account_path(settings))
    open_positions = account.get("open_positions")
    if not isinstance(open_positions, dict):
        open_positions = {}
    output: list[dict[str, Any]] = []
    for candidate in payload.get("candidates") or []:
        if (
            candidate.get("policy_id") != POLICY_ID
            or candidate.get("paper_decision") != "BUY_CANDIDATE"
        ):
            continue
        symbol = str(candidate.get("symbol") or "").strip().upper()
        if symbol not in set(payload["training_universe_symbols"]):
            continue
        quote = quotes_by_symbol.get(symbol, {})
        try:
            price = float(
                quote.get("price") or quote.get("last_price") or quote.get("last") or 0.0
            )
            raw_score = float(candidate["model_score"])
            cutoff = float(candidate["locked_score_cutoff"])
            confidence_rank = int(candidate["confidence_rank_1_to_100"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            price <= 0
            or raw_score < LOCKED_SCORE_CUTOFF
            or abs(cutoff - LOCKED_SCORE_CUTOFF) >= 1e-15
            or confidence_rank not in range(1, 101)
        ):
            continue
        position = open_positions.get(symbol)
        pyramid_allowed = False
        if isinstance(position, dict):
            same_engine = str(position.get("engine_id") or "") == POLICY_ID
            entry_price = float(
                position.get("risk_entry_price") or position.get("entry_price") or 0.0
            )
            last_add_epoch = float(position.get("last_add_epoch") or 0.0)
            interval = max(
                DEFAULT_PYRAMID_INTERVAL_SECONDS,
                int(settings.get("nasdaq101_baseline_pyramid_interval_seconds", DEFAULT_PYRAMID_INTERVAL_SECONDS)),
            )
            pyramid_allowed = bool(
                settings.get("nasdaq101_baseline_pyramid_enabled") is True
                and same_engine
                and trends.get(symbol) is True
                and price > entry_price
                and time.time() - last_add_epoch >= interval
            )
            if not pyramid_allowed:
                continue
        output.append({
            **candidate,
            "engine_id": POLICY_ID,
            "side": "LONG",
            "decision": "BUY_CANDIDATE",
            "price": price,
            "score": float(confidence_rank),
            "model_score": raw_score,
            "requested_position_dollars": price,
            "paper_pyramid_allowed": pyramid_allowed,
            "paper_pyramid_interval_seconds": DEFAULT_PYRAMID_INTERVAL_SECONDS,
            "paper_pyramid_shares": 1,
            "prediction_horizon_days": 5,
            "minimum_hold_minutes": 5 * 24 * 60,
            "emergency_stop_enabled": True,
            "emergency_stop_loss_pct": -1.0,
            "stop_loss_pct": -1.0,
            "trailing_stop_pct": 5.0,
            "trailing_stop_activation_pct": 0.0,
            "allow_stop_before_min_hold": True,
            "allow_trailing_before_min_hold": True,
            "paper_only": True,
            "live_trading_enabled": False,
            "reason": (
                "Paper-only frozen Nasdaq-101 technical-baseline candidate; "
                + ("one-share five-minute uptrend add." if pyramid_allowed else "initial entry.")
            ),
            "source": POLICY_ID,
        })
    return output or _avoid(
        "Current complete-101 payload contained no quotable candidate above the frozen cutoff."
    )
