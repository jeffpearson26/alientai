# Frozen Contextual Options Study

Status: research-only, non-executing, and intentionally low-cost.

## Purpose

Test one hypothesis without further feature hunting: public unusual call activity combined with strong technical context may identify stocks with a positive five-trading-session return more often than not.

This is not a claim of profitability, a recommendation, a paper-trading authorization, or an options-trading system.

## Frozen candidate rule

- Universe: a complete same-day S&P research panel with at least 400 unique symbols.
- Candidate: public unusual call activity and a technical-context score in the daily top quarter.
- Existing policy: `contextual_options_shadow_v1`.
- Holding measurement: stock close-to-close return over the next five trading sessions.
- Cost assumption: 0.25% round trip.
- Data source for outcomes: local Schwab daily CSV only. Never fill an outcome with Alpha Vantage or another source.
- Decision: `AVOID`; selected rows remain `BUY_CANDIDATE` only in the non-executing research journal.

## What is frozen

Until the study ends, do not change the universe, technical model, top-quarter rule, unusual-call definition, holding horizon, cost assumption, or candidate-selection logic. Do not add news, insider, analyst, sector, premarket, or stop-loss filters to this study.

The existing July 21, 2026 five-candidate payload is retained as a source-validated pilot only. It may be counted only if its five-session outcomes can be calculated from local Schwab daily CSV data and it passes the existing duplicate/source checks.

## Evidence gate

The study ends at the first point where both conditions hold:

1. At least 30 completed candidates across at least 10 distinct decision dates.
2. The existing prospective evaluator reports positive mean and median net return, at least a 50% post-cost win rate, and no failure other than any separately documented risk-tolerance exception.

Drawdown is recorded in every report. It is not ignored, but it is not an automatic reason to discard the underlying directional hypothesis during this first evidence stage. Any decision to paper trade still requires separate human approval and a written risk limit.

## Stop conditions

- Do not buy more data, invoke new model training, or download broad archives for this study.
- If the 30-signal/10-date evidence gate fails, archive the result and stop this hypothesis rather than tune it after the fact.
- If the gate passes, conduct a separate risk-policy review before any paper-trading decision.

## Routine

When a full same-day option panel and matching local Schwab technical panel are available, use the existing validation-only adapter and policy to write a non-executing payload. Re-evaluate outcomes only after five later Schwab trading sessions are present. Run `evaluate_contextual_options_prospective_gate.py` against all completed review files. It can never enable an order or change settings.
