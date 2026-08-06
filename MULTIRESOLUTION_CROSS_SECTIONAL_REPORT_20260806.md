# Multi-resolution cross-sectional ranker — historical screen

Date: 2026-08-06
Status: research only; no paper/live execution

## Outcome

The requested system is implemented and the locally testable variants were
screened. Neither five-session universe passed the frozen validation gate. Both
sealed historical tests remain `SEALED_UNLOADED`. The two twenty-session
variants were not fit because their common histories are shorter than the
predeclared 120-date minimum needed for defensible purge/embargo geometry.

This is useful negative evidence, not a failed pipeline and not evidence that
the idea can never work. The current common sample is entirely within 2026 and
is too short and regime-concentrated for a strong conclusion.

## Frozen design

- Candidate universes:
  - Nasdaq: exact 101 names in `nasdaq100_2026-06_symbols.txt`.
  - S&P: exact 483-name locally data-ready reference list. BF.B and BRK.B have
    no usable intraday archive rows; 481 symbols appear in the compiled panel.
- QQQ/SPY are context only and never candidates.
- Decision: 8:00 p.m. Eastern after the completed decision session.
- Entry: next complete regular-session open.
- Exit: fifth or twentieth subsequent complete regular-session close.
- Cost: 0.25% round trip.
- Target: within-date rank of the horizon's post-cost return.
- Algorithms: separately evaluated native LightGBM and XGBoost.
- Validation: whole-date contiguous folds, exact label-overlap purge,
  horizon-length embargo, date-clustered confidence interval, and a sealed
  latest period.

## Inputs

The eleven requested daily features are 5- and 10-session returns, ROC(10),
RSI(14), stochastic %K, CCI(20), relative volume, Bollinger %B, ATR%,
distance to EMA(10), and MACD histogram. Stock-specific features become
same-date cross-sectional percentile ranks.

Five-minute summaries cover the completed regular session and 4:00-8:00 p.m.
Eastern after-hours session. The model also receives QQQ/SPY regime context,
relative strength, recent call-side activity, strictly lagged unusual-call
baselines, and—only when adequately covered—timestamped headline features.

Alpha Vantage omits five-minute intervals with no reported trade. The compiler
reconstructs only bounded no-trade intervals using the last already-known
price and zero volume. It never fills from a future print. Regular-session
endpoints and at least one actual after-hours print remain mandatory, and
observed-bar fractions are features.

“Call purchases” is necessarily an aggregate call-side activity proxy. The
available chain aggregates cannot prove that volume was buyer-initiated.

## Panel audits

| Panel | Rows | Dates | Symbols | Per-date coverage | Audit |
|---|---:|---:|---:|---:|---|
| Nasdaq-100 | 7,272 | 72 | 101 | exactly 101 every date | PASS |
| S&P data-ready | 43,869 | 92 | 481 of 483 | 467 minimum; 477 median | PASS |

Nasdaq panel SHA-256:
`85a7daac0d55f36d75646bc9a71e4f8cfbc16f719559d3800a8b0e4ab5727a3e`

S&P panel SHA-256:
`2d449636444d13148a8f722a91afcd62b4171ff51ea3752117babde7ef0ebcae`

## Five-session validation results

The table shows the validation-selected top-score policy for the most relevant
tested variant, daily + five-minute + call features. These are out-of-fold
development results after the 0.25% cost; they are not sealed-test results.

| Universe / algorithm | Signals / dates | Mean | Median | Win rate | Mean rank IC | Top-minus-bottom | Lower 95% date-clustered bound | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nasdaq / LightGBM | 336 / 56 | +1.4217% | +0.1886% | 52.08% | -0.04984 | +0.3361% | -0.3216% | HOLD |
| Nasdaq / XGBoost | 336 / 56 | +1.1248% | -0.1075% | 48.51% | -0.04401 | +0.4427% | -0.6188% | HOLD |
| S&P / LightGBM | 1,095 / 73 | +0.0834% | -0.3658% | 46.30% | -0.04994 | -0.7812% | -0.5668% | HOLD |
| S&P / XGBoost | 1,095 / 73 | -0.2130% | -0.4953% | 44.84% | -0.04783 | -1.0182% | -0.8826% | HOLD |

The positive Nasdaq averages were driven by a minority of large winners. The
negative rank IC and negative lower confidence bound mean the model did not
reliably order the broader cross-section. Opening its test would invite
selection bias.

Daily-only and daily-plus-five-minute ablations were also run on the identical
rows and dates. None passed. On S&P, adding five-minute and call features made
the rank statistics worse. On Nasdaq, the additions increased average selected
return but did not repair negative rank IC or statistical uncertainty.

## Exact blockers

- Nasdaq timestamped news meets the 75% coverage threshold on only 36 dates;
  60 are required. The full news variant was not scored.
- S&P timestamped news meets the 90% threshold on only 30 dates; 60 are
  required. The full news variant was not scored.
- Nasdaq has 72 common dates versus 120 required for the twenty-session model.
- S&P has 92 common dates versus 120 required for the twenty-session model.
- The lists are fixed contemporary universes, so all historical results retain
  survivorship/selection bias.

## Next valid work

Continue collecting the same point-in-time daily, five-minute, after-hours,
option, and news families without changing definitions. Re-run the
twenty-session screen only after each panel reaches 120 common dates. Re-run a
news ablation only after at least 60 adequately covered dates exist. Any later
attempt must use a new model root and must not tune against the unopened tests
preserved here.

## Artifacts

- Contract: `NEW_MODEL_DRAFT_SPEC_20260806.md`
- Compiler: `build_multiresolution_cross_sectional_panel.py`
- Independent audit: `audit_multiresolution_cross_sectional_panel.py`
- Trainer: `train_multiresolution_cross_sectional.py`
- Shared feature/validation module:
  `alientai_v2/research/multiresolution_cross_sectional.py`
- Tests: `test_multiresolution_cross_sectional.py`
- Panels:
  `D:\AlientAI\Data\Compiled\multiresolution_cross_sectional_20260806`
- Reports:
  `D:\AlientAI\Models\multiresolution_*_20260806`

Controlling training-report SHA-256 values:

- Nasdaq 5-session:
  `8d3fbb52f5f190f035a58c4a0f0b4f6c4239eb08789a6b1d21caf9f35b19d973`
- Nasdaq 20-session readiness:
  `0f87cf7901caa9e8a5088dfd959173c79390a763d8945f9a8162aac1e4ef84e6`
- S&P 5-session:
  `5c1fa5ebd0e9db5055a0ca90e99fbf7ca0c9fd8a20379818bd957e775b2a5d90`
- S&P 20-session readiness:
  `8fc2d83e471b3a35e10ec2fac9208901c9c6b0c44278942386e5f87b52dbcb0f`
