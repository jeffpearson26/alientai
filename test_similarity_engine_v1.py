from alientai_v2.engines.similarity_engine import run

quotes = [
    {
        "symbol": "AAOI",
        "price": 20.00,
        "move_pct": 1.5,
        "spread_pct": 0.05,
        "volume": 1000000,
        "source": "manual_test",
    },
    {
        "symbol": "AMD",
        "price": 520.00,
        "move_pct": -2.0,
        "spread_pct": 0.05,
        "volume": 10000000,
        "source": "manual_test",
    },
]

settings = {
    "similarity_engine_enabled": True,
    "similarity_window_bars": 12,
    "similarity_horizon_bars": 78,
    "similarity_history_limit": 5000,
    "similarity_max_cases_to_scan": 2500,
    "similarity_top_k": 50,
    "similarity_min_cases": 20,
    "similarity_watch_score": 45,
    "similarity_buy_score": 62,
    "similarity_max_symbols_per_scan": 25,
}

rows = run(quotes, settings)

for row in rows:
    print("-----")
    print("engine:", row.get("engine_id"))
    print("symbol:", row.get("symbol"))
    print("decision:", row.get("decision"))
    print("score:", row.get("score"))
    print("cases:", row.get("similar_cases"))
    print("win_rate:", row.get("similarity_win_rate_pct"))
    print("avg_forward:", row.get("similarity_avg_forward_return_pct"))
    print("reason:", row.get("reason"))
