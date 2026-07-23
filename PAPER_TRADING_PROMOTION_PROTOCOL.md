# AlienTAI paper-trading promotion protocol

Status: **frozen research contract; not authorization to paper trade**.

## Candidate must be frozen first

Before a candidate can enter shadow measurement, record its artifact hash/path,
feature schema, universe, threshold, entry/exit assumptions, five-trading-day
horizon, round-trip cost, maximum concurrent positions, and rejection rules.
No threshold, feature, universe, or position-limit change may be made using
future shadow outcomes.

## Historical evidence gate

The candidate must pass the existing fail-closed rare-signal gate on an
untouched chronological evaluation using its frozen rule. Required metrics are:

- at least 30 signals;
- post-cost win rate at least 50%;
- positive mean and median net return;
- fifth-percentile net outcome no worse than -10%;
- worst trade no worse than -25%;
- capacity-aware cohort drawdown no worse than -20%; and
- no symbol above 20% of signals.

The evaluation must also report sector and regime concentration. Historical
evidence alone never authorizes paper orders.

## Prospective shadow gate

Record every eligible and rejected opportunity before its outcome is known.
Require at least 30 completed forward observations across at least 20 distinct
market dates and more than one market regime. Use the same entry, exit, cost,
capacity, and outcome method as the historical evaluation. Missing data,
partial daily universes, stale prices, or changed inputs must fail closed and
be reported rather than filled in.

## Paper-trading review

Only after both gates pass may Jeff explicitly request a separate paper-trading
review. That review must recheck settings, model isolation, portfolio limits,
emergency stops, cooldowns, data freshness, and an immediate rollback plan.
Nothing in this document enables paper or live trading.
