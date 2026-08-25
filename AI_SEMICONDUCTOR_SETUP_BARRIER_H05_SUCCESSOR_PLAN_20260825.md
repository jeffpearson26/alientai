# AI/Semiconductor H05 One-Concept Successor Plan

Predecessor: `ai_semiconductor_setup_barrier_h05_lgbm_v1_20260825`

Predecessor disposition: `RESEARCH_HOLD_POLICY_VALIDATION_FAILED`, with its
sealed test still `SEALED_UNLOADED`.

## Proposed V2 change

Change exactly one concept: replace V1's fixed 60% probability floor with a
positive expected-value gate calculated from the independently calibrated
target-first probability, the fixed +3% target, the fixed -1.5% stop/timeout
distribution observed only in the calibration partition, and the unchanged
0.25% cost.

Everything else remains unchanged:

- same ten-name fixed universe and survivorship disclosure;
- same Alpha Vantage source purity and disclosed VIXY direction proxy;
- same next-open entry, five-session path, +3% target, -1.5% stop, conservative
  same-day stop-first rule, and 0.25% cost;
- same 49 features and three setup detectors;
- same LightGBM hyperparameters and no parameter search;
- same train, fit-validation, calibration, policy-validation, embargo, and
  sealed-test boundaries;
- same maximum one candidate per engine/date, no forced selection, and
  independent engine gates;
- no inherited selections, outcomes, calibration, model weights, or evidence.

The calibrated probability action bands remain descriptive. V2 may create a
research candidate only when expected value after costs is strictly positive.
An uncertainty-aware lower-bound rule should be a later V3 concept, not added
to V2 at the same time.

Do not build V2 concurrently with schema-v3 training or another isolated clone
stage. Freeze its new contract and roots before compilation, and keep its
newest test sealed unless every unchanged policy gate passes.
