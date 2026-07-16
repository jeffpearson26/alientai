from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_DIRECT_OPTIONS_PAPER_SECTION.py")
backup.write_text(text, encoding="utf-8")

insert = r'''
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
    const res = await fetch("/v2/status?t=" + Date.now());
    const data = await res.json();

    const account = data.options_paper_account || {};

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
setInterval(refreshOptionsPaperAccount, 15000);
</script>
<!-- END V2 OPTIONS PAPER ACCOUNT SECTION -->
'''

if "v2-options-paper-account-monitor-js" in text:
    print("Options paper account monitor section is already installed.")
else:
    # Insert before the final </body> inside the HTMLResponse string.
    pos = text.rfind("</body>")
    if pos == -1:
        raise SystemExit("Could not find </body> in v2_routes.py monitor HTML.")

    text = text[:pos] + insert + "\n" + text[pos:]
    path.write_text(text, encoding="utf-8")
    print("Installed direct Options Paper Account section into monitor HTML.")
