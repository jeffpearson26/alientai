# AI/Semiconductor Narrative Data Audit — 2026-08-03

## Eligible now

### Event-time earnings

`data_v2/earnings_history/earnings_events.jsonl` preserves reported date,
estimated EPS, reported EPS, surprise, report timing, and a conservative
`available_at_utc`. All 1,694 rows in the 17-symbol/125-date catalyst panel have
at least one earnings event visible before their decision cutoff.

Implemented features:

- latest visible EPS surprise;
- days since the latest public report;
- consecutive EPS beat and miss streaks;
- visible earnings-history count.

No future report is included.

### Target-specific news

The completed Alpha Vantage AI/semiconductor event-news archive contains one
request payload for every panel symbol/date. All 1,694 rows contain at least
one target-specific article in the preceding five days.

Implemented features use only articles published before `as_of_utc`:

- 1/5/14-day article and distinct-source counts;
- target relevance-weighted sentiment;
- positive and negative article counts;
- mean target relevance;
- maximum earnings, technology, financial-markets, and manufacturing topic
  relevance;
- age of the latest target-specific article.

Articles are deduplicated by timestamp and URL/title. Other-ticker articles and
future publications are excluded.

## Not eligible for historical backfill

- The 2026-07-19 earnings-estimate, company-overview, and institutional files
  are current cross-sectional snapshots. They do not contain historical
  vintages and cannot be copied backward.
- Current Alpha Vantage financial-statement payloads contain historical fiscal
  periods but were collected in July 2026. Without original filing vintages,
  later revisions or restatements could leak backward.
- The downloaded 12-month earnings calendar is a current calendar, not a
  historical archive of what was scheduled on each decision date.
- No licensed structured event-level analyst-rating history is active. The
  conservative headline proxy remains the only eligible analyst approximation.
- Guidance midpoints, original consensus vintages, AI-segment disclosures,
  HBM pricing, foundry/packaging capacity, and hyperscaler-capex revisions lack
  complete timestamped historical tables.

## Paired historical ablations

All variants use the same 1,694 rows, separate 1/5/20-session labels, 0.25%
cost, chronological label-purged splits, and validation-selected basket
fractions.

| Horizon | Best prior variant | Added earnings | Added earnings + news | Conclusion |
|---|---:|---:|---:|---|
| 1 session | +0.6652%, 59.46% wins | **+0.7476%, 62.16% wins** | -0.0889% without calls; +0.7007% with calls | Earnings is a small exploratory improvement; news adds no improvement |
| 5 sessions | **+1.7260%, 48.39% wins** | +0.2198%, 38.71% wins | -0.0401% without calls; +0.2552% with calls | Keep the simpler technical+premarket candidate |
| 20 sessions | -2.3077% best prior | -8.4957% without calls | -6.1820% without calls; -1.0005% with calls | Every variant remains negative |

The historical test interval had already been opened before these extensions.
The one-day earnings improvement is therefore exploratory and requires a
future-only frozen comparison. It is not independent confirmation.

No new API calls were required. No engine, settings, paper-trading, or
live-trading behavior changed.

## Frozen future comparison

The one-session technical+premarket+earnings model is frozen as
`ai_semiconductor_narrative_1d_earnings_frozen_20260803`:

- immutable 17-symbol universe and artifact hashes;
- top 10% validation policy, capped at two selections;
- completed-session decision, next-session open entry, same-session close exit;
- 0.25% round-trip cost;
- append-only journal and outcome files;
- research only, with `execution_enabled=false`.

`journal_ai_semiconductor_narrative_model.py` fails closed on manifest/hash,
coverage, key, or timing changes. `evaluate_ai_semiconductor_narrative_outcomes.py`
uses exact Alpha Vantage next-open and same-session-close prices after the
outcome has matured. No August 3 observation was backfilled.
