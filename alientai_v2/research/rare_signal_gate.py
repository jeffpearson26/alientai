"""Fail-closed promotion gate for research-only rare-signal evaluations.

The gate does not estimate profitability and never enables an order.  It makes
the minimum evidence requirements explicit so an attractive average return
cannot hide sparse samples, negative typical outcomes, or concentrated risk.
"""

from __future__ import annotations

from typing import Any, Mapping


DEFAULT_POLICY = {
    "minimum_signals": 30,
    "minimum_win_rate_after_cost": 0.50,
    "minimum_median_net_return_pct": 0.0,
    "minimum_mean_net_return_pct": 0.0,
    "minimum_fifth_percentile_net_return_pct": -10.0,
    "minimum_worst_trade_net_return_pct": -25.0,
    "minimum_cohort_max_drawdown_pct": -20.0,
    "maximum_largest_symbol_signal_share": 0.20,
}


def _number(metrics: Mapping[str, Any], name: str) -> float | None:
    value = metrics.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def evaluate_rare_signal_gate(
    metrics: Mapping[str, Any], policy: Mapping[str, float | int] | None = None,
) -> dict[str, Any]:
    """Return an evidence gate result; missing metrics always fail closed."""
    rules = {**DEFAULT_POLICY, **dict(policy or {})}
    checks: list[dict[str, Any]] = []

    def add(name: str, observed_name: str, operator: str, threshold: float, passes: bool | None) -> None:
        observed = _number(metrics, observed_name)
        checks.append({
            "name": name,
            "observed_metric": observed_name,
            "observed": observed,
            "operator": operator,
            "threshold": threshold,
            "pass": bool(passes) if passes is not None else False,
            "missing": observed is None,
        })

    def minimum(name: str, threshold_name: str, observed_name: str) -> None:
        observed = _number(metrics, observed_name)
        threshold = float(rules[threshold_name])
        add(name, observed_name, ">=", threshold, None if observed is None else observed >= threshold)

    def maximum(name: str, threshold_name: str, observed_name: str) -> None:
        observed = _number(metrics, observed_name)
        threshold = float(rules[threshold_name])
        add(name, observed_name, "<=", threshold, None if observed is None else observed <= threshold)

    minimum("minimum sample", "minimum_signals", "signals")
    minimum("cost-adjusted win rate", "minimum_win_rate_after_cost", "win_rate_after_cost")
    minimum("positive typical outcome", "minimum_median_net_return_pct", "median_net_return_pct")
    minimum("positive average outcome", "minimum_mean_net_return_pct", "mean_net_return_pct")
    minimum("fifth-percentile tail", "minimum_fifth_percentile_net_return_pct", "fifth_percentile_net_return_pct")
    minimum("worst-trade limit", "minimum_worst_trade_net_return_pct", "worst_trade_net_return_pct")
    minimum("cohort drawdown limit", "minimum_cohort_max_drawdown_pct", "approximate_cohort_max_drawdown_pct")
    maximum("symbol concentration limit", "maximum_largest_symbol_signal_share", "largest_symbol_signal_share")

    failures = [check["name"] for check in checks if not check["pass"]]
    return {
        "status": "RESEARCH_PASS" if not failures else "RESEARCH_HOLD",
        "research_only": True,
        "execution_enabled": False,
        "policy": rules,
        "checks": checks,
        "failure_reasons": failures,
    }
