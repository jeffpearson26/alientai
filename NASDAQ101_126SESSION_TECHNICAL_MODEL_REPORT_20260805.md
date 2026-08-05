# Nasdaq-101 Six-Month Technical Long-Selection Model

## Research objective

Design a research-only model that ranks long candidates from the fixed June
2026 Nasdaq-100 membership list (101 securities) for an approximately
six-month, 126-market-session holding horizon.

QQQ and SPY are market-context inputs only. They are not eligible selections.
The model may select zero through five candidates on any decision date and
therefore has an explicit abstention path.

## Frozen outcome contract

- Decision: after a completed regular-session daily close.
- Entry: the next session's split/dividend-adjusted open.
- Exit: the 126th subsequent split/dividend-adjusted close.
- Round-trip cost: 0.25%.
- Direction: long only.
- Data source: Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`, full history.
- Candidate universe: `nasdaq100_2026-06_symbols.txt`.
- Context-only instruments: QQQ and SPY.

## Point-in-time technical inputs

The panel contains only information known by the completed decision close:

- Trend and location: SMA/EMA distances, log-price slopes and slope fit,
  moving-average alignment, MACD, ADX and directional indicators.
- Momentum: 1/5/10/20/40/60/90/126/189/252-session returns and RSI over
  short, medium, and standard windows.
- Risk: realized and downside volatility, return skew, positive-session
  fraction, ATR, and 20/55/126/252-session maximum drawdown.
- Range structure: Bollinger location, stochastic, Williams %R, Donchian
  location, distances from rolling highs/lows, and breakout flags.
- Volume/flow: relative volume, normalized OBV changes, money-flow index,
  and Chaikin money flow.
- Market context: the same technical families for QQQ and SPY.
- Relative context: candidate excess returns, beta, and correlation against
  QQQ and SPY over 20/60/126/252 sessions.

No news, options, fundamentals, future prices, or post-decision information
enters this technical-only model.

## Leakage and selection controls

- All partitions use whole market dates, never random rows.
- Historical decision rows use a deterministic five-market-session stride.
  This removes much of the redundancy from outcomes that otherwise overlap
  for 125 sessions; it does not restrict future scoring to one weekday.
- Train, fit-validation, calibration, policy-validation, and sealed-test
  periods are chronological.
- Every adjacent partition is separated by a 126-session embargo.
- A fixed equal-weight ensemble combines a classifier and regressor trained
  on each security's 126-session excess return over QQQ. This makes the
  learning problem stock selection rather than broad-market prediction.
- Policy and test gates still judge the selected stocks' absolute net
  returns after cost; outperforming QQQ alone is not sufficient.
- The calibration period standardizes and calibrates scores.
- Policy thresholds are chosen only on policy validation.
- The test is opened once only if a policy passes every predeclared gate.
- Boundary ties at the fifth selection cause an abstention for that date.
- Overlapping observations are reported alongside 126 rotating,
  market-calendar-aligned non-overlap cohorts.
- Mean-return uncertainty uses a Newey-West lag of 125 sessions.

## Portfolio-risk measurement

Drawdown is calculated from a daily mark-to-market equity curve. Each
position uses a fixed `1 / (5 * 126)` capital slot, idle slots remain cash,
and the 0.25% cost is charged at exit. This avoids treating sparse exit-day
returns as though 100% of the account were continuously invested.

## Limitations

The fixed June 2026 membership list causes survivorship bias because former
Nasdaq-100 members and delisted securities are absent. Historical results
therefore cannot by themselves establish future profitability. This model
is not connected to paper or live execution.

## Verified result

The adjusted-daily archive passed its content audit:

- 100,839 labeled observations.
- 101 candidate securities.
- 1,296 sampled decision dates.
- May 1, 2000 through January 29, 2026.
- 405 raw point-in-time technical/context fields.
- 137 additional date-local cross-sectional ranks.
- Exact panel SHA-256 match and zero malformed rows.

An initial absolute-return formulation was rejected before test inspection
because its scores were dominated by the broad market and did not distinguish
stocks reliably. The final training formulation predicts excess return over
QQQ, while all selection gates still use absolute net stock returns.

The best balanced policy-validation basket was the 97.5th cross-sectional
score percentile (generally three selections per decision date):

- 390 signals across 130 dates and 26 symbols.
- Mean net 126-session return: +14.2901%.
- Median net 126-session return: +5.2865%.
- Net win rate: 54.87%.
- Cash-scaled daily mark-to-market maximum drawdown: -6.9388%.
- 83 of 126 rotating non-overlap folds had positive mean returns.
- Median non-overlap fold mean: +9.3642%.
- Newey-West 95% lower bound on mean return: -1.8340%.
- Largest single-symbol share: 14.36%.

This policy failed the frozen promotion gate because the HAC lower bound was
not positive and concentration exceeded 12%. The more extreme top-one policy
showed +36.06% mean, +21.94% median, and 76.15% wins, but had only 130 signals
and 32.31% concentration in one symbol, making it unsuitable for promotion.

**Final status: `RESEARCH_HOLD`.** The sealed test remains unloaded. These
validation figures are a lead for future research, not evidence of a
deployable or profitable model.
