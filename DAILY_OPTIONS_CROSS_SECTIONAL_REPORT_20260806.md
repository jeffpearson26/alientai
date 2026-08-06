# Daily-only technical + call-option cross-sectional rankers

Date: 2026-08-06  
Status: research only; no paper/live execution

## Outcome

The isolated daily-candle variant is built, independently audited, and
historically screened. It never reads a one-minute or five-minute candle,
premarket data, after-hours data, news, headlines, or sentiment.

QQQ and SPY are included in both universe variants as reference/context
tickers only. They provide 5- and 20-session market returns, 20-session
realized-volatility context, and each candidate's 5-session relative strength.
Neither ETF may be selected.

Neither five-session universe passed the frozen validation gate. Both sealed
historical tests remain `SEALED_UNLOADED`. The twenty-session variants were not
fit because their common point-in-time call histories are shorter than the
predeclared 120-date minimum.

## Panels and independent audits

| Universe | Rows | Dates | Candidates per date | Excluded columns found | Audit |
|---|---:|---:|---:|---:|---|
| Nasdaq-100 | 7,272 | 72 | exactly 101 | 0 | PASS |
| S&P data-ready | 44,436 | 92 | exactly 483 | 0 | PASS |

Panel SHA-256 values:

- Nasdaq:
  `997b2cfb65a2fbe7690c3b5531b2e595d4198e3b1ccf12197172a901fa7da4aa`
- S&P:
  `ac477d9af011fb2a39075a7df1fdb41959bcd7ba2ad49d2a2adf721fdf34206a`

The daily-technical and daily-plus-options challengers use identical rows,
dates, labels, folds, costs, and selection rules. The only difference is
whether the point-in-time call-activity fields enter the model.

## Five-session development results

All results below are out-of-fold development results after the frozen 0.25%
round-trip cost. They are not sealed-test results.

| Universe / features / algorithm | Signals / dates | Mean | Median | Wins | Rank IC | Top-minus-bottom | Lower 95% clustered bound | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nasdaq / daily / LightGBM | 336 / 56 | +1.0930% | -0.0867% | 49.40% | -0.03887 | -0.0276% | -0.6175% | HOLD |
| Nasdaq / daily / XGBoost | 336 / 56 | +1.0363% | -0.1520% | 48.51% | -0.03183 | +0.5002% | -0.6811% | HOLD |
| Nasdaq / daily + calls / LightGBM | 336 / 56 | +1.7547% | +0.5134% | 52.98% | -0.04921 | +0.5886% | -0.0891% | HOLD |
| Nasdaq / daily + calls / XGBoost | 336 / 56 | +1.3426% | +0.1533% | 50.89% | -0.05386 | +0.0887% | -0.5346% | HOLD |
| S&P / daily / LightGBM | 1,095 / 73 | +0.3311% | -0.2500% | 48.13% | -0.03292 | +0.1734% | -0.4044% | HOLD |
| S&P / daily / XGBoost | 1,095 / 73 | +0.3371% | -0.2819% | 47.67% | -0.03956 | -0.0702% | -0.3545% | HOLD |
| S&P / daily + calls / LightGBM | 1,095 / 73 | +0.2788% | -0.4764% | 44.66% | -0.04843 | -0.1897% | -0.4410% | HOLD |
| S&P / daily + calls / XGBoost | 1,095 / 73 | +0.2080% | -0.3649% | 45.84% | -0.04207 | -0.4182% | -0.4683% | HOLD |

The Nasdaq call-enhanced LightGBM slice improved selected-basket mean, median,
win rate, and top-minus-bottom spread versus its daily-only baseline. It still
failed because the full-universe rank IC was negative and the lower
date-clustered confidence bound remained below zero. The positive average
cannot be treated as a stable edge.

On S&P, call features weakened the measured results. The simpler daily
technical baselines also failed.

## Twenty-session blockers

- Nasdaq: 72 common dates; 120 required.
- S&P: 92 common dates; 120 required.

No twenty-session fit or policy search was performed, and no sealed test was
created. This prevents purge/embargo geometry from being weakened merely to
obtain a result.

## Frozen design

- Candidate universes: exact 101-name Nasdaq list and exact 483-name S&P
  data-ready list.
- QQQ/SPY: context-only, never candidates.
- Daily features: requested momentum, oscillators, volume, volatility/position,
  trend, QQQ/SPY relative strength, and raw QQQ/SPY regime context.
- Optional calls: call volume, open interest, volume/open-interest ratio,
  strictly lagged unusual-volume baselines, near-money call IV, and explicit
  availability.
- Target: within-date percentile rank of the horizon's post-cost return.
- Decision: 8:00 p.m. Eastern after the completed daily session.
- Entry: next regular-session open.
- Exit: fifth or twentieth subsequent regular-session close.
- Validation: whole-date purged folds, horizon embargo, fixed policy
  thresholds, date-clustered confidence interval, and unopened latest-period
  test after a failed gate.

## Artifacts

- Contract: `DAILY_OPTIONS_CROSS_SECTIONAL_SPEC_20260806.md`
- Compiler: `build_daily_options_cross_sectional_panel.py`
- Independent audit: `audit_daily_options_cross_sectional_panel.py`
- Trainer: `train_daily_options_cross_sectional.py`
- Tests: `test_daily_options_cross_sectional.py`
- Panels:
  `D:\AlientAI\Data\Compiled\daily_options_cross_sectional_20260806`
- Reports: `D:\AlientAI\Models\daily_options_*_20260806`

Training-report SHA-256 values:

- Nasdaq 5-session:
  `9eea2e075014df25aed0ae328dc21c63e06475254e8f39534f67b20a58b472fa`
- Nasdaq 20-session readiness:
  `1da23c07666e641ebff14c03fa5bad2f285bd99191663602fe633adf92edf163`
- S&P 5-session:
  `741018a00a20e1c6d6d8941d6e1721b0461b3e2eb45414acc74fc516fb9eaa76`
- S&P 20-session readiness:
  `939a57ad31a9923c09b2766ff1de29a52ff1ea81401d02ecc0660262611fc341`

