# Nasdaq Model Champion Scorecard

Date: 2026-07-28

Decision: `KEEP_FROZEN_80_SECURITY_CHAMPION`

No challenger clears the complete validation, historical-sample, and
prospective-evidence replacement gate. This decision changes no paper or live
execution setting.

## Comparable five-day models

| Model | Validation | Historical confirmation | Portfolio result | Drawdown | Decision |
|---|---|---|---:|---:|---|
| Frozen 80-security champion | 24 signals, 70.83% wins, +3.38% mean | 40 signals, 75.00% wins, +1.95% mean | +16.25% | -7.44% | Keep champion |
| Complete 101 baseline | 21, 76.19%, +8.51% | 27, 66.67%, +6.27% | +37.18% | -12.01% | Closest challenger; sample short |
| Complete 101 + QQQ relative | 41, 43.90%, +0.37%; negative median | 23, 73.91%, +8.85% | +46.87% | -7.97% | Best observed economics; unstable validation |
| Complete 101 two-stage | 41, 51.22%, +2.16% | 23, 73.91%, +7.14% | +36.20% | -15.16% | Inferior to simpler QQQ model |
| Top-10 clone | 25, 72.00%, +6.51% | 16, 56.25%, +2.19% | +7.17% | -3.19% | Insufficient sample and win rate |

## Replacement gate

A new champion must have:

- all current-universe histories built consistently;
- at least 20 qualifying validation observations with positive mean and median
  net return and at least 50% wins;
- at least 30 independent historical confirmation positions, positive mean and
  median, at least 60% wins, and drawdown no worse than -20%; and
- at least 30 completed frozen prospective observations.

None clears every condition. The complete 101 baseline misses the historical
minimum by three positions and has no prospective completions. The QQQ-relative
challenger also fails validation median/win-rate requirements, has only 23
historical positions, and has no prospective completions.

## Recommended next evidence

Freeze the complete 101 baseline and QQQ-relative challenger alongside the
existing champion in a non-executing prospective journal. Collect at least 30
completed five-session outcomes per model without changing features, cutoffs,
or selection rules. Re-run this exact scorecard only after that evidence exists.
Do not manufacture additional retrospective variants from the already observed
period.
