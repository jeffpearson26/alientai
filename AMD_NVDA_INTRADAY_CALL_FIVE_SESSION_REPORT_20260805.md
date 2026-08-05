# AMD/NVDA Intraday-Resolution + Unusual-Call Five-Session Research

Date: 2026-08-05  
Status: complete; both models remain research hold  
Execution: disabled

## Objective

Train two otherwise matched AMD/NVDA-only technical-context models for a
five-session stock-return horizon:

1. Features derived from native one-minute regular-session candles.
2. Features derived from strict five-minute resampling of the same one-minute
   archive.

Both models may abstain. A historical candidate requires all of the following:

- the model's predicted probability of a positive net return exceeds 0.50;
- an exact non-empty Alpha Vantage option chain exists;
- at least ten strictly earlier call-volume observations exist;
- aggregate call volume has a rolling z-score of at least 3.0;
- at most one of AMD or NVDA is selected per decision date.

## Data and chronology

- Candle source: adjusted Alpha Vantage one-minute archive.
- Candle range used: 2020-03-30 through 2026-07-24.
- Rows: 3,169 for the one-minute panel; 3,174 for the five-minute panel.
- Exact option-feature rows: 240 per panel.
- Unusual aggregate-call rows: 10 per panel.
- Label: decision after the completed regular-session close; enter at the next
  regular-session open; exit at the fifth subsequent regular-session close.
- Assumed round-trip stock cost: 0.25%.
- Initial training: through 2023-12-21.
- Early-stopping validation: 2024-01-02 through 2024-12-23.
- Final pre-test refit: through 2025-12-23.
- Historical holdout: 2026-01-02 through 2026-07-24.
- Five-session label embargoes prevent labels from crossing partition
  boundaries.

Incomplete regular sessions are excluded. Valid early closes are retained.
Features include the symbol identity, daily momentum/pullback/volatility, and
resolution-specific intraday momentum, trend, range, VWAP, volume, and
volatility descriptors.

## Held-out results

| Model | Call-qualified picks | Win rate | Mean net return | Median net return | Bootstrap mean 95% CI | Worst pick | Capital-scaled drawdown |
|---|---:|---:|---:|---:|---:|---:|---:|
| Native 1-minute | 8 | 62.5% | +1.704% | +1.588% | -1.438% to +4.949% | -5.619% | -1.124% |
| Resampled 5-minute | 8 | 62.5% | +2.350% | +1.588% | -1.369% to +6.497% | -5.619% | -1.124% |

The five-minute version differs from the one-minute version on only one of the
eight selected dates. On 2026-04-10 it selected AMD rather than NVDA, accounting
for the higher mean return. This is not enough evidence to conclude that the
five-minute representation is superior.

For context, the ungated positive/top-one policies produced 140 selections:

| Model | Picks | Win rate | Mean net return | Bootstrap mean 95% CI | Capital-scaled drawdown |
|---|---:|---:|---:|---:|---:|
| Native 1-minute | 140 | 54.29% | +1.117% | -0.025% to +2.229% | -11.691% |
| Resampled 5-minute | 140 | 53.57% | +1.133% | -0.005% to +2.294% | -13.831% |

Even these larger samples have confidence intervals that touch or cross zero.

## Honest conclusion

Both variants show a positive nominal result, and the unusual-call gate improved
the observed win rate, but eight signals are far too few for promotion. Neither
model is authorized for paper or live execution. Both should be frozen as
development candidates and evaluated prospectively without retuning.

The Alpha Vantage historical chain supplies aggregate call volume, not
buyer-initiated option time-and-sales. Therefore `call_volume_unusual` is
accurately described as unusual **call activity**, not proven unusual call
buying. A true buy-volume feature requires a provider with trade-direction or
bid/ask-classified option prints.

## Reproduction

```powershell
.\.venv\Scripts\python.exe build_amd_nvda_intraday_five_session_panels.py `
  --candle-root D:\AlientAI\Data\AlphaVantage_2026\rolling_20m_nasdaq101_adjusted_1min_202001_202607 `
  --options-root D:\AlientAI\Data\AlphaVantage_2026\historical_options_natural_sp500_2026 `
  --output-root data_v2\rcef_research\amd_nvda_intraday_call_five_session

.\.venv\Scripts\python.exe train_amd_nvda_intraday_call_five_session.py `
  --panel-root data_v2\rcef_research\amd_nvda_intraday_call_five_session `
  --output-root data_v2\rcef_research\amd_nvda_intraday_call_five_session\models
```

Primary machine-readable comparison:

`data_v2\rcef_research\amd_nvda_intraday_call_five_session\models\comparison.json`
