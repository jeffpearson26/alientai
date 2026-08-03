# Future AI/Semiconductor Multi-Horizon Catalyst Model

Status: `PARTIAL_V1_BUILT_RESEARCH_ONLY`

This document preserves Jeff's August 3 model hypothesis. A partial V1 was
built on August 3 using only the feature families with defensible historical
point-in-time coverage. Its results and explicit missing families are recorded
in `AI_SEMICONDUCTOR_MULTI_HORIZON_CATALYST_REPORT_20260803.md`. It does not
select a security, create an order, or alter an active prospective study.

## Objective

Rank a frozen, point-in-time AI/semiconductor universe before 09:25 Eastern
for separate 1-, 5-, and 20-trading-session stock outcomes. Use the next
regular-session open as entry, fixed later-session closes as exits, and
realistic frozen costs. Each horizon gets its own label, model, calibration,
selection policy, and evaluation; a single model must not silently substitute
one horizon for another.

## Point-in-time feature families

### 1. Corporate fundamentals and guidance

- reported revenue, EPS, margins, cash flow, and segment growth;
- standardized surprise versus the consensus available before release;
- guidance midpoint and change versus the prior guide and prior consensus;
- explicit AI/data-center/HBM/custom-silicon/networking revenue when reported;
- estimate revisions available before the decision cutoff;
- days since the latest public report and guidance update.

Store the original value, comparison baseline, publication timestamp, source,
currency, fiscal period, and missingness. Never join a revised consensus or
later transcript passage to an earlier decision date.

### 2. Price, volume, and technical context

- 1/5/20/63/126-session returns, slopes, volatility, beta, and drawdown;
- distance from 9/20/50/126-session averages and recent highs;
- RSI, MACD, ATR, Bollinger width/position, ADX, and volume features;
- relative strength versus QQQ and a frozen semiconductor benchmark;
- premarket gap, relative volume, and directional-pressure features through
  exactly 09:25 Eastern;
- liquidity, spread, and tradability controls.

Pullback and oversold measures are interaction features, not automatic
buy-the-dip rules. Existing evidence already rejects premarket continuation as
a reliable standalone rule.

### 3. Known catalyst calendar

- trading sessions until and since earnings;
- whether a horizon crosses a scheduled earnings event;
- investor days, product events, regulatory decisions, and other public,
  timestamped scheduled events;
- option-expiration and broad macro-event proximity where relevant.

Only the known schedule may be used before the event. The later result,
guidance, price reaction, or revised event date cannot leak backward.

### 4. Analyst, news, and public narrative events

- timestamped upgrades, downgrades, initiations, reiterations, and
  price-target changes;
- original rating wording plus a separately versioned normalization;
- analyst firm, action type, magnitude, freshness, and source;
- timestamped company/industry news sentiment, relevance, novelty, and topic;
- explicit buy-the-dip or demand/supply narrative indicators only when their
  publication time and licensing permit historical use.

Media lists, free-text recommendations, opaque AI/quant scores, and current
rankings are not truth labels. They may be tested as a separately ablated
feature family only when the original historical value, methodology,
timestamp, and usage rights are reproducible.

### 5. Industry demand and supply

- global semiconductor sales and growth;
- memory/HBM pricing, shipments, inventory, and supply constraints;
- advanced-packaging and foundry capacity/utilization;
- hyperscaler capital spending and AI-infrastructure guidance;
- custom-ASIC, networking, accelerator, and equipment demand indicators.

Every macro or industry series needs a conservative public-availability date.
Later revisions must not replace the vintage originally available.

### 6. AI-stack role and cross-sectional context

Use a dated taxonomy such as memory, GPU/accelerator, custom ASIC/networking,
foundry, design software, and semiconductor equipment. Compare names within
and across roles, but do not treat the taxonomy as a return label. Include
same-day cross-sectional ranks and model disagreement so the system can avoid
concentrating five nominally different picks in one identical risk factor.

### 7. Market structure and risk

- market and semiconductor bull/bear/mixed regime features;
- valuation levels only when historically point-in-time and comparable;
- short interest, institutional positioning, and public unusual-call features
  when their availability contract is proven;
- earnings-gap risk, volatility, correlation, concentration, liquidity, and
  estimated slippage.

## Horizon-specific hypotheses

- **1 session:** emphasize current premarket state, very recent news, technical
  reset/rebound context, and proximity to a catalyst. Do not use a result
  released after the one-session exit.
- **5 sessions:** explicitly model whether the holding window crosses earnings
  or another binary event; combine technical reset with public fundamental,
  guidance, analyst, news, and unusual-call context.
- **20 sessions:** emphasize durable guidance/estimate trends, industry demand,
  relative valuation, market/sector regime, and AI-stack diversification while
  retaining catalyst and technical timing.

These are hypotheses to test, not hard-coded reasons to buy specific symbols.

## Pre-registered experiment

1. Freeze a dated universe and survivorship policy.
2. Freeze the 09:25 decision cutoff, next-open entry, horizon exits, costs,
   missing-data policy, and portfolio capacity.
3. Build separate point-in-time labels for 1, 5, and 20 sessions.
4. Use chronological train/validation/test partitions with horizon-aware
   purging and embargoes.
5. Compare, in order:
   - technical and market context;
   - plus premarket;
   - plus fundamentals/guidance and catalyst calendar;
   - plus analyst/news;
   - plus industry-demand and AI-stack context;
   - plus unusual-call/positioning features.
6. Select thresholds and any ensemble weights on validation only.
7. Report coverage, missingness, calibration, mean/median return, win rate,
   tails, drawdown, turnover, capacity, concentration, and regime stability
   after costs.
8. Open the untouched test once, then freeze the surviving design for
   append-only prospective observation.

The experiment must allow abstention. A model that cannot beat its appropriate
market/sector baseline consistently and prospectively is rejected regardless
of an attractive story or a few spectacular winners.

## Promotion boundary

Historical performance is research evidence only. No model from this design
may affect `engine.py`, paper buying, or live trading without passing
`PAPER_TRADING_PROMOTION_PROTOCOL.md`, completing an immutable prospective
sample, and receiving a separate explicit review.
