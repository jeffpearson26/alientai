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

## Build checkpoint

The V2 contract is now frozen at
`AI_SEMICONDUCTOR_SETUP_BARRIER_H05_LGBM_V2_CONTRACT_20260825.json`, SHA-256
`50500e8096516431b32d88f2415a38746aeab0f4d58a6d916497bc78eb3390e1`.
Its independently named source and panel audits both pass. The new panel root
contains the expected 18,621 rows, 10 symbols, 49 features, exact chronological
partitions, and the same setup/outcome counts as V1. No provider was contacted,
no prospective evidence was read, and no model weights or selections were
inherited.

This heartbeat used the one permitted isolated compilation stage. V2 training
has not started. The next permitted stage is exactly one training run against
the V2 panel and V2 panel audit, only while schema-v3 and every other isolated
clone trainer are idle. Keep the sealed test unloaded unless every unchanged
policy-validation gate passes.

## Terminal training checkpoint

The one permitted V2 training run is complete. Sector-Rip Momentum passed every
policy-validation gate on 17 candidates with +0.6324% mean net return and a
1.7679 profit factor, so its sealed test was opened exactly once. The lead did
not reproduce: all four sealed candidates stopped first, for -1.75% mean net
return, 0% target-first rate, zero profit factor, and -9.4485% Brier skill.
Pullback and Breakout did not pass policy validation and their tests remained
unopened. V2 is terminal `SEALED_TEST_COMPLETE_RESEARCH_HOLD`; its independent
model audit passes. Never retune or reopen this identity.
