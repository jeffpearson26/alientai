# Daily-only cross-sectional ranker specification

Date frozen: 2026-08-06, before historical results were inspected

Status: research only; no paper or live execution

## Purpose

This is an isolated copy of the multi-resolution cross-sectional research
design with a narrower input contract. It preserves the two candidate
universes, the 5- and 20-session targets, the LightGBM/XGBoost challengers,
the date-local quantile-ranking logic, the QQQ/SPY reference context, the
liquidity rule, the label construction, and the 0.25% round-trip cost.

The only price candles this model may read are completed one-day OHLCV
candles. It must not read or derive features from one-minute or five-minute
candles, premarket data, regular-session intraday paths, after-hours data, or
news.

## Universes

- Nasdaq: the exact 101 candidates in `nasdaq100_2026-06_symbols.txt`.
- S&P: the exact 483 locally data-ready candidates in
  `data_v2/rcef_research/lightgbm_shadow_symbols_2026-07-21.txt`.
- QQQ and SPY supply market context only and are never eligible selections.
- Candidate rows require at least $20 million in trailing 20-session average
  dollar volume.
- Both lists are fixed contemporary universes and therefore retain historical
  survivorship and selection bias.

## Inputs

### Daily technical features

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
- 5-session relative strength versus QQQ and SPY
- QQQ/SPY 5- and 20-session return and 20-session realized-volatility context

Every candidate-specific value is transformed into a percentile rank using
only candidates on the same decision date. QQQ/SPY context remains raw.

### Recent call-option activity

The enhanced variant retains the previous build's point-in-time Alpha Vantage
call-chain aggregates:

- call volume
- call open interest
- call-volume/open-interest ratio
- call volume relative to the strictly prior 10-observation median
- call-volume z-score using only the strictly prior 20 observations
- near-money call implied volatility
- an explicit availability field

These are call-activity proxies; aggregate chains cannot prove buyer
initiation. Empty or unavailable chains are missing, never zero activity.
The daily-technical baseline and daily-plus-options challenger use identical
rows and dates.

## Explicit exclusions

- no one-minute or five-minute candle input
- no intraday summaries
- no premarket features
- no previous-session or current-session after-hours features
- no headline, sentiment, or news features
- no fundamentals or information published after the decision cutoff

The compiler has no command-line arguments for an intraday or news source, and
the independent audit rejects excluded feature names.

## Labels and timing

- Decision cutoff: 8:00 p.m. Eastern following a completed decision session,
  retained from the source design so all historical option-chain aggregates
  are available under the same point-in-time contract.
- Entry: next complete regular-session open.
- Exit: official close of the fifth or twentieth subsequent complete regular
  session.
- Cost: exactly 0.25% round trip.
- Target: same-date percentile rank of the horizon's post-cost return.

The two horizons have separate reports, validation, and sealed-test states.

## Models and validation

- Independent regularized LightGBM and XGBoost challengers.
- Whole decision dates remain intact.
- Three contiguous development folds.
- Training observations whose labels overlap a validation interval are purged.
- A full horizon-length embargo follows each validation interval.
- The latest historical dates form an independent sealed test.
- The test opens once only if a challenger passes every frozen validation
  requirement; otherwise it remains `SEALED_UNLOADED`.
- Minimum panel history: 60 common dates for 5 sessions and 120 common dates
  for 20 sessions.
- Selection thresholds are limited to the predeclared 85th, 90th, and 95th
  score percentiles, with at most 15 equal-weight names per date.
- The validation gate requires at least 100 signals over 20 dates, positive
  mean and median net returns, at least 50% wins, mean rank IC of at least
  0.01, positive top-minus-bottom spread, and a positive lower
  date-clustered 95% confidence bound.

All results remain `AVOID` and research-only regardless of historical outcome.
