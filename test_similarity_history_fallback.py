from alientai_v2.engines.similarity_engine import fetch_history_with_fallback

for symbol in ["AMD", "AAOI", "NVDA", "AVGO", "SMCI", "PLTR", "MU", "SOXL"]:
    rows, source = fetch_history_with_fallback(symbol, limit=50)
    print(symbol, source, len(rows))
    if rows:
        print("  first:", rows[0].get("datetime_utc"))
        print("  last: ", rows[-1].get("datetime_utc"))
