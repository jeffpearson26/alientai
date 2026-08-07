from __future__ import annotations

"""Validate Jeff's source-pure Alpha Vantage/Schwab fallback registry."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "approved_source_fallback_registry.json"
ALLOWED_STATES = {"READY", "ALTERNATE_CLONE_REQUIRED"}
ALLOWED_PROVIDERS = {"Alpha Vantage", "Schwab"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolved(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def validate_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if registry.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if registry.get("research_only") is not True:
        errors.append("registry must remain research_only")
    if registry.get("execution_enabled") is not False:
        errors.append("execution must remain disabled")
    policy = registry.get("policy") or {}
    if set(policy.get("allowed_providers") or []) != ALLOWED_PROVIDERS:
        errors.append("allowed providers must be exactly Alpha Vantage and Schwab")
    if policy.get("row_level_provider_splicing_allowed") is not False:
        errors.append("row-level provider splicing must be forbidden")
    if (
        policy.get("provider_substitution_inside_frozen_model_allowed")
        is not False
    ):
        errors.append("provider substitution inside a frozen model is forbidden")
    historical = policy.get("historical_final_day_policy") or {}
    if historical.get("allowed_only_before_model_or_test_freeze") is not True:
        errors.append("historical endpoint truncation must be pre-freeze only")
    if historical.get("excluded_dates_must_be_recorded") is not True:
        errors.append("historical excluded dates must be recorded")
    prospective = policy.get("frozen_or_prospective_final_day_policy") or {}
    if "do not shorten" not in str(prospective.get("action") or "").casefold():
        errors.append("frozen/prospective horizons must not be shortened")

    routes = registry.get("routes") or []
    route_ids = [str(route.get("route_id") or "") for route in routes]
    if not routes or "" in route_ids or len(route_ids) != len(set(route_ids)):
        errors.append("route IDs must be nonempty and unique")
    ready_routes = 0
    pending_routes = 0
    for route in routes:
        route_id = str(route.get("route_id") or "")
        state = route.get("state")
        if state not in ALLOWED_STATES:
            errors.append(f"{route_id}: invalid state {state!r}")
            continue
        primary = route.get("primary") or {}
        alternate = route.get("alternate") or {}
        if primary.get("provider") not in ALLOWED_PROVIDERS:
            errors.append(f"{route_id}: invalid primary provider")
        if alternate.get("provider") not in ALLOWED_PROVIDERS:
            errors.append(f"{route_id}: invalid alternate provider")
        if primary.get("provider") == alternate.get("provider"):
            errors.append(f"{route_id}: primary and alternate providers match")
        if state == "ALTERNATE_CLONE_REQUIRED":
            pending_routes += 1
            if alternate.get("model_id") is not None:
                errors.append(f"{route_id}: pending alternate model must be null")
            if alternate.get("journal_path") is not None:
                errors.append(f"{route_id}: pending alternate journal must be null")
            continue
        ready_routes += 1
        if not primary.get("model_id") or not alternate.get("model_id"):
            errors.append(f"{route_id}: ready route requires two model IDs")
        if primary.get("model_id") == alternate.get("model_id"):
            errors.append(f"{route_id}: source-specific model IDs must differ")
        if primary.get("journal_path") == alternate.get("journal_path"):
            errors.append(f"{route_id}: source-specific journals must differ")
        for side_name, side in (("primary", primary), ("alternate", alternate)):
            audit_value = str(side.get("audit_path") or "")
            expected_hash = str(side.get("audit_sha256") or "").casefold()
            audit_path = _resolved(audit_value) if audit_value else Path()
            if not audit_value or not audit_path.is_file():
                errors.append(f"{route_id}: {side_name} audit is missing")
                continue
            if sha256(audit_path) != expected_hash:
                errors.append(f"{route_id}: {side_name} audit hash mismatch")
                continue
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if audit.get("status") != "PASS":
                errors.append(f"{route_id}: {side_name} audit is not PASS")
            if audit.get("model_id") != side.get("model_id"):
                errors.append(f"{route_id}: {side_name} model ID mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "registry": str(path.resolve()),
        "routes": len(routes),
        "ready_routes": ready_routes,
        "alternate_clone_required_routes": pending_routes,
        "errors": errors,
        "research_only": True,
        "execution_enabled": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate_registry(args.registry)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
