# AI/Semiconductor Five-Day Catalyst Study — 2026-07-31

## Research contract

- Universe: 17 current AI, semiconductor, equipment, and infrastructure symbols.
- Decision time: after the completed regular-session close.
- Entry: next market session open.
- Exit: fifth subsequent market session close.
- Cost: 0.25% round trip, deducted from every outcome.
- Winner label: net return at least 5%.
- Data source for outcomes: Alpha Vantage `TIME_SERIES_DAILY`.
- Research only; execution remains disabled.

## Point-in-time inputs

1. Technical indicators available at the decision close.
2. Premarket features ending at 09:25 ET on the decision date.
3. Historical unusual **call** activity only:
   `call_volume_open_interest_ratio`, `call_volume_vs_prior_median`,
   `call_volume_zscore`, `call_volume_unusual`, and prior-history count.
4. Conservative Alpha Vantage headline proxy for explicit, target-specific
   analyst upgrades and downgrades. This is not a licensed structured ratings feed.

Generic option features containing put volume, put volatility, or put/call ratios
were excluded from the corrected call variants.

## Coverage and split

- 1,694 rows
- 17 symbols
- 125 market dates, 2026-01-02 through 2026-07-02
- 796 rows with at least one conservatively parsed analyst-action event
- Training ended 2026-04-21
- Validation: 2026-04-29 through 2026-05-27
- Held-out test began 2026-06-04
- Labels were purged through their exact Alpha Vantage exit dates.

## Held-out findings

The basket fraction must be selected on validation, then evaluated once on test.

| Model | Validation-selected basket | Validation mean net | Held-out mean net | Held-out ≥5% rate | Held-out positive rate |
|---|---:|---:|---:|---:|---:|
| Technical | Top 10% (28) | +6.61% | -1.69% | 14.29% | 35.71% |
| Technical + premarket | Top 10% (28) | +6.63% | **+0.50%** | 25.00% | 42.86% |
| Technical + premarket + unusual calls | Top 20% (55) | +7.22% | -1.54% | 25.45% | 45.45% |
| Full + analyst proxy | Top 10% (28) | +6.99% | -2.61% | 46.43% | 67.86% |

The unusual-call model's held-out top 10% basket averaged +1.02%, but top 20%
was selected by validation and therefore governs the honest test conclusion.
Choosing top 10% after seeing test results would be test-set overfitting.

## Decision

- No variant is authorized for paper or live trading.
- Premarket remains the most transferable addition, but +0.50% across 28 held-out
  observations is preliminary and not yet robust.
- Unusual calls and analyst-action features remain research candidates, but the
  current formulations did not improve the validation-selected held-out portfolio.
- The next valid step is a new frozen prospective journal or a later, non-overlapping
  Alpha Vantage period. Do not tune again on the 2026-06-04 test partition.

