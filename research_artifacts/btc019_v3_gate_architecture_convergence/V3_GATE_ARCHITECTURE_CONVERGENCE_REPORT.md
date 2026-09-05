# BTC_REFERENCE_COMPOSITE_V3_GATE_ARCHITECTURE_CONVERGENCE_V1

Final gate-architecture convergence for BTC_REFERENCE_COMPOSITE_V3, on the evidence already in hand. No new evidence is collected, no candidate is constructed or measured, no frozen artifact is changed, and the sealed 2015-2019 validation sample is neither collected nor opened.

- Parent: `BTC_REFERENCE_COMPOSITE_V2` `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`
- Predecessor calibration: `BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1`, review `03bb52d2881ca11c55fd09b8a54d922ec7dc0079`
- Convergence boundary: `FINAL_CONVERGENCE_WITH_EXISTING_EVIDENCE`
- Outcome: **`V3_FROZEN_READY_FOR_VALIDATOR`**
- `BTC_REFERENCE_COMPOSITE_V3` definition hash: `4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a`

## Stage 1 -- the review's findings, reverified here

Each finding is recomputed from the repository's own measurements rather than taken on trust.

| Finding | Verdict | Evidence |
| --- | --- | --- |
| within-N identical to exact timestamp | CONFIRMED_BY_INDEPENDENT_RECOMPUTATION | 0 of 12 measurements distinguish them; 0 pairs merged in total |
| structural state nested in exact timestamp | CONFIRMED_BY_INDEPENDENT_RECOMPUTATION | 0 violations; strictly smaller on 2 of 6 |
| relative alternative degenerates | CONFIRMED_BY_INDEPENDENT_RECOMPUTATION | per-pair expected counts converge to 0.6402 against 1.9207 at every denominator |
| scalar minimum-n does not carry | CONFIRMED_BY_INDEPENDENT_RECOMPUTATION | holds at every probe: False; power monotone in n: False |

### The relative alternative, at every denominator

| per-pair n | pooled 6n | pi_bar | n*pi_bar | n*pi_alt |
| --- | --- | --- | --- | --- |
| 5 | 30 | 0.11351339 | 0.5675 | 1.7027 |
| 10 | 60 | 0.06017185 | 0.6017 | 1.8051 |
| 20 | 120 | 0.03101916 | 0.6203 | 1.8611 |
| 50 | 300 | 0.01264297 | 0.6321 | 1.8964 |
| 100 | 600 | 0.00636170 | 0.6361 | 1.9085 |
| 200 | 1200 | 0.00319100 | 0.6382 | 1.9146 |
| 1000 | 6000 | 0.00063983 | 0.6398 | 1.9195 |

### The scalar minimum, under unequal denominators

| metric | published minimum | denominators | family power | meets 0.80 |
| --- | --- | --- | --- | --- |
| exact_timestamp_swing_disagreement_rate | 13 | [20, 25, 30] | 0.8931 | True |
| exact_timestamp_swing_disagreement_rate | 13 | [18, 20, 22] | 0.8960 | True |
| exact_timestamp_swing_disagreement_rate | 13 | [30, 30, 30] | 0.9265 | True |
| exact_timestamp_swing_disagreement_rate | 13 | [25, 40, 55] | 0.9208 | True |
| structural_state_disagreement_rate | 17 | [20, 25, 30] | 0.7182 | False |
| structural_state_disagreement_rate | 17 | [18, 20, 22] | 0.7941 | False |
| structural_state_disagreement_rate | 17 | [30, 30, 30] | 0.7270 | False |
| structural_state_disagreement_rate | 17 | [25, 40, 55] | 0.7327 | False |

## Stage 2 -- the final architecture

| metric | role | supportable | covered elsewhere | reasons |
| --- | --- | --- | --- | --- |
| breakout_disagreement_rate | DIAGNOSTIC_ONLY | False | True | DENOMINATOR_CANNOT_CERTIFY, PROTECTION_RETAINED_AS_CENSUS_AND_TIER4 |
| exact_timestamp_swing_disagreement_rate | SOFT_WARNING_GATE | True | True | NESTED_IN_A_SURVIVING_HARD_GATE, LABEL_LEVEL_SIGNAL_ONLY |
| reclaim_disagreement_rate | DIAGNOSTIC_ONLY | False | True | DENOMINATOR_CANNOT_CERTIFY, PROTECTION_RETAINED_AS_CENSUS_AND_TIER4 |
| structural_state_disagreement_rate | HARD_APPROVAL_GATE | True | False | ECONOMICALLY_CONSEQUENTIAL_SUBSET, SUPPORTABLE_DENOMINATOR |
| within_1_week_swing_disagreement_rate | DIAGNOSTIC_ONLY | False | True | NOT_SEPARATELY_IDENTIFIED, MECHANISM_NEVER_EXERCISED |
| within_2_week_swing_disagreement_rate | DIAGNOSTIC_ONLY | False | True | NOT_SEPARATELY_IDENTIFIED, MECHANISM_NEVER_EXERCISED |

### Absolute materiality

A canonical BTC reference is materially unfit when, against an independent observable market reference, more than one in five economically consequential weekly structural events resolves differently. Economically consequential means the two series disagree about a weekly swing and the detecting series also confirmed a breakout or reclaim from it, so the difference changed downstream support and resistance state rather than only a label.

- Limit: `0.20`, direction `maximum`, applied to `structural_state_disagreement_rate`
- Relative `3 x pi_bar` retained: False
- **structural meaning.** The weekly structural map is a set of active levels, not a stream of independent observations. A disagreement rate is the fraction of that set which exists in one series and not the other. Above one in five, more than a fifth of the active map is source specific and the two series are no longer describing the same market structure -- whatever their prices look like.
- **strategy impact.** Weekly levels anchor BTC-141 invalidation and BTC-142 stops, feed the Structure Score and gate setup classification, and each level stays active for weeks. A level that only one series ever printed puts a stop and a setup on a venue artefact for the whole time it remains in the map.
- **stop / MFE / MAE consequences.** The trade-level cost of a bad reference is measured directly, and hard, by the inherited Tier-4 gates: stop_touch_disagreement_rate at most 0.01, cross_market_confirmed_stop_preservation_rate at least 1.0, MFE and MAE medians at most 0.0025 and p95 at most 0.01. The structural gate is the upstream cause, not the harm, so it is set where structural difference stops being isolated and becomes systematic -- not at the decision-tier tolerances, which bound the harm itself two orders of magnitude tighter.
- **known source sensitivity.** BTC-019 rejected Bitstamp as the sole canonical reference on a handful of structural differences whose Tier-4 consequences were a missed consensus stop and 2.433 / 4.605 percentage points of MFE / MAE sensitivity. The project's own precedent is that a few consequential structural differences are disqualifying when they propagate, which is what the Tier-4 gates test; the structural limit's job is to refuse a reference whose whole structural description differs.
- **Phase-1 tolerance philosophy.** Phase 1 asks for a reference a competent independent observer would accept as a description of the same market, not for a perfect one. Four in five agreement on consequential structural events is the weakest claim that still supports that reading, and the limit is a simple interpretable fraction rather than a fitted decimal.

### Certification rule

A pair certifies a maximum-direction structural gate when, and only when, it is admissible, its comparable-event denominator is non-zero, and the upper limit of the two-sided 95% Wilson score interval on its own numerator and denominator is at or below the absolute materiality limit. If the observed point rate itself exceeds the limit the pair is a material failure. If the point rate is at or below the limit but the upper limit is not, the pair has not produced enough evidence to exclude a material rate and is insufficient, never a pass. Equality certifies, in both comparisons, matching the repository's existing convention that a gate boundary is inclusive.

- One rule replaces the predecessor's separate threshold and scalar minimum-n, so there is no equal-denominator derivation to carry.
- It is evaluated on one pair's own numerator and denominator, so an unequal denominator vector needs no separate treatment and cannot invalidate it.
- A small denominator widens the interval, so thin evidence fails to certify rather than passing quietly: insufficient evidence can never approve.
- A zero comparable denominator has no interval at all and is insufficient, never a rate of 0.0.
- It is a deterministic function of two integers, a declared quantile and an explicit Decimal context, so it reproduces exactly.
- It separates a reference that is measurably bad from one that is merely unmeasured, which the predecessor's single threshold could not.

### Dependence

- **Removed:** pooled provider-pair rows as independent Bernoulli trials. No band is pooled across pairs to set a threshold. The materiality limit is absolute and economic, so the three provider pairs -- which share the same underlying weekly structural events, one market fact appearing in two or three rows -- are never combined into one estimate that a threshold is read off.
- **Removed:** multiplied family-wise survival across gate pairs. No family-wise probability is computed. The approval rule is a conjunction and is reported as one; each pair's 95% statement is about that pair alone and is labelled as such.
- **Disclosed:** One assumption remains and is declared rather than hidden. The Wilson interval treats the comparable structural events inside a single pair as exchangeable trials. They are distinct calendar events, not one fact repeated across rows, so this is far weaker than the cross-pair assumption that was removed -- but weekly structure is serially dependent and one episode can produce two adjacent-week disagreements, so it is not exact. Its violation is conservative for approval: clustering inflates a numerator, and on a maximum-direction gate read through an upper bound that pushes a pair towards insufficient or failure, never towards a pass. No claim of exact coverage is made or needed, because the approval rule is the deterministic conjunction and the bound only decides whether one pair has enough evidence.

### Transfer guard

Every unordered pair of distinct independent raw validation providers must itself certify the structural_state metric, under the same absolute materiality limit and the same per-pair confidence bound as the gate pairs, on the same sample and the same comparison contract. GUARD_FAILED when any provider pair is a material failure; GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE when any is missing, inadmissible, undefined or insufficient; GUARD_SATISFIED only when all of them certify.

- Blocks: The candidate is the element-wise median of the same three providers it is compared against, so median(A,B,C) against A, B or C is mechanically closer than A against B. A composite could therefore certify every gate pair merely because it is an arithmetic function of those pairs' own inputs, while the underlying providers do not agree about market structure at all. In that state 'the market structure' is not identified in the period, and no median of the three can be certified as a canonical description of it, however close it sits to each input.
- Depends on the candidate: False. Every input is a series the candidate is not built from on that pair's own side, so no arrangement of the median can satisfy the guard: it is arithmetically impossible for candidate construction to influence a provider-versus-provider measurement. That is the property the review's missing guard needed, and a cosmetic guard computed on candidate pairs would not have it.

## Observed development dispersion, and the realism check

The materiality limit is declared from economic consequence. This check runs afterwards and reports only whether that limit is realistic against legitimate independent-source variation. It cannot move the limit: had it failed -- had legitimate providers routinely exceeded the limit -- the conclusion would have been that the metric cannot be a hard gate, not that the limit should be raised.

| sample | pair | count | rate | 95% upper | comparability | admissibility |
| --- | --- | --- | --- | --- | --- | --- |
| data/btc019/2023-01-01_2025-12-31 | bitfinex_vs_bitstamp | 2/28 | 0.071428 | 0.226453 | 0.8 | PAIR_ADMISSIBLE |
| data/btc019/2023-01-01_2025-12-31 | bitfinex_vs_coinbase | 1/26 | 0.038461 | 0.188927 | 0.7647 | PAIR_ADMISSIBLE |
| data/btc019/2023-01-01_2025-12-31 | bitstamp_vs_coinbase | 1/28 | 0.035714 | 0.177121 | 0.9032 | PAIR_ADMISSIBLE |
| data/btc_reference_composite_v1/external_2019-12-01_2022-12-31 | bitfinex_vs_bitstamp | 0/23 | 0 | 0.143116 | 0.7187 | PAIR_ADMISSIBLE |
| data/btc_reference_composite_v1/external_2019-12-01_2022-12-31 | bitfinex_vs_coinbase | 0/22 | 0 | 0.148654 | 0.6666 | PAIR_ADMISSIBLE |
| data/btc_reference_composite_v1/external_2019-12-01_2022-12-31 | bitstamp_vs_coinbase | 0/29 | 0 | 0.116969 | 0.9062 | PAIR_ADMISSIBLE |

- Conclusion: **REALISTIC**
- Worst legitimate pair rate: 0.071428
- Measurements certifying at the limit: 5 of 6
- No independent raw-provider pair's observed structural_state rate reaches the limit; the worst is 0.07142857142857142857142857143. 5 of 6 measurements also certify it outright at their own development denominators, and at least one already-inspected sample has all three of its pairs certifying, so the limit is attainable and not only unexceeded.

## Sensitivity to the governance assumptions

The architecture, not a historical verdict label, is what is tested. structural_state can carry a hard gate from 0.15 onwards; breakout only from 0.30 and reclaim nowhere on the neighbourhood at all. That ordering is what the demotions rest on, and it is not a property of the declared limit: no limit in the neighbourhood reverses it. The limit does change what evidence the hard gate demands -- at 0.10 a clean pair needs 35 comparable events and no development sample can certify all three pairs, which is the boundary at which structural_state would itself stop being a viable hard gate. Denominator imbalance changes nothing, because the rule is evaluated per pair on that pair's own counts.

| limit | min n at 0/1/2/3 disagreements | realism | structural state viable | breakout viable | reclaim viable |
| --- | --- | --- | --- | --- | --- |
| 0.10 | 35/53/69/84 | NOT_REALISTIC_LIMIT_UNATTAINABLE_AT_REALISTIC_DENOMINATORS | False | False | False |
| 0.15 | 22/34/45/55 | REALISTIC | True | False | False |
| 0.20 | 16/25/33/40 | REALISTIC | True | False | False |
| 0.25 | 12/19/25/31 | REALISTIC | True | False | False |
| 0.30 | 9/15/21/25 | REALISTIC | True | True | False |

| metric | tightest limit at which it could be a hard gate |
| --- | --- |
| breakout_disagreement_rate | 0.30 |
| reclaim_disagreement_rate | nowhere |
| structural_state_disagreement_rate | 0.15 |

| confidence | min n at 0/1/2/3 disagreements |
| --- | --- |
| 90% | 11/20/28/35 |
| 95% | 16/25/33/40 |
| 99% | 27/36/45/53 |

| comparability floor | admissible measurements |
| --- | --- |
| 0.40 | 6 of 6 |
| 0.50 | 6 of 6 |
| 0.60 | 6 of 6 |
| 0.75 | 4 of 6 |

- Policy conclusion stable across the neighbourhood: **True**; the conclusion holds at the declared limit: **True**

## Old architecture against final architecture

- `BTC_REFERENCE_COMPOSITE_V2` / V3 proposal: 6 structural rate gates, 5 hard, thresholds `CARRIED_FORWARD_UNCALIBRATED`
- Final `BTC_REFERENCE_COMPOSITE_V3`: 1 hard structural rate gate, 1 soft, 4 diagnostics, plus 5 new hard requirements

| metric | change | parent hard | why | what remains |
| --- | --- | --- | --- | --- |
| breakout_disagreement_rate | DEMOTED_TO_DIAGNOSTIC | True | Zero disagreements over 39 pooled comparable events, on admissible pair denominators of 5 to 12. At a denominator of 12 and no disagreements the 95% upper bound is 0.2425, and at 9 it is 0.2991: the evidence cannot exclude a rate above any economically defensible limit for a derived level, so no certification is available at these denominators. Under the predecessor's relative alternative it was worse -- unidentifiable at every denominator, as Stage 1 reconfirms. | A breakout difference from a swing the two series disagree about is already counted once by structural_state -- which is defined as exactly the swing disagreements that changed breakout or reclaim state. What remains here is a differing confirmation of a shared level, whose trade-level consequence is bounded hard and directly by the inherited Tier-4 stop, MFE/MAE, eligibility, action and setup-classification gates on hourly synchronized bars. |
| exact_timestamp_swing_disagreement_rate | RETAINED_AS_SOFT | False | Same denominator as the hard gate, so it is measurable; but a label-level difference is not by itself economic harm, so its measurability does not make it an approval veto. | It shares structural_state's denominator and its numerator is a superset of structural_state's on every one of the twelve measurements; structural_state is exactly the part of it that propagated. Two hard vetoes over one nested event set would be the same evidence counted twice, which the project's factor-separation rule refuses. What it adds beyond the hard gate is timing information that has not yet propagated, which is a reason to look rather than a reason to reject. |
| reclaim_disagreement_rate | DEMOTED_TO_DIAGNOSTIC | True | Three disagreements over 21 pooled comparable events, with admissible pair denominators of 2 to 6. At 5 comparable events even a zero numerator has a 95% upper bound of 0.4345, and 1/5 gives 0.6245. Nothing in that range is an economically defensible materiality limit for a derived level, and the non-sealed history that would enlarge the denominator does not exist. | Same position as breakout: propagated swing differences are already counted by structural_state, and the trade-level consequence of a differing confirmation is bounded by the inherited Tier-4 gates. |
| structural_state_disagreement_rate | RETAINED_AS_HARD | True | not demoted | Nothing else in the protocol measures upstream structural difference. The Tier-4 gates measure the harm once it reaches a trade; this measures the cause, and a systematically different structural description can exist in a period whose trades happen not to expose it. |
| within_1_week_swing_disagreement_rate | DEMOTED_TO_DIAGNOSTIC | True | Its defining mechanism is never exercised by the evidence, so its own threshold is not separately identified. A number fixed here would be a number about exact_timestamp wearing another name. | It is exact_timestamp with matched opposing pairs merged. No measurement in either already-inspected sample merges a pair, so on all twelve observations it is numerically identical to exact_timestamp and carries no separate information. |
| within_2_week_swing_disagreement_rate | DEMOTED_TO_DIAGNOSTIC | True | Not separately identified for the same reason, and its inherited 0.02 was a round tail allowance never bound to any event universe. | Identical position to within_1_week, at a wider tolerance: no measurement merges a pair, and the only opposing-side swing disagreement pair anywhere in the record is three weeks apart, outside both tolerances. |

Five hard structural rate gates become one. Two of the five were numerically identical to a metric that is now soft, two could not certify at any defensible limit on their own denominators, and the survivor is the economically consequential subset of the fifth. In exchange the protocol gains four hard requirements that are actually computable -- a comparability floor, a required-pair count, a zero-count derived-level review census and a non-candidate-dependent raw-provider dispersion guard -- and keeps every inherited Tier-4 hard gate, which is where a structural difference's economic cost is measured directly.

## Derived-level protection after the simplification

- **structural_state hard gate** (hard: True). The hard structural gate is itself defined as the swing disagreements that changed a breakout or reclaim state, so derived-level propagation is what it counts. Demoting the breakout and reclaim rate gates does not remove derived-level protection; the surviving hard gate is about derived-level propagation.
- **hard comparability and coverage requirement** (hard: True). A derived-level comparison built on a gappy calendar is NOT_COMPARABLE by contract and is excluded from both numerator and denominator, and a pair whose measured set is a minority of its detected set cannot certify at all. A low rate bought with outages is refused before it is read.
- **derived-level census with mandatory individual review** (hard: True). Every comparable breakout and reclaim disagreement observed on a required gate pair must carry a structured manual review with a recorded economic assessment, in the form BTC-019 already uses. The gate is a zero count, in the parent's own zero-count provenance idiom, not a calibrated rate: at 21 to 39 comparable events a complete census that is individually reviewed is a stronger control than a rate compared against a threshold no one can defend.
- **inherited Tier-4 stop and MFE/MAE sensitivity gates** (hard: True). These are the direct economic measurement of what a breakout or reclaim difference actually costs, on hourly synchronized bars with denominators three orders of magnitude larger than the weekly structural counts. They are inherited hard and unchanged, and they are what rejected Bitstamp.
- **breakout and reclaim diagnostics** (hard: False). The full event census stays published per pair and per sample, with reasons, so a future sample that does produce a certifiable denominator can be read against this record without reopening the contract.

## Governance

- `BTC-019`: IN_PROGRESS
- Production canonical reference: UNRESOLVED
- `BTC_REFERENCE_COMPOSITE_V3` status: FROZEN_RESEARCH_PROTOCOL
- Validator construction authorised: True, after an independent review of this frozen definition
- Sealed sample collected: False; opened: False
- New evidence collected: False
- Candidate constructed / measured / evaluated: False / False / False
- Frozen prior artifacts changed: False
- Further evidence round authorised: False

Classification rule: V3_FROZEN_READY_FOR_VALIDATOR when every surviving hard gate carries an absolute materiality limit derived from consequence rather than from observation, a certification rule valid on the denominators a real gate will have, an explicit dependence treatment that assumes no cross-pair independence, a non-candidate-dependent transfer guard, a hard comparability policy whose insufficient-evidence branch cannot approve, and preserved derived-level protection -- and the realism check confirms the limit is achievable by a legitimate reference. V3_NOT_FREEZABLE_SOURCE_POLICY_REDESIGN_REQUIRED otherwise. There is no third outcome: this is the final convergence on the existing evidence, and a further research round is not available.
