# Nasdaq-100 Regime Specialization

Date: 2026-07-28

Status: `RESEARCH_FAIL`

Three point-in-time QQQ regimes were frozen before training:

- bullish: QQQ 20-session and 60-session returns both positive;
- bearish: QQQ 20-session and 60-session returns both nonpositive;
- mixed: the two returns disagree.

Each regime received a separate classifier. Validation alone selected the
regime, ranking fraction, and cutoff. Candidate selections required positive
mean and median net return, at least 50% wins, at least 15 signals, and no
excessive score-tie expansion.

## Validation selection

Validation selected the mixed-regime model at the top 0.50%:

- 16 signals
- +6.543888% mean net return
- +2.621953% median net return
- 62.50% post-cost wins
- locked cutoff `0.3688452908208664`

## Reused historical confirmation

Only seven positions survived the regime, cutoff, and five-slot capacity rules:

- -0.668923% mean net return
- +1.619029% median net return
- 57.142857% post-cost wins
- -1.039052% capital-scaled portfolio return
- -8.491980% capital-scaled maximum drawdown
- zero price/label alignment error

## Decision

The fixed regime-specialization design did not generalize and fragmented the
data into an inadequate final sample. Do not promote or retune these regime
models on the observed period. The simpler QQQ-relative model remains the best
challenger. QQQ regime may still be retained as a continuous model input, as it
already is, rather than as a hard training partition.
