from pathlib import Path

path = Path("train_v2_prediction_friday_down_from_daily.py")
text = path.read_text(encoding="utf-8-sig")

backup = Path("train_v2_prediction_friday_down_from_daily_BACKUP_ORIGINAL_COPY.py")
backup.write_text(text, encoding="utf-8")

# Rename build/output identity.
text = text.replace(
    'ALIENTAI_V2_PREDICTION_FRIDAY_DAILY_TRAINER_V1',
    'ALIENTAI_V2_PREDICTION_FRIDAY_DOWN_DAILY_TRAINER_V1'
)

text = text.replace(
    'prediction_friday_daily_training',
    'prediction_friday_down_daily_training'
)

text = text.replace(
    'prediction_friday_daily_records.jsonl',
    'prediction_friday_down_daily_records.jsonl'
)

text = text.replace(
    'prediction_friday_daily_summary.csv',
    'prediction_friday_down_daily_summary.csv'
)

text = text.replace(
    'prediction_friday_daily_summary.json',
    'prediction_friday_down_daily_summary.json'
)

text = text.replace(
    'prediction_friday_symbol_policy.json',
    'prediction_friday_down_symbol_policy.json'
)

text = text.replace(
    'prediction_friday_allow_symbols.txt',
    'prediction_friday_down_allow_symbols.txt'
)

# Change language labels where easy.
text = text.replace(
    'Target: outcome by same week\\'s final trading day, normally Friday.',
    'Target: DOWN outcome by same week\\'s final trading day, normally Friday.'
)

text = text.replace(
    'same_week_final_trading_day_normally_friday',
    'down_by_same_week_final_trading_day_normally_friday'
)

# Invert the core outcome logic.
# The original trainer likely treats future return > 0 as a win.
# We patch common variable names/expressions to make negative future return the win.
replacements = [
    ('future_return_pct > 0', 'future_return_pct < 0'),
    ('future_return_pct >= 0', 'future_return_pct < 0'),
    ('future_friday_return_pct > 0', 'future_friday_return_pct < 0'),
    ('future_friday_return_pct >= 0', 'future_friday_return_pct < 0'),
    ('forward_return_pct > 0', 'forward_return_pct < 0'),
    ('forward_return_pct >= 0', 'forward_return_pct < 0'),
    ('avg_buy_future_friday_return_pct > 0', 'avg_buy_future_friday_return_pct < 0'),
]

hits = 0
for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        hits += 1

# Rename some output labels from buy language to down/short language.
text = text.replace('buy_candidate_win_rate_pct', 'down_candidate_win_rate_pct')
text = text.replace('avg_buy_future_friday_return_pct', 'avg_down_future_friday_return_pct')
text = text.replace('buy_candidates', 'down_candidates')
text = text.replace('total_buy_candidates', 'total_down_candidates')

text = text.replace('ALLOW_BUY_STRONG', 'ALLOW_DOWN_STRONG')
text = text.replace('ALLOW_BUY', 'ALLOW_DOWN')
text = text.replace('BLOCK_BUY', 'BLOCK_DOWN')

text = text.replace('Top Friday allow symbols:', 'Top Friday DOWN allow symbols:')
text = text.replace('Top allow symbols:', 'Top DOWN allow symbols:')
text = text.replace('Top watch-only symbols:', 'Top DOWN watch-only symbols:')

path.write_text(text, encoding="utf-8")

print("Created Friday DOWN trainer.")
print("Outcome inversion replacements made:", hits)
print("If hits is 0, we need to inspect the original trainer's exact outcome variable names.")
