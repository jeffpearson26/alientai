# AI17 Intraday-Resolution + Call-History Five-Session Models

Date: 2026-08-05  
Status: complete; both models are research hold  
Execution: disabled

## Model contract

Two matched models were trained for the fixed 17-symbol AI/semiconductor
universe:

AMD, AMAT, AMZN, ANET, AVGO, CDNS, GOOGL, KLAC, LRCX, META, MSFT, MU, NVDA,
ORCL, PLTR, SMCI, and SNPS.

QQQ and SPY are benchmark/context inputs only and cannot be selected.

- Version 1 uses native one-minute regular-session features.
- Version 2 uses strict five-minute resampling of the same one-minute source.
- Decision occurs after a completed regular session.
- Entry is the next regular-session open.
- Exit is the fifth subsequent regular-session close.
- Round-trip cost is 0.25%.
- Zero through five selections are permitted; the models may fully abstain.

## Previous-session options rule

Every new prospective decision must use the option chains from the immediately
preceding completed market session. August 4 chains apply only to the August 5
decision. The next decision must use August 5 chains, and so on. Current-session
option activity is never substituted into that day's decision.

Call history is available to the models through:

- at least ten strictly earlier call observations;
- call-volume z-score;
- call volume versus its prior rolling median;
- call volume/open-interest ratio;
- aggregate call volume and call open interest;
- near-money call implied volatility;
- total and liquid chain-contract counts.

The selection gate additionally requires a call-volume z-score of at least
3.0. Missing/empty chains remain unavailable and can never become zero volume.

Alpha Vantage chains contain aggregate call volume, not buyer-initiated
time-and-sales. These features are therefore unusual **call activity**, not
verified unusual call buying.

## Data

- Missing ANET, ORCL, and SMCI one-minute histories were collected separately:
  237/237 monthly requests complete, zero unavailable, zero failed.
- August current-month data: 19/19 files complete for the 17 symbols plus
  QQQ/SPY.
- August 4 options: all 17 exact chains are nonempty.
- One-minute panel: 26,405 rows, 2020-03-30 through 2026-07-28.
- Five-minute panel: 26,761 rows over the same date range.
- Each panel has 1,966 exact call-feature rows and 83 unusual-call rows.
- Both August 4 prospective snapshots contain all 17 symbols and all 17 exact
  call-history rows.

## Architecture and leakage controls

Each resolution contains two frozen components:

1. Long-history technical/benchmark component, trained on 2020-2023,
   early-stopped on 2024, and refit through the embargoed end of 2025.
2. Call-aware component, trained on earlier 2026 call rows, early-stopped on
   May 2026, historically checked only from June 1 onward, then refit on all
   fully matured pre-August-4 observations for the new prospective score.

The final score is the fixed 50/50 mean of the two component probabilities.
Five-session labels are purged at chronological boundaries. August 4
prospective rows contain no outcome fields.

## Historical call-aware holdout

Both resolution variants selected the same 19 signals across 17 decision dates:

| Metric | 1-minute | 5-minute |
|---|---:|---:|
| Signals | 19 | 19 |
| Win rate | 36.84% | 36.84% |
| Mean net return | -2.748% | -2.748% |
| Median net return | -3.040% | -3.040% |
| Date-clustered bootstrap 95% CI | -5.471% to -0.293% | -5.471% to -0.293% |
| Worst signal | -15.515% | -15.515% |
| Cash-scaled max drawdown | -2.075% | -2.075% |
| Abstention rate | 56.41% | 56.41% |

The call-aware component stopped at one boosting iteration for both
resolutions, another indication that the validation slice did not support a
strong learned call-history relationship.

## August 4 prospective snapshot

Both research models produced one diagnostic selection for the next session:

| Model | Symbol | Technical probability | Call-aware probability | Combined score | Call-volume z-score |
|---|---|---:|---:|---:|---:|
| 1-minute | PLTR | 0.627651 | 0.505971 | 0.566811 | 9.442 |
| 5-minute | PLTR | 0.571505 | 0.505430 | 0.538468 | 9.442 |

Because both models failed the historical holdout, this PLTR result is only an
immutable research prediction. It is not a paper/live authorization and does
not establish a positive edge.

## Conclusion

The requested models are built and call history is genuinely available to the
learned call-aware components. The expanded 17-symbol thesis did not validate:
its later historical result was materially negative with an entirely negative
confidence interval. Preserve the August 4 prediction for future evaluation,
but do not promote or retune these variants from that outcome.

Machine-readable results:

`data_v2\rcef_research\ai17_intraday_call_five_session\models\comparison.json`
