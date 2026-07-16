from pathlib import Path

src = Path("similarity_sandbox_scan_once.py")
dst = Path("similarity_percentile_sandbox_scan_once.py")

if not src.exists():
    raise SystemExit("Missing similarity_sandbox_scan_once.py. Build the fixed-threshold sandbox scanner first.")

text = src.read_text(encoding="utf-8")

text = text.replace(
    'BUILD = "ALIENTAI_V2_SIMILARITY_SANDBOX_SCAN_ONCE_BUYER_V1"',
    'BUILD = "ALIENTAI_V2_SIMILARITY_PERCENTILE_SANDBOX_SCAN_ONCE_BUYER_V1"'
)

text = text.replace(
    'ACCOUNT_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_sandbox" / "similarity_engine_sandbox_account.json"',
    'ACCOUNT_PATH = PROJECT_ROOT / "data_v2" / "similarity_percentile_sandbox" / "similarity_percentile_sandbox_account.json"'
)

text = text.replace(
    'ALLOWED_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_v1_loose_test" / "similarity_engine_sandbox_allowed_symbols.txt"',
    'ALLOWED_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_allowed_symbols.txt"'
)

text = text.replace(
    'TOKEN_PATH = PROJECT_ROOT / "old_system_reference" / "token.json"',
    'THRESHOLDS_PATH = PROJECT_ROOT / "data_v2" / "similarity_engine_training" / "sp500_percentile_v1" / "similarity_percentile_sandbox_thresholds.json"\nTOKEN_PATH = PROJECT_ROOT / "old_system_reference" / "token.json"'
)

insert_after = '''def read_allowed_symbols():
    if not ALLOWED_PATH.exists():
        raise SystemExit(f"Missing allowed symbols file: {ALLOWED_PATH}")

    symbols = []
    seen = set()

    for line in ALLOWED_PATH.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip().upper()
        if s and s not in seen:
            seen.add(s)
            symbols.append(s)

    if not symbols:
        raise SystemExit("Allowed symbols file is empty.")

    return symbols
'''

replacement = insert_after + '''


def load_percentile_thresholds():
    if not THRESHOLDS_PATH.exists():
        raise SystemExit(f"Missing percentile thresholds file: {THRESHOLDS_PATH}")

    payload = load_json(THRESHOLDS_PATH)
    symbols = payload.get("symbols", {})

    if not symbols:
        raise SystemExit("Percentile threshold file has no symbols.")

    return payload
'''

if "def load_percentile_thresholds" not in text:
    text = text.replace(insert_after, replacement)

text = text.replace(
    '    model = load_json(MODEL_PATH)\n    allowed_symbols = read_allowed_symbols()',
    '    model = load_json(MODEL_PATH)\n    allowed_symbols = read_allowed_symbols()\n    threshold_payload = load_percentile_thresholds()\n    percentile_thresholds = threshold_payload.get("symbols", {})'
)

text = text.replace(
    '    score_threshold = safe_float(account.get("score_threshold"), 51.5)',
    '    default_score_threshold = safe_float(account.get("fallback_score_threshold"), 51.5)'
)

text = text.replace(
    '    print("Score threshold:", score_threshold)',
    '    print("Threshold mode: symbol-specific top10 percentile threshold")'
)

text = text.replace(
    '        score = score_info["score"]\n\n        q = quotes.get(symbol, {})',
    '        score = score_info["score"]\n        symbol_threshold_data = percentile_thresholds.get(symbol, {})\n        symbol_threshold = safe_float(symbol_threshold_data.get("top10_score_threshold"), default_score_threshold)\n\n        q = quotes.get(symbol, {})'
)

text = text.replace(
    '            "status": "CANDIDATE" if score >= score_threshold else "WATCH",\n            "score": round(score, 4),',
    '            "status": "CANDIDATE" if score >= symbol_threshold else "WATCH",\n            "score": round(score, 4),\n            "symbol_threshold": round(symbol_threshold, 6),\n            "below_threshold": round(symbol_threshold - score, 6),'
)

text = text.replace(
    '    account["last_scan"] = {\n        "time": now_iso(),\n        "build": BUILD,\n        "score_threshold": score_threshold,',
    '    account["last_scan"] = {\n        "time": now_iso(),\n        "build": BUILD,\n        "threshold_mode": "symbol_specific_top10_score_threshold",\n        "thresholds_path": str(THRESHOLDS_PATH),'
)

text = text.replace(
    '"reason": "Similarity sandbox score met threshold.",',
    '"reason": "Similarity percentile sandbox score met symbol-specific threshold.",'
)

text = text.replace(
    'This is PAPER ONLY and does NOT touch main V2.',
    'This is PAPER ONLY, percentile-calibrated, and does NOT touch main V2.'
)

text = text.replace(
    '            "score=", c.get("score", ""),\n            "last=", c.get("last_price", ""),',
    '            "score=", c.get("score", ""),\n            "threshold=", c.get("symbol_threshold", ""),\n            "below=", c.get("below_threshold", ""),\n            "last=", c.get("last_price", ""),'
)

dst.write_text(text, encoding="utf-8")

print("Created:", dst)
