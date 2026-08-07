# Nasdaq Small-Cap Range/Volume Baseline Clone

Date frozen: 2026-08-07 Pacific time

Model ID: `nasdaq_smallcap_range_volume_baseline_clone_h05_v1_20260807`

Status: `BLOCKED_WITH_EXACT_DATA_EVIDENCE / PROSPECTIVE_NOT_STARTED`

This research-only setup replaces the requested all-market screen before that
setup produced any observation. The earlier all-market contract remains
preserved as `SUPERSEDED_BEFORE_OBSERVATION`; it has no selections, outcomes,
or inherited evidence.

The active setup is an isolated clone of the frozen Nasdaq-101 five-session
technical baseline. It preserves the exact LightGBM artifact, 22-feature
order, completed-close decision, five-subsequent-session close horizon, 10%
winner target, validation-locked cutoff `0.20886314398519493`, five-position
cap, and 0.25% research cost. Only the candidate universe changes. None of the
source model's performance evidence transfers to this clone.

## Nasdaq-only screen

The preserved August 7 Alpha Vantage listing has 6,247 active Nasdaq listings:
4,952 stocks and 1,295 ETFs. The base universe is exactly the 4,952 stocks.
ETFs and all non-Nasdaq exchanges are excluded.

Every completed-session screen requires source-pure Schwab numerical rows
available by the decision cutoff. A stock is eligible only when:

1. Market capitalization is positive and strictly below $2 billion.
2. Completed closing price is positive and strictly below $50.
3. Completed-session volume is at least 2.0 times its prior-20-session mean.
4. EMA bullish alignment is true and close is above EMA(9), EMA(21), and
   EMA(50).
5. ATR(14) divided by close is at least 3.0%.

No lower-price, liquidity, sector, or discretionary filter is added. Threshold
changes after the first observation require a new model ID.

## Current blocker

The membership source and frozen model artifacts pass. Complete source-pure
Schwab daily technical and same-cutoff market-cap snapshots for all 4,952
stocks do not exist. The Nasdaq-wide Alpha adjusted-daily archive cannot be
numerically spliced into this Schwab clone. The readiness audit therefore
fails closed, compiles no screened universe, and writes no picks. Paper/live
execution remains disabled.
