from __future__ import annotations

"""Leakage-safe feature contract for Jeff's AI-semiconductor narrative thesis.

The source narrative is a hypothesis, never a label and never a ticker boost.
Only timestamped structured values available at the decision cutoff may enter.
"""

from datetime import datetime
from typing import Any, Mapping


NUMERIC_INPUTS = (
    "fund_revenue_surprise_pct",
    "fund_eps_surprise_pct",
    "fund_guidance_midpoint_revision_pct",
    "fund_ai_segment_growth_yoy_pct",
    "fund_estimate_revision_30d_pct",
    "analyst_net_upgrades_30d",
    "analyst_price_target_revision_pct_30d",
    "industry_semiconductor_sales_growth_yoy_pct",
    "industry_hbm_price_trend_pct",
    "industry_hyperscaler_capex_revision_pct",
    "industry_advanced_packaging_utilization_pct",
    "catalyst_sessions_to_earnings",
)

AI_STACK_ROLES = (
    "memory",
    "gpu_accelerator",
    "custom_asic_networking",
    "foundry",
    "semiconductor_equipment",
    "design_software",
    "ai_infrastructure",
)


def _timestamp(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def build_narrative_features(
    row: Mapping[str, Any],
    decision_cutoff_utc: str,
) -> dict[str, Any]:
    """Return interpretable components and interactions without hand-picked names."""
    cutoff = _timestamp(decision_cutoff_utc)
    available = row.get("narrative_available_at_utc")
    if not available:
        raise ValueError("narrative_available_at_utc is required")
    if _timestamp(available) > cutoff:
        raise ValueError("narrative data was not public by the decision cutoff")

    values = {name: _number(row.get(name)) for name in NUMERIC_INPUTS}
    result: dict[str, Any] = {}
    for name, value in values.items():
        result[f"narrative_{name}"] = 0.0 if value is None else value
        result[f"narrative_{name}_missing"] = value is None

    role = str(row.get("ai_stack_role") or "").strip().lower()
    if role and role not in AI_STACK_ROLES:
        raise ValueError(f"unsupported AI-stack role: {role}")
    for allowed in AI_STACK_ROLES:
        result[f"narrative_role_{allowed}"] = role == allowed
    result["narrative_role_missing"] = not role

    # Preserve the exact thesis as interactions for the learner. These are not
    # hard-coded buy rules and do not assign preferential weights to symbols.
    ema50 = _number(row.get("technical_ema50_distance_pct"))
    return20 = _number(row.get("return_20d_lag_pct"))
    rsi14 = _number(row.get("technical_rsi_14"))
    result["narrative_pullback_in_uptrend"] = bool(
        ema50 is not None and return20 is not None and ema50 > 0 and return20 < 0
    )
    result["narrative_oversold_in_uptrend"] = bool(
        ema50 is not None and rsi14 is not None and ema50 > 0 and rsi14 < 40
    )

    earnings = values["catalyst_sessions_to_earnings"]
    for horizon in (1, 5, 20):
        result[f"narrative_earnings_crosses_{horizon}d"] = bool(
            earnings is not None and 0 <= earnings <= horizon
        )

    positive_fundamentals = sum(
        (values[name] or 0.0) > 0
        for name in (
            "fund_revenue_surprise_pct",
            "fund_eps_surprise_pct",
            "fund_guidance_midpoint_revision_pct",
            "fund_ai_segment_growth_yoy_pct",
            "fund_estimate_revision_30d_pct",
        )
    )
    positive_demand = sum(
        (values[name] or 0.0) > 0
        for name in (
            "industry_semiconductor_sales_growth_yoy_pct",
            "industry_hbm_price_trend_pct",
            "industry_hyperscaler_capex_revision_pct",
        )
    )
    result["narrative_positive_fundamental_components"] = positive_fundamentals
    result["narrative_positive_demand_components"] = positive_demand
    result["narrative_fundamental_demand_agreement"] = (
        positive_fundamentals >= 3 and positive_demand >= 2
    )
    result["narrative_upgrade_with_positive_estimate_revision"] = bool(
        (values["analyst_net_upgrades_30d"] or 0.0) > 0
        and (values["fund_estimate_revision_30d_pct"] or 0.0) > 0
    )
    result["narrative_feature_contract_version"] = 1
    return result
