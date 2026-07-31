# AI/Semiconductor One-Hour Horizon Study — 2026-07-31

## Frozen research contract

- Universe: 17 AI/semiconductor/infrastructure symbols.
- Current-morning information: premarket data through 09:25 ET.
- Prior-session information only: technical and unusual-call features.
- Entry: 09:30 ET five-minute bar open.
- Exit: 10:25 ET five-minute bar close, representing 60 elapsed minutes.
- Round-trip cost: 0.25% deducted from every outcome.
- Positive label: net return greater than or equal to 0%.
- Research only; execution remains disabled.

The panel uses the same strict timing controls as the corrected 20-minute study.
No same-day closing technical data or same-day completed call activity is visible
to the model.

## Coverage and evaluation

- 1,302 leakage-safe labelled rows
- 17 symbols and 104 market dates
- Training: 777 rows, ending 2026-04-22
- Validation: 251 rows / 20 daily cohorts
- Held-out test: 247 rows / 20 daily cohorts
- Each date is ranked independently.
- The daily selection fraction is chosen using validation only and then applied
  unchanged to the held-out dates.

## Held-out daily-policy results

| Model | Frozen daily fraction | Test days | Trades | Positive days | Mean daily net | Mean trade net | Compounded return | Max drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Prior-close technical | Top 50% | 20 | 129 | 55% | +0.15% | +0.31% | +2.67% | -5.05% |
| Technical + 09:25 premarket | Top 10% | 20 | 28 | 65% | +0.62% | +0.87% | +12.39% | -5.93% |
| Technical + premarket + prior-day unusual calls | Top 10% | 20 | 28 | **65%** | **+0.70%** | **+1.03%** | **+14.28%** | **-5.70%** |

## Decision

- The one-hour technical+premarket+prior-day-unusual-call model is the leading
  candidate from this experiment.
- It outperformed the otherwise identical technical+premarket model, although the
  difference is based on only 20 held-out dates.
- Freeze both leading models for prospective comparison. Do not tune again on
  the current held-out dates.
- No paper/live authorization follows from this study. Opening spread, liquidity,
  auction-fill, latency, and capacity controls still require prospective evidence.

