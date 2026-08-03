# AI/Semiconductor Narrative Feature Contract

This contract preserves the exact useful logic in Jeff's attached August 3
ranking narrative. The narrative itself, its named picks, quoted prices, media
recommendations, and opaque third-party scores are not training data.

## Hypothesis

An AI/semiconductor stock may rank better when four independently timestamped
conditions agree:

1. Fundamentals, earnings, guidance, or estimates are accelerating.
2. Price has pulled back while the broader trend remains intact.
3. Public industry evidence confirms demand in the stock's AI-stack role.
4. A known catalyst aligns with the intended 1-, 5-, or 20-session horizon.

Analyst revisions, premarket state, market/sector regime, unusual call
activity, liquidity, volatility, and concentration are context or risk
features—not automatic reasons to buy.

## Required structured inputs

- Revenue and EPS surprise versus the consensus known before release.
- Guidance-midpoint revision and subsequent estimate revision.
- Reported AI/data-center/HBM/custom-silicon growth.
- Exact earnings distance and whether each horizon crosses the event.
- Original analyst actions and price-target changes with timestamps.
- Semiconductor sales, HBM/memory trend, hyperscaler-capex revision, and
  advanced-packaging/foundry utilization with conservative availability dates.
- A dated AI-stack role: memory, GPU/accelerator, custom ASIC/networking,
  foundry, equipment, design software, or infrastructure.
- Existing leakage-safe technical and premarket inputs.

Every source record must carry `narrative_available_at_utc`. Data published
after the decision cutoff fails closed. Missing values remain explicit.

## Learned interactions

The feature layer exposes, without assigning ticker-specific weights:

- pullback in an intact uptrend;
- oversold state in an intact uptrend;
- earnings crossing each separate horizon;
- count and agreement of positive fundamental and demand components;
- analyst upgrade agreement with positive estimate revision;
- AI-stack role indicators.

Separate 1-, 5-, and 20-session models learn their own weights. AMD, MU, AVGO,
TSM, NVDA, or any other name receives no boost because it appeared in the
source narrative.

Implementation:
`alientai_v2/research/ai_semiconductor_narrative_features.py`.
