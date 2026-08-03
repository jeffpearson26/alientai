# AlienTAI Prospective Pick Competition

This is a research-only comparison among Jeff, Codex, Claude, and frozen
AlienTAI models. It cannot create paper or live orders.

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

Jeff has elected a stricter standing-entry rule for himself. His August 3
selection of `MU`, `AVGO`, `AMD`, `MRVL`, and `NVDA` is frozen for the entire
competition. He will not make additional daily selections and the basket cannot
be revised using later information. The standing instruction is preserved in
`pick_competition_standing_entries.json`. Evaluation must identify it as one
precommitted standing basket rather than implying that Jeff reconsidered the
stocks each morning.

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

`evaluate_pick_competition_intraday.py` is the append-only scorer for the
unmanaged 20/60-minute tracks. It requires an Alpha Vantage current-mode,
realtime-entitled manifest completed after the relevant exit candle, exact
09:30 bar opens, and exact completed 09:45/10:25 bar closes. It fingerprints
the source manifest, deduplicates by round/participant/date/symbol/horizon, and
computes equal-weight participant baskets. It deliberately leaves every
stop-managed result pending until a separately validated high-resolution stop
path exists; it never infers a stop from the candle's later low or close.

## Claude information boundary

Claude receives a generated, uploadable packet containing the complete
101-symbol prior-session technical panel. The packet deliberately excludes
AlienTAI model predictions, scores, ranks, probabilities, labels, other
participants' selections, and future outcomes. Claude must use only the packet,
may select zero through five tickers, and must return its ranked picks before
the same 09:25 Eastern deadline. Its response is then recorded immutably through
the normal competition journal.

`build_claude_competition_packet.py` fails closed on incomplete or duplicate
universe coverage and on technical data dated on or after the decision date.
Optional premarket or call-feature families may be included only when they have
complete exact-universe coverage and satisfy their frozen timing checks. The
August 3 packet intentionally contains no premarket data at Jeff's direction.
