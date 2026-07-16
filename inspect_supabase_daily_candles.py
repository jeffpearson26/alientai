import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE key in .env")

client = create_client(url, key)

table = "v2_daily_candles"

print("Testing table:", table)

sample = client.table(table).select("*").limit(5).execute()

print("Rows returned:", len(sample.data or []))
print(json.dumps(sample.data, indent=2)[:5000])

# Try symbol count sample.
symbols = client.table(table).select("symbol").limit(1000).execute()
unique = sorted({str(r.get("symbol", "")).upper() for r in (symbols.data or []) if r.get("symbol")})
print("Unique symbols in first 1000 rows:", len(unique))
print(unique[:50])
