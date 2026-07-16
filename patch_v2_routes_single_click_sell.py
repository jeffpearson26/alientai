from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

# Add sell_one_symbol to the engine import.
if "sell_one_symbol" not in text:
    if "sell_all," in text:
        text = text.replace("sell_all,", "sell_all,\n    sell_one_symbol,", 1)
    elif "sell_all" in text:
        text = text.replace("sell_all", "sell_all,\n    sell_one_symbol", 1)
    else:
        raise SystemExit("Could not find sell_all import in v2_routes.py")

route = r'''

@router.post("/v2/sell-position/{symbol}")
def v2_sell_position(symbol: str):
    """
    Owner action: sell one V2 paper position immediately.
    """
    return sell_one_symbol(symbol)
'''

if "/v2/sell-position/{symbol}" not in text:
    text = text.rstrip() + "\n" + route + "\n"

path.write_text(text, encoding="utf-8")
