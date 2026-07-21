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

Schema audit detail: the 18,326-row base study already holds technical, short-interest, and insider fields. The current `historical_option_features_matched.jsonl` has only 1,837 rows from a smaller matched study, and `current_fundamental_snapshot_features.jsonl` is a July-2026 cross-sectional snapshot without historical event identities. Do not join either file to the full historical premarket study. Rebuild exact-scope historical feature tables with availability timestamps first. The harvested news records include `time_published` and ticker sentiment; transcripts need an explicit conservative availability-time policy before any historical join.

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

### 5. Build the rare-signal selector

Jeff prefers a few outstanding opportunities over many mediocre picks, but the system must allow multiple signals when several independently meet the same stringent standard. Calibrate probabilities on the natural universe. Evaluate top fractions and minimum sample sizes. Report mean, median, win rate after costs, tail loss, drawdown, turnover, symbol concentration, and regime stability.

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
