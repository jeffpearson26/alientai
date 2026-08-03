# AlienTAI Prospective Pick Competition

This is a research-only comparison among Jeff, Codex, and frozen AlienTAI
models. It cannot create paper or live orders.

## Frozen first-round rules

- Universe: the 101 symbols in `nasdaq100_2026-06_symbols.txt`.
- Selection period: five U.S. market mornings.
- Daily submission: zero through five unique tickers per participant.
- Deadline: 09:25 Eastern on the decision date.
- Entry reference: the 09:30 Eastern regular-session opening price.
- Horizons: 20 minutes, 60 minutes, and 2, 5, 10, and 20 trading sessions.
- Cost: 0.25% round trip, applied consistently.
- Daily basket: equal weight across every submitted ticker.
- No forced selection: zero picks is an abstention, not a win or loss.
- No revision: one participant/date submission is immutable once journaled.

Each pick is evaluated on two separate tracks:

1. Unmanaged: hold through each fixed horizon.
2. Stop-managed: exit at the first observable price after a fixed -5% stop is
   crossed. An adverse opening gap uses the actual opening price, not the
   theoretical stop price. There is no re-entry.

The daily horizon winner has the highest average post-cost percentage return
across that participant's submitted basket. Overall results must also report
sample size, cumulative and mean return, median return, win rate, worst result,
and abstentions. A single lucky round is not evidence of a durable edge.

Outcome scoring accepts explicit timestamped price facts only. Missing horizons
remain pending, and a stop exit must come from a validated intraday price path;
it is never inferred from a later closing price.
