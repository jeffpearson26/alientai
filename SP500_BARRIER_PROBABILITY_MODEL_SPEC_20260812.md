# S&P 500 Barrier-Probability Clone

Model ID: `barrier_probability_sp500_496_h10_alpha_vantage_v1_20260812`

Status: `PREDECLARED_RESEARCH_BUILD`

This is a new source-pure Alpha Vantage clone of the frozen 48-stock
barrier-probability model. It does not inherit that model's probabilities,
calibration evidence, weights, or prospective observations.

## Frozen universe and source

- Universe: the 496 unique symbols in `sp500_expanded_symbols.txt`.
- Universe SHA-256: `7cb50d31ad5ecb0123b811b9c88e161beee84d3b185742799353fb774720d1c8`.
- Provider: Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`, `outputsize=full`.
- Fixed contemporary membership creates survivorship and selection bias.
- Every symbol must have one independently audited, source-pure adjusted file.
  No Schwab rows, partial universe, or provider splicing is permitted.
- Three same-listing Alpha Vantage aliases are frozen before panel creation:
  `BF.B -> BF-B` plus corporate ticker transitions `BK -> BNY` and
  `MMC -> MRSH`. The model
  retains the universe identities `BF.B` and `MMC`; the raw payload identities
  must match the named aliases and pass the independent content audit.
- Nine inactive historical constituents have explicit audited terminal dates:
  `CTRA`, `DAY`, `DFS`, `EA`, `HES`, `HOLX`, `IPG`, `JNPR`, and `K`.
  Their histories end on the last provider row and they are unavailable for
  later decisions; no value is carried forward and no replacement is spliced.
- A whole-universe common-date intersection is not required because historical
  constituents and later listings do not share one date. Every individual file
  and every stage row remains date-exact; missing symbols simply abstain.
- A source window that cannot produce every frozen feature is recorded as
  `feature_unavailable` and excluded. It is never imputed or assigned a
  synthetic indicator value.

## Frozen question and features

From the next regular-session adjusted open, estimate conservative and
optimistic probability bounds for touching +1.5% before -0.5% within ten
sessions. Same-session double touches remain daily-path ambiguity. Use the
same 60-session, 19-feature daily technical contract as the 48-stock model,
with same-row adjusted OHLC and raw volume.

## Frozen chronology and gate

Use whole decision dates with independent train, fit-validation, calibration,
policy-validation, and sealed-test stages plus a ten-session two-sided
development embargo. Preserve the existing validation gates without lowering
or searching them. The sealed test may open once only if every gate passes;
otherwise it remains `SEALED_UNLOADED`.

The model is research-only. Every output is `execution_decision: AVOID` and no
paper or live order path is authorized. Historical passage would permit only a
new append-only future calibration journal, never a profitability claim.
