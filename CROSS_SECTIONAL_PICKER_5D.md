# AlienTAI Cross-Sectional Five-Session Picker

## Purpose

This is a production-style, research-only daily stock-ranking pipeline. It
ranks the Nasdaq-100 plus the focused AI/semiconductor screen and estimates
which liquid names are most likely to outperform the same-day universe over
the next five trading sessions.

It does not place orders, enable an engine, or authorize paper/live trading.
Every emitted name is marked `execution_decision: AVOID` until separate
append-only future evidence satisfies AlienTAI's promotion rules.

## Contract

- Data: full split/dividend-adjusted Alpha Vantage daily OHLCV.
- Universe: union of `nasdaq100_2026-06_symbols.txt` and
  `research_universes/ai_semiconductor_screen_2026.txt`.
- Context-only benchmarks: QQQ and SPY.
- Decision: after the official completed regular-session close.
- Research entry: next complete regular-session adjusted open.
- Research exit: fifth subsequent regular-session adjusted close.
- Cost: 0.25% round trip.
- Default target: within-date percentile rank of the five-session net return.
- Predictive inputs: only within-date cross-sectional percentile ranks.
- Daily policy: top 10%, at most 10 names, equal-weighted.
- Missing, illiquid, abnormally quiet, or excessive-ATR rows are excluded.

## Features

The point-in-time feature layer calculates:

- 1-, 5-, and 10-session momentum plus ROC(10);
- RSI(14), stochastic %K/%D, and CCI(20);
- ATR%, Bollinger %B/bandwidth, and realized volatility;
- relative volume, volume ROC, and directional volume;
- EMA distance, MACD histogram, ADX, gap, and recent range position.

For each completed decision date, every predictive feature is converted to a
0..1 average-tie percentile rank among the available universe. LightGBM sees
only those ranked columns. Absolute price, ATR, relative volume, and dollar
volume are used as eligibility/risk filters, not predictive shortcuts.

The transparent comparison is a frozen weighted rank composite. It is always
reported beside LightGBM and is never silently substituted after results are
observed.

## Leakage prevention and validation

The development chronology uses five contiguous, whole-date purged folds:

1. all symbols from a decision date stay together;
2. a training observation is purged if its five-session label interval
   overlaps the test fold;
3. five sessions after every fold are embargoed;
4. no random row-level K-fold is used;
5. the final 252 market dates are held out behind another five-session
   embargo.

Out-of-fold predictions report:

- daily Spearman rank information coefficient;
- top-basket mean/median net return and hit rate;
- matched bottom-basket return and top-minus-bottom spread;
- overlapping long-only portfolio return, Sharpe, and capital-scaled
  drawdown using exact five-session mark-to-market paths;
- fold-level diagnostics and the transparent baseline.

The sealed test remains unloaded unless the out-of-fold policy has at least
100 signals and 20 dates, positive mean and median net return, at least 50%
wins, rank IC of at least 0.01, a positive top-minus-bottom spread, and
drawdown above -20%.

## Files

- `alientai_v2/research/cross_sectional_technical_5d.py` — shared technical
  calculations used by historical and daily paths.
- `alientai_v2/research/cross_sectional_picker_5d.py` — purged folds,
  label-free snapshot ranking, selection, metrics, and portfolio simulation.
- `build_cross_sectional_technical_5d_panel.py` — adjusted historical panel.
- `audit_cross_sectional_technical_5d_panel.py` — full content and timing audit.
- `train_cross_sectional_picker_5d.py` — purged-CV training and sealed gate.
- `score_cross_sectional_picker_5d.py` — label-free current daily ranking.
- `run_cross_sectional_picker_5d.py` — end-to-end command runner.
- `cross_sectional_picker_5d_config.json` — frozen default configuration.
- `test_cross_sectional_picker_5d.py` — focused methodological tests.

## Commands

Use the repository virtual environment from
`C:\Users\jeffp\alientai_start_over_8010`.

Build and independently audit a new panel:

```powershell
.\.venv\Scripts\python.exe run_cross_sectional_picker_5d.py build `
  --panel-root D:\AlientAI\Data\Compiled\cross_sectional_picker_5d_v1
```

Train with purged cross-validation:

```powershell
.\.venv\Scripts\python.exe run_cross_sectional_picker_5d.py train `
  --panel-root D:\AlientAI\Data\Compiled\cross_sectional_picker_5d_v1 `
  --model-root D:\AlientAI\Models\cross_sectional_picker_5d_v1
```

Produce the current ranking:

```powershell
.\.venv\Scripts\python.exe run_cross_sectional_picker_5d.py score `
  --model-root D:\AlientAI\Models\cross_sectional_picker_5d_v1 `
  --ranking-root D:\AlientAI\Rankings\cross_sectional_picker_5d_v1
```

If the model is on `RESEARCH_HOLD`, the scorer refuses by default. An explicit
diagnostic may be generated with `--research-preview`; it remains AVOID-only.

The `all` subcommand runs build, audit, train, and score. Pass
`--reuse-audited-panel` only when the named panel root already contains a
verified `content_audit.json`.

## Daily operation

After a completed market close:

1. refresh every required symbol with the same full adjusted provider;
2. require a complete, zero-failure manifest and at least 80% universe
   coverage on one common decision date;
3. verify the saved model/config hashes;
4. build a label-free snapshot and rank features within that date;
5. write JSON and CSV rankings;
6. append a separate future observation only if the model has been frozen for
   prospective testing before its next-open entry.

Never backfill a missed decision after an outcome becomes visible.

## Limitations

- The current constituent files are contemporary and therefore retain
  survivorship and selection bias. Point-in-time Nasdaq membership is needed
  for a cleaner long-history claim.
- Technical rank effects are typically small, unstable, and sensitive to
  market regime.
- A 0.25% cost can erase an apparent five-session edge.
- Daily candles cannot prove intraday fill quality or simulate stop-loss paths.
- Purging prevents overlapping-label leakage; it does not prevent structural
  regime changes.
- Strong retrospective performance is insufficient. Promotion requires
  repeated, source-consistent, genuinely future observations.
