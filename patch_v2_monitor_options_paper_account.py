from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_OPTIONS_PAPER_MONITOR.py")
backup.write_text(text, encoding="utf-8")

script = r'''
<script id="v2-options-paper-account-monitor-js">
(function () {
  function money(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "$0.00";
    return "$" + n.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  function pct(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "0.000%";
    return n.toFixed(3) + "%";
  }

  function num(value, digits) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "";
    return n.toFixed(digits);
  }

  function safeText(value) {
    if (value === null || value === undefined) return "";
    return String(value);
  }

  async function loadStatus() {
    const res = await fetch("/v2/status?t=" + Date.now());
    return await res.json();
  }

  function removeOldSection() {
    const old = document.getElementById("v2-options-paper-account-section");
    if (old) old.remove();
  }

  function positionRows(account) {
    const open = account && account.open_option_positions ? account.open_option_positions : {};
    const rows = Object.values(open);

    if (!rows.length) {
      return `
        <tr>
          <td colspan="13" style="color:#94a3b8;">No open paper option positions.</td>
        </tr>
      `;
    }

    return rows.map(pos => {
      const entryCost = Number(pos.entry_cost || 0);
      const lastValue = Number(pos.last_value || entryCost || 0);
      const pnl = Number(pos.unrealized_pnl || (lastValue - entryCost));
      const pnlPct = Number(pos.unrealized_pnl_pct || (entryCost > 0 ? ((lastValue - entryCost) / entryCost * 100) : 0));

      const pnlColor = pnl > 0 ? "#22c55e" : (pnl < 0 ? "#ef4444" : "#cbd5e1");

      return `
        <tr>
          <td>${safeText(pos.underlying_symbol)}</td>
          <td style="font-family:monospace;font-size:12px;">${safeText(pos.option_contract_symbol)}</td>
          <td>${safeText(pos.side || pos.contract_type || "LONG_CALL")}</td>
          <td>${safeText(pos.contracts)}</td>
          <td>${safeText(pos.expiration)}</td>
          <td>${num(pos.strike, 2)}</td>
          <td>${money(pos.entry_mark)}</td>
          <td>${money(pos.last_mark)}</td>
          <td>${money(pos.entry_cost)}</td>
          <td>${money(pos.last_value)}</td>
          <td style="color:${pnlColor};font-weight:900;">${money(pnl)}</td>
          <td style="color:${pnlColor};font-weight:900;">${pct(pnlPct)}</td>
          <td>${safeText(pos.opened_at)}</td>
        </tr>
      `;
    }).join("");
  }

  function actionRows(account, status) {
    let actions = [];

    if (account && Array.isArray(account.actions)) {
      actions = account.actions;
    }

    if (!actions.length && Array.isArray(status.options_paper_actions)) {
      actions = status.options_paper_actions;
    }

    actions = actions.slice(-10).reverse();

    if (!actions.length) {
      return `
        <tr>
          <td colspan="7" style="color:#94a3b8;">No option paper actions yet.</td>
        </tr>
      `;
    }

    return actions.map(action => `
      <tr>
        <td>${safeText(action.time)}</td>
        <td>${safeText(action.action)}</td>
        <td>${safeText(action.underlying_symbol || action.symbol)}</td>
        <td style="font-family:monospace;font-size:12px;">${safeText(action.option_contract_symbol)}</td>
        <td>${safeText(action.contracts)}</td>
        <td>${money(action.cost)}</td>
        <td>${safeText(action.reason)}</td>
      </tr>
    `).join("");
  }

  function buildSection(status) {
    const account = status.options_paper_account || {};
    const manager = status.options_paper_manager || {};

    const cash = Number(account.cash || 0);
    const openValue = Number(account.open_option_value || 0);
    const accountValue = Number(account.account_value || cash + openValue);
    const totalPnl = Number(account.total_pnl || 0);
    const totalPnlPct = Number(account.total_pnl_pct || 0);
    const realized = Number(account.realized_pnl || 0);
    const unrealized = Number(account.unrealized_pnl || 0);

    const pnlColor = totalPnl > 0 ? "#22c55e" : (totalPnl < 0 ? "#ef4444" : "#cbd5e1");

    const section = document.createElement("section");
    section.id = "v2-options-paper-account-section";
    section.style.marginTop = "28px";

    section.innerHTML = `
      <h2>Options Paper Account</h2>

      <div style="
        margin:6px 0 12px 0;
        color:#93c5fd;
        font-size:13px;
        font-weight:700;
      ">
        Separate paper-only options account. This does not place real trades.
      </div>

      <div style="
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:10px;
        margin:12px 0 18px 0;
      ">
        <div class="card">
          <div class="label">Options Cash</div>
          <div class="value">${money(cash)}</div>
          <div class="sub">Available paper options cash</div>
        </div>

        <div class="card">
          <div class="label">Open Option Value</div>
          <div class="value">${money(openValue)}</div>
          <div class="sub">Current open option value</div>
        </div>

        <div class="card">
          <div class="label">Options Account Value</div>
          <div class="value">${money(accountValue)}</div>
          <div class="sub">Cash + open option value</div>
        </div>

        <div class="card">
          <div class="label">Realized Options P/L</div>
          <div class="value">${money(realized)}</div>
          <div class="sub">Closed paper option trades</div>
        </div>

        <div class="card">
          <div class="label">Unrealized Options P/L</div>
          <div class="value">${money(unrealized)}</div>
          <div class="sub">Open paper option positions</div>
        </div>

        <div class="card">
          <div class="label">Total Options P/L</div>
          <div class="value" style="color:${pnlColor};">${money(totalPnl)}</div>
          <div class="sub">${pct(totalPnlPct)} total return</div>
        </div>
      </div>

      <h3>Open Paper Option Positions</h3>
      <div style="overflow-x:auto;">
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
            ${positionRows(account)}
          </tbody>
        </table>
      </div>

      <h3 style="margin-top:20px;">Latest Option Paper Actions</h3>
      <div style="overflow-x:auto;">
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
            ${actionRows(account, status)}
          </tbody>
        </table>
      </div>

      <div style="
        margin-top:10px;
        color:#94a3b8;
        font-size:12px;
      ">
        Manager status: ${safeText(manager.status || "unknown")} — ${safeText(manager.message || "")}
      </div>
    `;

    return section;
  }

  function findInsertPoint() {
    const headings = Array.from(document.querySelectorAll("h1,h2,h3,div"))
      .filter(el => String(el.textContent || "").includes("Top Options Research Candidates"));

    if (headings.length) {
      let node = headings[0];

      for (let i = 0; i < 8 && node && node.nextElementSibling; i++) {
        node = node.nextElementSibling;

        if (node.tagName && node.tagName.toLowerCase() === "table") {
          return node;
        }

        if (node.querySelector && node.querySelector("table")) {
          return node;
        }
      }

      return headings[0];
    }

    const stockHeadings = Array.from(document.querySelectorAll("h1,h2,h3,div"))
      .filter(el => String(el.textContent || "").includes("Open V2 Paper Positions"));

    if (stockHeadings.length) {
      return stockHeadings[0];
    }

    return document.querySelector("main") || document.body;
  }

  async function installOptionsPaperAccountSection() {
    try {
      const status = await loadStatus();
      removeOldSection();

      const section = buildSection(status);
      const insertPoint = findInsertPoint();

      if (insertPoint && insertPoint.parentNode) {
        insertPoint.parentNode.insertBefore(section, insertPoint.nextSibling);
      } else {
        document.body.appendChild(section);
      }
    } catch (err) {
      console.log("Options paper account monitor failed:", err);
    }
  }

  window.addEventListener("load", installOptionsPaperAccountSection);
  setInterval(installOptionsPaperAccountSection, 15000);
})();
</script>
'''

# Remove older copy if present.
marker = '<script id="v2-options-paper-account-monitor-js">'
while marker in text:
    start = text.find(marker)
    end = text.find("</script>", start)
    if end == -1:
      break
    end += len("</script>")
    text = text[:start] + text[end:]

targets = [
    "return HTMLResponse(html)",
    "return HTMLResponse(content=html)",
]

patched = False
for target in targets:
    if target in text:
        insert = f'''html = html.replace("</body>", {script!r} + "\\n</body>") if "</body>" in html else html + {script!r}
    {target}'''
        text = text.replace(target, insert, 1)
        patched = True
        break

if not patched:
    raise SystemExit("Could not find HTMLResponse(html) or HTMLResponse(content=html).")

path.write_text(text, encoding="utf-8")
print("Installed Options Paper Account section on V2 monitor.")
