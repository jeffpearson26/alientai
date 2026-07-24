# AlienTAI Codex Continuation Instructions

Updated: 2026-07-21 Pacific time

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

### Active catalyst-data queue

The full matched-winner study has 13,473 unique `(symbol, market_date)` observations. Its first Alpha Vantage archive only covered 687 symbol/date pairs for both historical options and time-valid news, so do not train a combined options/news model from that small subset.

`download_alpha_vantage_event_news.py` is actively collecting full 14-day, as-of event news windows into `D:\AlientAI\Data\AlphaVantage_2026\event_news_sp500_full`. It is resumable through `manifest.json`; a provider-format normalization changes dots in share-class symbols to hyphens only in the outgoing request.

`run_full_catalyst_archive_queue.ps1` is a running fail-closed monitor. It will start the full historical-options collector only after the news manifest reaches `complete`; it stops if news reaches `failed_closed`. The planned options archive has 26,221 unique symbol/date requests and writes to `D:\AlientAI\Data\AlphaVantage_2026\historical_options_sp500_full`. Do not start a second collector while either job is running. Both are data-collection work only and never enable execution.

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

`evaluate_context_portfolio.py` implements that next diagnostic: score cutoffs are set on the earlier 60% of dates, a seven-calendar-day embargo separates the later test slice, and no more than five positions can remain open. In its 2026 run, unusual calls inside the top technical-score quartile produced 38 later-slice signals, 63.16% post-cost win rate, +3.149772% mean, +1.994354% median, -7.112770% fifth-percentile outcome, -9.136176% worst trade, and -6.093092% approximate realized-exit drawdown; this passed the research gate. The 10% and 5% variants did not pass. Treat all of this as a promising hypothesis only: the archive was already used in exploratory work, so repeat it on an independently untouched/future period before retaining any threshold or starting shadow ranking.

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
