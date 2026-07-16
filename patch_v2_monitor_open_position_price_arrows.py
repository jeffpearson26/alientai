from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/v2_routes_BACKUP_BEFORE_PRICE_ARROWS.py")
backup.write_text(text, encoding="utf-8")

script = r'''
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
'''

if "v2-open-position-price-arrows-js" in text:
    print("Price-arrow JS is already installed.")
else:
    # Best case: v2 monitor HTML contains </body>.
    if "</body>" in text:
        text = text.replace("</body>", script + "\n</body>", 1)
    else:
        # More robust fallback: inject script before HTMLResponse(html) / Response(html).
        patched = False

        targets = [
            "return HTMLResponse(html)",
            "return HTMLResponse(content=html)",
            "return Response(html)",
            "return Response(content=html)",
        ]

        for target in targets:
            if target in text:
                replacement = f'''html = html.replace("</body>", {script!r} + "\\n</body>") if "</body>" in html else html + {script!r}
    {target}'''
                text = text.replace(target, replacement, 1)
                patched = True
                break

        if not patched:
            raise SystemExit("Could not find a safe place to inject price-arrow script into v2_routes.py.")

    path.write_text(text, encoding="utf-8")
    print("Installed open-position price arrows on V2 monitor.")
