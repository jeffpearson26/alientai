from pathlib import Path

path = Path("alientai_v2/v2_routes.py")
text = path.read_text(encoding="utf-8-sig")

text = text.replace(
    '@router.post("/v2/sell-position/{symbol}")',
    '@router.post("/sell-position/{symbol}")'
)

path.write_text(text, encoding="utf-8")
print("Fixed sell-position route from /v2/v2/sell-position/{symbol} to /v2/sell-position/{symbol}")
