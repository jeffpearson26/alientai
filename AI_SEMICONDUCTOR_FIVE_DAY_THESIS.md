# AI Semiconductor Five-Day Research Thesis

Status: implemented research model / `RESEARCH_HOLD`
Execution enabled: `false`

This Markdown file is the qualitative contract, not an executable model file.
Its existing executable implementation is:

- `alientai_v2/research/catalyst_momentum_5d.py`
- `train_ai_semiconductor_catalyst_momentum_5d.py`
- `test_ai_semiconductor_catalyst_momentum_5d.py`
- `data_v2/rcef_research/ai_semiconductor_catalyst_momentum_5d_20260804`

The implementation was reverified on 2026-08-06 with all eight targeted tests
passing. It is operational research code, but it is not an approved or active
stock picker because its already-observed test did not establish reliable
selection skill.

## Durable industry context

- Merchant AI accelerator leaders retain software, scale, networking, and
  deployment advantages, but custom silicon can pressure their market share.
- Memory, advanced packaging, and foundry suppliers may have clearer
  bottleneck-driven scarcity and pricing power.
- Custom ASIC, networking, and interconnect enablers can benefit as
  hyperscalers diversify away from a single accelerator architecture.
- Emerging inference specialists—including wafer-scale, in-memory, and
  transformer-specific designs—may offer greater upside and greater failure,
  liquidity, customer-concentration, and production-scale risk.
- Capacity, bookings, pricing, customer commitments, and competitive
  positioning must be timestamped and refreshed because the landscape changes
  rapidly.

The durable context emphasizes:

1. visible AI demand;
2. scarcity and pricing power;
3. reasonable point-in-time valuation;
4. diversification across the AI infrastructure stack;
5. position sizing and catastrophic-loss avoidance.

These ideas are hypotheses and secondary context. They are never labels,
assumed outcomes, or manually assigned ticker bonuses.

## Five-session adaptation

A five-session horizon is driven primarily by catalysts, momentum, sentiment,
positioning, technical structure, and sector flows. Long-term quality and
valuation are supporting overlays rather than primary entry signals.

Priority order:

1. A public, timestamped catalyst plausibly relevant within five sessions:
   earnings/guidance, analyst action, capacity/HBM/packaging development,
   design win, product/partnership announcement, hyperscaler commentary, or
   broad semiconductor flow reversal.
2. A confirmed technical setup: oversold bounce, volume-backed breakout,
   continuation, or relative strength against semiconductor and market
   benchmarks.
3. Positioning and sentiment: unusual call buying, target-specific news,
   analyst-direction changes, short/squeeze context, and broader risk appetite.
4. A light business-context overlay: visible demand, scarcity, pricing power,
   recent execution, and credible production scale.
5. Strict risk controls: liquidity, volatility and parabolic-entry filters,
   correlated-position limits, smaller risk for emerging specialists, explicit
   entry/exit prices, costs, and a forced decision no later than session five.

## AI-stack roles

Every security should be compared with appropriate peers and tagged using a
point-in-time taxonomy:

- merchant GPU/accelerator;
- memory/HBM;
- foundry and advanced packaging;
- semiconductor equipment;
- custom ASIC, networking, and interconnect;
- semiconductor design software;
- AI infrastructure systems;
- emerging inference specialist.

Stack roles may guide diversification and risk sizing. They must not become a
hidden ticker identity feature.

## Evidence requirements

- Every input must have an `available_at` time no later than the decision
  cutoff.
- Upcoming event calendars must use the schedule visible at that cutoff.
- Guidance, capacity, bookings, pricing, and valuation require historical
  vintages rather than today's reconstructed values.
- Analyst labels must preserve the original firm wording as well as a separately
  documented normalization.
- Options features mean unusual call buying/positioning—not put activity or
  undirected total volume.
- Hard stops and time exits require complete price paths at the required
  frequency; endpoint returns cannot simulate them honestly.
- Training, validation, and test periods must be chronological and label-purged.
- Selection breadth, thresholds, sizing, and exits must be fixed on validation
  before the final test is opened.
- A historical result must pass a separately frozen future journal before any
  paper-trading consideration.

## Current implementation boundary

`train_ai_semiconductor_catalyst_momentum_5d.py` implements the currently
available technical, news, earnings-reaction, analyst-proxy, unusual-call,
insider, and risk components. Its first 1,694-row experiment is
`RESEARCH_HOLD`; it must not be tuned against its observed test.

The full available-data variant produced +0.227821% mean net return across 20
test trades, but -3.578902% median, 25% wins, and a -14.897556% worst trade.
The positive mean was driven by a few outliers and did not pass an honest
promotion standard. Do not create a duplicate fit on the same exposed
chronology or activate a prospective picker from this result.

The next legitimate implementation should wait for the long adjusted technical
archive and add independently timestamped structured catalyst, capacity,
booking, analyst, valuation, and stack-role histories. Emerging names such as
CBRS must retain explicit pre-listing missingness and a distinct higher-risk
classification until revenue, liquidity, and production scale are established.
