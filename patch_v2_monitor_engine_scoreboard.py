from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_ENGINE_ACCOUNTS_MONITOR.py")
backup.write_text(text, encoding="utf-8")

# ------------------------------------------------------------
# 1) Add endpoint helper if missing
# ------------------------------------------------------------

endpoint_block = r'''

def _read_v2_engine_accounts_summary_file():
    """
    Directly read the reconstructed per-engine account summary.
    This is research-only and does not place trades.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        summary_path = project_root / "data_v2" / "engine_accounts" / "engine_accounts_summary.json"

        if not summary_path.exists():
            return {
                "status": "missing",
                "engines": [],
                "note": "Engine accounts summary has not been built yet. Run build_v2_engine_accounts_v1.py.",
            }

        return json.loads(summary_path.read_text(encoding="utf-8"))

    except Exception as exc:
        return {
            "status": "error",
            "engines": [],
            "error": str(exc),
            "note": "Could not read engine accounts summary.",
        }


@router.get("/v2/engine-accounts")
def v2_engine_accounts_summary():
    """
    Owner monitor endpoint for per-engine paper account scoreboard.
    """
    return _read_v2_engine_accounts_summary_file()
'''

if "def _read_v2_engine_accounts_summary_file" not in text:
    marker = "def _read_v2_options_paper_account_file"
    if marker in text:
        text = text.replace(marker, endpoint_block + "\n\n" + marker, 1)
    else:
        # Fallback: add near top after imports.
        text = endpoint_block + "\n\n" + text

# ------------------------------------------------------------
# 2) Insert HTML section before Open V2 Paper Positions
# ------------------------------------------------------------

engine_section = r'''
  <div class="section card">
    <h2>Engine Performance Scoreboard</h2>
    <div class="small">
      Research-only reconstructed per-engine accounts. Existing shared V2 paper account is unchanged.
    </div>
    <div id="engineAccountsTable">Loading...</div>
  </div>

'''

if 'id="engineAccountsTable"' not in text:
    target = '''  <div class="section card">
    <h2>Open V2 Paper Positions</h2>
    <div id="openPositionsTable">Loading...</div>
  </div>
'''
    if target in text:
        text = text.replace(target, engine_section + target, 1)
    else:
        raise SystemExit("Could not find Open V2 Paper Positions section. No HTML insertion made.")

# ------------------------------------------------------------
# 3) Add JavaScript render/refresh functions before options script
# ------------------------------------------------------------

js_block = r'''
async function refreshEngineAccounts() {
  try {
    const res = await fetch("/v2/engine-accounts?ts=" + Date.now());
    const data = await res.json();
    renderEngineAccounts(data);
  } catch (err) {
    setHtml("engineAccountsTable", `<div class="small">Engine accounts unavailable: ${escapeHtml(String(err))}</div>`);
  }
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
'''

if "function refreshEngineAccounts()" not in text:
    marker = "<!-- V2 OPTIONS PAPER ACCOUNT SECTION -->"
    if marker in text:
        text = text.replace(marker, "<script>\n" + js_block + "\n</script>\n\n" + marker, 1)
    else:
        # Fallback: insert before closing body.
        text = text.replace("</body>", "<script>\n" + js_block + "\n</script>\n</body>", 1)

# ------------------------------------------------------------
# 4) Make existing refresh loop call refreshEngineAccounts()
# ------------------------------------------------------------

# Add load hook near existing options load hook if possible.
if "window.addEventListener(\"load\", refreshEngineAccounts);" not in text:
    if "window.addEventListener(\"load\", refreshOptionsPaperAccount);" in text:
        text = text.replace(
            "window.addEventListener(\"load\", refreshOptionsPaperAccount);",
            "window.addEventListener(\"load\", refreshOptionsPaperAccount);\nwindow.addEventListener(\"load\", refreshEngineAccounts);",
            1,
        )
    elif "window.addEventListener(\"load\", refresh);" in text:
        text = text.replace(
            "window.addEventListener(\"load\", refresh);",
            "window.addEventListener(\"load\", refresh);\nwindow.addEventListener(\"load\", refreshEngineAccounts);",
            1,
        )

if "setInterval(refreshEngineAccounts, 15000);" not in text:
    if "setInterval(refreshOptionsPaperAccount, 15000);" in text:
        text = text.replace(
            "setInterval(refreshOptionsPaperAccount, 15000);",
            "setInterval(refreshOptionsPaperAccount, 15000);\nsetInterval(refreshEngineAccounts, 15000);",
            1,
        )
    else:
        text = text.replace("</script>", "setInterval(refreshEngineAccounts, 15000);\n</script>", 1)

path.write_text(text, encoding="utf-8")

print("Patched V2 monitor with Engine Performance Scoreboard.")
print("Backup:", backup)
