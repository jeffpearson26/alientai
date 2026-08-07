# Barrier Probability Model Result

Model:
`barrier_probability_48_h10_alpha_vantage_v1_20260807`

Status: **FROZEN PENDING PROSPECTIVE REVIEW**

Safety: research only; execution is disabled; every score is
`execution_decision: AVOID`.

## What was built

The model estimates a conservative and optimistic probability bound for
reaching +1.5% before -0.5% from the next regular-session adjusted open within
ten sessions. It uses the 19 supplied daily technical state features, with
corrected standard CCI and price-normalized MACD.

The exact source-pure Alpha Vantage universe contains 48 of the supplied 50
liquid names. MS and NOW were excluded before any result was observed because
their only local files were unadjusted compact rows. Mixing those rows into the
adjusted panel was rejected. They require a separately frozen successor after
full adjusted histories are available.

Daily bars cannot order a session in which both barriers trade. Instead of
dropping those rows or inventing an order, the system learns:

- conservative lower probability: ambiguous touch is a failure;
- optimistic upper probability: ambiguous touch is a success.

The midpoint is diagnostic only.

## Data and integrity

Panel root:
`D:\AlientAI\Data\Compiled\barrier_probability_48_h10_alpha_vantage_v1_20260807`

Model root:
`D:\AlientAI\Models\barrier_probability_48_h10_alpha_vantage_v1_20260807`

- 4,172 decision dates
- 188,667 stage-assigned rows
- 48 source files, all individually hashed
- 188,667 labels independently reconstructed from source OHLC
- 753 sampled feature rows independently recomputed
- zero content-audit errors
- one incomplete unresolved history excluded
- 24,243 same-session ambiguous paths (12.58% of all resolved/full-horizon
  candidates)

The model used separate train, fit-validation, calibration,
policy-validation, and sealed-test stages with ten-session two-sided
development embargoes and exact label-information boundary purging.

## Policy-validation result

The frozen gate passed without searching probability thresholds.

| Metric | Conservative lower bound | Optimistic upper bound |
|---|---:|---:|
| Rows / dates | 18,994 / 396 | 18,994 / 396 |
| AUC | 0.54155 | 0.60307 |
| Brier score | 0.18137 | 0.22888 |
| Brier skill vs frozen constant baseline | +0.6947% | +2.9894% |
| 10-bin calibration error | 0.01812 | 0.01859 |
| Top-decile success lift vs calibration base | +4.338 pp | +20.561 pp |

The conservative date-clustered Brier-improvement 95% interval was
`[+0.000515, +0.001981]`. Mean probability-interval width was `0.14677`;
pre-projection bound crossings occurred on `0.31%` of rows.

## One-time sealed test

Because every frozen development gate passed, the sealed test was opened
exactly once. It was not used for retuning.

| Metric | Conservative lower bound | Optimistic upper bound |
|---|---:|---:|
| Rows / dates | 29,516 / 615 | 29,516 / 615 |
| AUC | **0.54999** | **0.60775** |
| Brier score | 0.17193 | 0.22724 |
| Brier skill vs frozen constant baseline | **+0.6156%** | **+3.7183%** |
| 10-bin calibration error | **0.00828** | **0.01251** |
| Top-decile success lift vs calibration base | **+3.183 pp** | **+21.583 pp** |

The conservative clustered Brier-improvement 95% interval remained positive:
`[+0.000434, +0.001665]`. Mean interval width was `0.16325`.

An independent model audit reloaded only the saved LightGBM text models,
recomputed both policy-validation and sealed-test probabilities, and verified
all 29,516 saved sealed predictions with zero errors.

## Interpretation

This is promising evidence that the feature set adds a small amount of
calibration and discrimination to a difficult path-probability problem. It is
not evidence of trading profitability:

- no entry threshold or portfolio policy has been validated;
- the +1.5%/-0.5% asymmetry makes transaction costs and false positives
  especially important;
- the fixed current universe is survivor-selected;
- the broad daily probability interval reflects genuine unresolved intraday
  order.

Future work is limited to a frozen, append-only calibration journal on new
completed sessions. Every eligible date should score all 48 names before the
next open; earlier pending ten-session paths must never suppress a later
attempt. Exact outcomes may be appended as soon as a path resolves or after
the full ten-session timeout. The model, barriers, features, source, and
threshold-free evaluation may not be retuned from those outcomes.

The first eligible future decision session is August 7, 2026. At the time of
this report it is not yet complete, and the singular Alpha Vantage bulk
collector is already occupied by Jeff's full-Nasdaq archive. No date has been
backfilled and no duplicate collector has been launched.
