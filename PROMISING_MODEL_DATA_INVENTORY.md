# Promising Model Data Inventory

Automatically refreshed: `2026-08-04T16:12:25.318925+00:00`

This is a readiness inventory, not a profitability claim. `DATA_PATH_PRESENT` means no required local dependency is missing; each dated observation must still pass its exact freshness, timing, universe, and hash checks.

## Model readiness

| Model | State | Blocking data |
|---|---|---|
| Technical context + unusual calls | **BLOCKED** | alpha_full_universe_option_chains |
| Nasdaq-101 baseline | **DATA_PATH_PRESENT** | None in current local audit |
| Nasdaq-101 QQQ-relative | **DATA_PATH_PRESENT** | None in current local audit |
| Nasdaq-80 champion | **DATA_PATH_PRESENT** | None in current local audit |
| AI/semiconductor technical + premarket | **BLOCKED** | alpha_ai17_premarket_0925 |
| AI/semiconductor narrative earnings | **BLOCKED** | alpha_ai17_premarket_0925 |
| Original Alpha AI/semiconductor intraday models | **BLOCKED** | alpha_ai17_realtime_premarket_0925 |
| Schwab 09:35 late-entry models | **BLOCKED** | schwab_ai17_0925_snapshot |
| Defined-risk options model (development) | **DEVELOPMENT_NOT_TESTING** | None in current local audit |
| Any-time rolling 20-minute model (development) | **DEVELOPMENT_NOT_TESTING** | adjusted_one_minute_archive |

## Data requirements

| Requirement | Data type | Source | Latest usable date | State | Timing contract / blocker |
|---|---|---|---|---|---|
| `schwab_sp500_daily` | Daily OHLCV | Schwab | — | **READY** | Completed regular sessions only; source-pure |
| `contextual_technical_panel` | Point-in-time technical features | Schwab daily candles | — | **READY** | Complete same-day universe before selection |
| `alpha_full_universe_option_chains` | Full-universe historical option chains | Alpha Vantage | — | **BLOCKED** | no file matches D:/AlientAI/Data/AlphaVantage_2026/contextual_options_prospective_*/manifest.json |
| `call_history_10` | Lagged call-activity history | Same provider as the observation | — | **READY** | At least ten prior observations per symbol |
| `five_session_daily_outcomes` | Five-session future daily OHLCV | Frozen model source | — | **CONTRACT** | validated when each observation reaches this stage |
| `one_session_daily_outcomes` | One-session future daily OHLCV | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `schwab_nasdaq101_daily` | Daily OHLCV for 101-symbol universe | Schwab | 2026-08-03 | **READY** | Latest common completed session; never splice providers |
| `qqq_daily` | QQQ benchmark daily OHLCV | Schwab | — | **READY** | Same completed session as Nasdaq universe |
| `nasdaq_frozen_artifacts` | Frozen model/report/manifest hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `schwab_nasdaq80_daily` | Daily OHLCV for frozen 80-symbol universe | Schwab | 2026-08-03 | **READY** | Latest common completed session |
| `nasdaq80_frozen_artifacts` | Frozen model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_daily` | Daily OHLCV for frozen 17-symbol universe | Alpha Vantage | 2026-08-03 | **READY** | Complete decision-session close before next-open selection |
| `alpha_ai17_prior_daily` | Prior-session technical features for 17 symbols | Alpha Vantage | 2026-08-03 | **READY** | Exact immediately preceding completed session |
| `alpha_ai17_premarket_0925` | Extended-hours five-minute premarket features | Alpha Vantage | 2026-08-04 | **BLOCKED** | only 0 usable rows; 17 required |
| `timestamped_earnings_events` | Earnings events and guidance available timestamps | Alpha Vantage archived earnings data | — | **READY** | available_at_utc must be no later than decision cutoff |
| `ai17_frozen_artifacts` | Frozen five-session model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `narrative_frozen_artifacts` | Frozen narrative model/report/universe hashes | Local immutable artifacts | — | **READY** | Hashes must match before every observation |
| `alpha_ai17_prior_calls` | Prior-session unusual call-option features | Alpha Vantage | 2026-08-03 | **READY** | Exact prior session only; calls, not puts/sell volume |
| `alpha_ai17_realtime_premarket_0925` | Realtime five-minute premarket candles | Alpha Vantage realtime entitlement | 2026-08-03 | **BLOCKED** | manifest status=failed_closed, completed=0, unavailable=0, failed=1; 17 completed and 0 accounted required |
| `alpha_ai17_exact_intraday_outcomes` | Exact 09:30-10:25 five-minute outcome path | Alpha Vantage | — | **CONTRACT** | validated when each observation reaches this stage |
| `alpha_intraday_frozen_artifacts` | Six frozen intraday model/report hashes | Local immutable artifacts | — | **READY** | Hashes and 09:30 timing contract must match |
| `schwab_ai17_0925_snapshot` | Current-session extended-hours five-minute snapshot | Schwab | — | **BLOCKED** | no file matches D:/AlientAI/Data/Schwab_2026/ai_semiconductor_late_*/manifest.json |
| `schwab_ai17_1030_outcomes` | Exact 09:35-entry through 10:30-bar outcome path | Schwab | — | **CONTRACT** | validated when each observation reaches this stage |
| `schwab_late_frozen_artifacts` | Frozen Schwab late-entry model/report hashes | Local immutable artifacts | — | **READY** | Hashes and 09:35 timing contract must match |
| `point_in_time_option_selection_chains` | Option chain observable at selection | Alpha Vantage archive | — | **READY** | Selection snapshot strictly before entry snapshot |
| `later_option_entry_chains` | Executable option quotes at simulated entry | Alpha Vantage archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `later_option_exit_chains` | Matching-contract option quotes at simulated exit | Alpha Vantage archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `option_quotes_liquidity_and_fees` | Bid/ask, volume, open interest, IV and fees | Archived option chains | — | **CONTRACT** | validated when each observation reaches this stage |
| `purged_option_training_labels` | Direction and absolute-move option labels | Exact compiled option outcomes | — | **CONTRACT** | validated when each observation reaches this stage |
| `adjusted_five_minute_archive` | Adjusted five-minute intraday candles | Alpha Vantage | — | **READY** | Audited complete archive; interval-start timestamps |
| `adjusted_one_minute_archive` | Adjusted one-minute intraday candles | Alpha Vantage | — | **BLOCKED** | manifest status=running, completed=189, unavailable=32, failed=0; 0 completed and 8137 accounted required |
| `rolling_archive_supplement_9` | Nine-symbol AI/data-center intraday supplement | Alpha Vantage | — | **BLOCKED** | no file matches D:/AlientAI/Data/AlphaVantage_2026/rolling_20m_ai_data_center_supplement_202001_202607 |
| `market_and_sector_context` | QQQ/SPY/semiconductor market context | Same source and timestamp as rolling observation | — | **CONTRACT** | validated when each observation reaches this stage |
| `one_minute_live_source_compatibility` | Current-session one-minute candles and source-agreement audit | Schwab live candidate versus Alpha Vantage training archive | — | **CONTRACT** | validated when each observation reaches this stage |
| `purged_rolling_20m_labels` | Any-time 20-minute forward labels | Audited one-minute archive | — | **CONTRACT** | validated when each observation reaches this stage |
