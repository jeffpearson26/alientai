# Nasdaq-100 QQQ-Relative Challenger

Date: 2026-07-28

Status: `RESEARCH_PROMISING_REGIME_SENSITIVE`

This experiment adds point-in-time QQQ returns and each stock's excess return
versus QQQ over 5, 20, and 60 sessions to the complete 101-security Nasdaq
technical dataset. All other data, split, selection, cost, capacity, and
mark-to-market rules match the complete-universe baseline.

## Locked result

Validation selected top 0.50% and locked score cutoff
`0.2246736047938044`. Its validation evidence was weak: 41 signals,
+0.367082% mean net return, -2.672611% median, and 43.902439% wins.

The untouched test retained 23 positions:

- mean net return: +8.847970%
- median net return: +9.544842%
- post-cost win rate: 73.913043%
- capital-scaled final return: +46.870445%
- capital-scaled maximum drawdown: -7.973577%
- peak concurrent positions: 5
- price/label alignment error: 0.0%

## Interpretation

QQQ-relative context materially improved the observed test economics compared
with the source-consistent technical baseline, but the weak validation slice
means the improvement may be regime-dependent. The test period is now observed
and must not be used for threshold tuning. Preserve this model as a challenger
for regime-specialization and prospective comparison; do not replace the
current champion or enable it for paper/live execution from this result alone.
