# Nasdaq-100 Expected-Return Second Stage

Date: 2026-07-28

Status: `RESEARCH_HOLD`

The complete 101-security QQQ-relative panel was used to train two independent
LightGBM components:

1. a classifier for a gross five-day return of at least 10%; and
2. an L1 regressor for the continuous five-day return.

Validation compared three predeclared rankers: classifier probability,
predicted return, and their positive-return joint score. Candidate fractions
were 0.25%, 0.50%, and 1.00%. A ranker had to retain at least 20 validation
signals, positive mean and median net return, at least 50% wins, and no score-tie
expansion above 1.5 times the intended selection count.

## Validation

The return-only model stopped after one boosting iteration. Its top-fraction
cutoffs expanded to 303 tied rows (3.74x to 15.15x their intended counts), so it
was correctly rejected as a degenerate rare-signal ranker.

Validation selected the joint score at 0.50%:

- 41 signals
- +2.156291% mean net return
- +0.502437% median net return
- 51.219512% post-cost wins
- locked cutoff `0.08889663789309665`

## Reused historical confirmation

The later period retained 23 capacity-limited positions:

- +7.135010% mean net return
- +5.611869% median net return
- 73.913043% post-cost wins
- +36.199567% capital-scaled return
- -15.164772% capital-scaled maximum drawdown
- zero price/label alignment error

This period has already been inspected by earlier Nasdaq experiments and is not
a fresh untouched test.

## Decision

The second stage is profitable but does not improve the QQQ-relative challenger,
which had the same win rate, higher mean and median returns, higher portfolio
return, and materially lower drawdown. Preserve the tie-expansion gate as a
useful safety control. Do not replace the current challenger or connect this
two-stage model to execution.
