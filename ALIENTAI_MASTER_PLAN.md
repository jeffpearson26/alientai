# AlienTAI Dynamic Master Plan

Last updated: 2026-08-02 Pacific time

## Purpose and authority

This is the durable, ordered roadmap for AlienTAI. Every AI task or chat working on this repository must read this file after `AGENTS.md` and before proposing, planning, or performing AlienTAI work.

This file is the source of truth for:

- the order of planned work;
- the current direction and priorities;
- dependencies and safety gates;
- what is active, blocked, completed, deferred, or cancelled;
- why the plan changed.

`CODEX_CONTINUATION_INSTRUCTIONS.md` contains detailed operational handoff information. If it conflicts with this file about roadmap order or current direction, stop, inspect current project evidence, and reconcile both files with Jeff before proceeding.

## Mandatory maintenance rules

1. Read the entire plan at the start of every AlienTAI task.
2. Inspect current Git state, live processes, logs, manifests, and relevant outputs before trusting a status recorded here.
3. Update this plan whenever Jeff adds work, removes work, changes direction, changes priority, or makes a decision that affects later phases.
4. Keep phases in the intended execution order. If the order changes, update the phase numbers and add a dated entry to the change log.
5. Do not silently delete old ideas. Mark them `DEFERRED` or `CANCELLED` and record why.
6. Do not mark a phase `COMPLETE` without evidence. Record the validating command, report, commit, or artifact.
7. Add newly discovered blockers and dependencies immediately.
8. Before ending a material work session, update the status, immediate next actions, and change log.
9. Never place secrets, API keys, OAuth data, broker credentials, or private token contents in this file.
10. This plan does not override the write-authorization, trading-safety, data-preservation, testing, or Git rules in `AGENTS.md` and `CODEX_CONTINUATION_INSTRUCTIONS.md`.

## Status vocabulary

- `ACTIVE`: work is currently underway or is the immediate next phase.
- `PLANNED`: approved direction, not yet started.
- `BLOCKED`: cannot proceed until a stated dependency or decision is resolved.
- `ONGOING`: recurring responsibility with no single completion date.
- `COMPLETE`: finished and verified with recorded evidence.
- `DEFERRED`: intentionally postponed but retained in the roadmap.
- `CANCELLED`: no longer planned, with the reason preserved.

## Mission and non-negotiable direction

Build AlienTAI as a research-first system that identifies a very small number of unusually strong five-trading-day stock opportunities. Optimize for honest out-of-sample evidence, calibrated probabilities, realistic trading costs, strict leakage prevention, tail-risk awareness, and reproducible results. Never promise profitability.

Real trading and new paper buying remain disabled unless Jeff explicitly requests a later review and activation after the evidence and safety gates are satisfied.

## Current project snapshot

- Canonical repository: `C:\Users\jeffp\alientai_start_over_8010`
- Canonical branch: `main`
- Active data directory: `data_v2`
- Large external archive: `C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026`
- External SSD structure: `D:\AlientAI`
- Verified SSD backup created 2026-07-20: `D:\AlientAI\Backups\alientai_start_over_8010_2026-07-20`
- Expected user-owned dirty state at plan creation:
  - modified `data_v2/v2_settings.json`
  - untracked `overnight_training_queue_summary.json`
- AlienTAI application and engine launch processes were running when this plan was created. Live state must always be rechecked.
- Data-source policy (Jeff direction, 2026-07-30): use Alpha Vantage as the default source for all new collection, feature construction, and research experiments. Existing Schwab-based artifacts, including frozen prospective studies, remain source-isolated and must finish or remain pending against their original Schwab archive; never splice Alpha Vantage candles into them.

### August 2 verified priority reset

The project has produced many useful historical diagnostics. Further model
proliferation is now lower value than collecting honest forward evidence.
Until the next roadmap review, active predictive work is limited to:

1. the frozen Nasdaq five-session prospective comparison;
2. the six frozen AI/semiconductor 20- and 60-minute prospective models; and
3. the frozen five-session technical-context plus unusual-call study.

Do not start another model family merely because these journals need time.
Complete the deterministic stratified-news archive and its exact-key timing
audit in parallel, then run only its already specified chronological ablation.

Verified blockers and state on August 2:

- The full repository test suite passes: 611 tests, zero failures.
- The stratified news request list contains 22,918 exact keys. Its prior process
  was interrupted at 11,246 completed, zero unavailable, and zero failed while
  its manifest incorrectly remained `running`. It was controlled-resumed after
  confirming no matching Python process and adequate external-drive space.
- Alpha Vantage previously failed the current-session 09:25 ET requirement
  because the account returned delayed intraday data. Faster Internet does not
  remove this entitlement/timing blocker. Every morning run must verify
  freshness and fail closed rather than substitute or estimate.
- Prospective evidence remains sparse: four pending complete-101 Nasdaq
  observations, one pending frozen-80 observation, two pending
  AI/semiconductor five-day observations, five completed contextual-options
  observations from one date, and no completed six-model intraday cohort.
- No model is eligible for paper promotion. Historical results may prioritize
  forward tests but may not replace the frozen prospective gate.
- The local application server is stopped. `paper_trading_enabled` remains true
  in the preserved settings file, while options paper buying is false. Do not
  restart the server until the restart boundary checks enabled engines, payload
  freshness, positions, limits, and rollback behavior.

### August 3 intraday prospective readiness

- The prior-session inputs for the six frozen AI/semiconductor intraday models
  are prepared for the August 3 decision date. The July 31 technical panel has
  all 17 frozen-universe symbols with zero missing rows.
- Alpha Vantage July 31 historical option chains completed for all 17 symbols
  with zero unavailable or failed requests. The compiled option and
  prior-session call-feature panels each contain the same exact 17 symbols.
- The continuous research automation now runs at 05:26, 06:26, 08:26, and
  14:26 Pacific on market weekdays. It advances the frozen daily journals
  pre-open, scores the six frozen intraday models after the 09:25 Eastern
  cutoff, evaluates complete intraday outcomes, and advances matured daily
  outcomes after the close. It preserves sequential cohorts indefinitely and
  cannot retune or trade. Its only unavoidable intraday dependency is a fresh
  Alpha Vantage response containing all 17 current-session premarket series
  through exactly 09:25 Eastern, followed by complete 09:30-10:25 bars.
- Four conflicting legacy Windows tasks scheduled from 06:00 through 06:31
  Pacific were disabled: Morning Research, V2 Server Start, Daily Mover
  Universe Scan, and V2 Engine Start. This preserves the research-only boundary
  and prevents API contention or an accidental engine restart.
- The separate stratified-news collector is stopped fail-closed at 15,745
  completed, 3 unavailable, and 1 failed request
  (`AZO|2026-04-27T20:00:00+00:00`) after a redacted `ChunkedEncodingError`.
  It is not a dependency of the August 3 six-model intraday run. Do not restart
  it before the morning run or without first rechecking its manifest and logs.
- Verification evidence: 13 targeted intraday/options tests passed; the seven
  involved scripts compiled; `git diff --check` passed. No settings, trading
  state, model artifact, or engine code changed.
- Claude is now an external participant in the prospective pick competition.
  `build_claude_competition_packet.py` creates a single uploadable ZIP from an
  exact complete-universe, prior-session panel while excluding model outputs,
  other participants' picks, labels, and outcomes. The August 3 packet contains
  all 101 symbols and only July 31 prior-close technical evidence; Jeff
  explicitly excluded premarket data. Claude's response must still be frozen
  before the normal deadline and scored under the identical rules.

## Ordered master roadmap

### Phase 0 - Governance, continuity, and safety

Status: `ONGOING`

Planned work:

1. Use this file as the authoritative dynamic roadmap.
2. Keep `AGENTS.md` as the mandatory entry point for every new task.
3. Keep `CODEX_CONTINUATION_INSTRUCTIONS.md` current for operational handoffs, active jobs, commands, and evidence.
4. Preserve single-task write ownership so two AI tasks never modify AlienTAI or control collectors/trainers simultaneously.
5. Preserve local safety state in `data_v2/v2_settings.json` and the user artifact `overnight_training_queue_summary.json`.
6. Keep real trading and new paper buying fail-closed.
7. Never expose or commit `.env`, OAuth tokens, broker credentials, API keys, or private datasets.
8. Use small, intentional Git changes and verify every claimed result.

Done when: This phase remains continuously enforced; individual continuity or safety improvements may be marked complete in the change log.

### Phase 1 - Finish and verify the current research-data harvest

Status: `COMPLETE`

Current direction: Jeff explicitly authorized continued use of the existing Alpha Vantage premium key on 2026-07-21. A safe check confirmed the active key is present in the ignored `.env`, `.env` is not Git-tracked, and the key is absent from all Git history. The prior local error log and backup copy remain sanitized; the credential-safe HTTP correction remains in force.

Verified review on 2026-07-20:

- No Alpha Vantage master queue or child collector is currently running.
- Master queue Phase 1 completed successfully in the latest attempts.
- Master queue Phase 2 completed successfully.
- Fundamental manifest: 9,806 completed, 6,868 unavailable, 0 failed, status `complete`.
- Market-regime archive: 26 files plus its manifest, status `complete`.
- Phase 3 matched premarket archive is complete: 10,245 completed plus 44 unavailable equals all 10,289 deduplicated requests.
- Phase 3 historical options is incomplete: 2,763 of 2,951 requests completed, 0 unavailable, 1 recorded temporary failure, and 188 requests not yet complete.
- Phase 3 event news is incomplete: 3 pilot requests completed out of 1,518 expected, leaving 1,515.
- Phase 4 transcripts have not run at full scope: 3 pilot requests completed out of 600 expected, leaving 597.
- Master queue Phases 5 and 6 have not started in the latest queue attempt.
- The options manifest stored a redacted error, but the redirected Python traceback did not protect the credential.
- All eight Alpha Vantage collectors now use one credential-safe HTTP helper that converts Requests transport failures into sanitized, non-chained exceptions before they can reach redirected logs.
- New tests simulate HTTP 503 and connection failures and verify that rendered tracebacks contain neither the key nor a credential-bearing query URL.
- The ignored local error log and its external-SSD backup copy were replaced with non-secret incident notices. A credential scan of all logs in both locations found zero remaining copies of the active key. The log was not tracked by Git and was not present in the OneDrive Alpha Vantage archive.
- System drive free space was 11.2 GB; this is above the current collector floors but leaves little margin for later expansion.

Planned work, in order:

1. Inspect whether the Alpha Vantage master queue or any child collector is currently running.
2. Read the latest manifests and logs; do not trust old handoff counts.
3. Verify completion and failure classification for the existing queue phases:
   - Phase 1: historical options, earnings, estimates, shares outstanding, and institutional holdings;
   - Phase 2: financial statements, company overviews, and market-regime archive;
   - Phase 3: matched extended-hours history, historical option chains, and event news;
   - Phase 4: point-in-time earnings transcripts.
4. Treat rate limits and temporary provider failures as resumable failures, not permanent unavailability.
5. Resume a collector only when no matching master process exists.
6. Verify archive integrity, free-space floors, resumability, duplicate handling, and manifest totals.
7. Record final counts, unavailable reasons, failed items, storage use, and completion evidence.
8. Use the existing authorized key already present in `.env`; do not print, move, copy, or commit it.
9. `COMPLETE 2026-07-20`: Make HTTP and traceback logging credential-safe across every Alpha Vantage collector, then add regression tests proving logs and stored errors cannot contain the key.
10. After the security fix, resume the master queue once. The collectors must skip completed and unavailable requests and retry the temporary options failure.

Dependencies: Existing premium API access, OneDrive availability, enough free archive space, and no duplicate collector process. Credential-safe collector error logging and legacy-log sanitization are complete.

Done when: All intended requests are completed, correctly classified as unavailable, or recorded as actionable failures; manifests and logs agree; no duplicate queue is running.

### Phase 2 - Validate premarket and supporting data coverage

Status: `ACTIVE`

Planned work:

1. Run or verify the Alpha Vantage master queue Phase 5 premarket feature build only after its queue Phase 3 inputs are complete.
2. Audit coverage by year, symbol, winner/control role, and event date.
3. Audit bar counts, missing prior closes, sparse trading, and zero-volume bars.
4. Verify exchange-local timestamps and enforce the 09:25 Eastern feature cutoff.
5. Detect corporate-action anomalies and invalid price or volume records.
6. Validate the supporting fundamental, earnings, news, transcript, options, short-interest, insider, and regime datasets before joining them.
7. Produce a concise coverage and data-quality report with exclusions and unresolved gaps.

Dependencies: Phase 1 data harvest and manifests.

Done when: Coverage is quantified, timestamp rules are verified, anomalies are documented, and invalid or incomplete rows have an explicit handling policy.

### Phase 3 - Audit leakage-safe prediction labels and decision timing

Status: `PLANNED`

Planned work:

1. Audit the separate premarket-decision target created by `build_matched_premarket_labels.py`.
2. Confirm entry uses the first regular-session five-minute bar close.
3. Confirm exit uses the final regular-session bar on `future_market_date`.
4. Exclude missing entry or exit history instead of labeling it negative.
5. Verify that no feature or label gives credit for movement before the simulated entry.
6. Add realistic slippage, round-trip costs, and timestamp availability checks.
7. Document the availability timestamp for every feature family.

Dependencies: Phase 2 coverage audit.

Done when: Labels, entry/exit timing, costs, exclusions, and feature-availability rules pass targeted tests and manual spot checks.

### Phase 4 - Build compact, keyed feature-family joins

Status: `PLANNED`

Planned work:

1. Use compact feature tables keyed by `study_event_id`, symbol, and timestamp.
2. Avoid repeatedly materializing the existing large base research rows.
3. Join feature families in controlled stages:
   - technical price and volume;
   - premarket movement and relative volume;
   - earnings history and estimate revisions;
   - point-in-time news sentiment;
   - point-in-time transcripts;
   - insider open-market purchases;
   - short interest;
   - historical option positioning;
   - market regime;
   - fundamental interactions.
4. Add an unusual-options-and-catalyst feature table. The completed matched-event archive already preserves point-in-time chain fields (volume, open interest, strike, expiration, bid/ask/last/mark where available, implied volatility, and Greeks) for all 2,951 research-event requests. It is sufficient for cross-sectional positioning features, but not for a contract's prior-volume baseline. After Phase 2 data audit, plan a separate resumable, point-in-time historical option-chain collection with prior snapshots per symbol/contract and documented public availability timing before claiming an "unusual versus history" feature.
5. Define outcome labels before testing: stock returns at 1, 3, 5, and 10 trading days; option outcomes at fixed horizons and expiration; maximum gain and drawdown; and estimated costs. Do not infer that an options pattern proves insider knowledge or unlawful conduct.
6. Add a point-in-time lead-lag feature table. Test whether an abnormal move in one symbol adds information about another symbol at 1, 2, 3, 5, or 10 trading-day lags beyond the target's own history, broad market, sector, and known catalyst context.
7. Preserve source provenance, availability timestamps, missingness indicators, and schema versions.
8. Add tests for duplicate keys, row loss, timestamp leakage, unintended future joins, and invalid lead-lag look-ahead.
9. Preserve a deferred AI/semiconductor multi-horizon catalyst design for
   separate 1-, 5-, and 20-session targets. Candidate inputs are point-in-time
   technical momentum/pullback/volatility and relative strength; premarket gap,
   relative volume, and directional pressure through 09:25 ET; known earnings
   proximity; publicly timestamped earnings/guidance, estimate revisions,
   analyst actions, and news; broad/sector regime; and structured
   supply-chain, memory, foundry, networking, and hyperscaler-capex context.
   Use only facts available before the decision cutoff, retain explicit
   missingness, and evaluate each feature family through chronological
   ablations. Opaque third-party scores, media recommendations, free-text
   rankings, unsupported price claims, and post-entry catalyst reactions are
   not labels or ground truth. The complete frozen proposal is in
   `FUTURE_AI_SEMICONDUCTOR_MULTI_HORIZON_MODEL.md`.

Dependencies: Phases 2 and 3.

Current join blockers found in the 2026-07-21 schema audit: the premarket feature and label tables align to all 18,326 composite matched-study rows; the current historical-option feature table contains 1,837 rows from a different, smaller matched study; the current fundamental snapshot table is a July 2026 cross-sectional snapshot rather than event-time history; and the transcript archive contains current 2026 Q1 symbol snapshots rather than transcripts tied to historical event dates. These outputs must not be joined to the 2022-2026 premarket study as if they were complete historical features. Build exact-scope, point-in-time feature tables first.

Point-in-time news progress: the completed Alpha Vantage archive compiles into 1,518 event-time rows, with 1,438 rows containing at least one usable article. The compiler filters publication times at or before each request's `as_of_utc`; the remaining study rows must remain explicitly missing rather than being silently imputed.

Done when: Reproducible compact joins pass integrity and leakage checks without generating unnecessary giant duplicate datasets.

### Phase 5 - Run staged feature-family ablation experiments

Status: `PLANNED`

Planned work, in order:

1. Reproduce the technical baseline.
2. Evaluate premarket features alone.
3. Evaluate technical plus premarket features.
4. Add catalyst data: news, earnings, and transcripts.
5. Add options and short-interest features.
6. Add fundamentals and market-regime interactions.
7. Retain insider-purchase signals as interaction features unless broader evidence supports more weight.
8. Evaluate unusual-options positioning around known catalysts against matched controls. Require the result to survive controls for earnings timing, market/sector movement, the underlying's own momentum, liquidity, and option-expiration structure; treat findings as market-behavior associations, not evidence of insider trading.
9. Evaluate lead-lag relationships with rolling chronological windows, multiple-testing controls, market/sector residualization, and expiry rules for relationships that stop working.
10. Compare identical chronological train, validation, and untouched test periods.
11. Report exceptional-winner rate, calibrated precision, mean and median net return, win rate, fifth-percentile loss, worst trade, drawdown, turnover, concentration, and sample size.
12. Promote a feature family only when it improves untouched validation and test evidence, not merely training metrics.

Dependencies: Phase 4 feature tables and Phase 3 label audit.

Done when: Each staged experiment has reproducible artifacts and a documented keep, revise, or reject decision.

### Phase 6 - Apply the premarket promotion gate and natural-universe evaluation

Status: `PLANNED`

Planned work:

1. Run the matched-case premarket ablation gate as a feature-family comparison, not as a natural-universe probability claim.
2. Require the combined model to independently beat the technical baseline on validation and test exceptional-winner rate and mean net return.
3. Require a positive median net return, at least 30 top-1% signals, and no worse fifth-percentile loss.
4. On `RESEARCH_HOLD`, stop expansion, diagnose the evidence, and update this plan before changing direction.
5. On `RESEARCH_PASS`, run Alpha Vantage master queue Phase 6 natural-universe collection and compact feature/label generation.
6. Calibrate all comparison models on natural-universe rows.
7. Evaluate untouched, chronological, cost-adjusted test slices with embargoes and whole timestamps.
8. Preserve the rule that a research pass permits ranking and journaling only; it cannot enable orders.

Dependencies: Phase 5 and the fail-closed promotion gate.

Done when: The promotion decision and natural-universe results are reproducible, calibrated, cost-adjusted, and explicitly separated from matched case-control evidence.

### Phase 7 - Build and validate the rare-signal selector

Status: `PLANNED`

Planned work:

1. Optimize for a few outstanding opportunities rather than a high signal count.
2. Allow multiple simultaneous signals only when each independently meets the same stringent standard.
3. Calibrate probabilities on the natural universe.
4. Evaluate top-score fractions, probability thresholds, and minimum sample sizes.
5. Report mean, median, win rate after costs, tail loss, drawdown, turnover, symbol concentration, sector concentration, and regime stability.
6. Add fail-closed handling for sparse samples, calibration drift, missing data, and out-of-distribution conditions.
7. Select thresholds only from training and validation evidence; preserve the final test period.

Implementation update (2026-07-22): `alientai_v2/research/rare_signal_gate.py` now provides a reusable, fail-closed research gate. It requires a minimum signal count, positive cost-adjusted mean and median return, at least a 50% cost-adjusted win rate, acceptable fifth-percentile and worst-trade losses, constrained cohort drawdown, and limited single-symbol concentration. `evaluate_natural_options_panel.py` and `evaluate_unusual_call_outcomes.py` attach the gate and its explicit failure reasons to every future report. A `RESEARCH_PASS` remains historical research evidence only; it cannot enable a paper or live order.

Implementation update (2026-07-26): `FIVE_DAY_SELECTIVE_CATALYST_STRATEGY.md` preregisters an isolated future challenger architecture using calibrated positive-return and large-move probabilities, expected and lower-quantile net returns, technical/options agreement, and model-disagreement abstention. `alientai_v2/research/selective_five_day_policy.py` implements only its fail-closed scored-row contract. It requires a complete same-day universe and validation-frozen thresholds, keeps zero, one, or several independently qualifying candidates, and always emits `decision="AVOID"`. It does not train, score, contact providers, modify settings, or execute. It does not alter the controlling frozen contextual-options prospective study.

Label implementation update (2026-07-26): `alientai_v2/research/five_day_open_close_labels.py` defines the challenger's executable timing contract: decide after the current close, enter at the next regular-session open, and exit at the fifth regular-session close. It subtracts the configured round-trip cost and emits positive-net and large-move labels only for complete, valid, continuous price windows. It skips invalid prices or excessive calendar gaps and rejects unsorted/duplicate dates. It is a pure builder and is not yet connected to a trainer or dataset.

Panel implementation update (2026-07-26): `alientai_v2/research/selective_five_day_panel.py` defines the challenger's exact-key feature/label boundary. It requires matching unique symbol/decision-date keys, timezone-aware feature availability and decision-cutoff timestamps, availability no later than the cutoff, valid future label timing, and explicitly required feature fields. It rejects outcome/label fields on the feature side to block accidental leakage from existing combined research panels. It is a pure in-memory join and has not rewritten an archive or started training.

Training update (2026-07-26): Jeff explicitly directed training of the isolated challenger. `train_selective_five_day_challenger.py` used only the existing 44,683-row point-in-time natural technical/options panel and 483 local Schwab daily histories. It materialized 44,116 corrected next-open-to-fifth-close examples, with 26,340 train rows, 5,753 validation rows, 5,787 untouched test rows, and two 12-calendar-day embargoes. The fixed pre-test policy required calibrated positive probability at least 0.60, calibrated large-move probability at least 0.30, expected net return at least 0.75%, and lower-quantile net return at least -5.0%, after 0.25% cost. The positive-return classifier stopped at iteration 1; validation calibration never exceeded approximately 0.4872. Therefore the untouched test produced zero qualifying candidates. The final report fingerprints the source panel, combined local daily archive, and all four model files. Status is `RESEARCH_HOLD`; do not lower thresholds or reuse the observed test to tune this model.

Validation diagnostic update (2026-07-26): `audit_selective_challenger_validation.py` inspected only the frozen validation partition and explicitly did not inspect the test partition. The positive-return classifier had AUC 0.4834 and no useful rank ordering. The large-move classifier had AUC 0.5670; its validation top 1% contained 57 rows with 64.91% large-move frequency, +8.800797% mean net return, +5.503135% median, and 75.44% post-cost wins. The expected-return and lower-quantile regressors had negative validation correlations (-0.0232 and -0.1205). This identifies large-move classification as the only component worth a materially new preregistered future-period challenger; it does not authorize removing failed gates or evaluating another rule on the observed test.

Premarket implementation update (2026-07-26): Jeff directed adding premarket movers to the model. The trainer now supports `premarket_*` columns and an optional exact-key `--premarket-features` input. `alientai_v2/research/selective_premarket_features.py` enforces the 09:25 ET cutoff, preserves explicit missingness, requires exact natural-universe keys, and blocks `study_*` winner/control metadata. The only current premarket feature table is the biased matched study: it overlaps 3,350 of 44,683 natural rows (7.4973%) and is therefore forbidden for this training run. Do not retrain with premarket until a complete, point-in-time natural-universe panel exists.

Natural premarket collection update (2026-07-26): Jeff explicitly directed downloading the premarket data required for the selective five-day challenger. One credential-safe, resumable Alpha Vantage collector is running against the exact 44,683-row natural options/technical panel (483 symbols, 2026-01-02 through 2026-07-02). It has 3,381 deduplicated symbol-month requests and writes only to `D:\AlientAI\Data\AlphaVantage_2026\selective_natural_premarket_5min_2026`, with a 20 GB free-space floor. After successful completion, build an exact-key 09:25 ET feature table, verify full key coverage and explicit missingness, then retrain the isolated challenger with `--premarket-features`. Do not substitute the biased matched-study premarket table.

Natural premarket continuation result (2026-07-26): the focused archive completed 3,367 of 3,381 requests with 14 explicit unavailabilities and zero failures. The optimized compiler produced all 44,683 exact natural keys, with valid premarket features for 44,371 rows (99.302%). A cost-adjusted next-open-to-fifth-close continuation audit found that a moderate premarket gap of at least 1% retained a positive mean in validation (+0.6776%, 786 rows) and untouched test (+0.6261%, 860 rows), with a 53.60% test win rate. Larger gaps were not monotonically better: at least 5% lost -1.3397% on average in untouched test with a 33.33% win rate. Treat premarket movement as a nonlinear model feature and possible interaction with liquidity/technical context, never as a standalone momentum rule.

Same-day premarket continuation result (2026-07-26): the strict 09:25-decision study used the first 09:30 five-minute bar close as entry, the 16:00 bar close as exit, and deducted 0.25% round-trip cost. It labeled 44,484 rows and excluded 199 missing/nonstandard sessions. The >=1% gap cohort changed from +0.1922% mean / 51.56% wins in validation (803 rows) to -0.3514% / 43.12% in untouched test (886 rows). The >=5% test cohort was positive but had only 44 rows and contradicted the negative training result. Therefore same-day premarket continuation is rejected as a standalone rule; retain the features only for nonlinear/contextual model interactions.

Premarket challenger retrain result (2026-07-26): the isolated LightGBM challenger successfully joined all 44,116 labeled rows after explicitly excluding the same 567 source rows without valid local five-day labels. Premarket expanded the matrix from 72 to 114 columns. The frozen promotion policy still selected zero untouched-test candidates and the run remains `RESEARCH_HOLD`; no trading path changed.

Two-day model comparison (2026-07-26): the next-open label contract and isolated challenger now support an explicit `--horizon-sessions 2` without changing the five-day default. All four current challenger heads trained on the same 44,116 labeled rows and 114 technical/options/premarket columns. Fixed top-10%, top-5%, and top-1% slices were declared before the one-time test read. The large-move classifier was the only head with a directionally consistent top-1% result: validation 57 rows, +0.8623% mean / 50.88% wins; untouched test 57 rows, +0.8709% mean / 57.89% wins. Its AUC fell from 0.6506 validation to 0.5705 test, so this is a lead, not promotion evidence. The profit classifier, expected-return regressor, and lower-quantile regressor were inconsistent or weak. Status remains `RESEARCH_HOLD`; do not use the observed test to retune thresholds.

Two-day shadow policy update (2026-07-26): froze a validation-only large-move score cutoff of 0.3647459048971379, corresponding to the validation top 1%, with a minimum complete-universe coverage of 95%. The policy is `SHADOW_OBSERVE_ONLY`, has no candidate quota, fingerprints the exact model, and explicitly prohibits paper/live orders, incomplete-universe scoring, matched-study substitution, and threshold retuning on the observed test. The next valid evidence must come from newly arriving future dates.

Two-day prospective scorer update (2026-07-27): `score_selective_two_day_shadow.py` now applies the frozen policy to a single future market date only. It rejects mixed dates and duplicate/blank symbols, fails closed below 95% expected-universe coverage, retains every independently qualified candidate without a quota, fingerprints the model through the policy, and can emit only `SHADOW_OBSERVE_ONLY` records with execution disabled.

Multi-horizon pullback research update (2026-07-27): added point-in-time features for Jeff's trend-plus-dip hypothesis. The setup measures log-price slopes across 20, 63, and 126 trading sessions, distance from each horizon mean, pullback depth from 5/10/20-session highs, one/five-session returns, and 20-session volatility. Research eligibility requires all three slopes positive, price above the 126-session mean, a 1%-12% pullback from the 20-session high, and a negative five-session return. This is an eligibility/feature contract only; it cannot buy or create orders. Train and compare two- and five-session recovery labels after the active Russell Transformer finishes.

Two-day Transformer isolation update (2026-07-26): created and validated `train_v2_transformer_2day_sp500_from_supabase.py` from the established 20-day architecture without overwriting any 20-day or five-day artifacts. The isolated build fixes the horizon at two trading sessions, uses a one-session sampling step, 12-calendar-day split embargo, four-calendar-day non-overlap evaluation, separate build/output/artifact names, and the existing three-way chronological/scaler/checkpoint safeguards.

Two-day Transformer result (2026-07-27): the full 496-symbol CPU run completed 2,233,585 windows (1,104,724 train / 552,390 validation / 568,704 untouched test). Validation selected epoch 2 at the frozen 0.55 threshold: 1,966 signals and +0.234609% mean net return. That result did not replicate: untouched test produced 1,929 signals, -0.121585% mean net return, 48.8854% cost-adjusted wins, and 0.909755 profit factor; the non-overlapping test subset averaged -0.124948%. The two-day Transformer therefore fails and remains research-only. Do not promote or retune it on this observed test.

Two-day Russell Transformer preparation (2026-07-27): the legacy Russell trainer was rejected because it lacks an untouched test, embargo, cost-adjusted checkpoint selection, and scaler isolation. Instead, `train_v2_transformer_2day_russell_from_supabase.py` is generated from the validated two-day S&P pipeline and retains its safeguards while isolating Russell build/output/artifact names. Use a full-universe screening run with a three-session sampling step and three epochs before considering an exhaustive one-session/five-epoch run.

Two-day Russell Transformer result (2026-07-27): the full 1,909-symbol screening pass produced 879,971 windows (496,776 train / 188,251 validation / 192,280 untouched test); many stale/listed-history symbols had no matching candle data. Epoch 2 won the valid >=1,000-signal checkpoint at threshold 0.55, but its edge was negligible in validation (+0.021583% mean net) and reversed in untouched test (-0.021745%, 48.5507% cost-adjusted wins, 0.985305 profit factor across 31,499 signals). The non-overlapping test mean was -0.020699%. This fails the screening gate, so do not run the exhaustive Russell Transformer or promote/integrate this model.

Dependencies: Phase 6 natural-universe evaluation.

Done when: A selector specification and frozen evaluation report demonstrate honest performance and acceptable risk across untouched periods and regimes.

### Phase 8 - Run prospective shadow ranking and journaling

Status: `ACTIVE`

Planned work:

1. Deploy the approved selector in shadow mode only.
2. Record every eligible signal, rejected signal, model version, feature version, timestamp, price assumption, and reason code.
3. Measure prospective outcomes with the same entry, exit, slippage, and cost rules used in research.
4. Monitor calibration, drift, data outages, latency, concentration, tail losses, and regime changes.
5. Compare prospective results with frozen backtest expectations.
6. Define minimum duration and sample size before any paper-trading review.
7. Run a small, isolated TradingAgents-inspired qualitative review experiment on AlienTAI-selected candidates:
   - use it only after AlienTAI's statistical selector has produced a candidate;
   - treat its bull, bear, catalyst, and risk output as a recorded second opinion, never as predictive proof or permission to trade;
   - prevent the qualitative layer from overriding AlienTAI scores, gates, position limits, or fail-closed controls;
   - provide fixed, point-in-time AlienTAI data snapshots instead of allowing uncontrolled live data retrieval during historical evaluation;
   - require the same decision timestamp, entry, exit, slippage, cost, and outcome rules used by AlienTAI;
   - compare shadow outcomes with and without the qualitative review before retaining any influence;
   - selectively adapt only useful patterns such as checkpoint resume, structured reports, decision journaling, and deterministic data verification;
   - do not merge the full TradingAgents repository or its dependency stack into AlienTAI;
   - preserve Apache 2.0 license notices and attribution for any adapted code;
   - independently fix and test credential-safe HTTP error handling rather than copying its Alpha Vantage request wrapper.

Dependencies: Phase 7 and intact fail-closed gates.

Done when: The required prospective period and sample size are complete and an evidence-based review is documented.

### Phase 9 - Decide whether to consider limited paper trading

Status: `BLOCKED`

Blocker: Requires successful completion of Phase 8 and a new explicit decision from Jeff.

Planned work if unblocked:

1. Review prospective evidence, drawdowns, tail risk, calibration, operational reliability, and failure modes with Jeff.
2. Define strict capital, position, daily-loss, concentration, kill-switch, and rollback limits.
3. Start with the smallest reasonable paper-only scope.
4. Preserve independent monitoring and fail-closed behavior.
5. Never infer permission for real trading from permission to paper trade.

Done when: Jeff explicitly approves a documented paper-trading protocol, or this phase is deferred or cancelled.

### Phase 10 - Evaluate structured analyst-rating data

Status: `BLOCKED`

Blocker: No approved licensed structured analyst-rating feed.

Planned work:

1. Review Benzinga Ratings API pricing and terms with Jeff; do not purchase anything automatically.
2. Consider other provenance-safe structured sources if available.
3. Preserve announcement time, firm, analyst, action, original rating wording, normalized score, price-target changes, currency, importance, and analyst accuracy when licensed.
4. Never infer structured upgrades from headlines when a structured source is available.
5. Archive raw and normalized events with resumable windows and provenance.
6. Add analyst events through the Phase 4-to-6 validation path before they can influence the selector.

Done when: Jeff approves a source and the data passes provenance, timestamp, coverage, and out-of-sample value tests, or the feature family is formally deferred.

### Phase 11 - Strengthen storage, backup, and recovery

Status: `ONGOING`

Planned work:

1. Maintain verified backups on `D:\AlientAI` without copying secrets to an unencrypted removable drive.
2. Create repeatable backup and restore verification procedures.
3. Decide whether the external SSD should be encrypted before any credential-bearing backup is allowed.
4. Relocate old archives from the constrained system drive only after copy verification and explicit approval.
5. Consider relocating large active datasets only with a tested path strategy, safe shutdown procedure, and rollback plan.
6. Preserve OneDrive research archives and manifests.
7. Periodically test that a backup can be read and restored without long-path loss.

Dependencies: Physical SSD availability and explicit approval for destructive moves or encryption decisions.

Done when: Backups are repeatable, verified, documented, appropriately protected, and no single storage device is the only copy of critical work.

### Phase 12 - Maintain testing, documentation, and release discipline

Status: `ONGOING`

Planned work:

1. Update tests with every behavior change.
2. Run targeted unit tests, compilation checks, and `git diff --check` before claiming completion.
3. Keep architecture, data schemas, feature availability, experiment decisions, and operational procedures documented.
4. Commit only intended files after inspecting the staged diff.
5. Preserve user-owned runtime changes and never use broad staging commands.
6. Update this master plan and the continuation instructions at every material handoff.
7. Record completed phases with evidence rather than removing them from the plan.

Done when: This remains an ongoing standard for all phases.

## Immediate next actions

00. `ACTIVE 2026-08-02`: Accumulate immutable forward evidence for only the
three priority programs listed in the August 2 reset. Preserve model hashes,
universes, thresholds, costs, source identity, and timing. Do not retune after
observing outcomes and do not start additional variants while the journals are
sparse.
00a. Before every AI/semiconductor intraday morning run, require a fresh
Alpha Vantage response containing all 17 symbols through exactly the permitted
09:25 ET cutoff. If the source is delayed, incomplete, or not entitled, record
the failure and stop. Do not fill the gap from Schwab without a separately
frozen source-specific protocol.
00b. Controlled-resume the 22,918-key stratified news archive only when no
matching collector exists. Completion requires completed plus unavailable to
equal 22,918 with zero failures, regardless of the manifest status string.
After genuine completion, compile, exact-key join, timing-audit, and run only
the predeclared chronological ablation.
00c. Keep port 8010 stopped until a read-only restart review confirms exact
enabled engines, current positions, daily limits, stale-payload rejection,
loopback binding, control authorization, and a rollback plan. Starting the
monitor is not itself permission to create new paper orders.

0. `ACTIVE 2026-07-30`: Run a separate, research-only headline-news ablation without changing the frozen contextual-options study or any paper/live setting. Use a deterministic 48-date, complete-natural-universe sample from the existing January-July 2026 FINRA/options panel; collect point-in-time news only for that sample, validate timestamp coverage, then compare identical technical/options baselines with and without news using chronological partitions and validation-frozen selection. The earlier 2,131-request news archive is too early-period-concentrated for this test. Do not mix the result with the frozen prospective study or promote it to trading.
0a. For new work, prefer Alpha Vantage raw archives and record the source in every report. Schwab is retained only for its existing source-isolated frozen studies and historical artifacts; do not begin new Schwab downloads or use Schwab data as a fallback without a new explicit direction from Jeff.
0b. `IMPLEMENTED, ACTIVATION DEFERRED 2026-07-30`: The active quote path now has a native Alpha Vantage `REALTIME_BULK_QUOTES` client and no longer depends on ignored `old_system_reference` source. The launcher is loopback-only, remote `/v2/` mutations fail closed unless `ALIENTAI_CONTROL_TOKEN` is configured, the duplicate root route is removed, and fresh-install ML dependencies are declared. Do not restart the running server or make a competing Alpha Vantage quote request while the stratified news collector is active. After that collector finishes, perform a controlled restart, restore the existing paper-engine state, and validate one bounded quote request without changing positions or settings.
0c. Preserve the legacy `routes/`, patch/fix scripts, and backup-named files until a separate reachability and provenance audit identifies safe quarantine candidates. Their volume is technical debt, but it is not permission to delete user history.

1. Use `PAPER_TRADING_PROMOTION_PROTOCOL.md` as the frozen promotion contract for every future candidate; do not relax it based on observed shadow outcomes.
2. Keep the five-day selective-catalyst challenger isolated while `FROZEN_CONTEXTUAL_OPTIONS_STUDY.md` runs. Do not choose its thresholds, train its component models, or connect it to a daily feed until the required point-in-time feature/label audits are complete and a separately frozen chronological experiment is approved. Its current policy module is a tested decision contract only.
3. Treat the existing five-day LightGBM target-2% result as `RESEARCH_HOLD`: its validation-locked 0.60 threshold yielded only two historical-test signals and -0.895205% average net return after the stated 0.25% cost. The target-3% S&P and Russell target-2% artifacts have encouraging locked-threshold historical results, but their historical test periods are already observed and must not be promoted. Require a separately pre-registered fresh period and realistic portfolio/tail evaluation before any shadow consideration.
4. Before any future Russell experiment, obtain a licensed or otherwise authorized dated constituent snapshot and validate it with `validate_current_universe_manifest.py`; do not reuse the legacy 1,909-symbol list as a current universe. Then construct dated membership/eligibility panels, exclude S&P overlap deliberately, and apply higher small-cap costs before training.
5. A current IWM ETF holdings CSV can be used only as a documented current equity-holdings proxy for prospective coverage checks—not as official historical Russell membership. The iShares automated endpoint returned HTML bot protection on 2026-07-23; use a manually downloaded CSV with provenance if this proxy is needed.
6. The 308-symbol `SPLITS` archive and reconciliation are complete. Keep all 308 flags as review-only evidence: only 2 have a provider date-and-factor match, 9 have a date-only match, and 297 are unmatched. Do not edit source candles, labels, or models; retain this result for the future clean-panel design.
7. The annual Alpha Vantage `LISTING_STATUS` archive is complete at `D:\AlientAI\Data\AlphaVantage_2026\listing_status_annual_2010_2026`: retain its 17 June-30 active-listing snapshots for later survivorship checks, but never treat them as Russell membership.
8. Complete the Phase 2 coverage and timestamp audit across premarket, options, news, transcripts, fundamentals, insider, short-interest, and regime data.
9. `COMPLETE 2026-07-23`: Reconciled completed transcript/premarket unavailabilities through `audit_alpha_vantage_unavailability_policy.py`. Preserve them as explicit missing data: three transcripts (ADSK 2025Q1, AES 2024Q1, AWK 2025Q3) and 44 premarket requests limited to BF.B, BRK.B, COR, and EG. Never zero-fill, substitute current data, or rename archive keys in place.
10. Preserve the premarket promotion gate result as `RESEARCH_HOLD`; do not run natural-universe expansion or enable trading from this matched-case result.
11. `COMPLETE 2026-07-23`: `audit_matched_catalyst_panel.py` verified the full matched catalyst panel has 18,326 unique keys, 13,473 unique symbol/date observations, no duplicate keys, no malformed/as-of-date-mismatched rows, and no news published after its recorded cutoff. It remains matched-case research only; 113 rows have no available option-chain detail and must retain missingness.
12. Audit labels, feature availability, slippage, and cost assumptions before feature-family joins.
13. After the data audit, create the two new research feature families: public unusual-options positioning around known catalysts, and point-in-time cross-symbol lead-lag relationships.
14. `DEFERRED 2026-08-03`: retain the AI/semiconductor 1/5/20-session
multi-horizon catalyst design in Phase 4, but do not train it while the three
August 2 priority prospective programs remain sparse. Before any future run,
freeze the universe, point-in-time cutoff, entry/exit contract, costs,
feature-family ablation order, chronological splits, and promotion gates.

## Current blockers and decisions needed

1. Phase 1 collection completed on 2026-07-21. The next blocker is data-quality and timestamp validation, not missing Alpha Vantage requests. Collector logging correction and sanitization of both known legacy-log copies remain complete and verified.
2. Analyst-rating expansion requires Jeff to review and explicitly approve a structured data source and any purchase.
3. Paper trading remains blocked pending prospective shadow evidence and a new explicit decision.
4. Credential-bearing SSD backups require an encryption decision.
5. Moving active `data_v2` storage requires a tested path, shutdown, and rollback plan.

## Evidence and completion log

- 2026-07-20: Created this dynamic master plan from the existing continuation instructions, current Git state, running-process inspection, and the verified SSD backup work.
- 2026-07-20: Verified SSD backup at `D:\AlientAI\Backups\alientai_start_over_8010_2026-07-20`; approximately 10.65 GB synchronized while excluding `.env`, OAuth token files, `.venv`, Git internals, and caches.
- 2026-07-20: Reviewed Phase 1 against live processes, master logs, queue scripts, request-generation logic, manifests, archive file counts, and free space. Queue Phases 1 and 2 are complete; premarket collection is complete; options, news, and transcripts remain incomplete. The queue was stopped and, at review time, Phase 1 was blocked pending key rotation and a correction for the credential-bearing redirected traceback.
- 2026-07-20: Completed the credential-safe Alpha Vantage HTTP correction across all eight collectors. The shared helper sanitizes and suppresses credential-bearing Requests exception chains; centralized stored-error redaction also removes unknown query-string credentials. Verified with 39 targeted tests, all 249 repository tests, Python compilation of every changed collector and helper, and `git diff --check`. The queue was not resumed; premium-key rotation remained required.
- 2026-07-20: Sanitized the credential-bearing ignored error log in the canonical repository and its copy in the verified external-SSD backup. A scan of every `.log` file in both locations found zero remaining copies of the active key; the sensitive log was not Git-tracked and no copy existed in the OneDrive Alpha Vantage archive. An escalation to Alpha Vantage's official premium-support channel was prepared because premium-key rotation has no documented self-service workflow. The queue remains stopped pending the replacement key.
- 2026-07-21: Jeff authorized continued use of the existing Alpha Vantage premium key. A non-disclosing check confirmed the key is present in ignored `.env`, `.env` is not tracked, and the key is absent from Git history. No Alpha Vantage queue was running and the external SSD had 943 GB free. Phase 1 was returned to `ACTIVE` for a single resumable queue run.
- 2026-07-21: The protected bounded request succeeded with the authorized key. One hidden resumable master queue was launched (PID 7708); its new error log was empty and its output showed completed statements were skipped before the market-regime archive resumed. No duplicate queue was started.
- 2026-07-21: The resumed Alpha Vantage master queue completed with an empty redirected error log. Historical options: 2,951 complete / 0 unavailable; event news: 1,518 / 0; transcripts: 597 / 3; matched premarket: 10,245 / 44; fundamentals: 9,806 / 6,868 / 0 failed; market-regime archive: complete. Phase 5 built 18,326 premarket feature rows (16,970 available) and 18,244 tradable labels. Its premarket promotion gate returned `RESEARCH_HOLD`, so no Phase 6 natural-universe collection occurred and no trading capability changed. Phase 1 is complete; Phase 2 audit is active.
- 2026-07-21: Added and ran the first read-only matched-study coverage audit. It verified 18,326 unique composite study rows; all feature and label rows matched the base study with no row loss; 16,971 premarket feature rows were available (92.606%); 18,244 open-entry labels were available (99.553%); and no recorded premarket feature timestamp exceeded the 09:25 Eastern cutoff. The audit also confirmed that current option and fundamental feature outputs have different scopes and require controlled point-in-time joins before any combined-model experiment.
- 2026-07-21: Inspected raw feature-family schemas. The base study already includes point-in-time technical, short-interest, and insider fields. Premarket rows use the same composite identity and passed cutoff validation. The options output is a 1,837-row smaller matched study, while the July-2026 fundamental snapshot has no event-date identity; neither may be merged into the 18,326-row historical study without rebuilding exact-scope, time-valid feature tables. The harvested news archive contains publication timestamps and ticker sentiment; transcript records require a separate availability-time policy before use.
- 2026-07-23: Verified that the current 319,131-row natural S&P research panel has zero rows with `short_interest_available`. Short-interest fields are schema placeholders, not validated inputs; no short-interest signal may be evaluated or used until an exact-scope, point-in-time historical collection is built.
- 2026-07-23: Identified FINRA Equity Short Interest as the preferred provenance-safe replacement source. Collection must preserve settlement date and publication date separately, use the publication date as the feature availability timestamp, and retain raw source files. FINRA provides historical downloads and an Equity API with up to five rolling years of data; access/terms must be verified before any automated collector is run.
- 2026-07-23: Jeff downloaded 108 official FINRA Equity Short Interest CSVs covering every bi-monthly settlement from 2022-01-14 through 2026-06-30. Raw originals were copied without alteration to `D:\AlientAI\Data\FINRA_Short_Interest\raw`. Added and tested a calendar helper that computes the conservative point-in-time publication date as the seventh U.S. market business day after settlement and matches FINRA's official 2026 examples. Batch normalization remains the next step; no rows are yet joined to research features or execution.
- 2026-07-23: Added and tested `import_finra_short_interest_batch.py`; it normalized all 108 preserved official FINRA files into 2,189,561 research-only rows at `D:\AlientAI\Data\FINRA_Short_Interest\normalized\finra_short_interest_2022_2026.jsonl`. Each row preserves the settlement date and uses a conservative 23:59:59Z timestamp on the verified publication date when intraday publication time is unavailable. No rows have been joined to a model, Supabase, or execution.
- 2026-07-30: Audited an external architecture/methodology critique against the current repository. Confirmed the active quote client depended on ignored legacy source, the dependency manifest omitted core ML packages, `main.py` had two root routes, mutating controls lacked a remote authorization boundary, the launcher exposed the app on all interfaces, and the repository contains substantial legacy patch/backup material. The critique's reported test-suite failure was not reproducible: after the safe correction tranche, focused tests passed and full discovery completed 557 tests with zero failures; Python compilation and `git diff --check` also passed. Added a native credential-safe Alpha Vantage bulk-quote client, a localhost-or-token control boundary, a single public root plus `/api` metadata route, loopback-only launcher binding, dependency declarations, and regression tests. No legacy files, settings, generated research data, positions, collectors, or trading permissions were deleted or changed.
- 2026-07-30: Runtime activation is intentionally deferred. The existing server is still the pre-change process on `0.0.0.0:8010`; its paper engine retains five positions but reports an expired Schwab refresh token. The separate stratified Alpha Vantage news collector remains active with zero recorded failures. Restart only after that collector finishes, then verify the new Alpha quote path and control boundary with bounded local checks before resuming the paper engine.
- 2026-07-30: Completed the five-session outcomes for the frozen July-21 contextual-options pilot after Schwab reauthorization. The append-only refresh added exactly one 2026-07-28 candle to each of TEL, NXPI, CPRT, URI, and TSCO; no historical row was rewritten. Net of the fixed 0.25% round-trip cost, the five records produced 80.00% wins, +1.894382% mean, +3.080338% median, and a -13.815280% worst trade. The required prospective gate remains `RESEARCH_HOLD`: only five completed signals from one decision date exist (minimums are 30 signals across 10 dates), and the five-record fifth percentile was -10.714807%, slightly below the fixed -10% tail limit. The gate evaluator now ignores legacy progress snapshots with zero completed records before checking their source metadata; targeted tests, compilation, and `git diff --check` passed. No trading, settings, model, or threshold changed.
- 2026-07-30: Ran one additional fixed-rule historical check, without threshold search: the independently trained technical model was scored on the natural options panel; the top-5% technical cutoff was set only from rows through 2026-04-01, then applied to the later 2026-04-13 through 2026-07-02 holdout. The holdout had 94 unusual-call-context signals across 41 exit dates, 54.2553% post-cost wins, +1.482190% mean net return, +0.847123% median, -9.141626% fifth percentile, and -16.262023% worst trade. It remains `RESEARCH_HOLD` solely because its older full-notional cohort drawdown metric was -25.957771%; do not use this already-observed holdout to choose a new cutoff or enable trading. The generated report is ignored research output at `data_v2\rcef_research\fixed_context_holdout_top5pct_2026-07-30.json`.
- 2026-07-23: Read-only point-in-time coverage audit against the 44,683-row natural 2026 options panel found a FINRA report already available for 44,500 rows (99.59%). Monthly coverage was similarly high through July. This clears the data-coverage prerequisite for a controlled short-interest feature join, but it is not a signal evaluation or promotion.
- 2026-07-23: Added and tested `build_finra_short_interest_features.py`. It built a compact 44,683-row natural-options short-interest table on the external drive, using only the latest FINRA report published on or before each market date; 44,500 rows were available. The current feature table contains shares, settlement date, publication timestamp, and age. It is research-only and has not been joined to a model or evaluated for predictive value.
- 2026-07-23: Built an exact-key 44,683-row research panel combining existing point-in-time five-day labels, historical options features, and FINRA short-interest features with zero row loss. It is stored on the external drive and is not connected to Supabase, model training, scoring, or execution. The next step is a chronological, locked-specification ablation; no result should be inferred from coverage alone.
- 2026-07-23: Ran the first chronological seven-calendar-day-embargo ablation on the 2026 natural options/FINRA panel using a fixed daily top-1 selection. The technical-plus-options baseline had 20 late-slice signals, +2.349177% mean net return, +0.430547% median, and 60% post-cost win rate. Adding current FINRA short-interest shares/age/availability reduced this to +1.639868% mean, -2.315037% median, and 40% win rate. This small, already-observed exploratory slice rejects FINRA as a standalone additive feature for the current configuration; retain it only for future pre-specified interaction tests. No execution or model integration changed.
- 2026-07-23: Re-ran the same locked, embargoed ablation with correctly scale-normalized FINRA fields (days-to-cover, shares-to-average-volume, reported change, age, availability). The FINRA variant improved median net return to +0.765827% but reduced mean net return to +1.776948% and win rate to 55%, versus the options-plus-technical baseline's +2.349177% mean and 60% win rate. Evidence remains mixed and too small (20 late-slice signals); FINRA stays interaction-only and is not promoted.
- 2026-07-23: Applied the reusable rare-signal gate to both embargoed options ablation variants. Both are `RESEARCH_HOLD`: each has only 20 signals; the technical/options baseline also failed fifth-percentile loss (-16.304757%), approximate drawdown (-35.266522%), and symbol concentration (25%); the FINRA variant similarly failed tail, drawdown, and concentration. Do not optimize thresholds around this already-observed slice or route either result to shadow/paper trading.
- 2026-07-23: Added and ran `audit_natural_panel_integrity.py` against the 44,683-row natural options/FINRA research panel. It found 44,683 unique symbol/date keys, valid future five-day labels, no decision timestamp after market date, and no available FINRA report dated after its decision date. All option rows were available and 44,500 short-interest rows were available. This verifies panel timing integrity only; it does not promote a model or change execution.
- 2026-07-23: Re-verified the SEC Form 4 feature boundary with 23 targeted tests: only open-market purchase code `P` is normalized; future filings are invisible; amendments are deduplicated; and five-day labels use a strictly future close. In the 2026 natural-universe holdout, large purchases in the prior 30 days had 1,110 observations, +0.138114% mean net return, +0.216153% median, and 51.62% post-cost win rate. Cluster buying did not improve typical return. Retain large purchases only as a future pre-specified interaction feature; do not promote either signal standalone.
- 2026-07-23: Re-verified the point-in-time earnings-event evaluator with five targeted tests. Its 2026 later-holdout contained 48 events across 24 symbols and produced -0.512161% average five-day net return, -0.227877% median, and 41.67% post-cost win rate. Large EPS-beat buckets were also negative on this small slice. Do not use earnings surprises as a standalone five-day long signal; retain earnings only as a controlled contextual feature family.
- 2026-07-23: Audited the Alpha Vantage market-regime archive before attempting a historical join. Its macro series retain observation date and value but not original publication time, release vintage, or revision history. Therefore it is not point-in-time eligible for the 2022-2026 backtests and must not be joined by observation date. Retain it for prospective context and obtain a vintage/release-timestamped source before any historical regime ablation.
- 2026-07-21: Built and ran a point-in-time historical-news compiler over the completed archive. It produced 1,518 rows, 1,438 with at least one usable article, and filtered every article at or before the archived request cutoff. No future-dated article was found in this archive. The result remains a partial feature family pending exact-scope coverage and controlled joins.
- 2026-07-21: Audited the transcript archive and collector selection logic. The collected files are current 2026 Q1 transcripts by symbol; the archive does not retain the historical research-event request timestamp or a transcript publication timestamp. It is unsuitable for the 2022-2026 historical study. Any transcript feature requires a separately rebuilt event-time archive using a conservative post-earnings availability policy.
- 2026-07-21: Added and tested a first lead-lag discovery tool using the existing Dow-30 daily library and SPY as a market control. It checks 1/2/3/5/10-session delays, controls for the target's current return, and applies a conservative Bonferroni filter across 4,350 pair/lag tests. Candidate selection now uses only the first two chronological partitions; the third is held out and cannot influence selection. The initial pass selected 270 candidates, of which 265 (98.15%) retained direction in the held-out partition. This remains a research inventory, not a result or a signal: approximate correlation p-values do not resolve serial dependence, sector effects, or economic value.
- 2026-07-21: Built a dedicated 11-ETF GICS sector reference library (47,355 daily feature rows) and added fail-closed static Dow-30-to-sector mappings to the lead-lag tool. The sector-controlled rerun selected 107 candidates, versus 270 with only the SPY control; 106 (99.07%) retained their train direction in the held-out partition. The removed candidates demonstrate why common sector motion must be controlled. The retained list is still a hypothesis inventory, not a model feature or trading signal: the mapping is a current research classification rather than point-in-time GICS history, and rolling-window stability plus economic-value tests remain required.
- 2026-07-21: Added a three-window rolling pre-test stability gate to lead-lag selection. It uses only the first two chronological thirds and requires every rolling pre-test correlation to agree in direction before the final third is inspected. The sector-controlled Dow-30 rerun retained 106 candidates; 105 (99.06%) retained their direction in the held-out partition. This is a stricter screening result, not evidence of profitability; the next gate is a cost-adjusted economic-value simulation with symbol and regime concentration checks.
- 2026-07-21: Ran the required causal, cost-adjusted held-out economic-value check for all 106 sector-controlled, rolling-stable Dow lead-lag hypotheses. The simulation observes the source at its close, enters the later target at its open, exits at that target close, and subtracts a 0.25% round-trip cost. Zero of 106 candidates had positive held-out mean net return; the median candidate mean net return was -0.2274%. The lead-lag inventory is therefore not promoted to a model feature or selector. Keep the tool only as a negative-result research record unless a materially different, preregistered data scope is proposed.
- 2026-07-21: The feature-coverage audit confirmed that the full matched-winner study has 13,473 unique symbol/date observations but only 687 currently have both archived point-in-time news and option-chain features. This is too small for a credible combined-family model, so no underpowered options/news training was run. A resumable full 14-day historical-news archive was started on `D:\AlientAI\Data\AlphaVantage_2026\event_news_sp500_full`; share-class symbols are normalized only for the provider request while AlienTAI retains the original symbol. A fail-closed sequential queue will start the estimated 26,221-snapshot full historical-options archive on the same SSD only after news completes successfully. Neither collection changes execution or enables trading.
- 2026-07-21: Reviewed the existing full-universe two-stage exceptional-winner result. Its untouched test selected 417 signals with mean net return 0.6124% after a 0.25% cost, but median net return was -0.1315%, win rate 48.44%, worst trade -23.47%, and approximate cohort drawdown -37.30%. These do not meet rare-signal promotion standards. The configuration remains research-only and must not be used for paper or real trading; future work should improve the data scope and test tail/drawdown-constrained gates rather than optimizing its historical average.
- 2026-07-22: Completed full-coverage matched-study catalyst ablation after compiling 13,473 unique, time-valid news rows and 13,473 unique historical-option feature rows from the external-SSD archives, then joining them exactly to all 18,326 matched rows. On the untouched matched test partition, technical-only top-1% precision was 37.78%; technical+news was 40.00%; technical+options was 48.89%; technical+news+options was 46.67%. Options also improved the top-5% matched precision from 31.42% to 41.59%. This is a promising discovery signal for historical option positioning, but it is not a probability, return, or tradability result because the study uses matched case-control sampling. Do not promote any model. Next required gate: construct an independently time-valid natural-universe evaluation with the same option features, calibrated scores, realistic costs, and tail/drawdown limits.
- 2026-07-22: Added the reusable, research-only rare-signal promotion gate and attached it to the natural-options-panel and unusual-call outcome evaluators. The gate fails closed for sparse samples, missing tail metrics, negative median or mean net results, poor post-cost win rate, excessive tail/worst trade loss, approximate cohort drawdown, or excessive single-symbol concentration. Targeted tests passed; no model was promoted and no execution setting changed.
- 2026-07-23: Completed the bounded 2026 natural-universe historical-options collection: 44,683 completed snapshots plus 26 correctly classified unavailable requests, with zero failures. Compiled 44,683 point-in-time option feature rows. The matched-trained technical-plus-options ranking failed the rare-signal gate on the natural panel: daily top-1 had +1.348659% mean net five-day return after the stated 0.25% cost, but -0.267803% median, 46.875% post-cost win rate, -15.214847% fifth-percentile outcome, -27.099183% worst trade, and -50.164499% approximate cohort drawdown. The standalone leakage-safe unusual-call rule had modest enrichment over the natural panel (4.9677% vs. 3.4756% exceptional-winner rate; +0.147209% vs. +0.042264% mean net return), but also failed the gate on negative median, below-50% win rate, worst trade, and drawdown. Neither result is promotable; no execution setting changed.
- 2026-07-23: Added `evaluate_unusual_call_contexts.py`, an exploratory leakage-safe diagnostic that scores the natural panel with the independent technical-only model before filtering unusual calls. Unusual calls within the top technical-score decile had 161 signals, +1.395004% mean net return, +1.483193% median, and a 55.90% post-cost win rate; the top 5% had 83 signals, +1.976916% mean, +2.451422% median, and 59.04% post-cost win rate. Both still failed the rare-signal gate solely because their approximate cohort drawdowns (-50.333635% and -39.000164%) exceed the -20% research limit. This is a promising, exploratory conditional interaction—not a chosen threshold, promotion, or trading input. Next work must use chronological threshold selection and a more realistic non-overlapping portfolio/drawdown simulation.
- 2026-07-23: Added `evaluate_context_portfolio.py`, a reusable chronological, seven-calendar-day embargo, capacity-limited (five concurrent positions) diagnostic. A prior output reported a top-quartile unusual-call `RESEARCH_PASS`, but it lacked a persisted model-artifact identity and could not be reproduced with the currently saved technical model. The evaluator now fingerprints every model and input panel. The current model hash `5bfa5258...f7bedea` produces 39 top-quartile later-slice signals at 0.25% cost, +1.704715% mean, +0.034788% median, 51.28% win rate, but -21.630095% drawdown: `RESEARCH_HOLD`. It remains `RESEARCH_HOLD` at 0.50% and 1.00% costs. The prior pass is invalid for any promotion; no execution setting changed.
- 2026-07-23: Added and ran `audit_promotion_evidence.py` against the fingerprinted current contextual-options report. It verified the report has all three required artifact identities and all required risk metrics, then correctly marked every candidate ineligible because each historical gate is `RESEARCH_HOLD`. The audit itself never authorizes paper/live trading and requires a separate prospective-shadow gate even for a future historical pass.
- 2026-07-24: Added and ran `audit_model_inventory.py` across all 58 local JSON research reports. Seven reports contain rare-signal gates; there are zero reproducible historical `RESEARCH_PASS` results. The only recorded pass is the already-invalid non-fingerprinted contextual-options output. This inventory is read-only, does not alter historical reports, and confirms no model may enter promotion review.
- 2026-07-24: Added and tested `refresh_sp500_daily_incremental.py`, an append-only local Schwab daily-candle refresher. It preserves existing historical rows, appends only later dates, never uploads to Supabase, and stops immediately on an authorization failure. Its three-symbol remote dry run found the Schwab token expired (HTTP 401), so no price data changed. Refresh the token before the next daily update; the pending July-21 research observations remain unevaluated.
- 2026-07-23: Added the pure, fail-closed `contextual_options_shadow_policy.py` component. It has no network, broker, order, or settings-write dependency; it requires a complete single-day input universe, selects at most five unusual-call candidates within the daily top technical-score quartile, sets the execution decision to `AVOID`, and supplies only a separate `shadow_research_decision` for a future journal integration. This freezes the research hypothesis without activating it. Live shadow journaling remains blocked until point-in-time current option snapshots and daily technical scores are supplied by a dedicated, tested adapter.
- 2026-07-23: Added `contextual_options_shadow_adapter.py`, a validation-only adapter boundary for future prospective data. It requires at least 400 unique symbols for exactly one market date and at least 90% of rows with ten prior call-volume observations; otherwise it fails closed. It produces a reviewable research payload only and cannot contact a provider, start the engine, journal a signal, write settings, or execute an order. This completes the safe policy/adapter boundary; the remaining blocker is a separately reviewed collector that can supply a complete current same-day panel.
- 2026-07-23: Validated the complete July 21 options-plus-technical panel through the adapter: 481 symbols had adequate history and it produced five non-executing research payload observations (TEL, NXPI, CPRT, URI, TSCO). Added and tested `evaluate_contextual_options_shadow_payload.py`, which evaluates only from local daily candles and refuses non-research payloads. Its July 23 review correctly reports all five pending because five later trading sessions are not yet available. No payload was journaled, no execution behavior changed, and no performance conclusion is available.
- 2026-07-23: Added and tested `download_alpha_vantage_option_panel.py`, a resumable, credential-safe generic symbol/date options-panel collector that reuses the shared archive implementation. Planned next collection: extend the existing natural S&P archive from 2026-07-03 through 2026-07-22. This bounded extension supplies recent history for a later genuinely prospective shadow panel; it does not create a signal, journal entry, paper order, or live order.
- 2026-07-23: Added and tested `audit_lightgbm_5day_holdout.py`, a report-only auditor that freezes a five-day LightGBM threshold from validation before looking up the matching historical test metric. For the existing S&P target-2% report, the validation-selected 0.60 threshold had 44 validation signals but only two test signals, with -0.895205% average net return after the stated 0.25% cost. This overturns the prior test-selected headline result; status is `RESEARCH_HOLD`. The generated audit is ignored research output and no model, data, setting, or execution behavior changed.
- 2026-07-23: Applied the same validation-locked audit to the remaining stored five-day LightGBM reports. The broad S&P direction model was effectively flat (+0.058238% average net on 123,389 test signals). The S&P target-3% artifact selected 0.55 from validation and showed 46 historical test signals, +6.010345% average net, 73.91% post-cost win rate, and +4.677949% non-overlapping average net across 27 signals. The legacy Russell target-2% artifact selected 0.55 and showed 75 historical test signals, +10.732698% average net and 61.33% post-cost win rate, but its broader report contains economically implausible five-day average returns (for example +52.475677% on the 0.50 test slice). Combined with the legacy-universe audit and an incorrect S&P build label, this result is now `RESEARCH_UNTRUSTED_PENDING_DATA_INTEGRITY_AUDIT`, not a promising hypothesis. It must not be scored, promoted, or integrated until source candle adjustments, corporate actions, symbol continuity, and price outliers are audited.
- 2026-07-23: Ran the authorized local S&P Schwab daily refresh after token renewal. It completed 483 symbols with 13 unresolved legacy symbols and no trading/Supabase activity, but the provider's daily-history endpoint still returned data only through 2026-07-21. Keep the five July-21 contextual-options observations pending; do not infer July-22/23 outcomes until a source supplies those daily closes.
- 2026-07-23: Performed a read-only source sample of the Supabase daily candles behind the legacy Russell LightGBM report. Extreme five-session moves are present in the underlying small-cap history (for example AAOI +119.12%, ABEO +850.00% with 14 moves over +100%, ACAD +154.35%, and ACCO +116.30%). This does not by itself prove a bad row, but it confirms that the headline return aggregates are dominated or materially affected by exceptional microcap/distressed-stock events. Any future Russell design must pre-register point-in-time minimum price and rolling dollar-volume/liquidity eligibility, corporate-action/outlier handling, realistic higher costs, and position/capacity limits before a model can be evaluated.
- 2026-07-23: Tightened and retested `audit_russell_liquidity_eligibility.py` after the legacy-gap discovery. It now sorts local files and requires every trailing 20-row liquidity window and every diagnostic five-session return to have no adjacent gap above five calendar days. Of 4,100,205 rows with sufficient row lookback, 4,088,044 have continuous trailing history and 2,162,577 pass the $5-close/$5-million trailing-dollar-volume preflight; 1,408 continuous five-session moves above +100% remain for separate corporate-action/outlier review. This is a data-quality screen only: it does not make the stale legacy list point-in-time Russell membership, establish tradability, or establish predictive value.
- 2026-07-23: Root-caused a critical legacy-history issue: some symbol files have long gaps between consecutive available rows (for example QUAD jumps from 2009-02-26 to 2010-07-05). A row-offset label could therefore misrepresent a multi-month/year change as a fixed trading-session horizon. Tightened and tested `audit_russell_price_discontinuities.py` to sort data and reject every one- or five-session review window containing a gap above five calendar days; its corrected 50%-move report preserves 1,630 one-session and 7,588 five-session events for manual provenance review, while excluding 6,888 discontinuous windows. It does not classify or alter any source row. Updated the active S&P five-day LightGBM and 20-day Transformer training paths with the same fail-closed continuity requirement. New tests prove both paths reject a synthetic year-long gap. All existing legacy Russell model artifacts remain invalid for promotion and must be retrained from a clean, pre-registered universe only after the full data-integrity design is complete.
- 2026-07-23: Regenerated the isolated five-day S&P Transformer from the protected source and added the same five-calendar-day continuity guard directly to the legacy Russell Transformer copy, with a dedicated Russell continuity test. This prevents an older duplicate trainer from bypassing the fixed-session label safeguard. Existing artifacts predate the guard and remain non-promotable.
- 2026-07-23: Added and tested `create_lightgbm_5day_shadow_snapshot.py`, a date-bounded, non-executing snapshot tool for frozen LightGBM artifacts. It truncates source candles at the requested decision date, requires fresh local history, emits only `SHADOW_JOURNAL_ONLY` records, and has no broker, network, settings, or engine dependency. The first S&P target-3% snapshot on 2026-07-21 covered 482 fresh symbols (one stale/missing) and selected zero at the validation-locked 0.55 threshold. This is an honest fail-closed prospective observation, not a signal or recommendation.
- 2026-07-23: Audited the existing Russell 2000 archive before treating it as new model evidence. Its historical constituent list has 1,909 symbols, of which 962 produced daily history and 947 are unresolved legacy/delisted/renamed symbols; completed daily files end 2026-07-09. The stored 20-day Russell Transformer used only 25 symbols and has weak validation separation, so it is not a credible universe benchmark. The stored five-day "Russell" LightGBM report has 1,909 symbols and promising already-observed metrics, but its build label incorrectly says S&P and its constituent membership, tail risk, concentration, liquidity, and portfolio behavior have not been audited. Treat all existing Russell artifacts as research hypotheses only. Before any new Russell evaluation, create a versioned current-universe/liquidity eligibility table, prevent overlap contamination with the S&P study, and apply higher small-cap cost/slippage assumptions with chronological out-of-sample tests.
- 2026-07-23: Added and tested `audit_russell_archive_coverage.py`, a read-only preflight guardrail. Its generated report confirms 962 usable local daily-history symbols from the legacy 1,909-symbol list, 947 missing/empty legacy entries, 23 overlaps with the current S&P symbol list, and newest local Russell candle coverage only through 2026-07-09. The audit does not claim point-in-time index membership or tradability; it exists to block accidental use of the legacy archive as a clean current Russell universe.
- 2026-07-23: Added and tested `validate_current_universe_manifest.py`, a fail-closed, research-only validator for any future current-universe source. It requires a dated snapshot, retrieval timestamp, provider name, absolute source URL, and valid ticker list, while reporting deliberate S&P overlap. No constituent list was downloaded or accepted in this task because the repository currently contains only the stale legacy Russell file.
- 2026-07-23: Added and tested `download_iwm_holdings_snapshot.py` as a provenance-preserving intake path for a current IWM equity-holdings proxy. It filters to equity tickers and preserves an as-of date, but explicitly does not claim official Russell or historical membership. The iShares endpoint returned HTML bot protection to the automated request, so the tool fails closed and supports only a manually downloaded CSV plus its public source URL; no current snapshot was accepted or used.
- 2026-07-23: Added and tested `audit_russell_split_ratio_candidates.py`, a read-only review tool for continuous one-session jumps near common 2x/3x/4x/5x/10x split or reverse-split ratios. It found 308 candidates while skipping 1,537 discontinuous rows. These are not classified corporate actions, data errors, exclusions, or adjustments; an independent corporate-actions source is still required before using any such conclusion in a historical panel.
- 2026-07-23: Extended the existing credential-safe, resumable Alpha Vantage fundamental collector to support the documented `SPLITS` endpoint, with a regression test. Started one archive for the 308 split-ratio review symbols at `D:\AlientAI\Data\AlphaVantage_2026\russell_split_history_2026` using a 0.75-second request delay. The archive stores raw provider responses and a manifest only; it has no model, candle, settings, broker, or execution path.
- 2026-07-23: Completed the Alpha Vantage split-history archive for all 85 unique symbols behind the 308 split-ratio review flags, with zero unavailable/failed requests. Added and tested `compare_russell_split_history.py`, a read-only reconciliation report. Only 2 flags match both a provider effective date and split factor; 9 match a nearby effective date only; 297 have no nearby provider event. This rules out automatic candle adjustment or event exclusion: preserve every finding as review evidence until a future source and historical-universe design can resolve the remaining cases.
- 2026-07-23: Extended and tested the credential-safe Alpha Vantage reference collector for dated `LISTING_STATUS` snapshots. Completed a single archive of active listings at June 30 for 2010–2026 in `D:\AlientAI\Data\AlphaVantage_2026\listing_status_annual_2010_2026`: 17 dated listing snapshots plus four current reference/calendar files, 12.19 MB uncompressed, no recorded error. These records can support later active/delisted survivorship checks; they neither establish Russell membership nor trigger training.
- 2026-07-23: Added and tested `audit_russell_listing_status_coverage.py`, a read-only survivorship reference audit. It finds that the stale 1,909-symbol legacy list has only 1,179 symbols present as active US stocks at the 2010-06-30 checkpoint and 942 at 2026-06-30, with material change across every annual checkpoint. This confirms the list is not stable enough to stand in for a point-in-time historical Russell universe. Active-listing presence remains only a necessary reference check, not membership evidence.
- 2026-07-23: Added and tested `audit_alpha_vantage_unavailability_policy.py` to make completed archive gaps join-safe. The transcript manifest has three unavailable requests (ADSK 2025Q1, AES 2024Q1, AWK 2025Q3); the premarket manifest has 44 requests across BF.B, BRK.B, COR, and EG. The generated policy requires explicit missingness, preserves request identity, blocks future-data substitution, and permits retry only after a separately tested provider mapping/coverage change.
- 2026-07-23: Added and tested `audit_matched_catalyst_panel.py`, a read-only key/timing audit for `matched_winners_catalyst_full.jsonl`. It verifies all 18,326 row keys are unique, 13,473 unique symbol/date observations are present, all news is at or before its `as_of_utc` cutoff, and all decision timestamps match their market date. News is available in all rows; option chains are available in 18,213 rows, so the remaining 113 must remain explicit missingness. This supports controlled matched-case ablations only and does not establish a natural-universe signal, promotion, or trading readiness.
- 2026-07-24: Added and ran `audit_matched_premarket_labels.py`, a read-only timing/arithmetic audit for the matched five-day premarket-open labels. It found 18,326 total rows and 18,244 available labels, with no duplicate keys, invalid dates/prices, or return-arithmetic mismatches. It also found nine labels whose first regular-session bar is later than 09:30 and 20 whose final bar is earlier than the expected 16:00 close (28 unique nonstandard-session rows). The audit fails closed; these rows must be explicitly excluded or repaired from a verified source before a strict matched-study premarket ablation. No source labels, model, settings, or execution behavior changed.
- 2026-07-24: Updated the matched premarket ablation trainer to exclude nonstandard-session labels rather than silently train on them, then reran its fixed chronological design. Of 18,326 base rows, 18,216 strict labels remained (28 excluded); 16,957 had available premarket features. The combined technical-plus-premarket top-1% slice remained `RESEARCH_HOLD`: validation had higher mean/median net return but lower exceptional-winner rate than technical-only, while the untouched test had no exceptional-rate improvement, lower mean net return (+1.297140% versus +2.237147%), and worse fifth-percentile loss (-7.120229% versus -6.459155%). This is a matched case-control feature-family result, not calibrated natural-universe performance; no model was promoted or connected to execution.
- 2026-07-24: Added SHA-256 fingerprints to the corrected matched-premarket ablation report for all three input files and each saved model artifact, then regenerated the report. This makes the current `RESEARCH_HOLD` reproducible and prevents a future report from being attributed to a different dataset or model. It does not alter the result, promote a model, or change execution.
- 2026-07-24: Renewed the Schwab access token through the existing refresh-token flow, then used the append-only local daily refresher to bring all 483 available S&P histories through 2026-07-22. The initial full run was interrupted only by terminal output timeout after 387 files; the refresher was improved and tested to resume only files older than a supplied target date, then safely added the remaining 96 rows with zero provider failures. No historical row was rewritten, no Supabase upload occurred, and no trading state changed. The five July-21 contextual-options shadow observations still require five later trading sessions before their fixed-horizon outcomes can be evaluated.
- 2026-07-24: Extended the research-only contextual-options shadow evaluator to retain interim one-through-four-session returns while keeping the fixed five-session result pending until fully observed. At the first subsequent session (July 22), the five observations were mixed: TEL -0.743958%, NXPI -0.541607%, CPRT +0.110416%, URI +10.110525%, and TSCO +3.269755%. These are interim observations onlyâ€”not an aggregate score, a model result, or a trading signal. The evaluator remains execution-disabled and reports zero completed outcomes.
- 2026-07-24: Added, tested, and ran a narrow Alpha Vantage daily-price archival fallback for only the five non-executing contextual-options research observations. It preserved five raw `TIME_SERIES_DAILY` responses on the external drive with a manifest and SHA-256 identities; each source has data through July 23, one session ahead of the local Schwab archive. The fallback is deliberately source-separated and must not be merged into Schwab outcomes, model features, Supabase, or execution. It supplies an independent later cross-check once the fixed five-session horizon is available.
- 2026-07-24: Added and ran a fail-closed source-alignment audit before using the Alpha Vantage fallback for any outcome. Across 79 overlapping dates for each of TEL, NXPI, CPRT, URI, and TSCO, Alpha Vantage's close almost always matches the immediately prior Schwab trading session rather than the same labeled date (only one same-day numeric match across 395 comparisons). `same_day_alignment_passes` is therefore false and source mixing is explicitly unauthorized. The Alpha archive remains raw reference evidence only; Schwab remains the sole outcome source for this prospective study until the date convention is independently reconciled.
- 2026-07-24: Added and tested `evaluate_contextual_options_prospective_gate.py`, which aggregates only completed, unique, source-consistent Schwab shadow outcomes behind the common rare-signal gate. It additionally requires at least ten distinct decision dates and never makes paper trading eligible automatically. The initial run correctly returns `RESEARCH_HOLD` with zero completed five-day outcomes. The frozen prospective requirement is now at least 30 completed signals across ten dates, positive average and median net returns after the stated cost, at least 50% post-cost win rate, controlled tail/worst loss/drawdown, and no excessive symbol concentration, followed by separate human review.
- 2026-07-24: Added and tested `build_local_schwab_daily_technical_panel.py`, a research-only builder that reads the append-only local Schwab archive rather than changing Supabase. It produced 483 source-labeled technical rows for July 22, with 13 existing unavailable symbols explicit as missing. The next dependency for another complete contextual-options daily panel is not technical coverage but option compilation: raw point-in-time option snapshots extend through July 22, while the existing compiled natural-option feature file ends July 2. Do not create a partial daily panel or shadow payload until a tested compiler produces the required full, history-aware option rows.
- 2026-07-24: Added, tested, and ran `compile_natural_options_daily_panel.py` to compile the July-22 raw natural-options snapshots into a complete 483-row feature panel. It uses the existing pre-July-22 compiled call-volume history only for earlier-date baselines, loads raw snapshots only after that history boundary, and computes July-22 unusual-call features without future rows. The 13 unavailable S&P symbols remain outside both panels. This closes the point-in-time data compilation gap, but July 22 is already historical at the time of this work; any joined output must be labeled backfill/research-only and excluded from the frozen prospective gate.
- 2026-07-24: Added, tested, and ran `build_contextual_options_backfill_panel.py` to exact-join the 483-row July-22 local Schwab technical panel and 483-row compiled options panel, then score only with the frozen technical-model artifact (`5bfa5258...f7bedea`). The complete backfill panel contains 22 unusual-call observations, five of which are in the daily top technical-score quartile. It fingerprints both inputs and the model, and is explicitly `BACKFILL_RESEARCH_ONLY` / ineligible for the prospective gate because its decision date was already in the past. This validates the full data path without creating a recommendation or paper trade.
- 2026-07-24: Completed the full research-only July-23 S&P option-snapshot collection in the existing external-drive archive. All 496 requested symbols completed, with zero unavailable requests and zero failures; the collector exited and no duplicate collector remained active. Local Schwab daily history currently ends July 22, so a same-date technical/options join cannot yet be built honestly. Keep the July-23 raw options snapshots archived until a matching point-in-time local Schwab daily close is available; do not create a partial panel, shadow payload, paper trade, or model result from this date.
- 2026-07-24: Audited the previously described catalyst-archive queue and corrected its stale status. The external-drive event-news archive is complete with 13,473 completed requests, zero unavailable, and zero failed. The separate full historical-options archive is complete with 26,221 completed requests, zero unavailable, and zero failed. Both manifests report `complete`; neither collector is active. These data are already reflected in the matched catalyst study and must not be downloaded again merely because older roadmap text described the earlier queue state.
- 2026-07-24: Added and tested `prepare_natural_event_news_requests.py`, a fail-closed preparer for a natural-universe historical-news archive. It derives 44,683 unique symbol/as-of requests directly from the existing point-in-time natural options/FINRA panel, preserving each original cutoff timestamp and rejecting duplicates or malformed rows. The request list is stored on the external drive. The resulting news archive is research-only: it must later be joined and evaluated chronologically with strict timing, realistic costs, and rare-signal safeguards before any conclusion or promotion.
- 2026-07-24: Started the resumable natural-universe Alpha Vantage news archive at `D:\AlientAI\Data\AlphaVantage_2026\natural_event_news_2026`, using the prepared 44,683 request list, a 14-day lookback, and a 0.75-second request delay. The initial Windows command had an argument-parsing failure before any provider request or manifest write; it was corrected after log inspection. The active corrected collector writes raw responses and its manifest only. It must not be run concurrently with another news collector, joined to a model while incomplete, uploaded to Supabase, or connected to any execution path.
- 2026-07-24: After confirming the active $99.99/month Alpha Vantage tier supports 150 requests/minute, safely stopped the resumable natural-news collector at a manifest boundary and restarted it with a 0.45-second delay (approximately 133 requests/minute, leaving a margin below the entitlement). It resumed from existing completed records without duplication. This is a collection-speed change only; the archive remains raw research data and execution-disabled.
- 2026-07-24: Added and tested `build_natural_news_research_panel.py` while the natural-news archive is collecting. It exact-joins compiled news features to the point-in-time natural base panel by `(symbol, as_of_utc)`, preserves all base rows, keeps archive gaps explicit rather than zero-filling them, and fails closed for duplicate or extra news keys. It is a research-panel builder only; it has no model, broker, settings, Supabase, paper-trading, or live-trading dependency. Once the archive completes, compile its features, run this exact join, audit timing/coverage, and only then define a pre-specified chronological news ablation.
- 2026-07-24: Added and tested `audit_natural_news_research_panel.py` while the archive is collecting. The audit verifies unique point-in-time keys, records coverage, requires an explicit reason for every unavailable news row, and fails closed if any visible article timestamp is after its row's decision cutoff. It produces an evidence report only and cannot score, train, alter settings, communicate with a provider, or execute a trade. This completes the collection-to-validated-panel path; only the later pre-specified chronological experiment remains after collection completes.
- 2026-07-24: Stopped the broad natural-news archive deliberately after preserving 2,130 raw requests with zero unavailable and zero failed records. The partial archive covers too few early decision dates for a credible chronological model test, so it must be retained only as a pipeline artifact—not interpreted, joined as a model dataset, or used to tune a strategy. The research priority is now evidence-driven evaluation of the already complete core price/options/technical/FINRA/insider datasets. Any future news work must use a smaller, pre-specified, time-stratified sample rather than another open-ended archive.
- 2026-07-24: Ran a fixed retrospective chronological stability diagnostic for the current fingerprinted technical-context plus unusual-call portfolio hypothesis at 40%, 50%, and 60% calibration fractions, each with a seven-calendar-day embargo, five-position capacity cap, and 0.25% round-trip cost. The top-quarter technical-context variant had positive mean/median net returns and above-50% post-cost win rates in all three later test slices: 59 signals, +2.439161% mean, +1.722185% median, 55.93% wins at 40%; 49, +2.420582%, +1.722185%, 57.14% at 50%; and 39, +1.704715%, +0.034788%, 51.28% at 60%. Every slice remains `RESEARCH_HOLD` solely because approximate cohort drawdown was -25.948509%, -22.517655%, and -21.630095%, respectively, beyond the -20% safeguard. This is the strongest current research lead, but it is still retrospective, already explored, and not paper-trading eligible. Do not tune a threshold from these diagnostics; next work must reduce drawdown through a separately specified portfolio/risk design and confirm prospectively.
- 2026-07-24: Ran the first pre-specified position-capacity stress test for that contextual-options hypothesis, holding its model, top-quarter technical context, 0.25% cost, seven-day embargo, and 40%/50%/60% chronological splits fixed while varying capacity from one to three positions. One position reduced drawdown to -16.933569% in all three splits, but yielded only 8–12 signals and therefore failed the 30-signal evidence minimum. Two and three positions restored more samples but had drawdowns from -24.981536% to -30.057847% (two) and -25.587063% (three); the only 30-signal three-position result remained `RESEARCH_HOLD` for drawdown. Position capacity alone does not produce a promotable model. Preserve all outputs; do not choose the superficially attractive sparse one-position result.
- 2026-07-24: Added and tested `contextual_options_stop_evaluator.py`, a research-only fixed-stop evaluator that reads raw local Schwab OHLC history, uses a gap-at-open fill when price opens through the stop and a same-day stop-price fill otherwise, and refuses incomplete five-session price paths. On the fixed 50% chronological split, tested -5%, -7.5%, and -10% stops retained 39 path-complete signals each. They had +2.312827%/+0.955602%/51.28% wins with -33.612597% drawdown; +2.596085%/+1.715415%/56.41% with -27.038709%; and +2.411283%/+1.715415%/56.41% with -34.979959%, respectively. All remain `RESEARCH_HOLD`; the -10% variant also failed the fifth-percentile tail limit. A simple fixed stop is therefore not the drawdown solution. These are retrospective diagnostics only and never change engine exits, settings, or orders.
- 2026-07-24: Added and tested a generic explicit-universe slicer, then evaluated the frozen contextual unusual-call model on a documented 17-symbol current AI/semiconductor infrastructure basket (AMD, AMAT, AMZN, ANET, AVGO, CDNS, GOOGL, KLAC, LRCX, META, MSFT, MU, NVDA, ORCL, PLTR, SMCI, SNPS). This current thematic classification is exploratory and not point-in-time sector membership. Its top-quarter contextual tests did not reproduce the broader result: 15 signals / 46.67% wins / -0.084304% median at the 40% split; 14 / 42.86% / -0.677894% at 50%; and 11 / 36.36% / -1.271483% at 60%. Drawdown was smaller (about -10.13%), but the win rates, typical return, and sample size all failed. Do not specialize the current model to this theme or infer a semiconductor/AI advantage.
- 2026-07-24: Jeff authorized a final low-cost, frozen prospective study rather than further broad data/model exploration. `FROZEN_CONTEXTUAL_OPTIONS_STUDY.md` fixes the sole hypothesis to the complete-universe, public-unusual-call plus daily top-quarter technical-context rule, measured as a five-session stock outcome with a 0.25% cost. It prohibits feature/model/universe/threshold changes, broad downloads, or any execution. It requires at least 30 completed candidates across ten decision dates before a separate human paper-trading review; failure ends the hypothesis without post-hoc tuning. Drawdown remains recorded but is a risk-review input rather than an automatic directional-hypothesis rejection during this evidence stage.
- 2026-07-26: Preregistered the future five-day selective-catalyst challenger without changing the controlling frozen study. Added a pure, non-executing policy that requires complete same-day coverage, validation-frozen thresholds, calibrated profit and large-move probabilities, expected and lower-quantile net return, technical/options agreement, and bounded model disagreement. It has no candidate quota and abstains on incomplete or missing evidence. Eleven targeted policy/shadow/gate tests passed, Python compilation passed, and `git diff --check` passed; no trainer, collector, settings file, runtime engine, paper account, or live account changed.
- 2026-07-26: Added the challenger's pure next-open-to-fifth-close label builder. It prevents the older close-to-close timing mismatch, subtracts the frozen cost, and excludes incomplete, invalid, discontinuous, duplicate, or unsorted price windows. Twelve targeted label/policy tests passed, Python compilation passed, and `git diff --check` passed. No historical dataset was rewritten and no training or execution was started.
- 2026-07-26: Added the selective challenger's exact-key, timestamp-aware feature/label join. It rejects duplicate or mismatched keys, features visible after the explicit UTC decision cutoff, invalid label timing, missing required fields, and every known outcome/label field on the feature side. Twenty targeted panel/label/policy tests passed, Python compilation passed, and `git diff --check` passed. No source panel, trainer, settings file, or execution path changed.
- 2026-07-26: Trained the first isolated selective five-day LightGBM challenger on existing local data only. The corrected panel had 44,116 rows and 72 technical/options feature columns. The untouched test covered 5,787 rows beginning 2026-06-07; its universe had a 51.29% positive-net rate and +0.236269% mean net return, but the validation-calibrated positive classifier could not reach the frozen 0.60 gate, so zero candidates qualified. The fingerprinted report and four model artifacts are isolated under ignored `data_v2/selective_five_day_challenger_training`; 24 targeted tests and compilation passed. No trading path changed. Preserve this as a clean negative result and do not tune on the now-observed test.
- 2026-07-26: Ran a validation-only component audit. Positive-direction and return-regression components failed to discriminate, while the large-move classifier showed modest validation discrimination (AUC 0.5670) and a strong but small 57-row top-1% slice. Preserve this as hypothesis-generation evidence only. Added premarket feature-family support with an exact natural-universe/09:25 ET gate; the existing matched table has only 7.4973% natural-key overlap and is explicitly blocked. Twelve targeted premarket/trainer/audit tests passed; no retraining or test retuning occurred.

## Direction-change log

- 2026-07-20: Jeff established a single mandatory dynamic roadmap that every future AI task must read and maintain. The initial roadmap consolidates the existing research priorities, safety gates, data-collection phases, evaluation path, storage work, and future decisions.
- 2026-07-20: Added a limited TradingAgents-inspired qualitative review experiment to Phase 8. It is a shadow-only second-opinion layer for candidates already selected by AlienTAI, not a replacement signal model or execution authority. The plan explicitly avoids a wholesale repository merge, uncontrolled live-data use in historical evaluation, and reuse of unsafe credential-bearing HTTP error paths.
- 2026-07-21: Jeff determined the existing Alpha Vantage key was not compromised through GitHub and directed AlienTAI to continue using it. The roadmap no longer requires key rotation as a precondition for the resumable research-data harvest.
- 2026-07-21: Jeff added two research hypotheses to the feature roadmap: (1) publicly observable unusual options positioning around known catalysts may have incremental predictive value, and (2) some cross-symbol movements may have stable delayed lead-lag relationships. Both are explicitly framed as leakage-safe, out-of-sample market-behavior research, not as evidence of insider trading or as a basis for unvalidated trading claims.
- 2026-07-22: Jeff confirmed the desired direction: build toward calibrated, rare high-quality stock-movement research candidates using staged point-in-time feature ablations, strict cost/tail/drawdown gates, and prospective shadow validation rather than a high-volume prediction system.
- 2026-07-26: Jeff directed AlienTAI to formalize the proposed five-day selective-catalyst strategy. The architecture was added as an isolated future challenger and fail-closed policy contract, while the already-frozen contextual-options prospective study remains unchanged and controlling.
- 2026-07-26: Jeff directed adding premarket movers to the selective challenger. Support and leakage/coverage gates were implemented, but retraining is blocked until a point-in-time natural-universe premarket table replaces the biased, 7.5%-overlap matched-study file.
- 2026-08-02: Jeff directed completion of the evidence-review recommendations.
  The roadmap now limits active predictive work to the frozen Nasdaq five-day,
  AI/semiconductor intraday, and contextual unusual-call prospective programs.
  New variants are deferred while prospective samples remain sparse. The
  interrupted stratified-news collector was safely resumed, and application
  restart remains gated because the preserved paper setting is enabled while
  the server is currently stopped.
- 2026-08-03: Jeff supplied an external AI/semiconductor ranking narrative and
  asked that its logic be considered for a future model. The viable hypothesis
  was preserved as a deferred, leakage-safe 1/5/20-session catalyst-context
  design. The narrative's rankings, opaque third-party scores, current price
  claims, and recommendations are not accepted as training labels or verified
  facts. No model, threshold, universe, collector, setting, or execution
  behavior changed. Jeff then supplied the underlying data-family and
  horizon-matching logic; it is preserved in
  `FUTURE_AI_SEMICONDUCTOR_MULTI_HORIZON_MODEL.md` as a pre-registered future
  design with separate 1/5/20-session targets and staged ablations.
- 2026-07-27: Added and tested an isolated multi-horizon uptrend-pullback LightGBM experiment using 135,713 cost-adjusted S&P observations from 483 local Schwab histories. The design required positive 20/63/126-session slopes and price above the 126-session average, froze model cutoffs on validation, and opened the untouched 2022-12-03+ test only once. It failed to generalize: the two-day frozen test slice averaged -0.064428% net with 48.05% wins (1,028 rows), while the five-day frozen test slice averaged -0.055000% with 47.62% wins (1,136 rows). The five-day validation gain (+0.446571%, 54.70% wins) vanished out of sample. Status remains `RESEARCH_HOLD`; do not tune this formulation on the observed test or connect it to execution.
- 2026-07-27: Corrected the contextual unusual-call portfolio risk measurement without deleting its conservative legacy metric. The prior cohort curve compounded each exit-date average as 100% account exposure. The tested simulator now price-anchors every trade to the exact stored entry close and label-implied exit close, marks every open position to market each day, limits each new position to one of five slots and available cash, leaves unused slots in cash, never borrows, and subtracts the stated cost. Every selected trade reconciles to its stored return label with zero reported error. At the frozen top-quarter rule, all three existing chronological splits pass the capital-scaled research gate: 40% split 59 signals, +2.439161% mean net, 55.93% wins, +31.006419% portfolio return and -9.883183% drawdown; 50% split 49 signals, +2.420582%, 57.14% wins, +25.073189% portfolio return and -9.883183% drawdown; 60% split 39 signals, +1.704715%, 51.28% wins, +13.611174% portfolio return and -10.757040% drawdown. These are retrospective robustness results from an already explored archive, not authorization for paper/live trading. The next requirement is the existing frozen prospective shadow protocol.
- 2026-07-27: Refreshed the Schwab token through its existing refresh-token flow and append-only added exactly one newer candle to each of 483 local S&P histories, with zero provider failures and no historical rewrites. Re-evaluated the frozen July-21 five-candidate pilot from Schwab only: each candidate now has two later sessions, so all five remain pending and the prospective gate remains `RESEARCH_HOLD` with zero completed outcomes. Do not aggregate the interim returns or backdate a new prospective payload; three additional later sessions are still required for this pilot.
- 2026-07-27: Added a deterministic SHA-256 identity for every filename and byte of the 483-file Schwab daily archive used by the corrected portfolio simulator. The strict price-anchored rerun uses daily archive hash `75b25e35e451...`; all three capital-scaled gates pass with zero label-alignment error. This closes report-provenance and date-alignment gaps; it does not replace prospective validation.
- 2026-07-28: Trained an isolated Nasdaq-100 technical-context clone on the 80 of 101 current securities available in the existing S&P-derived research table. A validation-only choice among predeclared top-0.25%/0.50%/1.00% ranking fractions selected top 0.25% and locked score cutoff `0.15986412677273237`. Its untouched, five-slot, daily mark-to-market test retained 40 trades after capacity control and 0.25% round-trip cost: +1.947586% mean net, +1.692813% median net, 75.00% wins, +16.246296% capital-scaled portfolio return, and -7.443113% maximum drawdown with zero price/label alignment error. Classify this as `RESEARCH_PASS_HISTORICAL`, not execution evidence: the test has now been observed, 21 constituents lack source-consistent rows, and prospective frozen shadow evidence is still required.
- 2026-07-28: Enabled the frozen Nasdaq clone for local paper observation under engine id `nasdaq100_technical_clone_v1`. Its payload builder and runtime adapter restrict selection to the exact 80 trained securities, require the locked score cutoff and a recent complete paper-only payload, cap the payload at five candidates, request one share through the existing paper manager, and fail closed for untrained symbols. The control panel now lists both enabled paper engines. The first payload contained INTC, MCHP, and LRCX; no immediate purchase occurred because the shared account had already reached its five-buy daily limit. This is paper observation only; no live execution path was enabled.
- 2026-07-28: Completed an isolated one-day Nasdaq clone using the same 80 securities and 50,255 rows. Labels use an executable contract—decide after close, enter next-session open, exit that close—and all rows aligned exactly to the Schwab archive. The 2% target model reached validation AUC 0.716242 and validation-selected cutoff `0.16009235126661475`, but failed untouched cost-adjusted testing: 241 signals over 87 days, -0.063818% mean net return, +0.069942% median, 51.037344% wins, -4.475285% capital-scaled return, and -13.407436% drawdown after 0.25% cost. Classify `RESEARCH_FAIL`; do not paper-enable or retune it on this observed test. The five-day Nasdaq model remains the stronger horizon.
- 2026-07-28: Completed an isolated ten-session Nasdaq clone on the same 80 securities and 50,255 fully aligned rows. The executable contract decides after close, enters next-session open, exits tenth-session close, targets >=10% gross return, uses 20-calendar-day split embargoes, locks its cutoff from validation, limits the portfolio to five concurrent slots, marks positions daily, and charges 0.25% round-trip cost. Validation chose top 0.50% / cutoff `0.20992159279836498`. Untouched test retained 57 trades with +1.520393% mean net, +1.173362% median, 56.140351% wins, and +15.396338% capital-scaled return, but -23.090912% drawdown. Classify `RESEARCH_HOLD`: the economic edge replicated, but risk exceeds the -20% boundary and the observed test cannot be tuned. Do not paper-enable it; the five-day Nasdaq clone remains superior.
- 2026-07-28: Repeated the successful five-day design on the ten largest securities by official Nasdaq May 1 index weight: NVDA, AAPL, MSFT, AMZN, GOOGL, GOOG, AVGO, TSLA, META, and WMT. The 5,175-row clone used the same technical features, 10% target, chronological splits, 12-day embargoes, validation-only fraction selection, 0.25% cost, and five-slot capital-scaled simulation. Validation chose top 2% / cutoff `0.038962159893157364`. Untouched test retained only 16 trades: +2.192283% mean net, +1.855858% median, 56.25% wins, +7.170045% portfolio return, and -3.190090% drawdown with zero alignment error. Classify `RESEARCH_HOLD_INSUFFICIENT_TEST_SAMPLE`; it is profitable but materially less convincing than the 80-security Nasdaq clone and must not be paper-enabled.
- 2026-07-28: Exported the exact 39-event frozen 60% contextual-options cohort with its original panel/model fingerprints and evaluated two precommitted call policies against the fuller natural-universe historical option archive. Thirty contracts per policy passed chain/contract/liquidity requirements; two event pairs lacked complete chains. Real ask entry, same-contract bid exit, and commissions produced lottery-like rather than consistently profitable call results: ATM/approximately-30-day calls had +21.533594% mean but -26.056060% median and only 40.00% profitable trades, with 3.33% total losses; delta-60/approximately-30-day calls had +7.348247% mean, -16.697239% median, and 43.33% profitable trades. Preserve this as a clean negative for these fixed call-selection policies. It does not invalidate the underlying-stock hypothesis, authorize option paper trading, or justify tuning on the observed cohort.
- 2026-07-28: Added and ran a leakage-safe joint after-hours/premarket same-day continuation study over the existing extended-hours archive. It labeled 44,484 of 44,683 symbol-days and had 39,579 rows with both session-volume baselines. Every fixed 1.5x/2x/3x/5x joint relative-volume threshold had negative full-history mean net return after 0.25% cost. In the untouched test, the 5x joint group had 70 rows, 48.57% net wins, -0.450914% mean net return, and -0.127161% median. Retain after-hours and premarket activity only as pre-specified contextual model features; do not use either as a standalone buy rule or connect this study to execution.
- 2026-07-28: Corrected that study to distinguish directional pressure from total volume using an explicitly labeled five-minute uptick/downtick-volume proxy. The fixed rule required at least 60% buy-proxy share, positive price movement, and independently unusual buy-proxy volume in both after-hours and premarket. It also failed at every fixed threshold. Untouched results were: 1.5x 81 rows / 39.51% net wins / -0.266448% mean; 2x 48 / 41.67% / -0.389225%; 3x 32 / 34.38% / -0.831475%; and 5x only 11 / 45.45% / -0.355808%. This is not exchange-classified aggressor-side volume, but it directly rejects the directional proxy as a standalone post-open continuation rule. Future use must be a pre-specified interaction or use true trade-and-quote classification.
- 2026-07-28: Added a strict 60-trading-session unusual-call outcome study with exact stored-close reconciliation and a fingerprinted Schwab archive. It obtained 28,608 complete rows and 1,184 leakage-safe unusual-call observations; 16,075 later rows remain incomplete and were excluded. Unusual calls modestly increased the chance of touching +20% within 60 sessions (23.1419% versus 21.2703%, +1.8716 points), +30% (12.5845% versus 11.5317%, +1.0527), and +50% (4.9831% versus 4.7155%, +0.2676). Mean day-60 net return was +3.4872% versus +3.3044%. The relationship was not stable: early-period mean-return and +20% reach lifts were negative, middle-period results were mixed, and the late period supplied the strongest +20% reach lift. Treat this as weak contextual enrichment, not a dramatic or standalone 60-day predictor. Overlapping observations also preclude treating row counts as independent trials.
- 2026-07-28: Audited the unofficial Kaggle/Benzinga-headline analyst archive for explicit same-day rating transitions. It contains zero exact Hold-to-Strong-Buy events and therefore cannot answer that exact question. It contains 402 explicit Hold-to-Buy events, 277 timestamped premarket, but only 42 unique premarket symbol-days match the current survivor-biased S&P daily archive. Those 42 averaged -0.069222% open-to-close with 50% positive days and -0.191087 percentage-point performance versus each stock's prior-20-session open-to-close mean. This limited sample does not show a same-day Hold-to-Buy edge and is not definitive. A licensed event feed plus historical delisted/non-current ticker prices is still required.
- 2026-07-28: Completed a source-consistent rebuild of all 101 current Nasdaq-100 securities from local Schwab daily histories after discovering that rows from the earlier S&P-derived table could not safely be spliced with newly downloaded rows. The 44,620-row five-day challenger selected top 0.25% on validation and retained 27 untouched test positions: +6.269610% mean net, +4.369699% median, 66.666667% wins, +37.184514% capital-scaled return, and -12.006414% drawdown after 0.25% cost, with zero label-alignment error. Classify `RESEARCH_PASS_HISTORICAL_CHALLENGER`; it is promising but does not replace the frozen 80-security champion because its test sample is smaller and win rate lower. No execution settings changed.
- 2026-07-28: Added point-in-time QQQ 5/20/60-session market returns and stock-minus-QQQ relative returns to the complete 101-security Nasdaq dataset, using the same frozen five-day protocol. Validation selected top 0.50% but was weak (41 signals, +0.367082% mean, -2.672611% median, 43.90% wins). The untouched test was much stronger: 23 positions, +8.847970% mean net, +9.544842% median, 73.913043% wins, +46.870445% capital-scaled return, and -7.973577% drawdown. Classify `RESEARCH_PROMISING_REGIME_SENSITIVE`: preserve it for regime and prospective comparison, but do not tune on the observed test, replace the champion, or enable execution.
- 2026-07-28: Completed the first controlled Nasdaq catalyst round. Historical options, news, analyst, earnings-event, and premarket archives do not presently provide complete natural-universe point-in-time coverage across the 2024-2026 training chronology; sparse/event-selected joins were rejected rather than confounded with time regime. SEC Form 4 features supported a fair 24,836-row paired ablation, but worsened validation versus the identical QQQ-relative baseline (-1.132327% vs. -0.363619% mean net; 31.82% vs. 43.18% wins). Its strong-looking test retained only eight trades after negative validation and is not reliable. Status `RESEARCH_HOLD`; do not add these insider features or alter execution.
- 2026-07-28: Tested a classifier-plus-expected-return second stage on the complete QQQ-relative Nasdaq panel. A new tie-expansion gate correctly rejected the one-iteration return-only regressor because nominal top fractions expanded into 303 tied validation rows. Validation selected the 0.50% joint score (41 signals, +2.156291% mean net, +0.502437% median, 51.22% wins). The reused historical confirmation retained 23 positions with +7.135010% mean, +5.611869% median, 73.91% wins, +36.199567% capital-scaled return, and -15.164772% drawdown. Status `RESEARCH_HOLD`: profitable, but inferior to the simpler QQQ-relative challenger on return and drawdown, and the period is no longer untouched. Preserve the rank-degeneracy gate; do not integrate the two-stage model.
- 2026-07-28: Tested three hard QQQ regime partitions (bullish, bearish, mixed), each with its own Nasdaq classifier and validation-locked fraction/cutoff. Validation chose mixed/top-0.50% (16 signals, +6.543888% mean net, +2.621953% median, 62.50% wins), but reused historical confirmation retained only seven trades and failed with -0.668923% mean net and -1.039052% capital-scaled return. Status `RESEARCH_FAIL`; hard regime specialization fragmented the data and did not generalize. Keep QQQ context as continuous features, not separate models, and do not retune this design on the observed period.
- 2026-07-28: Added a fail-closed 60-session pairwise-correlation portfolio control to the frozen QQQ-relative Nasdaq challenger. A 0.75 validation ceiling was directionally best, improving capital-scaled validation return from +3.675800% to +6.251769% and drawdown from -12.334440% to -10.156268%, but it retained only 16 positions versus the frozen 20-position minimum. Status `RESEARCH_HOLD_INSUFFICIENT_VALIDATION_SAMPLE`; no threshold was selected and the confirmation period was not opened. Preserve the control for future prospective evidence rather than lowering the gate after observation.
- 2026-07-28: Added dependency-free validation-only isotonic calibration for the complete QQQ-relative Nasdaq model and separated relative rank from probability. The locked score cutoff is rank 99/100 versus validation history but maps to only a 24.7024% estimated probability of a gross five-day move >=10%. On reused historical confirmation, calibration improved Brier error from 0.080593 raw and 0.084865 base-rate-only to 0.078954, with 0.029060 ten-bin ECE. Status `RESEARCH_CALIBRATED_PENDING_PROSPECTIVE`; retain the explicit “rank, not probability” display and do not expose calibrated probability as trusted execution confidence until prospective evidence accumulates.
- 2026-07-28: Completed the reproducible Nasdaq champion scorecard. Decision: keep the frozen 80-security model as the paper-observation champion. The complete 101 baseline is closest to replacement (strong validation; 27 historical confirmation positions, three short of the frozen 30 minimum). The QQQ-relative challenger has the best observed economics (+46.870445% portfolio return, -7.973577% drawdown) but weak validation, only 23 confirmation positions, and no prospective completions. No challenger clears all validation, confirmation, current-universe, and 30-outcome prospective gates. Next evidence must come from frozen non-executing prospective journals for the complete baseline and QQQ-relative challenger; do not generate more variants from the already observed period.
- 2026-07-28: Jeff directed an isolated correction of the Nasdaq five-day research contract after review found that the active historical clones label same-close entry while their signals are computed from that close. The correction must preserve all frozen artifacts and active paper settings, use next-regular-session open entry through the fifth regular-session close, preserve explicit entry/exit dates and prices, enforce positive validation mean/median and at least 50% validation win rate when selecting a cutoff, and remain research-only. The resulting historical result is exploratory because the earlier close-to-close period has already been examined; it cannot replace the champion, alter paper buys, or qualify as prospective evidence. A future runtime session-hold change must be separately checked against open paper positions before activation.
- 2026-07-28: Completed the isolated executable-label Nasdaq correction on the complete 101-security local Schwab universe, preserving all existing model artifacts and settings. The builder now records next-session entry date/open and fifth-session exit close; the portfolio simulator price-anchors open entries and marks them to daily closes; and validation cutoff selection fails closed unless mean and median net return are positive and win rate is at least 50%. The 44,620-row result selected top 0.25% / cutoff `0.23346458789809038` on validation (21 signals, +6.281492% mean, +4.771091% median, 76.19% wins), but its later historical test had only 11 trades, +3.580862% mean, -1.292366% median, 45.45% wins, +7.376964% capital-scaled return, and -13.018128% drawdown. Status `RESEARCH_FAIL_EXECUTABLE_LABELS`; do not paper-enable, tune, or replace the champion. The legacy QQQ-relative challenger now fails the stricter validation gate because none of its candidate fractions has positive validation median and at least 50% wins. All 30 targeted tests and compilation passed; the historical archive aligned to labels with zero error.
- 2026-07-28: Started the frozen, append-only, non-executing prospective journal for the complete 101 baseline and QQQ-relative challenger after force-refreshing all 101 Schwab histories plus QQQ. A freshness gate rejected stale/backdated use, and the journal records both the legacy stored archive key and actual UTC session date. The first valid July-27 session produced four pending observations: baseline SNDK/NBIS and QQQ-relative MU/NBIS. Every row is fingerprinted, rank-labeled as “not probability,” limited to five candidates per model/day, and marked `execution_decision: AVOID`. Do not evaluate until five later sessions exist or alter the frozen rules before 30 completed observations per challenger.
- 2026-07-29: Attempted the documented append-only Schwab S&P daily refresh to mature frozen prospective observations. It stopped safely on its first request (QQQ) with `Schwab HTTP 401 unauthorized`; zero rows were added and no historical files, Supabase data, model artifacts, or trading settings changed. The current blocker is renewing the Schwab access token through its existing refresh-token workflow, then rerunning only the append-only refresher before evaluating the fixed five-session outcomes. Do not mix the delayed Alpha Vantage daily fallback into the Schwab-only prospective record.
- 2026-07-29: The existing Schwab refresh-token utility then renewed the access token successfully. The correctly scoped append-only refresher ran over all 483 verified S&P symbols (not the accidental one-symbol QQQ default), added 885 newer rows, and reported zero failures. Re-evaluating the dated July-21 frozen contextual-options payload against that archive gives each of TEL, NXPI, CPRT, URI, and TSCO four verified later sessions; all five remain pending one final session. Seven targeted prospective-policy/evaluator tests passed and `git diff --check` passed. No model, Supabase, paper-account, or live-trading state was changed.
- 2026-07-29: Jeff directed a new isolated multi-horizon comparison. It must train separate 2-, 5-, 10-, and 20-session models using the same 80-security Nasdaq technical/QQQ-context feature scope, the executable next-regular-session-open entry, fixed later-session-close exits, a 0.25% round-trip cost, chronological train/validation/test partitions, and validation-only cutoffs. All outputs are exploratory because this broad archive has already been examined; do not replace an existing model, alter the paper engine, or claim prospective evidence from them.
- 2026-07-29: Completed that isolated executable-label multi-horizon comparison. The shared 2/5/10/20-session panels contain 35,680/35,680/35,680/35,440 rows with zero label-alignment error. Validation selected 0.25%/0.50%/1.00%/1.00% ranking fractions, respectively. Later historical tests were: 2 sessions: 8 trades, +5.722688% mean, +5.491405% median, 75.00% wins, -1.361301% drawdown; 5: 12, +2.870035%, +1.616327%, 58.33%, -3.687501%; 10: 29, +2.228394%, +0.055641%, 51.72%, -25.612709%; 20: 15, +21.161918%, +8.734997%, 60.00%, -17.635991%. Classify every result `RESEARCH_HOLD`: 2/5/20 have insufficient later-test sample sizes, and 10 breaches the -20% risk limit. The 20-session result is a lead for a separately frozen future journal, not a model promotion. The builder CLI now exposes and validates `--horizon-sessions`; 17 targeted tests passed. No paper/live settings changed.
- 2026-07-29: Audited and corrected the multi-horizon evaluator. The initial 10- and 20-session split logic allowed a future label window to cross a chronological boundary, and all initial cutoffs were selected before applying the five-position portfolio capacity. Those 10/20 outputs are invalidated. The trainer now purges partitions using `future_market_date`; selection now applies capacity before the validation gate; and portfolio marking accepts the report target field. The separate corrected run confirms: 2-session and 5-session variants pass validation but each has only 12 later test trades, so both remain `RESEARCH_HOLD`; 10-session and 20-session variants fail every corrected validation gate. No model, engine, paper account, live setting, or historical source file changed.
- 2026-07-29: Added a research-only, validation-frozen score-percentile basket evaluator for the corrected multi-horizon models. It fixes score boundaries at validation percentiles 0/50/60/70/80/90/100, applies the five-position capacity constraint within each basket, and reports later-period outcomes without selecting a basket from them. The two-session later period favored 90-100 (+1.318479% mean, +0.671846% median, 55.19% wins), while the five-session period favored 80-90 (+2.110527%, +2.068533%, 60.81%) and the 90-100 basket was negative (-1.257186%, -2.703701%, 38.18%). This supports the need for calibration and prospective comparison, but is post-hoc diagnostic evidence only. Do not replace a frozen cutoff, enable orders, or turn these observed bins into a rule.
- 2026-07-29: Applied the same frozen basket diagnostic to six prior boundary-audited Nasdaq models. Their later-period strongest bucket was consistently 90-100: complete-101 +4.818933% mean/+3.055499% median/61.43% wins (70 capacity-limited trades); QQQ-relative +3.033299%/+1.115288%/51.47% (68); executable-101 +2.993803%/+1.907180%/56.47% (85); one-day +0.245516%/+0.292101%/56.16% (146); ten-day +3.139300%/+1.024427%/53.90% (141); top-10 +1.571142%/+1.067001%/56.00% (75). The comparison is retrospective diagnostic evidence, not a cross-model contest or an order-authority change. The contradictory newer five-day result reinforces that raw score bands must be calibrated and tested prospectively.
- 2026-07-29: Added `journal_nasdaq_score_baskets.py`, a separate append-only prospective-study path for all 101 stocks under the frozen complete-101 and QQQ-relative models. It freezes validation percentile boundaries at 0/50/60/70/80/90/100, records every complete-universe model score and its bucket, fingerprints models/reports, enforces a one-calendar-day freshness limit, and marks every row `research_only` / `execution_decision: AVOID`. Its dry run scored 202 model-symbol observations with no writes; current local data maps to the July-27 market session and is two days old, so the script correctly refuses to start the journal until a fresh complete Schwab panel arrives. This is evidence collection only, not paper or live trading.
- 2026-07-29: At Jeff's request, collected an independent Alpha Vantage compact-daily archive for all 101 Nasdaq symbols after the Schwab panel lagged. The source-separated archive at `D:\AlientAI\Data\AlphaVantage_2026\nasdaq100_score_baskets_daily_20260729` completed 101/101 symbols with zero failures and has a common July-29 date. Its separately labeled July-29 technical panel has 101 rows and zero missing symbols. Do not merge it into the frozen Schwab journal or use it to evaluate Schwab candidates: it is a current source-coverage backup pending a dedicated source-consistency review.
- 2026-07-29: Added and ran `score_alpha_vantage_nasdaq_snapshot.py` after acquiring same-source Alpha Vantage QQQ daily history. It scored all 202 model-symbol combinations for the two frozen Schwab-trained 101-stock Nasdaq models against the complete Alpha Vantage July-29 panel, explicitly as a source-shift diagnostic. Both models rank NBIS first and put NBIS/MU/WDC/CRWV in their top five. These are current research rankings only: this snapshot cannot determine model quality, modify the Schwab prospective journal, or authorize paper/live orders. Future outcomes from a single frozen source are still required.
- 2026-07-30: Jeff directed Alpha Vantage to be the default source for all future data work. This changes no existing Schwab-based artifact: frozen studies must remain source-isolated rather than being completed or re-scored with Alpha Vantage data. New collectors, panels, and experiments must identify Alpha Vantage provenance explicitly; do not begin a new Schwab download without a later explicit direction.
- 2026-07-30: At Jeff's explicit direction, formally started the separate forward-only journal for the frozen 80-security Nasdaq champion. The Schwab access token was refreshed through the existing refresh-token flow, and the append-only daily refresher added 92 completed rows across all 80 frozen symbols with zero failures. A new tested `--max-candle-date` gate excluded any later in-progress candle. The first source-consistent observation uses stored archive date 2026-07-29 / actual market session 2026-07-30 and records PLTR as the sole score above the already locked `0.15986412677273237` cutoff. The fingerprinted observation is pending for its five-session close outcome, explicitly non-executing, and does not change the model, cutoff, paper account, engine settings, or live-trading state.
# Verified AI/Semiconductor catalyst study (2026-07-31)

- Completed 1,694/1,694 Alpha Vantage historical news windows with zero failures.
- Built a 17-symbol, 125-date, executable five-session panel using next-open entry,
  fifth-close exit, and 0.25% round-trip cost.
- Compared technical, premarket, unusual-call, and analyst-action-proxy ablations
  on purged chronological splits.
- Only the technical+premarket validation-selected top-10% basket stayed slightly
  positive on held-out data (+0.50% mean net across 28 rows). This is preliminary
  and is not authorized for paper trading.
- Full evidence: `AI_SEMICONDUCTOR_CATALYST_REPORT_20260731.md`.

## Twenty-minute follow-up

- Built a leakage-safe 09:30-open to 09:45-bar-close target using Alpha Vantage
  five-minute data and 0.25% round-trip cost.
- Shifted all technical and unusual-call inputs to the immediately preceding
  session; only 09:25 premarket fields come from the current morning.
- The technical+premarket validation-selected daily top-10% policy produced
  +0.52% mean daily net across 20 held-out dates, 70% positive days, +10.62%
  compounded return, and -4.56% max drawdown.
- This is promising but too small for paper-trading authorization. Freeze and
  gather prospective evidence. See `AI_SEMICONDUCTOR_20MIN_REPORT_20260731.md`.

## One-hour follow-up

- Repeated the same three leakage-safe models from 09:30 open to the 10:25 bar
  close, with 0.25% round-trip cost.
- The technical+premarket+prior-day-unusual-call validation-selected top-10%
  policy produced +0.70% mean daily net, 65% positive days, +14.28% compounded
  return, and -5.70% max drawdown across 20 held-out dates.
- Technical+premarket was close behind at +0.62% mean daily net.
- Freeze both for prospective comparison; do not authorize execution from this
  small test. See `AI_SEMICONDUCTOR_60MIN_REPORT_20260731.md`.

## Prospective intraday program

- All six frozen 20/60-minute models now have an append-only prospective testing
  workflow.
- Weekday 09:26 ET phase records candidates using prior-session technical/call
  data and current premarket data through 09:25 ET.
- Weekday 11:26 ET phase records exact 20/60-minute Alpha Vantage outcomes.
- Frozen daily fractions: 20m technical 20%, 20m premarket 10%, 20m calls 10%;
  60m technical 50%, 60m premarket 10%, and 60m calls 10%.
- This workflow never places orders and must remain isolated from `engine.py`.
- Testing is continuous. Results are divided into permanent, sequential,
  non-overlapping 20-market-day cohorts. Completing one cohort automatically
  starts the next while retaining cumulative and prior-cohort evidence.
- Frozen models and selection fractions are never retuned between cohorts.
- 2026-07-31: Built the research-only call-option shadow layer for the six frozen
  AI/semiconductor intraday stock models. `shadow_call_options.py` freezes a
  deterministic 14-45 DTE, 0.60-0.75 delta, minimum-100-open-interest,
  maximum-10%-spread policy and prices entries at the ask and exits at the bid.
  `capture_alpha_vantage_shadow_calls.py` provides append-only entry/outcome
  capture and rejects Alpha Vantage's artificial sample schema. The current
  Alpha Vantage key was directly verified against `REALTIME_OPTIONS`; it is not
  entitled and returns four explicitly artificial contracts. Therefore option
  return capture remains fail-closed, while the six stock-model prospective
  tests continue. Do not substitute last prices, end-of-day chains, or
  retrospective contract selection. Start option capture only after a genuine
  time-stamped bid/ask source passes the validator.
- 2026-07-31: Added and directly validated
  `capture_schwab_shadow_calls.py` as the approved real-time quote adapter for
  the research-only call shadow layer. A refreshed Schwab token returned a
  genuine NVDA chain with 100 contracts across five expiration groups and all
  required bid/ask, delta, open-interest, volume, and Greek fields. The frozen
  selector chose the liquid 2026-08-21 190 call in the validation probe
  (delta 0.677, 1.98% spread, open interest 18,604). This probe is not a
  signal or journal entry. The adapter prices entries at ask and exits at bid,
  remains append-only, and has no execution path.
- 2026-07-31: The first six-model prospective morning run failed closed for a
  valid source-timing reason. A fresh 17/17 Alpha Vantage intraday download at
  09:29 ET still ended at July 30 19:55 ET; an explicit
  `entitlement=realtime` request confirmed the current key is not entitled to
  real-time US stock data. Therefore no July-31 stock signals or option entries
  were journaled. Do not fill the 09:25 Alpha Vantage premarket requirement
  with Schwab data without an explicit, source-separated protocol decision.
