from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_PRICE_ARROWS_V2.py")
backup.write_text(text, encoding="utf-8")

start_marker = '<script id="v2-open-position-price-arrows-js">'
end_marker = "</script>"

# Remove old script block if present.
while start_marker in text:
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if end == -1:
        break
    end += len(end_marker)
    text = text[:start] + text[end:]

script = r'''
<script id="v2-open-position-price-arrows-js">
(function () {
  const STORAGE_PREFIX = "alientai_v2_last_open_price_";

  function cleanNumber(text) {
    const cleaned = String(text || "")
      .replace(/[$,%▲▼▬↔]/g, "")
      .replace(/,/g, "")
      .trim();

    const value = Number.parseFloat(cleaned);
    return Number.isFinite(value) ? value : null;
  }

  function norm(text) {
    return String(text || "").trim().toLowerCase();
  }

  function getRows(table) {
    return Array.from(table.querySelectorAll("tr"));
  }

  function getCells(row) {
    return Array.from(row.querySelectorAll("th,td"));
  }

  function findHeaderInfo(table) {
    const rows = getRows(table);
    if (!rows.length) return null;

    const headerCells = getCells(rows[0]);
    const headers = headerCells.map(c => norm(c.textContent));

    let symbolIndex = -1;
    let lastIndex = -1;

    for (let i = 0; i < headers.length; i++) {
      const h = headers[i];

      if (h === "symbol") {
        symbolIndex = i;
      }

      // Must be exactly Last, not Last Action or Last Scan.
      if (h === "last") {
        lastIndex = i;
      }
    }

    if (symbolIndex < 0 || lastIndex < 0) return null;

    // Make sure this is the open-position table, not candidate table.
    const joined = headers.join(" | ");
    const looksOpenPositions =
      joined.includes("entry") &&
      joined.includes("high") &&
      joined.includes("cost") &&
      joined.includes("unrealized");

    if (!looksOpenPositions) return null;

    return { symbolIndex, lastIndex };
  }

  function markTable(table) {
    const info = findHeaderInfo(table);
    if (!info) return false;

    const rows = getRows(table).slice(1);
    let changed = false;

    rows.forEach(row => {
      const cells = Array.from(row.querySelectorAll("td"));
      if (cells.length <= Math.max(info.symbolIndex, info.lastIndex)) return;

      const symbol = String(cells[info.symbolIndex].textContent || "").trim().toUpperCase();
      if (!symbol || symbol === "SYMBOL") return;

      const lastCell = cells[info.lastIndex];

      // Remove existing arrow first.
      const existing = lastCell.querySelector(".v2-price-direction-arrow");
      if (existing) existing.remove();

      const currentPrice = cleanNumber(lastCell.textContent);
      if (currentPrice === null || currentPrice <= 0) return;

      const key = STORAGE_PREFIX + symbol;
      const previousRaw = window.localStorage.getItem(key);
      const previousPrice = previousRaw ? Number.parseFloat(previousRaw) : null;

      let arrow = "↔";
      let color = "#94a3b8";
      let label = "first reading / unchanged";

      if (Number.isFinite(previousPrice) && previousPrice > 0) {
        if (currentPrice > previousPrice) {
          arrow = "▲";
          color = "#22c55e";
          label = "up from $" + previousPrice.toFixed(2);
        } else if (currentPrice < previousPrice) {
          arrow = "▼";
          color = "#ef4444";
          label = "down from $" + previousPrice.toFixed(2);
        }
      }

      const span = document.createElement("span");
      span.className = "v2-price-direction-arrow";
      span.textContent = " " + arrow;
      span.title = symbol + " " + label;
      span.style.color = color;
      span.style.fontWeight = "900";
      span.style.fontSize = "18px";
      span.style.marginLeft = "6px";
      span.style.display = "inline-block";

      lastCell.appendChild(span);

      window.localStorage.setItem(key, String(currentPrice));
      changed = true;
    });

    if (changed && !document.getElementById("v2-price-arrow-active-note")) {
      const note = document.createElement("div");
      note.id = "v2-price-arrow-active-note";
      note.textContent = "Price arrows active: ▲ up, ▼ down, ↔ unchanged/first reading.";
      note.style.margin = "8px 0";
      note.style.color = "#93c5fd";
      note.style.fontSize = "13px";
      note.style.fontWeight = "700";

      table.parentNode.insertBefore(note, table);
    }

    return changed;
  }

  function installArrows() {
    const tables = Array.from(document.querySelectorAll("table"));
    tables.forEach(markTable);
  }

  let scheduled = false;

  function scheduleInstall() {
    if (scheduled) return;
    scheduled = true;

    window.setTimeout(function () {
      scheduled = false;
      installArrows();
    }, 100);
  }

  function start() {
    installArrows();

    const observer = new MutationObserver(scheduleInstall);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });

    window.setInterval(installArrows, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
</script>
'''

# Inject into HTML response. If the monitor HTML has </body>, this will insert before it.
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
print("Installed stronger V2 price-arrow script.")
