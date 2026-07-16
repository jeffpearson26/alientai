from pathlib import Path

path = Path("alientai_v2/engines/prediction_20day.py")
text = path.read_text(encoding="utf-8-sig")

old = '''        if score >= 72:
            decision = "STRONG_BUY_CANDIDATE"
        elif score >= 55:
            decision = "BUY_CANDIDATE"
        elif score >= 40:
            decision = "WATCH"
        else:
            decision = "AVOID"

        candidates.append(
'''

new = '''        if score >= 72:
            decision = "STRONG_BUY_CANDIDATE"
        elif score >= 55:
            decision = "BUY_CANDIDATE"
        elif score >= 40:
            decision = "WATCH"
        else:
            decision = "AVOID"

        # Apply master 20-day policy.
        #
        # This gates the live placeholder score using the daily walk-forward
        # policy we trained from historical 1-day candles.
        #
        # Example:
        #   ALLOW_BUY_STRONG -> can become BUY_CANDIDATE
        #   ALLOW_BUY        -> can become BUY_CANDIDATE
        #   ALLOW_SMALL      -> can become BUY_CANDIDATE, but marked tiny
        #   WATCH_ONLY       -> visible but not buyable
        #   BLOCK_BUY        -> blocked
        #   NO_DATA          -> blocked unless we explicitly change that later
        decision, score, reason, master_policy_info = apply_prediction_20day_master_policy(
            symbol=symbol,
            decision=decision,
            score=score,
            reason=reason,
        )

        candidates.append(
'''

if old not in text:
    raise SystemExit("Could not find decision block to patch. The file may have changed.")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
