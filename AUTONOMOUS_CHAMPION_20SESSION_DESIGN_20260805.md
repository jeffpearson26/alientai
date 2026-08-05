# AlienTAI Autonomous Champion Candidate

Status: **FROZEN DESIGN — EVALUATED AND LOCKED**

This is the separately authorized experiment in which model design, universe,
horizon, feature selection, and abstention policy are chosen for methodological
strength rather than inherited from an older AlienTAI model.

It is research-only. It cannot modify `engine.py`, enable paper/live trading,
or create orders.

## Objective

Select zero through five liquid Nasdaq securities expected to produce positive
absolute returns and outperform QQQ over the next 20 regular-market sessions.

Twenty sessions were chosen because they:

- give technical, earnings-reaction, and institutional-flow information time
  to propagate;
- avoid the extreme noise and cost sensitivity found in five-to-90-minute
  models;
- mature quickly enough to accumulate prospective evidence;
- provide substantially more independent historical outcomes than a
  six-month target.

## Universe and tradability

- Candidates: the exact 101 securities in
  `nasdaq100_2026-06_symbols.txt`.
- Context-only benchmarks: QQQ and SPY.
- Decision-date adjusted price must be at least $5.
- Trailing 20-session average dollar volume must be at least $20 million.
- The filters are calculated point-in-time and never use present-day
  liquidity to admit an old observation.

The fixed June 2026 membership list creates survivorship bias. Historical
passage alone cannot authorize promotion; future-only evidence is mandatory.

## Outcome contract

- Decision: after a completed regular-session adjusted close.
- Entry: next regular session's adjusted open.
- Exit: 20th subsequent adjusted close.
- Cost: 0.25% round trip.
- Learning target: stock gross return minus matched QQQ gross return.
- Promotion metrics: the selected stock's absolute post-cost return.
- Direction: long only.

The QQQ-excess learning target forces the model to distinguish stocks rather
than merely predict whether the entire market will rise.

## Features

Only information available by the completed decision close is permitted:

- returns over 1/5/10/20/40/60/90/126/189/252 sessions;
- RSI, MACD, ADX/DI, ATR, Bollinger, stochastic, and Williams %R;
- SMA/EMA location, log-price slope, and trend-fit strength;
- realized/downside volatility, skew, positive-session fraction, and rolling
  maximum drawdown;
- Donchian position, breakout state, and distance from highs/lows;
- relative volume, dollar volume, OBV, money-flow index, and Chaikin flow;
- QQQ/SPY market regime and the same benchmark technical families;
- candidate beta, correlation, and excess return versus QQQ/SPY;
- date-local cross-sectional ranks for stock-specific features.

News, analyst actions, earnings metadata, and unusual-call buying are not
inserted into the long historical fit because the existing exact,
point-in-time coverage is too sparse and recent. They may later serve as a
separately frozen prospective overlay after adequate history exists; missing
signals will never be treated as zero.

## Validation contract

- Deterministic every-fifth-session historical sampling reduces redundant
  overlapping labels while preserving the ability to score any future date.
- Whole-date chronological train, fit-validation, calibration,
  policy-validation, and sealed-test stages.
- Twenty-session embargo at every boundary.
- Regularized LightGBM positive-excess classifier and excess-return regressor.
- Equal-weight standardized ensemble.
- Date-local cross-sectional selection thresholds: 90%, 95%, 97.5%, 99%.
- Zero through five picks; fifth-place boundary ties cause abstention.
- Newey-West uncertainty with 19 lags.
- Four observable market-calendar-aligned non-overlap cohorts. With a
  20-session outcome and deterministic five-session sampling, modulo-20
  decision positions can occupy exactly four offsets.
- Daily mark-to-market drawdown with fixed `1 / (5 * 20)` capital slots and
  idle cash unchanged.

Policy validation must have at least 250 signals, 100 decision dates, positive
mean and median absolute net returns, at least 52% wins, a positive clustered
95% lower confidence bound, drawdown no worse than -20%, no symbol above 12%
of selections, all four observable non-overlap cohorts, and at least three
positive-mean cohorts.

The sealed test is loaded once only if every gate passes. Failure leaves it
`SEALED_UNLOADED`; gates will not be loosened after seeing validation.

## Controls

The eventual report must compare the chosen policy against matched-capacity
QQQ and simple cross-sectional momentum/low-volatility controls. A complex
model that cannot beat a transparent control is not a champion.

The complex LightGBM candidate failed validation and its sealed test remained
unloaded. The predeclared transparent control passed every frozen validation
gate and its one-time sealed test without retuning. Its controlling results are
documented in `AUTONOMOUS_CHAMPION_20SESSION_REPORT_20260805.md`.
