# Promising Model Data Inventory

Automatically refreshed: `2026-08-12T00:17:33.399645+00:00`

This is a readiness inventory, not a profitability claim. `DATA_PATH_PRESENT` means no required local dependency is missing; each dated observation must still pass its exact freshness, timing, universe, and hash checks.

## Paper control readiness

| State | Sole enabled model | Paper buys | Live trading | Current payload / blocker |
|---|---|---|---|---|
| **DISABLED** | `configuration mismatch` | enabled | disabled | duplicate source sessions are unusable for 46/102 symbols; examples: ADBE=2026-08-05, AMD=2026-08-05, GOOGL=2026-08-05, GOOG=2026-08-05, AMZN=2026-08-05 |

Paper-account actions are simulation evidence and are never merged into prospective model evidence.

## Model readiness

| Model | State | Blocking data |
|---|---|---|
| Technical context + unusual calls | **DATA_PATH_PRESENT** | None in current local audit |
| Nasdaq-101 baseline | **BLOCKED** | schwab_nasdaq101_daily |
| Nasdaq-101 QQQ-relative | **BLOCKED** | schwab_nasdaq101_daily |
| Nasdaq-80 champion | **BLOCKED** | schwab_nasdaq80_daily |
| AI/semiconductor technical + premarket | **BLOCKED** | alpha_ai17_daily, alpha_ai17_premarket_0925 |
| AI/semiconductor narrative earnings | **BLOCKED** | alpha_ai17_daily, alpha_ai17_premarket_0925 |
| Original Alpha AI/semiconductor intraday models | **BLOCKED** | alpha_ai17_prior_daily, alpha_ai17_prior_calls, alpha_ai17_realtime_premarket_0925 |
| Schwab 09:35 late-entry models | **BLOCKED** | alpha_ai17_prior_daily, alpha_ai17_prior_calls |
| Autonomous transparent Nasdaq-101 champion | **DATA_PATH_PRESENT** | None in current local audit |
| Defined-risk options model (development) | **DEVELOPMENT_NOT_TESTING** | alpha_ai17_daily |
| Any-time 5/10/20/30/60/90-minute Nasdaq-101 clones (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Any-time 5/10/20/30/60/90-minute AI/semi-17 clones (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Exact Nasdaq + AI semiconductor five-day roadmap (development) | **DEVELOPMENT_NOT_TESTING** | nasdaq_quarterly_point_in_time_membership, nasdaq_ai_roadmap_point_in_time_fundamentals, nasdaq_ai_roadmap_known_earnings_calendar, nasdaq_ai_roadmap_readiness_audit |
| Nasdaq-100 daily + five-minute cross-sectional ranker, 5 sessions (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq-100 daily + five-minute cross-sectional ranker, 20 sessions (blocked development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready daily + five-minute cross-sectional ranker, 5 sessions (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready daily + five-minute cross-sectional ranker, 20 sessions (blocked development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq-100 daily-only technical + call-options ranker, 5 sessions (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq-100 daily-only technical + call-options ranker, 20 sessions (blocked development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready daily-only technical + call-options ranker, 5 sessions (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready daily-only technical + call-options ranker, 20 sessions (blocked development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq-100 pure daily-technical ranker, 5 sessions (development hold) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq-100 pure daily-technical ranker, 20 sessions (sealed-test failure) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready pure daily-technical ranker, 5 sessions (development hold) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| S&P data-ready pure daily-technical ranker, 20 sessions (development hold) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Full-archive Nasdaq-101 daily + five-minute technical ranker, 5 sessions (cancelled partial archive) | **DEVELOPMENT_NOT_TESTING** | full_nasdaq_adjusted_5min_audit, full_archive_multiresolution_panel_audit, full_archive_multiresolution_h05_report, full_archive_multiresolution_model_audit |
| Full-archive Nasdaq-101 daily + five-minute technical ranker, 20 sessions (cancelled partial archive) | **DEVELOPMENT_NOT_TESTING** | full_nasdaq_adjusted_5min_audit, full_archive_multiresolution_panel_audit, full_archive_multiresolution_h20_report, full_archive_multiresolution_model_audit |
| External clean-rank S&P-120-style 20-session model (audit hold) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Corrected external LambdaRank 120-stock model, 20 sessions | **BLOCKED** | external_lambdarank_primary_schwab_daily, external_lambdarank_future_snapshot |
| Source-pure Alpha Vantage LambdaRank clone candidate, 20 sessions | **BLOCKED** | external_lambdarank_alpha_vantage_future_snapshot |
| Calibrated first-passage probability bounds, 10 sessions | **BLOCKED** | barrier_probability_future_snapshot |
| Superseded all-market small-cap baseline clone (zero observations) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Nasdaq small-cap range/volume baseline clone, 5 sessions | **DEVELOPMENT_NOT_TESTING** | nasdaq_smallcap_clone_readiness, nasdaq_smallcap_clone_future_snapshot |

## Data requirements

| Requirement | Data type | Source | Latest usable date | State | Timing contract / blocker |
|---|---|---|---|---|---|
| `schwab_sp500_daily` | Daily OHLCV | Schwab | — | **READY** | Completed regular sessions only; source-pure |
| `contextual_technical_panel` | Point-in-time technical features | Schwab daily candles | — | **READY** | Complete same-day universe before selection |
| `alpha_full_universe_option_chains` | Full-universe historical option chains | Alpha Vantage | — | **READY** | Nonempty exact-date chains; empty chains are unavailable |
| `call_history_10` | Lagged call-activity history | Same provider as the observation | — | **READY** | At least ten prior observations per symbol |
| `five_session_daily_outcomes` | Five-session future daily OHLCV | Frozen model source | — | **CONTRACT** | validated when each observation reaches this stage |
| `one_session_daily_outcomes` | One-session future daily OHLCV | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `schwab_nasdaq101_daily` | Daily OHLCV for 101-symbol universe | Schwab | 2026-08-04 | **BLOCKED** | duplicate source sessions are unusable for 46/102 symbols; examples: ADBE=2026-08-05, AMD=2026-08-05, GOOGL=2026-08-05, GOOG=2026-08-05, AMZN=2026-08-05 |
| `qqq_daily` | QQQ benchmark daily OHLCV | Schwab | — | **READY** | Same completed session as Nasdaq universe |
| `nasdaq_frozen_artifacts` | Frozen model/report/manifest hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `schwab_nasdaq80_daily` | Daily OHLCV for frozen 80-symbol universe | Schwab | 2026-08-04 | **BLOCKED** | duplicate source sessions are unusable for 42/80 symbols; examples: AAPL=2026-08-05, ADBE=2026-08-05, ADI=2026-08-05, ADP=2026-08-05, AMAT=2026-08-05 |
| `nasdaq80_frozen_artifacts` | Frozen model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_daily` | Daily OHLCV for frozen 17-symbol universe | Alpha Vantage | 2026-08-05 | **BLOCKED** | stale date 2026-08-05; expected 2026-08-11 |
| `alpha_ai17_prior_daily` | Prior-session technical features for 17 symbols | Alpha Vantage | 2026-08-05 | **BLOCKED** | stale date 2026-08-05; expected 2026-08-11 |
| `alpha_ai17_premarket_0925` | Extended-hours five-minute premarket features | Alpha Vantage | 2026-08-04 | **BLOCKED** | only 0 usable rows; 17 required |
| `timestamped_earnings_events` | Earnings events and guidance available timestamps | Alpha Vantage archived earnings data | — | **READY** | available_at_utc must be no later than decision cutoff |
| `ai17_frozen_artifacts` | Frozen five-session model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `narrative_frozen_artifacts` | Frozen narrative model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_prior_calls` | Prior-session unusual call-option features | Alpha Vantage | 2026-08-05 | **BLOCKED** | stale date 2026-08-05; expected 2026-08-11 |
| `alpha_ai17_realtime_premarket_0925` | Realtime five-minute premarket candles | Alpha Vantage realtime entitlement | 2026-08-03 | **BLOCKED** | manifest status=failed_closed, completed=0, unavailable=0, failed=1; 17 completed required |
| `alpha_ai17_exact_intraday_outcomes` | Exact 09:30-10:25 five-minute outcome path | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `alpha_intraday_frozen_artifacts` | Six frozen intraday model/report hashes | Local immutable artifacts | — | **READY** | Hashes and 09:30 timing contract must match |
| `schwab_ai17_0925_snapshot` | Current-session extended-hours five-minute snapshot | Schwab | 2026-08-11 | **READY** | All exact 09:25 interval-start candles captured 09:30-09:34:59 ET |
| `schwab_ai17_1030_outcomes` | Exact 09:35-entry through 10:30-bar outcome path | Schwab | — | **CONTRACT** | validated when each observation reaches this stage |
| `schwab_late_frozen_artifacts` | Frozen Schwab late-entry model/report hashes | Local immutable artifacts | — | **READY** | Hashes and 09:35 timing contract must match |
| `point_in_time_option_selection_chains` | Option chain observable at selection | Alpha Vantage archive | — | **READY** | Selection snapshot strictly before entry snapshot |
| `later_option_entry_chains` | Executable option quotes at simulated entry | Alpha Vantage archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `later_option_exit_chains` | Matching-contract option quotes at simulated exit | Alpha Vantage archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `option_quotes_liquidity_and_fees` | Bid/ask, volume, open interest, IV and fees | Archived option chains | — | **CONTRACT** | validated when each observation reaches this stage |
| `purged_option_training_labels` | Direction and absolute-move option labels | Exact compiled option outcomes | — | **CONTRACT** | validated when each observation reaches this stage |
| `adjusted_five_minute_archive` | Adjusted five-minute intraday candles | Alpha Vantage | — | **READY** | Audited complete archive; interval-start timestamps |
| `adjusted_one_minute_archive` | Adjusted one-minute intraday candles | Alpha Vantage | — | **READY** | Completed 8,137-request monthly archive; independent content audit passed on 82,425,431 rows with zero orphan files |
| `rolling_archive_supplement_9` | Nine-symbol AI/data-center intraday supplement | Alpha Vantage | — | **READY** | Completed 869-request archive; independent audit passed on 793 gzip files and 10,412,846 rows with 76 explicitly unavailable months and zero orphans |
| `market_and_sector_context` | QQQ/SPY/semiconductor market context | Same source and timestamp as rolling observation | — | **CONTRACT** | validated when each observation reaches this stage |
| `one_minute_live_source_compatibility` | Current-session one-minute candles and source-agreement audit | Schwab live candidate versus Alpha Vantage training archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `purged_rolling_multi_horizon_labels` | Any-time 5/10/20/30/60/90-minute forward labels | Audited one-minute archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `autonomous_daily_adjusted_archive` | Nasdaq-101 plus QQQ/SPY full adjusted daily candles | Alpha Vantage | — | **READY** | Completed regular sessions only; all candidates and both context benchmarks must share the decision date |
| `autonomous_transparent_frozen_report` | Frozen transparent-model formula, gates, validation and sealed test | Immutable local research artifact | — | **READY** | Report SHA-256 and frozen formula must match every prospective observation |
| `autonomous_prospective_journal` | Append-only pre-entry prospective selections and abstentions | Frozen model applied to Alpha Vantage adjusted daily data | — | **READY** | Journal after the completed decision close and strictly before the next regular-session open; no backfill |
| `twenty_session_daily_outcomes` | Exact 20-session prospective outcomes | Alpha Vantage adjusted daily archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `nasdaq_ai_roadmap_contract` | Immutable five-session model, feature, timing, validation and safety contract | Jeff-supplied roadmap normalized into local machine-readable contract | — | **READY** | Five-session next-open to fifth-close label; 0.25% cost; whole-date purge and embargo; research only |
| `nasdaq_quarterly_point_in_time_membership` | Quarterly historical Nasdaq-100 membership with provenance and known timestamps | Authorized dated constituent source | — | **BLOCKED** | no file matches D:/AlientAI/Data/PointInTime/nasdaq100_quarterly_membership.jsonl |
| `nasdaq_ai_roadmap_adjusted_daily_context` | Full adjusted daily candidates plus QQQ, SMH, SOXX, VIX and NVDA regime context | Alpha Vantage source-pure archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `nasdaq_ai_roadmap_point_in_time_fundamentals` | Revenue/EPS growth, gross-margin trend and earnings beat/miss streak | Timestamped filings and earnings facts | — | **BLOCKED** | no file matches D:/AlientAI/Data/PointInTime/nasdaq_ai_roadmap_fundamentals.jsonl |
| `nasdaq_ai_roadmap_known_earnings_calendar` | Historically known next-earnings dates | Timestamped earnings calendar archive | — | **BLOCKED** | no file matches D:/AlientAI/Data/PointInTime/nasdaq_ai_roadmap_earnings_calendar.jsonl |
| `nasdaq_ai_roadmap_readiness_audit` | Content- and timing-level fail-closed readiness result | audit_nasdaq_ai_roadmap_5d_readiness.py | — | **BLOCKED** | JSON status='BLOCKED'; required 'READY_TO_BUILD_PANEL' |
| `multiresolution_nasdaq_daily` | Full adjusted daily OHLCV for 101 Nasdaq candidates plus QQQ/SPY context | Alpha Vantage | — | **READY** | Completed decision session only; adjusted ratios and next-open/horizon-close labels |
| `multiresolution_sp500_daily` | Long daily OHLCV for the 483-symbol S&P data-ready list | Schwab candidates; Alpha Vantage QQQ/SPY context only | — | **READY** | Schwab stored key maps plus one calendar day to the U.S. session; context never supplies candidate labels |
| `multiresolution_nasdaq_intraday` | Decision-session regular and 16:00-20:00 ET intraday OHLCV | Alpha Vantage one-minute archive aggregated to five-minute | — | **READY** | Completed bars only; bounded no-trade intervals carry the last known price with zero volume and expose observed-bar fractions |
| `multiresolution_sp500_intraday` | Decision-session regular and 16:00-20:00 ET five-minute OHLCV | Alpha Vantage native five-minute archive | — | **READY** | Completed bars only; regular endpoints and at least one after-hours print required |
| `multiresolution_options` | Recent call-side activity and strictly lagged unusual-call baselines | Alpha Vantage historical option-chain aggregates | — | **READY** | Nonempty chains only; unavailable is missing, never zero; aggregate activity is not claimed to prove buyer initiation |
| `multiresolution_news` | Ticker-specific recent headline count, recency, and sentiment | Alpha Vantage NEWS_SENTIMENT archive | — | **READY** | Articles published after each request's as_of_utc are excluded; full news variant remains blocked below 60 adequately covered dates |
| `multiresolution_nasdaq_panel` | Audited Nasdaq-100 cross-sectional panel with 5- and 20-session labels | Local point-in-time compiler | — | **READY** | Exact 101-symbol date-local ranks; decision at 20:00 ET; next-open entry; 0.25% cost |
| `multiresolution_sp500_panel` | Audited S&P data-ready cross-sectional panel with 5- and 20-session labels | Local point-in-time compiler | — | **READY** | At least 90% cross-sectional coverage per date; decision at 20:00 ET; next-open entry; 0.25% cost |
| `multiresolution_nasdaq_h05_report` | Purged LightGBM/XGBoost five-session ablation report | Local immutable historical screen | — | **READY** | Whole-date folds, five-session purge/embargo, unopened sealed test after validation failure |
| `multiresolution_nasdaq_h20_report` | Twenty-session chronology-readiness report | Local fail-closed historical screen | — | **READY** | Blocked until at least 120 common dates exist |
| `multiresolution_sp500_h05_report` | Purged LightGBM/XGBoost five-session ablation report | Local immutable historical screen | — | **READY** | Whole-date folds, five-session purge/embargo, unopened sealed test after validation failure |
| `multiresolution_sp500_h20_report` | Twenty-session chronology-readiness report | Local fail-closed historical screen | — | **READY** | Blocked until at least 120 common dates exist |
| `daily_options_nasdaq_panel` | Audited Nasdaq-100 daily-only technical and call-option panel | Local point-in-time compiler | — | **READY** | Exact 101-symbol date-local ranks; QQQ/SPY context-only; no intraday, after-hours, or news sources |
| `daily_options_sp500_panel` | Audited S&P data-ready daily-only technical and call-option panel | Local point-in-time compiler | — | **READY** | Exact 483-symbol date-local ranks; QQQ/SPY context-only; no intraday, after-hours, or news sources |
| `daily_options_nasdaq_h05_report` | Purged daily-only LightGBM/XGBoost five-session report | Local immutable historical screen | — | **READY** | Daily technical and daily-plus-calls same-sample comparison; unopened sealed test after validation failure |
| `daily_options_nasdaq_h20_report` | Daily-only twenty-session chronology-readiness report | Local fail-closed historical screen | — | **READY** | Blocked until at least 120 common call-history dates exist |
| `daily_options_sp500_h05_report` | Purged daily-only LightGBM/XGBoost five-session report | Local immutable historical screen | — | **READY** | Daily technical and daily-plus-calls same-sample comparison; unopened sealed test after validation failure |
| `daily_options_sp500_h20_report` | Daily-only twenty-session chronology-readiness report | Local fail-closed historical screen | — | **READY** | Blocked until at least 120 common call-history dates exist |
| `technical_only_nasdaq_panel` | Audited exact-101 pure daily-technical panel | Alpha Vantage adjusted daily candidates and QQQ/SPY context | — | **READY** | Full candidate coverage every date; no option, news, event, intraday, premarket, or after-hours source |
| `technical_only_sp500_panel` | Audited exact-483 pure daily-technical panel | Schwab daily candidates; Alpha Vantage QQQ/SPY context only | — | **READY** | Full candidate coverage every date; no option, news, event, intraday, premarket, or after-hours source |
| `technical_only_nasdaq_h05_report` | Purged pure-technical Nasdaq five-session report | Local immutable historical screen | — | **READY** | Development gate failed; sealed test remains unloaded |
| `technical_only_nasdaq_h20_report` | Purged pure-technical Nasdaq twenty-session report | Local immutable historical screen | — | **READY** | Development passed; sealed test opened once and failed; never retune against opened period |
| `technical_only_sp500_h05_report` | Purged pure-technical S&P five-session report | Local immutable historical screen | — | **READY** | Development gate failed; sealed test remains unloaded |
| `technical_only_sp500_h20_report` | Purged pure-technical S&P twenty-session report | Local immutable historical screen | — | **READY** | Development gate failed; sealed test remains unloaded |
| `full_nasdaq_adjusted_daily_audit` | Full active-Nasdaq adjusted-daily content audit | Alpha Vantage | — | **READY** | Exact frozen 6,247-symbol listing, explicit gaps, adjusted OHLC plus raw volume/dividend/split records; no source splice |
| `full_nasdaq_adjusted_5min_audit` | Full active-Nasdaq adjusted five-minute content audit | Alpha Vantage | — | **BLOCKED** | no file matches D:/AlientAI/Data/AlphaVantage_2026/full_nasdaq_active_stock_etf_adjusted_5min_201608_202607_20260807/content_audit.json |
| `full_archive_multiresolution_technical_spec` | Pre-result frozen full-archive technical model specification | AlienTAI research contract | — | **READY** | Exact Nasdaq-101 candidates, QQQ/SPY context only, technicals only, 5/20 sessions, next-open entry, 0.25% cost |
| `full_archive_multiresolution_panel_audit` | Full-archive multi-resolution panel and sealed-shard audit | AlienTAI compiler over independently audited Alpha Vantage archives | — | **BLOCKED** | no file matches D:/AlientAI/Data/Compiled/full_archive_multiresolution_nasdaq101_v1_20260807/content_audit.json |
| `full_archive_multiresolution_h05_report` | Purged full-archive Nasdaq five-session training report | AlienTAI LightGBM/XGBoost technical trainer | — | **BLOCKED** | no file matches D:/AlientAI/Models/full_archive_multiresolution_nasdaq101_h05_v1_20260807/training_report.json |
| `full_archive_multiresolution_h20_report` | Purged full-archive Nasdaq twenty-session training report | AlienTAI LightGBM/XGBoost technical trainer | — | **BLOCKED** | no file matches D:/AlientAI/Models/full_archive_multiresolution_nasdaq101_h20_v1_20260807/training_report.json |
| `full_archive_multiresolution_model_audit` | Independent validation-decision and model-artifact audit for both full-archive horizons | AlienTAI independent local auditor | — | **BLOCKED** | no file matches D:/AlientAI/Models/full_archive_multiresolution_nasdaq101_v1_20260807_model_audit.json |
| `external_clean_rank_bundle` | External scripts and saved S&P-style predictions | Jeff-supplied ZIP | — | **READY** | Immutable source hash only; all outcomes through 2026-07-09 are exposed and cannot become a sealed test |
| `external_clean_rank_audit` | Independent integrity, metric, purge, and robustness audit | AlienTAI local read-only review | — | **READY** | Development evidence only; exact defects must be corrected before any new prospective contract |
| `external_barrier_probability_bundle` | Jeff-supplied barrier-probability source bundle | Immutable external ZIP | — | **READY** | SHA256 acfce81f6e6faa4b79dbcbb6f6a9fd0b2277cd57b21a01ee977636a559f55bba; bundled joblib remains quarantined and unloaded; exposed reports are development evidence only |
| `barrier_probability_frozen_spec` | Frozen corrected first-passage probability contract | AlienTAI research specification | — | **READY** | Completed decision close; next-session adjusted-open reference; +1.5%/-0.5% barriers; maximum ten sessions; daily ambiguity represented as probability bounds |
| `barrier_probability_alpha_daily_inputs` | Full adjusted-daily histories for the exact 48-symbol barrier universe | Alpha Vantage TIME_SERIES_DAILY_ADJUSTED | — | **READY** | One source file per symbol; same-row adjusted OHLC and raw point-in-time volume; MS/NOW unadjusted compact rows excluded; every source hash frozen in the panel manifest |
| `barrier_probability_panel_audit` | Independent source, label, feature-sample, chronology, and sealed-partition audit | AlienTAI local auditor | — | **READY** | 188,667 labels reconstructed; two-sided ten-session development embargoes; label information must end within its assigned stage |
| `barrier_probability_model_audit` | Independent LightGBM text-model, calibration, validation-gate, and one-time sealed-test audit | AlienTAI local auditor | — | **READY** | Both bound heads rescored; 29,516 sealed probabilities verified; prospective eligibility begins with the completed 2026-08-07 session |
| `barrier_probability_future_snapshot` | Outcome-free exact-48 barrier feature snapshot and append-only probability journal | New independently audited Alpha Vantage adjusted-daily archive | — | **BLOCKED** | no file matches D:/AlientAI/Data/Prospective/barrier_probability_48_h10_alpha_vantage_v1_*/snapshot_manifest.json |
| `barrier_probability_ten_session_outcomes` | Append-only prospective first-passage outcomes | Exact source-tagged Alpha Vantage adjusted-daily observation route | — | **CONTRACT** | validated when each observation reaches this stage |
| `external_lambdarank_bundle` | Jeff-supplied LambdaRank source bundle | Immutable external ZIP | — | **READY** | SHA256 dcfcd7e3403d93842ec732b2b8a46d99cf71fe8e15176ff7c1041299d94aff4d; bundled joblib is untrusted and must remain quarantined and unloaded |
| `external_lambdarank_panel_audit` | Corrected source-pure 120-stock training panel audit | Schwab daily OHLCV with per-file date-schema mapping | — | **READY** | Next-session-open entry, twentieth subsequent close, 0.25% cost, exact full-universe dates, purged labels |
| `external_lambdarank_model_audit` | Safe LightGBM text-model and OOF evidence audit | AlienTAI corrected LambdaRank trainer | — | **READY** | Development gate only; no historical sealed test; future-only eligibility begins after 2026-08-06 |
| `external_lambdarank_primary_schwab_daily` | Primary daily OHLCV for the exact 120-stock universe plus SPY | Schwab | 2026-08-05 | **BLOCKED** | duplicate source sessions are unusable for 121/121 symbols; examples: AAPL=2026-08-05, MSFT=2026-08-05, NVDA=2026-08-05, AMZN=2026-08-05, META=2026-08-05 |
| `external_lambdarank_alpha_vantage_daily_clone_input` | Source-pure full adjusted-daily archive for the exact 120-stock universe plus SPY | Alpha Vantage | — | **READY** | Separate clone input only; full TIME_SERIES_DAILY_ADJUSTED through 2026-08-06; never substitute into or evaluate the frozen Schwab model |
| `external_lambdarank_alpha_vantage_panel_audit` | Source-pure Alpha Vantage 120-stock panel and sealed-split audit | Alpha Vantage | — | **READY** | Adjusted OHLC, raw point-in-time volume, exact 120-name cross-sections, next-open to twentieth-close labels, 20-session boundary embargo |
| `external_lambdarank_alpha_vantage_model_audit` | Alpha Vantage LightGBM model and one-time sealed-test audit | AlienTAI source-pure trainer | — | **READY** | Fixed hyperparameters and top-10 policy; 497-date purged development followed by one 130-date sealed test; future eligibility begins after 2026-08-06 |
| `external_lambdarank_alpha_vantage_future_snapshot` | Immutable prospective Alpha Vantage 120-name feature snapshot | Alpha Vantage TIME_SERIES_DAILY_ADJUSTED | — | **BLOCKED** | no file matches D:/AlientAI/Data/Prospective/external_lambdarank_120_h20_alpha_vantage_v2_*/snapshot_manifest.json |
| `external_lambdarank_alpha_vantage_twenty_session_outcomes` | Future-only Alpha Vantage twenty-session outcomes | The exact source-tagged Alpha Vantage observation archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `approved_source_fallback_registry` | Jeff-authorized source-pure Alpha Vantage/Schwab fallback routes | Immutable local routing registry and independent validator | — | **READY** | Route only between separately identified complete-provider model observations; never splice rows, rewrite frozen evidence, backfill, or shorten a frozen/prospective horizon |
| `external_lambdarank_fallback_schwab_daily` | Same-provider long-history fallback for TSM and SPY | Schwab | — | **READY** | datetime_ms/datetime_utc schema uses the stored U.S. session date with no offset; exact overlap equality is required before a component merge |
| `external_lambdarank_future_snapshot` | Immutable prospective 120-name feature snapshot | Corrected Schwab snapshot builder | — | **BLOCKED** | no file matches D:/AlientAI/Data/Prospective/external_lambdarank_120_h20_corrected_v2_*/snapshot_manifest.json |
| `external_lambdarank_twenty_session_outcomes` | Future-only twenty-session next-open-to-close outcomes | The exact frozen Schwab observation source | — | **CONTRACT** | validated when each observation reaches this stage |
| `us_smallcap_clone_contract` | Frozen model-3 artifact identity and all-market small-cap screen | AlienTAI immutable research contract | — | **READY** | Same Schwab model/features/horizon/cost/cutoff/capacity; only the point-in-time candidate universe changes |
| `us_smallcap_clone_readiness` | Exact all-market listing, Schwab daily-history, market-cap, source and cutoff readiness | AlienTAI fail-closed readiness audit | — | **BLOCKED** | JSON status='BLOCKED_WITH_EXACT_DATA_EVIDENCE'; required 'READY_TO_SCORE' |
| `us_smallcap_clone_future_snapshot` | Immutable screened-universe scores and selections | Frozen model-3 artifact over a source-pure Schwab all-market snapshot | — | **BLOCKED** | no file matches D:/AlientAI/Data/Prospective/us_smallcap_range_volume_baseline_clone_h05_v1_*/snapshot.json |
| `us_smallcap_clone_five_session_outcomes` | Append-only five-session prospective outcomes | The exact source-tagged Schwab observation route | — | **CONTRACT** | validated when each observation reaches this stage |
| `us_smallcap_clone_superseded` | Immutable scope-replacement record | Jeff's explicit Nasdaq-only universe direction | — | **READY** | All-market setup produced zero observations and may not resume under its old model ID |
| `nasdaq_smallcap_clone_contract` | Frozen model-3 artifact identity and Nasdaq-only small-cap screen | AlienTAI immutable research contract | — | **READY** | Same Schwab model/features/horizon/cost/cutoff/capacity; only the point-in-time Nasdaq candidate universe changes |
| `nasdaq_smallcap_clone_readiness` | Exact Nasdaq listing, Schwab daily-history, market-cap, source and cutoff readiness | AlienTAI fail-closed readiness audit | — | **BLOCKED** | JSON status='BLOCKED_WITH_EXACT_DATA_EVIDENCE'; required 'READY_TO_SCORE' |
| `nasdaq_smallcap_clone_future_snapshot` | Immutable Nasdaq-screened universe scores and selections | Frozen model-3 artifact over a source-pure Schwab Nasdaq snapshot | — | **BLOCKED** | no file matches D:/AlientAI/Data/Prospective/nasdaq_smallcap_range_volume_baseline_clone_h05_v1_*/snapshot.json |
| `nasdaq_smallcap_clone_five_session_outcomes` | Append-only five-session prospective outcomes | The exact source-tagged Schwab observation route | — | **CONTRACT** | validated when each observation reaches this stage |
