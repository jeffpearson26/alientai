from __future__ import annotations

import json
from pathlib import Path

from validate_approved_source_fallback_registry import (
    DEFAULT_REGISTRY,
    validate_registry,
)


def test_repository_registry_passes() -> None:
    result = validate_registry()
    assert result["status"] == "PASS"
    assert result["ready_routes"] == 1
    assert result["alternate_clone_required_routes"] == 3


def test_registry_forbids_row_splicing_and_prospective_shortening() -> None:
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    policy = registry["policy"]
    assert policy["row_level_provider_splicing_allowed"] is False
    assert policy["provider_substitution_inside_frozen_model_allowed"] is False
    assert (
        policy["historical_final_day_policy"][
            "allowed_only_before_model_or_test_freeze"
        ]
        is True
    )
    assert "do not shorten" in policy[
        "frozen_or_prospective_final_day_policy"
    ]["action"]


def test_ready_route_uses_distinct_models_providers_and_journals() -> None:
    registry = json.loads(DEFAULT_REGISTRY.read_text(encoding="utf-8"))
    ready = next(route for route in registry["routes"] if route["state"] == "READY")
    assert ready["primary"]["provider"] != ready["alternate"]["provider"]
    assert ready["primary"]["model_id"] != ready["alternate"]["model_id"]
    assert ready["primary"]["journal_path"] != ready["alternate"]["journal_path"]
    assert Path(ready["primary"]["audit_path"]).is_file()
    assert Path(ready["alternate"]["audit_path"]).is_file()
