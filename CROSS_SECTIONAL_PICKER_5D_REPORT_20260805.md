# Cross-Sectional Five-Session Picker V1 — Verified Result

Date: 2026-08-05
Status: `RESEARCH_HOLD`
Execution: disabled

## What was built

Jeff supplied a complete cross-sectional Nasdaq-100 plus AI/semiconductor
five-session specification. A new isolated implementation now provides:

- adjusted-daily OHLCV loading and audited panel reuse;
- short momentum, oscillators, volatility, volume, and trend features;
- same-date cross-sectional percentile ranks for every predictive input;
- LightGBM rank prediction and a transparent weighted-rank baseline;
- whole-date purged five-fold cross-validation with five-session embargo;
- a separate 252-session sealed test;
- rank IC, top/bottom baskets, hit rate, cost-adjusted returns, exact-path
  overlapping portfolio P/L, Sharpe, and capital-scaled drawdown;
- configurable liquidity, relative-volume, price, and ATR filters;
- label-free daily JSON/CSV ranking;
- a complete end-to-end command runner;
- explicit research-only and AVOID-only safety behavior.

The model uses 23 date-local ranked technical features. It never receives an
absolute technical value as a predictive feature.

## Data and split

- Historical panel: 162,609 audited rows across 1,650 decision dates.
- Development dates used in purged CV: 1,393.
- Purged folds: 5 contiguous whole-date folds.
- Post-fold embargo: 5 sessions.
- Label-overlap purge: exact stored five-session exit date.
- Pre-test embargo: 5 sessions.
- Sealed test: final 252 sessions, never loaded.
- Cost: 0.25% round trip.
- Policy: top 10%, maximum 10 names per day, equal weight.

## Out-of-fold LightGBM result

- Selections: 11,248 across 1,393 dates.
- Mean net return per selection: **+0.244242%**.
- Median net return: **+0.157053%**.
- Hit rate: **51.5025%**.
- Mean daily Spearman rank IC: **+0.000010**.
- Positive-IC date fraction: **48.7419%**.
- Bottom-control mean net return: **+0.334803%**.
- Top-minus-bottom mean: **-0.090561%**.
- Overlapping portfolio total return: **+80.8420%** across the long history.
- Annualized portfolio Sharpe: **0.5137**.
- Capital-scaled maximum drawdown: **-44.9781%**.

The positive average return is not evidence of selection skill because the
bottom-ranked control performed better and rank IC was effectively zero.
Results were also regime-unstable: two of five fold top baskets had negative
mean returns.

The promotion gate failed:

1. rank IC below +0.01;
2. negative top-minus-bottom spread;
3. drawdown below the fixed -20% boundary.

The final 252-session test therefore remains `UNOPENED`.

## Transparent baseline

- Mean net return: +0.221907%.
- Hit rate: 50.7692%.
- Mean rank IC: -0.006703.
- Top-minus-bottom mean: +0.090692%.
- Maximum drawdown: -37.1350%.

It also fails the rank-IC and drawdown requirements and is not promoted.

## Daily-path validation

The label-free scorer ran successfully against the current complete adjusted
archives. The latest common complete decision date was 2026-08-04, with 84
rows passing the stricter configured filters. It wrote an explicitly
`RESEARCH_PREVIEW_HOLD` JSON/CSV output. Preview names are diagnostics only and
must not be journaled as a validated prospective model or presented as trade
recommendations.

## Evidence

- Configuration: `cross_sectional_picker_5d_config.json`
- Methodology: `CROSS_SECTIONAL_PICKER_5D.md`
- Controlling training report:
  `D:\AlientAI\Models\nasdaq_ai_cross_sectional_picker_5d_purged_cv_v1_20260805\training_report.json`
- Daily preview:
  `D:\AlientAI\Rankings\nasdaq_ai_cross_sectional_picker_5d_purged_cv_v1_20260805\daily_ranking.json`
- Targeted verification: 21 tests passed.

## Decision

Preserve the implementation as a complete reusable research pipeline, but do
not open the sealed test, invert the model, tune the observed folds, create a
prospective journal, or connect it to an engine. A legitimate successor would
need a pre-registered independent feature change—preferably point-in-time
constituent membership and timestamped catalyst data—followed by a new sealed
chronology.
