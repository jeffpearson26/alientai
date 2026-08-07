# Full-archive multi-resolution technical ranker

Date frozen: 2026-08-07, before the new full-Nasdaq daily/five-minute archive
was complete or any result from this isolated run was observed.

Status: queued historical research; no paper/live execution.

## Purpose and identity

This is the clean completion run of the previously blocked multi-resolution
Nasdaq ranker. It is a new isolated model family and does not alter, overwrite,
or inherit evidence from any model screened on 2026-08-06.

Model IDs:

- `full_archive_multiresolution_nasdaq101_h05_v1_20260807`
- `full_archive_multiresolution_nasdaq101_h20_v1_20260807`

## Universe and source

- Candidates: the exact 101 symbols in
  `nasdaq100_2026-06_symbols.txt`.
- QQQ and SPY: daily market context only; never eligible selections.
- The broader 6,247-symbol archive is a data source, not permission to expand
  or retrospectively choose the candidate universe.
- Candidate and QQQ data must come from the independently audited full
  active-Nasdaq Alpha Vantage adjusted-daily and five-minute archives.
- SPY daily context must come from the separately preserved source-pure Alpha
  Vantage adjusted-daily file and be fingerprinted.
- Fixed 2026 constituents retain survivorship and selection bias.

Daily OHLC uses same-date adjusted-close scaling and raw point-in-time volume.
It must not split-adjust historical volume with a later split factor.
Five-minute data use the frozen `adjusted=true`, `extended_hours=true`,
America/New_York interval-start contract. Missing or unavailable months remain
missing. No alternate provider may be inserted.

## Inputs

Candidate-specific completed-daily technicals:

- 5-session return
- 10-session return
- ROC(10)
- RSI(14)
- stochastic %K(14)
- CCI(20)
- relative volume versus 20 sessions
- Bollinger %B(20)
- ATR(14) as a percentage of price
- distance to EMA(10)
- MACD histogram as a percentage of price
- 5-session relative strength versus QQQ and SPY

Completed-decision-session five-minute summaries:

- regular-session return, range, realized volatility, close location,
  last-hour return, up-volume fraction, and observed-bar fraction
- 16:00-19:55 ET after-hours return, range, close location, volume relative
  to the regular session, up-volume fraction, and observed-bar fraction

QQQ/SPY context:

- 5- and 20-session returns
- 20-session realized volatility

Candidate-specific values become same-date cross-sectional percentile ranks.
QQQ/SPY context remains raw. The system requires at least $20 million trailing
20-session average dollar volume and at least 95% candidate coverage per
decision date.

Explicit exclusions: options, option chains, call activity, news, sentiment,
fundamentals, earnings calendars, premarket data, one-minute features, and
future information.

## Labels and models

- Decision: 20:00 ET after a completed decision session.
- Entry: next complete regular-session open.
- Exits: fifth and twentieth subsequent complete regular-session closes.
- Cost: 0.25% round trip.
- Target: within-date rank of the horizon's post-cost return.
- Challengers: independent regularized LightGBM and XGBoost.
- Ablations: `daily_only` and `daily_plus_5minute`.
- Horizons are trained, validated, stored, and reported independently.

## Validation and sealing

- Whole decision dates only.
- Three contiguous development folds.
- Exact label-interval purge plus a full horizon-length embargo.
- Latest 15% of dates (minimum ten) form the sealed test.
- A separate horizon-length pre-test embargo separates development and test.
- The compiler writes separately hashed development and sealed-test shards.
  The trainer may load only the development shard until a challenger passes.
- Validation gate: at least 100 signals over 20 dates, positive mean and
  median net return, at least 50% wins, mean Rank IC at least 0.01, positive
  top-minus-bottom spread, and a positive date-clustered lower 95% bound.
- Policies are limited to the 85th, 90th, and 95th score percentiles, capped
  at 15 equal-weight names per date.
- If validation fails, the test remains `SEALED_UNLOADED`. If validation
  passes, the test may be opened exactly once and the result must be preserved
  without retuning.

All outcomes remain research-only. Historical passage is not permission for
paper/live trading because the fixed contemporary universe is biased and the
result still requires genuinely future confirmation.
