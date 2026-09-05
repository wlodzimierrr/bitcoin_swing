# BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1

An executable interpretation contract bound to the frozen
`BTC_REFERENCE_COMPOSITE_V3` definition hash. It is not a new
price-reference protocol: it authors no threshold, moves no frozen byte,
and resolves only what the frozen definition left to a validator.

## Binding

- Bound protocol: `BTC_REFERENCE_COMPOSITE_V3`
- Bound definition hash: `4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a`
- Parent hash (not bound to): `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`
- Freeze commit: `b60ecc7f36840b429f27a8742b7245d417cf52db`
- Review commit: `e2df3ce036c0e7045361c871f8d303b51533f18d` (PASS_WITH_NON_BLOCKING_FINDINGS)
- On mismatch: `REFUSE_TO_RUN`
- Validator definition hash: `b9a1d878c98fbda7f6ef93186262fb1d7e5825d93249fa1157c3f0856aa15194`

## Verdict precedence

```text
if any hard requirement is a material failure: FAIL; else if any hard requirement is missing, undefined, inadmissible, insufficient or incomplete: UNDEFINED_INSUFFICIENT_EVIDENCE; else: PASS.
```

## Composed hard requirements

- `structural_state_hard_gate` -- can fail: true
- `raw_provider_structural_dispersion_guard` -- can fail: true
- `structural_comparability_sufficiency` -- can fail: false
- `required_gate_pair_completeness` -- can fail: false
- `unrecorded_not_comparable_event_count` -- can fail: true
- `unreviewed_derived_level_disagreement_count` -- can fail: false
- `inherited_approval_hard_gates` -- can fail: true

## Certification rule

- Formula id: `WILSON_SCORE_UPPER_BOUND_UNCORRECTED_V1`
- Continuity correction: false
- Quantile: `1.959963984540054235631`
- Confidence level: 95%

| k | n | outcome |
| --- | --- | --- |
| 0 | 15 | PAIR_INSUFFICIENT_EVIDENCE |
| 0 | 16 | PAIR_CERTIFIED |
| 1 | 24 | PAIR_INSUFFICIENT_EVIDENCE |
| 1 | 25 | PAIR_CERTIFIED |
| 2 | 32 | PAIR_INSUFFICIENT_EVIDENCE |
| 2 | 33 | PAIR_CERTIFIED |
| 3 | 39 | PAIR_INSUFFICIENT_EVIDENCE |
| 3 | 40 | PAIR_CERTIFIED |

## Required pairs

Approval gate pairs:

- `MEDIAN_OHLC_V2_vs_bitfinex`
- `MEDIAN_OHLC_V2_vs_bitstamp`
- `MEDIAN_OHLC_V2_vs_coinbase`

Transfer-guard pairs:

- `bitfinex_vs_bitstamp`
- `bitfinex_vs_coinbase`
- `bitstamp_vs_coinbase`

## Sealed sample

- Window: `2015-07-20T21:00:00+00:00` .. `2019-11-30T23:00:00+00:00`
- Collection authorized: no
- Opening authorized: no
- `SEALED_EXECUTION` authorized: no

## Statistical limitation

The uncorrected Wilson bound treats the comparable structural events inside a single pair as exchangeable Bernoulli-type observations. Weekly structure is serially dependent and one episode can produce two adjacent-week disagreements, so they are not. Positive within-pair dependence widens the count's distribution in both tails, so nominal 95% coverage is not attained and the residual risk includes a false certification, not only a false refusal: against a beta-binomial with the same mean, a pair whose true structural disagreement rate is 0.30 certifies with probability 0.115 at n=30 under an intra-cluster correlation of 0.2, against 0.0003 under exchangeability. The frozen artifact's claim that this violation can only push a pair towards insufficiency or failure is wrong in direction, and this validator does not repeat it. The deterministic point-rate limit remains an assumption-free floor that the bound only tightens, so the gate is never weaker than having no bound at all. This is recorded provenance about a frozen rule the validator implements unchanged; it is not a new gate and it moves no verdict.
