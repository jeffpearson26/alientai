# External Barrier Probability Bundle Audit

## Safe handling

- Supplied ZIP:
  `D:\Downloads\barrier_prob_model.zip`
- ZIP SHA-256:
  `acfce81f6e6faa4b79dbcbb6f6a9fd0b2277cd57b21a01ee977636a559f55bba`
- Safe isolated extraction:
  `D:\AlientAI\ExternalModels\barrier_prob_model_20260807_acfce81f`
- Entries: 13
- Aggregate compressed entry bytes: 2,176,396
- Aggregate uncompressed entry bytes: 5,279,941
- Immutable ZIP bytes: 2,179,070
- Bundled joblib SHA-256:
  `b53b0f4f9cebb007684e8cc197c4c1562b67823d940a5bd336f2a8102b625c9a`
- Bundled joblib status: **QUARANTINED; NEVER LOADED**

The ZIP passed rooted-path, traversal, symlink, entry-size, and compression
ratio checks before extraction. Source and text reports were inspected without
importing the package or deserializing the saved model.

## Supplied result

The bundle reports a roughly 50-name daily LightGBM classifier for reaching
+1.5% before -0.5% within ten sessions. Its exposed test report states:

- AUC: `0.530244`
- ML Brier: `0.224036`
- reported GBM Brier: `0.236825`
- test positive rate: `33.9873%`

These values are development claims only. They are not inherited by the
corrected AlienTAI model.

## Defects requiring a clean-room rebuild

1. `CalibratedClassifierCV(cv=3)` splits pooled rows rather than whole market
   dates. Calibration therefore mixes later and earlier time periods and
   overlapping symbol/date labels.
2. The chronological train/test boundary has no ten-session purge or embargo.
   Labels immediately before the boundary can consume prices from the test
   period.
3. Unresolved rows near the end of the source are silently counted as timeout
   failures even when fewer than ten future sessions exist. The last nine
   usable rows per symbol can therefore receive truncated false-negative
   labels.
4. The model consumes the completed decision close and simultaneously treats
   that same close as the entry reference. That fill is not executable after
   the completed close is known.
5. Same-session double touches are dropped. That changes the estimand to a
   conditional probability on non-ambiguous paths and can create selection
   bias because ambiguity is volatility-dependent.
6. The CCI implementation uses rolling standard deviation rather than the
   standard mean absolute deviation definition.
7. MACD is left in absolute price units inside a pooled multi-stock model,
   creating an avoidable price-scale feature.
8. The stated Brownian first-passage formula has the wrong drift/sign
   arrangement for the documented boundaries. It also describes eventual
   passage, not passage within the model's finite ten-session timeout, so its
   Brier comparison is not like-for-like.
9. Data are downloaded live from yfinance without a source manifest, immutable
   raw hashes, content audit, adjustment audit, or point-in-time universe
   record.
10. There is no independent sealed test, clustered uncertainty estimate,
    calibration-support diagnostic, source consistency gate, or future-only
    journal.

## Disposition

The outline is a useful hypothesis, but the bundled model and its joblib are
not approved for reuse. The corrected, independently audited implementation is
documented in `BARRIER_PROBABILITY_MODEL_SPEC_20260807.md` and
`BARRIER_PROBABILITY_MODEL_REPORT_20260807.md`.
