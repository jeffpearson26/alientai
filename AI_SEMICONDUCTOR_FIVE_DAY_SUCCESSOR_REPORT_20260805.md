# AI/Semiconductor Five-Session Successor

Status: **RESEARCH HOLD — SEALED TEST NOT LOADED**

This is a separate research-only successor. It does not change a frozen model,
`engine.py`, the control panel, paper trading, or live trading.

## Exact contract

- Universe: the existing 17-name AI/semiconductor/data-center research basket:
  AMD, AMAT, AMZN, ANET, AVGO, CDNS, GOOGL, KLAC, LRCX, META, MSFT, MU,
  NVDA, ORCL, PLTR, SMCI, and SNPS.
- Decision: after a completed regular-session close.
- Entry: next regular-session open.
- Exit: fifth subsequent regular-session close.
- Cost: 0.25% round trip.
- Maximum selections: five per decision date.
- Portfolio drawdown: cash-scaled across 25 possible overlapping slots
  (five new selections per day held for five sessions).
- Missing catalyst, premarket, analyst-proxy, and options data remains missing;
  it is never converted to zero.

## Panel

- 95,694 exact point-in-time rows.
- 6,665 distinct market dates.
- First decision date: 2000-01-26.
- Last fully labeled decision date: 2026-07-28.
- All 17 symbols passed the source and label audit.
- 1,694 rows have the richer exact-date 2026 catalyst overlay.
- The rich overlay is retained for a future frozen prospective layer, but was
  excluded from the long-history base fit because equivalent older
  point-in-time coverage does not exist.

Panel artifact:
`D:\AlientAI\Data\AlphaVantage_2026\ai_semiconductor_five_day_successor_20260804\panel.jsonl`

## Leakage controls

The chronology uses separate whole-date partitions for model fitting,
early-stopping validation, calibration, policy validation, and final testing.
Each internal boundary has a five-session embargo on both sides. No future
label is allowed in the feature set. The final 2022-08-09 through 2026-07-28
test partition is loaded only if a policy-validation rule passes every frozen
gate.

The model is a fixed equal-weight ensemble of:

1. a classifier estimating whether the five-session net return is positive;
2. a regressor estimating the five-session net return.

Standardization and confidence calibration use only the calibration partition.
Ranking uses the continuous ensemble score so isotonic confidence plateaus
cannot collapse different score percentiles into the same policy.

## Honest validation result

Two predeclared selection variants were evaluated without opening the test.

| Variant | Best validation policy | Signals | Dates | Mean net | Median net | Win rate | Clustered 95% lower bound | Cash-scaled drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| All eligible symbols | 90th percentile | 954 | 220 | +0.3629% | +0.3027% | 53.35% | -0.2879% | -20.56% |
| Thesis technical setups only | 60th percentile | 1,247 | 361 | +0.1039% | +0.4018% | 53.65% | -0.2759% | -16.89% |

Both variants show a modest positive validation signal, but neither passed the
predeclared uncertainty gate because its clustered 95% lower confidence bound
was below zero. The all-symbol variant also narrowly missed the -20% drawdown
floor. Therefore:

- no threshold was promoted;
- the final test remains `SEALED_UNLOADED`;
- no paper or live execution is authorized;
- the result is a legitimate development lead, not evidence of profitability.

Model artifacts:

- `D:\AlientAI\Models\ai_semiconductor_five_day_successor_schema3_all_20260804`
- `D:\AlientAI\Models\ai_semiconductor_five_day_successor_schema3_setup_20260804`

## What should happen next

The next scientifically useful improvement is not further tuning against this
same validation period. It is to expand timestamped historical catalyst,
earnings/guidance, analyst-action, premarket, and unusual-call coverage, then
train a catalyst-aware successor with the same partition and sealed-test
contract. The existing rich 2026 overlay can also be frozen for genuinely
future append-only prospective observations without using already-seen
outcomes to retune it.

Known limitation: this is a current thematic basket applied backward through
history, so survivorship and universe-selection bias remain.
