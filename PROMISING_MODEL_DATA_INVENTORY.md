# Promising Model Data Inventory

Automatically refreshed: `2026-08-06T18:15:18.536791+00:00`

This is a readiness inventory, not a profitability claim. `DATA_PATH_PRESENT` means no required local dependency is missing; each dated observation must still pass its exact freshness, timing, universe, and hash checks.

## Model readiness

| Model | State | Blocking data |
|---|---|---|
| Technical context + unusual calls | **DATA_PATH_PRESENT** | None in current local audit |
| Nasdaq-101 baseline | **BLOCKED** | schwab_nasdaq101_daily |
| Nasdaq-101 QQQ-relative | **BLOCKED** | schwab_nasdaq101_daily |
| Nasdaq-80 champion | **BLOCKED** | schwab_nasdaq80_daily |
| AI/semiconductor technical + premarket | **BLOCKED** | alpha_ai17_premarket_0925 |
| AI/semiconductor narrative earnings | **BLOCKED** | alpha_ai17_premarket_0925 |
| Original Alpha AI/semiconductor intraday models | **BLOCKED** | alpha_ai17_realtime_premarket_0925 |
| Schwab 09:35 late-entry models | **DATA_PATH_PRESENT** | None in current local audit |
| Autonomous transparent Nasdaq-101 champion | **DATA_PATH_PRESENT** | None in current local audit |
| Defined-risk options model (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
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

## Data requirements

| Requirement | Data type | Source | Latest usable date | State | Timing contract / blocker |
|---|---|---|---|---|---|
| `schwab_sp500_daily` | Daily OHLCV | Schwab | — | **READY** | Completed regular sessions only; source-pure |
| `contextual_technical_panel` | Point-in-time technical features | Schwab daily candles | — | **READY** | Complete same-day universe before selection |
| `alpha_full_universe_option_chains` | Full-universe historical option chains | Alpha Vantage | — | **READY** | Nonempty exact-date chains; empty chains are unavailable |
| `call_history_10` | Lagged call-activity history | Same provider as the observation | — | **READY** | At least ten prior observations per symbol |
| `five_session_daily_outcomes` | Five-session future daily OHLCV | Frozen model source | — | **CONTRACT** | validated when each observation reaches this stage |
| `one_session_daily_outcomes` | One-session future daily OHLCV | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `schwab_nasdaq101_daily` | Daily OHLCV for 101-symbol universe | Schwab | 2026-08-04 | **BLOCKED** | stale session 2026-08-04 (stored 2026-08-03); expected 2026-08-05 |
| `qqq_daily` | QQQ benchmark daily OHLCV | Schwab | — | **READY** | Same completed session as Nasdaq universe |
| `nasdaq_frozen_artifacts` | Frozen model/report/manifest hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `schwab_nasdaq80_daily` | Daily OHLCV for frozen 80-symbol universe | Schwab | 2026-08-04 | **BLOCKED** | stale session 2026-08-04 (stored 2026-08-03); expected 2026-08-05 |
| `nasdaq80_frozen_artifacts` | Frozen model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_daily` | Daily OHLCV for frozen 17-symbol universe | Alpha Vantage | 2026-08-05 | **READY** | Complete decision-session close before next-open selection |
| `alpha_ai17_prior_daily` | Prior-session technical features for 17 symbols | Alpha Vantage | 2026-08-05 | **READY** | Exact immediately preceding completed session |
| `alpha_ai17_premarket_0925` | Extended-hours five-minute premarket features | Alpha Vantage | 2026-08-04 | **BLOCKED** | only 0 usable rows; 17 required |
| `timestamped_earnings_events` | Earnings events and guidance available timestamps | Alpha Vantage archived earnings data | — | **READY** | available_at_utc must be no later than decision cutoff |
| `ai17_frozen_artifacts` | Frozen five-session model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `narrative_frozen_artifacts` | Frozen narrative model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_prior_calls` | Prior-session unusual call-option features | Alpha Vantage | 2026-08-05 | **READY** | Exact prior session only; calls, not puts/sell volume |
| `alpha_ai17_realtime_premarket_0925` | Realtime five-minute premarket candles | Alpha Vantage realtime entitlement | 2026-08-03 | **BLOCKED** | manifest status=failed_closed, completed=0, unavailable=0, failed=1; 17 completed required |
| `alpha_ai17_exact_intraday_outcomes` | Exact 09:30-10:25 five-minute outcome path | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `alpha_intraday_frozen_artifacts` | Six frozen intraday model/report hashes | Local immutable artifacts | — | **READY** | Hashes and 09:30 timing contract must match |
| `schwab_ai17_0925_snapshot` | Current-session extended-hours five-minute snapshot | Schwab | 2026-08-06 | **READY** | All exact 09:25 interval-start candles captured 09:30-09:34:59 ET |
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
