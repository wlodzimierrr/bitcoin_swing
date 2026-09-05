# BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1

Pre-sealed threshold calibration for the six BTC_REFERENCE_COMPOSITE_V3 structural approval gates. No candidate is evaluated, no canonical reference is promoted, no frozen artifact is changed, and the sealed 2015-2019 validation sample is neither collected nor opened.

- Parent protocol: `BTC_REFERENCE_COMPOSITE_V2`
- Parent definition hash: `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`
- Proposed successor: `BTC_REFERENCE_COMPOSITE_V3` (`1ac5438a2eaf742c72bde285ba8289629d17986e1ec00fbee61d724b38417baa`)
- Phase-A governance: `BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_CALIBRATION_GOVERNANCE_V1`
- Phase-A governance hash: `503ec79517f34b030d1e8aa690e8a65a4b03050bdb0e2b020b28f9a85267e6e6`
- Comparison contract: `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2`
- Structural detector: `BTC_PREDICTOR_WEEKLY_LEVELS_V1`
- Final classification: **CALIBRATION_INSUFFICIENT**

## Phase A -- governance settled before any rate was computed

**Gate pair universe** (`CANDIDATE_VERSUS_INDEPENDENT_RAW_PROVIDER_PAIRS_V1`)

- `MEDIAN_OHLC_V2_vs_bitfinex`
- `MEDIAN_OHLC_V2_vs_bitstamp`
- `MEDIAN_OHLC_V2_vs_coinbase`

The gate pair universe is every unordered pair {candidate series, independent raw validation provider}, canonicalised by sorted series id on the pair's common canonical UTC Monday calendar. With the inherited provider set that is exactly three pairs, and the candidate is on one side of every one of them.

The V3 approval question is whether the candidate canonical reference agrees sufficiently with independent observable BTC market references. Only a pair with the candidate on one side is evidence about the candidate, so only those pairs are gates. Provider-versus-provider pairs answer a different and necessary question -- how much two legitimate independent references disagree with each other -- so they set the tolerance rather than the verdict. This split is also what keeps the calibration candidate-blind: the series used to choose the thresholds and the series the thresholds are applied to are disjoint.

Rejected pair universes:

- **the three independent raw-provider pairs, used as gates** -- The candidate is on neither side, so the gate would approve or reject the candidate on evidence about two other series. Two independent venues disagreeing with each other is source dispersion, not a property of the reference under evaluation. This is the universe every measurement so far was taken over, which is exactly why it is retained as calibration evidence and refused as a gate.
- **all ten unordered pairs among the frozen parent's five declared comparison series** -- Seven of the ten do not contain the candidate, so seven of the worst-pair inputs could fail the candidate for a disagreement it is not party to. It also admits MEDIAN_OHLC_V1, a research composite built from the same three providers, whose agreement with any of them is a property of the median formula rather than an independent market observation.
- **candidate-versus-provider pairs plus provider-versus-provider pairs, all treated as gates** -- Same defect as above in a smaller form: three of the six inputs to a worst-pair verdict would not contain the candidate. Source dispersion belongs in the calibration of the tolerance, not in the verdict.

**Calibration pair universe** (`INDEPENDENT_RAW_PROVIDER_PAIRS_V1`): `bitfinex_vs_bitstamp`, `bitfinex_vs_coinbase`, `bitstamp_vs_coinbase`. The calibration pair universe is every unordered pair of distinct independent raw validation providers, canonicalised the same way. With the inherited provider set that is exactly three pairs per sample, and the candidate is on neither side of any of them.

**Pair admissibility.** A pair is PAIR_INADMISSIBLE when its identity is wrong -- it is not in the declared universe, its two series do not carry the declared roles, or it was produced by a different comparison contract, structural detector or price-source policy -- or when its evidence is malformed or an excluded event was not individually recorded. A pair is PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE when its identity is sound but its evidence cannot support a rate: no shared weekly calendar, an empty candidate-event universe, an empty comparable-event universe, structural comparability below the declared floor, or fewer comparable events than the metric's declared minimum. A pair is PAIR_ADMISSIBLE otherwise. No pair is ever silently dropped: every pair in the universe is measured, classified and persisted with its reason codes.

**Calibration-pair admissibility.** A calibration measurement is admissible on identity, provenance, a non-zero comparable denominator and the same comparability floor. It is deliberately not subject to the minimum-comparable-event count: a calibration measurement contributes to a pooled estimate of the independent reference band, while a gate measurement has to stand alone as one pair's verdict. Applying the gate's own minimum to the evidence that derives it would be circular.

**Worst-pair aggregation.** One measurement per pair in the gate universe. The gate verdict is the verdict of the worst admissible defined pair, where 'worst' is read from the gate's own declared direction: for a maximum gate the worst pair is the one with the highest defined rate, for a minimum gate the lowest, and for an equality gate the one furthest from the threshold. Ties are broken by the lexicographically smallest comparison_id, so the reported pair identity is deterministic. An undefined or inadmissible required pair is never converted to a number and never treated as a pass: it makes the whole gate UNDEFINED_INSUFFICIENT_EVIDENCE, which cannot satisfy approval. No evidence is not zero disagreement.

**Threshold comparison.** maximum: rate <= threshold PASSES, rate > threshold FAILS; minimum: rate >= threshold PASSES; equal: rate == threshold PASSES. Equality is a pass in every direction, matching the repository's existing structural gate convention. Comparison is exact Decimal, never binary floating point.

**Zero-comparable-event semantics.** candidate_event_count == 0 makes the pair measurement UNDEFINED_NO_CANDIDATE_EVENTS. A zero comparable denominator -- because no candidate was detected, or because every detected candidate is NOT_COMPARABLE -- makes it UNDEFINED_NO_COMPARABLE_EVENTS. In both cases the rate is null, never 0.0, and it can neither pass nor fail a threshold. One undefined pair in the gate universe makes the whole gate UNDEFINED_INSUFFICIENT_EVIDENCE; so does every pair being undefined. NO EVIDENCE != ZERO DISAGREEMENT, in the metric and in the aggregation.

**Within-N-week matching.** Within a tolerance of N weekly sessions, opposing one-sided comparable swing disagreements are matched one-to-one, with the swing-high and swing-low families matched separately and never across each other. The matching is a maximum-cardinality bipartite matching on the tolerance graph, so no ordering of the inputs can produce fewer matched pairs than the graph admits. Among all maximum-cardinality matchings the one minimising total absolute calendar distance in weeks is taken; among those, the one whose sorted tuple of (left session, right session) pairs is lexicographically smallest. The result is therefore independent of provider order, dictionary order and input order. 'Nearest-admissible-pair first' is replaced because it is not maximum-cardinality at the two-week tolerance: left {W0, W4} against right {W2, W6} admits both a matched count of 2 and a matched count of 1 under orderings that all satisfy it, and the difference moves a hard gate.

**Comparability sufficiency.** A gate pair is sufficient evidence only when its structural comparability rate is at least 0.50, its comparable-event count reaches the metric's own minimum -- derived in Phase B from the selected threshold's operating characteristics, not chosen -- and every excluded event is individually recorded with its reason code, its side and its missing sessions. All 3 gate pairs must be sufficient. Insufficient evidence produces UNDEFINED_INSUFFICIENT_EVIDENCE and cannot approve; it never produces a pass. The comparability floor and the disagreement threshold are separate numbers with separate meanings.

**Sampling uncertainty.** Every observed rate is published with a two-sided 95% Wilson score interval, computed in an explicit Decimal context from the predeclared normal quantile. Wilson is used rather than the normal approximation because the denominators here are small and several numerators are zero, where the normal interval degenerates to a point and would turn no evidence into certainty. A zero observed rate therefore never justifies a strict threshold on its own: the interval's upper limit carries the denominator into every decision the objective makes.

**Calibration objective.** For each metric: estimate the independent reference band by pooling the admissible calibration measurements, take its two-sided 95% Wilson upper limit as the band's conservative level pi_bar, and set the detectable alternative at pi_alt = 3 x pi_bar. A threshold T on the predeclared grid is ADMISSIBLE when, for every calibration sample's own pair-denominator regime, the family-wise probability that a reference at pi_bar fails the worst-pair gate is at most 1/10 and the probability that a reference at pi_alt fails it is at least 4/5. The selected threshold is the SMALLEST admissible grid value, so the objective always pushes toward strictness and is bounded below by achievability rather than by any observed rate. Binomial probabilities are exact rational arithmetic over the pair denominators.

**Metric status.** INSUFFICIENT_EVIDENCE when there is no admissible calibration evidence, when the detectable alternative degenerates to certainty because the independent band itself is too wide, when the metric's own distinguishing mechanism is never exercised by the evidence, or when no grid value is both achievable and discriminating; CALIBRATION_UNSTABLE when a threshold is selected but an adjacent grid value changes the historical pair verdicts, so the number sits on a knife edge; CALIBRATED otherwise. Only a CALIBRATED metric may enter a frozen V3 approval protocol.

**Sample governance.** Calibration may read only the two already-inspected research samples, 2019-12-01..2022-12-31 and 2023-01-01..2025-12-31, each verified against its own collection manifest digests before use. They are development and calibration evidence, not validation evidence: both have already influenced earlier research decisions in this line, so no result measured on them is out-of-sample performance. The 2015-07-20..2019-11-30 sample stays sealed -- not collected, not opened, not inspected, not queried, not summarised -- and the inherited guard refuses any window that reaches into it.

Prohibited optimisation criteria:

- maximising the number of pairs, samples or gates that pass
- placing a threshold immediately above the maximum observed rate
- choosing a threshold because the candidate reference would survive it
- choosing a threshold because it reproduces a frozen V2 verdict
- using any measurement in which the candidate reference is one side
- using the sealed 2015-2019 sample in any form
- fitting a model of any kind, including any machine-learned model
- widening a threshold after seeing that a metric would not be calibrated

## Phase B -- calibration evidence and thresholds

Both samples are development and calibration evidence, not validation evidence. Neither is out-of-sample: both have already informed earlier decisions in this research line.

- `data/btc019/2023-01-01_2025-12-31`: 2023-01-01T00:00:00+00:00 .. 2025-12-31T23:00:00+00:00, evaluated at `2026-08-29T13:55:40.343607+00:00`
  - `bitfinex` `b10e9ace4098245bb0dd1343d0ca4808ac341b72d863520e949c31be0ba07fa0`
  - `bitstamp` `f8243a1ab5c5cdef4172127a6bc769804f4b8ce6d57e6be1e8141e59c5e07679`
  - `coinbase` `300b283f9bdeca0b9305fe02af5157845a7167561ae88c7c5c9c6e3faff36929`
- `data/btc_reference_composite_v1/external_2019-12-01_2022-12-31`: 2019-12-01T00:00:00+00:00 .. 2022-12-31T23:00:00+00:00, evaluated at `2026-08-29T14:55:55.351927+00:00`
  - `bitfinex` `7ed5c1cd67075211395ffcfb815c7ced978966e29a404f1bc11bb3781515cf92`
  - `bitstamp` `0af33e8e13d874e6bba187f9174c579feeb928d8c3a9fd7723866fed6cc657a0`
  - `coinbase` `5556cbb479ea2addbf879e4898e9986e6fb3fec7e8b9a0fdd82e4f3bc64bb27f`

### exact_timestamp_swing_disagreement_rate

- Frozen V2 threshold: `0.15` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, soft (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 3/28 | 0.107142 | [0.0371, 0.2719] | 28/35 | 0.8 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 1/26 | 0.038461 | [0.0068, 0.1889] | 26/34 | 0.7647 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 1/28 | 0.035714 | [0.0063, 0.1771] | 28/31 | 0.9032 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/23 | 0 | [0, 0.1431] | 23/32 | 0.7187 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/22 | 0 | [0, 0.1486] | 22/33 | 0.6666 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 2/29 | 0.068965 | [0.0191, 0.2196] | 29/32 | 0.9062 | PAIR_ADMISSIBLE |

- Pooled independent band: 7/156 = 0.044871, Wilson 95% [0.021903, 0.089716]
- Band level pi_bar = 0.089716, detectable alternative pi_alt = 0.269149

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.9773 / 0.9999; external_2019-12-01_2022-12-31: 0.9619 / 0.9999 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.8332 / 0.9999; external_2019-12-01_2022-12-31: 0.7696 / 0.9999 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.3536 / 0.9995; external_2019-12-01_2022-12-31: 0.3406 / 0.9991 |
| 0.20 | no | 2023-01-01_2025-12-31: 0.0921 / 0.9900; external_2019-12-01_2022-12-31: 0.1269 / 0.9907 |
| 0.25 | yes | 2023-01-01_2025-12-31: 0.0116 / 0.8903; external_2019-12-01_2022-12-31: 0.0277 / 0.9224 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.0025 / 0.7313; external_2019-12-01_2022-12-31: 0.0062 / 0.7773 |
| 0.40 | no | 2023-01-01_2025-12-31: 0.0000 / 0.1562; external_2019-12-01_2022-12-31: 0.0000 / 0.2216 |
| 0.50 | no | 2023-01-01_2025-12-31: 1.2125 / 0.0082; external_2019-12-01_2022-12-31: 2.2116 / 0.0181 |

- Proposed V3 threshold: `0.25`
- Minimum comparable events per gate pair: `13`
- Sensitivity neighbourhood: 0.20, 0.25, 0.30; neighbours moving historical verdicts: none
- Status: **CALIBRATED**

### within_1_week_swing_disagreement_rate

- Frozen V2 threshold: `0.05` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, hard (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- Matching: `MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1`
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 3/28 | 0.107142 | [0.0371, 0.2719] | 28/35 | 0.8 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 1/26 | 0.038461 | [0.0068, 0.1889] | 26/34 | 0.7647 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 1/28 | 0.035714 | [0.0063, 0.1771] | 28/31 | 0.9032 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/23 | 0 | [0, 0.1431] | 23/32 | 0.7187 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/22 | 0 | [0, 0.1486] | 22/33 | 0.6666 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 2/29 | 0.068965 | [0.0191, 0.2196] | 29/32 | 0.9062 | PAIR_ADMISSIBLE |

- Pooled independent band: 7/156 = 0.044871, Wilson 95% [0.021903, 0.089716]
- Band level pi_bar = 0.089716, detectable alternative pi_alt = 0.269149

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.9773 / 0.9999; external_2019-12-01_2022-12-31: 0.9619 / 0.9999 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.8332 / 0.9999; external_2019-12-01_2022-12-31: 0.7696 / 0.9999 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.3536 / 0.9995; external_2019-12-01_2022-12-31: 0.3406 / 0.9991 |
| 0.20 | no | 2023-01-01_2025-12-31: 0.0921 / 0.9900; external_2019-12-01_2022-12-31: 0.1269 / 0.9907 |
| 0.25 | yes | 2023-01-01_2025-12-31: 0.0116 / 0.8903; external_2019-12-01_2022-12-31: 0.0277 / 0.9224 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.0025 / 0.7313; external_2019-12-01_2022-12-31: 0.0062 / 0.7773 |
| 0.40 | no | 2023-01-01_2025-12-31: 0.0000 / 0.1562; external_2019-12-01_2022-12-31: 0.0000 / 0.2216 |
| 0.50 | no | 2023-01-01_2025-12-31: 1.2125 / 0.0082; external_2019-12-01_2022-12-31: 2.2116 / 0.0181 |

- Proposed V3 threshold: `0.25`
- Minimum comparable events per gate pair: `13`
- Sensitivity neighbourhood: 0.20, 0.25, 0.30; neighbours moving historical verdicts: none
- Status: **INSUFFICIENT_EVIDENCE**
- Reasons: METRIC_MECHANISM_NOT_EXERCISED_BY_THE_EVIDENCE

### within_2_week_swing_disagreement_rate

- Frozen V2 threshold: `0.02` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, hard (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- Matching: `MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1`
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 3/28 | 0.107142 | [0.0371, 0.2719] | 28/35 | 0.8 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 1/26 | 0.038461 | [0.0068, 0.1889] | 26/34 | 0.7647 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 1/28 | 0.035714 | [0.0063, 0.1771] | 28/31 | 0.9032 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/23 | 0 | [0, 0.1431] | 23/32 | 0.7187 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/22 | 0 | [0, 0.1486] | 22/33 | 0.6666 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 2/29 | 0.068965 | [0.0191, 0.2196] | 29/32 | 0.9062 | PAIR_ADMISSIBLE |

- Pooled independent band: 7/156 = 0.044871, Wilson 95% [0.021903, 0.089716]
- Band level pi_bar = 0.089716, detectable alternative pi_alt = 0.269149

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9995 / 0.9999; external_2019-12-01_2022-12-31: 0.9990 / 0.9999 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.9773 / 0.9999; external_2019-12-01_2022-12-31: 0.9619 / 0.9999 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.8332 / 0.9999; external_2019-12-01_2022-12-31: 0.7696 / 0.9999 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.3536 / 0.9995; external_2019-12-01_2022-12-31: 0.3406 / 0.9991 |
| 0.20 | no | 2023-01-01_2025-12-31: 0.0921 / 0.9900; external_2019-12-01_2022-12-31: 0.1269 / 0.9907 |
| 0.25 | yes | 2023-01-01_2025-12-31: 0.0116 / 0.8903; external_2019-12-01_2022-12-31: 0.0277 / 0.9224 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.0025 / 0.7313; external_2019-12-01_2022-12-31: 0.0062 / 0.7773 |
| 0.40 | no | 2023-01-01_2025-12-31: 0.0000 / 0.1562; external_2019-12-01_2022-12-31: 0.0000 / 0.2216 |
| 0.50 | no | 2023-01-01_2025-12-31: 1.2125 / 0.0082; external_2019-12-01_2022-12-31: 2.2116 / 0.0181 |

- Proposed V3 threshold: `0.25`
- Minimum comparable events per gate pair: `13`
- Sensitivity neighbourhood: 0.20, 0.25, 0.30; neighbours moving historical verdicts: none
- Status: **INSUFFICIENT_EVIDENCE**
- Reasons: METRIC_MECHANISM_NOT_EXERCISED_BY_THE_EVIDENCE

### structural_state_disagreement_rate

- Frozen V2 threshold: `0.05` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, hard (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 2/28 | 0.071428 | [0.0198, 0.2264] | 28/35 | 0.8 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 1/26 | 0.038461 | [0.0068, 0.1889] | 26/34 | 0.7647 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 1/28 | 0.035714 | [0.0063, 0.1771] | 28/31 | 0.9032 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/23 | 0 | [0, 0.1431] | 23/32 | 0.7187 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/22 | 0 | [0, 0.1486] | 22/33 | 0.6666 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 0/29 | 0 | [0, 0.1169] | 29/32 | 0.9062 | PAIR_ADMISSIBLE |

- Pooled independent band: 4/156 = 0.025641, Wilson 95% [0.010015, 0.064067]
- Band level pi_bar = 0.064067, detectable alternative pi_alt = 0.192201

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9956 / 0.9999; external_2019-12-01_2022-12-31: 0.9925 / 0.9999 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9956 / 0.9999; external_2019-12-01_2022-12-31: 0.9925 / 0.9999 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9956 / 0.9999; external_2019-12-01_2022-12-31: 0.9925 / 0.9999 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.8962 / 0.9999; external_2019-12-01_2022-12-31: 0.8565 / 0.9999 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.5852 / 0.9994; external_2019-12-01_2022-12-31: 0.5087 / 0.9982 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.1372 / 0.9707; external_2019-12-01_2022-12-31: 0.1338 / 0.9613 |
| 0.20 | yes | 2023-01-01_2025-12-31: 0.0203 / 0.8183; external_2019-12-01_2022-12-31: 0.0338 / 0.8418 |
| 0.25 | no | 2023-01-01_2025-12-31: 0.0015 / 0.4423; external_2019-12-01_2022-12-31: 0.0051 / 0.5437 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.0002 / 0.2355; external_2019-12-01_2022-12-31: 0.0008 / 0.3022 |
| 0.40 | no | 2023-01-01_2025-12-31: 3.4335 / 0.0127; external_2019-12-01_2022-12-31: 0.0000 / 0.0271 |
| 0.50 | no | 2023-01-01_2025-12-31: 1.3270 / 0.0001; external_2019-12-01_2022-12-31: 5.0348 / 0.0007 |

- Proposed V3 threshold: `0.20`
- Minimum comparable events per gate pair: `17`
- Sensitivity neighbourhood: 0.15, 0.20, 0.25; neighbours moving historical verdicts: none
- Status: **CALIBRATED**

### breakout_disagreement_rate

- Frozen V2 threshold: `0.05` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, hard (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/9 | 0 | [0, 0.2991] | 9/14 | 0.6428 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/9 | 0 | [0, 0.2991] | 9/13 | 0.6923 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 0/12 | 0 | [0, 0.2424] | 12/13 | 0.9230 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 0/5 | 0 | [0, 0.4344] | 5/12 | 0.4166 | PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE |
| bitfinex_vs_coinbase | 0/5 | 0 | [0, 0.4344] | 5/12 | 0.4166 | PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE |
| bitstamp_vs_coinbase | 0/9 | 0 | [0, 0.2991] | 9/11 | 0.8181 | PAIR_ADMISSIBLE |

- Pooled independent band: 0/39 = 0, Wilson 95% [0, 0.089666]
- Band level pi_bar = 0.089666, detectable alternative pi_alt = 0.269000

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9402 / 0.9999; external_2019-12-01_2022-12-31: 0.5706 / 0.9403 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9402 / 0.9999; external_2019-12-01_2022-12-31: 0.5706 / 0.9403 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9402 / 0.9999; external_2019-12-01_2022-12-31: 0.5706 / 0.9403 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.9402 / 0.9999; external_2019-12-01_2022-12-31: 0.5706 / 0.9403 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.8697 / 0.9995; external_2019-12-01_2022-12-31: 0.5706 / 0.9403 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.5363 / 0.9916; external_2019-12-01_2022-12-31: 0.1900 / 0.7430 |
| 0.20 | no | 2023-01-01_2025-12-31: 0.4003 / 0.9779; external_2019-12-01_2022-12-31: 0.1900 / 0.7430 |
| 0.25 | no | 2023-01-01_2025-12-31: 0.0949 / 0.8232; external_2019-12-01_2022-12-31: 0.0400 / 0.4524 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.0949 / 0.8232; external_2019-12-01_2022-12-31: 0.0400 / 0.4524 |
| 0.40 | no | 2023-01-01_2025-12-31: 0.0138 / 0.4913; external_2019-12-01_2022-12-31: 0.0056 / 0.2029 |
| 0.50 | no | 2023-01-01_2025-12-31: 0.0010 / 0.1449; external_2019-12-01_2022-12-31: 0.0005 / 0.0652 |

- Proposed V3 threshold: none
- Minimum comparable events per gate pair: `None`
- Sensitivity neighbourhood: none; neighbours moving historical verdicts: none
- Status: **INSUFFICIENT_EVIDENCE**
- Reasons: NO_ACHIEVABLE_AND_DISCRIMINATING_THRESHOLD_EXISTS

### reclaim_disagreement_rate

- Frozen V2 threshold: `0.05` (CARRIED_FORWARD_UNCALIBRATED)
- Direction `maximum`, hard (INHERITED_FROM_FROZEN_PARENT_UNCHANGED)
- NOT_COMPARABLE: EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR

**data/btc019/2023-01-01_2025-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 1/5 | 0.2 | [0.0362, 0.6244] | 5/9 | 0.5555 | PAIR_ADMISSIBLE |
| bitfinex_vs_coinbase | 0/5 | 0 | [0, 0.4344] | 5/10 | 0.5 | PAIR_ADMISSIBLE |
| bitstamp_vs_coinbase | 1/6 | 0.166666 | [0.0300, 0.5635] | 6/7 | 0.8571 | PAIR_ADMISSIBLE |

**data/btc_reference_composite_v1/external_2019-12-01_2022-12-31**

| pair | numerator/denominator | rate | Wilson 95% | comparable/detected | comparability | pair state |
| --- | --- | --- | --- | --- | --- | --- |
| bitfinex_vs_bitstamp | 1/2 | 0.5 | [0.0945, 0.9054] | 2/5 | 0.4 | PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE |
| bitfinex_vs_coinbase | 1/2 | 0.5 | [0.0945, 0.9054] | 2/5 | 0.4 | PAIR_UNDEFINED_INSUFFICIENT_EVIDENCE |
| bitstamp_vs_coinbase | 1/5 | 0.2 | [0.0362, 0.6244] | 5/5 | 1 | PAIR_ADMISSIBLE |

- Pooled independent band: 3/21 = 0.142857, Wilson 95% [0.049810, 0.346360]
- Band level pi_bar = 0.346360, detectable alternative pi_alt = 1

| threshold | admissible | per-sample false rejection / power |
| --- | --- | --- |
| 0.01 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.02 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.03 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.05 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.10 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.15 | no | 2023-01-01_2025-12-31: 0.9988 / 1; external_2019-12-01_2022-12-31: 0.8806 / 1 |
| 0.20 | no | 2023-01-01_2025-12-31: 0.9382 / 1; external_2019-12-01_2022-12-31: 0.5645 / 1 |
| 0.25 | no | 2023-01-01_2025-12-31: 0.9382 / 1; external_2019-12-01_2022-12-31: 0.5645 / 1 |
| 0.30 | no | 2023-01-01_2025-12-31: 0.9382 / 1; external_2019-12-01_2022-12-31: 0.5645 / 1 |
| 0.40 | no | 2023-01-01_2025-12-31: 0.6115 / 1; external_2019-12-01_2022-12-31: 0.2295 / 1 |
| 0.50 | no | 2023-01-01_2025-12-31: 0.4737 / 1; external_2019-12-01_2022-12-31: 0.2295 / 1 |

- Proposed V3 threshold: none
- Minimum comparable events per gate pair: `None`
- Sensitivity neighbourhood: none; neighbours moving historical verdicts: none
- Status: **INSUFFICIENT_EVIDENCE**
- Reasons: DEGENERATE_ALTERNATIVE_HYPOTHESIS, NO_ACHIEVABLE_AND_DISCRIMINATING_THRESHOLD_EXISTS

## Outcome

- Classification: **CALIBRATION_INSUFFICIENT**
- Calibrated: exact_timestamp_swing_disagreement_rate, structural_state_disagreement_rate
- Insufficient: breakout_disagreement_rate, reclaim_disagreement_rate, within_1_week_swing_disagreement_rate, within_2_week_swing_disagreement_rate
- Unstable: none
- Unresolved hard gates: breakout_disagreement_rate, reclaim_disagreement_rate, within_1_week_swing_disagreement_rate, within_2_week_swing_disagreement_rate
- BTC_REFERENCE_COMPOSITE_V3 status after this task: **PROPOSED_PENDING_THRESHOLD_CALIBRATION**
- Validator construction authorised: no
- Sealed sample collected: no
- Sealed sample opened: no

GOVERNANCE_UNRESOLVED when any Phase-A semantic is unresolved or the frozen governance hash does not bind Phase B; CALIBRATION_INSUFFICIENT when any of the six metrics is INSUFFICIENT_EVIDENCE; CALIBRATION_UNSTABLE when none is insufficient but at least one is CALIBRATION_UNSTABLE; NEW_RESEARCH_REQUIRED when a metric is REQUIRES_NEW_RESEARCH; V3_FROZEN_READY_FOR_VALIDATOR only when all six are CALIBRATED and every freeze condition holds. The successor is never frozen partially.
