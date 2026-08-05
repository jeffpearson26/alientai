# Nasdaq-101 + QQQ/SPY Three-Month Clone

Status: **RESEARCH HOLD — FINAL TEST SEALED AND UNLOADED**

This is a separate research-only clone. It does not change the frozen
five-session QQQ model, `engine.py`, paper trading, or live trading.

## Exact contract

- Universe: the current 101-stock Nasdaq research universe plus QQQ and SPY.
- Total selectable instruments: 103.
- Decision: after a completed regular-session close.
- Entry: the next regular-session adjusted open.
- Exit: the 60th subsequent regular-session adjusted close.
- Cost: 0.25% round trip.
- Capacity: at most five new selections per decision date.
- Drawdown sizing: 300 possible overlapping slots
  (five selections per day times 60 sessions).

QQQ and SPY are both market-regime inputs and eligible scored instruments.
Every instrument has 5-, 20-, and 60-session returns relative to both
benchmarks.

## Data and panel audit

Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` full histories were collected for
all 103 instruments:

- completed: 103;
- failed: 0;
- source files stored on the external SSD;
- adjusted OHLC and volume were calculated before any feature or label.

The final point-in-time panel contains:

- 155,304 rows;
- all 103 instruments;
- 1,595 decision dates;
- first decision date: 2020-01-02;
- last fully labeled decision date: 2026-05-07;
- 1,595 QQQ rows and 1,595 SPY rows;
- zero entry/exit/cost-contract errors.

Panel:
`D:\AlientAI\Data\AlphaVantage_2026\nasdaq101_qqq_spy_60session_panel_20260805\panel.jsonl`

## News and unusual-call signals

The existing exact-key Nasdaq overlay was attached to 2,612 panel rows. It
contains target-specific news, historical call-volume features, and option
positioning. It covers only 48 sampled 2026 dates and 80 symbols.

Those fields are retained in the panel, but they are not included in the
long-history model fit. Forty-eight sampled dates cannot support independent
fit, early-stopping, calibration, policy-validation, and final-test periods
when each outcome requires 60 later sessions. Missing news or call history is
never interpreted as a zero signal.

This is the exact blocker to a trustworthy catalyst-aware three-month clone:
more naturally sampled, timestamped historical news and unusual-call coverage
is required.

## Methodology

- Whole-date chronological partitions.
- A 60-session embargo on both sides of every internal boundary.
- Separate model-fit, early-stopping, calibration, policy-validation, and
  final-test periods.
- Fixed equal-weight ensemble of a positive-return classifier and expected
  net-return regressor.
- Continuous rank kept separate from isotonic confidence.
- No forced selections.
- Fail-closed fifth-place tie guard.
- Newey-West uncertainty using 59 lags.
- Sixty rotating non-overlapping cohort diagnostics.
- Final test loaded only after every frozen validation gate passes.

## Results

### Full QQQ/SPY market-context clone

Both component models stopped after one tree and produced market-regime scores
that were tied across stocks. The tie guard rejected every nominal selection:

- 80th/90th/95th percentiles: all 17 active dates rejected for boundary ties;
- 97.5th percentile: all 11 active dates rejected;
- 99th percentile: all 7 active dates rejected.

This model had market-timing information but no defensible ticker-selection
ranking. It is rejected.

Artifact:
`D:\AlientAI\Models\nasdaq101_qqq_spy_60session_all_context_schema2_20260805`

### Stock-specific QQQ/SPY-relative ablation

Removing shared raw benchmark fields while retaining stock-minus-QQQ and
stock-minus-SPY features reduced, but did not eliminate, score degeneracy.
The broadest sufficiently populated policy was the 99th percentile:

- 309 signals across 99 dates;
- +22.0178% mean net return;
- +21.3910% median net return;
- 66.99% wins;
- 55 of 60 non-overlap cohorts had positive means;
- -7.8461% cash-scaled drawdown;
- Newey-West 95% lower bound: **-15.3141%**.

The large nominal return is a regime-sensitive validation result affected by
current-membership/survivorship bias and overlapping three-month outcomes.
There are fewer than two independent 60-session spans in that policy window.
Its overlap-aware confidence bound therefore crosses zero by a wide margin.

Artifact:
`D:\AlientAI\Models\nasdaq101_qqq_spy_60session_relative_schema2_20260805`

## Decision

- No policy passed the frozen gate.
- The 2025-12-12 through 2026-05-07 final test remains
  `SEALED_UNLOADED`.
- The relative model is a development lead, not a validated winning model.
- No paper or live execution is authorized.

The next useful evidence should come from a longer point-in-time universe
history and substantially more naturally sampled news/unusual-call history,
not from loosening the uncertainty gate or repeatedly tuning this validation
period.
