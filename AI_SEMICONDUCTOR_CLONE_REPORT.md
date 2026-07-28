# AI/Semiconductor Technical-Context Clone

Date: 2026-07-28

This is an isolated research clone of the active natural technical-context
LightGBM model. It does not alter the active model, engine settings, paper
positions, or live-trading controls.

## Universe and design

- Requested explicit universe: 21 AI/chip/semiconductor tickers.
- Existing S&P research table coverage: 17 tickers and 8,638 rows.
- Missing from that source: ARM, ASML, MRVL, and TSM.
- Target: forward five-session return of at least 10%.
- Split: chronological 60%/20%/20% with 12-calendar-day embargoes.
- Split dates and training hyperparameters match the active model.
- Untouched test begins 2025-11-17 and contains 2,006 rows.

## Untouched test comparison

| Ranking slice | Model | Rows | >=10% winners | Mean 5-day return | Median | Positive |
|---|---|---:|---:|---:|---:|---:|
| Top 0.25% | Active broad model | 5 | 20.00% | +4.9748% | +4.4505% | 60.00% |
| Top 0.25% | Sector clone | 5 | 0.00% | +0.4117% | +0.9132% | 80.00% |
| Top 1% | Active broad model | 20 | 5.00% | +0.5864% | +2.0060% | 65.00% |
| Top 1% | Sector clone | 20 | 0.00% | -1.4982% | +0.6683% | 60.00% |
| Top 5% | Active broad model | 100 | 14.00% | +2.0405% | +2.5554% | 63.00% |
| Top 5% | Sector clone | 100 | 7.00% | -0.5030% | +0.5608% | 56.00% |

## Conclusion

`RESEARCH_HOLD`. The sector-only clone does not outperform the active broad
model on the same untouched semiconductor holdout. The likely limitation is
the much smaller and highly correlated training sample. Do not connect this
clone to paper or live trading. A future sector experiment should first add
source-consistent history for the four missing names and preferably a broader
historical semiconductor universe including delisted constituents.
