from __future__ import annotations

"""Read-only AlienTAI research-model monitoring dashboard."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from fastapi import APIRouter
from fastapi.responses import HTMLResponse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = PROJECT_ROOT / "data_v2" / "rcef_research"
GROK_REPORT = Path(
    r"D:\Downloads\nasdaq_ai_semi_predictor\nasdaq_ai_semi_predictor"
    r"\outputs\nasdaq101_5d_20260805_current_report.json"
)

router = APIRouter(prefix="/v2", tags=["AlientAI model research monitor"])


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    name: str
    description: str
    horizon: str
    universe: str
    inputs: str
    state: str
    state_note: str
    journal: Path | None = None
    outcomes: Path | None = None
    source_kind: str = "jsonl"
    aggregate_summary: Path | None = None


MODEL_SPECS = (
    ModelSpec(
        "autonomous_transparent_20session",
        "Autonomous Transparent Champion",
        "Cross-sectional momentum model designed for interpretable, repeatable long selections.",
        "20 sessions",
        "Nasdaq-101",
        "126/60-session QQQ-relative momentum and inverse 60-session volatility",
        "active",
        "First prospective basket is pending its complete 20-session horizon.",
        RESEARCH_ROOT / "autonomous_champion_20session_prospective_journal.jsonl",
        RESEARCH_ROOT / "autonomous_champion_20session_prospective_outcomes.jsonl",
        "autonomous",
        RESEARCH_ROOT / "autonomous_champion_20session_prospective_summary.json",
    ),
    ModelSpec(
        "contextual_options_top_quarter",
        "Technical Context + Unusual Calls",
        "Selects technically strong candidates only when prior-session call buying is unusually elevated.",
        "5 sessions",
        "Natural universe",
        "Daily technical context and prior-session nonempty call-option history",
        "active",
        "August 4 selections are frozen and pending; new eligible dates continue independently.",
        RESEARCH_ROOT / "contextual_options_shadow_payload_2026-08-04.json",
        None,
        "contextual",
        RESEARCH_ROOT / "contextual_options_prospective_gate_2026-07-30.json",
    ),
    ModelSpec(
        "nasdaq100_complete_101_baseline_v1",
        "Nasdaq-101 Baseline",
        "Frozen five-session technical ranking model for the complete Nasdaq research universe.",
        "5 sessions",
        "Nasdaq-101",
        "Daily technical features",
        "attention",
        "Prior prospective outcomes exist, but the latest eligible attempt lacks an explicit journaled abstention.",
        RESEARCH_ROOT / "nasdaq100_prospective" / "journal.jsonl",
        RESEARCH_ROOT / "nasdaq100_prospective" / "outcomes.jsonl",
    ),
    ModelSpec(
        "nasdaq100_complete_101_qqq_relative_v1",
        "Nasdaq-101 QQQ-Relative",
        "Five-session technical model augmented with broad Nasdaq-relative context.",
        "5 sessions",
        "Nasdaq-101",
        "Daily technical and QQQ-relative features",
        "attention",
        "Prior prospective outcomes exist, but the latest eligible attempt lacks an explicit journaled abstention.",
        RESEARCH_ROOT / "nasdaq100_prospective" / "journal.jsonl",
        RESEARCH_ROOT / "nasdaq100_prospective" / "outcomes.jsonl",
    ),
    ModelSpec(
        "nasdaq100_technical_clone_v1",
        "Nasdaq-80 Champion",
        "Validation-locked technical-context clone restricted to securities represented in its training panel.",
        "5 sessions",
        "Nasdaq-80",
        "Daily technical and QQQ-context features",
        "active",
        "QCOM is the newest frozen observation; older horizons remain independent.",
        RESEARCH_ROOT / "nasdaq80_champion_prospective" / "journal.jsonl",
        RESEARCH_ROOT / "nasdaq80_champion_prospective" / "outcomes.jsonl",
        "jsonl",
        RESEARCH_ROOT / "nasdaq80_champion_prospective" / "outcome_summary.json",
    ),
    ModelSpec(
        "ai_semiconductor_technical_premarket_5d_20260731",
        "AI/Semiconductor Premarket",
        "Five-session model focused on AI infrastructure and semiconductor names.",
        "5 sessions",
        "17 AI/semi symbols",
        "Prior daily technical context and exact 09:25 ET premarket features",
        "active",
        "Four earlier observations are pending; the latest new-day attempt is source-blocked.",
        RESEARCH_ROOT / "ai_semiconductor_premarket_prospective_journal.jsonl",
        RESEARCH_ROOT / "ai_semiconductor_premarket_prospective_outcomes.jsonl",
    ),
    ModelSpec(
        "ai_semiconductor_late_60m_premarket_schwab_frozen_20260803",
        "Schwab Late-Entry Premarket",
        "Source-separated intraday model that enters after the exact 09:25 premarket candle is observable.",
        "60 minutes",
        "17 AI/semi symbols",
        "Prior daily technical context and Schwab premarket data",
        "active",
        "Today completed its first exact future-data outcome; the next market day remains eligible.",
        RESEARCH_ROOT / "ai_semiconductor_late_intraday_schwab_journal.jsonl",
        RESEARCH_ROOT / "ai_semiconductor_late_intraday_schwab_outcomes.jsonl",
    ),
    ModelSpec(
        "ai_semiconductor_late_60m_calls_schwab_frozen_20260803",
        "Schwab Late-Entry Unusual Calls",
        "Late-entry intraday variant that adds prior-session call-option activity.",
        "60 minutes",
        "17 AI/semi symbols",
        "Technical, exact Schwab premarket and prior-session unusual-call features",
        "active",
        "Today completed its first exact future-data outcome; the next market day remains eligible.",
        RESEARCH_ROOT / "ai_semiconductor_late_intraday_schwab_journal.jsonl",
        RESEARCH_ROOT / "ai_semiconductor_late_intraday_schwab_outcomes.jsonl",
    ),
    ModelSpec(
        "ai_semiconductor_narrative_1d_earnings_frozen_20260803",
        "AI/Semiconductor Narrative Context",
        "One-session model adding point-in-time earnings context to technical and premarket inputs.",
        "1 session",
        "17 AI/semi symbols",
        "Technical, premarket and timestamped earnings context",
        "blocked",
        "No valid future observation yet because exact premarket coverage was unavailable.",
        RESEARCH_ROOT / "ai_semiconductor_narrative_1d_prospective" / "journal.jsonl",
        RESEARCH_ROOT / "ai_semiconductor_narrative_1d_prospective" / "outcomes.jsonl",
    ),
    *tuple(
        ModelSpec(
            f"ai_semiconductor_{horizon}m_{variant}_frozen_20260731",
            f"Original Alpha {horizon}-Minute {variant.title()}",
            "Frozen opening-session model preserved for evidence but unable to satisfy its original live timing contract.",
            f"{horizon} minutes",
            "17 AI/semi symbols",
            {
                "technical": "Prior-session technical context",
                "premarket": "Technical plus exact 09:25 ET premarket context",
                "calls": "Technical, premarket and prior-session unusual calls",
            }[variant],
            "blocked",
            "Alpha Vantage cannot deliver the required completed 09:25 interval before the frozen 09:30 entry.",
            RESEARCH_ROOT / "ai_semiconductor_intraday_prospective_journal.jsonl",
            RESEARCH_ROOT / "ai_semiconductor_intraday_prospective_outcomes.jsonl",
        )
        for horizon in (20, 60)
        for variant in ("technical", "premarket", "calls")
    ),
    *tuple(
        ModelSpec(
            f"rolling_anytime_ai17_schema3_h{horizon:02d}",
            f"Any-Time AI/Semi {horizon}-Minute",
            "Schema-v3 one-minute research clone with strict next-interval entry, chronology and sealed-test controls.",
            f"{horizon} minutes",
            "17 AI/semi symbols",
            "One-minute price, volume, volatility, momentum and market-relative features",
            "development",
            (
                "Policy validation failed after costs; the sealed test remained unopened."
                if horizon in (5, 10, 20, 30)
                else "Historical panel and training stage have not completed yet."
            ),
        )
        for horizon in (5, 10, 20, 30, 60, 90)
    ),
    ModelSpec(
        "grok_nasdaq101_5d_20260805",
        "Grok Nasdaq-101 Technical Preview",
        "External LightGBM implementation retrained locally on the exact 101-security list.",
        "5 sessions",
        "Nasdaq-101",
        "Thirty-seven adjusted-daily technical features",
        "preview",
        "Scored after the August 5 open, so this basket is a preview rather than a formal pre-entry observation.",
        GROK_REPORT,
        None,
        "grok",
    ),
    ModelSpec(
        "defined_risk_options_volatility",
        "Defined-Risk Options Volatility",
        "Future multi-leg options selector with conservative spread-crossing fills and explicit abstention.",
        "Up to 5 sessions",
        "17 AI/semi symbols",
        "Direction, absolute move, implied volatility, liquidity and event timing",
        "development",
        "Strategy and fill contracts exist; learned direction and move heads are not complete.",
    ),
)


RETURN_FIELDS = (
    "net_return_pct",
    "label_forward_return_60m_net_pct",
    "return_after_cost_pct",
    "final_net_return_pct",
    "realized_return_pct",
)
PRELIMINARY_RETURN_FIELDS = (
    "preliminary_net_return_pct",
    "current_net_return_pct",
    "mark_to_market_return_pct",
)


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    return rows


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _first_number(row: dict[str, Any], fields: Iterable[str]) -> float | None:
    for field in fields:
        value = _number(row.get(field))
        if value is not None:
            return value
    return None


def _row_date(row: dict[str, Any]) -> str:
    for field in (
        "market_session_date",
        "entry_session_date",
        "actual_market_session_date",
        "decision_date",
        "market_date",
    ):
        value = str(row.get(field) or "").strip()
        if value:
            return value[:10]
    return "Unknown"


def _journal_rows(spec: ModelSpec) -> list[dict[str, Any]]:
    if spec.source_kind == "contextual":
        payload = _read_json(spec.journal)
        date = str(payload.get("actual_market_session_date") or payload.get("market_date") or "")
        return [
            {
                "model_id": spec.model_id,
                "symbol": row.get("symbol"),
                "rank": index,
                "market_session_date": date,
                "status": "pending",
            }
            for index, row in enumerate(payload.get("candidates") or [], 1)
            if isinstance(row, dict) and row.get("symbol")
        ]
    if spec.source_kind == "autonomous":
        output: list[dict[str, Any]] = []
        for batch in _read_jsonl(spec.journal):
            for selection in batch.get("selections") or []:
                if isinstance(selection, dict):
                    output.append(
                        {
                            **selection,
                            "model_id": spec.model_id,
                            "market_session_date": batch.get("decision_date"),
                            "status": "pending",
                        }
                    )
        return output
    if spec.source_kind == "grok":
        payload = _read_json(spec.journal)
        return [
            {
                **row,
                "model_id": spec.model_id,
                "market_session_date": payload.get("latest_complete_session"),
                "status": "preview",
                "forecast_return_pct": row.get("predicted_5d_return_pct"),
            }
            for row in payload.get("picks") or []
            if isinstance(row, dict)
        ]
    return [
        row
        for row in _read_jsonl(spec.journal)
        if str(row.get("model_id") or "") == spec.model_id
    ]


def _outcome_rows(spec: ModelSpec) -> list[dict[str, Any]]:
    return [
        row
        for row in _read_jsonl(spec.outcomes)
        if str(row.get("model_id") or "") == spec.model_id
    ]


def _aggregate_override(spec: ModelSpec) -> tuple[float | None, float | None, int]:
    payload = _read_json(spec.aggregate_summary)
    if spec.source_kind == "contextual":
        metrics = payload.get("metrics") or {}
        return (
            _number(metrics.get("mean_net_return_pct")),
            (
                100.0 * float(metrics["win_rate_after_cost"])
                if metrics.get("win_rate_after_cost") is not None
                else None
            ),
            int(payload.get("completed_outcomes") or metrics.get("signals") or 0),
        )
    return (
        _number(payload.get("mean_net_return_pct")),
        _number(payload.get("win_rate_after_cost_pct")),
        int(payload.get("signals") or 0),
    )


def _daily_ledger(
    journal_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for row in journal_rows:
        date = _row_date(row)
        bucket = by_date.setdefault(
            date,
            {"date": date, "picks": [], "forecast_values": [], "preliminary_values": [], "final_values": []},
        )
        symbol = str(row.get("symbol") or "").strip()
        if symbol and symbol not in bucket["picks"]:
            bucket["picks"].append(symbol)
        forecast = _number(row.get("forecast_return_pct"))
        if forecast is not None:
            bucket["forecast_values"].append(forecast)
        preliminary = _first_number(row, PRELIMINARY_RETURN_FIELDS)
        if preliminary is not None:
            bucket["preliminary_values"].append(preliminary)
    for row in outcome_rows:
        date = _row_date(row)
        bucket = by_date.setdefault(
            date,
            {"date": date, "picks": [], "forecast_values": [], "preliminary_values": [], "final_values": []},
        )
        symbol = str(row.get("symbol") or "").strip()
        if symbol and symbol not in bucket["picks"]:
            bucket["picks"].append(symbol)
        value = _first_number(row, RETURN_FIELDS)
        if value is not None:
            bucket["final_values"].append(value)

    output = []
    for bucket in by_date.values():
        finals = bucket.pop("final_values")
        preliminaries = bucket.pop("preliminary_values")
        forecasts = bucket.pop("forecast_values")
        pick_count = len(bucket["picks"])
        completed = len(finals)
        output.append(
            {
                **bucket,
                "pick_count": pick_count,
                "preliminary_pl_pct": (
                    sum(preliminaries) / len(preliminaries) if preliminaries else None
                ),
                "forecast_pct": sum(forecasts) / len(forecasts) if forecasts else None,
                "final_pl_pct": sum(finals) / completed if completed else None,
                "win_rate_pct": (
                    100.0 * sum(value > 0 for value in finals) / completed
                    if completed
                    else None
                ),
                "completed_picks": completed,
                "status": (
                    "final"
                    if completed and completed >= pick_count
                    else "partial"
                    if completed
                    else "preview"
                    if forecasts
                    else "pending"
                ),
            }
        )
    return sorted(output, key=lambda row: row["date"], reverse=True)


def _model_record(spec: ModelSpec) -> dict[str, Any]:
    journals = _journal_rows(spec)
    outcomes = _outcome_rows(spec)
    returns = [
        value
        for row in outcomes
        if (value := _first_number(row, RETURN_FIELDS)) is not None
    ]
    final_pl = sum(returns) / len(returns) if returns else None
    win_rate = 100.0 * sum(value > 0 for value in returns) / len(returns) if returns else None
    completed = len(returns)
    override_pl, override_win, override_signals = _aggregate_override(spec)
    if not returns and override_signals:
        final_pl, win_rate, completed = override_pl, override_win, override_signals

    ledger = _daily_ledger(journals, outcomes)
    latest = ledger[0] if ledger else None
    pending = sum(
        max(0, row["pick_count"] - row["completed_picks"])
        for row in ledger
        if row["status"] in {"pending", "partial"}
    )
    return {
        "model_id": spec.model_id,
        "name": spec.name,
        "description": spec.description,
        "horizon": spec.horizon,
        "universe": spec.universe,
        "inputs": spec.inputs,
        "state": spec.state,
        "state_note": spec.state_note,
        "active": spec.state == "active",
        "latest_pick_date": latest["date"] if latest else None,
        "latest_picks": latest["picks"] if latest else [],
        "latest_preliminary_pl_pct": latest["preliminary_pl_pct"] if latest else None,
        "latest_forecast_pct": latest["forecast_pct"] if latest else None,
        "final_pl_pct": final_pl,
        "win_rate_pct": win_rate,
        "completed_signals": completed,
        "pending_signals": pending,
        "daily": ledger,
    }


def build_model_monitor_payload() -> dict[str, Any]:
    models = [_model_record(spec) for spec in MODEL_SPECS]
    completed_returns = [
        model["final_pl_pct"]
        for model in models
        if model["completed_signals"] and model["final_pl_pct"] is not None
    ]
    completed_signals = sum(model["completed_signals"] for model in models)
    weighted_wins = sum(
        (model["win_rate_pct"] or 0.0) * model["completed_signals"]
        for model in models
        if model["win_rate_pct"] is not None
    )
    return {
        "status": "success",
        "research_only": True,
        "execution_enabled": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "models": len(models),
            "active": sum(model["state"] == "active" for model in models),
            "attention": sum(model["state"] == "attention" for model in models),
            "blocked": sum(model["state"] == "blocked" for model in models),
            "development": sum(model["state"] == "development" for model in models),
            "preview": sum(model["state"] == "preview" for model in models),
            "pending_signals": sum(model["pending_signals"] for model in models),
            "completed_signals": completed_signals,
            "weighted_win_rate_pct": (
                weighted_wins / completed_signals if completed_signals else None
            ),
            "mean_model_pl_pct": (
                sum(completed_returns) / len(completed_returns)
                if completed_returns
                else None
            ),
        },
        "models": models,
    }


@router.get("/models/data")
def v2_model_monitor_data():
    return build_model_monitor_payload()


@router.get("/models", response_class=HTMLResponse)
def v2_model_monitor_page():
    return HTMLResponse(MODEL_MONITOR_HTML)


MODEL_MONITOR_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AlientAI — Model Intelligence Monitor</title>
  <style>
    :root {
      color-scheme: dark;
      --ink: #edf6ff;
      --muted: #91a7bb;
      --quiet: #60788e;
      --bg: #061018;
      --surface: #0b1923;
      --surface-2: #102431;
      --line: rgba(152, 190, 210, .16);
      --cyan: #55d8dc;
      --cyan-soft: rgba(85, 216, 220, .12);
      --green: #5ee6a8;
      --green-soft: rgba(94, 230, 168, .12);
      --amber: #f5bd63;
      --amber-soft: rgba(245, 189, 99, .12);
      --red: #ff7d83;
      --red-soft: rgba(255, 125, 131, .12);
      --violet: #b9a4ff;
      --violet-soft: rgba(185, 164, 255, .12);
      --shadow: 0 22px 65px rgba(0, 0, 0, .28);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 9% -10%, rgba(85, 216, 220, .16), transparent 31rem),
        radial-gradient(circle at 95% 0%, rgba(185, 164, 255, .11), transparent 30rem),
        linear-gradient(180deg, #07121b 0%, var(--bg) 48%, #050c12 100%);
    }
    button, input { font: inherit; }
    .shell { width: min(1680px, calc(100% - 36px)); margin: 0 auto; padding: 26px 0 48px; }
    .masthead {
      display: flex; align-items: center; justify-content: space-between; gap: 20px;
      padding: 8px 2px 28px;
    }
    .brand { display: flex; align-items: center; gap: 15px; }
    .brand-mark {
      width: 46px; height: 46px; border-radius: 15px; display: grid; place-items: center;
      color: #041316; font-weight: 900; letter-spacing: -.06em;
      background: linear-gradient(145deg, #79edf0, #45bdc4);
      box-shadow: 0 0 0 1px rgba(255,255,255,.18), 0 12px 34px rgba(56,201,208,.24);
    }
    .brand h1 { margin: 0; font-size: clamp(25px, 3vw, 36px); letter-spacing: -.035em; }
    .brand p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .mast-actions { display: flex; align-items: center; gap: 10px; }
    .timestamp { color: var(--muted); font-size: 12px; text-align: right; }
    .refresh {
      border: 1px solid rgba(85,216,220,.28); background: var(--cyan-soft); color: var(--cyan);
      padding: 10px 14px; border-radius: 11px; cursor: pointer; font-weight: 750;
    }
    .refresh:hover { background: rgba(85,216,220,.2); }
    .hero {
      position: relative; overflow: hidden; border: 1px solid var(--line); border-radius: 22px;
      padding: clamp(24px, 4vw, 42px); background: linear-gradient(125deg, rgba(16,36,49,.96), rgba(7,21,30,.96));
      box-shadow: var(--shadow);
    }
    .hero::after {
      content: ""; position: absolute; width: 360px; height: 360px; border-radius: 50%;
      right: -170px; top: -210px; border: 54px solid rgba(85,216,220,.055);
    }
    .eyebrow { color: var(--cyan); text-transform: uppercase; letter-spacing: .14em; font-size: 11px; font-weight: 850; }
    .hero h2 { max-width: 770px; margin: 12px 0 10px; font-size: clamp(28px, 4.4vw, 52px); line-height: 1.03; letter-spacing: -.045em; }
    .hero-copy { max-width: 770px; color: var(--muted); line-height: 1.65; font-size: 15px; }
    .research-flag {
      display: inline-flex; gap: 8px; align-items: center; margin-top: 19px; padding: 8px 11px;
      border-radius: 999px; border: 1px solid rgba(245,189,99,.25); background: var(--amber-soft);
      color: var(--amber); font-size: 12px; font-weight: 750;
    }
    .summary-grid {
      display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin: 18px 0 24px;
    }
    .metric {
      min-height: 115px; border: 1px solid var(--line); border-radius: 16px; padding: 17px;
      background: rgba(11,25,35,.88); box-shadow: 0 12px 36px rgba(0,0,0,.16);
    }
    .metric-label { color: var(--muted); font-size: 11px; letter-spacing: .09em; text-transform: uppercase; font-weight: 750; }
    .metric-value { margin-top: 10px; font-size: 28px; font-weight: 820; letter-spacing: -.035em; }
    .metric-note { color: var(--quiet); font-size: 11px; margin-top: 6px; }
    .toolbar {
      display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap;
      margin-bottom: 13px;
    }
    .filters { display: flex; gap: 7px; flex-wrap: wrap; }
    .filter {
      border: 1px solid var(--line); color: var(--muted); background: rgba(11,25,35,.75);
      padding: 8px 11px; border-radius: 999px; cursor: pointer; font-size: 12px; font-weight: 720;
    }
    .filter.active { border-color: rgba(85,216,220,.4); color: var(--cyan); background: var(--cyan-soft); }
    .search {
      width: min(340px, 100%); color: var(--ink); background: rgba(11,25,35,.82);
      border: 1px solid var(--line); border-radius: 11px; padding: 10px 12px; outline: none;
    }
    .search:focus { border-color: rgba(85,216,220,.48); box-shadow: 0 0 0 3px rgba(85,216,220,.08); }
    .table-card { border: 1px solid var(--line); border-radius: 18px; overflow: hidden; background: rgba(9,22,31,.92); box-shadow: var(--shadow); }
    .table-scroll { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 1190px; }
    th {
      padding: 13px 14px; color: var(--quiet); text-align: left; font-size: 10px;
      text-transform: uppercase; letter-spacing: .095em; background: rgba(16,36,49,.88);
      border-bottom: 1px solid var(--line);
    }
    td { padding: 15px 14px; border-bottom: 1px solid var(--line); vertical-align: top; font-size: 13px; }
    tbody tr { cursor: pointer; transition: background .15s ease; }
    tbody tr:hover { background: rgba(85,216,220,.035); }
    tbody tr:last-child td { border-bottom: 0; }
    .model-name { font-weight: 790; font-size: 14px; }
    .model-description { color: var(--muted); font-size: 11px; line-height: 1.45; margin-top: 5px; max-width: 330px; }
    .state {
      display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 5px 8px;
      font-size: 10px; letter-spacing: .06em; text-transform: uppercase; font-weight: 850;
    }
    .state::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
    .state-active { color: var(--green); background: var(--green-soft); }
    .state-attention { color: var(--amber); background: var(--amber-soft); }
    .state-blocked { color: var(--red); background: var(--red-soft); }
    .state-development { color: var(--violet); background: var(--violet-soft); }
    .state-preview { color: var(--cyan); background: var(--cyan-soft); }
    .picks { display: flex; flex-wrap: wrap; gap: 5px; max-width: 240px; }
    .ticker { padding: 4px 6px; border-radius: 7px; background: rgba(255,255,255,.055); border: 1px solid var(--line); font-size: 11px; font-weight: 780; }
    .number { font-variant-numeric: tabular-nums; font-weight: 760; white-space: nowrap; }
    .positive { color: var(--green); }
    .negative { color: var(--red); }
    .pending { color: var(--muted); font-weight: 550; }
    .empty { padding: 50px 20px; color: var(--muted); text-align: center; }
    .drawer {
      position: fixed; inset: 0; z-index: 20; display: none; justify-content: flex-end;
      background: rgba(2,8,12,.7); backdrop-filter: blur(8px);
    }
    .drawer.open { display: flex; }
    .drawer-panel {
      width: min(760px, 96vw); height: 100%; overflow-y: auto; padding: 25px;
      background: #08151e; border-left: 1px solid var(--line); box-shadow: -25px 0 70px rgba(0,0,0,.42);
    }
    .drawer-head { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
    .drawer h3 { font-size: 25px; margin: 8px 0 6px; letter-spacing: -.03em; }
    .close { border: 1px solid var(--line); background: var(--surface-2); color: var(--ink); width: 38px; height: 38px; border-radius: 11px; cursor: pointer; }
    .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; margin: 19px 0; }
    .detail { border: 1px solid var(--line); border-radius: 13px; padding: 13px; background: var(--surface); }
    .detail-label { color: var(--quiet); font-size: 10px; text-transform: uppercase; letter-spacing: .08em; }
    .detail-value { margin-top: 6px; font-size: 13px; line-height: 1.5; }
    .state-note { border-left: 3px solid var(--cyan); background: var(--cyan-soft); padding: 13px 14px; color: #ccebed; border-radius: 0 11px 11px 0; line-height: 1.55; font-size: 13px; }
    .ledger-title { margin: 24px 0 10px; font-size: 15px; }
    .ledger { min-width: 680px; }
    .ledger td, .ledger th { padding: 11px 9px; }
    .footer { display: flex; justify-content: space-between; gap: 20px; color: var(--quiet); font-size: 11px; margin-top: 20px; line-height: 1.6; }
    @media (max-width: 1100px) { .summary-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    @media (max-width: 700px) {
      .shell { width: min(100% - 22px, 1680px); padding-top: 15px; }
      .masthead { align-items: flex-start; }
      .timestamp { display: none; }
      .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric { min-height: 102px; padding: 14px; }
      .metric-value { font-size: 24px; }
      .detail-grid { grid-template-columns: 1fr; }
      .footer { flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="masthead">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">A</div>
        <div><h1>AlientAI</h1><p>Model Intelligence Monitor</p></div>
      </div>
      <div class="mast-actions">
        <div class="timestamp"><div>Last verified refresh</div><strong id="updatedAt">Loading…</strong></div>
        <button class="refresh" id="refreshButton" type="button">Refresh data</button>
      </div>
    </header>

    <section class="hero">
      <div class="eyebrow">Prospective research control room</div>
      <h2>Every model. Every pick. Every honest outcome.</h2>
      <div class="hero-copy">
        A single read-only view of frozen future-data tests, pending horizons, completed performance,
        blocked pipelines and development candidates. Preliminary marks remain separate from final
        cost-adjusted outcomes.
      </div>
      <div class="research-flag">● Research only · execution disabled</div>
    </section>

    <section class="summary-grid" aria-label="Model program summary">
      <div class="metric"><div class="metric-label">Active models</div><div class="metric-value positive" id="activeCount">—</div><div class="metric-note">Collecting future evidence</div></div>
      <div class="metric"><div class="metric-label">Needs attention</div><div class="metric-value" id="attentionCount">—</div><div class="metric-note">Recoverable journal gaps</div></div>
      <div class="metric"><div class="metric-label">Pending signals</div><div class="metric-value" id="pendingCount">—</div><div class="metric-note">Waiting for full horizons</div></div>
      <div class="metric"><div class="metric-label">Completed signals</div><div class="metric-value" id="completedCount">—</div><div class="metric-note">Exact finalized outcomes</div></div>
      <div class="metric"><div class="metric-label">Weighted win rate</div><div class="metric-value" id="winRate">—</div><div class="metric-note">Across completed signals</div></div>
      <div class="metric"><div class="metric-label">Blocked models</div><div class="metric-value negative" id="blockedCount">—</div><div class="metric-note">Exact blockers retained</div></div>
    </section>

    <section>
      <div class="toolbar">
        <div class="filters" id="filters">
          <button class="filter active" data-filter="all" type="button">All models</button>
          <button class="filter" data-filter="active" type="button">Active</button>
          <button class="filter" data-filter="attention" type="button">Attention</button>
          <button class="filter" data-filter="blocked" type="button">Blocked</button>
          <button class="filter" data-filter="development" type="button">Development</button>
          <button class="filter" data-filter="preview" type="button">Preview</button>
        </div>
        <input class="search" id="search" type="search" placeholder="Search model, universe, horizon or ticker…" aria-label="Search models">
      </div>
      <div class="table-card">
        <div class="table-scroll">
          <table>
            <thead><tr>
              <th>Model</th><th>Status</th><th>Horizon</th><th>Universe</th><th>Latest pick date</th>
              <th>Latest picks</th><th>Preliminary P/L</th><th>Win rate</th><th>Final P/L</th>
            </tr></thead>
            <tbody id="modelRows"></tbody>
          </table>
        </div>
        <div class="empty" id="emptyState" hidden>No models match this view.</div>
      </div>
    </section>

    <footer class="footer">
      <div>Profit/loss figures are averages of exact source-tagged outcomes after recorded costs where available.</div>
      <div>Forecasts, preliminary marks and final outcomes are intentionally not interchangeable.</div>
    </footer>
  </main>

  <aside class="drawer" id="drawer" aria-hidden="true">
    <section class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawerTitle">
      <div class="drawer-head">
        <div><div id="drawerState"></div><h3 id="drawerTitle"></h3><div class="model-description" id="drawerDescription"></div></div>
        <button class="close" id="closeDrawer" type="button" aria-label="Close details">×</button>
      </div>
      <div class="detail-grid">
        <div class="detail"><div class="detail-label">Horizon</div><div class="detail-value" id="drawerHorizon"></div></div>
        <div class="detail"><div class="detail-label">Universe</div><div class="detail-value" id="drawerUniverse"></div></div>
        <div class="detail"><div class="detail-label">Input signals</div><div class="detail-value" id="drawerInputs"></div></div>
        <div class="detail"><div class="detail-label">Evidence</div><div class="detail-value" id="drawerEvidence"></div></div>
      </div>
      <div class="state-note" id="drawerNote"></div>
      <h4 class="ledger-title">Daily pick and outcome ledger</h4>
      <div class="table-card table-scroll">
        <table class="ledger">
          <thead><tr><th>Date</th><th>Picks</th><th>State</th><th>Forecast</th><th>Preliminary</th><th>Final P/L</th><th>Win rate</th></tr></thead>
          <tbody id="ledgerRows"></tbody>
        </table>
      </div>
    </section>
  </aside>

  <script>
    let payload = { models: [], summary: {} };
    let activeFilter = "all";
    const rows = document.getElementById("modelRows");
    const drawer = document.getElementById("drawer");

    const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
    const pct = value => value === null || value === undefined ? "—" : `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;
    const pctClass = value => value === null || value === undefined ? "pending" : value >= 0 ? "positive" : "negative";
    const statePill = state => `<span class="state state-${escapeHtml(state)}">${escapeHtml(state)}</span>`;
    const tickerPills = picks => picks?.length ? `<div class="picks">${picks.map(p => `<span class="ticker">${escapeHtml(p)}</span>`).join("")}</div>` : `<span class="pending">No picks</span>`;

    function updateSummary() {
      const s = payload.summary || {};
      document.getElementById("activeCount").textContent = s.active ?? "—";
      document.getElementById("attentionCount").textContent = s.attention ?? "—";
      document.getElementById("pendingCount").textContent = s.pending_signals ?? "—";
      document.getElementById("completedCount").textContent = s.completed_signals ?? "—";
      document.getElementById("blockedCount").textContent = s.blocked ?? "—";
      document.getElementById("winRate").textContent = s.weighted_win_rate_pct == null ? "—" : `${Number(s.weighted_win_rate_pct).toFixed(1)}%`;
      document.getElementById("updatedAt").textContent = new Date(payload.generated_at_utc).toLocaleString();
    }

    function renderModels() {
      const query = document.getElementById("search").value.trim().toLowerCase();
      const visible = payload.models.filter(model => {
        if (activeFilter !== "all" && model.state !== activeFilter) return false;
        const haystack = [model.name, model.description, model.horizon, model.universe, model.inputs, ...(model.latest_picks || [])].join(" ").toLowerCase();
        return !query || haystack.includes(query);
      });
      rows.innerHTML = visible.map(model => `
        <tr data-model="${escapeHtml(model.model_id)}" tabindex="0">
          <td><div class="model-name">${escapeHtml(model.name)}</div><div class="model-description">${escapeHtml(model.description)}</div></td>
          <td>${statePill(model.state)}</td>
          <td>${escapeHtml(model.horizon)}</td>
          <td>${escapeHtml(model.universe)}</td>
          <td>${escapeHtml(model.latest_pick_date || "—")}</td>
          <td>${tickerPills(model.latest_picks)}</td>
          <td class="${pctClass(model.latest_preliminary_pl_pct)}">${pct(model.latest_preliminary_pl_pct)}</td>
          <td class="${pctClass(model.win_rate_pct)}">${model.win_rate_pct == null ? "—" : `${Number(model.win_rate_pct).toFixed(1)}%`}</td>
          <td class="${pctClass(model.final_pl_pct)} number">${pct(model.final_pl_pct)}</td>
        </tr>`).join("");
      document.getElementById("emptyState").hidden = visible.length > 0;
      [...rows.querySelectorAll("tr")].forEach(row => {
        const open = () => openDrawer(row.dataset.model);
        row.addEventListener("click", open);
        row.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } });
      });
    }

    function openDrawer(modelId) {
      const model = payload.models.find(item => item.model_id === modelId);
      if (!model) return;
      document.getElementById("drawerState").innerHTML = statePill(model.state);
      document.getElementById("drawerTitle").textContent = model.name;
      document.getElementById("drawerDescription").textContent = model.description;
      document.getElementById("drawerHorizon").textContent = model.horizon;
      document.getElementById("drawerUniverse").textContent = model.universe;
      document.getElementById("drawerInputs").textContent = model.inputs;
      document.getElementById("drawerEvidence").textContent = `${model.completed_signals} completed · ${model.pending_signals} pending · ${model.win_rate_pct == null ? "win rate pending" : Number(model.win_rate_pct).toFixed(1) + "% wins"}`;
      document.getElementById("drawerNote").textContent = model.state_note;
      document.getElementById("ledgerRows").innerHTML = model.daily.length ? model.daily.map(day => `
        <tr>
          <td>${escapeHtml(day.date)}</td><td>${tickerPills(day.picks)}</td><td>${escapeHtml(day.status)}</td>
          <td class="${pctClass(day.forecast_pct)}">${pct(day.forecast_pct)}</td>
          <td class="${pctClass(day.preliminary_pl_pct)}">${pct(day.preliminary_pl_pct)}</td>
          <td class="${pctClass(day.final_pl_pct)}">${pct(day.final_pl_pct)}</td>
          <td>${day.win_rate_pct == null ? "—" : Number(day.win_rate_pct).toFixed(1) + "%"}</td>
        </tr>`).join("") : `<tr><td colspan="7" class="pending">No prospective observations recorded.</td></tr>`;
      drawer.classList.add("open");
      drawer.setAttribute("aria-hidden", "false");
      document.getElementById("closeDrawer").focus();
    }

    function closeDrawer() { drawer.classList.remove("open"); drawer.setAttribute("aria-hidden", "true"); }

    async function loadData() {
      const button = document.getElementById("refreshButton");
      button.disabled = true; button.textContent = "Refreshing…";
      try {
        const response = await fetch("/v2/models/data", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        payload = await response.json();
        updateSummary(); renderModels();
      } catch (error) {
        rows.innerHTML = `<tr><td colspan="9" class="negative">Model data could not be loaded. ${escapeHtml(error.message)}</td></tr>`;
      } finally {
        button.disabled = false; button.textContent = "Refresh data";
      }
    }

    document.getElementById("filters").addEventListener("click", event => {
      const button = event.target.closest(".filter");
      if (!button) return;
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button));
      renderModels();
    });
    document.getElementById("search").addEventListener("input", renderModels);
    document.getElementById("refreshButton").addEventListener("click", loadData);
    document.getElementById("closeDrawer").addEventListener("click", closeDrawer);
    drawer.addEventListener("click", event => { if (event.target === drawer) closeDrawer(); });
    document.addEventListener("keydown", event => { if (event.key === "Escape") closeDrawer(); });
    loadData();
    setInterval(loadData, 60000);
  </script>
</body>
</html>
"""
