# AI/Semiconductor Multi-Horizon Catalyst Model — Partial V1

Status: `RESEARCH_PROMISING_PARTIAL_INPUTS`

This isolated research build implements the saved
`FUTURE_AI_SEMICONDUCTOR_MULTI_HORIZON_MODEL.md` contract for the point-in-time
feature families currently supported by complete historical coverage. It does
not modify an active frozen model, `engine.py`, settings, paper trading, or live
trading.

## Contract

- Universe: 17 AI/semiconductor and infrastructure symbols.
- Decision timestamp: after the completed regular-session close.
- Entry: next regular-session open.
- Exits: first, fifth, and twentieth subsequent session closes.
- Cost: 0.25% round trip in every label.
- Large-move classification thresholds: 2%, 5%, and 10%, respectively.
- Split: chronological 60% train / 20% validation / 20% untouched test with
  label-end purging.
- Basket fraction: selected from 10%, 20%, 30%, and 50% using validation only.
- Test opened once after the fraction was locked.

The panel contains 1,694 rows, 17 symbols, and 125 decision dates from
2026-01-02 through 2026-07-02. Coverage is 1,694 rows for 1 and 5 sessions and
1,684 rows for 20 sessions.

## Implemented feature-family ablations

1. Technical, momentum, volatility, and relative context.
2. Plus premarket state through 09:25 ET.
3. Plus prior public unusual **call** activity.
4. Plus the conservative target-specific Alpha Vantage analyst-headline proxy.
5. Plus FINRA short-interest fields when nonconstant and available.

Full feature participation was used during training. This is important:
feature subsampling would cause the baseline model to change merely because a
new family added columns, confounding the nested ablation.

## Validation-locked untouched results

| Horizon | Best available variant | Basket | Test N | Mean net | Median net | Positive | Large move | 5th percentile | All-universe mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 session | Technical + premarket | 10% | 37 | +0.6652% | +0.4831% | 59.46% | 27.03% ≥2% | -5.5270% | -0.6362% |
| 5 sessions | Technical + premarket | 10% | 31 | +1.7260% | -0.0638% | 48.39% | 25.81% ≥5% | -4.6939% | -2.0387% |
| 20 sessions | Technical + premarket + calls | 50% | 37 | -2.3077% | -1.3152% | 40.54% | 8.11% ≥10% | -18.7673% | -9.7296% |

### Interpretation

- The one-session technical+premarket ranking is the cleanest preliminary
  result: positive mean and median, 59.46% net wins, and substantial
  improvement over the same-period universe. Its 37 observations and adverse
  tail are not enough for promotion.
- The five-session variant improved materially over the sharply negative
  same-period universe, but its median remained slightly negative and fewer
  than half of selections won. Large winners drive the positive mean.
- Adding unusual calls did not improve the one- or five-session result in this
  experiment. It reduced the loss at 20 sessions, but every 20-session variant
  remained negative.
- The analyst proxy and short-interest stage produced identical outcomes to
  the preceding stage. They added no demonstrated incremental value here.
- The 20-session test begins 2026-06-25 and contains very few independent
  decision dates. It is a rejection for this build, not a general conclusion
  about long-horizon catalyst modeling.

## Feature families still missing

The saved full model also requires historically point-in-time:

- fundamentals, earnings surprise, estimate revisions, and guidance changes;
- a structured catalyst calendar;
- licensed event-level analyst rating history;
- general news sentiment, novelty, and topic;
- semiconductor supply/demand, memory/HBM, packaging, foundry, and
  hyperscaler-capex vintages;
- comparable point-in-time valuation.

Those families were not fabricated or joined sparsely. They remain explicit
future ablations.

## Decision

Preserve the one- and five-session technical+premarket variants as research
candidates. Do not retune them on the now-observed test. The defensible next
step is to freeze their exact artifacts and compare them prospectively on
future dates while separately building the missing timestamped feature
archives. No result authorizes an order.
