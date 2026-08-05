# AlienTAI Autonomous Champion — 20-Session Transparent Model

Status: **FROZEN PENDING PROSPECTIVE EVIDENCE**

This is the result of Jeff's unrestricted model-design authorization. The
candidate is intentionally transparent rather than a forced machine-learning
winner.

## Frozen model

Universe: the fixed June 2026 Nasdaq-100 list containing 101 securities.
QQQ and SPY are context only. Candidates require at least a $5 adjusted price
and $20 million trailing 20-session average dollar volume.

The score is:

`0.50 × cross-sectional rank(126-session excess return vs QQQ)`

`+ 0.30 × cross-sectional rank(60-session excess return vs QQQ)`

`+ 0.20 × (1 - cross-sectional rank(60-session realized volatility))`

The model selects at most five securities after a completed close, enters at
the next adjusted open, exits at the 20th subsequent adjusted close, and
subtracts 0.25% round-trip cost.

## Data audit

- Alpha Vantage full adjusted-daily source.
- 102,960 labeled rows in the immutable panel.
- 86,085 rows passed the point-in-time price/liquidity filters.
- 101 securities and 1,317 sampled decision dates.
- May 1, 2000 through July 1, 2026.
- 417 raw technical/context fields before cross-sectional ranks.
- Exact panel SHA-256 match, zero malformed rows.

## Validation

- 825 signals across 165 dates and 81 symbols.
- Mean net return: **+2.3893%**.
- Median net return: **+1.0648%**.
- Win rate: **55.88%**.
- Newey-West 95% mean interval: **+0.2633% to +4.5154%**.
- Cash-scaled daily mark-to-market maximum drawdown: **-4.9230%**.
- Largest-symbol share: **4.85%**.
- All four observable non-overlap cohorts had positive means.
- Matched QQQ mean: **+1.0297%**.

Every frozen validation gate passed.

## One-time sealed test

The test was not JSON-parsed until validation passed.

- 590 signals across 118 dates and 66 symbols.
- Mean net return: **+3.1682%**.
- Median net return: **+1.3389%**.
- Win rate: **55.59%**.
- Newey-West 95% mean interval: **+0.4315% to +5.9048%**.
- Cash-scaled daily mark-to-market maximum drawdown: **-6.0750%**.
- Largest-symbol share: **7.46%**.
- All four observable non-overlap cohorts had positive means.
- Matched QQQ mean: **+1.5910%**.

The result held up without retuning.

## Interpretation and limitations

This is the strongest newly completed autonomous result, but it is not proof
of future profitability. The current-membership universe creates survivorship
bias, labels overlap between sampled dates, and adjusted next-open/close fills
remain research approximations.

The formula, eligibility rules, costs, universe, and 20-session horizon are now
frozen. The next evidence must be append-only and genuinely prospective.
Nothing here authorizes paper or live trading.

Controlling artifact:

`D:\AlientAI\Models\autonomous_transparent_20session_corrected_folds_20260805\training_report.json`

Controlling artifact SHA-256:

`67c31d496e02fc0193630a99e3258d0d330dc38170085718d579ca0f0ffa139b`

## Prospective program

The first observation was appended before the August 5, 2026 regular-session
open from the completed August 4 close. Its locked selections are FTNT, DDOG,
PANW, CSX, and CRWD. The journal is:

`data_v2\rcef_research\autonomous_champion_20session_prospective_journal.jsonl`

`journal_autonomous_transparent_20session.py` appends future selections or
honest abstentions before entry. Each eligible market date is independent;
pending older horizons do not suppress a new attempt.

`evaluate_autonomous_transparent_20session_outcomes.py` leaves each selection
pending until its exact 20-session exit exists, then appends the source-hashed,
post-cost outcome without rewriting prior evidence. The first five outcomes
are currently pending. No prospective result has matured yet.
