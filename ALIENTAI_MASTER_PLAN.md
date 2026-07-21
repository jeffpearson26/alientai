# AlienTAI Dynamic Master Plan

Last updated: 2026-07-21 Pacific time

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

Dependencies: Phase 6 natural-universe evaluation.

Done when: A selector specification and frozen evaluation report demonstrate honest performance and acceptable risk across untouched periods and regimes.

### Phase 8 - Run prospective shadow ranking and journaling

Status: `PLANNED`

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

1. Complete the Phase 2 coverage and timestamp audit across premarket, options, news, transcripts, fundamentals, insider, short-interest, and regime data.
2. Reconcile the four unavailabilities in the completed transcript/premarket manifests and document their handling policy.
3. Preserve the premarket promotion gate result as `RESEARCH_HOLD`; do not run natural-universe expansion or enable trading from this matched-case result.
4. Audit labels, feature availability, slippage, and cost assumptions before feature-family joins.
5. After the data audit, create the two new research feature families: public unusual-options positioning around known catalysts, and point-in-time cross-symbol lead-lag relationships.

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
- 2026-07-21: Built and ran a point-in-time historical-news compiler over the completed archive. It produced 1,518 rows, 1,438 with at least one usable article, and filtered every article at or before the archived request cutoff. No future-dated article was found in this archive. The result remains a partial feature family pending exact-scope coverage and controlled joins.
- 2026-07-21: Audited the transcript archive and collector selection logic. The collected files are current 2026 Q1 transcripts by symbol; the archive does not retain the historical research-event request timestamp or a transcript publication timestamp. It is unsuitable for the 2022-2026 historical study. Any transcript feature requires a separately rebuilt event-time archive using a conservative post-earnings availability policy.
- 2026-07-21: Added and tested a first lead-lag discovery tool using the existing Dow-30 daily library and SPY as a market control. It checks 1/2/3/5/10-session delays, controls for the target's current return, and applies a conservative Bonferroni filter across 4,350 pair/lag tests. Candidate selection now uses only the first two chronological partitions; the third is held out and cannot influence selection. The initial pass selected 270 candidates, of which 265 (98.15%) retained direction in the held-out partition. This remains a research inventory, not a result or a signal: approximate correlation p-values do not resolve serial dependence, sector effects, or economic value.
- 2026-07-21: Built a dedicated 11-ETF GICS sector reference library (47,355 daily feature rows) and added fail-closed static Dow-30-to-sector mappings to the lead-lag tool. The sector-controlled rerun selected 107 candidates, versus 270 with only the SPY control; 106 (99.07%) retained their train direction in the held-out partition. The removed candidates demonstrate why common sector motion must be controlled. The retained list is still a hypothesis inventory, not a model feature or trading signal: the mapping is a current research classification rather than point-in-time GICS history, and rolling-window stability plus economic-value tests remain required.
- 2026-07-21: Added a three-window rolling pre-test stability gate to lead-lag selection. It uses only the first two chronological thirds and requires every rolling pre-test correlation to agree in direction before the final third is inspected. The sector-controlled Dow-30 rerun retained 106 candidates; 105 (99.06%) retained their direction in the held-out partition. This is a stricter screening result, not evidence of profitability; the next gate is a cost-adjusted economic-value simulation with symbol and regime concentration checks.
- 2026-07-21: Ran the required causal, cost-adjusted held-out economic-value check for all 106 sector-controlled, rolling-stable Dow lead-lag hypotheses. The simulation observes the source at its close, enters the later target at its open, exits at that target close, and subtracts a 0.25% round-trip cost. Zero of 106 candidates had positive held-out mean net return; the median candidate mean net return was -0.2274%. The lead-lag inventory is therefore not promoted to a model feature or selector. Keep the tool only as a negative-result research record unless a materially different, preregistered data scope is proposed.

## Direction-change log

- 2026-07-20: Jeff established a single mandatory dynamic roadmap that every future AI task must read and maintain. The initial roadmap consolidates the existing research priorities, safety gates, data-collection phases, evaluation path, storage work, and future decisions.
- 2026-07-20: Added a limited TradingAgents-inspired qualitative review experiment to Phase 8. It is a shadow-only second-opinion layer for candidates already selected by AlienTAI, not a replacement signal model or execution authority. The plan explicitly avoids a wholesale repository merge, uncontrolled live-data use in historical evaluation, and reuse of unsafe credential-bearing HTTP error paths.
- 2026-07-21: Jeff determined the existing Alpha Vantage key was not compromised through GitHub and directed AlienTAI to continue using it. The roadmap no longer requires key rotation as a precondition for the resumable research-data harvest.
- 2026-07-21: Jeff added two research hypotheses to the feature roadmap: (1) publicly observable unusual options positioning around known catalysts may have incremental predictive value, and (2) some cross-symbol movements may have stable delayed lead-lag relationships. Both are explicitly framed as leakage-safe, out-of-sample market-behavior research, not as evidence of insider trading or as a basis for unvalidated trading claims.
