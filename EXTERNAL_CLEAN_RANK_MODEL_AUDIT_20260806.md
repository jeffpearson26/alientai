# External clean-rank model audit

Date: 2026-08-06

Status: promising external research lead; not validated or execution-authorized

## Source

- Archive:
  `D:\Downloads\alientai_clean_rank_model.zip`
- Archive SHA-256:
  `0ef7c67df672d9badd57d0331c3d38211dd722e74e87155617ace9b3d64697d6`
- Isolated extraction:
  `D:\AlientAI\ExternalModels\alientai_clean_rank_model_20260806_0ef7c67d`

The ZIP path audit passed: 15 entries, no rooted paths, and no parent-directory
traversal. It contains three Python research scripts and saved CSV/Markdown
reports. It contains no model binary, raw-price archive, requirements file,
broker integration, or execution path.

## What was independently verified

The bundled `purged_cv_predictions.csv` contains:

- 220,753 unique date/ticker predictions
- 1,856 decision dates from 2019-02-20 through 2026-07-09
- 119 distinct S&P-style tickers
- no duplicate date/ticker keys
- cross-sections of 118 or 119 names

Recomputing directly from those predictions reproduced the bundled S&P
20-session claims:

- mean daily Spearman Rank IC: `+0.0485087`
- top-20% mean close-to-close return: `+2.6111%`
- bottom-20% mean close-to-close return: `+1.0662%`
- top-minus-bottom spread: `+1.5449%`
- stored versus recomputed prediction-rank maximum difference:
  approximately `1.1e-16`

The five reconstructed fold results also match the report:

| Fold | Dates | Rank IC | Top 20% | Spread |
|---:|---|---:|---:|---:|
| 1 | 2019-02-20 to 2020-08-10 | +0.03823 | +2.682% | +1.157% |
| 2 | 2020-08-11 to 2022-01-28 | +0.04879 | +3.163% | +1.889% |
| 3 | 2022-01-31 to 2023-07-24 | +0.04535 | +1.656% | +1.271% |
| 4 | 2023-07-25 to 2025-01-14 | +0.03882 | +2.329% | +0.890% |
| 5 | 2025-01-15 to 2026-07-09 | +0.07138 | +3.225% | +2.519% |

The latest fold is the most relevant because it has no later dates available
to its training side. Across its 20 possible non-overlapping decision-date
offsets:

- all 20 have positive mean Rank IC
- all 20 have positive mean top-minus-bottom spread
- offset mean Rank IC is `+0.07118` (range `+0.04372` to `+0.09915`)
- offset mean spread is `+2.5166%` (range `+1.5819%` to `+3.4452%`)

A deterministic 20-session moving-block bootstrap on the latest fold gives:

- Rank IC 95% interval: `+0.01854` to `+0.13925`
- top-20% return interval: `+1.1298%` to `+5.7627%`
- spread interval: `+0.8820%` to `+4.8195%`

Subtracting AlienTAI's 0.25% cost mechanically from the bundled latest-fold
top-basket mean leaves `+2.9754%`, but this is not an executable cost-adjusted
backtest because the entry itself is not executable.

## Material defects

1. The label is decision-close to the twentieth later close. A model that uses
   the completed decision close cannot enter at that same close. AlienTAI
   requires the next executable open or another timestamped entry.
2. No transaction cost, slippage, turnover, drawdown, or capital-scaled cohort
   accounting is included.
3. The purger approximates a 20-trading-day label as 22 calendar days. Exact
   trading-session audit found label overlap left in the training set:
   4 dates in fold 2, 6 in fold 3, 5 in fold 4, and 7 in fold 5.
4. The five folds are generic K-fold blocks. Early folds train on later market
   history; they are not prospective walk-forward evidence.
5. The claimed Nasdaq universe is a hand-selected 60-name list, not the exact
   Nasdaq-100. The S&P universe is a hand-selected 120-name list, not the S&P
   500. The saved predictions contain only 119 names.
6. The fixed current lists retain survivorship and selection bias.
7. The scripts silently omit failed downloads and do not freeze a source
   manifest, timestamp, source hash, or minimum exact-universe coverage.
8. Only SPY relative strength is present; the requested QQQ reference context
   is absent.
9. The pass gate is only mean Rank IC above 0.02. There is no confidence,
   tail-risk, return, win-rate, or sealed-test gate.
10. The bundle contains no sealed test. All included dates and results are
    already exposed and cannot now become a sealed period.
11. The bundled S&P prediction file permits its S&P result to be verified.
    Equivalent Nasdaq prediction files are absent, so the Nasdaq `+0.0489`
    and five-session `+0.0136` claims cannot be independently reproduced from
    the ZIP alone.
12. The scripts compile, but the repository virtual environment lacks the
    `ta` package and the ZIP supplies no pinned requirements file. A network
    rerun would also download mutable Yahoo data without an explicit end
    timestamp.

## Robustness observations

The S&P result is not merely one favorable year. Recomputed annual mean Rank
IC was positive in 2019, 2020, 2021, 2023, 2024, 2025, and 2026, but negative
in 2022 (`-0.0160`). This regime failure matters.

Excluding the first 20 sessions of the latest fold, which removes the portion
nearest its contaminated boundary, did not eliminate the result:

- mean Rank IC: `+0.08040`
- top-20% mean: `+3.4568%`
- top-minus-bottom spread: `+2.7367%`

This supports further research, but it does not repair the model's label,
source, universe, or sealed-test contracts.

## Verdict and safe next step

Verdict: `PROMISING_EXTERNAL_LEAD / NOT VALIDATED`.

Do not copy this into a frozen model, prospective journal, paper engine, or
live engine as-is. The S&P 20-session ranking signal is strong enough to merit
one clean AlienTAI reimplementation with:

- a predeclared exact liquid universe
- source-pure frozen daily data
- exact next-open-to-twentieth-close labels
- exact label-interval purge and full embargo
- 0.25% costs and capital-scaled drawdown
- QQQ and SPY context-only references
- whole-date chronology
- a future append-only prospective journal

Because every bundled outcome through July 9, 2026 is already visible, none of
that period can serve as a new sealed test. Any corrected historical run is
development evidence only; genuine confirmation must come from future data
frozen before its outcome.
