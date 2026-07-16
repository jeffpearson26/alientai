from alientai_v2.history.supabase_candle_reader import fetch_symbol_candles

for symbol in ["AAOI", "AMD"]:
    rows = fetch_symbol_candles(symbol, limit=20)
    print(symbol, "candles:", len(rows))
    if rows:
        print("oldest returned:", rows[0].get("datetime_utc"))
        print("newest returned:", rows[-1].get("datetime_utc"))
