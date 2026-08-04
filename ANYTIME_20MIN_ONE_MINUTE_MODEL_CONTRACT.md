# Any-Time 20-Minute One-Minute Model Contract

Status: active development, research only  
Created: 2026-08-04

## Question

For an eligible Nasdaq-universe ticker at an eligible regular-session minute,
what is the distribution of its price return over the next 20 regular-session
minutes?

This is distinct from the frozen opening models, which predict fixed intervals
after 09:30 Eastern. Those models and their evidence remain unchanged.

## Timing

- Source timestamps are one-minute interval starts in `America/New_York`.
- Use only a candle whose full one-minute interval has completed.
- `effective_as_of` is the close of the newest fully completed minute.
- The target is the close of the twentieth subsequent regular-session minute.
- Do not create labels that cross 16:00 Eastern or an overnight boundary.
- Eligible effective times are 09:31 through 15:40 Eastern.
- A query received during a partially formed minute uses the preceding complete
  minute and reports that effective timestamp. One-minute candles cannot support
  an exact-to-the-second 20-minute claim.

## Historical source and universe

- Alpha Vantage adjusted one-minute `TIME_SERIES_INTRADAY`.
- Completed months 2020-01 through 2026-07.
- The exact 101-symbol Nasdaq file plus QQQ and SPY as market context.
- Supplemental AI/data-center symbols may be added only through a separate
  audited archive and a new frozen universe version.

## Leakage controls

- Every feature must be computable at or before `effective_as_of`.
- The partially formed current minute is forbidden.
- Split by whole market dates, preserve chronological order, and purge label
  overlap at partition boundaries.
- Align QQQ/SPY context to the exact same completed timestamp.
- Preserve missingness; do not fill missing bars using future information.
- Never use post-query headlines, options activity, prices, or outcomes.

## Initial feature families

- one-, two-, five-, ten-, twenty-, and sixty-minute returns;
- intraday range, realized volatility, volume acceleration, and VWAP distance;
- session return, distance from session high/low, and minutes since open;
- exact-timestamp QQQ/SPY returns and symbol-relative residuals;
- time-of-day and day-of-week context;
- explicit history/coverage indicators.

The first model intentionally excludes news, options, and fundamentals so the
intraday price/volume baseline can be measured honestly. Those families require
their own point-in-time one-minute availability contracts and ablations.

## Outputs

- predicted gross 20-minute return;
- probability of a positive return after the frozen research cost;
- uncertainty and an explicit abstention state;
- effective input timestamp and target timestamp;
- source, model hash, universe version, and data-coverage diagnostics.

## Evaluation

- chronological train, validation, and untouched test periods;
- model and all cutoffs selected using train/validation only;
- report gross and 0.25%-cost-adjusted mean, median, win rate, calibration,
  fifth percentile, worst observation, concentration, and time-of-day/regime
  stability;
- compare against unconditional, QQQ-relative, momentum, and mean-reversion
  controls;
- preserve overlapping observations for realistic query behavior and a
  separate non-overlapping cohort analysis.

No historical result authorizes paper or live trading. A future live research
scorer also requires a source-compatibility audit between the Alpha Vantage
training archive and its chosen current one-minute feed.
