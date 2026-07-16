from pathlib import Path

path = Path("train_v2_prediction_friday_from_supabase.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_prediction_friday_from_supabase_BACKUP_BEFORE_PAGINATION.py")
backup.write_text(text, encoding="utf-8")

start = text.find("def fetch_symbol_rows(")
if start == -1:
    raise SystemExit("Could not find def fetch_symbol_rows.")

end = text.find("\ndef fetch_all_symbols", start)
if end == -1:
    raise SystemExit("Could not find def fetch_all_symbols after fetch_symbol_rows.")

new_func = r'''def fetch_symbol_rows(client, table: str, symbol: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetch all daily candles for one symbol using Supabase pagination.

    Supabase commonly returns only 1,000 rows per request unless we page
    with .range(start, end). This function keeps paging until it reaches
    the requested limit or runs out of rows.
    """
    all_raw_rows: List[Dict[str, Any]] = []
    page_size = 1000
    start = 0

    while True:
        if limit > 0 and len(all_raw_rows) >= limit:
            break

        remaining = limit - len(all_raw_rows) if limit > 0 else page_size
        this_page_size = min(page_size, remaining) if limit > 0 else page_size
        end = start + this_page_size - 1

        result = (
            client
            .table(table)
            .select("*")
            .eq("symbol", symbol)
            .order("date", desc=False)
            .range(start, end)
            .execute()
        )

        raw_rows = result.data or []

        if not raw_rows:
            break

        all_raw_rows.extend(raw_rows)

        if len(raw_rows) < this_page_size:
            break

        start += this_page_size

    rows: List[Dict[str, Any]] = []

    for raw in all_raw_rows:
        row = normalize_row(raw)
        if row:
            rows.append(row)

    rows.sort(key=lambda r: r["dt"])

    if limit > 0 and len(rows) > limit:
        rows = rows[-limit:]

    return rows


'''

text = text[:start] + new_func + text[end + 1:]

path.write_text(text, encoding="utf-8")
print("Patched Supabase trainer with per-symbol pagination.")
