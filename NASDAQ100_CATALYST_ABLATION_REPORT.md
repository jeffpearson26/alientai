# Nasdaq-100 Catalyst Ablation Round

Date: 2026-07-28

Status: `RESEARCH_HOLD`

This round asked whether currently available point-in-time catalyst data can
improve the complete Nasdaq QQQ-relative challenger under a fair chronological
comparison. No execution setting changed.

## Coverage audit

| Family | Exact overlap with 44,620 Nasdaq rows | Decision |
|---|---:|---|
| Historical options (matched archive) | 1,451 | Blocked: event-selected and too sparse across chronology |
| Historical options (natural archive) | 7,191 | Blocked: concentrated in 2026, with no training-period coverage |
| SEC Form 4 purchases | 24,836 | Eligible for a paired ablation |
| Historical news | Same event-selected scope as the matched archive | Blocked for a natural-universe ablation |
| Analyst rating changes | 42 previously verified premarket symbol-days | Blocked: incomplete/unlicensed event history |
| Earnings events | Event-only pilot/holdout data | Retain as context; not a complete daily training feature |
| Premarket | Existing matched overlap is 7.4973% | Blocked until a natural-universe point-in-time archive exists |

Using sparse 2026-only or event-selected data as though it covered the full
training chronology would confound catalyst value with time regime and sampling
selection. Those ablations were therefore not run.

## Paired SEC Form 4 ablation

The exact-key panel retained 24,836 rows. Every catalyst row had an `as_of_utc`
date no later than its market date. Both models used identical rows, labels,
chronological splits, QQQ-relative technical features, costs, and portfolio
rules.

Validation-selected results:

| Variant | Validation signals | Validation mean net | Validation median | Validation wins |
|---|---:|---:|---:|---:|
| QQQ-relative baseline | 44 | -0.363619% | -2.385195% | 43.18% |
| Plus insider purchases | 22 | -1.132327% | -3.867525% | 31.82% |

The insider model's observed test had eight retained positions, +12.722753%
mean net return and 87.5% wins. This is not promotable: the validation evidence
was negative and the test sample is far below the minimum needed to distinguish
signal from chance.

## Decision

Do not add insider-purchase features to the Nasdaq model in this formulation.
Do not infer negative value for all catalyst data; the other families lack a
fair daily point-in-time archive. The next model improvement should use the
complete technical/QQQ panel and add a validation-locked expected-net-return
second stage rather than fabricating coverage.
