# Nasdaq-100 One-Day Technical Clone

Date: 2026-07-28

## Frozen design

- Exact same 80-security training universe as the five-day Nasdaq clone.
- 50,255 point-in-time technical rows; all 50,255 received complete labels.
- Decide after the current session close.
- Enter at the next regular session open and exit at that session close.
- Classification target: gross intraday return of at least 2%.
- Chronological 60%/20%/20% partitions with 12-calendar-day embargoes.
- Candidate fraction/cutoff selected from validation only.
- Maximum five positions per session; unused slots remain cash.
- Evaluation subtracts 0.25% round-trip cost.

## Results

The model stopped at LightGBM iteration 24 with validation AUC 0.716242.
Its score distribution was coarse enough that the predeclared 0.25%, 0.50%,
and 1.00% validation quantiles resolved to the same cutoff
(`0.16009235126661475`) and the same 83 validation signals.

Validation:

- 83 signals across 37 trading days.
- +0.689682% mean net return.
- +0.097222% median net return.
- 51.807229% post-cost win rate.
- +11.243137% capital-scaled return.
- -6.020910% maximum drawdown.

Untouched test:

- 241 signals across 87 trading days.
- -0.063818% mean net return.
- +0.069942% median net return.
- 51.037344% post-cost win rate.
- -4.475285% capital-scaled return.
- -13.407436% maximum drawdown.

## Conclusion

`RESEARCH_FAIL`.

The validation return did not replicate after costs in untouched testing.
Do not add this one-day clone to the control panel, paper account, or live
execution. Preserve it as evidence that the current technical feature set is
materially better suited to the successful five-day horizon than a
next-session intraday trade.
