# Nasdaq-100 Technical-Context Clone

Date: 2026-07-28

This is an isolated research clone. It does not replace the active model,
change engine settings, or authorize paper/live trading.

## Universe and design

- Constituent source: official Nasdaq May 1, 2026 list, adjusted for Nasdaq's
  announced June 22 additions/removals.
- Requested securities: 101 (the index can contain two share classes).
- Existing S&P research-table coverage: 80 securities and 50,255 rows.
- Missing from the existing source: ALAB, ALNY, APP, ARM, ASML, CCEP, CRWD,
  CRWV, DASH, DDOG, FER, MELI, MRVL, MSTR, NBIS, PDD, RKLB, SHOP, SNDK, TRI,
  and WDAY.
- Target: forward five-session return of at least 10%.
- Chronological 60%/20%/20% split with 12-calendar-day embargoes.
- Untouched test starts 2025-11-17 and contains 8,924 rows.
- The active broad model and clone were scored on the identical test rows.

## Untouched test comparison

Returns below are gross label returns; subtracting a fixed 0.25% round-trip
cost would reduce each mean and median by 0.25 percentage points.

| Ranking slice | Model | Rows | >=10% winners | Mean 5-day return | Median | Positive |
|---|---|---:|---:|---:|---:|---:|
| Top 0.10% | Active broad model | 8 | 12.50% | +2.8492% | +1.3678% | 50.00% |
| Top 0.10% | Nasdaq clone | 8 | 0.00% | +2.3513% | +2.3299% | 62.50% |
| Top 0.25% | Active broad model | 22 | 4.55% | +1.7055% | +3.0240% | 68.18% |
| Top 0.25% | Nasdaq clone | 22 | 9.09% | +2.9059% | +1.8496% | 77.27% |
| Top 0.50% | Active broad model | 44 | 9.09% | +2.7344% | +2.6050% | 72.73% |
| Top 0.50% | Nasdaq clone | 44 | 9.09% | +2.2717% | +1.9428% | 75.00% |
| Top 1.00% | Active broad model | 89 | 11.24% | +2.7726% | +2.9793% | 67.42% |
| Top 1.00% | Nasdaq clone | 89 | 14.61% | +2.5209% | +2.3173% | 68.54% |
| Top 5.00% | Active broad model | 446 | 15.70% | +2.0255% | +1.1818% | 57.85% |
| Top 5.00% | Nasdaq clone | 446 | 12.78% | +1.4893% | +0.8813% | 56.95% |

## Conclusion

`RESEARCH_HOLD`, but more promising than the semiconductor-only clone.

The Nasdaq clone improves the top-0.25% mean return, positive rate, and large
winner rate, and improves the top-1% large-winner rate. The active broad model
remains stronger on several neighboring slices, including top-0.5%, top-1%
mean/median return, and top-5%. The clone therefore does not clearly dominate.

Next evidence should come from a pre-specified, validation-frozen threshold,
cost-adjusted non-overlapping portfolio simulation with capital-scaled
drawdown. The 21 missing current constituents should be added through a
source-consistent historical dataset before calling this a complete
Nasdaq-100 model.
