from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

js = r'''
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
'''

if "v2-click-sell-open-position-js" not in text:
    if "</body>" in text:
        text = text.replace("</body>", js + "\n</body>", 1)
    else:
        # Fallback: append to route file. If the page HTML is generated as a string,
        # this may not render, but it will not break Python.
        text = text.rstrip() + "\n\n# Click-to-sell JS was not inserted because </body> was not found.\n"

path.write_text(text, encoding="utf-8")
