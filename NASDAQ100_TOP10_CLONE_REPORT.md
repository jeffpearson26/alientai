# Nasdaq-100 Top-10 Weighted Five-Day Clone

Date: 2026-07-28

## Frozen universe

Official Nasdaq weights dated May 1, 2026 were used to freeze the ten largest
securities: NVDA, AAPL, MSFT, AMZN, GOOGL, GOOG, AVGO, TSLA, META, and WMT.
Alphabet appears twice because its Class A and Class C securities have separate
index weights.

All ten were present in the existing training archive:

- 5,175 total examples.
- Target: forward five-session return of at least 10%.
- Same point-in-time technical features as the successful 80-security clone.
- Chronological 60%/20%/20% partitions with 12-calendar-day embargoes.
- Validation-only selection among predeclared top 2%, 4%, and 8% fractions.
- 0.25% round-trip cost and five-position, daily mark-to-market portfolio.

## Model and selection

- LightGBM best iteration: 14.
- Validation AUC: 0.646553.
- Validation chose top 2%.
- Locked cutoff: `0.038962159893157364`.

Validation at the locked rule:

- 25 trades.
- +6.509795% mean net return.
- +7.265433% median net return.
- 72.00% post-cost win rate.

## Untouched test

- 17 candidates before capacity control; 16 simulated trades.
- +2.192283% mean net return.
- +1.855858% median net return.
- 56.25% post-cost win rate.
- +7.170045% capital-scaled return.
- -3.190090% maximum drawdown.
- Four peak concurrent positions.
- Zero price/label alignment error.

## Conclusion

`RESEARCH_HOLD_INSUFFICIENT_TEST_SAMPLE`.

The positive mean, median, win rate, portfolio return, and low drawdown
replicated directionally, but only 16 test trades survived the frozen cutoff
and capacity rule. This is insufficient for promotion. It also underperformed
the broader 80-security Nasdaq clone's 40 trades and 75% win rate. Keep the
top-10 result isolated and use it as evidence that concentrating the universe
did not improve the current model.
