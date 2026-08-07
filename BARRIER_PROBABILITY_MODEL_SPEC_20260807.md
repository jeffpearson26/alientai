# Frozen Barrier Probability Model Contract

Model ID:
`barrier_probability_48_h10_alpha_vantage_v1_20260807`

Status at freeze: research-only historical development. No order, paper, or
live-trading path is permitted.

## Question

After a completed regular-session close, what conservative probability range
does the model assign to the stock reaching **+1.5% before -0.5%**, measured
from the next regular-session open, within at most ten sessions?

This is a first-passage problem, not a ten-session endpoint-return forecast.
The next open is used because a model that consumes the completed close cannot
also assume an executable fill at that same close.

## Universe and source

The universe is the exact 48-symbol file
`research_universes/barrier_probability_48_20260807.txt`. It preserves every
supplied liquid name for which a full adjusted Alpha Vantage history was
already available. MS and NOW are excluded from this first contract because
the only local files for them are unadjusted compact rows; silently mixing
those with adjusted histories would make the features and barriers
inconsistent. They may enter a separately identified 50-name successor after
their full adjusted histories pass audit. All rows are source-pure Alpha
Vantage `TIME_SERIES_DAILY_ADJUSTED` observations. The source router in
`barrier_probability_model_config_20260807.json` chooses one complete file per
symbol and never fills a symbol row from another provider. Every selected
file, source manifest, and generated artifact is SHA-256 fingerprinted.

Adjusted OHLC is calculated only with that same row's
`adjusted close / close` factor. Volume remains the raw value visible on that
row. Future split coefficients are never applied to historical volume.

The current fixed universe creates survivorship and selection bias. Historical
passage cannot by itself authorize promotion.

## Inputs

Only completed daily candles through the decision close enter the model:

- 1-, 3-, 5-, and 10-session returns;
- RSI(14), stochastic %K(14), and standard mean-deviation CCI(20);
- ATR(14) percent, Bollinger %B and width;
- distance to EMA(10) and EMA(20), normalized MACD histogram, and ADX(14);
- relative volume versus the prior 20 sessions;
- adjusted intraday range and close location;
- 20-session realized volatility and the 5/20 volatility ratio.

The implementation uses a fixed 60-session feature window. It contains no
news, options, fundamentals, ticker favorites, future outcomes, or opaque
third-party scores.

## Labels and unresolved daily path order

The entry reference is the next adjusted regular-session open. Starting with
that entry session, the label scans at most ten adjusted daily high/low bars.

- upper only on the first touched day: definite success;
- lower only on the first touched day: definite failure;
- both on the first touched day: daily-path ambiguity;
- neither after ten complete sessions: timeout failure;
- neither with fewer than ten available sessions: incomplete and excluded.

Daily bars cannot truthfully order a same-session double touch. The model
therefore fits two calibrated heads:

1. a conservative lower bound that counts ambiguity as failure;
2. an optimistic upper bound that counts ambiguity as success.

Predictions are projected to `lower <= upper`. The lower bound is the only
conservative headline probability. The midpoint is diagnostic only. A later
five-minute or one-minute successor may narrow the interval, but must be a
separately frozen model with independently audited path data.

## Chronology and validation

Whole decision dates are divided once into:

- 50% train;
- 15% fit-validation;
- 10% calibration;
- 10% policy-validation;
- 15% sealed test.

Ten complete market dates are embargoed on both sides of every development
boundary. A row is retained only when all information used by its label ends
inside its assigned stage. LightGBM early stopping uses only fit-validation.
Isotonic calibration uses only calibration. The fixed research gate is
evaluated only on policy-validation.

The sealed-test file must remain unopened by the trainer unless every frozen
policy-validation condition passes:

- at least 5,000 rows across 60 dates;
- AUC at least 0.52 for both probability-bound heads;
- positive Brier skill versus calibration-frozen constant baselines;
- positive date-clustered 95% lower bound for conservative Brier improvement;
- conservative ten-bin ECE no worse than 0.05;
- conservative top-decile success lift of at least two percentage points;
- mean probability-interval width no wider than 0.30;
- pre-projection bound-crossing rate no higher than 5%.

There is no threshold search and no trade-return optimization. If the gate
fails, the test remains `SEALED_UNLOADED`. If it passes, it may be opened once
and reported without retuning.

## Costs and execution boundary

This model estimates path probabilities; it does not claim a trading return.
Any later decision policy must be separately frozen and must account for
spread, slippage, turnover, and the asymmetric +1.5%/-0.5% payoff. Every output
must remain `execution_decision: AVOID` until an independently approved
prospective program exists.

## External bundle boundary

The supplied ZIP SHA-256 is
`acfce81f6e6faa4b79dbcbb6f6a9fd0b2277cd57b21a01ee977636a559f55bba`.
Its bundled joblib is untrusted and was never loaded. Its reports are exposed
development evidence only and are not inherited by this model.
