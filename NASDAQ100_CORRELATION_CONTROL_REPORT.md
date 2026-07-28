# Nasdaq-100 Correlation Control

Date: 2026-07-28

Status: `RESEARCH_HOLD_INSUFFICIENT_VALIDATION_SAMPLE`

The frozen QQQ-relative model and score cutoff were evaluated with four
predeclared maximum trailing-correlation limits: 0.60, 0.75, 0.90, and 1.01
(effectively no correlation rejection). Correlations use only the 60 sessions
ending on the decision date, require at least 40 common returns, and fail closed
when history is unavailable.

Validation selection required at least 20 capacity-limited positions, positive
mean and median net returns, at least 50% wins, drawdown no worse than -20%, and
then maximized capital return divided by absolute drawdown.

## Validation evidence

| Maximum correlation | Positions | Mean net | Median net | Wins | Portfolio return | Drawdown |
|---:|---:|---:|---:|---:|---:|---:|
| 0.60 | 15 | +1.446901% | +3.993615% | 53.33% | +3.665405% | -10.156268% |
| 0.75 | 16 | +2.136299% | +4.535032% | 56.25% | +6.251769% | -10.156268% |
| 0.90 | 17 | +1.301212% | +3.993615% | 52.94% | +3.675800% | -12.334440% |
| 1.01 | 17 | +1.301212% | +3.993615% | 52.94% | +3.675800% | -12.334440% |

The 0.75 control is directionally promising: it rejected one highly correlated
candidate, increased return, and reduced drawdown. However, every threshold
retained fewer than the frozen 20-position minimum. No threshold was selected,
and the confirmation period was not evaluated.

## Decision

Preserve the correlation-control code for future validation when more
prospective observations exist. Do not lower the sample gate after seeing these
results, change the current challenger, or connect this control to execution.
