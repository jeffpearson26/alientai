from pathlib import Path
import json
"""
AlientAI V2 routes and monitor page.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from alientai_v2.engine import (
    BUILD,
    get_status,
    run_one_scan,
    sell_all,
    sell_one_symbol,
    start_engine,
    stop_engine,
)

router = APIRouter(prefix="/v2", tags=["AlientAI V2"])






def _read_v2_engine_accounts_summary_file():
    """
    Directly read the reconstructed per-engine account summary.
    This is research-only and does not place trades.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        summary_path = project_root / "data_v2" / "engine_accounts" / "engine_accounts_summary.json"

        document = (
            json.loads(summary_path.read_text(encoding="utf-8"))
            if summary_path.exists() else {"engines": []}
        )
        status = get_status()
        enabled = [
            str(value) for value in status.get("enabled_engines", [])
            if str(value).strip()
        ]
        historical = {
            str(row.get("engine_id") or ""): row
            for row in document.get("engines", [])
            if isinstance(row, dict)
        }
        engines = []
        for engine_id in enabled:
            row = historical.get(engine_id)
            if row is not None:
                engines.append(row)
                continue
            engines.append({
                "engine_id": engine_id,
                "account_value": status.get("account_value", 0.0),
                "total_pnl": status.get("total_pnl", 0.0),
                "total_pnl_pct": status.get("total_pnl_pct", 0.0),
                "realized_pnl": status.get("realized_pnl", 0.0),
                "unrealized_pnl": status.get("unrealized_pnl", 0.0),
                "open_positions_count": status.get("open_positions_count", 0),
                "closed_trades_count": 0,
                "closed_win_rate_pct": 0.0,
                "profit_factor": None,
                "current_shared_paper_account": True,
            })
        return {
            "status": "success",
            "engines": engines,
            "note": "Only currently enabled paper engines are shown.",
        }

    except Exception as exc:
        return {
            "status": "error",
            "engines": [],
            "error": str(exc),
            "note": "Could not read engine accounts summary.",
        }


@router.get("/engine-accounts")
def v2_engine_accounts_summary():
    """
    Owner monitor endpoint for per-engine paper account scoreboard.
    """
    return _read_v2_engine_accounts_summary_file()


def _read_v2_options_paper_account_file():
    """
    Directly read the separate V2 options paper account file.
    This endpoint is used by the owner monitor.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        account_path = project_root / "data_v2" / "v2_options_paper_account.json"

        if account_path.exists():
            account = json.loads(account_path.read_text(encoding="utf-8-sig"))
            if isinstance(account, dict):
                return {
                    "status": "success",
                    "source": str(account_path),
                    "account": account,
                }

        return {
            "status": "missing",
            "source": str(account_path),
            "account": {
                "starting_balance": 1000.0,
                "cash": 1000.0,
                "open_option_positions": {},
                "closed_option_trades": [],
                "actions": [],
                "open_option_value": 0.0,
                "unrealized_pnl": 0.0,
                "account_value": 1000.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
                "note": "Separate options paper account. This does not place real trades.",
            },
        }

    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "account": {},
        }


@router.get("/status")
def v2_status():
    return get_status()


@router.post("/start")
def v2_start():
    return start_engine()


@router.post("/stop")
def v2_stop():
    return stop_engine()


@router.post("/scan-once")
def v2_scan_once():
    return run_one_scan()


@router.post("/sell-all")
def v2_sell_all():
    return sell_all()


@router.get("/build")
def v2_build():
    return {
        "status": "success",
        "build": BUILD,
        "message": "AlientAI V2 route is installed.",
        "old_scanner_decision_making_enabled": False,
    }




@router.get("/options-paper-account")
def v2_options_paper_account():
    return _read_v2_options_paper_account_file()


@router.get("/monitor", response_class=HTMLResponse)
def v2_monitor():
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>AlientAI V2 Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
    :root {
      --bg: #070b14;
      --panel: #111827;
      --panel2: #172033;
      --border: #2b3754;
      --text: #e5eefc;
      --muted: #94a3b8;
      --good: #5ee787;
      --bad: #ff6b6b;
      --warn: #ffd166;
      --blue: #60a5fa;
      --purple: #c084fc;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 18px;
      background:
        radial-gradient(circle at top left, rgba(96,165,250,0.18), transparent 34%),
        radial-gradient(circle at top right, rgba(192,132,252,0.13), transparent 30%),
        var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }

    #optionsPaperAccountSection { display: none !important; }

    a {
      color: var(--blue);
      text-decoration: none;
    }

    .wrap {
      max-width: 1600px;
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 16px;
    }

    .title h1 {
      margin: 0;
      font-size: 30px;
      letter-spacing: 0.3px;
    }

    .subtitle {
      margin-top: 6px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }

    .nav {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }

    .nav a {
      background: rgba(96,165,250,0.12);
      border: 1px solid rgba(96,165,250,0.25);
      padding: 9px 11px;
      border-radius: 10px;
      font-size: 13px;
    }

    .notice {
      background: rgba(94,231,135,0.10);
      border: 1px solid rgba(94,231,135,0.35);
      color: #d9ffe4;
      padding: 12px 14px;
      border-radius: 12px;
      margin-bottom: 16px;
      font-size: 14px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .account-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 0;
    }

    .card {
      background: rgba(17,24,39,0.92);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.22);
    }

    .metric-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }

    .metric-value {
      margin-top: 7px;
      font-size: 24px;
      font-weight: 700;
      word-break: break-word;
    }

    .small {
      font-size: 13px;
      color: var(--muted);
      margin-top: 6px;
      line-height: 1.35;
    }

    .good { color: var(--good); }
    .bad { color: var(--bad); }
    .warn { color: var(--warn); }
    .blue { color: var(--blue); }
    .purple { color: var(--purple); }

    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
    }

    button {
      border: 1px solid var(--border);
      border-radius: 11px;
      background: var(--panel2);
      color: var(--text);
      padding: 11px 14px;
      cursor: pointer;
      font-weight: 700;
      font-size: 14px;
    }

    button:hover { filter: brightness(1.15); }

    button.start {
      background: rgba(34,197,94,0.20);
      border-color: rgba(34,197,94,0.5);
    }

    button.stop {
      background: rgba(248,113,113,0.20);
      border-color: rgba(248,113,113,0.5);
    }

    button.scan {
      background: rgba(96,165,250,0.20);
      border-color: rgba(96,165,250,0.5);
    }

    button.sell {
      background: rgba(251,191,36,0.18);
      border-color: rgba(251,191,36,0.5);
    }

    .section {
      margin-bottom: 16px;
    }

    .section h2 {
      margin: 0 0 10px 0;
      font-size: 18px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      overflow: hidden;
    }

    th, td {
      text-align: left;
      padding: 9px 8px;
      border-bottom: 1px solid rgba(43,55,84,0.75);
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(23,32,51,0.65);
    }

    tr:hover td {
      background: rgba(96,165,250,0.04);
    }

    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
    }

    .pill.good {
      border-color: rgba(94,231,135,0.5);
      background: rgba(94,231,135,0.10);
    }

    .pill.bad {
      border-color: rgba(255,107,107,0.5);
      background: rgba(255,107,107,0.10);
    }

    .pill.warn {
      border-color: rgba(255,209,102,0.5);
      background: rgba(255,209,102,0.10);
    }

    .pill.blue {
      border-color: rgba(96,165,250,0.5);
      background: rgba(96,165,250,0.10);
    }

    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #020617;
      border: 1px solid var(--border);
      padding: 12px;
      border-radius: 12px;
      max-height: 260px;
      overflow: auto;
      color: #cbd5e1;
      font-size: 12px;
    }

    .two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    @media (max-width: 1100px) {
      .grid { grid-template-columns: repeat(3, minmax(150px, 1fr)); }
      .account-grid { grid-template-columns: repeat(2, minmax(150px, 1fr)); }
      .two { grid-template-columns: 1fr; }
    }

    @media (max-width: 700px) {
      body { padding: 12px; }
      .topbar { flex-direction: column; }
      .nav { justify-content: flex-start; }
      .grid { grid-template-columns: repeat(2, minmax(135px, 1fr)); }
      .account-grid { grid-template-columns: repeat(1, minmax(150px, 1fr)); }
      table { font-size: 12px; }
      th, td { padding: 7px 6px; }
    }
  </style>
</head>

<body>
<div class="wrap">

  <div class="topbar">
    <div class="title">
      <h1>AlientAI V2 Monitor</h1>
      <div class="subtitle">
        New V2 paper engine monitor. This page watches <b>/v2/status</b>.
        Old scanner decision-making is expected to stay OFF.
      </div>
    </div>

    <div class="nav">
      <a href="/v2/status" target="_blank">V2 JSON</a>
      <a href="/quote-debug/AAPL" target="_blank">Quote Test</a>
      <a href="/dashboard" target="_blank">Old Dashboard</a>
      <a href="/" target="_blank">Home</a>
    </div>
  </div>

  <div class="notice" id="notice">Loading V2 status...</div>

  <div class="controls">
    <button class="start" onclick="postAction('/v2/start')">Start V2</button>
    <button class="stop" onclick="postAction('/v2/stop')">Stop V2</button>
    <button class="scan" onclick="postAction('/v2/scan-once')">Scan Once</button>
    <button class="sell" onclick="confirmSellAll()">Sell All V2 Paper</button>
    <button onclick="loadStatus()">Refresh</button>
  </div>

  <div class="grid">
    <div class="card">
      <div class="metric-label">V2 Running</div>
      <div class="metric-value" id="running">...</div>
      <div class="small">Engine thread status</div>
    </div>

    <div class="card">
      <div class="metric-label">Old Scanner Brain</div>
      <div class="metric-value" id="oldbrain">...</div>
      <div class="small">Should be OFF</div>
    </div>

    <div class="card">
      <div class="metric-label">Paper Trading</div>
      <div class="metric-value" id="paper">...</div>
      <div class="small">V2 paper mode</div>
    </div>

    <div class="card">
      <div class="metric-label">Cash</div>
      <div class="metric-value" id="cash">...</div>
      <div class="small">V2 paper cash</div>
    </div>

    <div class="card">
      <div class="metric-label">Open Positions</div>
      <div class="metric-value" id="positions">...</div>
      <div class="small">Current V2 holdings</div>
    </div>

    <div class="card">
      <div class="metric-label">Last Action</div>
      <div class="metric-value" id="lastAction">...</div>
      <div class="small" id="lastScan">...</div>
    </div>
  </div>

  <div class="section card">
    <h2>V2 Account Balance / Profit & Loss</h2>
    <div class="account-grid">
      <div class="card">
        <div class="metric-label">Starting Balance</div>
        <div class="metric-value" id="startingBalance">...</div>
        <div class="small">Original V2 paper balance</div>
      </div>

      <div class="card">
        <div class="metric-label">Cash</div>
        <div class="metric-value" id="accountCash">...</div>
        <div class="small">Uninvested paper cash</div>
      </div>

      <div class="card">
        <div class="metric-label">Open Position Value</div>
        <div class="metric-value" id="openValue">...</div>
        <div class="small">Current value of open positions</div>
      </div>

      <div class="card">
        <div class="metric-label">Account Value</div>
        <div class="metric-value" id="accountValue">...</div>
        <div class="small">Cash + open position value</div>
      </div>

      <div class="card">
        <div class="metric-label">Realized P/L</div>
        <div class="metric-value" id="realizedPnl">...</div>
        <div class="small">Closed V2 paper trades</div>
      </div>

      <div class="card">
        <div class="metric-label">Unrealized P/L</div>
        <div class="metric-value" id="unrealizedPnl">...</div>
        <div class="small">Open V2 paper positions</div>
      </div>

      <div class="card">
        <div class="metric-label">Total P/L</div>
        <div class="metric-value" id="totalPnl">...</div>
        <div class="small">Account value minus starting balance</div>
      </div>

      <div class="card">
        <div class="metric-label">Total P/L %</div>
        <div class="metric-value" id="totalPnlPct">...</div>
        <div class="small">Total return</div>
      </div>
    </div>
  </div>


  <div class="section card">
    <h2>Active Paper Engine</h2>
    <div class="small">
      Only the currently enabled paper engine is shown.
    </div>
    <div id="engineAccountsTable">Loading...</div>
  </div>

  <div class="section card">
    <h2>Open V2 Paper Positions</h2>
    <div id="openPositionsTable">Loading...</div>
  </div>

  <div class="section card">
    <h2>Top V2 Candidates</h2>
    <div id="candidatesTable">Loading...</div>
  </div>

  <div class="two">
    <div class="section card">
      <h2>Latest Buy Actions</h2>
      <div id="buyActionsTable">Loading...</div>
    </div>

    <div class="section card">
      <h2>Latest Sell Actions</h2>
      <div id="sellActionsTable">Loading...</div>
    </div>
  </div>

  <div class="section card">
    <h2>V2 Message</h2>
    <pre id="messageBox">Loading...</pre>
  </div>

</div>

<script>
function money(value) {
  const n = Number(value || 0);
  return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function num(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll(String.fromCharCode(34), "&quot;")
    .replaceAll("'", "&#039;");
}

function minutesToDuration(value) {
  const total = Math.max(0, Math.floor(Number(value || 0)));
  const days = Math.floor(total / 1440);
  const hours = Math.floor((total % 1440) / 60);
  const minutes = total % 60;

  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function daysText(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return "";
  if (Math.abs(n - Math.round(n)) < 0.001) return `${Math.round(n)}d`;
  return `${n.toFixed(2)}d`;
}

function pnlHtml(value, isPercent = false) {
  const n = Number(value || 0);
  const cls = n > 0 ? "good" : (n < 0 ? "bad" : "warn");
  const text = isPercent ? `${num(n, 3)}%` : money(n);
  return `<span class="${cls}">${text}</span>`;
}

function pill(text, kind) {
  return `<span class="pill ${kind || ""}">${escapeHtml(text)}</span>`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setHtml(id, value) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = value;
}

async function loadStatus() {
  try {
    const res = await fetch("/v2/status?t=" + Date.now());
    const data = await res.json();
    render(data);
  } catch (err) {
    setHtml("notice", `<span class="bad">Could not load /v2/status:</span> ${escapeHtml(err)}`);
  }
}

async function postAction(url) {
  setHtml("notice", `Running ${escapeHtml(url)}...`);

  try {
    const res = await fetch(url, { method: "POST" });
    const data = await res.json();
    render(data);
    setTimeout(loadStatus, 1200);
  } catch (err) {
    setHtml("notice", `<span class="bad">Action failed:</span> ${escapeHtml(err)}`);
  }
}

function confirmSellAll() {
  if (!confirm("Sell all open V2 paper positions?")) return;
  postAction("/v2/sell-all");
}

function render(data) {
  const running = !!data.v2_engine_running;
  const oldBrain = !!data.old_scanner_decision_making_enabled;
  const paper = !!data.paper_trading_enabled;

  setHtml("running", running ? `<span class="good">YES</span>` : `<span class="bad">NO</span>`);
  setHtml("oldbrain", oldBrain ? `<span class="bad">ON</span>` : `<span class="good">OFF</span>`);
  setHtml("paper", paper ? `<span class="good">ON</span>` : `<span class="bad">OFF</span>`);

  setText("cash", money(data.cash));
  setText("positions", data.open_positions_count ?? 0);

  const action = data.last_action || "WAIT";
  let actionClass = "warn";
  if (action === "BUY") actionClass = "good";
  if (action === "SELL" || action === "SELL_ALL") actionClass = "blue";
  if (action === "ERROR") actionClass = "bad";

  setHtml("lastAction", `<span class="${actionClass}">${escapeHtml(action)}</span>`);
  setText("lastScan", data.last_scan_time ? "Last scan: " + data.last_scan_time : "Last scan: none");

  const msg = String(data.last_message || "").toLowerCase();
  const quoteOk = !msg.includes("schwab quotes failed") && !msg.includes("http 401") && !msg.includes("invalid_grant");

  setHtml("notice",
    `${running ? pill("V2 RUNNING", "good") : pill("V2 STOPPED", "bad")}
     ${paper ? pill("PAPER ON", "good") : pill("PAPER OFF", "bad")}
     ${oldBrain ? pill("OLD BRAIN ON", "bad") : pill("OLD BRAIN OFF", "good")}
     ${quoteOk ? pill("NO QUOTE ERROR", "good") : pill("QUOTE ERROR", "bad")}`
  );

  setText("startingBalance", money(data.starting_cash));
  setText("accountCash", money(data.cash));
  setText("openValue", money(data.open_position_value));
  setText("accountValue", money(data.account_value));
  setHtml("realizedPnl", pnlHtml(data.realized_pnl));
  setHtml("unrealizedPnl", pnlHtml(data.unrealized_pnl));
  setHtml("totalPnl", pnlHtml(data.total_pnl));
  setHtml("totalPnlPct", pnlHtml(data.total_pnl_pct, true));

  setText("messageBox", JSON.stringify({
    updated_at: data.updated_at,
    last_message: data.last_message,
    last_action: data.last_action,
    last_scan_time: data.last_scan_time,
    enabled_engines: data.enabled_engines,
    paper_buys_today: data.paper_buys_today,
    max_new_buys_per_day: data.max_new_buys_per_day,
    paper_buys_remaining_today: data.paper_buys_remaining_today,
    note: data.note
  }, null, 2));

  renderOpenPositions(data.open_positions || {});
  renderCandidates(data.top_v2_candidates || []);
  renderActions("buyActionsTable", data.buy_actions || []);
  renderActions("sellActionsTable", data.sell_actions || []);
}

function renderOpenPositions(openPositions) {
  const symbols = Object.keys(openPositions);

  if (!symbols.length) {
    setHtml("openPositionsTable", `<div class="small">No open V2 paper positions.</div>`);
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Engine</th>
          <th>Side</th>
          <th>Shares</th>
          <th>Entry</th>
          <th>Last</th>
          <th>High</th>
          <th>Cost</th>
          <th>Unrealized %</th>
          <th>Trail Drop %</th>
          <th>Prediction</th>
          <th>Age</th>
          <th>Countdown</th>
          <th>Sell Lock</th>
          <th>Entry Model Score %</th>
          <th>Quote Source</th>
          <th>Sell Blocked Reason</th>
          <th>Entry Time</th>
        </tr>
      </thead>
      <tbody>
  `;

  for (const symbol of symbols) {
    const p = openPositions[symbol] || {};
    const pnl = Number(p.unrealized_pnl_pct || 0);
    const pnlClass = pnl > 0 ? "good" : (pnl < 0 ? "bad" : "warn");
    const locked = p.min_hold_complete === true ? false : true;

    html += `
      <tr>
        <td><b>${escapeHtml(symbol)}</b></td>
        <td>${escapeHtml(p.engine_id || "")}</td>
        <td>${escapeHtml(p.side || "")}</td>
        <td>${escapeHtml(p.shares || "")}</td>
        <td>${money(p.entry_price)}</td>
        <td>${money(p.last_price)}</td>
        <td>${money(p.highest_price)}</td>
        <td>${money(p.cost)}</td>
        <td class="${pnlClass}">${p.unrealized_pnl_pct !== undefined ? num(p.unrealized_pnl_pct, 3) + "%" : ""}</td>
        <td>${p.trail_drop_pct !== undefined ? num(p.trail_drop_pct, 3) + "%" : ""}</td>
        <td>${daysText(p.prediction_horizon_days)}</td>
        <td>${p.age_minutes !== undefined ? minutesToDuration(p.age_minutes) : ""}</td>
        <td>${p.minutes_until_sell_allowed !== undefined ? minutesToDuration(p.minutes_until_sell_allowed) : ""}</td>
        <td>${locked ? pill("LOCKED", "warn") : pill("UNLOCKED", "good")}</td>
        <td>${escapeHtml(p.entry_score || "")}</td>
        <td>${escapeHtml(p.quote_source || "")}</td>
        <td>${escapeHtml(p.last_sell_blocked_reason || "")}</td>
        <td>${escapeHtml(p.entry_time || "")}</td>
      </tr>
    `;
  }

  html += `</tbody></table>`;
  setHtml("openPositionsTable", html);
}

function renderCandidates(rows) {
  if (!rows.length) {
    setHtml("candidatesTable", `<div class="small">No candidate rows in the latest V2 status yet. Run Scan Once.</div>`);
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Engine</th>
          <th>Symbol</th>
          <th>Decision</th>
          <th>Model Score %</th>
          <th>Daily Cutoff %</th>
          <th>Price</th>
          <th>Move %</th>
          <th>Rel Vol</th>
          <th>Spread %</th>
          <th>Volume</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
  `;

  rows.forEach((r, index) => {
    const score = Number(r.model_score_pct ?? r.score ?? 0);
    const kind = "";
    html += `
      <tr>
        <td>${index + 1}</td>
        <td>${escapeHtml(r.engine_id || "")}</td>
        <td><b>${escapeHtml(r.symbol || "")}</b></td>
        <td>${pill(r.decision || "", kind)}</td>
        <td>${num(score, 2)}</td>
        <td>${num(r.selection_cutoff_pct, 2)}</td>
        <td>${money(r.price)}</td>
        <td>${num(r.move_pct, 3)}%</td>
        <td>${num(r.relative_volume, 3)}</td>
        <td>${num(r.spread_percent, 4)}%</td>
        <td>${r.volume !== undefined ? Number(r.volume).toLocaleString() : ""}</td>
        <td>${escapeHtml(r.source || "")}</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  setHtml("candidatesTable", html);
}

function renderActions(elementId, rows) {
  if (!rows.length) {
    setHtml(elementId, `<div class="small">No actions in the latest status response.</div>`);
    return;
  }

  let html = `
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
  `;

  rows.forEach((r) => {
    const action = r.action || "";
    const kind = action === "BUY" ? "good" : "blue";
    html += `
      <tr>
        <td>${escapeHtml(r.time || "")}</td>
        <td>${pill(action, kind)}</td>
        <td>${escapeHtml(r.engine_id || "")}</td>
        <td><b>${escapeHtml(r.symbol || "")}</b></td>
        <td>${escapeHtml(r.shares || "")}</td>
        <td>${money(r.price || r.exit_price)}</td>
        <td>${money(r.value)}</td>
        <td>${r.pnl !== undefined ? money(r.pnl) : ""}</td>
        <td>${escapeHtml(r.reason || "")}</td>
      </tr>
    `;
  });

  html += `</tbody></table>`;
  setHtml(elementId, html);
}

loadStatus();
setInterval(loadStatus, 10000);
</script>

<script id="v2-click-sell-open-position-js">
async function v2SellOpenPositionNow(symbol) {
  symbol = String(symbol || "").trim().toUpperCase();
  if (!symbol) return;

  const rowNote = document.getElementById("v2-click-sell-note");
  if (rowNote) {
    rowNote.textContent = "Selling " + symbol + " now...";
  }

  try {
    const res = await fetch("/v2/sell-position/" + encodeURIComponent(symbol), {
      method: "POST"
    });

    const data = await res.json();

    if (rowNote) {
      rowNote.textContent = data.last_message || ("Sell request sent for " + symbol);
    }

    setTimeout(function () {
      window.location.reload();
    }, 700);

  } catch (err) {
    if (rowNote) {
      rowNote.textContent = "Sell failed for " + symbol + ": " + err;
    } else {
      alert("Sell failed for " + symbol + ": " + err);
    }
  }
}

function v2FindOpenPositionsTable() {
  const all = Array.from(document.querySelectorAll("h1,h2,h3,h4,div,section"));
  const heading = all.find(el => String(el.textContent || "").includes("Open V2 Paper Positions"));
  if (!heading) return null;

  let node = heading;
  for (let i = 0; i < 12 && node; i++) {
    node = node.nextElementSibling;
    if (!node) break;

    if (node.tagName && node.tagName.toLowerCase() === "table") {
      return node;
    }

    const table = node.querySelector ? node.querySelector("table") : null;
    if (table) return table;
  }

  return null;
}

function v2InstallClickToSellRows() {
  const table = v2FindOpenPositionsTable();
  if (!table) return;

  if (!document.getElementById("v2-click-sell-note")) {
    const note = document.createElement("div");
    note.id = "v2-click-sell-note";
    note.style.margin = "8px 0 10px 0";
    note.style.fontSize = "13px";
    note.style.color = "#fbbf24";
    note.textContent = "Owner control: click an open position row to sell it immediately.";
    table.parentNode.insertBefore(note, table);
  }

  const rows = Array.from(table.querySelectorAll("tr")).slice(1);

  rows.forEach(row => {
    const cells = row.querySelectorAll("td");
    if (!cells || cells.length < 1) return;

    const symbol = String(cells[0].textContent || "").trim().toUpperCase();
    if (!symbol || symbol === "SYMBOL") return;

    if (row.dataset.v2ClickSellInstalled === "1") return;
    row.dataset.v2ClickSellInstalled = "1";

    row.style.cursor = "pointer";
    row.title = "Click to sell " + symbol + " immediately";

    row.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      v2SellOpenPositionNow(symbol);
    });

    const btn = document.createElement("button");
    btn.textContent = "SELL NOW";
    btn.style.padding = "5px 8px";
    btn.style.borderRadius = "8px";
    btn.style.border = "1px solid rgba(248,113,113,0.55)";
    btn.style.background = "rgba(127,29,29,0.80)";
    btn.style.color = "#fee2e2";
    btn.style.fontWeight = "800";
    btn.style.cursor = "pointer";

    btn.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      v2SellOpenPositionNow(symbol);
    });

    const sellCell = document.createElement("td");
    sellCell.appendChild(btn);
    row.appendChild(sellCell);
  });
}

setInterval(v2InstallClickToSellRows, 1000);
window.addEventListener("load", v2InstallClickToSellRows);
</script>


<script id="v2-open-position-price-arrows-js">
(function () {
  function parseMoney(text) {
    text = String(text || "")
      .replace(/[$,%]/g, "")
      .replace(/,/g, "")
      .trim();

    const value = Number.parseFloat(text);
    return Number.isFinite(value) ? value : null;
  }

  function findOpenPositionsTable() {
    const possibleHeadings = Array.from(document.querySelectorAll("h1,h2,h3,h4,div,section,p,strong"));
    const heading = possibleHeadings.find(el =>
      String(el.textContent || "").includes("Open V2 Paper Positions")
    );

    if (!heading) return null;

    let node = heading;

    for (let i = 0; i < 15 && node; i++) {
      node = node.nextElementSibling;
      if (!node) break;

      if (node.tagName && node.tagName.toLowerCase() === "table") {
        return node;
      }

      const table = node.querySelector ? node.querySelector("table") : null;
      if (table) return table;
    }

    return null;
  }

  function headerIndex(headers, names) {
    const lowerNames = names.map(n => n.toLowerCase());

    for (let i = 0; i < headers.length; i++) {
      const label = String(headers[i].textContent || "").trim().toLowerCase();

      if (lowerNames.some(name => label === name || label.includes(name))) {
        return i;
      }
    }

    return -1;
  }

  function installPriceArrows() {
    const table = findOpenPositionsTable();
    if (!table) return;

    const headerCells = Array.from(table.querySelectorAll("tr:first-child th, tr:first-child td"));
    if (!headerCells.length) return;

    const symbolIdx = headerIndex(headerCells, ["symbol"]);
    const priceIdx = headerIndex(headerCells, ["last", "current price", "current", "price"]);

    if (symbolIdx < 0 || priceIdx < 0) return;

    const rows = Array.from(table.querySelectorAll("tr")).slice(1);

    rows.forEach(row => {
      const cells = Array.from(row.querySelectorAll("td"));
      if (cells.length <= Math.max(symbolIdx, priceIdx)) return;

      const symbol = String(cells[symbolIdx].textContent || "").trim().toUpperCase();
      if (!symbol || symbol === "SYMBOL") return;

      const priceCell = cells[priceIdx];

      // Remove old arrow before recalculating, so refreshes do not duplicate arrows.
      const oldArrow = priceCell.querySelector(".v2-price-direction-arrow");
      if (oldArrow) oldArrow.remove();

      const currentPrice = parseMoney(priceCell.textContent);
      if (currentPrice === null || currentPrice <= 0) return;

      const key = "alientai_v2_last_open_price_" + symbol;
      const previousRaw = window.localStorage.getItem(key);
      const previousPrice = previousRaw ? Number.parseFloat(previousRaw) : null;

      let arrow = "▬";
      let color = "#94a3b8";
      let title = "First reading / unchanged";

      if (Number.isFinite(previousPrice) && previousPrice > 0) {
        if (currentPrice > previousPrice) {
          arrow = "▲";
          color = "#22c55e";
          title = "Price increased from $" + previousPrice.toFixed(2) + " to $" + currentPrice.toFixed(2);
        } else if (currentPrice < previousPrice) {
          arrow = "▼";
          color = "#ef4444";
          title = "Price decreased from $" + previousPrice.toFixed(2) + " to $" + currentPrice.toFixed(2);
        } else {
          arrow = "▬";
          color = "#94a3b8";
          title = "Price unchanged at $" + currentPrice.toFixed(2);
        }
      }

      const span = document.createElement("span");
      span.className = "v2-price-direction-arrow";
      span.textContent = " " + arrow;
      span.title = title;
      span.style.fontWeight = "900";
      span.style.fontSize = "15px";
      span.style.marginLeft = "4px";
      span.style.color = color;

      priceCell.appendChild(span);

      // Save current price for next refresh/comparison.
      window.localStorage.setItem(key, String(currentPrice));
    });
  }

  window.v2InstallOpenPositionPriceArrows = installPriceArrows;

  window.addEventListener("load", installPriceArrows);

  // The monitor updates dynamically, so keep reapplying.
  setInterval(installPriceArrows, 1500);
})();
</script>


<script>

async function refreshEngineAccounts() {
  try {
    const res = await fetch("/v2/engine-accounts?ts=" + Date.now());
    const data = await res.json();
    renderEngineAccounts(data);
  } catch (err) {
    setHtml("engineAccountsTable", `<div class="small">Engine accounts unavailable: ${escapeHtml(String(err))}</div>`);
  }
}


function pct(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return "";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(3)}%`;
}

function renderEngineAccounts(data) {
  const engines = Array.isArray(data.engines) ? data.engines : [];

  if (!engines.length) {
    setHtml("engineAccountsTable", `<div class="small">No engine account summary yet. Run build_v2_engine_accounts_v1.py.</div>`);
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Engine</th>
          <th>Value</th>
          <th>P/L</th>
          <th>P/L %</th>
          <th>Open</th>
          <th>Closed</th>
          <th>Win %</th>
          <th>Profit Factor</th>
        </tr>
      </thead>
      <tbody>
  `;

  for (const e of engines) {
    const engineId = e.engine_id || "";
    const pnl = Number(e.total_pnl || 0);
    const pnlPct = Number(e.total_pnl_pct || 0);

    html += `
      <tr>
        <td>${escapeHtml(engineId)}</td>
        <td>${money(e.account_value)}</td>
        <td>${money(pnl)}</td>
        <td>${pct(pnlPct)}</td>
        <td>${escapeHtml(String(e.open_positions_count ?? 0))}</td>
        <td>${escapeHtml(String(e.closed_trades_count ?? 0))}</td>
        <td>${pct(e.closed_win_rate_pct)}</td>
        <td>${e.profit_factor === null || e.profit_factor === undefined ? "" : escapeHtml(String(e.profit_factor))}</td>
      </tr>
    `;
  }

  html += `
      </tbody>
    </table>
  `;

  setHtml("engineAccountsTable", html);
}

</script>

<!-- V2 OPTIONS PAPER ACCOUNT SECTION -->
<div class="section" id="optionsPaperAccountSection">
  <h2>Options Paper Account</h2>
  <div class="small">
    Separate paper-only options account. This does not place real trades.
  </div>

  <div class="metrics">
    <div class="metric-card">
      <div class="metric-label">Options Cash</div>
      <div class="metric-value" id="optionsCash">...</div>
      <div class="small">Available options paper cash</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Open Option Value</div>
      <div class="metric-value" id="optionsOpenValue">...</div>
      <div class="small">Current open option value</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Options Account Value</div>
      <div class="metric-value" id="optionsAccountValue">...</div>
      <div class="small">Cash + open option value</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Options Total P/L</div>
      <div class="metric-value" id="optionsTotalPnl">...</div>
      <div class="small" id="optionsTotalPnlPct">Total options return</div>
    </div>
  </div>

  <h3>Open Paper Option Positions</h3>
  <div id="openOptionsTable" class="table-wrap">
    <div class="small">Loading options positions...</div>
  </div>

  <h3>Latest Option Paper Actions</h3>
  <div id="optionActionsTable" class="table-wrap">
    <div class="small">Loading option actions...</div>
  </div>
</div>

<script id="v2-options-paper-account-monitor-js">
function setOptionsText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function optionsMoney(value) {
  const n = Number(value || 0);
  return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function optionsNum(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function optionsEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll(String.fromCharCode(34), "&quot;")
    .replaceAll("'", "&#039;");
}

function optionsPnlHtml(value, isPercent = false) {
  const n = Number(value || 0);
  const cls = n > 0 ? "good" : (n < 0 ? "bad" : "warn");
  const text = isPercent ? `${optionsNum(n, 3)}%` : optionsMoney(n);
  return `<span class="${cls}">${text}</span>`;
}

function renderOpenOptions(account) {
  const box = document.getElementById("openOptionsTable");
  if (!box) return;

  const open = account.open_option_positions || {};
  const rows = Object.values(open);

  if (!rows.length) {
    box.innerHTML = `<div class="small">No open paper option positions.</div>`;
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Underlying</th>
          <th>Option Contract</th>
          <th>Side</th>
          <th>Contracts</th>
          <th>Expiration</th>
          <th>Strike</th>
          <th>Entry Mark</th>
          <th>Last Mark</th>
          <th>Entry Cost</th>
          <th>Last Value</th>
          <th>Unrealized</th>
          <th>Unrealized %</th>
          <th>Opened At</th>
        </tr>
      </thead>
      <tbody>
  `;

  for (const pos of rows) {
    const entryCost = Number(pos.entry_cost || 0);
    const lastValue = Number(pos.last_value || entryCost || 0);
    const pnl = Number(pos.unrealized_pnl || (lastValue - entryCost));
    const pnlPct = Number(pos.unrealized_pnl_pct || (entryCost > 0 ? ((lastValue - entryCost) / entryCost * 100) : 0));

    html += `
      <tr>
        <td>${optionsEscape(pos.underlying_symbol)}</td>
        <td style="font-family:monospace;font-size:12px;">${optionsEscape(pos.option_contract_symbol)}</td>
        <td>${optionsEscape(pos.side || pos.contract_type || "LONG_CALL")}</td>
        <td>${optionsEscape(pos.contracts)}</td>
        <td>${optionsEscape(pos.expiration)}</td>
        <td>${optionsEscape(pos.strike)}</td>
        <td>${optionsMoney(pos.entry_mark)}</td>
        <td>${optionsMoney(pos.last_mark)}</td>
        <td>${optionsMoney(pos.entry_cost)}</td>
        <td>${optionsMoney(pos.last_value)}</td>
        <td>${optionsPnlHtml(pnl, false)}</td>
        <td>${optionsPnlHtml(pnlPct, true)}</td>
        <td>${optionsEscape(pos.opened_at)}</td>
      </tr>
    `;
  }

  html += `</tbody></table>`;
  box.innerHTML = html;
}

function renderOptionActions(account, status) {
  const box = document.getElementById("optionActionsTable");
  if (!box) return;

  let actions = [];

  if (account && Array.isArray(account.actions)) {
    actions = account.actions;
  } else if (status && Array.isArray(status.options_paper_actions)) {
    actions = status.options_paper_actions;
  }

  actions = actions.slice(-10).reverse();

  if (!actions.length) {
    box.innerHTML = `<div class="small">No option paper actions yet.</div>`;
    return;
  }

  let html = `
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Action</th>
          <th>Underlying</th>
          <th>Option Contract</th>
          <th>Contracts</th>
          <th>Cost</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody>
  `;

  for (const action of actions) {
    html += `
      <tr>
        <td>${optionsEscape(action.time)}</td>
        <td>${optionsEscape(action.action)}</td>
        <td>${optionsEscape(action.underlying_symbol || action.symbol)}</td>
        <td style="font-family:monospace;font-size:12px;">${optionsEscape(action.option_contract_symbol)}</td>
        <td>${optionsEscape(action.contracts)}</td>
        <td>${optionsMoney(action.cost)}</td>
        <td>${optionsEscape(action.reason)}</td>
      </tr>
    `;
  }

  html += `</tbody></table>`;
  box.innerHTML = html;
}

async function refreshOptionsPaperAccount() {
  try {
    const statusRes = await fetch("/v2/status?t=" + Date.now());
    const data = await statusRes.json();

    const accountRes = await fetch("/v2/options-paper-account?t=" + Date.now());
    const accountPayload = await accountRes.json();

    const account = accountPayload.account || data.options_paper_account || {};

    const cash = Number(account.cash || 0);
    const openValue = Number(account.open_option_value || 0);
    const accountValue = Number(account.account_value || (cash + openValue));
    const totalPnl = Number(account.total_pnl || 0);
    const totalPnlPct = Number(account.total_pnl_pct || 0);

    setOptionsText("optionsCash", optionsMoney(cash));
    setOptionsText("optionsOpenValue", optionsMoney(openValue));
    setOptionsText("optionsAccountValue", optionsMoney(accountValue));

    const totalEl = document.getElementById("optionsTotalPnl");
    if (totalEl) totalEl.innerHTML = optionsPnlHtml(totalPnl, false);

    const pctEl = document.getElementById("optionsTotalPnlPct");
    if (pctEl) pctEl.innerHTML = optionsPnlHtml(totalPnlPct, true) + " total options return";

    renderOpenOptions(account);
    renderOptionActions(account, data);
  } catch (err) {
    console.log("Options paper monitor refresh failed:", err);
  }
}

window.addEventListener("load", refreshOptionsPaperAccount);
window.addEventListener("load", refreshEngineAccounts);
setInterval(refreshOptionsPaperAccount, 15000);
setInterval(refreshEngineAccounts, 15000);
</script>
<!-- END V2 OPTIONS PAPER ACCOUNT SECTION -->

</body>
</html>
    """)


@router.post("/sell-position/{symbol}")
def v2_sell_position(symbol: str):
    """
    Owner action: sell one V2 paper position immediately.
    """
    return sell_one_symbol(symbol)

