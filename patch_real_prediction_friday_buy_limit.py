from pathlib import Path

path = Path("alientai_v2/engine.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("alientai_v2/engine_BACKUP_BEFORE_REAL_FRIDAY_BUY_LIMIT.py")
backup.write_text(text, encoding="utf-8")

# 1. Add Friday per-scan counter.
old_counter = '''    buy_actions: List[Dict[str, Any]] = []
'''

new_counter = '''    buy_actions: List[Dict[str, Any]] = []
    friday_buys_this_scan = 0
'''

if old_counter not in text:
    raise SystemExit("Could not find buy_actions typed marker.")

if "friday_buys_this_scan = 0" not in text:
    text = text.replace(old_counter, new_counter, 1)


# 2. Add Friday limit inside the candidate loop, before approval.
old_loop_gate = '''            if candidate.get("decision") not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                continue

            approval = approve_candidate_buy(
'''

new_loop_gate = '''            if candidate.get("decision") not in {"BUY_CANDIDATE", "STRONG_BUY_CANDIDATE"}:
                continue

            engine_id_for_limit = str(candidate.get("engine_id") or "").strip()

            if engine_id_for_limit == "prediction_friday":
                max_friday_buys = int(safe_float(settings.get("prediction_friday_max_buys_per_scan"), 1))
                max_friday_open = int(safe_float(settings.get("prediction_friday_max_open_positions"), 5))
                friday_reserve_cash = safe_float(settings.get("prediction_friday_min_cash_reserve"), 500.0)

                open_positions_for_limit = account.get("open_positions", {})
                if not isinstance(open_positions_for_limit, dict):
                    open_positions_for_limit = {}

                open_friday_count = 0
                for _sym, _pos in open_positions_for_limit.items():
                    if isinstance(_pos, dict) and str(_pos.get("engine_id") or "").strip() == "prediction_friday":
                        open_friday_count += 1

                current_cash_for_limit = safe_float(account.get("cash"), 0.0)

                if max_friday_buys >= 0 and friday_buys_this_scan >= max_friday_buys:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday buy limit reached: {friday_buys_this_scan}/{max_friday_buys} this scan."
                    continue

                if max_friday_open >= 0 and open_friday_count >= max_friday_open:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday open-position limit reached: {open_friday_count}/{max_friday_open}."
                    continue

                if current_cash_for_limit < friday_reserve_cash:
                    candidate["manager_decision"] = "REJECTED"
                    candidate["manager_reason"] = f"Friday cash reserve protected. Cash {current_cash_for_limit:.2f} below reserve {friday_reserve_cash:.2f}."
                    continue

            approval = approve_candidate_buy(
'''

if old_loop_gate not in text:
    raise SystemExit("Could not find candidate decision gate.")

if "Friday buy limit reached" not in text:
    text = text.replace(old_loop_gate, new_loop_gate, 1)


# 3. Increment Friday counter after a successful Friday buy.
old_append = '''            if trade:
                buy_actions.append(trade)
'''

new_append = '''            if trade:
                buy_actions.append(trade)
                if str(candidate.get("engine_id") or "").strip() == "prediction_friday":
                    friday_buys_this_scan += 1
'''

if old_append not in text:
    raise SystemExit("Could not find trade append block.")

if "friday_buys_this_scan += 1" not in text:
    text = text.replace(old_append, new_append, 1)

path.write_text(text, encoding="utf-8")
print("Patched real engine.py buy loop with Friday per-scan, max-open, and cash-reserve limits.")
