# Nasdaq + AI/Semiconductor Cross-Sectional Technical Model

Status: `RESEARCH_HOLD`
Execution enabled: `false`
Sealed test: `UNOPENED`

## Purpose

This isolated model implements Jeff's supplied five-trading-day technical
thesis: short momentum, oscillators, volatility regime, volume confirmation,
trend context, and same-day cross-sectional ranks. It does not modify any
frozen model, prospective journal, `engine.py`, paper setting, or live-trading
path.

## Universe and data

- Candidate universe: the fixed 101-security Nasdaq file union the fixed
  17-name AI/semiconductor screen, producing 104 unique candidates.
- AI additions outside the Nasdaq file: ANET, ORCL, and SMCI.
- QQQ and SPY: context only, never candidates.
- Source: Alpha Vantage full split/dividend-adjusted daily OHLCV.
- The three additions were collected separately as full adjusted history
  after an audit rejected the earlier unadjusted compact files.
- Panel: 162,609 unique symbol/date rows across 1,650 decision dates.
- Historical decision span: January 3, 2020 through July 29, 2026.
- Per-date coverage: 92 to 104 candidates.
- Eligible rows after fixed liquidity/price/ATR/ADX/gap filters: 133,062.
- Full content audit: `PASS`, zero errors.
- Panel SHA-256:
  `27b0a6a30d04a3a728f2013a54ed0c2b9b99c7f98a9437e8d71911825656f133`.

The fixed current-membership universe creates survivorship and selection bias.
Historical passage could not by itself authorize promotion.

## Timing and cost

- Features use only adjusted OHLCV available at the completed decision close.
- Entry: next regular-session adjusted open.
- Exit: fifth subsequent regular-session adjusted close.
- Round-trip cost: 0.25%, deducted from every label.
- Each row stores the exact five-session mark-to-market path.

## Features

- Momentum: 1-, 5-, and 10-session returns and ROC(10).
- Oscillators: RSI(14), stochastic K/D, and CCI(20).
- Volatility: ATR%, Bollinger %B/width, and annualized 10/20-session realized
  volatility.
- Volume: relative volume, five-session volume ROC, directional up/down volume
  ratio, and average dollar volume.
- Trend/range: EMA(10/20) distance, MACD histogram, ADX(14), five-session
  high/low proximity, and overnight gap.
- Context: contemporaneous QQQ/SPY momentum, trend, volatility, and ADX.
- Every stock feature is percentile-ranked within that date's candidate
  cross-section.

The supplied transparent formula is preserved exactly. ROC(10) and the
10-session return are algebraically identical, however, so its nominal
15%+15% weights are one combined 30% ten-session momentum weight rather than
two independent signals.

## Models and validation

Two candidates were predeclared:

1. the supplied transparent weighted rank composite; and
2. a LightGBM regressor trained to predict the within-date rank of the future
   five-session net return.

Whole decision dates were divided into train, fit-validation, calibration,
policy-validation, and sealed-test stages. Each pre-test boundary has a
two-sided five-session embargo. Calibration alone selected the model and
top-15%/top-20% policy. Maximum daily positions were fixed at 15.

| Stage | Dates |
|---|---:|
| Train | 820 |
| Fit validation | 237 |
| Calibration | 205 |
| Policy validation | 188 |
| Sealed test | 160 |
| Embargo | 40 |

Calibration selected LightGBM, top 20%. The learner stopped at iteration 4.
Its calibration basket contained 1,888 trades across 130 active dates:
+0.6883% mean net, +0.3918% median, 54.98% wins, and +0.0258 mean rank IC.
The saved model SHA-256 is
`bffb01c4609a46ee5d90bc0ea1cbe02b2899a9143424213ebaf3dc8df88e0ce8`.

## Independent policy-validation result

| Metric | Result |
|---|---:|
| Selections | 1,719 |
| Active decision dates | 119 |
| Mean net return | -0.0252% |
| Median net return | -0.1887% |
| Positive-return rate | 48.17% |
| Fifth percentile | -10.2647% |
| Worst trade | -30.1140% |
| Mean rank IC | -0.0590 |
| Top-minus-bottom mean | -1.1345% |
| Capital-scaled max drawdown | -12.8692% |
| Capital-scaled annualized Sharpe | -0.0462 |

The bottom-ranked control actually did better: +1.1093% mean, +0.5990%
median, and 54.39% wins. This is a regime reversal, not evidence that the
model should simply be inverted; inversion would be a new hypothesis selected
after seeing policy validation and would require a new chronology.

The policy failed positive mean, positive median, 50% winners, positive rank
IC, and top-over-bottom gates. Drawdown alone passed.

## Decision

Keep this exact run as `RESEARCH_HOLD`. Do not open its December 8, 2025
through July 29, 2026 sealed test, retune weights, invert it, create a
prospective journal, or connect it to paper/live execution.

This result is still useful: it rejects the claim that the supplied
cross-sectional technical combination is automatically a robust five-session
winner selector in this fixed universe. A future successor would need a
pre-registered regime interaction or genuinely point-in-time catalyst family,
trained and validated on a new chronology without using this policy period to
choose the change.
