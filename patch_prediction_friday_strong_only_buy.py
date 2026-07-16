from pathlib import Path

path = Path("alientai_v2/engines/prediction_friday.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/engines/prediction_friday_BACKUP_BEFORE_STRONG_ONLY_BUY.py")
backup.write_text(text, encoding="utf-8")

if "def _raw_scan(" not in text:
    idx = text.find("def scan(")
    if idx == -1:
        raise SystemExit("Could not find def scan(...) in prediction_friday.py")
    text = text[:idx] + "def _raw_scan(" + text[idx + len("def scan("):]

wrapper = r'''

def _friday_policy_from_row(row: dict) -> str:
    for key in [
        "prediction_friday_policy",
        "prediction_friday_daily_policy",
        "friday_policy",
        "policy",
        "prediction_20day_daily_policy",
    ]:
        value = row.get(key)
        if value:
            return str(value).upper().strip()

    reason = str(row.get("reason") or "").upper()
    for policy in ["ALLOW_BUY_STRONG", "ALLOW_BUY", "WATCH_ONLY", "BLOCK_BUY", "NO_DATA"]:
        if policy in reason:
            return policy

    return "UNKNOWN"


def scan(quotes, settings):
    """
    Friday prediction live wrapper.

    Safety rules:
    - Only lets ALLOW_BUY_STRONG become BUY_CANDIDATE by default.
    - Normal ALLOW_BUY becomes WATCH unless settings explicitly allow it.
    - Can be disabled back to confirmation-only from data_v2/v2_settings.json.
    """
    rows = _raw_scan(quotes, settings)

    buying_enabled = bool(settings.get("prediction_friday_buying_enabled", False))
    confirmation_only = bool(settings.get("prediction_friday_confirmation_only", True))

    allow_policies = settings.get("prediction_friday_buy_policies", ["ALLOW_BUY_STRONG"])
    if not isinstance(allow_policies, list):
        allow_policies = ["ALLOW_BUY_STRONG"]

    allow_policies = {str(p).upper().strip() for p in allow_policies}

    adjusted = []

    for row in rows:
        if not isinstance(row, dict):
            adjusted.append(row)
            continue

        row["engine_id"] = "prediction_friday"
        row["prediction_horizon_days"] = 5.0
        row["minimum_hold_minutes"] = float(settings.get("prediction_friday_minimum_hold_minutes", 7200.0))

        policy = _friday_policy_from_row(row)
        row["prediction_friday_policy"] = policy

        original_decision = str(row.get("decision") or "").upper().strip()
        row["prediction_friday_original_decision"] = original_decision

        # If Friday buying is not enabled, downgrade buys to WATCH.
        if confirmation_only or not buying_enabled:
            if original_decision in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                row["decision"] = "WATCH"
                row["reason"] = str(row.get("reason", "")) + " Friday engine confirmation-only: buy downgraded to WATCH."
            adjusted.append(row)
            continue

        # Strong-only buying rule.
        if original_decision in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
            if policy not in allow_policies:
                row["decision"] = "WATCH"
                row["reason"] = (
                    str(row.get("reason", ""))
                    + f" Friday buying blocked because policy={policy}, allowed={sorted(allow_policies)}."
                )
            else:
                row["decision"] = "BUY_CANDIDATE"
                row["reason"] = (
                    str(row.get("reason", ""))
                    + f" Friday buying allowed by policy={policy}."
                )

        adjusted.append(row)

    return adjusted
'''

if "def _friday_policy_from_row" not in text:
    text = text.rstrip() + "\n" + wrapper + "\n"

path.write_text(text, encoding="utf-8")
print("Patched prediction_friday to allow strong-only paper buys.")
