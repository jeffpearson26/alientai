from pathlib import Path

path = Path("alientai_v2/engines/prediction_20day.py")
text = path.read_text(encoding="utf-8-sig")

# Remove any broken/partial helper block if it exists somewhere odd.
start_marker = "# --- V2 MASTER 20-DAY POLICY HELPERS ---"
end_marker = "# --- END V2 MASTER 20-DAY POLICY HELPERS ---"

if start_marker in text and end_marker in text:
    start = text.index(start_marker)
    end = text.index(end_marker) + len(end_marker)
    text = text[:start] + text[end:]

helper = r'''
# --- V2 MASTER 20-DAY POLICY HELPERS ---
from pathlib import Path as _V2PolicyPath
import json as _v2_policy_json

_MASTER_POLICY_CACHE = None


def _v2_project_root_for_policy() -> _V2PolicyPath:
    # prediction_20day.py is:
    # project_root/alientai_v2/engines/prediction_20day.py
    return _V2PolicyPath(__file__).resolve().parents[2]


def _load_prediction_20day_master_policy() -> dict:
    global _MASTER_POLICY_CACHE

    if isinstance(_MASTER_POLICY_CACHE, dict):
        return _MASTER_POLICY_CACHE

    root = _v2_project_root_for_policy()

    master_path = (
        root
        / "data_v2"
        / "prediction_20day_daily_training"
        / "prediction_20day_master_symbol_policy.json"
    )

    old_path = (
        root
        / "data_v2"
        / "prediction_20day_daily_training"
        / "prediction_20day_symbol_policy.json"
    )

    raw = {}

    try:
        path_to_use = master_path if master_path.exists() else old_path
        if path_to_use.exists():
            raw = _v2_policy_json.loads(path_to_use.read_text(encoding="utf-8-sig"))
    except Exception:
        raw = {}

    if isinstance(raw, dict) and isinstance(raw.get("policy"), dict):
        raw_policy = raw.get("policy", {})
    elif isinstance(raw, dict):
        raw_policy = raw
    else:
        raw_policy = {}

    normalized = {}

    if isinstance(raw_policy, dict):
        for symbol, value in raw_policy.items():
            sym = str(symbol or "").upper().strip()
            if not sym:
                continue

            if isinstance(value, dict):
                info = dict(value)
                info["policy"] = str(info.get("policy") or "NO_DATA").upper()
                normalized[sym] = info
            else:
                normalized[sym] = {
                    "policy": str(value or "NO_DATA").upper()
                }

    _MASTER_POLICY_CACHE = normalized
    return normalized


def get_prediction_20day_master_policy(symbol: str) -> dict:
    symbol = str(symbol or "").upper().strip()
    policy_map = _load_prediction_20day_master_policy()

    value = policy_map.get(symbol)

    if isinstance(value, dict):
        return value

    return {"policy": "NO_DATA"}


def apply_prediction_20day_master_policy(symbol: str, decision: str, score: float, reason: str):
    policy_info = get_prediction_20day_master_policy(symbol)
    policy = str(policy_info.get("policy", "NO_DATA")).upper()

    decision = str(decision or "AVOID").upper()
    score = float(score or 0.0)
    reason = str(reason or "")

    buy_like = {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}

    if policy in {"BLOCK_BUY", "NO_DATA"}:
        if decision in buy_like:
            decision = "AVOID" if policy == "BLOCK_BUY" else "WATCH"
        score = min(score, 39.0)
        reason += f" Master20dPolicy={policy}: buy blocked."

    elif policy == "WATCH_ONLY":
        if decision in buy_like:
            decision = "WATCH"
        score = min(score, 49.0)
        reason += " Master20dPolicy=WATCH_ONLY: watch only."

    elif policy == "ALLOW_SMALL":
        if score >= 45.0:
            decision = "BUY_CANDIDATE"
        else:
            decision = "WATCH"
        score = max(score, 55.0)
        reason += " Master20dPolicy=ALLOW_SMALL: tiny paper position only."

    elif policy == "ALLOW_BUY":
        if score >= 45.0:
            decision = "BUY_CANDIDATE"
        score = max(score, 55.0)
        reason += " Master20dPolicy=ALLOW_BUY."

    elif policy == "ALLOW_BUY_STRONG":
        if score >= 40.0:
            decision = "BUY_CANDIDATE"
        score = max(score, 62.0)
        reason += " Master20dPolicy=ALLOW_BUY_STRONG."

    else:
        reason += f" Master20dPolicy={policy}."

    return decision, score, reason, policy_info
# --- END V2 MASTER 20-DAY POLICY HELPERS ---
'''

scan_marker = "def scan("
if scan_marker not in text:
    raise SystemExit("Could not find def scan(...) in prediction_20day.py")

idx = text.index(scan_marker)
text = text[:idx] + helper + "\n\n" + text[idx:]

path.write_text(text, encoding="utf-8")
