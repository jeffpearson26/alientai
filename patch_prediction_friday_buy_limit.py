from pathlib import Path

path = Path("alientai_v2/engine.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/engine_BACKUP_BEFORE_FRIDAY_BUY_LIMIT.py")
backup.write_text(text, encoding="utf-8")

# Add a per-scan counter before the candidate buy loop.
marker = "buy_actions = []"
if marker not in text:
    raise SystemExit("Could not find buy_actions = [] marker.")

if "friday_buys_this_scan = 0" not in text:
    text = text.replace(
        marker,
        marker + "\n    friday_buys_this_scan = 0",
        1,
    )

# Insert Friday buy limit check before buy approval/execute logic.
# We look for the common loop area by finding candidate decision checks.
target = '''        if row.get("decision") != "BUY_CANDIDATE":
            continue
'''

insert = '''        if row.get("decision") != "BUY_CANDIDATE":
            continue

        engine_id_for_limit = str(row.get("engine_id") or "").strip()
        if engine_id_for_limit == "prediction_friday":
            max_friday_buys = int(safe_float(settings.get("prediction_friday_max_buys_per_scan"), 1))
            if max_friday_buys >= 0 and friday_buys_this_scan >= max_friday_buys:
                row["manager_decision"] = "BLOCKED"
                row["manager_reason"] = f"Friday buy limit reached: {friday_buys_this_scan}/{max_friday_buys} this scan."
                continue
'''

if target not in text:
    raise SystemExit("Could not find BUY_CANDIDATE loop target. Paste the buy loop around buy_actions if this fails.")

if "Friday buy limit reached" not in text:
    text = text.replace(target, insert, 1)

# After a successful buy action append, increment the Friday counter.
# Patch common location: after buy_actions.append(action)
append_marker = "buy_actions.append(action)"
if append_marker not in text:
    raise SystemExit("Could not find buy_actions.append(action).")

increment = '''buy_actions.append(action)
            if str(row.get("engine_id") or "").strip() == "prediction_friday":
                friday_buys_this_scan += 1'''

if "friday_buys_this_scan += 1" not in text:
    text = text.replace(append_marker, increment, 1)

path.write_text(text, encoding="utf-8")
print("Patched engine.py to enforce prediction_friday_max_buys_per_scan.")
