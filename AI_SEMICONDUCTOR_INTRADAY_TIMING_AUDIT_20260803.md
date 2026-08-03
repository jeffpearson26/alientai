# AI/Semiconductor Intraday Timing Audit — 2026-08-03

## Decision

The six frozen 20/60-minute models remain research artifacts, but their
09:25-feature / 09:30-open prospective entry contract is not point-in-time
executable with completed Alpha Vantage five-minute candles. The prospective
journal must fail closed rather than record a selection from a partial candle
or retrospectively use the 09:30 opening price.

No model was retrained, retuned, promoted, or connected to execution.

## Evidence

- Alpha Vantage documents five-minute `TIME_SERIES_INTRADAY` data and requires
  `entitlement=realtime` for realtime freshness:
  <https://www.alphavantage.co/documentation/#intraday>.
- The project’s historical collector omitted an entitlement and specified a
  month, so a request completed at 09:31 ET on 2026-07-31 contained candles
  only through 2026-07-30. A later refresh contained 2026-07-31.
- The refreshed raw AMD file contains:
  - `04:00` with real extended-hours activity;
  - `09:25` with premarket activity;
  - `09:30` with the large regular-session opening candle.
- The frozen label contract explicitly says `09:30 ET bar open to 09:45 ET bar
  close (20 elapsed minutes)` and records the 09:45 candle’s completion as
  `09:50`. This proves that the source timestamps denote interval starts.

Therefore the `09:25` candle spans 09:25–09:30 and is not complete until the
same instant as the frozen `09:30` entry. At 09:26 it is partial; at or after
09:30 the opening reference is no longer a genuinely future entry.

## Safeguards added

- The current-session collector now has an explicit, separate
  `--entitlement realtime --current-date YYYY-MM-DD` mode.
- Its resumable manifest freezes:
  - current date;
  - entitlement;
  - five-minute interval;
  - `interval_start` timestamp convention.
- The feature compiler preserves that manifest provenance in every row.
- The prospective journal rejects:
  - historical/default snapshots;
  - non-realtime snapshots;
  - partial 09:25 candles;
  - completed 09:25 candles that were not observable before the frozen 09:30
    entry.

## Future repair (separate authorization and retraining)

A later experiment may preserve genuine point-in-time execution by choosing one
of these predeclared contracts:

1. use completed candles only through 09:20 and retain a 09:30 entry; or
2. use the completed 09:25 candle and move entry to the next observable price
   after 09:30.

Either option changes the frozen feature/entry contract and therefore requires
a separately named model, chronological retraining, held-out evaluation, and a
new prospective manifest. It must not be silently substituted into the current
program.
