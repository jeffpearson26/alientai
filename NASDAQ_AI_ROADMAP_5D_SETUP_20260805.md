# Nasdaq-100 + AI Semiconductor Five-Day Roadmap Model

Status: `SETUP_COMPLETE_DATA_BLOCKED`

Execution enabled: `false`

## Exact model contract

This is a separate research-only setup for Jeff's supplied practical roadmap.
It does not inherit the earlier fixed-104-universe technical model's evidence,
model weights, threshold, or failed policy-validation result.

- Candidate universe: quarterly point-in-time Nasdaq-100 membership union the
  22 explicitly named AI-semiconductor stocks.
- Current reference union: 103 securities; TSM and ON are the two overlay
  names outside the current 101-security Nasdaq file.
- Decision: after a completed regular-session close.
- Entry: next complete regular-session adjusted open.
- Exit: fifth subsequent complete regular-session adjusted close.
- Cost: 0.25% round trip.
- Selection policies: top 15% and top 20%, maximum 15 selections.
- Models: transparent composite, LightGBM absolute-return regressor, and
  LightGBM cross-sectional-rank regressor.
- A sequence model and ensemble may be added only if out-of-fold sequence
  predictions add independent value on validation.
- Test discipline: whole-date chronological stages, overlap purge, five-session
  embargoes, calibration-only policy choice, and at least a 12-month sealed
  holdout.

The machine-readable source of truth is
`nasdaq_ai_roadmap_5d_contract.json`.

## Mandatory inputs

The model requires all of the following before panel construction or training:

1. Full split/dividend-adjusted daily OHLCV.
2. Quarterly point-in-time Nasdaq-100 membership.
3. Technical, momentum, oscillator, volatility, volume, trend, and same-date
   cross-sectional features.
4. Relative context versus Nasdaq-100/QQQ, SMH, SOXX, and NVDA.
5. VIX level and changes.
6. Point-in-time revenue growth, EPS growth, gross margin and margin trend, and
   earnings beat/miss streaks.
7. A point-in-time earnings calendar supporting days-to-next-known-earnings.

Short-interest change, prior-session options implied move, and timestamped
FinBERT headline sentiment remain optional additions exactly as stated in the
roadmap. Their absence cannot be disguised as a numeric zero.

## Current blockers

The first exact readiness audit correctly fails closed:

- no dated quarterly Nasdaq-100 membership table exists;
- the full adjusted Alpha Vantage archive lacks TSM and ON;
- SMH, SOXX, and VIX full daily context is absent from the source-pure model
  archive;
- complete point-in-time fundamental and known-earnings-calendar tables do not
  yet exist for the exact universe.

The existing fixed-universe technical panel cannot substitute for these inputs
without changing the requested model and reintroducing survivorship bias.

## Safety

The setup cannot place paper or live orders. It does not modify `engine.py`,
`data_v2\v2_settings.json`, any frozen model, or any prospective journal. The
readiness audit exits nonzero until every mandatory content and timing check
passes.
