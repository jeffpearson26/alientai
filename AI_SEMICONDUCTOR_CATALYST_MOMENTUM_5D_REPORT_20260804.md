# AI/Semiconductor Catalyst-Momentum Five-Session Model

Status: `RESEARCH_HOLD`
Execution enabled: `false`

## Purpose

This isolated model translates Jeff's five-day catalyst + momentum framework
into point-in-time features where the repository has defensible historical
data. It does not modify an existing frozen model, `engine.py`, settings, paper
trading, or live trading.

The executable label is:

- decision after the completed source panel cutoff;
- entry at the next regular-session open;
- exit at the fifth subsequent session close;
- 0.25% round-trip cost already deducted;
- positive training class at a net return of at least 2%.

## Implemented logic

- Technical setups: oversold bounce, volume-confirmed breakout, continuation,
  cross-sectional 20/60-session relative strength, MACD, moving-average
  structure, RSI, Bollinger position, OBV, relative volume, and ATR.
- Catalyst gate: target-specific material news, recent earnings reaction, or
  the conservative target-specific analyst-action proxy.
- Positioning: unusual call activity, call-volume history, open interest,
  volume/open-interest ratios, put/call ratios, and near-money IV.
- Fundamental sanity overlay: recent EPS surprise/streak, analyst/news
  negativity, insider code-P purchase features, and explicit short-interest
  availability.
- Risk: reject parabolic setups, require ATR between 0.5% and 8%, select no
  more than five names per decision date, and allow no more than five
  concurrent positions.

All cross-sectional ranks use lagged values from the same decision date. No
future label is read by feature construction.

## Chronology

- Rows: 1,694
- Symbols: 17
- Train decisions through: 2026-04-21
- Training labels through: 2026-04-28
- Validation: 2026-04-29 through 2026-05-27
- Validation labels through: 2026-06-03
- Untouched test begins: 2026-06-04
- Selection fractions tested: 10%, 20%, 30%, and 50%
- Each stage selected its fraction from validation only.

## Untouched test results

| Stage | Validation-selected fraction | Trades | Mean net | Median net | Win rate | >=2% | >=5% | Worst |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Technical setup | 30% | 20 | -0.5822% | -1.7859% | 40% | 30% | 25% | -17.9846% |
| Catalyst + technical | 30% | 20 | -1.5868% | -2.9232% | 25% | 15% | 15% | -13.5422% |
| Catalyst + technical + positioning | 50% | 20 | -0.9506% | -3.1709% | 25% | 25% | 20% | -13.5422% |
| Full available-data model | 30% | 20 | +0.2278% | -3.5789% | 25% | 25% | 25% | -14.8976% |

The full model's positive mean is not persuasive: its negative median and 25%
win rate show that a few large winners mask a poor typical selection.

The predeclared one-day time-stop diagnostic exited at the first close whenever
the first-session net return was nonpositive; otherwise it held to session
five. It worsened all four stages. The full model fell from +0.2278% to
-0.7541% mean, with a 10% win rate. Do not adopt that exit.

## Missing logic that was not fabricated

- Complete point-in-time upcoming earnings calendar.
- Licensed structured analyst rating and price-target changes.
- Historical guidance, design-win, capacity, HBM/CoWoS, and hyperscaler-event
  taxonomy.
- Intraday paths for hard-stop simulation.
- Exact second-session prices for a two-session time stop.
- Historical portfolio-level sector-correlation estimates.

## Decision

Do not promote or prospectively freeze this current instantiation. Validation
was strong but did not generalize, which is consistent with a small,
regime-specific six-month panel and sparse catalyst histories.

Preserve the code and report. After the 2020-2026 adjusted intraday archive and
AI/data-center supplement complete, rebuild the technical pretraining sample
and obtain point-in-time structured catalyst histories. Pre-register the next
chronology and risk policy before retraining. The present test is now observed
and must not be used repeatedly to tune a replacement.
