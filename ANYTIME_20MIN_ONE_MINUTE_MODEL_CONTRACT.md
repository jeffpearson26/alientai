# Any-Time Multi-Horizon One-Minute Model Contract

Status: active development, research only
Created: 2026-08-04

## Question

For an eligible Nasdaq-universe ticker at an eligible regular-session minute,
what is the distribution of its price return over the next 5, 10, 20, 30, 60,
or 90 regular-session minutes?

This is distinct from the frozen opening models, which predict fixed intervals
after 09:30 Eastern. Those models and their evidence remain unchanged.

## Timing

- Source timestamps are one-minute interval starts in `America/New_York`.
- Schema-v3 compiled shards store observation, entry, target-bar-start, and
  effective exit timestamps as signed 64-bit
  nanoseconds since the Unix epoch. The compiler and trainer reject any schema
  or timestamp-unit mismatch.
- Use only a candle whose full one-minute interval has completed.
- `effective_as_of` is the close of the newest fully completed minute.
- Historical entry is the next interval's recorded open and the target is the
  close of the horizon-th subsequent regular-session bar. The effective exit
  timestamp is one minute after that target bar's interval-start timestamp.
  The frozen 0.25% round-trip cost is intended to cover spread/slippage; exact
  next-bar-open fills are still a research approximation, not an execution
  promise.
- Do not create labels that cross 16:00 Eastern or an overnight boundary.
- The compiler independently excludes every observation whose entry or exit
  minute is missing or whose exit would cross 16:00 Eastern.
- A query received during a partially formed minute uses the preceding complete
  minute and reports that effective timestamp. One-minute candles cannot support
  an exact-to-the-second 20-minute claim.

## Historical source and universe

- Alpha Vantage adjusted one-minute `TIME_SERIES_INTRADAY`.
- Completed months 2020-01 through 2026-07.
- The exact 101-symbol Nasdaq file plus QQQ and SPY as market context.
- Supplemental AI/data-center symbols may be added only through a separate
  audited archive and a new frozen universe version. The compiler hashes the
  exact target list, requires identical archive semantics, and requires every
  requested symbol-month to be explicitly completed or unavailable.
- The exact 17-symbol AI/semiconductor clone is a separate experiment. It may
  combine the main archive with the independently audited supplement only for
  ANET, ORCL, and SMCI; it must never alter the Nasdaq-universe artifacts.
- Both universes are fixed contemporary research baskets and therefore retain
  survivorship/selection bias in historical tests. No retrospective result
  from either fixed universe is sufficient for promotion without prospective
  evidence.

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

- five chronological stages: train, fit-validation for early stopping,
  calibration, policy-validation, and untouched test, with five-session
  embargoes at all four boundaries;
- isotonic probability calibration and score scaling are learned on the
  calibration stage, while the abstention threshold is chosen only on the
  later policy-validation stage;
- test arrays are not loaded and test predictions are not produced unless a
  policy-validation threshold first passes every frozen gate;
- selection may honestly return zero names at a timestamp; it never forces a
  top-ranked name;
- report gross and 0.25%-cost-adjusted mean, median, win rate, calibration,
  fifth percentile, worst observation, concentration, and time-of-day/regime
  stability;
- report non-retuned 0.05%/0.10%/0.25% cost sensitivity and a market-date
  clustered 95% confidence interval; policy passage requires its lower bound
  to remain above zero across at least 20 market dates;
- compare against unconditional, QQQ-relative, momentum, and mean-reversion
  controls;
- preserve overlapping observations for realistic query behavior and a
  separate non-overlapping cohort analysis.

No historical result authorizes paper or live trading. A future live research
scorer also requires a source-compatibility audit between the Alpha Vantage
training archive and its chosen current one-minute feed.

## Immutable schema-v2 evidence from 2026-08-04

A deliberately non-promotable snapshot proved the compiler/trainer path while
the production archive continued collecting. It used 872 symbol-month shards,
5,249,807 labeled rows, and 211 market dates from January through October 2020.
The chronological split contained 126 training dates, 37 validation dates, two
five-session embargoes, and 38 still-sealed test dates.

The initial technical/market-context LightGBM policy failed validation. Its
least-negative basket selected 683 observations, averaged -0.2220% net after
the frozen 0.25% cost, had a -0.2433% median, a 37.34% win rate, and -27.16%
capital-scaled drawdown. No threshold passed, so the trainer did not open the
test partition. The report is permanently labeled
`PARTIAL_PIPELINE_PILOT_ONLY`; it must never be promoted, frozen, compared as a
final model, or connected to trading.

This pilot exposed and fixed a pandas timestamp-resolution incompatibility
before test evaluation. A regression test now proves exact nanosecond
round-tripping. The legitimate experiment remains the complete independently
audited 2020-01 through 2026-07 archive.

The first complete schema-v2 Nasdaq run was also a clean `RESEARCH_HOLD`. Its
least-negative validation basket had 6,030 signals, -0.2238% mean net,
-0.2188% median net, 38.84% wins, and -93.63% capital-scaled drawdown. No
validation policy passed and its test stayed sealed. It remains immutable
evidence that the original forced-ranking, close-to-future-close formulation
did not show an edge.

Schema v3 is a corrected successor, not a rewrite of either schema-v2 result.
It adds executable-time entry labeling, effective exit timestamps, strict gap
handling, exact live/compiler feature parity, explicit abstention, independent
fit/calibration/policy stages, a genuinely unloaded sealed test, capacity-
matched controls, calibration/uncertainty diagnostics, immutable universe
hashes, pre-training shard/hash/orphan validation, and independently stored
5/10/20/30/60/90-minute artifacts.
