# Five-Stock Large-Cap AI Infrastructure QQQ Clone

Date: 2026-08-03

Status: `RESEARCH_PROMISING_SECTOR_REGIME_NOT_MODEL_PROOF`

## Frozen universe

- NVDA
- AVGO
- AMD
- MU
- AMAT

The universe was frozen before training. All five already existed in the
source-consistent complete Nasdaq QQQ-relative archive, allowing a clean clone
without introducing a new price source or rebuilding labels after observing
results.

## Contract

- Input: 2,230 rows sliced from the 44,620-row QQQ-relative panel.
- Features: the identical 28 point-in-time technical and stock-minus-QQQ
  relative-return features.
- Target: gross five-session return of at least 10%.
- Split: train through 2025-10-13; validation 2025-10-25 through 2026-02-22;
  untouched test from 2026-03-06.
- Embargo: 12 calendar days.
- Portfolio: at most five concurrent positions.
- Cost: 0.25% round trip.

## Model behavior

The LightGBM model stopped at iteration 1 and produced only seven distinct
validation scores. A new tie-expansion guard rejected the nominal 5% and 10%
fractions because their score cutoffs selected 4.86 and 2.49 times the intended
row counts. The 20% fraction passed the fixed 1.5 maximum at 1.26.

Validation locked the 20% fraction:

- 40 capacity-limited signals
- +0.403883% mean net return
- +0.726920% median net return
- 52.50% net wins

The untouched test then produced:

- 50 signals
- +5.186912% mean net return
- +4.241945% median net return
- 76.00% net wins
- +59.328065% capital-scaled return
- -15.706655% maximum drawdown
- zero label-alignment error

## Required interpretation

The numbers are promising, but they do not prove that the model learned a
durable selector. A simple capacity-limited equal-weight version of all five
stocks was stronger during validation: 70 signals, +1.744935% mean net,
+1.010438% median, and 54.29% wins. Its later diagnostic period also gained,
with 70 signals, +2.750605% mean net, +3.318778% median, and 58.57% wins.

Therefore much of the apparent edge is a large-cap AI semiconductor sector
regime. The model enriched the already-observed test period, but it did not
beat the simple universe baseline during validation and its one-iteration,
low-resolution scores are weak evidence of stock-level intelligence.

Preserve both the frozen 20% model policy and the equal-weight five-stock
control for future-only comparison. Do not enable execution or retune from the
observed test.
