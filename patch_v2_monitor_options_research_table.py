from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_OPTIONS_TABLE.py")
backup.write_text(text, encoding="utf-8")

script = r'''
<script id="v2-options-research-table-js">
(function () {
  function money(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "";
    return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function num(value, digits) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "";
    return n.toFixed(digits);
  }

  function getStatusUrl() {
    return "/v2/status?t=" + Date.now();
  }

  function findMainContainer() {
    return document.querySelector("main") || document.body;
  }

  function removeOldTable() {
    const old = document.getElementById("v2-options-research-section");
    if (old) old.remove();
  }

  function rowHtml(row) {
    const decision = String(row.decision || "");
    const pass = decision.includes("PASS");

    const decisionStyle = pass
      ? "color:#22c55e;font-weight:900;"
      : "color:#fbbf24;font-weight:800;";

    return `
      <tr>
        <td>${row.underlying_symbol || row.symbol || ""}</td>
        <td style="font-family:monospace;font-size:12px;">${row.option_contract_symbol || row.option_symbol || ""}</td>
        <td>${row.expiration || ""}</td>
        <td>${row.dte ?? ""}</td>
        <td>${num(row.strike, 2)}</td>
        <td>${money(row.mark ?? row.price)}</td>
        <td>${money(row.estimated_contract_cost)}</td>
        <td>${num(row.spread_pct, 2)}%</td>
        <td>${Number(row.open_interest || 0).toLocaleString()}</td>
        <td>${num(row.delta, 3)}</td>
        <td>${num(row.research_score ?? row.score, 2)}</td>
        <td style="${decisionStyle}">${decision}</td>
      </tr>
    `;
  }

  function buildSection(rows) {
    const section = document.createElement("section");
    section.id = "v2-options-research-section";
    section.style.marginTop = "26px";

    if (!rows.length) {
      section.innerHTML = `
        <h2>Top Options Research Candidates</h2>
        <div style="
          padding:12px;
          border:1px solid rgba(255,255,255,0.12);
          border-radius:12px;
          background:rgba(255,255,255,0.05);
          color:#cbd5e1;
        ">
          No options research rows in latest V2 status.
        </div>
      `;
      return section;
    }

    section.innerHTML = `
      <h2>Top Options Research Candidates</h2>
      <div style="
        margin:6px 0 10px 0;
        color:#93c5fd;
        font-size:13px;
        font-weight:700;
      ">
        Research only. No option paper trades or live option trades are allowed from this table.
      </div>

      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Underlying</th>
              <th>Option</th>
              <th>Expiration</th>
              <th>DTE</th>
              <th>Strike</th>
              <th>Mark</th>
              <th>Est. Cost</th>
              <th>Spread %</th>
              <th>Open Interest</th>
              <th>Delta</th>
              <th>Score</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(rowHtml).join("")}
          </tbody>
        </table>
      </div>
    `;

    return section;
  }

  async function installOptionsResearchTable() {
    try {
      const res = await fetch(getStatusUrl());
      const status = await res.json();

      const rows = Array.isArray(status.top_v2_candidates)
        ? status.top_v2_candidates.filter(row => String(row.engine_id || "") === "options_research")
        : [];

      rows.sort((a, b) => Number(b.score || b.research_score || 0) - Number(a.score || a.research_score || 0));

      removeOldTable();

      const section = buildSection(rows.slice(0, 20));
      const container = findMainContainer();

      const candidateHeadings = Array.from(document.querySelectorAll("h1,h2,h3,div"))
        .filter(el => String(el.textContent || "").includes("Top V2 Candidates"));

      if (candidateHeadings.length) {
        const heading = candidateHeadings[0];

        let afterNode = heading;
        for (let i = 0; i < 4 && afterNode && afterNode.nextElementSibling; i++) {
          afterNode = afterNode.nextElementSibling;
          if (afterNode.tagName && afterNode.tagName.toLowerCase() === "table") {
            break;
          }
          if (afterNode.querySelector && afterNode.querySelector("table")) {
            break;
          }
        }

        afterNode.parentNode.insertBefore(section, afterNode.nextSibling);
      } else {
        container.appendChild(section);
      }

    } catch (err) {
      console.log("Options research table failed:", err);
    }
  }

  window.addEventListener("load", installOptionsResearchTable);
  setInterval(installOptionsResearchTable, 15000);
})();
</script>
'''

# Remove older copy if present.
marker = '<script id="v2-options-research-table-js">'
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
print("Installed Top Options Research Candidates table on V2 monitor.")
