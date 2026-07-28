# Nasdaq-100 Ten-Session Technical Clone

Date: 2026-07-28

## Frozen design

- Same exact 80-security universe as the successful five-day clone.
- 50,255 complete point-in-time examples with zero missing labels or anchors.
- Decide after the current close, enter next-session open, exit tenth-session close.
- Target: gross ten-session return of at least 10%.
- Chronological 60%/20%/20% partitions with 20-calendar-day embargoes.
- Validation-only choice among predeclared top 0.25%, 0.50%, and 1.00% score fractions.
- Five concurrent equal target slots, unused capital held in cash, no borrowing.
- Daily mark-to-market equity curve and 0.25% round-trip cost.

## Model

- LightGBM best iteration: 88.
- Validation AUC: 0.731354.
- Validation selected the top 0.50% fraction.
- Locked raw score cutoff: `0.20992159279836498`.

## Validation

- 30 capacity-limited trades.
- +4.502850% mean net return.
- +4.574116% median net return.
- 66.666667% post-cost win rate.
- +28.882931% capital-scaled return.
- -4.886682% maximum drawdown.

## Untouched test

- 57 capacity-limited trades.
- +1.520393% mean net return.
- +1.173362% median net return.
- 56.140351% post-cost win rate.
- +15.396338% capital-scaled return.
- -23.090912% maximum drawdown.

## Conclusion

`RESEARCH_HOLD`.

The positive mean, median, win rate, and portfolio return replicated in the
untouched test, so this is a credible secondary research lead. However, the
test drawdown exceeded the current -20% risk boundary and performance decayed
substantially from validation. Do not add it to paper or live trading from
this already-observed test. The five-day Nasdaq clone remains superior on
win rate and drawdown.
