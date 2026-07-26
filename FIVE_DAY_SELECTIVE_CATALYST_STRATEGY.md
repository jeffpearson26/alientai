# Five-Day Selective Catalyst Strategy

Status: research-only challenger specification. It does not replace or modify
`FROZEN_CONTEXTUAL_OPTIONS_STUDY.md`, authorize training from incomplete data,
or permit paper/live trading.

## Objective and timing

Predict the net stock return from the next regular-session open through the
fifth regular-session close. A row may use only information available before
its recorded decision cutoff. End-of-day and premarket decisions must remain
separate studies because their available information and entry prices differ.

The scorer must produce:

- calibrated probability that the net five-day return is positive;
- calibrated probability that the net return exceeds the frozen large-move
  target;
- expected net return after the frozen round-trip cost;
- a lower quantile of net return; and
- model disagreement.

## Feature-family order

1. Technical price/volume and market/sector context.
2. Point-in-time unusual public call activity.
3. Premarket, analyst, Form 4 purchase, earnings, and news features only through
   separately locked chronological ablations after their timing/coverage audits.

Missing feature families remain explicit missingness and may not be backfilled
with current or future observations.

## Model design

- LightGBM binary classifiers estimate positive-return and large-move
  probabilities.
- LightGBM regression and quantile objectives estimate the expected, lower, and
  upper return distribution.
- The existing Transformer is a challenger only. Its disagreement may cause
  abstention, but it receives no vote until it independently improves an
  untouched chronological evaluation.
- Calibration uses validation rows only. Final-test outcomes may never select a
  threshold, feature, universe, cost, or model.

## Split and cost contract

- Use whole chronological timestamps for train, validation, and final test.
- Preserve the existing conservative embargo and purge all overlapping
  five-session labels.
- Fit feature transforms, models, calibration, and thresholds on train and
  validation only.
- Subtract at least 0.25% round-trip cost and report a higher-cost stress case.
- Fingerprint every input, model, policy, and result artifact.

## Selective decision contract

`alientai_v2.research.selective_five_day_policy` accepts thresholds frozen from
validation and a complete same-day scored universe. A row survives only when:

- point-in-time data are complete;
- technical and options evidence agree;
- both calibrated probabilities clear their frozen thresholds;
- expected net return and lower return estimate clear their frozen thresholds;
  and
- model disagreement remains below its frozen maximum.

The policy deliberately has no quota: zero, one, or several independently
qualified rows may survive. Every surviving row remains `decision="AVOID"` and
is only a non-executing research candidate. An incomplete universe or missing
score fails closed.

## Evidence required before paper review

Use `PAPER_TRADING_PROMOTION_PROTOCOL.md`. Historical and prospective gates
must both pass without changing the frozen design. Prediction evidence and
portfolio-risk evidence are reported separately, but neither may be hidden.
Only a later explicit human review can authorize limited paper trading.
