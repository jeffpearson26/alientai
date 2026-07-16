import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

PROJECT_ROOT = Path.cwd()
symbols_file = PROJECT_ROOT / "russell_2000_symbols.txt"
out_file = PROJECT_ROOT / "data_v2" / "training_library" / "russell2000_feature_ready_symbols.txt"
rejected_file = PROJECT_ROOT / "data_v2" / "training_library" / "russell2000_feature_rejected_symbols.txt"

table = "v2_daily_candles"
min_candles = 240

url = os.getenv("SUPABASE_URL")
key = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
)

if not url or not key:
    raise SystemExit("Missing Supabase URL/key in .env")

sb = create_client(url, key)

def clean_symbol(s):
    return s.replace("\ufeff", "").strip().upper()

symbols = []
seen = set()

for line in symbols_file.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
    s = clean_symbol(line)
    if not s or s.startswith("#"):
        continue
    if "," in s:
        s = clean_symbol(s.split(",", 1)[0])
    if s and s not in seen:
        seen.add(s)
        symbols.append(s)

ready = []
rejected = []

print("Checking symbols:", len(symbols))
print("Minimum candles required:", min_candles)
print("")

for i, sym in enumerate(symbols, 1):
    try:
        r = (
            sb.table(table)
            .select("symbol", count="exact")
            .eq("symbol", sym)
            .eq("timeframe", "1d")
            .limit(1)
            .execute()
        )
        count = int(r.count or 0)

        if count >= min_candles:
            ready.append(sym)
            status = "READY"
        else:
            rejected.append((sym, count))
            status = "REJECT"

        print(f"[{i}/{len(symbols)}] {sym:8} {status:6} candles={count}")

    except Exception as exc:
        rejected.append((sym, 0))
        print(f"[{i}/{len(symbols)}] {sym:8} ERROR {exc}")

out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text("\n".join(ready) + ("\n" if ready else ""), encoding="utf-8")

with rejected_file.open("w", encoding="utf-8") as f:
    for sym, count in rejected:
        f.write(f"{sym},{count}\n")

print("")
print("DONE")
print("ready symbols:", len(ready))
print("rejected symbols:", len(rejected))
print("ready file:", out_file)
print("rejected file:", rejected_file)
