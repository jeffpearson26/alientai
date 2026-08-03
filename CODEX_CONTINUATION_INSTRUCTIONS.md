# AlienTAI Codex Continuation Instructions

Updated: 2026-08-02 Pacific time

## Mission

Continue building AlienTAI as a research-first system for finding a very small number of unusually strong five-trading-day stock opportunities. Optimize for honest out-of-sample evidence, calibrated probabilities, realistic costs, and severe leakage prevention. Never promise profitability.

## Project locations

- Working repository: `C:\Users\jeffp\alientai_start_over_8010`
- GitHub: `https://github.com/jeffpearson26/alientai`
- Alpha Vantage OneDrive archive: `C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026`
- Python: `C:\Users\jeffp\alientai_start_over_8010\.venv\Scripts\python.exe`
- Active secrets file: `C:\Users\jeffp\alientai_start_over_8010\.env`

Never print, commit, paste, or otherwise expose API keys, tokens, OAuth codes, broker credentials, or the contents of `.env`.

## Non-negotiable safety rules

1. Keep all real trading and new paper buying disabled unless Jeff explicitly requests otherwise after reviewing evidence.
2. Do not modify `data_v2/v2_settings.json`. It contains Jeff's local safety state and is intentionally modified but uncommitted.
3. Do not modify or delete `overnight_training_queue_summary.json`; it is an untracked user artifact.
4. Preserve unrelated dirty-worktree changes. Stage only files created or intentionally changed for the current task.
5. Never delete raw research data, OneDrive archives, model artifacts, or project files merely to free space without explicit approval.
6. Never use future information in a feature. Every feature must have a documented availability timestamp and be available before the simulated decision cutoff.
7. Keep winner/control studies research-only. Ex-post winner option returns are payoff demonstrations, not predictive proof.
8. Use chronological train/validation/test splits, whole timestamps, embargoes, realistic costs, and natural-universe final evaluation.
9. Test and compile every change, run `git diff --check`, then commit and push only the intended files.
10. Do not start a second Alpha Vantage master queue if one is already running.

## Current live state

Verified on 2026-07-21 after the master queue completed:

- No Alpha Vantage master queue or child collector is running. Do not restart it without first inspecting the completed manifests and deciding on a new, separately scoped collection.
- Master queue Phases 1 and 2 completed.
- Matched premarket archive completed all 10,289 deduplicated requests: 10,245 complete and 44 unavailable.
- Historical options completed all 2,951 requests with 0 unavailable.
- Event news completed all 1,518 requests with 0 unavailable.
- Earnings transcripts completed 597 requests with 3 unavailable.
- Phase 5 completed its feature/label builds and uploaded 135,925 earnings-event rows to Supabase. Phase 6 did not make additional API calls because the premarket promotion gate returned `RESEARCH_HOLD`.
- The HTTP 503 traceback issue was corrected in the collectors and both known local log copies were replaced with non-secret incident notices. The existing Alpha Vantage key is present only in ignored `.env`, is absent from Git history, and Jeff explicitly authorized its continued use on 2026-07-21. The queue may resume once no duplicate process is running.

Inspect live state rather than assuming these counts remain current. Do not reproduce the sensitive legacy log line.

### Current runtime handoff (August 2)

- August 3 morning preflight is complete for every input that can exist before
  the live session. `ai_semiconductor_technical_2026-07-31.jsonl`,
  `ai_semiconductor_option_features_2026-07-31.jsonl`, and
  `ai_semiconductor_call_features_2026-07-31.jsonl` each contain the exact
  17-symbol frozen universe with zero missing rows. The July 31 Alpha Vantage
  option collection completed all 17 requests with zero unavailable/failed.
  The active automation now runs at 05:26/06:26/08:26/14:26 Pacific on market
  weekdays. It advances the frozen daily programs pre-open and after-close in
  addition to the six-model intraday run, preserves append-only sequential
  cohorts indefinitely, and must still fail closed unless each frozen source
  and timing contract is satisfied. Alpha Vantage must supply all 17
  current-session intraday series through exactly 09:25 Eastern and complete
  outcome bars. Four legacy 06:00-06:31 Windows tasks were disabled to prevent
  API contention and accidental engine/server startup. No settings, model, or
  trading state changed.

- The stratified, research-only Alpha Vantage news collector for 22,918 requests
  is currently stopped. Its verified manifest is `failed_closed` at 15,745
  completed, 3 unavailable, and 1 failed request
  (`AZO|2026-04-27T20:00:00+00:00`) after a credential-redacted
  `ChunkedEncodingError`; no matching Python process exists. It is not required
  by the August 3 six-model intraday run. Do not restart it before that run or
  blindly resume it: first inspect the manifest/logs, preserve the completed
  keys, verify no duplicate, and treat completion only as
  `completed + unavailable == 22,918` with zero failures.
- The broad archive at `D:\AlientAI\Data\AlphaVantage_2026\natural_event_news_2026` remains intentionally paused and must not be resumed. After the stratified collector truly completes, compile its features, exact-key join them to its own `requests.jsonl`, and run the timing/coverage audit before specifying any chronological ablation.
- The research-only prospective pick competition is frozen in `PICK_COMPETITION_RULES.md`. `record_pick_competition.py` journals zero-to-five immutable picks before 09:25 ET from the exact 101-symbol Nasdaq universe. Its pure outcome scorer requires explicit timestamped price facts, keeps missing horizons pending, subtracts 0.25% round-trip cost, and never infers a stop from a later close. It has no paper/live order path.
- No Uvicorn/Python application server is currently listening on port 8010. The preserved settings still have stock paper trading enabled and option paper buying disabled. Do not restart casually: first perform the read-only restart review in the master plan, preserve positions and limits, verify stale payloads remain `AVOID`, start through the loopback-only launcher, and retain an immediate rollback path. Do not change `data_v2/v2_settings.json`.
- Schwab was reauthorized on July 30 for the local daily research path. The frozen July-21 contextual-options pilot now has all five later sessions through July 28 and is complete: 5 signals, 1 date, 80.00% post-cost wins, +1.894382% mean net return, +3.080338% median, and -13.815280% worst trade. This is not enough evidence to promote: the fixed prospective gate remains `RESEARCH_HOLD` for minimum sample/date diversity and fifth-percentile tail. Do not tune from these five outcomes or change paper settings.
- A July-30 fixed historical holdout check used an early-2026 calibration boundary and a later-2026 holdout for the already specified unusual-call plus top-5% technical-context rule. The later holdout contained 94 signals across 41 exit dates and showed +1.482190% post-cost mean, +0.847123% median, and 54.2553% wins, but its legacy full-notional cohort drawdown was -25.957771%. It remains research-only and must not select a new threshold; the result is support for continuing the prospective journal, not a promotion.
- August 2 priority is prospective evidence, not new variants. Limit active predictive work to the frozen Nasdaq five-session journals, the six frozen AI/semiconductor 20/60-minute models, and the frozen contextual technical-plus-unusual-call study. The Alpha Vantage 09:25 ET entitlement/timeliness check remains a hard blocker for the intraday program; fail closed on delayed data. The full repository discovery suite passed 611 tests.
- The repository now contains a tested native Alpha Vantage bulk-quote replacement and a loopback/token control boundary, but those changes are not active until a controlled server restart. Wait for the news collector to finish, capture the five positions, stop only the exact Uvicorn process tree, restart through `START_ALIENTAI_V2.bat`, verify `/api` and local control behavior, make one bounded quote validation, then restore/verify the paper engine without changing its allowlist or settings.
- Do not copy the ignored legacy quote implementation back into active code. `alientai_v2/schwab_client.py` is now only a compatibility adapter to the Alpha Vantage client.

### Check whether the queue is running

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'run_alpha_vantage_all_remaining|download_alpha_vantage' } |
  Select-Object ProcessId, ParentProcessId, Name, CommandLine
```

### Read the fundamental manifest safely

```powershell
$p = 'C:\Users\jeffp\OneDrive\AlienTAI_Data\AlphaVantage_2026\fundamental_snapshots_2026-07-19\manifest.json'
$j = Get-Content $p -Raw | ConvertFrom-Json
[pscustomobject]@{
  Status = $j.status
  Completed = @($j.completed).Count
  Unavailable = @($j.unavailable).Count
  Failed = @($j.failed).Count
  Updated = $j.updated_at_utc
}
```

Do not name a PowerShell helper function `R`; `R` is an alias for `Invoke-History`.

### Restart with the authorized existing key only if no master process exists

The collectors are resumable and skip completed/unavailable requests and existing files. The existing key in `.env` is authorized by Jeff; never print, copy, or commit it. The legacy logs have already been sanitized.

```powershell
cd C:\Users\jeffp\alientai_start_over_8010
$out = Join-Path (Get-Location) 'alpha_vantage_all_remaining_resume2.log'
$err = Join-Path (Get-Location) 'alpha_vantage_all_remaining_resume2.error.log'
Start-Process powershell.exe `
  -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path (Get-Location) 'run_alpha_vantage_all_remaining.ps1')) `
  -WorkingDirectory (Get-Location) `
  -WindowStyle Hidden `
  -RedirectStandardOutput $out `
  -RedirectStandardError $err
```

If a collector reports a rate limit, do not classify it as unavailable. Stop, increase delay, and resume. Invalid symbol/endpoint combinations such as `INCOME_STATEMENT|BCOR` are correctly classified as unavailable by commit `b16a434`.

## Alpha Vantage master queue

`run_alpha_vantage_all_remaining.ps1` sequentially runs:

1. `run_alpha_vantage_month_harvest.ps1`
   - Winner historical options
   - Russell and S&P earnings
   - Earnings estimates, shares outstanding, and institutional holdings
2. `run_alpha_vantage_month_harvest_phase2.ps1`
   - Russell and S&P financial statements and overviews
   - Market-regime archive
3. `run_alpha_vantage_month_harvest_phase3.ps1`
   - Full S&P matched winner/control five-minute extended-hours history
   - Matched winner/control historical option chains
   - Matched event news
4. `run_alpha_vantage_month_harvest_phase4.ps1`
   - Matched point-in-time earnings transcripts
5. `run_alpha_vantage_month_harvest_phase5.ps1`
   - Premarket feature build
   - Fundamental feature build
   - Option-chain feature build
   - Historical call evaluation
   - Earnings upload to Supabase
6. `run_alpha_vantage_month_harvest_phase6.ps1` (called conditionally by Phase 5)
   - Reads the premarket promotion gate
   - Makes no additional API calls when status is `RESEARCH_HOLD`
   - On `RESEARCH_PASS` only, downloads natural-universe extended-hours history and builds compact features and tradable labels
   - Calibrates all three ablation models on natural-universe rows and evaluates untouched cost-adjusted test slices
   - Builds a fail-closed prospective shadow policy; even a pass permits ranking/journaling only and cannot enable paper or live orders

The extended-hours collector will deduplicate 18,326 matched rows into approximately 13,473 symbol-month requests. It stores compressed CSV files in OneDrive under `matched_premarket_5min`.

Large premarket collectors enforce free-space floors on the archive drive: 6 GB for the matched study and 8 GB for conditional natural-universe expansion. A low-space stop is an intentional fail-closed event; preserve the manifest, move or free storage safely, and resume.

On 2026-07-26 Jeff explicitly requested the focused natural-universe premarket download needed by the selective five-day challenger. A single resumable collector was started for the 44,683-row 2026 natural options/technical panel: 3,381 deduplicated symbol-month requests, stored at `D:\AlientAI\Data\AlphaVantage_2026\selective_natural_premarket_5min_2026` with a 20 GB free-space floor. Monitor that manifest and never launch a duplicate. On clean completion, compile point-in-time features through 09:25 ET for every exact `(symbol, market_date)` key, retain explicit unavailable rows, validate coverage, and only then rerun `train_selective_five_day_challenger.py --premarket-features ...`. The matched winner/control premarket table remains forbidden for this natural training.

The focused collection and compilation are now complete: 3,367 downloaded symbol-months, 14 explicit unavailabilities, zero failures; 44,683 exact feature rows, 44,371 available. `evaluate_selective_premarket_continuation.py` uses the leakage-safe next-open-to-fifth-close label and 0.25% cost. A >=1% premarket gap showed +0.6776% validation mean and +0.6261% untouched-test mean (860 test rows, 53.60% wins), but >=5% gaps reversed in test (-1.3397% mean, 33.33% wins). Preserve the raw continuous premarket features and their missing flags for the challenger; do not turn any threshold from this audit into an execution rule.

`evaluate_selective_premarket_same_day.py` tests the stricter same-session alternative: enter on the first 09:30 five-minute bar close, exit on the 16:00 bar close, and deduct 0.25%. Of 44,683 feature rows, 44,484 have strict labels and 199 are excluded. The >=1% cohort failed replication (+0.1922% validation mean versus -0.3514% untouched-test mean). Do not use premarket gap as a standalone same-day rule. The premarket-enabled five-day challenger trained on 114 columns and all 44,116 valid labeled keys but still selected zero candidates under the frozen gates, so its status remains `RESEARCH_HOLD`.

The generic leakage-safe label now permits a two-session horizon while preserving the five-session wrapper/default. A one-time fixed-slice evaluation trained all four current challenger heads on identical 44,116-row, 114-column data. Only the large-move classifier showed consistent top-1% mean returns: +0.8623% validation and +0.8709% untouched test (57 rows each), with 57.89% test wins. Test AUC was only 0.5705 and the other heads did not replicate consistently. Keep this as a preregistered future-period lead; do not retune against the already observed test or enable execution.

`build_selective_two_day_shadow_policy.py` freezes the validation-only top-1% large-move cutoff at 0.3647459048971379 and requires at least 95% universe coverage. Its generated policy is research-only, fingerprints the model, permits any number of independently qualifying observations, and cannot create orders. Do not alter the cutoff using historical test results; score only genuinely future complete-universe panels and journal outcomes after the two-session horizon matures.

Use `score_selective_two_day_shadow.py` only on a newly built, one-date complete feature panel. It rejects mixed dates, duplicate/blank symbols, and coverage below 95% of the expected universe. It keeps all scores at or above the frozen cutoff and writes research-only shadow observations; it has no engine or order path. Do not backfill old dates through this prospective scorer.

`alientai_v2/research/multi_horizon_pullback.py` defines the new trend-plus-dip feature contract: positive log-price slopes at 20/63/126 sessions, price above the 126-session mean, a 1%-12% pullback from the 20-session high, and negative five-session return. It also preserves all underlying continuous slopes, mean distances, pullback depths, and volatility for learning. This is research-only and has no buying path. Do not start its training concurrently with the active Russell Transformer; once resources are free, build chronological two- and five-session recovery panels and compare them with costs.

The legacy 20-day Transformer architecture now has a separately generated two-day trainer, `train_v2_transformer_2day_sp500_from_supabase.py`. It cannot accept another horizon and writes only under `data_v2/transformer_2day_sp500_supabase_training` with `transformer_2day_*` artifacts. Its defaults use a one-session step, 12-calendar-day embargo, and four-calendar-day non-overlap. Never point the original 20-day trainer at a two-day horizon because its fixed output names would overwrite historical artifacts.

The full two-day Transformer run completed on 2026-07-27 with 2,233,585 windows across 496 symbols. Epoch 2 won validation at threshold 0.55 (+0.234609% mean net across 1,966 signals), but the untouched test failed: -0.121585% mean net, 48.8854% cost-adjusted win rate, 0.909755 profit factor across 1,929 signals; non-overlapping mean was -0.124948%. Preserve the artifacts as negative evidence. Do not promote, integrate, or retune this model using its observed test.

Do not use `train_v2_transformer_20day_russell_from_supabase.py` for a two-day experiment: that legacy file has only an 80/20 train-validation split and lacks the current embargo, untouched test, cost-adjusted checkpoint, and scaler safeguards. The isolated replacement is `train_v2_transformer_2day_russell_from_supabase.py`, generated from the validated S&P two-day pipeline with separate Russell artifacts. Screen the full Russell list first at `--step-days 3 --epochs 3`; run the much more expensive one-session/five-epoch design only if the untouched screening test passes.

The Russell screening run completed with 879,971 windows across the 1,909-symbol request list. The validation-selected threshold-0.55 checkpoint averaged only +0.021583% net and failed untouched test at -0.021745% mean net, 48.5507% cost-adjusted wins, and 0.985305 profit factor across 31,499 signals; non-overlapping mean was -0.020699%. The screening gate failed. Preserve the artifacts as negative evidence and do not launch the exhaustive Russell run.

## Completed research infrastructure

- Leakage-safe five-day LightGBM baseline
- Isolated five-day Transformer trainer
- Big-winner reverse lookup with date-matched controls
- Exceptional-winner LightGBM classifier and natural-universe calibration
- SEC Form 4 open-market purchase normalization and features
- Earnings history, earnings estimates, shares outstanding, and institutional holding features
- Historical options-chain collection and realistic call evaluation
- Pre-move option-chain features
- News and earnings-transcript collectors
- Market-regime archive covering rates, GDP, inflation, labor, oil, and commodities
- Premarket extended-hours collector
- Leakage-safe premarket feature builder with a strict 9:25 a.m. Eastern cutoff
- Matched-case premarket ablation trainer comparing technical-only, premarket-only, and combined models on identical chronological splits
- Tradable premarket target builder using the first regular five-minute bar close as entry and the five-day exit-session close as exit
- Shadow signals, cost-adjusted outcome evaluation, and engine scorecards
- Fail-closed engine and main-account buying gates

## Important current findings

- The existing five-day S&P LightGBM target-2% artifact is `RESEARCH_HOLD`. The new report-only locked-threshold audit selects 0.60 from validation (44 signals), then finds only two matching historical test signals with -0.895205% average net return after the stated 0.25% cost. Do not promote or integrate it; require a separately pre-registered fresh period before reconsidering it.
- The locked-threshold S&P target-3% five-day LightGBM report is a research hypothesis only; its historical test period is already observed and portfolio tail/concentration behavior has not been audited. The legacy Russell target-2% report is `RESEARCH_UNTRUSTED_PENDING_DATA_INTEGRITY_AUDIT`: it uses a stale legacy universe, carries an incorrect S&P build label, and includes economically implausible five-day return aggregates. Do not treat either as a model selection or shadow-ranking decision.
- The active S&P five-day LightGBM and 20-day Transformer source paths now reject any feature-plus-label window containing an adjacent daily-candle gap over five calendar days. This was added after the legacy Russell archive exposed multi-month/year row gaps that could turn a fixed row offset into a false fixed-session outcome. Do not use old artifacts generated before this guard without a separate integrity review and retraining.
- The isolated five-day S&P Transformer and legacy Russell Transformer copy have also been updated with the same continuity rule; do not bypass the protected trainers by using an older duplicate script.
- The Russell liquidity preflight now also requires continuous history: a trailing 20-row dollar-volume window and its five-session diagnostic both reject any adjacent gap over five calendar days. Its latest report has 4,088,044 continuous windows and 2,162,577 eligible windows; these are data-quality counts only, not a tradable Russell universe or model evidence.
- The Russell price-discontinuity audit now applies the same five-calendar-day continuity rule to one- and five-session review windows. Its corrected 50% report has 1,630 one-session and 7,588 five-session events, after excluding 6,888 discontinuous windows. These remain review flags, not automatic corporate-action labels or source-data edits.
- `validate_current_universe_manifest.py` is the required fail-closed entry point for a future Russell/current-small-cap source. Do not use `russell_2000_symbols.txt` as current membership. A supplied snapshot must document the as-of date, retrieval timestamp, source name/URL, and tickers before later membership/eligibility construction can begin.
- `download_iwm_holdings_snapshot.py` can turn a manually downloaded IWM holdings CSV into a validated current equity-holdings proxy. iShares currently returns HTML bot protection to its automated CSV URL, so do not bypass it; use `--input-csv` and `--source-url` after a normal browser download. This proxy is only for current/prospective coverage, never official historical Russell membership.
- `audit_russell_split_ratio_candidates.py` found 308 continuous one-session moves near common split/reverse-split ratios, with 1,537 discontinuous rows skipped. Treat every result as a review flag only; do not edit raw candles or exclude events until independently verified corporate-action data is available.
- The Alpha Vantage `SPLITS` archive for all 85 symbols behind the 308 flags is complete at `D:\AlientAI\Data\AlphaVantage_2026\russell_split_history_2026`: 2 flags have a date-and-factor match, 9 date-only, and 297 unmatched. `compare_russell_split_history.py` is read-only. Do not adjust raw candles or retrain; this result strengthens the need for a separate clean historical-universe design.
- The dated Alpha Vantage `LISTING_STATUS` archive is complete at `D:\AlientAI\Data\AlphaVantage_2026\listing_status_annual_2010_2026`: 17 June-30 snapshots from 2010–2026 plus four current reference/calendar files, 12.19 MB uncompressed, no recorded error. It is reference data for future survivorship checks only, not Russell membership or an approval to train.
- `audit_russell_listing_status_coverage.py` confirms the stale 1,909-symbol list is not temporally stable: 1,179 symbols are active US stocks in its 2010 snapshot versus 942 in 2026. This is further evidence not to train from it as a historical Russell universe.
- `audit_alpha_vantage_unavailability_policy.py` records three transcript gaps (ADSK 2025Q1, AES 2024Q1, AWK 2025Q3) and 44 premarket gaps across BF.B, BRK.B, COR, and EG. Future joins must keep explicit missingness; do not zero-fill, substitute current data, or rename existing archive keys in place.
- `audit_matched_catalyst_panel.py` passed the 18,326-row full matched catalyst panel: no duplicate keys, malformed/as-of-date-mismatched rows, or future news. It has 13,473 unique symbol/date observations and 113 rows without option-chain detail, which must remain missing. It is valid only for matched-case ablation—not a natural-universe probability or trading result.
- `audit_natural_panel_integrity.py` passed the 44,683-row natural options/FINRA panel: all keys unique, every five-day label is future-dated, no decision timestamp is after market date, and no available FINRA report is later than its decision date. This is a timing-integrity result only; FINRA remains `RESEARCH_HOLD` for the tested configuration.
- SEC Form 4 purchase features are leakage-safe in targeted tests. The natural 2026 holdout showed a modestly positive large-purchase association but no useful clustered-purchase result; retain open-market large purchases as a future pre-specified interaction only, never a standalone selection rule.
- The 2026 later-holdout earnings-event study is negative after costs (48 events, -0.512161% mean and -0.227877% median five-day net return). Do not create a standalone earnings-beat selector; use earnings only as a contextual feature in a later locked experiment.
- The Alpha Vantage macro/regime archive is not point-in-time eligible for historical model joins: it contains observation dates but no original publication-time, vintage, or revision history. Keep it prospective-only until a vintage-aware source is obtained.
- The July 21 contextual-options research payload has five pending, non-executing observations. Re-evaluate it only after five later trading sessions have local daily-candle coverage; do not infer results early or route it into a paper-trading journal.
- Natural frequency of a 10% five-day S&P winner in the evaluation universe: approximately 3.30%.
- Highest-ranked reverse-lookup slices reached approximately 8.7% to 12.5% exceptional-winner frequency, roughly 2.6 to 3.8 times enrichment.
- This is not yet a deployable strategy: median returns were often negative and approximate drawdowns were excessive.
- The most repeatable pre-move signature so far is elevated ATR/realized volatility/wider Bollinger Bands combined with a short-term pullback, low RSI(2), and price below the short EMA.
- Insider purchases were weak and inconsistent as a standalone discriminator. Keep them as an interaction feature, not a mandatory gate.
- Earnings beat streaks and large EPS surprises showed modest promise in a small pilot, but require broader out-of-sample validation.
- Winner-only call-option simulations showed large returns, but they are ex-post payoff studies and must never be described as predictive performance.

## Highest-priority work after downloads

### 1. Validate premarket data coverage and features

Run the Phase 5 premarket builder after Phase 3 completes. Audit:

- Coverage by year, symbol, winner/control role, and event date
- Bar counts and missing prior close
- Correct exchange-local timestamps
- No bars later than 09:25 Eastern
- Corporate-action anomalies
- Sparse premarket trading and zero-volume bars

Premarket features already include gap, session return, 30/60-minute momentum, range, volume, dollar volume, relative volume, VWAP, and last-price-versus-VWAP.

The initial read-only coverage audit is implemented by `audit_matched_research_coverage.py`. On 2026-07-21 it verified 18,326 unique composite matched-study rows with no feature/label row loss and zero recorded timestamps after the 09:25 Eastern cutoff. It found 16,971 available premarket feature rows (92.606%) and 18,244 available open-entry labels (99.553%). Its report is intentionally not sufficient to approve joins: option and fundamental feature files use different scopes and still require point-in-time join design.

Schema audit detail: the 18,326-row base study already holds technical, short-interest, and insider fields. The current `historical_option_features_matched.jsonl` has only 1,837 rows from a smaller matched study, and `current_fundamental_snapshot_features.jsonl` is a July-2026 cross-sectional snapshot without historical event identities. Do not join either file to the full historical premarket study. Rebuild exact-scope historical feature tables with availability timestamps first. The harvested news records include `time_published` and ticker sentiment. The transcript archive is current 2026 Q1 by symbol and lacks historical request/publication timestamps, so it is not eligible for the 2022-2026 study; rebuild it with a conservative post-earnings availability rule before joining.

`compile_historical_news_features.py` compiles the harvested news archive with a strict `time_published <= as_of_utc` filter. On 2026-07-21 it generated 1,518 rows, of which 1,438 had at least one usable article; no future-dated archive article was found. Treat this as partial event-time coverage and preserve missingness when joining it to a study.

Phase 5 also runs `train_matched_winner_premarket_ablation.py`. It compares precision and cost-adjusted return slices (mean, median, win rate, fifth-percentile loss, and worst trade) at identical top-score fractions. Its output is explicitly a matched case-control feature-family comparison and is not a calibrated natural-universe probability.

The ablation report contains a fail-closed `premarket_promotion_gate`. It permits deeper natural-universe evaluation only when the combined model independently beats the technical baseline on validation and test exceptional-winner rate and mean net return, has a positive median net return, at least 30 top-1% signals, and no worse fifth-percentile loss. A pass never enables trading.

### 2. Audit the re-anchored prediction labels for premarket decisions

`build_matched_premarket_labels.py` now creates a separate leakage-safe target using the close of the first regular-session five-minute bar as entry and the final regular-session bar on `future_market_date` as exit. Missing entry/exit history is excluded, not labeled negative. Audit coverage and timestamps, then include slippage and round-trip costs in natural-universe evaluation. Do not allow the model to receive credit for a move that occurred before its entry.

### 3. Join feature families without creating giant duplicate files

Prefer keyed compact feature tables joined by `study_event_id`, symbol, and timestamp. Avoid repeatedly materializing the existing 800 MB base research rows. Candidate families:

- Technical price/volume
- Premarket movement and relative volume
- Earnings history and estimate revisions
- Point-in-time news sentiment
- Point-in-time transcripts
- Insider open-market purchases only
- Short interest
- Historical option positioning
- Market regime
- Public unusual-options positioning around known catalysts: preserve the public snapshot timestamp, contract structure, volume/open interest, unusualness, and catalyst timing; evaluate fixed-horizon stock and option outcomes with costs. Do not allege or infer insider trading from a pattern.
- The completed 2,951-request matched-event option archive includes point-in-time volume, open interest, strike, expiration, bid/ask/last/mark where available, implied volatility, and Greeks. It can support initial cross-sectional positioning features, but it cannot establish a contract's normal prior volume from one snapshot. Schedule a separate resumable prior-snapshot option-history collection only after the Phase 2 audit confirms the required public timestamps, storage budget, and event/control universe.
- Cross-symbol lead-lag relationships: evaluate whether a source symbol's abnormal move adds incremental point-in-time information for a target symbol at 1, 2, 3, 5, or 10 trading-day lags after controlling for the target's own history, broad market, sector, and known catalysts. Use rolling chronological validation and expire unstable edges.

### 4. Run ablation experiments

Do not blindly train all 127 combinations first. Use staged ablation:

1. Technical baseline
2. Premarket alone
3. Technical plus premarket
4. Add catalyst data (news/earnings)
5. Add options and short interest
6. Add fundamentals and regime interactions
7. Add unusual-options/catalyst and lead-lag feature families only through controlled ablations with matched controls and untouched chronological test periods.

Promote a feature family only when it improves untouched chronological validation and test periods, not merely training metrics.

### 4a. Lead-lag hypothesis discovery

`discover_lead_lag_candidates.py` is a research-only discovery tool. It uses daily returns, removes the target symbol's current return, and then checks source-to-target 1/2/3/5/10-session relationships across three chronological partitions. Candidate selection uses only train/validation and a conservative Bonferroni filter; the final partition is held out and only reported.

The initial SPY-controlled Dow-30 scan selected 270 candidates from 4,350 tests, and 265 retained direction in the held-out window. Sector residualization is now implemented with a 47,355-row 11-ETF GICS reference library and the static `dow30_sector_etf_map.json` research mapping. In its first sector-controlled rerun, 107 candidates remained and 106 retained direction in the held-out window. It fails closed by skipping unmapped/missing-sector pairs. This mapping is a current research classification, not point-in-time GICS history.

A further three-window rolling pre-test gate now requires every pre-test correlation to agree with the selected train direction. It retained 106 sector-controlled Dow candidates, 105 of which retained direction in the final held-out third.

The required causal economic-value evaluation is now complete in `evaluate_lead_lag_economic_value.py`: it observes the source at close, enters the target at a later target-session open, exits at that target close, calibrates its signal threshold only on pre-test data, and subtracts a 0.25% round-trip cost. All 106 candidates were negative by held-out mean net return, with a -0.2274% median candidate mean. Do not promote this lead-lag inventory into any model, selector, paper account, or trading logic. Preserve it as a documented negative result; revisit only for a materially different, preregistered research design.

### Completed catalyst-data archives

The full matched-winner study has 13,473 unique `(symbol, market_date)` observations. Its first Alpha Vantage archive only covered 687 symbol/date pairs for both historical options and time-valid news, so do not train a combined options/news model from that small subset.

`download_alpha_vantage_event_news.py` collected full 14-day, as-of event-news windows into `D:\AlientAI\Data\AlphaVantage_2026\event_news_sp500_full`. Its manifest is complete: 13,473 completed, zero unavailable, and zero failed. It remains resumable if a future separately authorized extension is required; a provider-format normalization changes dots in share-class symbols to hyphens only in the outgoing request.

`run_full_catalyst_archive_queue.ps1` is a fail-closed queue monitor, but it is not currently running. The full historical-options archive at `D:\AlientAI\Data\AlphaVantage_2026\historical_options_sp500_full` also completed: 26,221 completed, zero unavailable, and zero failed. Do not start either completed collector again unless a separately authorized extension is needed. Both archives remain research data only and never enable execution.

### Existing exceptional-winner baseline

`two_stage_exceptional_winner_10pct/two_stage_report.json` is not promotable. Its untouched full-universe test selected 417 signals and had mean net return 0.6124% after the stated 0.25% cost, but median net return was -0.1315%, win rate 48.44%, worst trade -23.47%, and approximate cohort drawdown -37.30%. Do not select this model for paper or real trading. A positive average alone is insufficient; future gates must require positive median results, acceptable tail loss/drawdown, concentration controls, and fresh chronologically held-out evidence.

### Completed catalyst ablation; natural-universe gate remains

`matched_winners_catalyst_full.jsonl` now joins all 18,326 matched study rows to full-coverage point-in-time news and historical option features. Its unique underlying symbol/date feature coverage is 13,473 for base, news, and options, with no duplicate catalyst keys. `compile_historical_option_features.py` deliberately emits one option row per symbol/date so matched-study duplication cannot multiply features during a join.

The chronological held-out matched discovery ablation reports are under `data_v2\rcef_research\catalyst_ablation`:

- Technical top-1% precision: 37.78%.
- Technical + news: 40.00%.
- Technical + options: 48.89%.
- Technical + news + options: 46.67%.

Options improved the top-5% matched precision from 31.42% to 41.59%. This is promising hypothesis-generation evidence only. It cannot be treated as a probability, expected return, or trade criterion because the input is matched case-control sampling. Do not promote it. The next research requirement is an independently time-valid natural-universe panel with matching option features, followed by calibrated, cost-adjusted, tail- and drawdown-constrained evaluation.

Natural-universe gate completed 2026-07-23: the bounded 2026 collector accounted for all 44,709 requests (44,683 completed, 26 unavailable, zero failures). `compile_historical_option_features.py` produced `data_v2\rcef_research\natural_option_features_2026.jsonl` with 44,683 rows. Reports are `data_v2\rcef_research\natural_options_2026_evaluation.json` and `data_v2\rcef_research\unusual_call_outcomes_2026.json`.

Neither is promotable. The technical-plus-options model's daily top-1 had +1.348659% mean net return but a -0.267803% median, 46.875% post-cost win rate, -15.214847% fifth-percentile outcome, and -50.164499% approximate drawdown. The unusual-call rule was modestly enriched versus the natural universe (4.9677% vs. 3.4756% exceptional-winner rate; +0.147209% vs. +0.042264% mean net return), but had a -0.091622% median, 49.081% post-cost win rate, -27.693938% worst trade, and -28.770658% drawdown. Preserve options as a conditional feature family for future ablations; do not use either result as a standalone selector or trading input.

`evaluate_unusual_call_contexts.py` now explores unusual calls only after an independent technical-only score, explicitly as a diagnostic rather than a threshold-selection tool. On the same natural panel, unusual calls in the top technical-score 10% had 161 signals, +1.395004% mean net return, +1.483193% median, and 55.90% post-cost win rate; the top 5% had 83 signals, +1.976916% mean, +2.451422% median, and 59.04% post-cost win rate. Each still returned `RESEARCH_HOLD` solely due to excessive approximate cohort drawdown (-50.333635% and -39.000164%). The next required validation is chronological threshold selection plus a non-overlapping, capital-constrained portfolio simulation; do not retain these score fractions as final settings.

`evaluate_context_portfolio.py` implements the capacity-limited, chronological unusual-call diagnostic. Its reports now fingerprint model and input artifacts. An older output that reported a pass cannot be reproduced from the current saved model and is invalid for promotion. The fingerprinted current-model top-quartile run has 39 later-slice signals at 0.25% cost, +1.704715% mean, +0.034788% median, 51.28% post-cost win rate, and -21.630095% drawdown—therefore `RESEARCH_HOLD`. It also remains `RESEARCH_HOLD` at 0.50% and 1.00% cost. Do not retain a threshold, start shadow ranking, or change execution from this exploratory archive.

`audit_promotion_evidence.py` fail-closes promotion review for reports that lack required artifact identities or risk metrics, or whose historical gate is not `RESEARCH_PASS`. The current fingerprinted contextual-options report has complete identities and metrics, but all three variants are still ineligible because their gates are `RESEARCH_HOLD`. Its output never enables paper/live trading.

`audit_model_inventory.py` scanned 58 local research reports on 2026-07-24: seven contain rare-signal gates, zero are reproducible historical passes, and the lone non-fingerprinted historical pass is already invalid. No report is eligible for promotion review.

`refresh_sp500_daily_incremental.py` is the safe local daily-refresh path: it appends only dates newer than each existing Schwab CSV, preserves history, does not upload to Supabase, and stops on the first HTTP 401. Its initial dry run on 2026-07-24 found the Schwab token expired, so do not launch a full refresh until Jeff renews the token.

`alientai_v2/research/contextual_options_shadow_policy.py` freezes the candidate logic without wiring it into runtime: complete same-day input only; unusual public call activity; daily top technical-score quartile; maximum five candidates. Every emitted row keeps `decision="AVOID"` and uses `shadow_research_decision="BUY_CANDIDATE"`; it has no broker, order, network, or settings-write path. Do not integrate it into `engine.py` until a point-in-time current-data adapter provides complete same-day option activity and technical scores, with a dedicated test and a new review of the prospective-shadow gate.

`contextual_options_shadow_adapter.py` is the validation-only boundary for that future current-data feed. It accepts a local JSONL panel only if it contains one market date, at least 400 unique symbols, all required score/unusualness/history fields, and at least 90% with ten prior call-volume observations. It produces a `research_payload_ready` JSON artifact but neither contacts a provider nor writes to the shadow journal. The current live Schwab options engine is insufficient because it intentionally scans only a small configured basket; do not use it as the complete-universe source.

`download_alpha_vantage_option_panel.py` is the reusable bounded collector for a complete S&P symbol/date panel. It reads an explicit symbols file and inclusive date range, uses the existing credential-safe `run` archive function, skips prior completed/unavailable entries, and writes only compressed raw option snapshots plus a resumable manifest. The planned forward-history extension is 2026-07-03 through 2026-07-22 into the existing `D:\AlientAI\Data\AlphaVantage_2026\historical_options_natural_sp500_2026` archive. Do not start another collector concurrently. On completion, compile the extended feature panel and use a separate, point-in-time daily technical panel builder before calling the validation-only shadow adapter.

The July 3–22 extension completed on 2026-07-23: the shared archive manifest reports 51,619 completed requests, 33 unavailable requests, and zero failures. The raw archive is ready, but `sp500_full_rows.jsonl` currently ends on 2026-07-01. Do not compile or evaluate the July 3–22 option rows against that stale base panel. First build a complete point-in-time daily technical/label panel through the extension dates, then compile the matching option features and validate it through the research-only adapter.

### 5. Build the rare-signal selector

Jeff prefers a few outstanding opportunities over many mediocre picks, but the system must allow multiple signals when several independently meet the same stringent standard. Calibrate probabilities on the natural universe. Evaluate top fractions and minimum sample sizes. Report mean, median, win rate after costs, tail loss, drawdown, turnover, symbol concentration, and regime stability.

`alientai_v2/research/rare_signal_gate.py` is the common fail-closed gate for this work. It evaluates a metrics object and returns `RESEARCH_PASS` or `RESEARCH_HOLD` with every check and failure reason preserved. Its default policy requires: 30 signals, 50% post-cost win rate, non-negative mean and median net return, fifth-percentile loss no worse than -10%, worst trade no worse than -25%, approximate cohort drawdown no worse than -20%, and no single symbol above 20% of signals. These thresholds are research safeguards, not performance claims. Both natural-options-panel and unusual-call reports now include this gate. A pass is still historical research only and never changes execution.

### 6. Analyst upgrades

The provider-neutral schema and Benzinga/FMP normalizers exist in `alientai_v2/data/analyst_ratings.py`. No structured event feed is currently being collected. Alpha Vantage does not expose a dedicated analyst-upgrade history. Do not infer upgrades from headlines if a structured source can be obtained.

`download_benzinga_analyst_ratings.py` is ready but must not be run until Jeff explicitly purchases access and places `BENZINGA_API_KEY` or `BENZINGA_TOKEN` in the active `.env`. It archives resumable 30-day windows as compressed raw-plus-normalized JSONL without exposing the token.

Recommended future source: Benzinga Ratings API, contingent on Jeff reviewing price. Preserve:

- Announcement timestamp UTC
- Firm and analyst
- Action
- Original old/new rating wording
- Normalized score separately
- Old/new price targets and currency
- Importance and analyst accuracy when licensed

Do not purchase a subscription without Jeff's explicit approval.

## Tests for recently added components

```powershell
cd C:\Users\jeffp\alientai_start_over_8010
.\.venv\Scripts\python.exe -m unittest -v `
  test_fundamental_snapshot_downloader.py `
  test_alpha_vantage_market_regimes.py `
  test_alpha_vantage_matched_premarket.py `
  test_premarket_features.py `
  test_compile_fundamental_snapshot_features.py

.\.venv\Scripts\python.exe -m py_compile `
  download_alpha_vantage_fundamental_snapshots.py `
  download_alpha_vantage_market_regimes.py `
  download_alpha_vantage_matched_premarket.py `
  build_matched_premarket_features.py `
  compile_fundamental_snapshot_features.py

git diff --check
```

Run broader targeted suites for any modules changed. Do not run live collectors inside unit tests.

The credential-safe Alpha Vantage request layer is covered by `test_alpha_vantage_http.py`. On 2026-07-20, its targeted 39-test downloader suite and the full 249-test repository suite passed; all changed collectors compiled and `git diff --check` passed.

## Git discipline

Before editing:

```powershell
git status --short
git log -5 --oneline
```

Expected local user-owned changes at handoff:

```text
 M data_v2/v2_settings.json
?? overnight_training_queue_summary.json
```

Leave them alone. Stage explicit filenames, never `git add -A`, and inspect the staged diff before committing.

## Current research boundary: matched premarket labels

`audit_matched_premarket_labels.py` is the required first audit before any new matched-study premarket feature ablation. Its July 24 report found 28 unique nonstandard-session labels: nine have a first regular bar later than 09:30 ET and 20 have a final bar earlier than 16:00 ET (one row is in both groups). Arithmetic, date ordering, and row keys otherwise pass. Do not silently fill or relabel these observations. A future research panel must explicitly exclude those 28 rows or rebuild their intraday bars from a verified source, then rerun the audit before evaluating any technical/premarket interaction.

The trainer now applies that exclusion itself. The corrected July 24 rerun still returns `RESEARCH_HOLD`; do not retry thresholds or launch natural-universe premarket collection from this already-observed matched study. A materially new, preregistered data scope is required before revisiting the family.

The regenerated report fingerprints its three input datasets and saved model artifacts with SHA-256. Treat any premarket result without those identities as nonreproducible and ineligible for promotion review.

## Daily-price refresh status

On July 24, the local Schwab daily archive was renewed through 2026-07-22 for all 483 available S&P histories. `refresh_sp500_daily_incremental.py` is append-only and now supports `--only-before-date YYYY-MM-DD` to safely resume only stale existing files. It does not upload to Supabase. Do not treat one later close as a five-day outcome: the five July-21 contextual-options shadow observations remain pending until five subsequent trading sessions are available.

`evaluate_contextual_options_shadow_payload.py` now records interim observed session returns for pending payloads, but only emits `realized_return_pct` and counts a record complete at its fifth later session. Do not aggregate or promote interim observations.

`download_alpha_vantage_daily_research_fallback.py` archives raw Alpha Vantage daily responses for an explicitly research-only payload to `D:\AlientAI\Data\AlphaVantage_2026\prospective_daily_research_fallback`. It is a source-separated fallback; never merge its rows with Schwab results or use it to fill missing Schwab candles. Its July 24 archive covers TEL, NXPI, CPRT, URI, and TSCO through July 23.

`audit_daily_price_source_alignment.py` found the Alpha Vantage daily source is systematically one Schwab session behind across the July-24 reference archive. It fails closed for same-day research use. Do not use Alpha Vantage daily dates to evaluate these prospective payloads unless a separately reviewed source-date reconciliation is completed.

`evaluate_contextual_options_prospective_gate.py` is the only route from completed contextual-options shadow outcomes toward paper-review consideration. It accepts only source-tagged Schwab review files, rejects duplicates/unapproved sources, requires 30 completed signals across at least 10 decision dates, and applies the rare-signal gate after the stated round-trip cost. Its output never enables paper trading; Jeff must separately review any future `RESEARCH_PASS`.

On 2026-07-29, `refresh_sp500_daily_incremental.py --apply` stopped safely on QQQ with `Schwab HTTP 401 unauthorized`. It added zero rows. Renew the existing Schwab access token before retrying this append-only refresh; do not use the source-separated Alpha Vantage daily fallback to complete Schwab-only prospective outcomes.

The existing refresh-token utility succeeded later that day. The correct full 483-symbol refresh, explicitly using `sp500_expanded_symbols.txt`, appended 885 newer Schwab rows with zero failures. The dated July-21 contextual-options payload now has four later sessions for each of its five records and remains pending its fifth; do not aggregate or promote interim returns. The refresher's default `sp500_symbols_used.txt` currently contains only `QQQ`, so every S&P-wide run must supply the explicit 483/496-symbol file or a separately validated source manifest.

`build_local_technical_training_rows.py` now exposes `--horizon-sessions` and records it in the generated summary. The July-29 isolated 80-security Nasdaq multi-horizon experiment is at `data_v2\rcef_research\nasdaq80_multi_horizon_executable_20260729`. It used next-open entry, QQQ-context technical features, fixed later-session exits, 0.25% cost, and validation-only cutoffs. Its 2/5/10/20 later-test samples are only 8/12/29/15 trades. Preserve all four as `RESEARCH_HOLD`; do not tune them on the observed historical period or connect any to paper/live execution. The 20-session output has promising but insufficient evidence and may only receive a separately frozen future-only journal after a dedicated review.

`build_local_schwab_daily_technical_panel.py` creates a source-labeled, research-only technical panel from `data_v2\sp500_daily_schwab_max_history`, without updating Supabase. The July-22 run produced 483 rows. Raw natural options snapshots cover July 22, but `natural_option_features_2026.jsonl` ends July 2; a full history-aware compilation step is required before a new complete daily contextual-options panel or payload is allowed.

`compile_natural_options_daily_panel.py` now provides that compilation for a requested later date. Its July-22 run yielded 483 rows, using only earlier compiled call-volume history plus raw snapshots strictly after the older history boundary. Join it to the equally sized local Schwab technical panel only as a historical backfill/research validation; do not count it toward the frozen prospective gate because the decision date was already observed when joined.

`build_contextual_options_backfill_panel.py` is the exact-key, fingerprinted join/score validation path. It requires complete equal technical/options keys and applies only the frozen technical artifact. Its July-22 result is `BACKFILL_RESEARCH_ONLY` (22 unusual calls; five within the daily top technical quartile) and must never be written as a shadow payload or included in `evaluate_contextual_options_prospective_gate.py`.

The July-23 full S&P option-snapshot collection completed cleanly on 2026-07-24: all 496 requested symbols were archived at `D:\AlientAI\Data\AlphaVantage_2026\historical_options_natural_sp500_2026`, with zero unavailable requests and zero failures. The process has exited. Do not compile it into a contextual panel or prospective payload yet: the point-in-time local Schwab daily source ends on July 22, so there is no same-date technical panel to join without mixing timing. When a local Schwab July-23 close becomes available, build the matching local technical panel first, then compile the July-23 option features with history strictly before that date, and use the dedicated validation-only adapter.

`prepare_natural_event_news_requests.py` creates a deterministic, point-in-time news request list from a base research panel. The July 24 run produced 44,683 unique requests from `D:\AlientAI\Data\FINRA_Short_Interest\features\natural_options_finra_research_panel_2026.jsonl`, preserving `symbol`, `market_date`, and `as_of_utc` at `D:\AlientAI\Data\AlphaVantage_2026\natural_event_news_2026\requests.jsonl`. A natural-news collector may use this list only with `download_alpha_vantage_event_news.py --role all`, writes raw archives only, and must never be connected to execution. Any later join must preserve the original cutoff and be evaluated as a separately pre-specified chronological research study.

The broad natural-news archive at `D:\AlientAI\Data\AlphaVantage_2026\natural_event_news_2026` is intentionally paused after 2,130 completed requests, zero unavailable, and zero failures. Do not restart it automatically or use this early-date partial archive for model evaluation: it lacks sufficient chronological coverage. Preserve its raw files and manifest as a pipeline artifact. Any future news experiment must first define a smaller, time-stratified request sample and its evaluation plan before downloading more data.

`build_natural_news_research_panel.py` is the exact-key post-collection join. Supply the existing natural base panel and the output of `compile_historical_news_features.py`; it keys both sources by `(symbol, as_of_utc)`, preserves missing archive responses explicitly, and rejects duplicate or extra feature rows. Use only after the complete archive has been compiled; then perform a timing/coverage audit before any pre-specified chronological ablation. It cannot score, train, contact a provider, change settings, or execute anything.

## Default market-data source (July 30, 2026)

Jeff directed that all new collection, feature-building, and research work use Alpha Vantage by default. Existing Schwab-based frozen prospective studies and historical artifacts remain source-isolated; never substitute Alpha Vantage candles into them. Do not start a new Schwab downloader or use Schwab as a fallback unless Jeff later explicitly changes this direction.

`alientai_v2/alpha_vantage_quote_client.py` is the active-code replacement for the ignored legacy Schwab quote bridge. It uses the credential-safe shared HTTP layer and the premium `REALTIME_BULK_QUOTES` endpoint in chunks no larger than 100 symbols. `alientai_v2/schwab_client.py` remains only as a backward-compatible import adapter. Do not reintroduce dynamic loading from `old_system_reference`.

`alientai_v2/control_auth.py` protects mutating `/v2/` requests. Localhost callers are allowed; remote callers must supply the configured `ALIENTAI_CONTROL_TOKEN` in `X-AlienTAI-Control-Token`, and remote mutations fail closed when no token is configured. `START_ALIENTAI_V2.bat` binds to `127.0.0.1`. Do not weaken these defaults to expose the control plane publicly. The public informational page is separate from control endpoints.

The July-30 critique remediation passed 24 focused tests and all 557 discovered repository tests, plus Python compilation and `git diff --check`. `requirements.txt` now declares NumPy, pandas, LightGBM, PyTorch, and schwab-py for reproducible fresh installs. The large `routes/` tree, patch/fix scripts, backup-named files, duplicated trainer families, broad exception handling, and oversized settings remain technical-debt work; audit reachability and provenance before quarantining anything, and never mass-delete them.

Methodology reminder: the large retrospective model/search surface relative to the strongest cohorts is a genuine multiple-testing risk. Retrospective results may generate hypotheses, but only predeclared prospective journals and untouched chronological evidence may support promotion.

`audit_natural_news_research_panel.py` is the required timing/coverage gate after the exact join. It requires unique `(symbol, as_of_utc)` keys, explicit missing-data reasons, and no latest visible article timestamp after the row cutoff. Its JSON report records coverage only. A successful audit does not establish predictive value; the next step remains a separately specified chronological ablation with costs and risk gates.

Current highest-priority research lead: the frozen technical-context plus unusual-call portfolio produced positive mean and median net returns and over-50% post-cost wins at three fixed chronological calibration splits (40%, 50%, and 60%), but every result is `RESEARCH_HOLD` solely for approximate cohort drawdown worse than -20%. Treat this as a robustness clue, not a threshold-selection result or trading model. The next allowed experiment is a separately specified portfolio/risk design aimed at reducing drawdown, followed by prospective non-executing shadow evidence; do not alter engine behavior or paper-buy settings.

The first fixed capacity test (one, two, and three concurrent positions) did not resolve the issue. One position reduced drawdown to -16.933569% but supplied only 8–12 signals, below the 30-signal minimum. Two and three positions had sufficient or near-sufficient samples in some splits but drawdowns roughly -25% to -30%. Do not adopt a capacity setting from this already-observed diagnostic; it rules out simple capacity reduction as the complete solution.

`contextual_options_stop_evaluator.py` is a research-only fixed-stop diagnostic. It uses local Schwab OHLC data, handles adverse opening gaps conservatively, and leaves original position capacity unchanged so an early stop cannot create extra entries optimistically. The initial -5%, -7.5%, and -10% stop test on the fixed 50% split did not pass: drawdowns were -33.61%, -27.04%, and -34.98%. Do not apply these stop levels to `engine.py` or settings based on this result.

The current AI/semiconductor thematic basket experiment is negative. `research_universes/ai_semiconductor_screen_2026.txt` is a documented current basket only, not historical membership. Across fixed 40%/50%/60% chronological splits, the top-quarter contextual model had 46.67%, 42.86%, and 36.36% win rates with too few signals and negative medians in every split. Do not create a sector-specific AI/semiconductor version of the model from this result.

`FROZEN_CONTEXTUAL_OPTIONS_STUDY.md` is now the controlling low-cost prospective-study protocol. Do not restart broad collectors or tune this hypothesis. Generate only non-executing complete-universe payloads when matching same-day local Schwab technical and option panels are available, evaluate only five-session local-Schwab outcomes, and use the existing prospective gate. The study ends at 30 completed candidates across ten decision dates; a pass requires separate human risk/paper-trading review, while a failure ends this hypothesis without post-hoc changes.

`FIVE_DAY_SELECTIVE_CATALYST_STRATEGY.md` defines a separate future challenger; it does not modify the frozen study. `alientai_v2/research/selective_five_day_policy.py` is its pure scored-row contract. It requires one complete same-day universe plus validation-frozen thresholds for calibrated profit probability, calibrated large-move probability, expected net return, lower-quantile net return, and model disagreement. Technical/options evidence must agree. It retains every independently qualifying row rather than enforcing a quota, but all rows remain `decision="AVOID"` and research-only. Missing scores, duplicate symbols, mixed dates, or incomplete coverage fail closed. Do not train or connect this challenger until its point-in-time feature/label inputs and chronological experiment are separately approved; the module itself cannot load models, contact providers, write settings, or execute.

`alientai_v2/research/five_day_open_close_labels.py` is the challenger's pure label-timing contract. It decides after a daily close, enters at the next regular-session open, exits at the fifth regular-session close, subtracts the specified round-trip cost, and excludes invalid or discontinuous windows. It is not connected to the existing trainers; do not replace historical labels or retrain until a separately frozen experiment and exact input panel are approved.

`alientai_v2/research/selective_five_day_panel.py` is the challenger's pure exact-key join. It requires matching unique symbol/date keys, timezone-aware `as_of_utc` and `decision_cutoff_utc`, feature availability no later than the cutoff, and valid future label dates. It rejects label/future/entry/exit outcome fields on the feature side. This is the required boundary before any future training-panel materialization; it currently performs no file, model, settings, or execution writes.

Jeff explicitly authorized the first isolated selective-challenger training run on 2026-07-26. `train_selective_five_day_challenger.py` joined 44,116 corrected local labels to the existing natural technical/options panel and used 26,340/5,753/5,787 chronological train/validation/test rows with 12-calendar-day embargoes. The positive classifier stopped at iteration 1 and validation-calibrated positive probability never reached the frozen 0.60 gate; the untouched test therefore emitted zero candidates. Keep the report as `RESEARCH_HOLD`. Do not lower thresholds, add features, or reuse this now-observed test for model selection. Artifacts are isolated in ignored `data_v2/selective_five_day_challenger_training`.

The validation-only component audit found the positive classifier is worse than random (AUC 0.4834) and both return regressors have negative validation correlation. The large-move classifier is the only component showing a possible lead (AUC 0.5670; validation top 1%: 57 rows, 64.91% large moves, +8.800797% mean net return, +5.503135% median, 75.44% wins). This is validation hypothesis evidence only; do not apply a new rule to the observed test.

Premarket support is available through `alientai_v2/research/selective_premarket_features.py` and the trainer's `--premarket-features` argument. It requires exact natural-universe keys, explicit missing rows, and 09:25 ET timestamps and rejects `study_*` fields. The current `matched_premarket_features.jsonl` is prohibited: it is a winner/control table and overlaps only 3,350 of 44,683 natural keys (7.4973%). A complete point-in-time natural premarket table is required before retraining.

`train_multi_horizon_pullback.py` is the completed isolated uptrend-dip experiment. It uses 20/63/126-session log-price slopes, pullback/distance/volatility features, next-open entries, two- and five-session exits, 0.25% round-trip cost, chronological 60/20/20 partitions, 12-calendar-day embargoes, and validation-frozen top-5% score cutoffs. Its 135,713-row S&P run failed untouched testing: two-day mean net return -0.064428% with 48.05% wins on 1,028 rows; five-day mean net return -0.055000% with 47.62% wins on 1,136 rows. The rule-only slices were also negative. Preserve `RESEARCH_HOLD`; the observed test cannot be used for tuning, and this model must not enter `engine.py` or paper/live trading.

`evaluate_context_portfolio.py --daily-dir data_v2\sp500_daily_schwab_max_history` adds a daily mark-to-market, capital-scaled five-slot curve while retaining the old full-notional cohort approximation for auditability. Because the research panel's nominal dates are not uniformly aligned to the local archive, the simulator does not apply a blanket date offset: it must locate the exact stored entry close and label-implied exit close within a narrow date window, and it fails closed if either anchor is absent. It allocates at most one-fifth of marked equity and no more than cash, leaves unused slots in cash, never borrows, and charges the supplied cost on exit. At the frozen top-quarter cutoff, all selected trades have zero label-alignment error and the capital-scaled research gate passes all three splits: 40% (59 signals, +31.006419% portfolio return, -9.883183% drawdown), 50% (49, +25.073189%, -9.883183%), and 60% (39, +13.611174%, -10.757040%). Mean net trade returns were +2.439161%, +2.420582%, and +1.704715%, respectively. This corrects the risk diagnosis but does not make the explored archive prospective or authorize paper trading. Continue only through `FROZEN_CONTEXTUAL_OPTIONS_STUDY.md` and the non-executing prospective gate.

On July 27 the existing Schwab refresh token successfully produced a new access token, and the append-only refresher added one row to all 483 existing S&P histories with zero failures. `contextual_options_shadow_review_2026-07-27.json` now observes two later sessions for each July-21 pilot candidate but zero completed five-session outcomes; `contextual_options_prospective_gate_2026-07-27.json` correctly remains `RESEARCH_HOLD`. Wait for three more Schwab sessions before evaluating the fixed outcomes. Do not treat the interim values as completed evidence and do not manufacture a retrospective payload for July 22/23.

Capital-scaled portfolio reports fingerprint the complete Schwab daily directory with `daily_archive_sha256`; the strict July-27 483-file identity begins `75b25e35e451`. Reject any future comparison that omits the daily archive identity, has nonzero label-alignment error, or silently uses different candles.

`export_contextual_options_selected_events.py` reproducibly exports the frozen 60%/top-quarter/five-slot cohort for instrument-payoff research. Its July-28 output contains 39 events across 31 symbols and fingerprints the same base rows, option features, and technical model used by the portfolio study. Running `evaluate_historical_calls.py` against `historical_options_natural_sp500_2026` produced 30 valid trades for each fixed policy (37 complete chain pairs; two missing). Both policies fail a typical-trade test despite positive means: ATM-30d median -26.056060% / 40.00% profitable; delta60-30d median -16.697239% / 43.33% profitable. Treat the positive means as winner-skew, not a pass. Do not enable options paper buying or tune strikes/expiry on this observed cohort.

`evaluate_afterhours_premarket_continuation.py` is the fixed-threshold, research-only test of the prior 16:05-19:55 ET session plus the current 04:00-09:25 ET session. It reads the existing extended-hours archive, requires complete 09:30 and 16:00 bars, subtracts 0.25% round-trip cost, and reports chronological partitions. Its July-28 run labeled 44,484 rows. All full-history joint 1.5x/2x/3x/5x relative-volume thresholds were negative after costs. The untouched 5x joint subset had 70 rows, -0.450914% mean net return, -0.127161% median, and 48.57% net wins. This rejects unusual extended-hours volume as a standalone same-day long rule. Preserve it only as contextual evidence for a future pre-specified multivariate experiment; do not tune these observed thresholds or connect the evaluator to paper/live trading.

The evaluator now also separates an explicitly named directional buy-volume proxy: volume on rising five-minute closes is buy proxy and volume on falling closes is sell proxy. This is not true exchange-classified aggressor-side volume. The fixed rule requires positive price pressure, at least 60% buy-proxy share, and unusual buy-proxy volume in both sessions. Every threshold remained negative. Untouched results were 1.5x: 81 rows, 39.51% net wins, -0.266448% mean; 2x: 48, 41.67%, -0.389225%; 3x: 32, 34.38%, -0.831475%; 5x: 11, 45.45%, -0.355808%. Do not tune the observed rule. A future directional-volume study requires true trade-and-quote classification or a separately frozen interaction with catalyst/options/technical context.

`evaluate_unusual_call_60day_outcomes.py` tests whether the existing leakage-safe three-sigma unusual-call definition precedes large 60-session stock gains. It reconciles every entry to the exact stored close, requires all 60 later trading sessions, fingerprints the daily archive, and reports both terminal return and maximum close reached. The July-28 run had 28,608 complete rows and 1,184 unusual calls. Full-history unusual calls versus the universe reached +20% at 23.1419% versus 21.2703%, +30% at 12.5845% versus 11.5317%, and +50% at 4.9831% versus 4.7155%; mean terminal net return was +3.4872% versus +3.3044%. These are small lifts and were not stable across chronological thirds. Treat unusual calls as weak contextual enrichment only. Do not promote a 60-day rule, tune the three-sigma definition, or interpret overlapping symbol/date rows as independent statistical trials.

`evaluate_analyst_upgrade_same_day.py` reads only explicitly parsed old-to-new rating headlines and uses return metrics only when the announcement was timestamped before 09:30 Eastern. The unofficial archive has zero exact Hold-to-Strong-Buy events. For Hold-to-Buy it has 402 events, 277 premarket, but only 42 unique symbol-days with matching prices in the current S&P survivor archive. Those 42 averaged -0.069222% open-to-close with 50% positive outcomes and -0.191087 points versus their prior-20-session intraday mean. Do not infer a same-day analyst edge from this small survivor-biased sample. The exact Strong Buy question remains unanswered pending a licensed structured feed and broader historical price coverage including delisted/non-current names.

## Nasdaq executable-label correction (July 28)

`build_local_technical_training_rows.py --entry-assumption next_regular_session_open` now preserves the decision close for technical features while labeling entry at the next session's open and exit at the fifth later session close. It records explicit entry date/price and `holding_sessions=5`. `evaluate_context_portfolio.py` now supports those explicit open entries, marks them to each session close, and retains legacy close-entry behavior for prior reports. `evaluate_nasdaq100_clone_portfolio.py` now fails closed unless a selected validation fraction has the minimum signal count, positive mean and median net return, and at least a 50% net win rate.

The isolated complete-101 executable result is at `data_v2\rcef_research\nasdaq100_executable_101` (ignored generated data). Validation selected top 0.25% / `0.23346458789809038`: 21 signals, +6.281492% mean, +4.771091% median, 76.19% wins. Its later test is `RESEARCH_FAIL_EXECUTABLE_LABELS`: 11 signals, +3.580862% mean, **-1.292366% median**, 45.45% wins, +7.376964% capital-scaled return, -13.018128% drawdown, and zero label-alignment error. Do not paper-enable or tune it. The frozen QQQ-relative challenger now fails the stricter validation-quality gate. The legacy paper champion and all account/settings files remain unchanged. A trading-session runtime exit mechanism has not been activated because it would alter existing paper behavior and cannot rescue the failed executable-label challenger.

## Multi-horizon correction (July 29)

The July-29 80-security 2/5/10/20-session comparison must use only the corrected artifacts at `data_v2\rcef_research\nasdaq80_multi_horizon_purged_capacity_20260729` (ignored). The older `nasdaq80_multi_horizon_executable_20260729` 10- and 20-session reports allowed label windows to overlap partition boundaries, and every old cutoff was chosen before applying the five-slot capacity constraint. Treat its headline 10- and 20-session results as invalid.

The corrected trainer purges based on every preceding row's `future_market_date`; the evaluator capacity-limits validation selections as well as test selections; and capital-scaled marking reads the report's actual target key. All 31 focused tests and Python compilation passed. Corrected validation leaves 2-session and 5-session variants eligible, but their later tests each contain only 12 capacity-limited trades: 2-session +5.634527% mean / +3.891531% median / 83.33% wins; 5-session +2.870035% / +1.616327% / 58.33%. Both remain exploratory `RESEARCH_HOLD`. Corrected 10-session validation fails all slices on negative median and sub-50% win rate. Corrected 20-session validation fails all slices on insufficient capacity-limited signals or negative median/win rate. Do not enable, tune, or paper-trade any of these variants; do not modify settings.

`evaluate_score_percentile_baskets.py` is the research-only counterpart to confidence-bucket analysis. It freezes raw score thresholds from the validation distribution at 0/50/60/70/80/90/100 score percentiles, then applies those same thresholds to later rows. These are score percentiles, not calibrated probabilities. Each basket is capacity-limited independently so its results describe a hypothetical portfolio that selected only that band. The corrected 2-day later period has its strongest broad basket at 90-100 (+1.318479% mean, +0.671846% median, 55.19% wins); the corrected 5-day later period has its strongest at 80-90 (+2.110527%, +2.068533%, 60.81%), while 90-100 is negative (-1.257186%, -2.703701%, 38.18%). This is a useful warning against assuming the very top raw score is always best, but the later period has already been examined. Do not use these results to select a live/paper threshold; evaluate the predeclared buckets on new prospective observations instead.

The same basket audit was safely reproduced on six prior Nasdaq artifacts whose saved label windows do not cross their split boundaries. In their already-observed later periods, all six have their strongest bucket at 90-100: complete-101 (+4.818933% mean, +3.055499% median, 61.43% wins, 70 capacity-limited trades), QQQ-relative (+3.033299%, +1.115288%, 51.47%, 68), executable-101 (+2.993803%, +1.907180%, 56.47%, 85), one-day (+0.245516%, +0.292101%, 56.16%, 146), ten-day (+3.139300%, +1.024427%, 53.90%, 141), and top-10 (+1.571142%, +1.067001%, 56.00%, 75). These reports do not override their individual research statuses or authorize a model/basket choice. The difference from the newer five-day 80-symbol model is precisely why future observation must track fixed percentile bands rather than presume monotonic score quality.

`journal_nasdaq_score_baskets.py` is the forward-only companion study for score-percentile bins. It reuses only the two frozen complete-101 Nasdaq artifacts, computes each model's validation-score boundaries at 0/50/60/70/80/90/100, and appends all 101 scores per model for a fresh complete daily universe. It records model/report fingerprints, the score percentile basket, same-day score rank (not a probability), and `execution_decision: AVOID`; it cannot place paper or live orders. It refuses a panel older than one calendar day. As of July 29, a dry run scored 202 rows but made no output directory, manifest, or journal write because the newest common local session was July 27 (two calendar days old). When the next Schwab refresh makes a fresh complete common date available, run this journal once; never backfill July 27 after its date has been observed.

Jeff requested an alternate source while the Schwab panel lagged. `download_alpha_vantage_daily_panel.py` completed an independent 101/101 compact-daily archive, zero failures, at `D:\AlientAI\Data\AlphaVantage_2026\nasdaq100_score_baskets_daily_20260729`; all 101 share common daily coverage through July 29. `build_alpha_vantage_daily_technical_panel.py` produced its 101-row, zero-missing July-29 panel in that same folder. This archive is explicitly source-separated and cannot extend, evaluate, or replace the Schwab-only prospective journal. Use it only as current coverage backup unless a separately tested source-consistency protocol is approved.

`score_alpha_vantage_nasdaq_snapshot.py` is the explicit source-shift diagnostic for that panel. After acquiring QQQ from the same Alpha Vantage endpoint, it scored both frozen Schwab-trained complete-101 Nasdaq models across all 101 July-29 rows (202 observations) without writing an order, journal entry, or Schwab artifact. Both models rank NBIS first; the baseline top five are NBIS/MU/WDC/TER/CRWV and the QQQ-relative top five are NBIS/WDC/MU/CRWV/SNDK. The output remains under the Alpha Vantage archive and declares `execution_decision: AVOID`. Do not call these scores a model comparison or use them to pick a paper/live trade: they only demonstrate current model agreement under a changed data source.

## Frozen Nasdaq-80 champion prospective journal (July 30)

`journal_nasdaq80_champion.py` is now the formal append-only, non-executing prospective path for model `nasdaq100_technical_clone_v1`. Its manifest freezes the exact model, training report, 80-symbol file, five-session close outcome contract, maximum five candidates, and score cutoff `0.15986412677273237`. It refuses stale data, fingerprints all frozen artifacts, deduplicates by model/date/symbol, labels score rank as not probability, and writes `execution_decision: AVOID`.

The first valid run followed an explicit Schwab refresh requested by Jeff. `refresh_sp500_daily_incremental.py` now has a tested `--max-candle-date` safety gate, and the refresh appended 92 completed rows across all 80 symbols with zero failures. The common stored archive date is 2026-07-29, which maps to actual market session 2026-07-30 under the legacy Schwab date convention. One observation, PLTR, cleared the frozen cutoff and is pending in `data_v2\rcef_research\nasdaq80_champion_prospective\journal.jsonl`; the immutable contract is in the adjacent `frozen_manifest.json`. Do not score the outcome until five later sessions exist, backfill earlier dates, alter the cutoff, convert the score to a probability, or use the observation to place an order.

Recent relevant commits:

- `0c88e0c` Build leakage-safe matched premarket features
- `1af092b` Archive matched historical premarket candles
- `b16a434` Resume past unsupported Alpha Vantage symbols
- `8190cca` Archive Alpha Vantage market regime history
- `78e5a4b` Compile Alpha Vantage fundamental snapshot features
- `bc764d8` Add pre-move historical option chain features
- `73e7e18` Add resumable master Alpha Vantage harvest queue

## Communication with Jeff

Jeff is not a programmer and benefits from concrete, short instructions. Lead with the result. If he must run something, provide one PowerShell block at a time and say exactly where to paste it. Prefer doing safe in-scope work directly. Explain failures plainly. Never imply that a research result guarantees profit.

## Deferred AI/semiconductor multi-horizon catalyst design (August 3)

Jeff asked to preserve the useful logic from an external AI/semiconductor
ranking narrative for a future model. Treat the narrative only as hypothesis
input, not as verified market data, a training label, or a recommendation.
Several cited prices and opaque third-party rankings were unsupported or
non-reproducible.

If this design is activated after the current prospective priorities mature,
pre-register separate 1-, 5-, and 20-session targets and use only
point-in-time inputs available before the decision cutoff:

- technical momentum, pullback, volatility, liquidity, and relative strength;
- premarket gap, relative volume, and directional pressure through 09:25 ET;
- known earnings proximity without using the later earnings reaction;
- publicly timestamped earnings/guidance, estimate revisions, analyst actions,
  and news;
- broad-market and semiconductor-sector regime;
- structured memory, foundry, networking, supply-chain, and hyperscaler-capex
  context when provenance and historical availability can be verified.

Require exact availability timestamps, explicit missingness, chronological
embargoed splits, validation-frozen thresholds, realistic costs, and staged
feature-family ablations. Do not use media picks, free-text recommendations,
opaque AI scores, unsupported price targets, or post-entry information. This
design is deferred and research-only; it does not alter any active model,
prospective journal, paper setting, or execution path.

The detailed feature contract, horizon-specific hypotheses, leakage controls,
ablation order, evaluation metrics, and promotion boundary are frozen in
`FUTURE_AI_SEMICONDUCTOR_MULTI_HORIZON_MODEL.md`. Use that document rather than
reconstructing the design from chat. Jeff's named recommendations remain
hypothesis context only and must never become labels or preferential ticker
weights.

# 2026-07-31 AI/Semiconductor catalyst checkpoint

- Alpha Vantage event-news archive:
  `D:\AlientAI\Data\AlphaVantage_2026\ai_semiconductor_event_news_full_20260730`
  is complete: 1,694 completed, 0 unavailable, 0 failed.
- Full Alpha Vantage daily archive:
  `D:\AlientAI\Data\AlphaVantage_2026\ai_semiconductor_daily_full_20260730`
  contains all 17 requested symbols.
- Reproducible report: `AI_SEMICONDUCTOR_CATALYST_REPORT_20260731.md`.
- Do not integrate any of these models into `engine.py` or paper trading.
- Do not select a new score fraction using the held-out partition beginning
  2026-06-04. Use a new frozen prospective period for further confirmation.
- Frozen technical+premarket prospective journal:
  `data_v2\rcef_research\ai_semiconductor_premarket_prospective_journal.jsonl`.
  The first 2026-07-30 entries are AVGO and ORCL, both pending and non-executing.
  Do not evaluate them before the fifth subsequent market-session close.
- A separate 20-minute study is documented in
  `AI_SEMICONDUCTOR_20MIN_REPORT_20260731.md`. Its leading frozen research policy
  is technical + 09:25 premarket, daily top 10%, entry 09:30 open, exit 09:45
  bar close, with 0.25% cost. It has only 20 held-out dates and is not authorized
  for paper/live execution. Never use same-day closing technical or call data.
- The one-hour extension is documented in
  `AI_SEMICONDUCTOR_60MIN_REPORT_20260731.md`. The leading historical model uses
  prior-close technical + 09:25 premarket + prior-day unusual-call features and
  a validation-frozen daily top-10% policy. It has only 20 held-out dates and is
  research-only. Preserve the 09:30-open to 10:25-bar-close timing contract.
- Active automation `score-alientai-frozen-intraday-models` runs weekdays at
  05:26, 06:26, 08:26, and 14:26 Pacific. It advances frozen daily journals
  pre-open, scores all six frozen 20/60-minute models after the 09:25 ET
  premarket cutoff, appends exact Alpha Vantage intraday outcomes after both
  horizons finish, and advances matured daily outcomes after the close.
- Prospective selections:
  `data_v2\rcef_research\ai_semiconductor_intraday_prospective_journal.jsonl`.
- Prospective outcomes:
  `data_v2\rcef_research\ai_semiconductor_intraday_prospective_outcomes.jsonl`.
- Keep the journal and outcome ledger append-only and model-specific. Never
  substitute another price source or use current-day close/call features.
- Do not stop prospective collection when the 20-day evidence gate is reached.
  `summarize_intraday_prospective.py` maintains sequential 20-day cohorts and
  cumulative evidence. A completed cohort must roll directly into the next
  collecting cohort without resetting, deleting history, or tuning models.
## AI/semiconductor call-option shadow layer (2026-07-31)

`shadow_call_options.py` and `capture_alpha_vantage_shadow_calls.py` are a
separate, research-only derivative test for the six frozen 20/60-minute stock
models. Contract selection is fixed before outcomes: calls only, 14-45 DTE,
delta 0.60-0.75 (target 0.675), open interest at least 100, quoted spread no
more than 10%, deterministic liquidity-first ranking. Conservative returns buy
at the entry ask and sell at the exit bid. Every record is `research_only` and
`execution_decision=AVOID`; there is no broker or order path.

The active Alpha Vantage key was probed on July 31. `REALTIME_OPTIONS` returned
the provider's four-row artificial example and a message requiring a 600- or
1200-request/minute realtime-options plan. The validator rejects this response.
Do not journal it, infer returns from `last`, use end-of-day historical chains
for intraday fills, or select a contract after observing the outcome. The
existing stock-model prospective automation remains active. Option capture can
start without code changes once a genuine real-time bid/ask entitlement or a
separately approved source passes the same validator.

Schwab is now that validated option-quote source:
`capture_schwab_shadow_calls.py` reads the existing refreshed `token.json`,
normalizes the genuine Schwab chain, applies the identical frozen selector, and
maintains separate append-only entry/outcome ledgers. A July-31 NVDA probe
returned 100 real contracts and selected an eligible contract, but it was not
journaled because it was not attached to a valid frozen stock signal.

The July-31 06:26 stock-scoring phase did not produce observations. The fresh
Alpha Vantage monthly five-minute archive remained one session behind and an
explicit real-time entitlement probe was denied. Preserve the fail-closed
result: no option contract may be selected without the predeclared 09:25 stock
signal. Do not silently replace Alpha Vantage premarket inputs with Schwab;
that would be a new, source-separated experiment requiring an explicit
decision and validation.
