import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

from alientai_v2.control_auth import CONTROL_HEADER, control_request_allowed, is_control_request
from alientai_v2.v2_routes import router as v2_router


load_dotenv(Path(__file__).resolve().parent / ".env")
app = FastAPI(title="AlientAI V2 Clean App")

app.include_router(v2_router)


@app.middleware("http")
async def protect_remote_control_requests(request: Request, call_next):
    if is_control_request(request.method, request.url.path):
        client_host = request.client.host if request.client else ""
        supplied = request.headers.get(CONTROL_HEADER, "")
        configured = os.getenv("ALIENTAI_CONTROL_TOKEN", "")
        if not control_request_allowed(client_host, supplied, configured):
            return JSONResponse(
                status_code=403,
                content={"detail": "Remote control request denied."},
            )
    return await call_next(request)


@app.get("/api")
def api_home():
    return {
        "status": "success",
        "message": "AlientAI V2 Clean App is running.",
        "monitor": "/v2/monitor",
        "status_url": "/v2/status",
        "build": "ALIENTAI_V2_REFACTORED_CLEAN_APP_V1",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "AlientAI V2 Clean App",
        "old_scanner_loaded": False,
    }

@app.get("/")
def public_home():
    from pathlib import Path
    import json

    status_path = Path("data_v2/v2_status.json")
    status = {}

    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            status = {}

    account_value = status.get("account_value", 10000.0)
    total_pnl = status.get("total_pnl", 0.0)
    total_pnl_pct = status.get("total_pnl_pct", 0.0)
    open_positions_count = status.get("open_positions_count", 0)
    last_action = status.get("last_action", "WAIT")
    last_scan_time = status.get("last_scan_time", "")
    candidates = status.get("top_v2_candidates", [])[:10]
    positions = status.get("open_positions", {})

    candidate_rows = ""
    for c in candidates:
        candidate_rows += f"""
        <tr>
            <td>{c.get('engine_id','')}</td>
            <td><b>{c.get('symbol','')}</b></td>
            <td>{c.get('decision','')}</td>
            <td>{c.get('score','')}</td>
            <td>${c.get('price',0)}</td>
            <td>{c.get('move_pct','')}%</td>
        </tr>
        """

    position_rows = ""
    for symbol, p in positions.items():
        position_rows += f"""
        <tr>
            <td><b>{symbol}</b></td>
            <td>{p.get('engine_id','')}</td>
            <td>{p.get('shares','')}</td>
            <td>${p.get('entry_price','')}</td>
            <td>${p.get('last_price','')}</td>
            <td>{p.get('unrealized_pnl_pct','')}%</td>
            <td>{p.get('prediction_horizon_days','')}d</td>
        </tr>
        """

    if not candidate_rows:
        candidate_rows = '<tr><td colspan="6">No current candidates.</td></tr>'

    if not position_rows:
        position_rows = '<tr><td colspan="7">No open V2 paper positions.</td></tr>'

    return f"""
<!doctype html>
<html>
<head>
    <title>AlientAI Public Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="30">
    <style>
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #070b14;
            color: #e8eefc;
        }}
        .wrap {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px;
        }}
        .hero {{
            padding: 28px;
            border-radius: 18px;
            background: linear-gradient(135deg, #121a2f, #09111f);
            border: 1px solid #1f3157;
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0 0 8px;
            font-size: 34px;
        }}
        .muted {{
            color: #9fb0d0;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin: 20px 0;
        }}
        .card {{
            background: #0d1424;
            border: 1px solid #1f3157;
            border-radius: 14px;
            padding: 16px;
        }}
        .label {{
            color: #9fb0d0;
            font-size: 13px;
            margin-bottom: 8px;
        }}
        .value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .good {{
            color: #54e38f;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            background: #0d1424;
            border-radius: 14px;
            overflow: hidden;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #1f3157;
        }}
        th {{
            color: #9fb0d0;
            background: #101a30;
        }}
        a {{
            color: #8db7ff;
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="hero">
            <h1>AlientAI</h1>
            <div class="muted">Public V2 paper-trading research monitor. This page is read-only.</div>
            <div class="muted">Old scanner decision-making is not used by this public page.</div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="label">Paper Account Value</div>
                <div class="value">${account_value:,.2f}</div>
            </div>
            <div class="card">
                <div class="label">Total Paper P/L</div>
                <div class="value good">${total_pnl:,.2f}</div>
            </div>
            <div class="card">
                <div class="label">Total Return</div>
                <div class="value good">{total_pnl_pct:.3f}%</div>
            </div>
            <div class="card">
                <div class="label">Open Positions</div>
                <div class="value">{open_positions_count}</div>
            </div>
            <div class="card">
                <div class="label">Last Action</div>
                <div class="value">{last_action}</div>
            </div>
        </div>

        <div class="card">
            <div class="label">Last Scan</div>
            <div>{last_scan_time}</div>
        </div>

        <h2>Open V2 Paper Positions</h2>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Engine</th>
                <th>Shares</th>
                <th>Entry</th>
                <th>Last</th>
                <th>Unrealized %</th>
                <th>Prediction</th>
            </tr>
            {position_rows}
        </table>

        <h2>Top V2 Candidates</h2>
        <table>
            <tr>
                <th>Engine</th>
                <th>Symbol</th>
                <th>Decision</th>
                <th>Score</th>
                <th>Price</th>
                <th>Move</th>
            </tr>
            {candidate_rows}
        </table>

        <p class="muted">
            Experimental paper-trading research only. Not financial advice.
            <br>
            Owner monitor: <a href="/v2/monitor">V2 Monitor</a>
        </p>
    </div>
</body>
</html>
"""

@app.get("/public", response_class=HTMLResponse)
def public_alias():
    return public_home()


# --- ALIENTAI PUBLIC V2 PAGE WIRING ---
# Public page is read-only and connected to clean V2 status.
try:
    from alientai_v2.public_v2_page import public_v2_page

    # Remove older /public route if it already exists.
    app.router.routes = [
        route for route in app.router.routes
        if getattr(route, "path", None) not in {"/public"}
    ]

    app.add_api_route(
        "/public",
        public_v2_page,
        methods=["GET"],
        include_in_schema=False,
    )

    app.add_api_route(
        "/public-v2",
        public_v2_page,
        methods=["GET"],
        include_in_schema=False,
    )

except Exception as exc:
    print(f"Public V2 page wiring failed: {exc}")
# --- END ALIENTAI PUBLIC V2 PAGE WIRING ---

