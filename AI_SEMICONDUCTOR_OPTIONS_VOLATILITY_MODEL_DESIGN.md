# AI Semiconductor Defined-Risk Options Volatility Model

Status: framework and exact point-in-time fill compiler implemented; learned
heads and full strategy backtest pending
Execution enabled: `false`

## Objective

Convert the preserved AI-semiconductor five-day thesis into a two-stage options
research model:

1. predict direction, absolute realized movement, range-bound probability, and
   volatility behavior over the next five sessions;
2. compare those frozen predictions with contemporaneous implied volatility,
   term structure, liquidity, catalyst timing, and AI-stack risk, then choose a
   defined-risk structure or abstain.

The model must optimize conservative multi-leg return on capital after crossing
the quoted spread for every leg. It must not infer option profit from the
underlying stock return.

## Permitted structures

- Bull call debit spread.
- Bear put debit spread.
- Bull put credit spread.
- Bear call credit spread.
- Long straddle.
- Iron condor.
- Iron butterfly.
- Calendar spread.
- Abstain.

Naked calls, naked puts, short straddles, and short strangles are excluded.

## Strategy logic

- Forecast realized move materially above implied move:
  - strong direction + technical agreement: directional debit spread;
  - low direction confidence: long straddle.
- Forecast realized move materially below implied move, high IV rank, and no
  binary event:
  - front IV rich to back IV with range confidence: calendar;
  - very high pin confidence: iron butterfly;
  - moderate range confidence: iron condor;
  - strong direction: defined-risk credit vertical.
- Otherwise abstain.

The deterministic strategy layer is implemented in
`alientai_v2/research/defined_risk_option_strategy.py`. It is not itself proof
of an edge; it prevents a learned forecast from silently selecting an
undefined-risk or structurally incompatible trade.

## Thesis integration

- Merchant leaders, memory/HBM, foundry/packaging, equipment, custom
  ASIC/networking, design software, infrastructure, and emerging inference
  specialists receive explicit peer-role tags.
- Stack role can control diversification and risk, never a ticker bonus.
- Emerging inference specialists receive no more than half the normal
  hypothetical risk ceiling until liquidity, revenue, customer diversity, and
  production scale are established.
- Visible demand, scarcity/pricing power, valuation, capacity, bookings, and
  competition can enter only through timestamped historical features.
- A public catalyst inside the horizon is context, not permission to sell
  volatility through an unbounded binary event.

## Data audit

The completed Alpha Vantage natural options archive contains daily chain files
with bid, ask, size, strike, expiration, IV, delta, gamma, theta, vega, volume,
and open interest.

All 17 established AI/semiconductor research symbols are covered:

- 122 dated chains: AMAT, AMD, AVGO, INTC, KLAC, LRCX, MU, NVDA, SMCI.
- 109 dated chains: ADI, CDNS, MCHP, MPWR, ON, SNPS, TXN.
- 108 dated chains: QCOM.

Coverage is approximately January through July 2026. This is enough to build an
exact prototype but too short and regime-concentrated for a profitability
claim. CBRS has no archive history and must begin prospectively.

An exact feasibility scan joined the 1,694 underlying panel rows to the
next-session option-entry date and fifth-session option-exit date:

- 1,262 rows have both exact dated chain files.
- 382 rows lack the entry-date chain.
- 92 rows lack the exit-date chain.
- Some rows lack both, so the missing counts overlap.
- All 1,262 complete pairs retain at least one identical contract ID at exit.
- Exact contract overlap ranges from 42 to 11,510 contracts, with a median of
  2,424.

This supports an exact multi-leg compiler. Missing rows must remain missing;
they cannot use nearby dates, theoretical prices, or another provider.

## Required backtest contract

- Make the underlying forecast before the option-entry snapshot.
- Freeze contract identities from an earlier observable selection snapshot.
- Require a later, distinct entry snapshot; selecting and filling from the same
  date-only snapshot is prohibited.
- Use the next available complete end-of-day chain for entry; never pretend an
  end-of-day chain was an opening quote.
- Select every leg deterministically before observing its outcome.
- Buy at ask and sell at bid; sell at bid and buy back at ask.
- Require every selected contract to exist in the exact exit-date chain.
- Measure debit trades against debit paid and credit structures against defined
  maximum risk.
- Include assignment/expiration rules, contract multipliers, fees, and missing
  quote handling.
- Split by decision date with label purging and embargoes.
- Choose prediction thresholds and strategy boundaries on validation only.
- Keep the final test sealed, then require a frozen prospective journal.

## Next build

`alientai_v2/research/exact_multileg_option_compiler.py` now enforces
selection-available <= decision < entry < exit, exact contract identity across
all three snapshots, ask-side purchases, bid-side sales, fees, and return on
defined maximum risk. Compile exact candidates for the 17-symbol archive and
quantify missing-leg rates before training any strategy label. Then train
separate direction and absolute-move heads; derive IV rank and term structure
only from chains available by the option-entry cutoff. If exact fills are too
sparse, reduce the permitted set rather than substitute marks, last prices, or
theoretical option values.
