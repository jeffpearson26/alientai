# AI/Semiconductor Schwab Late-Entry Research

Status: `FROZEN_PROSPECTIVE_RESEARCH_PENDING`

This is a separate research program. It does not alter the original Alpha
Vantage-frozen intraday study, the pick competition, `engine.py`, or any paper
or live account.

## Executable timing contract

- Universe: the fixed 17 symbols in
  `research_universes/ai_semiconductor_screen_2026.txt`.
- Current-session premarket source: Schwab five-minute extended-hours candles.
- Decision window: 09:30 through 09:34:59 ET, after the 09:25
  interval-start candle is complete.
- Entry: 09:35 ET five-minute bar open.
- Exit: 10:30 ET five-minute bar close, observable at 10:35 ET.
- Cost: 0.25% round trip.
- Technical and call features remain prior-session, point-in-time Alpha
  Vantage data. Each feature family must retain this source contract in every
  future run.

## Historical construction

The bounded Schwab collection produced files for all 17 real symbols, covering
104 usable dates. Two comment lines in the documented universe file were
mistakenly counted as unavailable symbols by the old downloader; the symbol
reader is now tested to ignore comments. Both 20- and 60-minute panels contain
1,275 rows. Timing audits found zero bad source labels, zero post-cutoff
premarket timestamps, zero non-prior technical/call dates, and zero safety
flag violations.

## Untouched chronological test

The daily selection fraction was selected using validation only.

| Model | Fraction | Validation | Untouched test |
|---|---:|---|---|
| 20m technical | 30% | 87 trades, 47.13% wins, -0.0937% mean | 84 trades, 53.57% wins, +0.0481% mean |
| 20m premarket | 50% | 132 trades, 44.70% wins, -0.0890% mean | 129 trades, 53.49% wins, +0.0217% mean |
| 20m calls | 10% | 29 trades, 62.07% wins, +0.2456% mean | 28 trades, 46.43% wins, -0.1884% mean |
| 60m technical | 50% | 132 trades, 52.27% wins, +0.1565% mean | 129 trades, 51.16% wins, +0.1339% mean |
| 60m premarket | 20% | 58 trades, 58.62% wins, +0.4342% mean | 56 trades, 51.79% wins, +0.3895% mean; +4.6607% compounded; -7.1860% drawdown |
| 60m calls | 10% | 29 trades, 55.17% wins, +0.4968% mean | 28 trades, 57.14% wins, +0.6325% mean; +11.2514% compounded; -5.7230% drawdown |

The 60-minute premarket and calls variants are frozen for prospective testing.
The samples remain too small to authorize execution. The 20-minute variants
are retained as research artifacts but are not advanced.

## Forward-only rules

The first eligible decision date is the next valid U.S. market morning after
August 3, 2026. August 3 cannot be backfilled because its outcomes were visible
before this contract was frozen. Every run must fail closed if any of the 17
symbols lacks an exact 09:25 Schwab candle, if scoring occurs outside the
09:30–09:34:59 window, or if prior-session technical/call inputs are missing.
The program records research observations only and never creates an order.
