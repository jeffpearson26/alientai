from pathlib import Path

path = Path("alientai_v2/engines/prediction_20day.py")
text = path.read_text(encoding="utf-8-sig")

old = '''        symbol = str(quote.get("symbol") or "").upper()
        price = safe_float(quote.get("price"), 0.0)
'''

new = '''        symbol = str(quote.get("symbol") or quote.get("ticker") or quote.get("key") or "").upper().strip()

        # Do not allow blank-symbol rows into the candidate table.
        # A blank symbol row becomes a confusing dashboard line like:
        # prediction_20day AVOID 0.0 $0.00
        if not symbol:
            continue

        price = safe_float(quote.get("price"), 0.0)
'''

if old not in text:
    raise SystemExit("Could not find symbol assignment block in prediction_20day.py")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
