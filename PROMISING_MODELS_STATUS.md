# AlienTAI Promising Model Register

Generated: 2026-08-04 08:36 Pacific
Purpose: permanent morning operating list for every legitimate research lead.
Safety: research only; no model listed here is authorized for paper or live trading.

The automatically refreshed data-family and coverage matrix is
`PROMISING_MODEL_DATA_INVENTORY.md`.

## Primary models

| Priority | Frozen model | Universe / horizon / inputs | Best honest evidence | Current testing state | Exact reason if not advancing |
|---:|---|---|---|---|---|
| 1 | Technical context + unusual calls | Natural universe; 5 sessions; technical score then unusual call buying | Prospective: 5 signals, 80% wins, +1.8944% mean, +3.0803% median. Historical fixed slices were positive at three chronological splits. | **BLOCKED UNTIL AFTER-CLOSE CHAIN COLLECTION** | Only one prospective decision date. August 4 full-universe nonempty option chains must be collected after the close and joined to the frozen technical/call history before another payload can be frozen. |
| 2 | Nasdaq-101 baseline | 101 symbols; 5 sessions; technical | Historical untouched top 0.25%: 20 rows, 70% >=10% winners. First completed prospective date: 2 signals, 100% wins, +6.7067% mean. | **READY FOR AUGUST 4 AFTER-CLOSE ATTEMPT** | All 101 symbols plus QQQ now share completed August 3 coverage. No backfill is allowed; refresh the final August 4 close and journal before the August 5 entry. |
| 3 | Nasdaq-101 QQQ-relative | 101 symbols; 5 sessions; technical + QQQ-relative context | Historical untouched top 0.10%: 8/8 >=10% winners; top 0.25%: 65%. First prospective date: 2 signals, 50% wins, +2.3750% mean. | **READY FOR AUGUST 4 AFTER-CLOSE ATTEMPT** | Same verified 101+QQQ coverage as baseline; the dedicated journal must append its August 4 observation or abstention after the final close. |
| 4 | AI/semi 20-minute technical + premarket | 17 symbols; 09:30 entry to 09:45 close; prior technical + 09:25 premarket | 20 held-out days, 28 trades, 70% positive days, +0.52% mean daily net, +10.62% compounded, -4.56% drawdown. | **BLOCKED BY ORIGINAL SOURCE/TIMING CONTRACT** | Alpha Vantage lacked entitled pre-entry realtime data and its 09:25 interval is not complete before the frozen 09:30 entry. Cannot be repaired without a separately frozen timing/source model. |
| 5 | AI/semi 60-minute technical + premarket + calls | 17 symbols; 09:30 to 10:25; prior technical/calls + 09:25 premarket | 20 held-out days, 28 trades, 65% positive days, +0.70% mean daily net, +14.28% compounded, -5.70% drawdown. | **BLOCKED BY ORIGINAL SOURCE/TIMING CONTRACT** | Same Alpha Vantage 09:30-entry impossibility. Preserve frozen evidence; use the separate Schwab late-entry variants prospectively. |
| 6 | Schwab late-entry 60-minute calls | 17 symbols; 09:35 to 10:30; Alpha prior technical/calls + Schwab 09:25 premarket | Untouched: 28 trades, 57.14% wins, +0.6325% mean, +11.2514% compounded, -5.7230% drawdown. | **PRIOR INPUTS REPAIRED; NEXT CAPTURE AUGUST 5** | Exact August 3 technical/call panels now contain all 17 symbols, nonempty chains, and at least 20 prior call observations; readiness passed. The August 4 09:30 capture window had already elapsed, so August 4 cannot be backfilled. |
| 7 | Schwab late-entry 60-minute premarket | Same 17-symbol 09:35 program without call feature family | Untouched: 56 trades, 51.79% wins, +0.3895% mean, +4.6607% compounded, -7.1860% drawdown. | **PRIOR INPUTS REPAIRED; NEXT CAPTURE AUGUST 5** | Same verified readiness and missed-window constraint as the calls variant. |
| 8 | AI/semi one-session narrative earnings context | 17 symbols; 1 session; technical + premarket + point-in-time earnings context | Exploratory frozen comparison: 37 selections, 62.16% wins, +0.7476% mean, +0.5398% median. | **BLOCKED ON AUGUST 4 PREMARKET COVERAGE** | Exact August 3 daily technical data is ready, but Alpha's historical current-month download produced 0/17 usable August 4 premarket rows and both realtime and delayed entitlements were denied. Retry historical data after the close; otherwise Jeff must resolve Alpha data entitlement. |
| 9 | AI/semi technical + premarket | 17 symbols; 5 sessions | Validation-locked historical test: 31 selections, +1.7260% mean, -0.0638% median, 48.39% wins. Separate journal has 4 pending observations across 2 dates. | **BLOCKED ON AUGUST 4 PREMARKET COVERAGE** | Same 0/17 Alpha premarket blocker as the narrative model. Existing outcomes remain pending and do not excuse the new-day attempt. |
| 10 | Nasdaq-80 champion | 80 symbols; 5 sessions; QQQ-context technical | Corrected historical test: 12 trades, +2.8700% mean, +1.6163% median, 58.33% wins. | **READY FOR AUGUST 4 AFTER-CLOSE ATTEMPT** | The frozen 80-symbol universe has completed August 3 coverage. Refresh the final August 4 close and append its next observation or abstention; the older PLTR outcome remains pending independently. |

## Secondary promising leads currently parked

| Model | Evidence | Why parked |
|---|---|---|
| Nasdaq two-stage QQQ-relative | 23 historical confirmation positions, +7.1350% mean, 73.91% wins, +36.20% capital-scaled return, -15.16% drawdown | Confirmation period was already reused and the model was inferior to the simpler QQQ-relative challenger. |
| Nasdaq 10-session clone | 57 test trades, +1.5204% mean, 56.14% wins, +15.40% capital return | -23.09% drawdown exceeded the fixed limit; observed test cannot be retuned. |
| Nasdaq top-10-company clone | 16 test trades, +2.1923% mean, 56.25% wins, -3.19% drawdown | Far too few trades for promotion or priority prospective capacity. |
| Selective two-session large-move head | 57 test rows, +0.8709% mean, 57.89% wins | AUC weakened from 0.6506 validation to 0.5705 test; not yet frozen into a prospective program. |
| Corrected Nasdaq-80 two-session model | 12 trades, +5.6345% mean, +3.8915% median, 83.33% wins | Sample is only 12; preserved as a fragile lead rather than treated as established. |

## Development candidates without promising performance evidence yet

- Defined-risk options-volatility picker: strategy layer, explicit policy,
  readiness safeguards, and exact point-in-time multi-leg fill compiler exist;
  learned direction/move heads and full chronological backtest are pending.
- Any-time rolling 20-minute model: Jeff refined this to one-minute resolution.
  The 103-symbol five-minute archive remains preserved and audited; the
  separate 8,137-request one-minute archive is actively collecting after a
  successful AAPL pilot (21,095 rows and complete 390-bar regular sessions).
  Panel construction, chronological training, and live-source compatibility
  validation remain pending.
- Five-day catalyst-momentum model: explicitly excluded from this promising
  list because its typical held-out selection lost money; status remains
  `RESEARCH_HOLD`.

## Morning rules

1. Refresh this file every valid market morning before any decision cutoff.
2. Never call a model active merely because an old outcome is still pending.
3. Every promising frozen model must show one state: new observation,
   abstention, pending outcome plus a new-day attempt, not scheduled, or exact
   blocker.
4. A pending horizon never prevents the next eligible frozen observation.
5. Immediately surface missed windows, stale journals, missing files, empty
   provider payloads, credentials, or timing conflicts.
6. Preserve frozen models and all prior observations; never backfill or retune.
