from __future__ import annotations

"""Point-in-time feature contract for the five-session catalyst-momentum thesis."""

from collections import defaultdict
from typing import Any, Mapping, Sequence

from alientai_v2.features.insider_purchase_features import safe_float


def _number(row: Mapping[str, Any], name: str) -> float:
    return safe_float(row.get(name))


def _percentile_ranks(rows: Sequence[Mapping[str, Any]], field: str) -> dict[int, float]:
    """Cross-sectional ranks use only same-cutoff lagged inputs."""
    ordered = sorted(
        ((safe_float(row.get(field)), index) for index, row in enumerate(rows)),
        key=lambda item: (item[0], item[1]),
    )
    denominator = max(1, len(ordered) - 1)
    return {index: rank / denominator for rank, (_, index) in enumerate(ordered)}


def engineer_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add interpretable setup, catalyst, positioning, and risk features.

    No future label is read while constructing a feature.  Rows are ranked only
    against securities sharing the same point-in-time market date.
    """
    by_date: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_date[str(row.get("market_date") or "")].append((index, row))

    output: list[dict[str, Any] | None] = [None] * len(rows)
    for market_date, indexed_rows in by_date.items():
        if not market_date:
            raise ValueError("market_date is required")
        date_rows = [row for _, row in indexed_rows]
        return20_ranks = _percentile_ranks(date_rows, "return_20d_lag_pct")
        return60_ranks = _percentile_ranks(date_rows, "return_60d_lag_pct")

        for local_index, (original_index, source) in enumerate(indexed_rows):
            row = dict(source)
            rsi2 = _number(row, "technical_rsi_2")
            rsi14 = _number(row, "technical_rsi_14")
            bollinger = _number(row, "technical_bollinger_position")
            ema9 = _number(row, "technical_ema9_distance_pct")
            ema21 = _number(row, "technical_ema21_distance_pct")
            ema50 = _number(row, "technical_ema50_distance_pct")
            macd_hist = _number(row, "technical_macd_histogram_pct")
            relative_volume = _number(row, "technical_latest_relative_volume_20")
            obv = _number(row, "technical_obv_change_10d_normalized")
            atr = _number(row, "technical_atr14_pct")

            oversold = (rsi2 <= 10.0 or rsi14 <= 35.0) and (
                bollinger <= 0.30 or ema9 <= 0.0
            )
            breakout = (
                0.80 <= bollinger <= 1.20
                and macd_hist > 0.0
                and relative_volume >= 1.20
            )
            continuation = (
                bool(row.get("technical_ema_bullish_alignment"))
                and return20_ranks[local_index] >= 0.70
                and macd_hist > 0.0
                and relative_volume >= 0.90
            )
            parabolic = rsi14 > 85.0 or bollinger > 1.25 or ema21 > 12.0
            risk_ok = 0.5 <= atr <= 8.0 and not parabolic

            analyst_net_5d = _number(row, "model_analyst_proxy_net_action_5d")
            analyst_events = _number(row, "model_analyst_proxy_event_count_14d")
            earnings_age = row.get("narrative_fund_days_since_report")
            recent_earnings = (
                earnings_age is not None and 0.0 <= safe_float(earnings_age) <= 5.0
            )
            news_count = _number(row, "narrative_news_1d_article_count")
            news_relevance = _number(row, "narrative_news_1d_mean_relevance")
            news_sentiment = _number(row, "narrative_news_1d_weighted_sentiment")
            material_news = (
                news_count >= 2.0
                and news_relevance >= 0.50
                and abs(news_sentiment) >= 0.10
            )
            catalyst_active = (
                analyst_events > 0.0 or recent_earnings or material_news
            )

            unusual_calls = bool(row.get("model_call_volume_unusual"))
            call_zscore = _number(row, "model_call_volume_zscore")
            call_vs_median = _number(row, "model_call_volume_vs_prior_median")
            call_positioning_positive = unusual_calls and (
                call_zscore >= 2.0 or call_vs_median >= 2.0
            )

            fundamental_positive = (
                _number(row, "narrative_fund_eps_surprise_pct") > 0.0
                or _number(row, "narrative_fund_eps_beat_streak") >= 2.0
            )
            obvious_negative_overlay = (
                _number(row, "narrative_fund_eps_surprise_pct") <= -10.0
                or analyst_net_5d < 0.0
                or news_sentiment <= -0.35
            )
            technical_setup = oversold or breakout or continuation

            row.update({
                "cm_technical_return20_rank": return20_ranks[local_index],
                "cm_technical_return60_rank": return60_ranks[local_index],
                "cm_technical_oversold_bounce": oversold,
                "cm_technical_breakout": breakout,
                "cm_technical_continuation": continuation,
                "cm_technical_setup": technical_setup,
                "cm_technical_volume_confirmation": relative_volume >= 1.20 and obv > 0,
                "cm_catalyst_analyst_event": analyst_events > 0.0,
                "cm_catalyst_recent_earnings_reaction": recent_earnings,
                "cm_catalyst_material_target_news": material_news,
                "cm_catalyst_active": catalyst_active,
                "cm_catalyst_direction": analyst_net_5d + news_sentiment,
                "cm_positioning_unusual_calls": unusual_calls,
                "cm_positioning_positive_call_pressure": call_positioning_positive,
                "cm_fundamental_positive_overlay": fundamental_positive,
                "cm_fundamental_obvious_negative": obvious_negative_overlay,
                "cm_risk_atr_pct": atr,
                "cm_risk_parabolic": parabolic,
                "cm_risk_ok": risk_ok,
                "cm_technical_eligible": technical_setup and risk_ok,
                "cm_primary_eligible": (
                    catalyst_active
                    and technical_setup
                    and risk_ok
                    and not obvious_negative_overlay
                ),
            })
            output[original_index] = row
    return [row for row in output if row is not None]
