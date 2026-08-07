# AlienTAI Codex Continuation Instructions

Updated: 2026-08-06 Pacific time

## Mandatory D-drive runtime policy (2026-08-06)

Jeff directed that AlienTAI use drive D for new storage. Before every
collector, compiler, trainer, content audit, or other potentially large
research job, dot-source:

```powershell
. .\scripts\use_alientai_d_runtime.ps1
```

New raw downloads, compiled panels, model artifacts, logs, caches, and
process-temporary files must use the resulting `D:\AlientAI\Data`,
`D:\AlientAI\Models`, `D:\AlientAI\Logs`, and `D:\AlientAI\Temp` roots. The
helper fails closed if D is unavailable or has less than 20 GiB free. Never
silently fall back to C for a large output.

Do not move, rewrite, or relabel existing frozen evidence merely to implement
this policy. The canonical repository, protected settings, small append-only
journals, and frozen source paths stay where their contracts currently place
them. A frozen C-based source may be refreshed in place only when its existing
model contract explicitly requires that exact path; do not splice or redirect
it to a new provider/archive. Any future physical migration requires a
separate content-hash audit and path-preserving migration plan.

The first audited path-preserving migration completed on 2026-08-06. The
logical repository path
`C:\Users\jeffp\alientai_start_over_8010\data_v2` is now an NTFS junction to
`D:\AlientAI\Data\RepositoryStorage\alientai_start_over_8010\data_v2`.
Before the swap, all 3,360 files and 11,074,239,590 bytes were copied and every
relative path, length, and SHA-256 hash matched with zero mismatches. The
post-migration tree-manifest SHA-256 is
`9a931ec904e340c5587c774e77c0272bb7e6cc38d933e7badce7d02f3a6fc89b`.
The original physical copy is retained on D at
`D:\AlientAI\Backups\CDriveMigration\data_v2_prejunction_backup_20260806`.
The model monitor was restarted and returned HTTP 200, and the promising-model
inventory regenerated successfully through the unchanged logical path.

## External clean-rank research lead (2026-08-06)

Preserve the source audit in
`EXTERNAL_CLEAN_RANK_MODEL_AUDIT_20260806.md` and the original ZIP hash
`0ef7c67df672d9badd57d0331c3d38211dd722e74e87155617ace9b3d64697d6`.
The bundled S&P-style prediction file internally reproduces +0.04851 mean
daily Rank IC and +1.5449% top-minus-bottom spread, with positive latest-fold
non-overlap diagnostics. It remains `PROMISING_EXTERNAL_LEAD / NOT VALIDATED`.

Never integrate or promote the scripts as-is. Their label enters at the same
close used by the features, costs are absent, the current hand-selected
universe has survivorship/selection bias, exact audit found label-overlap
leakage in folds 2-5, QQQ context is absent, and no sealed test exists. Every
bundled outcome through July 9 is already exposed. A future corrected
implementation must use a new predeclared source/universe/entry/purge/cost
contract and treat all historical work as development evidence; genuine
confirmation must be prospective.

## Pure daily-technical rankers (2026-08-06)

Preserve the source-isolated contract in
`TECHNICAL_ONLY_CROSS_SECTIONAL_SPEC_20260806.md`. These models use only
completed daily technicals and QQQ/SPY technical context. They must never read
options/calls, news/events/fundamentals, intraday, premarket, or after-hours
inputs. QQQ and SPY are reference-only and cannot be selected.

The audited panels are under
`D:\AlientAI\Data\Compiled\technical_only_cross_sectional_20260806`. Nasdaq has
208 exact-101 dates and S&P has 394 exact-483 dates. Nasdaq 5-session and both
S&P horizons are `RESEARCH_HOLD` with unopened tests. Nasdaq 20-session passed
development, opened its test once, and then failed decisively: LightGBM
returned -4.4546% mean and XGBoost -3.9485%, with negative medians, win rates
below 40%, and negative rank IC. Preserve the opened-test artifacts under
`D:\AlientAI\Models\technical_only_nasdaq100_h20_20260806`; never retune or
retest against that period.

## Daily-only technical + call-option rankers (2026-08-06)

Preserve the isolated research contract in
`DAILY_OPTIONS_CROSS_SECTIONAL_SPEC_20260806.md`. These Nasdaq-101 and
S&P-data-ready variants use completed daily OHLCV, QQQ/SPY context, and an
optional recent call-activity feature family. They must never read intraday,
premarket, after-hours, headline, sentiment, or news inputs. QQQ and SPY are
reference-only and cannot be selected.

The independently audited panels are under
`D:\AlientAI\Data\Compiled\daily_options_cross_sectional_20260806`. Both
five-session historical screens are `RESEARCH_HOLD` and their sealed tests
remain `SEALED_UNLOADED`. The twenty-session variants were not fit: Nasdaq has
72 and S&P has 92 common point-in-time call-history dates versus the frozen
120-date minimum. Preserve the reports under
`D:\AlientAI\Models\daily_options_*_20260806`; do not retune against these
development results or open either test after a failed gate.

## Autonomous transparent Nasdaq-101 champion (2026-08-05)

Treat the frozen transparent 20-session model documented in
`AUTONOMOUS_CHAMPION_20SESSION_REPORT_20260805.md` as a primary promising
research program. Its exact report is
`D:\AlientAI\Models\autonomous_transparent_20session_corrected_folds_20260805\training_report.json`
with SHA-256
`67c31d496e02fc0193630a99e3258d0d330dc38170085718d579ca0f0ffa139b`.
Never change its 101-security universe, formula, eligibility rules, 20-session
horizon, 0.25% cost, entry/exit contract, or prior observations.

After each completed market close and before the next regular-session open,
refresh the complete source-pure Alpha Vantage adjusted-daily universe and run
`journal_autonomous_transparent_20session.py`. Append a new observation or
honest abstention even while older horizons are pending; never backfill after
the next open. Use
`data_v2\rcef_research\autonomous_champion_20session_prospective_journal.jsonl`.
Run `evaluate_autonomous_transparent_20session_outcomes.py` after daily data
refreshes. It must leave incomplete horizons pending and append source-hashed
outcomes only after the exact twentieth subsequent adjusted close exists.
Preserve the outcomes and summary under `data_v2\rcef_research`. No prospective
outcome has matured yet; the first August 4 observation contains FTNT, DDOG,
PANW, CSX, and CRWD and was journaled before the August 5 open.

## Jeff competition basket stop clarification (2026-08-05)

Jeff's five frozen competition picks remain MU, AVGO, AMD, MRVL, and NVDA.
Track a separate Jeff-specific equal-weight basket rule with a fixed overall
stop at -3% from the initial competition basket entry value. This is not a
3% stop on each ticker. Preserve the original competition manifest/journal
unchanged and report the clarified basket-stop track separately using
`data_v2\rcef_research\pick_competition_rule_amendments.jsonl`. Do not silently
reinterpret it as a trailing stop unless Jeff explicitly clarifies that.

## Read-only model intelligence monitor (2026-08-05)

`alientai_v2\model_monitor.py` provides the professional owner research page
at `/v2/models` and its read-only JSON feed at `/v2/models/data`. It displays
model descriptions, horizons, universes, dated picks, daily ledgers,
preliminary and final P/L, win rates, and explicit operating states. It reads
only preserved local research journals/outcomes and never makes provider calls,
changes a model, or exposes an execution action.

The normal V2 application includes this router when it is safely restarted.
Until then, `model_monitor_server.py` may be run loopback-only on port 8011 to
serve the monitor without importing or starting the trading engine. Preserve
the separation between forecasts, preliminary marks, and final cost-adjusted
outcomes. Update the model registry whenever a promising, blocked, development,
or preview model materially changes state.

## Canonical Jeff research memory

The canonical append-only file for material Jeff explicitly asks Codex to
remember, save, preserve, or retain is:

`D:\AlientAI\Project_Memory\JEFF_RESEARCH_MEMORY.md`

Whenever Jeff explicitly marks pasted information for memory, append a dated,
descriptive entry there and preserve its substantive content and intended use.
Do not substitute a vague summary. Never store credentials, authentication
codes, private tokens, or other secrets. Treat hypotheses as hypotheses rather
than verified evidence. If drive D is unavailable, notify Jeff and do not
silently create a competing canonical memory file on another drive.

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

### Promising-model data inventory (August 4)

`promising_model_data_requirements.json` is the living registry of every data
family required by each promising frozen model and the two active development
candidates. Run `update_promising_model_data_inventory.py` on every scheduled
model pass. It regenerates both
`data_v2/rcef_research/promising_model_data_inventory.json` and the
human-readable `PROMISING_MODEL_DATA_INVENTORY.md`. A file's existence is not
enough: the audit checks content coverage, usable-row flags, exact latest
session where applicable, provider manifests, and frozen artifacts. Add or
change a registry entry whenever a model or data contract changes.

The August 4 audit exposed and repaired two real preparation failures. The
17-symbol August 3 Alpha daily/technical and option/call panels are now
complete; the corrected call build uses `natural_option_features_2026.jsonl`
and has at least 20 prior observations per symbol rather than zero. The Schwab
late-entry readiness audit passed, but the August 4 entry window had already
closed and must never be backfilled. It may next attempt August 5 after exact
August 4 after-close inputs are prepared.

Schwab daily candle keys are Pacific-local and occur one calendar day before
their associated U.S. session. Use
`refresh_sp500_daily_incremental.py --max-session-date YYYY-MM-DD`; do not pass
a U.S. session date through the advanced `--max-candle-date` option. An
August 4 refresh initially admitted 125 in-progress rows under stored key
August 3; no model consumed them. They were fingerprinted into the ignored
quarantine evidence and removed through
`quarantine_incomplete_schwab_daily_rows.py`. The completed August 3 common
Nasdaq coverage remains intact. After the August 4 close, refresh through
`--max-session-date 2026-08-04` to append final rows.

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
- `evaluate_pick_competition_intraday.py` advances the unmanaged and frozen
  -5% stop-managed 20/60-minute outcomes from either a complete Alpha Vantage
  historical archive or a current-mode, realtime-entitled archive. It requires
  exact entry/exit candles plus every five-minute bar through the horizon,
  waits until the exit candle is complete, and fingerprints the source
  manifest. An opening gap uses the observed bar open; an intrabar threshold
  crossing uses the next observed bar open; a crossing in the final horizon
  bar uses the frozen horizon close. It fails closed on an incomplete path and
  never assumes a theoretical stop fill. For the 2026-08-03 round, the exact
  derived 18-symbol event request is
  `data_v2\rcef_research\pick_competition_events_2026-08-03.jsonl`.
- Claude participates through `build_claude_competition_packet.py`, which emits
  one uploadable ZIP containing instructions plus exact-universe point-in-time
  data. It whitelists underlying feature fields and excludes model scores,
  probabilities, ranks, predictions, labels, other picks, and outcomes. The
  verified August 3 packet contains 101/101 symbols, zero missing rows, and only
  July 31 prior-close technical evidence; Jeff explicitly requested no
  premarket data. Record Claude's returned zero-to-five picks immutably before
  the normal deadline through `record_pick_competition.py`.
- Jeff will submit no additional competition picks. His fixed standing basket
  for the entire competition is `MU`, `AVGO`, `AMD`, `MRVL`, and `NVDA`, as
  preserved in `pick_competition_standing_entries.json` and the August 3
  journal row. Never request a replacement or describe subsequent evaluation
  as daily reselection; report it as one precommitted standing basket.
- Run `summarize_prospective_programs.py` after prospective journals or outcomes
  change. Its generated `prospective_program_status.json` is a read-only
  operational summary of frozen Nasdaq, AI/semiconductor, contextual-options,
  and pick-competition evidence. Missing journals remain explicit; it cannot
  score candidates, alter frozen contracts, or enable execution.
- Use `build_prospective_event_requests.py` to prepare each 17-symbol intraday
  request list. It fails closed unless `as_of_utc` converts to exactly 09:25
  Eastern on the requested decision date. Preparing requests early is allowed;
  the Alpha Vantage download itself must still occur after the live cutoff and
  pass the exact freshness checks.
- No Uvicorn/Python application server is currently listening on port 8010. The preserved settings still have stock paper trading enabled and option paper buying disabled. Do not restart casually: first perform the read-only restart review in the master plan, preserve positions and limits, verify stale payloads remain `AVOID`, start through the loopback-only launcher, and retain an immediate rollback path. Do not change `data_v2/v2_settings.json`.
- For new research observations, Alpha Vantage is the preferred market-data
  source. If it cannot provide a complete, timely panel, Schwab may be used as
  an explicitly source-tagged fallback only when the entire observation uses
  Schwab under a predeclared timing contract. Never splice Schwab data into an
  Alpha-Vantage-frozen observation (or the reverse), and never use a fallback
  to backfill a decision after its outcome is observable.
- Schwab was reauthorized on July 30 for the local daily research path. The frozen July-21 contextual-options pilot now has all five later sessions through July 28 and is complete: 5 signals, 1 date, 80.00% post-cost wins, +1.894382% mean net return, +3.080338% median, and -13.815280% worst trade. This is not enough evidence to promote: the fixed prospective gate remains `RESEARCH_HOLD` for minimum sample/date diversity and fifth-percentile tail. Do not tune from these five outcomes or change paper settings.
- A July-30 fixed historical holdout check used an early-2026 calibration boundary and a later-2026 holdout for the already specified unusual-call plus top-5% technical-context rule. The later holdout contained 94 signals across 41 exit dates and showed +1.482190% post-cost mean, +0.847123% median, and 54.2553% wins, but its legacy full-notional cohort drawdown was -25.957771%. It remains research-only and must not select a new threshold; the result is support for continuing the prospective journal, not a promotion.
- August 2 priority is prospective evidence, not new variants. Limit active predictive work to the frozen Nasdaq five-session journals, the six frozen AI/semiconductor 20/60-minute models, and the frozen contextual technical-plus-unusual-call study. The Alpha Vantage 09:25 ET entitlement/timeliness check remains a hard blocker for the intraday program; fail closed on delayed data. The full repository discovery suite passed 611 tests.
- On August 3 the contextual unusual-call study was found to be named in the
  automation without a working daily input routine. This is now a fail-loud
  operating requirement: every promising frozen program must either append a
  valid scheduled observation or report its exact blocker immediately.
  `build_contextual_options_prospective_payload.py` provides the missing
  source-timestamped, complete-universe scoring/payload boundary while
  retaining the immutable model, top-quarter rule, maximum-five policy,
  five-session horizon, and research-only `AVOID` decision.
- The August 3 after-close Alpha Vantage full-universe probe returned 496 HTTP
  successes but every response contained an empty explicit "No data" chain.
  These files and the resulting zero-signal artifacts were quarantined and do
  not count as a prospective observation. The downloader now classifies an
  empty `data` list as unavailable. Retry the exact August 3 request once at
  the August 4 05:31 Pacific pre-open pass. It may count only if nonempty
  chains are available and the payload is frozen before the next session
  begins. If it remains unavailable, report the blocker and continue building
  a separately source-pure Schwab call-volume history; never compare a current
  Schwab volume with an Alpha Vantage historical baseline.
- The August 4 after-close collection completed with 479 nonempty chains, four
  explicit provider-unavailable symbols (BF.B, BRK.B, EA, NVR), and zero
  failures. Before the August 5 open, the append-only Schwab refresher added the
  matching completed session to all 483 existing histories with zero failures.
  `build_contextual_options_prospective_payload.py` then formed a complete
  479-symbol common universe, with 479 technical rows, 479 nonempty option rows,
  and 479 rows having 20 prior call observations. It locked NRG, INTC, GPN, CAT,
  and IT in
  `data_v2\rcef_research\contextual_options_shadow_payload_2026-08-04.json`.
  This is the second prospective decision date. Leave it pending for five later
  Schwab sessions and continue later eligible observations without retuning.
- The local Schwab daily refresher also previously omitted `endDate`, allowing
  Schwab to return a cached prior-session series. It now anchors each request
  to the current instant. On August 3 it appended the completed session across
  the full available local universe with zero failures. This correction also
  matured the first four Nasdaq-101 five-session outcomes; use the generated
  outcome summary without changing their frozen models.
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

## Default market-data source and approved fallback (updated August 7, 2026)

Jeff directed that all new collection, feature-building, and research work use
Alpha Vantage by default. Existing Schwab-based frozen prospective studies and
historical artifacts remain source-isolated; never substitute Alpha Vantage
candles inside them. Jeff later explicitly approved source-pure alternate
models as described below; a new Schwab download is allowed only for an
approved, predeclared Schwab model route and never as an improvised row patch.

Jeff explicitly changed the fallback direction on August 7: Alpha Vantage and
Schwab are both approved when the intended provider has missing, duplicate, or
conflicting rows. The controlling machine-readable policy is
`approved_source_fallback_registry.json`, validated by
`validate_approved_source_fallback_registry.py`. Fallback is model routing,
not row replacement: one observation must use one complete predeclared source
contract, a distinct model ID and a distinct journal. Never splice providers
inside an observation, relabel an existing frozen model, pool source-specific
evidence, or switch after any outcome is visible.

At the start of every model pass, run
`validate_approved_source_fallback_registry.py --output
data_v2\rcef_research\approved_source_fallback_registry_audit.json` before
`update_promising_model_data_inventory.py`. Fail closed if the registry audit
does not pass.

The 120-stock twenty-session LambdaRank route is already `READY`: the
conflicted Schwab candidate and the separately trained/audited Alpha Vantage
clone remain independent programs, and the Alpha clone may attempt its own
future observation when Schwab is unusable. Nasdaq-101 baseline,
Nasdaq-101 QQQ-relative, and Nasdaq-80 remain
`ALTERNATE_CLONE_REQUIRED`; their existing Alpha scorer is only a diagnostic
and must not be promoted as a fallback observation. Build independently
validated Alpha clones with new IDs and journals before routing those models.

Jeff also directed that an unfrozen historical test whose only unavailable
data is its final day may end on the latest prior fully complete session.
Record every excluded date and apply this only before the model/test boundary
is frozen or opened. Never shorten an already frozen test, an existing
prospective horizon, or a pending outcome. Those must remain pending, record a
source-blocked abstention, or proceed through a separately source-pure
alternate model.

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

`evaluate_nasdaq_prospective_outcomes.py` is the append-only outcome path for
the frozen Nasdaq journals. It reads the same
`data_v2\sp500_daily_schwab_max_history` source, verifies each recorded entry
close has not changed, translates the legacy stored date to the actual session,
requires the fifth later stored candle, subtracts the frozen 0.25% cost, and
fingerprints each source file. Before the 2026-08-03 close, all four July-27
Nasdaq-101 observations correctly remain `pending_candle_coverage`; refresh the
frozen Schwab source after the close before evaluating them.

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

On 2026-08-03 Jeff explicitly activated this design. Partial V1 is complete:
`build_ai_semiconductor_multi_horizon_panel.py` produced 1,694 point-in-time
rows with separate 1/5/20-session labels, and
`train_ai_semiconductor_multi_horizon_catalyst.py` ran fifteen nested,
chronological, validation-locked ablations. Full results are in
`AI_SEMICONDUCTOR_MULTI_HORIZON_CATALYST_REPORT_20260803.md`. Preserve the
one- and five-session technical+premarket candidates without retuning. Do not
claim that unusual calls, the analyst proxy, or short interest helped in this
run, and reject the negative 20-session build. Missing historical
fundamentals/guidance, catalyst-calendar, structured analyst, general-news, and
industry-demand families remain separate future data work. No engine,
settings, paper, or live-trading change is authorized.

Jeff then clarified the exact narrative logic he intended. Use
`AI_SEMICONDUCTOR_NARRATIVE_FEATURE_CONTRACT.md` and
`alientai_v2/research/ai_semiconductor_narrative_features.py` for that
extension. The thesis is accelerating fundamentals/guidance plus a pullback
inside an intact trend plus role-specific AI demand plus a horizon-aligned
known catalyst. The source narrative's named picks, prices, media lists, and
opaque scores are expressly excluded. Do not train the full extension until
the required timestamped fundamentals, estimates, catalyst calendar, analyst,
and vintage industry-demand records exist with adequate chronological
coverage.

The 2026-08-03 source audit then found two complete eligible families already
on disk. `build_ai_semiconductor_earnings_context.py` attaches only events
whose `available_at_utc` is at or before the decision cutoff;
`build_ai_semiconductor_news_context.py` attaches deduplicated target-specific
1/5/14-day news aggregates published by the cutoff. Both cover all 1,694 rows.
The exploratory one-day technical+premarket+earnings result improved to
+0.747626% mean and 62.16% wins across 37 selections; earnings hurt five days,
broader news did not beat the simpler candidates, and all 20-day variants
remained negative. The test was already observed, so do not retune. Current
snapshot estimates/statements/calendar remain ineligible for historical
backfill. See `AI_SEMICONDUCTOR_NARRATIVE_DATA_AUDIT_20260803.md`.

The one-day technical+premarket+earnings artifact is now immutable under
`data_v2/rcef_research/ai_semiconductor_narrative_1d_prospective/frozen_manifest.json`.
Use `journal_ai_semiconductor_narrative_model.py` only for genuinely future,
complete 17-symbol panels before the next-session open; append to that
directory's `journal.jsonl`. Use
`evaluate_ai_semiconductor_narrative_outcomes.py` only after the exact
same-session close matures, writing append-only outcomes and summary there.
Never backfill August 3, change the top-10%/maximum-two policy, or substitute a
different source. The program is included in the existing weekday automation
and remains research-only.

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
- Before the 06:26 pass, run `audit_intraday_prospective_readiness.py` with the
  exact prior-session technical panel, prior-session call-feature panel,
  decision-date event requests, frozen 17-symbol file, and model root. The
  audit fails closed unless all three panels contain the exact frozen universe,
  the event cutoff is exactly 09:25 ET, every model report is research-only
  with execution disabled, and all six model/report fingerprints can be
  recorded. Store the dated JSON audit beside the other ignored research
  evidence. This audit does not replace the journal's own timing checks.
- Current-session 09:25 and 10:25 snapshots must use
  `download_alpha_vantage_matched_premarket.py --entitlement realtime
  --current-date YYYY-MM-DD`. The historical/default mode deliberately supplies
  no entitlement and, when a month is specified, can lag by a completed
  session; it is therefore forbidden for a same-session prospective decision.
  Realtime mode omits `month`, freezes its date and entitlement in the
  resumable manifest, refuses to run before the event cutoff, and must use a
  separate dated output directory for the later outcome snapshot. Fail closed
  if the account lacks realtime entitlement or exact bars are unavailable.
- The point-in-time audit in
  `AI_SEMICONDUCTOR_INTRADAY_TIMING_AUDIT_20260803.md` established that Alpha
  Vantage five-minute timestamps are interval starts. Consequently, the 09:25
  candle is partial at the scheduled 09:26 scoring pass and becomes complete
  only at the frozen 09:30 entry. `journal_ai_semiconductor_intraday_models.py`
  now fails closed for both cases. Do not remove this guard, journal a partial
  bar, use the already-known 09:30 open, or silently switch to 09:20/09:35.
  Repair requires a separately named and retrained timing contract.
- The 2026-08-03 08:26 Pacific outcome checkpoint verified that no valid
  pre-entry journal or outcome ledger existed. It therefore recorded
  `SKIPPED_NO_VALID_PRE_ENTRY_JOURNAL`, attempted no outcome download, and
  wrote no outcome. The failed provider-manifest hash remained unchanged.
- Prospective selections:
  `data_v2\rcef_research\ai_semiconductor_intraday_prospective_journal.jsonl`.
- Frozen six-model identity:
  `data_v2\rcef_research\ai_semiconductor_intraday_frozen_manifest.json`.
  `journal_ai_semiconductor_intraday_models.py` writes or verifies this
  manifest before reading session inputs, so a missing or timing-invalid
  premarket panel cannot leave the model contract undefined. Its six
  model/report hashes were independently matched to the August 3 readiness
  preflight.
- Prospective outcomes:
  `data_v2\rcef_research\ai_semiconductor_intraday_prospective_outcomes.jsonl`.
- `evaluate_intraday_prospective_outcomes.py` independently verifies the
  outcome archive manifest before reading prices. It requires `status:
  complete`, current mode, realtime entitlement, the exact decision date,
  interval-start five-minute bars, and an archive completion time after the
  longest requested exit candle matured. Every outcome fingerprints that
  manifest. It rejects historical, failed, mixed-date, empty, and unsupported
  batches rather than allowing the automation to substitute a convenient
  source.
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

Jeff explicitly authorized that new source-separated experiment on 2026-08-03.
`AI_SEMICONDUCTOR_LATE_ENTRY_SCHWAB_REPORT_20260803.md` is its controlling
record. It uses a completed Schwab 09:25 interval-start candle, scores only
from 09:30 through 09:34:59 ET, enters at the 09:35 bar open, and exits at the
10:30 bar close observable at 10:35. Only the frozen 60-minute premarket and
calls variants advance to future-only research. Never backfill August 3,
replace an existing Alpha Vantage-frozen result, or create an order.

`LARGE_CAP_AI_INFRASTRUCTURE_5_QQQ_CLONE_REPORT_20260803.md` controls the
separate NVDA/AVGO/AMD/MU/AMAT QQQ-relative five-session clone. It uses the
unchanged source panel, features, labels, chronology, embargo, and 0.25% cost.
The model stopped at one iteration; the tie-expansion guard locked the 20%
validation policy. Its strong observed test must be compared prospectively
against the frozen equal-weight five-stock control because that simple control
was stronger during validation. Never retune from the observed test or enable
execution.

## Rolling 20-minute adjusted archive (started 2026-08-03)

Jeff approved collecting the Alpha Vantage candles needed for a separate model
that predicts any eligible ticker's return over the next four five-minute bars,
instead of only predicting a fixed interval after the market open.

The immutable archive contract is:

- collector: `download_alpha_vantage_adjusted_intraday_archive.py`
- universe: the 101 exact rows in `nasdaq100_2026-06_symbols.txt`, plus QQQ and
  SPY (103 unique symbols)
- source/function: Alpha Vantage `TIME_SERIES_INTRADAY`
- interval: five minutes
- months: 2020-01 through the completed month 2026-07
- `adjusted=true`, `extended_hours=true`
- timestamp convention: interval start, `America/New_York`
- destination:
  `D:\AlientAI\Data\AlphaVantage_2026\rolling_20m_nasdaq101_adjusted_202001_202607`
- request count: 8,137 symbol-months
- research only, with no engine, broker, paper-order, or live-order path

The separate July-2026 five-request pilot completed AAPL, ABNB, ADBE, ADI, and
ADP with zero unavailable or failed requests. Its rows passed month, timestamp
grid, duplicate, OHLC envelope, positive-price, and nonnegative-volume checks.
The full collector is resumable and atomically records content hashes and
explicit unavailable/failure evidence in `manifest.json`.

At 2,537 accounted requests, Alpha Vantage returned one HTTP 503 for MU
2022-01. The collector failed closed as designed. Logs were credential-safe,
no duplicate process existed, disk was healthy, and the identical command
resumed from the manifest; the retry succeeded and the manifest failure
cleared. The collector now retries only `AlphaVantageRequestError` failures up
to four total attempts with bounded exponential delays. Never extend that
retry to CSV validation, provider information messages, or contract
mismatches.

While it runs, never launch a duplicate adjusted-intraday collector. A stopped
process is not enough reason to restart: first inspect the manifest and
redacted logs, preserve completed keys, verify disk space and retryability, and
resume the identical command only. After completion, independently audit
regular-session continuity, split adjustment consistency, per-symbol/month
coverage, missing bars, and the exact four-bar target alignment before building
or training a model. Keep current-month/live inference data in a separate
source contract. Do not treat the archive itself as model evidence or authorize
paper/live trading from it.

Run `audit_alpha_vantage_adjusted_intraday_archive.py` immediately after a
genuine complete manifest. It independently requires the immutable contract,
zero failures, exact 8,137-key completed/unavailable coverage with no overlap,
unique records, valid gzip CSV contents, exact stored hashes/row counts/time
bounds/sizes, and zero orphan gzip files. Save its JSON report outside the raw
archive. Do not begin the supplement or model panel if this audit fails.

After that 8,137-request archive completes and passes its audit, run the same
collector contract for the nine symbols in
`ai_data_center_supplemental_symbols.txt` (ON, SMCI, TSM, ORCL, ANET, DELL,
VRT, IBM, and CBRS). CBRS is newly public as of 2026-05-14, so its pre-listing
months must remain explicitly unavailable rather than being imputed. Do not run
this supplement concurrently with the active collector. The combined 110-stock
research universe is frozen in
`nasdaq101_ai_data_center_expanded_symbols.txt`. Preserve
`nasdaq100_2026-06_symbols.txt` unchanged because its hash identifies the
active archive and prior Nasdaq research. The supplemental archive must have
its own output directory and manifest; combine only after exact contract and
coverage validation.

## One-minute any-time 20-minute successor (started 2026-08-04)

Jeff explicitly refined the desired model to one-minute resolution: it must
answer throughout the regular session rather than only at the open or on a
five-minute grid. Preserve the completed five-minute archive and all frozen
opening models unchanged.

The new archive contract is:

- collector: `download_alpha_vantage_adjusted_intraday_archive.py`
- universe: the exact 101 rows in `nasdaq100_2026-06_symbols.txt`, plus QQQ and
  SPY (103 unique symbols)
- source/function: Alpha Vantage `TIME_SERIES_INTRADAY`
- interval: one minute
- months: completed months 2020-01 through 2026-07
- `adjusted=true`, `extended_hours=true`
- timestamp convention: interval start, `America/New_York`
- dataset: `rolling_20m_nasdaq101_adjusted_1min`
- destination:
  `D:\AlientAI\Data\AlphaVantage_2026\rolling_20m_nasdaq101_adjusted_1min_202001_202607`
- research only; no engine, paper-order, or live-order path

The separate July AAPL pilot passed: 21,095 rows, 22 regular sessions, exactly
390 regular-session rows on every session, zero failures. The production
archive must remain resumable, singular, credential-safe, and separately
audited before panel construction.

The prediction contract uses only fully completed one-minute bars. Schema v3
keys each historical observation by the effective close of the newest completed
minute, uses the next interval's recorded open as the research entry, and uses
the close of the horizon-th subsequent regular-session bar as the exit. Store
both the target bar start and its one-minute-later effective close timestamp;
never label an interval-start as though it were the close. The 0.25% frozen cost
covers an execution allowance, but exact next-bar-open fills remain a research
approximation. Exclude missing entry/target minutes and overnight crossings. A
mid-minute user query must report its effective completed-minute `as_of`
timestamp and minute-resolution target; never pretend one-minute candles
support exact sub-minute timing. Use whole market dates for five separate
chronological stages (train, fit-validation, calibration, policy-validation,
and sealed test) with five-session embargoes at every boundary.

Alpha Vantage is the historical training source. A live Schwab one-minute feed
may be considered only after a separately recorded overlapping
source-compatibility audit shows that normalized features and timestamp
semantics match closely enough. Never silently splice sources or use a partial
current minute. The first implementation remains research-only and must expose
predicted return, direction probability, uncertainty/abstention, effective
`as_of`, and target timestamps.

Jeff's multi-horizon refinement uses the same original model architecture and
the same point-in-time feature definition for every fit. Train separate,
independently stored copies whose only intentional experimental difference is
the target horizon: 5, 10, 30, 60, and 90 subsequent regular-session minutes.
These are not five unrelated model designs and training one horizon must never
overwrite another horizon's artifact. Each observation must use only fully
completed one-minute candles, report its effective completed-minute `as_of`
timestamp, and exclude targets that would cross the regular-session close.

After every horizon model has independently passed the same validation and
sealed-test discipline, a separate research-only consensus engine may combine
their out-of-fold predictions. It must expose every component prediction and
must distinguish sustained agreement, short-lived momentum, pullback/recovery,
conflict, and abstention. Any learned combiner must train only on out-of-fold
base-model predictions so it cannot learn from in-sample scores or sealed-test
outcomes. Preserve the standalone horizon results alongside the combined
result; the consensus engine may not conceal disagreement or authorize paper
or live execution.

Jeff also requested a separately trained AI/semiconductor-only clone. Its exact
universe is the 17 symbols in
`research_universes\ai_semiconductor_screen_2026.txt`; fourteen are in the main
one-minute archive and ANET, ORCL, and SMCI come from the separately tagged
one-minute AI/data-center supplement. Audit the supplement independently, then
train the same 5/10/30/60/90-minute architecture, features, costs, chronology,
embargoes, and validation/sealed-test rules with universe as the intentional
experimental difference. Preserve and hash the exact 17-symbol list, keep the
Nasdaq model unchanged, and do not silently add the other supplemental symbols.

On 2026-08-04, a separate partial pipeline pilot was explicitly allowed while
the production collector continued. Schema v2 stores observation and target
timestamps as nanoseconds since Unix epoch; both compiler and trainer fail
closed on another unit. The first pilot exposed a pandas
microsecond/nanosecond compatibility error before the test partition was
opened. After correction, 872 symbol-month shards produced 5,249,807 rows and
211 market dates. The chronological LightGBM run used 126 train dates, 37
validation dates, two five-session embargoes, and kept 38 test dates sealed
because no validation policy passed. Best validation: 683 signals, -0.2220%
mean net, -0.2433% median, 37.34% wins, and -27.16% capital-scaled drawdown.
The controlling report is
`data_v2\rcef_research\rolling_20m_1min_partial_model_v2_20260804\training_report.json`
with status `PARTIAL_PIPELINE_PILOT_ONLY`. Never promote or trade it. Continue
the singular production collector, then compile/train again only after a
complete manifest and content audit.

On 2026-08-04 the main 8,137-request archive and the separate 869-request
AI/data-center supplement both reached complete with zero failures. The
main archive independently passed its content audit: 7,670 valid gzip files,
467 explicitly unavailable symbol-months, 82,425,431 rows, and zero orphans.
The controlling report is
`data_v2\rcef_research\rolling_20m_1min_full_archive_audit_20260804.json`. The
supplement independently passed its content audit: 793 valid gzip files,
76 explicitly unavailable symbol-months, 10,412,846 rows, and zero orphans.
Its controlling report is
`data_v2\rcef_research\rolling_20m_ai_data_center_supplement_1min_content_audit_20260804.json`.
Both schema-v3 compilation prerequisites are therefore satisfied.

Schema v3 corrects deficiencies found in the first implementation without
rewriting either schema-v2 artifact. `compile_rolling_twenty_minute_panel.py`
now supports independently stored 5/10/20/30/60/90-minute labels, exact
next-interval entry and effective-exit timestamps, strict gap semantics,
immutable target-universe hashes, and same-contract main+supplement inputs.
`build_model_features_at` uses the compiler's exact feature implementation.
Before loading data, the trainer verifies every compiled shard hash, rejects
duplicates/unexpected symbols/path escapes/orphans, and reconciles the manifest
row count. The trainer may abstain, separates early stopping, calibration, and policy
selection into later chronological stages, and does not load or score the test
partition unless a threshold first passes the frozen policy-validation gate.
It reports calibration, uncertainty, concentration, time/regime slices,
capacity-matched controls, non-retuned 0.05%/0.10%/0.25% cost sensitivity,
market-date-clustered confidence intervals, and capital-scaled drawdown. A
policy cannot pass unless it spans at least 20 market dates and the lower 95%
clustered bound remains above zero at the frozen 0.25% cost.
Each horizon and universe must use a new empty output root. The contemporary
fixed Nasdaq and AI/semiconductor universes still carry historical
survivorship/selection bias, so retrospective passage alone never authorizes
promotion.

The first schema-v3 production result is the AI/semi-17 five-minute clone at
`D:\AlientAI\Models\rolling_anytime_ai17_schema3_h05_20260804`. Its panel
contained 1,335 shards and 9,563,195 rows. All five policy-validation thresholds
failed: the least-negative mean was -0.2049% net after 0.25% cost (gross
+0.0451%), with -0.25% median, 32.93% wins, and -38.61% capital-scaled
drawdown. Status is `RESEARCH_HOLD`; the 243-date test is explicitly
`SEALED_UNLOADED`. Never retune or open that test. The separate AI17 ten-minute
schema-v3 panel is the next active artifact; continue the frozen horizon
sequence one at a time.

The Nasdaq-101 20-minute schema-v3 panel then completed at
`D:\AlientAI\Data\Compiled\rolling_anytime_nasdaq101_schema3_h20_20260804`
with 7,512 verified shards, 43,554,397 rows, zero failures, the exact frozen
101-symbol hash, nanosecond timestamps, and next-minute-open entry. Its one
permitted training run is preserved at
`D:\AlientAI\Models\rolling_anytime_nasdaq101_schema3_h20_20260804`.
All five policy-validation percentiles failed after 0.25% cost. The
least-negative fixed slice was the 99.5th percentile: 180 signals across 23
dates, +0.105089% mean gross but -0.144911% mean net, -0.240700% median net,
42.78% wins, and -7.431377% capital-scaled drawdown. Status is
`RESEARCH_HOLD`; no threshold was selected and the 243-date test remains
`SEALED_UNLOADED`. Never retune or open that test. Continue with the separate
Nasdaq-101 30-minute schema-v3 panel, one logical job at a time.

## Multi-resolution Nasdaq/S&P cross-sectional ranker (2026-08-06)

Jeff specified two new research-only cross-sectional rankers: exact
Nasdaq-101 candidates and the 483-symbol S&P data-ready list, with QQQ/SPY as
context only. Both use the eleven requested daily technical features,
completed regular/after-hours five-minute summaries, recent call-side activity,
strictly lagged unusual-call baselines, and optional timestamped news. Separate
LightGBM and XGBoost challengers target five- and twenty-session within-date
return ranks. Decision is 20:00 Eastern, entry is the next complete open, exit
is the fifth or twentieth subsequent close, and cost is 0.25%.

The exact implementation is
`alientai_v2/research/multiresolution_cross_sectional.py`,
`build_multiresolution_cross_sectional_panel.py`,
`audit_multiresolution_cross_sectional_panel.py`, and
`train_multiresolution_cross_sectional.py`. Both panels passed independent
content audits. Nasdaq contains 7,272 rows across 72 dates with exact 101-name
coverage. S&P contains 43,869 rows across 92 dates; 481 of 483 reference
symbols appear and every date has at least 467 candidates.

Both five-session screens are `RESEARCH_HOLD` and their sealed tests remain
`SEALED_UNLOADED`. The most relevant Nasdaq daily+five-minute+calls LightGBM
slice had 336 selections across 56 development dates, +1.4217% mean net,
+0.1886% median, 52.08% wins, but -0.04984 mean rank IC and a -0.3216%
date-clustered lower 95% bound. The comparable S&P result had 1,095 selections
across 73 dates, +0.0834% mean, -0.3658% median, 46.30% wins, -0.04994 rank IC,
and -0.5668% lower bound. No variant passed.

News remains blocked: only 36 Nasdaq dates meet 75% coverage and 30 S&P dates
meet 90%, versus 60 required. Both twenty-session variants are
`BLOCKED_INSUFFICIENT_HISTORY`: 72 and 92 common dates respectively, versus
the frozen 120-date minimum needed for defensible purge/embargo/test geometry.
Do not weaken the gate, open the sealed five-session tests, start prospective
journals, or connect execution. Continue collecting the exact same families
and retry only in a new root after the stated date thresholds are met. The
controlling report is
`MULTIRESOLUTION_CROSS_SECTIONAL_REPORT_20260806.md`.

## Cross-sectional technical five-session model (2026-08-05)

Jeff explicitly directed a separate implementation of the supplied
short-momentum, oscillator, volatility-regime, volume-confirmation, and
date-local cross-sectional ranking thesis. The exact candidate universe is the
union of `nasdaq100_2026-06_symbols.txt` and
`research_universes\ai_semiconductor_screen_2026.txt`: 104 unique candidates.
QQQ and SPY are context only.

The new research-only implementation is:

- `alientai_v2\research\cross_sectional_technical_5d.py`
- `build_cross_sectional_technical_5d_panel.py`
- `audit_cross_sectional_technical_5d_panel.py`
- `train_cross_sectional_technical_5d.py`
- `test_cross_sectional_technical_5d.py`

It uses completed adjusted-daily OHLCV through the decision close, enters at
the next regular-session adjusted open, exits at the fifth subsequent regular
close, deducts 0.25%, and stores the exact five-session mark-to-market path.
Features include 1/5/10-session momentum, RSI, stochastic K/D, CCI, ATR,
Bollinger position/width, 10/20-session realized volatility, relative and
directional volume, EMA distance, MACD histogram, ADX, five-session range
position, gap, liquidity, and date-local percentile ranks. The supplied
transparent formula is preserved, but its ROC(10) and 10-session-return
redundancy is disclosed rather than represented as two independent signals.
A separate LightGBM learner predicts the within-date future-return rank.

The trainer never reads sealed-test JSON rows unless policy validation passes.
It uses whole-date train, fit-validation, calibration, policy-validation, and
sealed-test stages with two-sided five-session embargoes. The policy gate
requires at least 100 trades across 20 dates, positive mean and median,
at least 50% wins, mean rank IC of at least 0.01, a positive top-minus-bottom
spread, and fixed-slot capital-scaled drawdown above -20%. It also reports five
non-overlap rotations and capital-scaled Sharpe. Ten model/panel tests plus the
adjusted-downloader test, compilation, and diff checks pass.

Do not launch its panel builder or trainer while a schema-v3 compiler/trainer
is active. Once the singular current job releases resources, build into a new
D-drive panel root using
`nasdaq101_qqq_spy_daily_adjusted_full_20260805` as the primary full adjusted
archive and
`nasdaq_ai_cross_sectional_additions_adjusted_full_20260805` for the three
same-provider additions ANET, ORCL, and SMCI. The dedicated supplement
completed all three `TIME_SERIES_DAILY_ADJUSTED` full requests with zero
failures; all three files contain adjusted-close fields and end on August 5.
The earlier compact AI archive is explicitly unsuitable because ANET and SMCI
have split histories. Verify both manifests and all hashes. Historical results
retain fixed-current-universe survivorship and selection bias and cannot
authorize execution.

The completed panel at
`D:\AlientAI\Data\Compiled\nasdaq_ai_cross_sectional_technical_5d_v1_20260805`
contains 162,609 unique rows across 1,650 decision dates, with 133,062 eligible
rows and 92-104 candidates per date. Its full content audit passed with zero
errors and fingerprints panel SHA-256
`27b0a6a30d04a3a728f2013a54ed0c2b9b99c7f98a9437e8d71911825656f133`.

Calibration chose the LightGBM top-20%/maximum-15 policy. It stopped at
iteration 4. Independent policy validation then failed: 1,719 selections
across 119 dates, -0.025200% mean net, -0.188650% median, 48.17% wins,
-0.058954 mean rank IC, -1.134547% top-minus-bottom mean, and -12.869151%
capital-scaled drawdown. The bottom-ranked control was positive; do not invert
the model after observing this result. Status is `RESEARCH_HOLD`, and the
160-date December 2025-July 2026 test remains `UNOPENED`. Never retune, open
that test, create a prospective journal, or enable execution. Controlling
evidence: `NASDAQ_AI_CROSS_SECTIONAL_TECHNICAL_5D_REPORT_20260805.md`.

## Exact Nasdaq + AI semiconductor five-day roadmap (2026-08-05)

Jeff separately supplied the broader roadmap preserved in
`nasdaq_ai_roadmap_5d_contract.json` and directed that it be set up as written.
Do not merge it with or inherit evidence from
`nasdaq_ai_cross_sectional_technical_5d_v1`. The exact current reference
universe is the 101-security Nasdaq file union the 22 explicitly named symbols
in `research_universes\nasdaq_ai_roadmap_overlay_20260805.txt`, producing 103
current candidates; TSM and ON are the only overlay additions. The phrase
"a few others" is not reproducible and must not be used to invent symbols.

The model requires quarterly point-in-time Nasdaq membership, full adjusted
daily history, QQQ/SMH/SOXX/NVDA relative context, VIX level/change, lagged
revenue/EPS/gross-margin/earnings-streak facts, and a historically known
earnings calendar. Optional short-interest, prior-session implied-move, and
timestamped FinBERT news families may be added only with explicit missingness
and timing audits. Entry is the next complete adjusted open, exit is the fifth
subsequent adjusted close, cost is 0.25%, and validation uses whole dates,
overlap purging, five-session embargoes, calibration-only policy choice, and a
minimum twelve-month sealed holdout. Start with transparent and tree models;
add a sequence model or ensemble only if out-of-fold sequence predictions add
independent validation value.

Run `audit_nasdaq_ai_roadmap_5d_readiness.py` before any panel or training
work. Its first verified result is `BLOCKED`: dated Nasdaq membership is
absent; TSM, ON, SMH, SOXX, and VIX are missing from the full adjusted model
archive; and the point-in-time fundamental and earnings-calendar tables are
absent. These are exact data blockers, not permission to weaken the contract.
Preserve the active singular schema-v3 job and do not train this model until
the audit returns `READY_TO_BUILD_PANEL`. No engine, settings, paper, live, or
frozen prospective state changed.

## Production-style purged-CV cross-sectional picker (2026-08-05)

Jeff supplied and explicitly authorized a complete cross-sectional
Nasdaq-100 plus AI/semiconductor five-session pipeline with mandatory purged
K-fold validation. The isolated implementation is:

- `alientai_v2\research\cross_sectional_picker_5d.py`
- `train_cross_sectional_picker_5d.py`
- `score_cross_sectional_picker_5d.py`
- `run_cross_sectional_picker_5d.py`
- `cross_sectional_picker_5d_config.json`
- `CROSS_SECTIONAL_PICKER_5D.md`
- `test_cross_sectional_picker_5d.py`

It reuses only the already audited 162,609-row adjusted-daily panel and pure
technical calculations; it inherits no model, threshold, or evidence from the
earlier failed fixed-104 experiment. Every predictive input is a same-date
cross-sectional percentile rank. The default model uses five whole-date
purged folds, exact label-interval overlap removal, five-session post-fold
embargoes, a separate five-session pre-test embargo, and 252 sealed dates.
Daily scoring rebuilds the same ranks without labels and emits JSON/CSV with
`execution_decision: AVOID`.

The completed out-of-fold evaluation selected 11,248 rows across 1,393 dates:
+0.244242% mean net, +0.157053% median, 51.5025% wins, essentially zero mean
rank IC (+0.000010), -0.090561% top-minus-bottom mean, +80.8420% long-history
overlapping return, and -44.9781% drawdown. The bottom-ranked control was
better. Status is `RESEARCH_HOLD`; the 252-date test remains `UNOPENED`.
Twenty-one targeted tests and compilation passed. Preserve the implementation
as reusable infrastructure, but never invert or retune the observed folds,
open the test, start a prospective journal, or connect it to execution.
Controlling evidence: `CROSS_SECTIONAL_PICKER_5D_REPORT_20260805.md`.

## Five-session catalyst-momentum model (2026-08-04)

`train_ai_semiconductor_catalyst_momentum_5d.py` and
`alientai_v2\research\catalyst_momentum_5d.py` preserve Jeff's catalyst-first,
technical-setup, call-positioning, fundamental-overlay, and risk-control logic
as a research-only contract. Seven focused tests cover the primary gate,
parabolic rejection, negative-overlay rejection, lagged relative-strength
ranks, capacity, validation-only fraction choice, and the fixed one-day time
stop.

The four-stage test is `RESEARCH_HOLD`. On the untouched period, technical,
catalyst+technical, and positioning variants had negative means. The full
variant had +0.227821% mean across 20 trades, but -3.578902% median, 25% wins,
and -14.897556% worst trade. Its few winners do not establish an edge. The
one-day nonpositive time stop worsened every model. Do not adopt it, retune
against this now-observed test, create a prospective journal, or connect it to
execution. The controlling evidence is
`AI_SEMICONDUCTOR_CATALYST_MOMENTUM_5D_REPORT_20260804.md`.

The next legitimate attempt must use a pre-registered new chronology after the
long adjusted technical archive is complete and should add independently
timestamped upcoming earnings, structured analyst actions/targets, and
guidance/design-win/capacity events. Hard stops require intraday path data; do
not infer them from five-session endpoint returns.

Jeff's controlling qualitative framework is preserved in
`AI_SEMICONDUCTOR_FIVE_DAY_THESIS.md`. Future agents must retain the distinction
between durable industry context (visible demand, scarcity/pricing power,
valuation, and AI-stack diversification) and five-session drivers (catalyst,
technical confirmation, sentiment/positioning, and risk). Merchant leaders,
memory/packaging/foundry, custom-ASIC enablers, and emerging inference
specialists require separate peer roles and risk treatment. Do not hand-score
favored names, treat the thesis as a label, backfill current capacity or
valuation into history, or retune the already observed 2026 test.

## Defined-risk options-volatility framework (2026-08-04)

`alientai_v2\research\defined_risk_option_strategy.py` is the deterministic
strategy layer for a future learned options model. It permits only defined-risk
debit/credit verticals, long straddles, iron condors, iron butterflies,
calendars, or abstention. It rejects low liquidity, blocks short-volatility
structures through binary events, halves risk for emerging inference
specialists, and never executes.

The natural Alpha Vantage archive covers all 17 established AI/semiconductor
symbols with 108-122 dated chains each. Of 1,694 underlying panel rows, 1,262
have exact next-session entry and fifth-session exit chains, and every complete
pair has matching contract IDs at exit (minimum 42, median 2,424, maximum
11,510). Preserve the other rows as missing.
`alientai_v2\research\exact_multileg_option_compiler.py` now requires a prior
observable selection snapshot, a later distinct entry snapshot, and a later
exit snapshot; it rejects same-snapshot selection/fill, missing contract IDs,
and malformed quotes, crosses every spread, and charges fees. Next compile the
full candidate set, then train separate direction and absolute-move heads with
purged chronology. Do not use
stock returns as option returns, marks/lasts as fills, nearby dates, naked short
structures, or CBRS backfill. Controlling design:
`AI_SEMICONDUCTOR_OPTIONS_VOLATILITY_MODEL_DESIGN.md`.

For the Schwab 09:35 late-entry program, run
`audit_schwab_late_entry_readiness.py` before the capture window. It requires
the exact immediately preceding session (not merely any older date), one row
per frozen symbol, Alpha Vantage technical provenance, at least ten historical
call observations per symbol, and the frozen research-only manifest.
`journal_ai_semiconductor_late_intraday_models.py` also requires an explicit
`--prior-session-date` and independently rejects stale technical/call inputs.

## Corrected external LambdaRank future-test candidate (2026-08-06)

Preserve `D:\Downloads\lambdarank_ready.zip` and its isolated extraction. Never
load the bundled joblib. The only controlling implementation is model ID
`external_lambdarank_120_h20_corrected_v2_20260806`, documented in
`EXTERNAL_LAMBDARANK_20D_PREPARATION_20260806.md`. Its safe panel and model
roots are respectively
`D:\AlientAI\Data\Compiled\external_lambdarank_120_h20_corrected_v2_20260806`
and
`D:\AlientAI\Models\external_lambdarank_120_h20_corrected_v2_20260806`.
Preserve the 120-stock universe, SPY context-only role, 13 ranked technical
features, next-session-open entry, twentieth subsequent close, 0.25% cost,
five exact purged folds, 20-session embargo, top-10 policy, model hash, and
all historical evidence. Do not retune.

The future test is `NOT_STARTED`. A future decision must be later than
2026-08-06 and must use a new immutable snapshot from
`build_external_lambdarank_20d_snapshot.py`; never score from the training
panel. Require all 120 candidates and SPY to have the exact completed decision
session, no outcomes attached, matching source/model hashes, and journal
before next-session entry. Fail closed and record an abstention/blocker for
stale, duplicate, malformed, partial, or mismatched data. Evaluate only after
that observation's twentieth subsequent regular-session close.

Schwab has two daily date schemas: `schwab_symbol/datetime` files use the
stored Pacific key plus one calendar day, while
`datetime_ms/datetime_utc` files use the stored U.S. session date with no
offset. Never apply one mapping to both. Same-provider component merges are
allowed only when overlaps match exactly and every component hash is recorded.
Jeff completed fresh Schwab authorization at approximately August 6 22:12
Pacific. The exact 120-candidate refresh and separate SPY refresh completed
with zero HTTP failures, but Schwab returned two rows mapping to the August 6
market session for all 121 required series. NVDA has conflicting closes
(`218.99` versus `218.780147`), and many other pairs have conflicting volume.
Preserve both raw rows, treat the complete duplicate session as unavailable,
and write no snapshot or observation from it. The frozen cutoff already made
August 6 ineligible, so no legitimate decision was missed. The incremental
refresher and living inventory now fail closed on duplicate provider session
keys. Retry the exact source request only after the provider payload settles;
require one unambiguous completed candle for every required series before the
first eligible snapshot. No missed date may be backfilled.

At Jeff's later direction, a separate source-pure Alpha Vantage full
adjusted-daily archive was collected for the exact 120 candidates plus SPY at
`D:\AlientAI\Data\AlphaVantage_2026\external_lambdarank_120_plus_spy_adjusted_daily_full_20260806`.
Its content audit passed 121/121 files with zero failures, exact latest date
2026-08-06, 726 common dates beginning 2023-09-14, and 726-6,731 rows per
series. Preserve this as input to a new Alpha Vantage clone only. Never use it
to unblock, score, extend, or evaluate the frozen Schwab model. A clone needs
new source-specific panels, training, thresholds, sealed-test identity,
model ID, and append-only future journal before it can make any observation.

The pre-freeze `v1` Alpha Vantage build is preserved but permanently rejected:
it split-adjusted volume using future split coefficients, creating a possible
future-information leak. Never use or promote it. The corrected separate
model is frozen as
`external_lambdarank_120_h20_alpha_vantage_v2_20260806`; adjusted OHLC uses
same-date adjusted-close scaling, while volume remains raw and point-in-time.
Its independent
panel audit passed 80,040 feature rows and 77,640 labeled rows. The immutable
split has 497 purged development dates, a 20-session boundary embargo, and a
130-date sealed test. Development passed with Rank IC 0.06197 and exact
top-10 +2.0230% mean net, +1.4517% median, and 56.34% wins. The sealed test
was then opened once and passed with Rank IC 0.08305, exact top-10 +5.1226%
mean net, +2.7377% median, 57.00% wins, and all 20 non-overlap rotations
positive. The independent model audit passed; model SHA256 begins
`7f2c65ca020d`. Treat this as promising but biased historical evidence, not
established profitability.

Its future test is `NOT_STARTED`, and decisions through 2026-08-06 are
immutably ineligible. After each later completed session, collect a new exact
121-series Alpha Vantage adjusted-daily compact/full archive into a new dated
root, run `audit_alpha_vantage_adjusted_daily_archive.py`, then use
`build_external_lambdarank_alpha_vantage_20d_snapshot.py` and
`score_external_lambdarank_alpha_vantage_20d.py` before next-session entry.
Keep its journal, snapshots, outcomes, thresholds, and source completely
separate from the Schwab model. Pending 20-session outcomes never suppress a
new eligible daily observation.

Use
`run_external_lambdarank_alpha_vantage_20d_future_attempt.py --decision-date
YYYY-MM-DD` as the canonical fail-closed orchestrator for that sequence. It
must be launched only after the requested session reaches 16:15 Eastern and
before the next-entry deadline. It checks the immutable cutoff, existing
journal, other Python Alpha Vantage collectors/queues, D-drive free space,
credential presence, exact source audit, snapshot/model hashes, and duplicate
dates. On a valid session it collects a new exact 121-series compact adjusted
archive, audits it, snapshots it, scores it, journals the top ten, refreshes
the inventory, and writes append-only attempt evidence. On a blocked attempt
it writes exact redacted evidence and a safe recovery action; never weaken the
gate or backfill. The first possible decision date is 2026-08-07. A verified
check at 2026-08-06 23:13 Pacific correctly returned `NOT_SCHEDULED_YET`
rather than making provider calls.
