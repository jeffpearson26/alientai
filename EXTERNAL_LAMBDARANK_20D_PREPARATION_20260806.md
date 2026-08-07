# External LambdaRank 20-session preparation

Date: 2026-08-06
Status: `READY_FOR_FUTURE_ONLY_TEST`, but the first observation is blocked by
stale Schwab inputs and an expired credential.

## What was supplied

Jeff supplied `D:\Downloads\lambdarank_ready.zip`, SHA256
`dcfcd7e3403d93842ec732b2b8a46d99cf71fe8e15176ff7c1041299d94aff4d`.
The source archive is preserved untouched at
`D:\AlientAI\ExternalModels\lambdarank_ready_dcfcd7e3403d`.

The bundled `lambdarank_20d_champion.joblib`, SHA256
`44ad9f72ed26f749c759977fba082e5d7ca656cc36b5d71e7b75b345534c1e91`,
was never loaded. Joblib/pickle is executable serialization, and the package
did not include a trusted provenance or feature-schema manifest.

## Defects corrected before testing

- Replaced same-close entry with next-session-open entry.
- Set the exit to the twentieth subsequent regular-session close.
- Applied the frozen 0.25% round-trip cost.
- Replaced approximate calendar purging with exact label-interval purging and
  a 20-session embargo.
- Corrected the relevance labels to five populated within-date buckets.
- Removed silent Yahoo failures and required the complete 120-name
  cross-section.
- Unified training and scoring feature calculations.
- Removed fallback retraining from the scorer.
- Replaced unsafe joblib output with a LightGBM text model plus hashed JSON
  metadata.
- Added a freeze-date guard so no already-observable date can enter the future
  journal.
- Separated immutable training panels from daily prospective feature
  snapshots.
- Corrected the two Schwab date schemas. Files with
  `schwab_symbol/datetime` use the stored Pacific key plus one calendar day;
  files with `datetime_ms/datetime_utc` use the stored U.S. session date with
  no offset. Same-provider component merges require exact overlap equality.

The first corrected development run that applied the wrong universal
plus-one-day mapping is preserved under superseded D-drive roots and is not
valid evidence. The controlling model is the isolated `v2` artifact below.

## Controlling implementation and artifacts

- Frozen universe:
  `research_universes\external_lambdarank_120_20260806.txt`
- Shared feature/label contract:
  `alientai_v2\research\external_lambdarank_20d.py`
- Panel builder and independent audit:
  `build_external_lambdarank_20d_panel.py`,
  `audit_external_lambdarank_20d_panel.py`
- Development trainer and independent audit:
  `train_external_lambdarank_20d.py`,
  `audit_external_lambdarank_20d_model.py`
- Future snapshot and scorer:
  `build_external_lambdarank_20d_snapshot.py`,
  `score_external_lambdarank_20d.py`
- Panel:
  `D:\AlientAI\Data\Compiled\external_lambdarank_120_h20_corrected_v2_20260806`
- Model:
  `D:\AlientAI\Models\external_lambdarank_120_h20_corrected_v2_20260806`

The content audit passed 77,400 feature rows across 645 complete dates and
75,000 labeled rows across 625 complete dates. It independently reproduced
every next-open/twentieth-close net label with maximum numeric error
`1.42e-14`, verified all source hashes, and verified five overlap-free purged
folds.

## Development-only results

These are purged out-of-fold development results, not a sealed historical
test and not proof of profitability:

- Mean daily cross-sectional Rank IC: `0.08552` across 625 dates.
- Exact top-10 policy: 6,250 selections, `+3.4520%` mean net,
  `+2.0525%` median net, and `57.968%` positive selections.
- Top-20% mean net: `+2.9402%`.
- Bottom-20% mean net: `+0.2819%`.
- Top-minus-bottom mean spread: `+2.6583%`.
- All 20 sequential non-overlap rotations were positive.

The independent model audit passed. The safe LightGBM text artifact SHA256 is
`f0fe683ab493e2d210a320d0f7b416ff88d17103d5d88093499aae704e7fa15b`.
The future test remains `NOT_STARTED`; the package's advertised holdout was
already exposed and was not reused as a sealed test.

## Important limitations

- The 120 stocks are a fixed contemporary universe, creating material
  survivorship and selection bias.
- The complete chronology begins in December 2023 because all 120 current
  names are required. Much of the sample is a favorable equity regime.
- Strong development results can therefore be optimistic. Only new,
  genuinely prospective observations can determine whether the signal
  survives.
- This is research only, with `execution_decision: AVOID`.

## Exact blocker and recovery

The model was frozen on 2026-08-06, so its first eligible decision date is
later than 2026-08-06. The primary 120-name Schwab files currently end at the
2026-08-05 session, while TSM ends at 2026-07-07 after a duplicate 2026-07-08
source session was excluded. The future snapshot builder correctly refuses to
create a partial observation.

The existing Schwab token was saved at 2026-08-06 08:33 Pacific with a
30-minute access lifetime. Its automatic refresh now returns HTTP 400. Jeff
must complete a fresh Schwab authorization. After authorization:

1. Append completed daily candles through the decision session for all 120
   candidates and SPY, including a new primary TSM file.
2. Run `build_external_lambdarank_20d_snapshot.py` before the next-session
   entry.
3. Require exactly 120 candidates, a current SPY context series, complete
   source hashes, and no attached outcomes.
4. Run `score_external_lambdarank_20d.py` and append the observation before
   entry.
5. Evaluate only after that observation's twentieth subsequent regular-session
   close. Never backfill a missed decision date.
