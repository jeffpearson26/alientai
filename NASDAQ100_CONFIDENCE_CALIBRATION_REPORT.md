# Nasdaq-100 Confidence Calibration

Date: 2026-07-28

Status: `RESEARCH_CALIBRATED_PENDING_PROSPECTIVE`

The QQQ-relative model's raw LightGBM score is not a percentage confidence.
This step creates and clearly separates:

1. `confidence_rank_1_to_100`: the empirical percentile of a score within the
   validation distribution; and
2. `calibrated_exceptional_move_probability`: a validation-fitted isotonic
   estimate that the gross five-day return reaches at least 10%.

## Selected model cutoff

- raw score cutoff: `0.2246736047938044`
- relative confidence rank: 99/100
- calibrated probability of a gross five-day move of at least 10%: 24.7024%

Thus, 99 means the score is near the top of the historical validation ranking.
It does **not** mean a 99% probability of success.

## Reliability

On the reused later historical period:

- base rate: 9.3632%
- raw-score Brier error: 0.080593
- calibrated Brier error: 0.078954
- base-rate-only Brier error: 0.084865
- ten-bin expected calibration error: 0.029060

The calibrated estimate improves on both the raw score and the constant
base-rate forecast in this reused historical period. The validation in-sample
calibration error is not treated as independent evidence.

## Decision

Preserve the calibration artifact and reusable dependency-free calibration
code. Continue displaying relative rank only with the explicit “not
probability” definition. Do not expose the calibrated probability as trusted
production confidence or use it for execution until enough frozen prospective
outcomes establish reliability.
