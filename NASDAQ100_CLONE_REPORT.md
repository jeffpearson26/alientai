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

## Validation-locked portfolio result

The model was then evaluated under a stricter contract:

- Candidate ranking fractions were limited in advance to 0.25%, 0.50%, and
  1.00%.
- The fraction and exact score cutoff were selected only from validation data.
- The untouched test was evaluated once.
- Returns include a 0.25% round-trip cost.
- The portfolio has five equal target slots, leaves unused capital in cash,
  never borrows, and is marked to market daily.

Validation selected the top 0.25% fraction (score cutoff
`0.15986412677273237`). On the untouched test:

- 42 candidates before the position-capacity rule and 40 executed simulations.
- +1.947586% mean net five-day return per trade.
- +1.692813% median net five-day return.
- 75.00% post-cost winning trades.
- +16.246296% capital-scaled portfolio return.
- -7.443113% capital-scaled maximum drawdown.
- Five peak concurrent positions and zero label/price alignment error.

The report fingerprints the rows, model, training report, and complete daily
price archive. The generated JSON is stored in the ignored research-data
directory as `nasdaq100_clone/portfolio_validation.json`.

## Conclusion

`RESEARCH_PASS_HISTORICAL`, but not yet prospective.

The Nasdaq clone improves the top-0.25% mean return, positive rate, and large
winner rate, and improves the top-1% large-winner rate. The active broad model
remains stronger on several neighboring slices, including top-0.5%, top-1%
mean/median return, and top-5%. The clone therefore does not clearly dominate.

The required validation-frozen, cost-adjusted, capacity-limited,
capital-scaled historical simulation now passes convincingly. This is the
strongest technical-only clone result so far, but its test archive has now
been observed and only 80 of 101 requested securities were available.
Therefore it must remain isolated from execution. The next evidence is a
frozen prospective shadow period plus source-consistent history for the 21
missing current constituents.

## Paper observation

On 2026-07-28 the frozen clone was added to the local owner control panel as
`nasdaq100_technical_clone_v1`. Its candidate universe is restricted to the
exact 80 symbols present in training, not the broader 101-security constituent
request. The adapter requires a complete, recent, paper-only payload; checks
the frozen cutoff again; rejects untrained symbols; and uses the existing
one-share, five-position, five-daily-buy paper safeguards. Live trading remains
disabled. The first July 27 payload identified INTC, MCHP, and LRCX, but the
shared account had already used all five daily paper buys, so no Nasdaq-clone
orders were placed immediately.
