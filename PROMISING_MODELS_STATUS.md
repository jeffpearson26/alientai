# AlienTAI Promising Model Register

Generated: 2026-08-12 06:05 Pacific (morning source/readiness refresh)
Schema-v3 completion correction: 2026-08-11 17:17 Pacific
Purpose: permanent morning operating list for every legitimate research lead.
Safety: prospective research evidence remains separate from execution. Only the
Nasdaq-101 technical baseline is explicitly authorized for the local V2 paper
account; no model is authorized for live trading.

The automatically refreshed data-family and coverage matrix is
`PROMISING_MODEL_DATA_INVENTORY.md`.

## Paper control panel (August 7)

The V2 paper control panel now has exactly one enabled and buy-authorized
engine: `nasdaq100_complete_101_baseline_v1`. All other paper-model entries and
buy allowlists are disabled; all live/real-trading flags remain false. The
engine uses the immutable 101-symbol file, model/report hashes, frozen
`0.20886314398519493` cutoff, complete source-pure Schwab payloads, at most five
daily candidates, and one-share initial entries. New positions carry a hard
1% stop from their original entry and a 5% trailing stop. An existing selected
position may add exactly one share no more often than every five minutes only
when its current price is above both the original entry and a quote sampled at
least five minutes earlier; the account cash and exposure caps still apply.

The app is loopback-only at `http://127.0.0.1:8010/v2/monitor` and its engine is
running. Paper-entry windows are premarket, regular market, and the standard
after-hours session through 17:00 Pacific; no paper entry is allowed after that
time. The first scan at 12:58 Pacific correctly returned `AVOID`: no current
paper payload was written because 46/101 frozen Schwab histories contain
duplicate source sessions (ADBE, AMD, GOOGL, GOOG, and AMZN are the first five
examples). Existing positions from removed engines remain in the paper account
for orderly management, but those engines cannot open or add positions. Paper
trades, add-ons, stops, and P/L must never be merged into the append-only
prospective journal or cited as model-validation evidence.

## August 7 storage incident

The external AlienTAI SSD was absent from Windows during the 04:31, 05:31,
06:31, and 08:31 Pacific passes and remained absent at 10:32 Pacific. It was
restored as healthy `D:` storage with more than 832 GiB free before 10:51
Pacific. Because `data_v2` and the immutable D-drive artifacts were
unavailable during the frozen morning cutoffs, no August 7 daily or Schwab
09:35-entry observation may be backfilled. Existing valid earlier journals
and their pending outcomes remain intact.

The interrupted full-Nasdaq Alpha Vantage adjusted-daily collector resumed
from its exact manifest after duplicate-process, disk, source, and credential
checks. It reached all 6,247 frozen symbols with 6,245 completed files, 2
explicitly unavailable symbols, and 0 failures. Its independent audit passed
as `PASS_WITH_EXPLICIT_GAPS`: 5,775 current files, 470 provider-stale symbols,
and one ten-year-eligible coverage gap, all preserved without substitution.
The singular five-minute queue initially failed before provider access because
its recovery command referenced a nonexistent seed alias. It was safely
restarted with the exact independently audited 8,137-request five-minute seed;
no five-minute payload or contract was altered. At the 11:31 Pacific
verification, the production contract remained singular and healthy. Jeff
then explicitly cancelled it at 12:43 Pacific because the measured completion
estimate was too long. All queue/collector launcher and child processes are
stopped. The preserved partial archive has 3,027/749,640 requests accounted
for (830 completed, 2,197 explicitly unavailable, 0 request failures, and
746,613 pending). Nothing was deleted or relabeled complete; the immutable
cancellation record blocks content audit, downstream compilation/training, and
automatic resume without new explicit authorization.

## Primary models

| Priority | Frozen model | Universe / horizon / inputs | Best honest evidence | Current testing state | Exact reason if not advancing |
|---:|---|---|---|---|---|
| 1 | Autonomous transparent Nasdaq-101 champion | 101 securities; 20 sessions; 126/60-session QQQ-relative momentum + inverse 60-session volatility | Frozen validation: 825 signals, +2.3893% mean, 55.88% wins, -4.9230% drawdown. One-time sealed test: 590 signals, +3.1682% mean, 55.59% wins, -6.0750% drawdown; all four observable non-overlap cohorts positive. | **OUTCOME PENDING; AUGUST 11 ATTEMPT BLOCKED WITH EVIDENCE** | August 4 selections FTNT, DDOG, PANW, CSX, and CRWD remain pending. The exact 103-symbol universe includes EA; a completed source-pure Alpha adjusted-daily archive reports EA only through August 4 while its peers reach August 11. The complete-101 scorer therefore cannot form an August 11 panel and writes no observation. |
| 2 | Technical context + unusual calls | Natural universe; 5 sessions; technical score then unusual call buying | First completed prospective date: 5 signals, 80% wins, +1.8944% mean, +3.0803% median. Historical fixed slices were positive at three chronological splits. | **NEW AUGUST 11 OBSERVATION; EARLIER OUTCOMES PENDING** | BX, APTV, and GEN were frozen before the August 12 open from 479/479 technical rows and 479/479 nonempty option rows. Every scored row has 20 prior call observations; 17 source-manifest exclusions were explicitly unavailable and zero common-universe rows were missing. Earlier August 4 and August 5 selections remain pending. |
| 3 | Nasdaq-101 baseline | 101 symbols; 5 sessions; technical | Historical untouched top 0.25%: 20 rows, 70% >=10% winners. First completed prospective date: 2 signals, 100% wins, +6.7067% mean. | **PAPER ENABLED; AUGUST 11 PAPER/RESEARCH OBSERVATION BLOCKED WITH EVIDENCE** | The Schwab token refresh succeeded and 1,065 append-only rows brought active files through the August 11 session, but 46/102 required Nasdaq-plus-QQQ files still contain a conflicting duplicate stored session. The paper adapter and unchanged prospective journal fail closed; no payload or order is created. Earlier missed dates are never backfilled. |
| 4 | Nasdaq-101 QQQ-relative | 101 symbols; 5 sessions; technical + QQQ-relative context | Historical untouched top 0.10%: 8/8 >=10% winners; top 0.25%: 65%. First prospective date: 2 signals, 50% wins, +2.3750% mean. | **AUGUST 11 ATTEMPT BLOCKED WITH EVIDENCE** | The same 46/102 conflicting Schwab source files prevent a complete source-pure August 11 observation. No source substitution, row splicing, or retrospective journal is allowed. |
| 5 | AI/semi 20-minute technical + premarket | 17 symbols; 09:30 entry to 09:45 close; prior technical + 09:25 premarket | 20 held-out days, 28 trades, 70% positive days, +0.52% mean daily net, +10.62% compounded, -4.56% drawdown. | **BLOCKED BY ORIGINAL SOURCE/TIMING CONTRACT** | Alpha Vantage lacked entitled pre-entry realtime data and its 09:25 interval is not complete before the frozen 09:30 entry. Cannot be repaired without a separately frozen timing/source model. |
| 6 | AI/semi 60-minute technical + premarket + calls | 17 symbols; 09:30 to 10:25; prior technical/calls + 09:25 premarket | 20 held-out days, 28 trades, 65% positive days, +0.70% mean daily net, +14.28% compounded, -5.70% drawdown. | **BLOCKED BY ORIGINAL SOURCE/TIMING CONTRACT** | Same Alpha Vantage 09:30-entry impossibility. Preserve frozen evidence; use the separate Schwab late-entry variants prospectively. |
| 7 | Schwab late-entry 60-minute calls | 17 symbols; 09:35 to 10:30; Alpha prior technical/calls + Schwab 09:25 premarket | Untouched: 28 trades, 57.14% wins, +0.6325% mean, +11.2514% compounded, -5.7230% drawdown. Prospective: 4 trades across 2 dates, 50% wins, +1.0013% mean net, +1.9507% compounded, -1.4876% drawdown. | **OUTCOME COMPLETE; NEXT ATTEMPT NEXT VALID DAY** | August 6 KLAC gained +4.3827% net and AVGO gained +2.5978% net; both won. Cohort 1 is collecting at 2/20 dates, and the evidence gate remains unmet. |
| 8 | Schwab late-entry 60-minute premarket | Same 17-symbol 09:35 program without call feature family | Untouched: 56 trades, 51.79% wins, +0.3895% mean, +4.6607% compounded, -7.1860% drawdown. Prospective: 8 trades across 2 dates, 75% wins, +2.0367% mean net, +4.0593% compounded, -0.3193% drawdown. | **OUTCOME COMPLETE; NEXT ATTEMPT NEXT VALID DAY** | August 6 KLAC +4.3827%, ANET +2.7359%, AMAT +3.7342%, and MU +6.7180% net were all winners. Cohort 1 is collecting at 2/20 dates; this two-day sample is far too small for promotion. |
| 9 | AI/semi one-session narrative earnings context | 17 symbols; 1 session; technical + premarket + point-in-time earnings context | Exploratory frozen comparison: 37 selections, 62.16% wins, +0.7476% mean, +0.5398% median. | **BLOCKED BY ORIGINAL ALPHA TIMING CONTRACT** | Exact August 5 daily technical data is ready, but the Alpha 09:25 interval cannot be verified as a complete all-17 source-pure panel before the frozen 09:30 entry. At 06:31 Pacific that entry was already observable, so no August 6 observation may be backfilled. |
| 10 | AI/semi technical + premarket | 17 symbols; 5 sessions | Validation-locked historical test: 31 selections, +1.7260% mean, -0.0638% median, 48.39% wins. Separate journal has 4 pending observations across 2 dates. | **OUTCOME PENDING; NEW-DAY ATTEMPT BLOCKED BY TIMING** | The same Alpha 09:25-before-09:30 timing impossibility blocked a valid August 6 observation. Existing pending outcomes remain intact; Schwab data is used only by the separately frozen 09:35 study and is not spliced into this model. |
| 11 | Nasdaq-80 champion | 80 symbols; 5 sessions; QQQ-context technical | Corrected historical test: 12 trades, +2.8700% mean, +1.6163% median, 58.33% wins. | **OUTCOMES PENDING; AUGUST 11 ATTEMPT BLOCKED WITH EVIDENCE** | PLTR and QCOM observations remain pending. The refreshed Schwab archive reaches the August 11 session, but 42/80 frozen-universe files retain a conflicting duplicate stored session, so the complete-universe attempt fails closed rather than dropping or replacing rows. |

## Secondary promising leads currently parked

| Model | Evidence | Why parked |
|---|---|---|
| Nasdaq two-stage QQQ-relative | 23 historical confirmation positions, +7.1350% mean, 73.91% wins, +36.20% capital-scaled return, -15.16% drawdown | Confirmation period was already reused and the model was inferior to the simpler QQQ-relative challenger. |
| Nasdaq 10-session clone | 57 test trades, +1.5204% mean, 56.14% wins, +15.40% capital return | -23.09% drawdown exceeded the fixed limit; observed test cannot be retuned. |
| Nasdaq top-10-company clone | 16 test trades, +2.1923% mean, 56.25% wins, -3.19% drawdown | Far too few trades for promotion or priority prospective capacity. |
| Selective two-session large-move head | 57 test rows, +0.8709% mean, 57.89% wins | AUC weakened from 0.6506 validation to 0.5705 test; not yet frozen into a prospective program. |
| Corrected Nasdaq-80 two-session model | 12 trades, +5.6345% mean, +3.8915% median, 83.33% wins | Sample is only 12; preserved as a fragile lead rather than treated as established. |

## Development and future-test candidates without prospective evidence yet

- Nasdaq small-cap range/volume baseline clone, 5 sessions: this isolated
  setup keeps model 3's frozen LightGBM artifact, 22-feature order, 5-session
  horizon, `0.20886314398519493` cutoff, five-position cap, and 0.25% cost;
  only the candidate universe changes. The preserved Nasdaq listing has 6,247
  active listings: 4,952 stocks and 1,295 excluded ETFs. The screen requires
  market cap below $2 billion, close below $50, relative volume at least 2.0,
  EMA-aligned uptrend, and ATR(14) at least 3% of price. **BLOCKED WITH EXACT
  EVIDENCE:** source-pure Schwab technical and same-cutoff market-cap snapshots
  for all 4,952 stocks do not exist, so no partial universe or observation was
  written. It inherits none of the Nasdaq baseline's performance evidence.
  The earlier all-market scope was superseded with zero observations.
- Calibrated first-passage barrier model, 10 sessions: the corrected
  source-pure Alpha Vantage build covers 48 liquid names and estimates a
  conservative/optimistic probability interval for reaching +1.5% before
  -0.5% from the next open. Its 188,667-row panel and saved text models passed
  independent audits. Every frozen development gate passed; the one-time
  29,516-row sealed test retained AUC `0.54999` and `+0.6156%` Brier skill for
  the conservative bound, AUC `0.60775` and `+3.7183%` Brier skill for the
  optimistic bound, with calibration errors `0.00828` and `0.01251`.
  **Future test: ACTIVE; FIRST CALIBRATION OUTCOME PENDING.** A fresh
  source-pure compact archive for the August 11 decision passed independent
  audit for all 48 symbols, with 100 common dates through exactly August 11
  and zero failures. The immutable snapshot scored and append-only journaled
  all 48 probability intervals before the next open. The highest conservative
  bounds were KO `25.7491%`, WMT `25.7491%`, PEP `25.6075%`, ABBV `25.0965%`,
  and BAC `25.0965%`. Every row remains `AVOID`; outcomes may resolve early or
  after the full ten-session timeout. This is probability evidence, not a
  validated trade-return policy.
- S&P 500 calibrated first-passage barrier clone, 10 sessions: the isolated
  496-identity Alpha Vantage clone passed its 1,914,495-row independent panel
  audit with 7,629 feature recomputations and zero errors. Every frozen
  policy-validation gate passed. Its one-time 303,572-row sealed test retained
  conservative-bound AUC `0.53282`, Brier skill `+0.3276%`, calibration error
  `0.00195`, and positive date-cluster Brier-improvement CI; the optimistic
  bound retained AUC `0.60414` and Brier skill `+3.5283%`. The independent
  model audit rescored all 303,572 sealed predictions with zero errors.
  **Future test: ACTIVE; FIRST CALIBRATION OUTCOME PENDING.** The August 11
  source-pure snapshot journaled 486 eligible probabilities before the next
  open. Nine terminal historical constituents explicitly abstained, and ANSS
  abstained because its frozen ADX feature was unavailable. The maximum
  conservative bound was `23.4558%`; BXP had the highest optimistic bound
  within that tied conservative tier at `40.3839%`, followed by UPS and GS at
  `39.5122%`. All rows remain `AVOID`; this is probability calibration
  evidence, not a validated trading policy or profitability finding.
- Corrected external LambdaRank 120-stock ranker, 20 sessions: the immutable
  `v2` panel passed an independent 75,000-row/625-date content audit, and its
  purged out-of-fold development gate passed with `0.08552` mean Rank IC,
  `+3.4520%` mean net across the exact top-10 policy, and 20/20 positive
  non-overlap rotations. This is promising development evidence only: the
  fixed current universe has survivorship bias and the sample begins in late
  2023. The future test is unopened. Its first prospective snapshot is
  blocked by provider data, not authorization: the renewed Schwab session
  completed all 121 requests with zero HTTP failures but returned two
  conflicting rows for the August 6 session on every series. The duplicate
  session is unusable and no observation was written. August 6 was still
  inside the frozen cutoff, so no eligible decision was missed. Retry after
  the provider payload settles; require one unambiguous completed candle for
  all 121 series and never backfill.
- Source-pure Alpha Vantage LambdaRank clone candidate, 20 sessions: the exact
  120-stock universe plus SPY has a source-pure full adjusted archive and an
  independently audited leakage-corrected `v2` model using adjusted OHLC and
  raw point-in-time volume. Development passed over 497 dates with Rank IC
  `0.06197`, exact top-10 `+2.0230%` mean net, `+1.4517%` median, and
  `56.34%` wins. Its one-time 130-date sealed test passed with Rank IC
  `0.08305`, top-10 `+5.1226%` mean net, `+2.7377%` median, `57.00%` wins,
  and all 20 non-overlap rotations positive. **Future test: ACTIVE; FIRST
  OUTCOME PENDING.** The first eligible observation was created after the
  August 11 close and before the August 12 entry. Its fresh source-pure compact
  archive passed the independent audit for all 121 required series, with 100
  common dates through exactly August 11 and zero failures. The frozen top-10
  ranking is MU, ARM, AMAT, INTC, ACN, ADBE, AMZN, FTNT, BSX, and INTU. The
  observation is append-only, research-only, and enters at the next complete
  regular-session adjusted open; its outcome remains pending until the
  twentieth subsequent regular-session adjusted close. Fixed-universe bias,
  overlap, and adjusted-history revision risk mean this is promising evidence,
  not established profitability.
- Approved Alpha Vantage/Schwab fallback routing: Jeff authorized either
  provider when rows are missing, duplicated, or conflicting. The 120-stock
  LambdaRank route is ready because both providers have separately identified,
  independently audited models and journals. Nasdaq-101 baseline,
  QQQ-relative, and Nasdaq-80 remain `ALTERNATE_CLONE_REQUIRED`; their
  Schwab-trained models will not be fed Alpha rows. Provider rows are never
  spliced. An unfrozen historical test may exclude an unusable final date and
  end on the prior complete session, but frozen/prospective horizons are never
  shortened.
- Defined-risk options-volatility picker: strategy layer, explicit policy,
  readiness safeguards, and exact point-in-time multi-leg fill compiler exist;
  learned direction/move heads and full chronological backtest are pending.
- Any-time one-minute Nasdaq-101 horizon clones (5/10/20/30/60/90 minutes):
  both the 8,137-request archive and its independent 82,425,431-row content
  audit are complete. Schema v3 corrected executable-time labels, exit
  timestamps, gap handling, abstention, calibration/policy separation, and
  genuinely unloaded sealed tests. The earlier schema-v2 full 20-minute run is
  immutable `RESEARCH_HOLD` (best validation -0.2238% mean net, 38.84% wins;
  test sealed). All six schema-v3 5/10/20/30/60/90-minute variants completed
  in separate horizon-specific panel and model roots and returned
  `RESEARCH_HOLD`. For the 60- and 90-minute variants, each panel completed
  7,512 shards with zero failures for the exact 101-symbol universe, schema
  version 3, nanosecond timestamps, `next_minute_open` entry, and
  `exit_bar_close` targets. Neither policy-validation stage passed, so both
  sealed tests remain unopened and unloaded. No compiler or trainer is
  currently running.
- Any-time one-minute AI/semiconductor-17 horizon clones
  (5/10/20/30/60/90 minutes): the separate 869-request supplement is complete
  and independently audited (793 valid files, 76 unavailable, 10,412,846 rows,
  zero orphans). Exact combined coverage is 79/79 accounted months for every
  one of the 17 symbols. All six corrected 5/10/20/30/60/90-minute variants
  completed and returned `RESEARCH_HOLD`; every sealed test remained unloaded.
  Each horizon has separate immutable panel/model roots. These remain negative
  development evidence, and live-source compatibility validation is pending.
- Five-day catalyst-momentum model: explicitly excluded from this promising
  list because its typical held-out selection lost money; status remains
  `RESEARCH_HOLD`.
- Multi-resolution Nasdaq-101 ranker, 5 sessions: 72-date panel and all
  LightGBM/XGBoost ablations completed. The strongest requested
  daily+five-minute+calls slice had +1.4217% mean across 336 selections, but
  rank IC was -0.04984 and the date-clustered lower 95% bound was -0.3216%.
  Status is `RESEARCH_HOLD`; the sealed test is unopened.
- Multi-resolution S&P ranker, 5 sessions: 92-date panel and all
  LightGBM/XGBoost ablations completed. The comparable LightGBM slice had
  +0.0834% mean, -0.3658% median, 46.30% wins and -0.04994 rank IC. Status is
  `RESEARCH_HOLD`; the sealed test is unopened.
- Multi-resolution 20-session clones: Nasdaq has 72 and S&P has 92 common
  point-in-time dates, below the frozen 120-date minimum. Both are visibly
  `BLOCKED_INSUFFICIENT_HISTORY`; no misleading fit was run.
- Multi-resolution timestamped-news ablation: only 36 Nasdaq and 30 S&P dates
  meet their coverage thresholds, below 60 required. Missing news was not
  treated as no news.
- Daily-only Nasdaq-101 technical + call-options ranker, 5 sessions: the
  independently audited panel contains 72 dates and exactly 101 candidates per
  date; QQQ/SPY are context-only. The strongest LightGBM call-enhanced slice
  had +1.7547% mean, +0.5134% median, and 52.98% wins across 336 development
  selections, but rank IC was -0.04921 and the date-clustered lower 95% bound
  was -0.0891%. Status is `RESEARCH_HOLD`; the sealed test is unopened.
- Daily-only S&P technical + call-options ranker, 5 sessions: the independently
  audited panel contains 92 dates and exactly 483 candidates per date. Its
  daily-technical baseline was stronger than the call-enhanced versions, but
  still had negative median return and rank IC. Status is `RESEARCH_HOLD`; the
  sealed test is unopened.
- Daily-only 20-session rankers: Nasdaq has 72 and S&P has 92 common
  point-in-time call-history dates, below the frozen 120-date minimum. Both
  are `BLOCKED_INSUFFICIENT_HISTORY`; neither was fit. These variants read no
  intraday, premarket, after-hours, or news source.
- Pure daily-technical Nasdaq rankers: the 5-session XGBoost slice had positive
  basket statistics but missed the frozen 0.01 rank-IC gate at 0.00794, so its
  test remains sealed. The 20-session LightGBM/XGBoost slices passed
  development strongly, then both failed the once-opened May 20-July 7 sealed
  test: -4.4546% and -3.9485% mean, respectively, with negative rank IC and
  sub-40% win rates. Both horizons are `RESEARCH_HOLD`; no retuning is allowed.
- Pure daily-technical S&P rankers: both 5- and 20-session horizons produced
  negative development means, medians, and rank IC. Both are `RESEARCH_HOLD`
  and their sealed tests remain unopened.
- External clean-rank S&P-120-style 20-session model: the bundled 220,753
  prediction rows independently reproduce +0.04851 mean daily Rank IC and
  +1.5449% top-minus-bottom spread. Its latest chronological fold remains
  positive across all 20 non-overlapping offsets. It is parked as
  `PROMISING_EXTERNAL_LEAD / NOT VALIDATED`: the label enters at an
  unexecutable same close, costs are absent, exact purge audit found 4-7
  overlapping training dates in folds 2-5, the universe is hand-selected, and
  no sealed test exists. See `EXTERNAL_CLEAN_RANK_MODEL_AUDIT_20260806.md`.

## Morning rules

1. Refresh this file every valid market morning before any decision cutoff.
2. Never call a model active merely because an old outcome is still pending.
3. Every promising frozen model must show one state: new observation,
   abstention, pending outcome plus a new-day attempt, not scheduled, or exact
   blocker.
4. A pending horizon never prevents the next eligible frozen observation.
5. Immediately surface missed windows, stale journals, missing files, empty
   provider payloads, credentials, or timing conflicts.
6. Preserve frozen models and all prior observations; never backfill or retune.
