# Technical-only cross-sectional rankers

Date: 2026-08-06

Status: research only; no paper/live execution

## Outcome

The pure daily-technical variants are implemented, independently audited, and
historically screened for both universes and both horizons. They contain no
options, call activity, implied volatility, news, events, fundamentals,
one-minute/five-minute data, intraday features, premarket data, or after-hours
data.

QQQ and SPY are technical reference/context series only. They cannot be
selected.

None of the four model variants is eligible for promotion:

- Nasdaq 5 sessions failed development validation; its test remains sealed.
- S&P 5 and 20 sessions failed development validation; their tests remain
  sealed.
- Nasdaq 20 sessions passed the frozen development gate, which authorized one
  opening of its sealed test. Both LightGBM and XGBoost then reversed sharply
  and lost money on the untouched latest period. This is a failed sealed
  confirmation and remains `RESEARCH_HOLD`.

No retuning, alternate threshold, or second test attempt is permitted against
the opened Nasdaq 20-session period.

## Panels and audits

| Universe | Rows | Dates | Candidates each date | Excluded columns | Audit |
|---|---:|---:|---:|---:|---|
| Nasdaq-100 | 21,008 | 208 | exactly 101 | 0 | PASS |
| S&P data-ready | 190,302 | 394 | exactly 483 | 0 | PASS |

Panel SHA-256 values:

- Nasdaq:
  `4d53c82a80f077337a57ffefe9e649e2ad993bd08f29751250a6b51bb11461cc`
- S&P:
  `881945696f3ea78135f92a8ab98fb9be4e0d5bb9961d7eec14ffe9f6f21eb2d3`

The fixed contemporary universes create survivorship and selection bias. Full
candidate coverage was nevertheless required on every retained date so the
cross-section never changes silently.

## Development results

Results are purged out-of-fold development estimates after the frozen 0.25%
round-trip cost.

| Universe / horizon / algorithm | Signals / dates | Mean | Median | Wins | Rank IC | Top-minus-bottom | Lower 95% bound | Development gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Nasdaq / 5 / LightGBM | 1,881 / 171 | +0.9598% | +0.4345% | 53.00% | -0.00158 | -0.0860% | +0.2820% | FAIL |
| Nasdaq / 5 / XGBoost | 1,026 / 171 | +1.0998% | +0.8543% | 55.36% | +0.00794 | +0.1414% | +0.2694% | FAIL |
| Nasdaq / 20 / LightGBM | 936 / 156 | +9.4160% | +5.5305% | 61.54% | +0.08759 | +6.4590% | +7.4464% | PASS |
| Nasdaq / 20 / XGBoost | 936 / 156 | +8.5083% | +5.3193% | 60.36% | +0.08191 | +5.6869% | +6.5161% | PASS |
| S&P / 5 / LightGBM | 4,935 / 329 | -0.1423% | -0.0810% | 49.04% | -0.01811 | -0.3675% | -0.5013% | FAIL |
| S&P / 5 / XGBoost | 4,935 / 329 | -0.1170% | -0.0989% | 48.86% | -0.02040 | -0.2248% | -0.4536% | FAIL |
| S&P / 20 / LightGBM | 4,710 / 314 | -0.3425% | -0.1008% | 49.34% | -0.05389 | -1.6584% | -1.0122% | FAIL |
| S&P / 20 / XGBoost | 4,710 / 314 | -0.4884% | -0.2430% | 48.81% | -0.05329 | -1.7066% | -1.1418% | FAIL |

The Nasdaq five-session XGBoost model missed the frozen minimum mean rank IC
of 0.01 despite positive selected-basket statistics. Its sealed test remains
unopened.

## Nasdaq 20-session sealed test

The untouched period was May 20 through July 7, 2026. It was opened once only
after both algorithms independently passed every development requirement.

| Algorithm | Signals / dates | Mean | Median | Wins | Rank IC | Top-minus-bottom | Lower 95% bound |
|---|---:|---:|---:|---:|---:|---:|---:|
| LightGBM | 192 / 32 | -4.4546% | -7.1613% | 36.98% | -0.11796 | -2.4026% | -10.7803% |
| XGBoost | 192 / 32 | -3.9485% | -5.2211% | 39.06% | -0.11513 | -2.4072% | -9.9175% |

Every central statistic reversed sign. The development result was
regime-specific or otherwise unstable; the test supplies strong evidence
against treating it as a robust stock-picking model.

## Artifacts

- Contract: `TECHNICAL_ONLY_CROSS_SECTIONAL_SPEC_20260806.md`
- Compiler: `build_technical_only_cross_sectional_panel.py`
- Independent audit: `audit_technical_only_cross_sectional_panel.py`
- Trainer: `train_technical_only_cross_sectional.py`
- Tests: `test_technical_only_cross_sectional.py`
- Panels:
  `D:\AlientAI\Data\Compiled\technical_only_cross_sectional_20260806`
- Reports: `D:\AlientAI\Models\technical_only_*_20260806`

Training-report SHA-256 values:

- Nasdaq 5:
  `1a1640ade5a84890dae2038cb9b4f9dde9e733540a420dc9aad7ddaa25da0f2d`
- Nasdaq 20:
  `a2ca177eb2153daaf6e6531953fe4c5007ce6d7b6bcc0928f7411f8744a7088f`
- S&P 5:
  `0d2af9b5bf2424aacfa7a6bf1441f9a19dff82e797140fdf644a0112079be0e6`
- S&P 20:
  `1cbf74c98ffc268cf95fb5325b1965aa478ba3dc87408c301150906a36c036d9`
