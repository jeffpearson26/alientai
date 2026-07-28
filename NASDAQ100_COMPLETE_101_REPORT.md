# Nasdaq-100 Complete-Universe Challenger

Date: 2026-07-28

Status: `RESEARCH_PASS_HISTORICAL_CHALLENGER`

This isolated challenger rebuilds all 101 current Nasdaq-100 securities from the
same local Schwab daily source. It does not splice rows from the earlier
S&P-derived table, does not replace the frozen 80-security champion, and is not
connected to paper or live execution.

## Data and protocol

- 101 of 101 requested securities produced rows.
- 44,620 point-in-time technical rows cover 2024-09-19 through 2026-07-01.
- The label is the close-to-close return over five future trading sessions.
- The target is a gross return of at least 10%.
- Chronological train/validation/test partitions use 12-calendar-day embargoes.
- The ranking fraction and score cutoff are selected on validation only.
- Test positions use five capital slots, daily mark-to-market accounting, idle
  cash, no borrowing, and a 0.25% round-trip cost.

## Locked result

Validation selected the predeclared top 0.25% fraction and locked cutoff
`0.20886314398519493`.

The untouched test retained 27 positions:

- mean net return: +6.269610%
- median net return: +4.369699%
- post-cost win rate: 66.666667%
- capital-scaled final return: +37.184514%
- capital-scaled maximum drawdown: -12.006414%
- peak concurrent positions: 5
- price/label alignment error: 0.0%

## Decision

The result is economically promising and validates the complete, consistent
source pipeline. It remains a challenger because it has fewer test positions
and a lower win rate than the frozen 80-security champion (40 positions and
75% wins). The champion remains unchanged. The next controlled experiment adds
Nasdaq-relative features to this same 101-security dataset and evaluates them
under the identical locked protocol.
