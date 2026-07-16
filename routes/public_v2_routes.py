
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
BUILD = "ALIENTAI_V206_PUBLIC_VERSION_2_INFO"

PUBLIC_V2_HTML = '\n<section id="alientai-version-2" style="margin-top:28px;padding:22px;border-radius:18px;background:rgba(10,18,32,.72);border:1px solid rgba(80,180,255,.25);box-shadow:0 0 24px rgba(0,160,255,.10);">\n  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">\n    <span style="font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:#7dd3fc;">Version 2 Research System</span>\n    <span style="font-size:12px;padding:4px 9px;border-radius:999px;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.35);color:#86efac;">Paper Research Only</span>\n    <span style="font-size:12px;padding:4px 9px;border-radius:999px;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.35);color:#93c5fd;">Read-Only Public View</span>\n  </div>\n  <h2 style="margin:14px 0 8px;font-size:clamp(1.6rem,2.2vw,2.4rem);color:#e5f3ff;">AlientAI Version 2: Research Brain</h2>\n  <p style="max-width:980px;color:#cbd5e1;line-height:1.65;font-size:1rem;">\n    AlientAI Version 2 expands the platform from a simple scanner into a structured AI market research system.\n    The system checks data freshness, ranks opportunities, creates morning research reports, tracks paper-only decisions,\n    and learns from completed outcomes.\n  </p>\n  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:18px;">\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Morning Command Center</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">Data freshness first</div>\n      <p style="color:#cbd5e1;line-height:1.55;">Before producing a morning watchlist, AlientAI checks whether the historical database is current and blocks stale reports.</p>\n    </div>\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Research Brain</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">Organized intelligence layer</div>\n      <p style="color:#cbd5e1;line-height:1.55;">The Research Brain organizes historical data, feature snapshots, pattern discovery, learning records, and adaptive research tools.</p>\n    </div>\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Opportunity Ranking</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">BUY / HOLD / WAIT</div>\n      <p style="color:#cbd5e1;line-height:1.55;">The system ranks tracked symbols by trend strength, pullback quality, liquidity, and confidence-style scoring.</p>\n    </div>\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Learning Ledger</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">Self-evaluation loop</div>\n      <p style="color:#cbd5e1;line-height:1.55;">Recommendations can be recorded, completed, and evaluated so research engines can be measured over time.</p>\n    </div>\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Pattern Discovery</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">Historical edge research</div>\n      <p style="color:#cbd5e1;line-height:1.55;">AlientAI searches completed historical outcomes for recurring setups, win rates, and average return patterns.</p>\n    </div>\n    <div style="padding:15px;border-radius:14px;background:rgba(15,23,42,.78);border:1px solid rgba(148,163,184,.18);">\n      <div style="font-size:12px;color:#7dd3fc;text-transform:uppercase;letter-spacing:.12em;">Paper Trade Engine</div>\n      <div style="margin-top:8px;color:#f8fafc;font-weight:700;">Simulation, not live orders</div>\n      <p style="color:#cbd5e1;line-height:1.55;">Version 2 can create paper-only trade simulations from morning reports. It does not place live brokerage orders.</p>\n    </div>\n  </div>\n  <div style="margin-top:18px;padding:14px;border-radius:14px;background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.25);color:#fde68a;line-height:1.55;">\n    <strong>Research disclaimer:</strong>\n    AlientAI is an experimental paper-trading and market-research system. Public information shown here is read-only and should not be treated as financial advice or a live trading recommendation.\n  </div>\n</section>\n'

@router.get("/public/version-2", response_class=HTMLResponse)
def public_version_2_page():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AlientAI Version 2</title>
  <style>
    body {
      margin:0;
      padding:24px;
      font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      background:radial-gradient(circle at top,#10213f,#020617 62%);
      color:#e5e7eb;
    }
  </style>
</head>
<body>
  <main style="max-width:1180px;margin:0 auto;">
    <h1 style="font-size:clamp(2rem,4vw,4rem);margin-bottom:8px;">AlientAI</h1>
    <p style="color:#cbd5e1;max-width:880px;line-height:1.6;">
      Autonomous market intelligence for experimental paper-trading research.
    </p>
    """ + PUBLIC_V2_HTML + """
  </main>
</body>
</html>
"""

@router.get("/alpha/v206/status")
def public_v2_status():
    return {
        "status": "success",
        "build": BUILD,
        "message": "Public Version 2 information page is installed.",
        "routes": ["/public/version-2"]
    }
