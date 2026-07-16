from pathlib import Path

path = Path("alientai_v2/engines/prediction_20day.py")
text = path.read_text(encoding="utf-8-sig")

old = '''        # Apply master 20-day policy.
        #
        # This gates the live placeholder score using the daily walk-forward
'''

new = '''        reason = "; ".join(reasons) if reasons else f"20-day prediction candidate from {ENGINE_ID}."

        # Apply master 20-day policy.
        #
        # This gates the live placeholder score using the daily walk-forward
'''

if old not in text:
    raise SystemExit("Could not find master policy comment block.")

text = text.replace(old, new)

old2 = '''                reason=f"20-day prediction candidate from {ENGINE_ID}.",
                quote=quote,
                warnings=warnings,
                reasons=reasons,
'''

new2 = '''                reason=reason,
                quote=quote,
                warnings=warnings,
                reasons=reasons + [
                    f"Master 20-day policy: {master_policy_info.get('policy')}",
                    f"Master buy win rate: {master_policy_info.get('buy_candidate_win_rate_pct')}",
                    f"Master avg buy return: {master_policy_info.get('avg_buy_future_20d_return_pct')}",
                    f"Master records: {master_policy_info.get('records')}",
                    f"Master buy candidates: {master_policy_info.get('buy_candidates')}",
                ],
'''

if old2 not in text:
    raise SystemExit("Could not find candidate reason block.")

text = text.replace(old2, new2)

path.write_text(text, encoding="utf-8")
