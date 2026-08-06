# Technical-only cross-sectional ranker specification

Date frozen: 2026-08-06, before historical results were inspected

Status: research only; no paper or live execution

## Isolation

This model family preserves the prior cross-sectional design but receives
technical inputs only. It must not read or use:

- options, option chains, implied volatility, or call activity
- news, headlines, sentiment, transcripts, or fundamentals
- one-minute or five-minute candles
- intraday, premarket, or after-hours data
- earnings calendars or any other event feature

The only market data are completed one-day OHLCV candles. QQQ and SPY remain
technical reference series only and cannot be selected.

## Universes and horizons

- Nasdaq: exact 101 candidates in `nasdaq100_2026-06_symbols.txt`.
- S&P: exact 483 candidates in
  `data_v2/rcef_research/lightgbm_shadow_symbols_2026-07-21.txt`.
- Separate 5-session and 20-session targets for each universe.
- A decision date enters the panel only when every candidate and both reference
  ETFs have the completed daily session, enough prior history, and the exact
  future sessions required to form both labels.
- The fixed contemporary lists retain survivorship and selection bias.

## Technical inputs

Candidate-specific features:

- 5-session return
- 10-session return
- ROC(10)
- RSI(14)
- Stochastic %K(14)
- CCI(20)
- relative volume versus 20 sessions
- Bollinger %B(20)
- ATR(14) as a percentage of price
- distance to EMA(10)
- MACD histogram as a percentage of price
- 5-session relative strength versus QQQ
- 5-session relative strength versus SPY

Reference context:

- QQQ 5- and 20-session returns and 20-session realized volatility
- SPY 5- and 20-session returns and 20-session realized volatility

Candidate-specific values become same-date cross-sectional percentile ranks.
QQQ/SPY context remains raw because it is constant across that date's
cross-section. ROC(10) and 10-session return are retained as Jeff requested,
with their algebraic redundancy disclosed.

Candidate rows require at least $20 million of trailing 20-session average
dollar volume. QQQ and SPY are never candidate rows.

## Timing, labels, and cost

- Decision cutoff: 8:00 p.m. Eastern following the completed decision session.
- Entry: next complete regular-session open.
- Exit: official close of the fifth or twentieth subsequent complete session.
- Cost: exactly 0.25% round trip.
- Target: same-date percentile rank of the horizon's post-cost return.

## Models and validation

- Independent regularized LightGBM and XGBoost challengers.
- Whole-date contiguous development folds.
- Exact label-overlap purge and full horizon-length embargo.
- Latest historical dates form a separately sealed test.
- The test opens once only if a challenger passes the predeclared validation
  gate; otherwise it remains `SEALED_UNLOADED`.
- Policy thresholds are limited to the 85th, 90th, and 95th score percentiles,
  capped at 15 equal-weight selections per date.
- Gate: at least 100 signals across 20 dates, positive mean and median
  post-cost return, at least 50% wins, mean rank IC of at least 0.01, positive
  top-minus-bottom spread, and positive lower date-clustered 95% confidence
  bound.

Historical output remains `AVOID` and research-only regardless of result.
