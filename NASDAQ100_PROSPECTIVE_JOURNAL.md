# Nasdaq Challenger Prospective Journal

Started: 2026-07-28

Status: `ACTIVE_RESEARCH_ONLY`

Two frozen challengers are now being observed without paper or live orders:

- `nasdaq100_complete_101_baseline_v1`
- `nasdaq100_complete_101_qqq_relative_v1`

The manifest fingerprints each model and training report, freezes both score
cutoffs, limits each model to five candidates per market session, requires a
fresh complete 101-security universe plus QQQ, and targets a five-session
outcome. The journal is append-only and deduplicates model/date/symbol keys.

The local Schwab archive retains a legacy Pacific-local date key one calendar
day before the corresponding UTC market session. The journal preserves that key
for model compatibility and separately records `market_session_date`.

## First valid frozen observations

Session: 2026-07-27

| Model | Symbol | Entry close | Raw score | Relative rank |
|---|---|---:|---:|---:|
| Complete 101 baseline | SNDK | 1278.23 | 0.232312 | 100 |
| Complete 101 baseline | NBIS | 187.88 | 0.218966 | 99 |
| Complete 101 + QQQ | MU | 900.20 | 0.249965 | 100 |
| Complete 101 + QQQ | NBIS | 187.88 | 0.238673 | 99 |

These four observations are pending. Relative rank is a same-day score
percentile, not a probability. Every journal row is marked `research_only`,
`status: pending`, and `execution_decision: AVOID`.

No outcome should be calculated until five later trading sessions exist. Model
features, cutoffs, and selection rules must remain unchanged while collecting
the required 30 completed observations per challenger.
