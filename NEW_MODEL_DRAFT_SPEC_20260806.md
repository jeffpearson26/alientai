# AlienTAI New Model Draft Specification

Status: historical research contract frozen on 2026-08-06; implementation and
historical screening are in progress. It is not execution-authorized.

Jeff directed Codex to build and test the model on available historical data
after supplying Details 1-5 and the attached Nasdaq/AI-semiconductor roadmap.
The reproducibility choices below are therefore frozen before any model result
is observed.

## Detail 1 - Technical feature families

### Momentum

- 5-day return
- 10-day return
- ROC(10)

### Oscillators

- RSI(14)
- Stochastic %K
- CCI(20)

### Volume

- Relative volume

### Volatility and price position

- Bollinger %B
- ATR percentage

### Trend context

- Distance to the 10-day EMA
- MACD histogram

## Frozen technical definitions

- The eleven requested daily technical values use completed daily OHLCV through
  the decision session and a minimum 60-session history.
- Every security-specific input is converted to a same-decision-date
  cross-sectional percentile rank. QQQ/SPY regime values remain raw because
  they are constant across the cross-section.
- ROC(10) and 10-session return are intentionally retained as requested, but
  their algebraic redundancy is disclosed.
- Missing alternative-data values remain missing and receive explicit
  availability fields; they are never replaced with zero activity or no news.

## Detail 2 - Model family, ranking, and universe variants

Build two separately trained and stored models with identical feature
definitions and evaluation rules except for their candidate universes:

1. Nasdaq-100 candidate universe, with QQQ and SPY included only as reference
   and market-context series.
2. S&P 500 candidate universe, with QQQ and SPY included only as reference and
   market-context series.

Use cross-sectional quantile-ranking logic. On each decision date, derive ranks
or quantile positions from the eligible candidate universe without allowing
future dates into the transformation. QQQ and SPY must not be eligible picks
unless Jeff later changes that rule explicitly.

Use LightGBM and XGBoost as the requested candidate model families. Their exact
role remains to be frozen: they may be evaluated as two independently trained
challengers under identical splits, or combined only through a separately
specified out-of-fold ensemble. Do not select between them using sealed-test
results.

### Frozen universe definitions

- Nasdaq model: the exact 101 securities in
  `nasdaq100_2026-06_symbols.txt`.
- S&P model: the exact 483 locally data-ready securities in
  `data_v2/rcef_research/lightgbm_shadow_symbols_2026-07-21.txt`. This is the
  auditable subset of the 496-symbol contemporary reference list; unavailable
  symbols are not silently fabricated.
- QQQ and SPY are context only and can never be selected.
- A row requires at least $20 million of trailing 20-session average dollar
  volume.
- Both universes are fixed contemporary lists. Historical tests therefore
  retain survivorship and selection bias and cannot authorize promotion.

## Detail 3 - Options, news, and prior after-hours context

Add these point-in-time feature families to both universe variants:

### Recent call-option purchases

- Use recent call-side activity only; do not substitute put volume, put/call
  ratios, or presumed sell volume for call purchases.
- Features may include call volume, call open interest, volume/open-interest
  ratios, near-money call activity, and unusual call volume relative to the
  same symbol's strictly earlier history.
- The final contract must define the exact recent window, liquidity filters,
  moneyness/expiry scope, trade-direction inference, and minimum historical
  baseline.
- Empty or unavailable option chains are missing data, never zero activity.
- Only chains and trades observable before the decision cutoff may be used.

### Recent significant news headlines

- Use ticker-specific, materially relevant headlines with publication or
  availability timestamps no later than the decision cutoff.
- Candidate features may include significance, relevance, direction/sentiment,
  recency, novelty, source quality, and catalyst category.
- Deduplicate syndicated or substantially identical headlines.
- Do not treat the absence of a successfully collected headline as confirmed
  absence of news unless coverage is complete and audited.

### Yesterday's after-market data

- Use the immediately preceding completed session's extended-hours data after
  the 4:00 p.m. Eastern regular close through 8:00 p.m. Eastern.
- Candidate features may include after-hours return, range, relative volume,
  directional pressure, closing position, and distance from the regular close.
- Do not include the current decision day's premarket data under this feature
  family.
- Require exact interval coverage and source timestamps; incomplete or stale
  after-hours panels must fail closed.

### Required isolated ablations

The eventual validation plan must measure the incremental contribution of the
technical-only baseline, then options, news, and prior after-hours features
under the same dates, universe, labels, costs, and selection policy. No feature
family may be credited using a different or easier sample.

The historical feature sets are:

1. `daily_only`
2. `daily_plus_5minute` (regular session plus prior after-hours)
3. `daily_5minute_options`
4. `daily_5minute_options_news`

Comparisons are performed only on identical rows and dates. A feature-set
variant is blocked rather than scored when its audited common history is too
short for the relevant horizon.

## Detail 4 - Prediction horizons

Test both universe models at two separate horizons:

- 5 trading sessions.
- 20 trading sessions.

This creates four separately trained and stored universe/horizon variants:

1. Nasdaq-100, 5-session horizon.
2. Nasdaq-100, 20-session horizon.
3. S&P 500, 5-session horizon.
4. S&P 500, 20-session horizon.

Each horizon must have its own forward label, purge/embargo distance,
calibration, selection policy, immutable artifacts, sealed test, and
append-only prospective journal. Do not train one shared target and relabel its
predictions for the other horizon. Do not choose a horizon using sealed-test or
prospective outcomes.

The decision occurs at 8:00 p.m. Eastern after the completed decision session.
Entry is the next complete regular-session open. Exit is the official close of
the fifth or twentieth subsequent complete regular session. Every result
deducts a frozen 0.25% round-trip cost.

## Detail 5 - Multi-resolution candle inputs

Train every universe/horizon variant using both:

- Five-minute OHLCV candles.
- One-day OHLCV candles.

Both resolutions are required inputs to each model; they are not permission to
change the four specified candidate universes or horizons. Five-minute data
must be transformed only from bars fully completed by the decision cutoff and
then aligned to the corresponding decision row. Daily data must contain only
fully completed regular sessions available by that cutoff.

The implementation must:

- Preserve source, timestamp convention, session, adjustment, and split
  handling for both resolutions.
- Aggregate or encode five-minute behavior into reproducible point-in-time
  features suitable for LightGBM/XGBoost without allowing later intraday bars
  into an earlier decision.
- Keep prior-session after-hours bars separate from regular-session bars.
- Reject gaps, duplicate bars, mixed interval conventions, stale sessions, and
  source-mismatched joins.
- Define how daily adjusted prices and intraday unadjusted prices are normalized
  across splits and corporate actions.
- Use whole decision dates for splitting so rows from one date cannot appear
  in both training and validation/test partitions.

Run a same-sample daily-only baseline against the full daily-plus-five-minute
model for every universe/horizon pair. Five-minute inputs remain part of the
requested full model, but their incremental value must be reported honestly.

Five-minute features summarize the completed decision day's regular session
and the completed 4:00-8:00 p.m. Eastern after-hours session. The Nasdaq
archive's one-minute bars are deterministically aggregated to five-minute
OHLCV before features are calculated. No current-day premarket or future bar is
used. Alpha Vantage omits intervals in which no trade was reported. Bounded
no-trade intervals are therefore reconstructed with the last already-known
price and zero volume, never with a later price. Regular-session endpoints and
at least one actual after-hours print remain mandatory, and observed-bar
fractions enter the model so sparse extended trading is not concealed.

## Frozen modeling and validation contract

- LightGBM and XGBoost are independent challengers with fixed regularized
  configurations. They are not blended unless a later, predeclared
  out-of-fold ensemble is built.
- The target is the within-date percentile rank of the horizon's net forward
  return. Report raw net-return performance as well as daily Spearman rank IC.
- All splits use whole decision dates. Development folds are contiguous and
  purge every training label interval that overlaps a validation interval,
  followed by a horizon-length embargo.
- The latest dates form an independently sealed historical test. It may be
  opened once only if a challenger first passes the frozen out-of-fold
  validation gate; otherwise it remains `SEALED_UNLOADED`.
- A five-session screen requires at least 60 common decision dates. A
  twenty-session screen requires at least 120 common dates (six non-overlapping
  horizon blocks) so purging, a full horizon embargo, and a sealed test do not
  reduce a middle fold to a handful of training dates.
- The gate requires adequate date/trade counts, positive mean and median net
  return, at least 50% wins, positive mean rank IC and top-minus-bottom spread,
  and a positive lower date-clustered 95% confidence bound.
- Selection is the highest validation-chosen score quantile, capped at 15
  equal-weight names per decision date. Research output is always `AVOID`;
  there is no broker or order path.

## Historical source contract

- Nasdaq daily: source-pure Alpha Vantage full adjusted daily archive.
- S&P candidate daily: source-pure local Schwab maximum-history archive with
  its audited one-calendar-day stored-key-to-session mapping. The local Schwab
  SPY reference file has only 26 rows, so the already-audited full Alpha
  Vantage QQQ/SPY series supplies context only; it never supplies an S&P
  candidate price or label.
- Intraday: Alpha Vantage archives only; Nasdaq one-minute source data are
  aggregated to five-minute bars and S&P source data are native five-minute.
- Calls: Alpha Vantage historical option-chain aggregates. “Call purchases” is
  represented only as an unusual call-side activity proxy because aggregate
  volume does not prove buyer initiation.
- News: Alpha Vantage ticker-news responses filtered to articles published no
  later than each request's `as_of_utc`.
- Each family keeps its provider identity. No missing observation is replaced
  from another provider after an outcome is known.

## Safety

Research only. This draft does not authorize paper trading, live trading,
orders, changes to existing frozen models, or use of future information.
