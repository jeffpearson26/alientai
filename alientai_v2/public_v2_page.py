from __future__ import annotations

import html
from typing import Any, Dict, List

from fastapi.responses import HTMLResponse

from alientai_v2.engine import get_status


BUILD = "ALIENTAI_PUBLIC_V2_PAGE_V1"


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def pct(value: Any) -> str:
    try:
        return f"{float(value):.3f}%"
    except Exception:
        return "0.000%"


def safe_text(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def status_badge(value: Any) -> str:
    text = str(value if value is not None else "").upper().strip()

    cls = "badge neutral"

    if text in {"YES", "RUNNING", "ON", "BUY", "BUY_CANDIDATE", "ALLOW_BUY"}:
        cls = "badge good"
    elif text in {"NO", "OFF", "AVOID", "BLOCK_BUY", "ERROR"}:
        cls = "badge bad"
    elif text in {"WATCH", "WAIT", "WATCH_ONLY"}:
        cls = "badge warn"

    return f'<span class="{cls}">{safe_text(text)}</span>'


def row_value(label: str, value: Any, note: str = "") -> str:
    return f"""
    <div class="metric-card">
      <div class="metric-label">{safe_text(label)}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-note">{safe_text(note)}</div>
    </div>
    """


def render_positions(status: Dict[str, Any]) -> str:
    positions = status.get("open_positions") or {}

    if not isinstance(positions, dict) or not positions:
        return '<div class="empty">No open V2 paper positions.</div>'

    rows = []

    for symbol, pos in positions.items():
        if not isinstance(pos, dict):
            continue

        rows.append(f"""
        <tr>
          <td>{safe_text(symbol)}</td>
          <td>{safe_text(pos.get("engine_id", ""))}</td>
          <td>{safe_text(pos.get("side", ""))}</td>
          <td>{safe_text(pos.get("shares", ""))}</td>
          <td>{money(pos.get("entry_price"))}</td>
          <td>{money(pos.get("last_price"))}</td>
          <td>{pct(pos.get("unrealized_pnl_pct"))}</td>
          <td>{pct(pos.get("trail_drop_pct"))}</td>
          <td>{safe_text(pos.get("prediction_horizon_days", ""))}</td>
          <td>{safe_text(pos.get("quote_source", ""))}</td>
        </tr>
        """)

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Engine</th>
            <th>Side</th>
            <th>Shares</th>
            <th>Entry</th>
            <th>Last</th>
            <th>Unrealized</th>
            <th>Trail Drop</th>
            <th>Horizon Days</th>
            <th>Quote Source</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


def render_candidates(status: Dict[str, Any]) -> str:
    candidates = status.get("top_v2_candidates") or []

    if not isinstance(candidates, list) or not candidates:
        return '<div class="empty">No candidate rows in latest public status.</div>'

    rows = []

    for index, c in enumerate(candidates[:50], start=1):
        if not isinstance(c, dict):
            continue

        engine_id = str(c.get("engine_id") or "")
        decision = str(c.get("decision") or "")
        policy = str(
            c.get("prediction_20day_daily_policy")
            or c.get("similarity_policy")
            or ""
        )

        original_decision = str(
            c.get("prediction_20day_original_decision")
            or c.get("original_decision")
            or ""
        )

        original_score = c.get("prediction_20day_original_score")
        if original_score is None:
            original_score = c.get("original_score", "")

        reason = str(c.get("reason") or "")
        if len(reason) > 180:
            reason = reason[:180] + "..."

        rows.append(f"""
        <tr>
          <td>{index}</td>
          <td>{safe_text(engine_id)}</td>
          <td>{safe_text(c.get("symbol", ""))}</td>
          <td>{status_badge(decision)}</td>
          <td>{safe_text(c.get("score", ""))}</td>
          <td>{money(c.get("price"))}</td>
          <td>{pct(c.get("move_pct"))}</td>
          <td>{safe_text(c.get("relative_volume", ""))}</td>
          <td>{pct(c.get("spread_percent"))}</td>
          <td>{safe_text(c.get("volume", ""))}</td>
          <td>{status_badge(policy) if policy else ""}</td>
          <td>{safe_text(original_decision)}</td>
          <td>{safe_text(original_score)}</td>
          <td>{safe_text(c.get("history_source", ""))}</td>
          <td>{safe_text(reason)}</td>
        </tr>
        """)

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Engine</th>
            <th>Symbol</th>
            <th>Decision</th>
            <th>Score</th>
            <th>Price</th>
            <th>Move %</th>
            <th>Rel Vol</th>
            <th>Spread %</th>
            <th>Volume</th>
            <th>Policy</th>
            <th>Original</th>
            <th>Orig Score</th>
            <th>History</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


def render_actions(title: str, actions: Any) -> str:
    if not isinstance(actions, list) or not actions:
        return f"""
        <section class="panel">
          <h2>{safe_text(title)}</h2>
          <div class="empty">No actions in latest public status.</div>
        </section>
        """

    rows = []

    for a in actions[:20]:
        if not isinstance(a, dict):
            continue

        rows.append(f"""
        <tr>
          <td>{safe_text(a.get("time", a.get("timestamp", "")))}</td>
          <td>{safe_text(a.get("action", ""))}</td>
          <td>{safe_text(a.get("engine_id", ""))}</td>
          <td>{safe_text(a.get("symbol", ""))}</td>
          <td>{safe_text(a.get("shares", ""))}</td>
          <td>{money(a.get("price"))}</td>
          <td>{money(a.get("value"))}</td>
          <td>{money(a.get("pnl"))}</td>
          <td>{safe_text(a.get("reason", ""))}</td>
        </tr>
        """)

    return f"""
    <section class="panel">
      <h2>{safe_text(title)}</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Action</th>
              <th>Engine</th>
              <th>Symbol</th>
              <th>Shares</th>
              <th>Price</th>
              <th>Value</th>
              <th>P/L</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </section>
    """


def render_public_page(status: Dict[str, Any]) -> str:
    updated_at = status.get("updated_at", "")
    last_message = status.get("last_message", "")
    last_action = status.get("last_action", "")

    v2_running = "YES" if status.get("v2_engine_running") else "NO"
    old_brain = "ON" if status.get("old_scanner_decision_making_enabled") else "OFF"
    paper = "ON" if status.get("paper_trading_enabled") else "OFF"

    metrics = ""
    metrics += row_value("V2 Running", status_badge(v2_running), "Clean V2 engine thread")
    metrics += row_value("Old Scanner Brain", status_badge(old_brain), "Expected to stay OFF")
    metrics += row_value("Paper Trading", status_badge(paper), "Research paper mode")
    metrics += row_value("Last Action", status_badge(last_action), f"Last scan: {status.get('last_scan_time', '')}")

    account = ""
    account += row_value("Starting Balance", money(status.get("starting_cash")), "Original V2 paper balance")
    account += row_value("Cash", money(status.get("cash")), "Uninvested paper cash")
    account += row_value("Open Position Value", money(status.get("open_position_value")), "Current value of open positions")
    account += row_value("Account Value", money(status.get("account_value")), "Cash + open positions")
    account += row_value("Realized P/L", money(status.get("realized_pnl")), "Closed V2 paper trades")
    account += row_value("Unrealized P/L", money(status.get("unrealized_pnl")), "Open V2 paper positions")
    account += row_value("Total P/L", money(status.get("total_pnl")), "Account value minus starting balance")
    account += row_value("Total P/L %", pct(status.get("total_pnl_pct")), "Total paper return")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AlientAI Public V2 Research Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <style>
    :root {{
      --bg: #050816;
      --panel: rgba(15, 23, 42, 0.92);
      --panel2: rgba(30, 41, 59, 0.82);
      --text: #e5e7eb;
      --muted: #94a3b8;
      --border: rgba(148, 163, 184, 0.24);
      --good: #22c55e;
      --bad: #ef4444;
      --warn: #f59e0b;
      --blue: #38bdf8;
      --purple: #a78bfa;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 35%),
        radial-gradient(circle at top right, rgba(167, 139, 250, 0.16), transparent 35%),
        linear-gradient(180deg, #020617, #0f172a);
      min-height: 100vh;
    }}

    header {{
      padding: 42px 22px 22px;
      text-align: center;
    }}

    .brand {{
      font-size: 14px;
      letter-spacing: 0.22em;
      color: var(--blue);
      text-transform: uppercase;
      margin-bottom: 8px;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(32px, 6vw, 64px);
      line-height: 1;
    }}

    .subtitle {{
      max-width: 980px;
      margin: 16px auto 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.5;
    }}

    .nav {{
      margin-top: 22px;
      display: flex;
      justify-content: center;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .nav a {{
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--border);
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.72);
    }}

    main {{
      width: min(1500px, calc(100% - 28px));
      margin: 0 auto 60px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}

    .account-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}

    .metric-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 44px rgba(0, 0, 0, 0.24);
    }}

    .metric-card {{
      padding: 16px;
    }}

    .metric-label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .metric-value {{
      margin-top: 8px;
      font-size: 24px;
      font-weight: 700;
    }}

    .metric-note {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
      min-height: 16px;
    }}

    .panel {{
      padding: 18px;
      margin-bottom: 18px;
    }}

    h2 {{
      margin: 0 0 14px;
      font-size: 22px;
    }}

    .message {{
      color: var(--muted);
      line-height: 1.5;
      background: var(--panel2);
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
    }}

    .table-wrap {{
      overflow-x: auto;
      border-radius: 14px;
      border: 1px solid var(--border);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1000px;
      background: rgba(2, 6, 23, 0.45);
    }}

    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      white-space: nowrap;
      font-size: 13px;
    }}

    th {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: 11px;
      background: rgba(15, 23, 42, 0.95);
      position: sticky;
      top: 0;
    }}

    .badge {{
      display: inline-block;
      padding: 4px 9px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      border: 1px solid var(--border);
    }}

    .badge.good {{
      color: #bbf7d0;
      background: rgba(34, 197, 94, 0.16);
      border-color: rgba(34, 197, 94, 0.42);
    }}

    .badge.bad {{
      color: #fecaca;
      background: rgba(239, 68, 68, 0.16);
      border-color: rgba(239, 68, 68, 0.42);
    }}

    .badge.warn {{
      color: #fde68a;
      background: rgba(245, 158, 11, 0.16);
      border-color: rgba(245, 158, 11, 0.42);
    }}

    .badge.neutral {{
      color: #cbd5e1;
      background: rgba(148, 163, 184, 0.12);
    }}

    .empty {{
      color: var(--muted);
      padding: 14px;
      background: var(--panel2);
      border-radius: 12px;
    }}

    footer {{
      color: var(--muted);
      text-align: center;
      padding: 30px 10px 50px;
      font-size: 13px;
    }}

    @media (max-width: 900px) {{
      .grid, .account-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}

    @media (max-width: 580px) {{
      .grid, .account-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">AlientAI</div>
    <h1>Public V2 Research Monitor</h1>
    <div style="
      display:inline-flex;
      align-items:center;
      gap:8px;
      margin:10px 0 18px 0;
      padding:8px 14px;
      border:1px solid rgba(255,255,255,0.18);
      border-radius:999px;
      background:rgba(255,255,255,0.08);
      color:#dbeafe;
      font-size:14px;
      font-weight:700;
      letter-spacing:0.3px;
    ">
      Built by JEP26
    </div>

    <div style="
      margin:12px 0 20px 0;
      padding:14px 16px;
      border:1px solid rgba(96,165,250,0.28);
      border-radius:16px;
      background:rgba(30,64,175,0.16);
      color:#dbeafe;
      line-height:1.45;
      max-width:980px;
    ">
      <div style="font-size:15px;font-weight:800;margin-bottom:6px;">
        Autonomous Trading System
      </div>
      <div style="font-size:14px;color:#bfdbfe;">
        AlientAI V2 is an autonomous experimental paper-trading system. Four trading engines are currently active from a planned total of eight.
      </div>
      <div style="font-size:13px;color:#93c5fd;margin-top:8px;">
        Active engines: <strong>prediction_20day</strong>, <strong>momentum_5min</strong>, <strong>similarity_engine</strong>, and <strong>transformer_20day</strong>.
      </div>
    </div>


    <div class="subtitle">
      Read-only experimental market intelligence monitor. This page displays V2 paper-trading status,
      engine signals, replay-policy context, and candidate rankings. It does not expose owner controls.
    </div>
    <div class="public-note">
      Read-only public view. Owner controls are not shown on this page.
    </div>
  </header>

  <main>
    <section class="grid">
      {metrics}
    </section>

    <section class="panel">
      <h2>V2 Message</h2>
      <div class="message">
        <strong>Updated:</strong> {safe_text(updated_at)}<br>
        <strong>Message:</strong> {safe_text(last_message)}<br>
        <strong>Build:</strong> {safe_text(BUILD)}
      </div>
    </section>

    <section class="account-grid">
      {account}
    </section>

    <section class="panel">
      <h2>Open V2 Paper Positions</h2>
      {render_positions(status)}
    </section>

    <section class="panel">
      <h2>Top V2 Candidates</h2>
      {render_candidates(status)}
    </section>

    {render_actions("Latest Buy Actions", status.get("buy_actions"))}
    {render_actions("Latest Sell Actions", status.get("sell_actions"))}
  </main>

  <footer>
    AlientAI V2 is an experimental paper-trading research system. This is not financial advice.
  </footer>
</body>
</html>
"""


async def public_v2_page() -> HTMLResponse:
    status = get_status()
    return HTMLResponse(render_public_page(status))


