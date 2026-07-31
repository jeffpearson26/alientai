# AI/Semiconductor 20-Minute Horizon Study — 2026-07-31

## Frozen research contract

- Universe: 17 AI/semiconductor/infrastructure symbols.
- Current-morning information: premarket data through 09:25 ET.
- Prior-session information only: technical and unusual-call features.
- Entry: 09:30 ET five-minute bar open.
- Exit: 09:45 ET five-minute bar close, representing 20 elapsed minutes.
- Round-trip cost: 0.25% deducted from every outcome.
- Positive label: net return greater than or equal to 0%.
- Research only; execution remains disabled.

The first exploratory run was discarded because it accidentally used the same
day's closing technical and call data. The corrected panel shifts those fields
to the immediately preceding market session and fails closed where an exact
prior-session feature row is unavailable.

## Coverage

- 1,302 leakage-safe labelled rows
- 17 symbols
- 104 market dates
- 392 rows excluded because an exact prior-session feature row was unavailable
- Training: 777 rows, ending 2026-04-22
- Validation: 251 rows / 20 daily cohorts, 2026-04-24 through 2026-05-28
- Held-out test: 247 rows / 20 daily cohorts, beginning 2026-05-30

## Executable daily-rank results

Each morning is ranked independently. The selection fraction is chosen using
validation only and then applied unchanged to held-out dates.

| Model | Frozen daily fraction | Test days | Trades | Positive days | Mean daily net | Compounded test return | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|
| Prior-close technical | Top 20% | 20 | 56 | 65% | +0.10% | +1.87% | -5.50% |
| Technical + 09:25 premarket | Top 10% | 20 | 28 | **70%** | **+0.52%** | **+10.62%** | **-4.56%** |
| Technical + premarket + prior-day unusual calls | Top 10% | 20 | 28 | 60% | +0.28% | +5.44% | -4.98% |

The technical+premarket model had a +0.60% mean net return per held-out trade.
The unusual-call addition remained positive but did not improve on premarket alone.

## Decision

- The technical+premarket 20-minute model is the leading candidate from this study.
- Twenty held-out dates are insufficient to authorize paper or live trading.
- Freeze the model, feature contract, and top-10% daily policy.
- The next valid evidence must come from new prospective dates; do not tune again
  on this held-out period.
- Real execution would additionally require spread, liquidity, opening-auction,
  and fill-quality controls beyond the current 0.25% cost assumption.
