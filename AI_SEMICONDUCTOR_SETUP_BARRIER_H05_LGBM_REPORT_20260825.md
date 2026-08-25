# AI/Semiconductor Setup-Specific H05 LightGBM — V1 Terminal Report

Model ID: `ai_semiconductor_setup_barrier_h05_lgbm_v1_20260825`

Status: `RESEARCH_HOLD_POLICY_VALIDATION_FAILED`

Authorization: `NONE_RESEARCH_ONLY`

## What was built

- Ten-name focused universe: NVDA, AMD, AVGO, MU, MRVL, CRDO, ALAB, ARM,
  SMCI, and SNDK.
- Three separately fit LightGBM classifiers:
  `PULLBACK_CONTINUATION_V1`, `BREAKOUT_ANTICIPATION_V1`, and
  `SECTOR_RIP_MOMENTUM_V1`.
- A shared deterministic path definition: decide after a completed close,
  enter at the next adjusted open, seek +3% before -1.5%, and otherwise exit
  at the fifth subsequent adjusted close.
- Conservative stop-first handling when both barriers occur in the same daily
  bar, plus 0.25% total spread/slippage/fee cost on every resolved path.
- Forty-nine completed-session features spanning trend, momentum change,
  volume, volatility, QQQ/SOXX/SPY context, relative-strength acceleration,
  and ten-name breadth.
- Isotonic probability calibration, chronological train/fit-validation/
  calibration/policy-validation partitions, expanding walk-forward
  diagnostics, and a newest sealed test.
- A deterministic research director that may compare only engines which first
  pass independently. It is not a learned combiner and it creates no orders.

The exact cash VIX series was absent from the frozen source-pure Alpha archive.
V1 therefore uses only VIXY adjusted-return changes as a disclosed volatility-
direction proxy. It never represents VIXY as the VIX level. An exact-VIX
version requires a new identity and inherits no V1 evidence.

## Data and audit result

The exact 14-series subset passed its source audit through 2026-08-21. The
compiled panel contains 18,621 rows, all ten candidates, 49 finite features,
and exact non-overlapping chronology controls. The independent panel audit
reconstructed every path and passed with zero errors.

| Frozen setup | All panel setup rows | Train | Fit validation | Calibration | Policy validation |
|---|---:|---:|---:|---:|---:|
| Pullback continuation | 1,433 | 881 | 160 | 161 | 162 |
| Breakout anticipation | 760 | 510 | 65 | 64 | 98 |
| Sector-rip momentum | 2,332 | 1,305 | 216 | 283 | 306 |

Across all candidate-days, the conservative path labels contain 6,063
target-first outcomes, 11,016 stop-first outcomes, 1,115 same-day dual hits
assigned stop-first, and 427 timeouts.

## Policy-validation result

| Engine | Calibrated base rate | Policy-period actual target-first rate | Brier skill | ECE | Frozen selections |
|---|---:|---:|---:|---:|---:|
| Pullback continuation | 33.54% | 37.65% | -2.86% | 0.0807 | 0 |
| Breakout anticipation | 31.25% | 36.73% | 0.00% | 0.0548 | 0 |
| Sector-rip momentum | 30.04% | 33.99% | +2.38% | 0.0338 | 0 |

The calibrated policy-period probabilities clustered near 31% to 34%. None
reached the preregistered 60% research-action floor, so no candidate was
forced. Pullback and breakout also failed the strictly-positive Brier-skill
gate. Sector-rip showed modest calibration skill but still produced no frozen
policy selection.

The expanding 2021, 2022, and 2023 raw-probability diagnostics did not beat
their corresponding unconditional Brier baselines for any engine. This warns
against treating the stable-looking calibrated probabilities as useful
discrimination.

## Sealed-test disposition

All three engines failed policy validation. The newest 150-decision-date,
1,500-row sealed partition remains `SEALED_UNLOADED`; it was not scored,
summarized, or used to redesign V1. The independent terminal model audit
reproduced every policy decision and passed with zero errors.

## Meaning

V1 successfully answers the engineering question and negatively answers its
preregistered model question. These exact setup rules and tree configuration
did not produce a sufficiently discriminating, calibrated 60%-probability
opportunity stream in later unseen policy data. That does not prove the setup
ideas are permanently useless, and it does not justify lowering thresholds
inside V1 after seeing the result.

The next permitted experiment is a separately frozen one-concept successor.
The preferred first change is to remove the arbitrary 60% probability floor
and gate solely on independently calibrated positive expected value, while
leaving the universe, label, costs, features, setup detectors, chronology, and
sealed-test discipline unchanged. That rule follows the original economic
objective more closely, but it must compile and train under a new identity and
inherit no V1 evidence.

This report is research evidence only. It is not proof of profitability and
does not authorize shadow, paper, or live trading.
