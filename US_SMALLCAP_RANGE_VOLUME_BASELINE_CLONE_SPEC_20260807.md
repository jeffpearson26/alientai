# U.S. Small-Cap Range/Volume Baseline Clone

Date frozen: 2026-08-07 Pacific time

Model ID: `us_smallcap_range_volume_baseline_clone_h05_v1_20260807`

Status: `BLOCKED_WITH_EXACT_DATA_EVIDENCE / PROSPECTIVE_NOT_STARTED`

This is an isolated research-only clone of model 3, the frozen Nasdaq-101
five-session technical baseline. It does not alter that model or inherit any
of its historical or prospective evidence. Paper and live execution remain
disabled.

## What remains identical

- Frozen LightGBM artifact and exact 22-feature order.
- Completed-close decision and five-subsequent-session close horizon.
- Gross-return-at-least-10% training target embodied by the frozen artifact.
- Validation-locked score cutoff `0.20886314398519493`.
- Maximum five simultaneous selections.
- Fixed 0.25% round-trip research cost.
- Research-only abstention when no screened name clears the locked cutoff.

Changing the candidate distribution from Nasdaq-100 constituents to volatile
small-cap stocks is a material external-validity change. Therefore none of the
source model's returns, win rate, weights of evidence, or observations count
for this clone. Its evidence begins at zero.

## Entire-market universe screen

The starting membership is every active U.S. listing classified as `Stock` in
a preserved Alpha Vantage `LISTING_STATUS` snapshot. The August 7 reference
contains 14,277 active listings across Nasdaq, NYSE, AMEX, BATS, NYSE Arca,
and NYSE MKT; 8,570 are classified as stocks. ETFs are excluded because the
market-cap condition is a company-equity screen.

Each completed-session screen requires source-pure Schwab price, volume,
technical, and market-cap rows for all 8,570 stocks. A stock is eligible only
when all of these predeclared conditions hold:

1. Market capitalization is positive and strictly below $2 billion.
2. Completed closing price is positive and strictly below $50.
3. Completed-session volume is at least 2.0 times the mean volume of the prior
   20 completed sessions.
4. Uptrend is true: EMA bullish alignment plus close above EMA(9), EMA(21),
   and EMA(50).
5. "Has range" means ATR(14) divided by close is at least 3.0%.

No lower price, dollar-volume, sector, exchange, or discretionary quality
filter has been added. Changing a threshold or adding a filter requires a new
model ID; it may not be decided after prospective outcomes are visible.

## Timing and source integrity

All numerical screen inputs and model features remain Schwab-source-pure so
that the source is unchanged from the frozen baseline. The Alpha Vantage file
supplies membership only. Every row must include an availability timestamp no
later than the decision cutoff. Duplicate symbols, mixed providers, stale
decision dates, missing features, or a partial market-cap snapshot fail
closed. No Alpha/Schwab numerical rows may be spliced.

`build_us_smallcap_range_volume_clone_snapshot.py` verifies the frozen source
model/report hashes, applies the screen, scores the eligible universe, caps
the list at five, and writes a new immutable D-drive snapshot. It never writes
orders and declares `execution_decision: AVOID`.

## Exact current blocker

The complete membership file is present, but a full source-pure Schwab daily
history and same-cutoff market-cap snapshot for all 8,570 active stocks are
not. The existing fundamental snapshot has only 1,441 rows, 1,347 with basic
shares, is dated July 21, and does not contain the required market-cap field;
it is not eligible. The completed Alpha archive covers Nasdaq rather than the
entire market and cannot be numerically spliced into this Schwab clone.

The singular full-Nasdaq five-minute Alpha collector remains active. No
unrelated collector is launched beside it. The clone stays blocked, produces
no universe or picks, and will not be backfilled. Once exact full-market
Schwab inputs exist, run the readiness audit and create the first eligible
snapshot before its next-session observation window closes.
