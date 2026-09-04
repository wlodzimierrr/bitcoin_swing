# STRUCTURAL_GATE_DENOMINATOR_RESOLUTION

Namespace: `research_artifacts/btc019_gate_denominator_resolution/`

`BTC_REFERENCE_COMPOSITE_V2` froze six approval gates that are **rates**, and
declared a threshold and a direction for each. It never declared what any of
them is a rate *of*. This record answers one question:

> can the denominator the frozen protocol intended be recovered from evidence
> that existed before the defect was found — or does writing it down create a
> statistical rule the frozen hash never contained?

It approves no provider or composite, opens and collects no sealed sample,
moves no threshold, calibrates none, and rewrites no frozen artifact. BTC-019
remains **IN PROGRESS** and the production canonical reference remains
**UNRESOLVED**.

- Parent protocol: `BTC_REFERENCE_COMPOSITE_V2`
- Parent definition SHA-256: `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a` (**unchanged**)
- Comparison contract examined: `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2`
- Machine-readable record: `denominator_resolution.json`
- Proposed successor: `successor_protocol_definition.json`
- Schema: `STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_RECORD_V1`
- Sealed 2015-2019 sample opened: **no**; collected: **no**
- Outcome: **`NEW_PROTOCOL_VERSION_REQUIRED`**

---

## 1. What the frozen protocol actually says

Read from `protocol_definition.json`, whose bytes and definition hash this
record re-verifies before reasoning from it. For each of the six metrics the
frozen artifact declares exactly five things:

```text
metric  threshold  direction  hard  rationale (+ source_of_rationale)
```

It declares **no** numerator, **no** denominator, **no** candidate universe,
**no** comparison basis, and no treatment of an event that cannot be evaluated.
`validation_metric_families` lists the metric names under `swings`; a family
listing is not a definition.

So the denominator was not written down ambiguously. It was not written down.

## 2. What the pre-existing code says

Two implementations predate the defect, and they do not agree with each other.

| Source | Unit | Denominator | Comparison basis |
| --- | --- | --- | --- |
| `reference_composite_empirical.py::_structural_comparison` (V1) | per category: swing_high, swing_low, **breakout**, **reclaim** | `\|events XOR consensus\| / \|events OR consensus\|` | candidate series vs a **two-of-three raw-provider consensus** |
| `btc019b_diagnostics.py::_swing_metric_summary` (BTC-019B) | swing families pooled; **no breakout or reclaim rate exists** | `exact_timestamp` and `structural_state` over `len(exact_union)` = 33; `within_1_week` / `within_2_week` over `len(exact_union) - matched_pair_count` = 31 | composite vs exact provider consensus |

Three findings follow directly.

1. **A denominator formula is recoverable for four of the six metrics** —
   BTC-019B is the named calibration source for exactly those four, and it uses
   the all-detected-event union, with the within-N-week metrics on a
   pair-merged variant of it. The frozen artifact even records both numbers,
   33 and 31, so the six were never intended to share one denominator.
2. **`breakout_disagreement_rate` and `reclaim_disagreement_rate` have no
   pre-existing definition at all.** BTC-019B computes no breakout or reclaim
   rate; V1's frozen gate set contains one structural rate,
   `external_combined_swing_disagreement_rate_maximum = 0.10`, over the
   *combined swing* union. V2's two new gates are listed under the `swings`
   family while the only implementation measures them per category. Two
   incompatible readings, and the frozen definition chooses neither.
3. **The comparison basis is undeclared too.** Both pre-existing formulas
   compare against a two-of-three consensus series. `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2`
   is pairwise and declines to form a quorum, for a stated reason: a consensus
   series assembled from providers with different calendars has no calendar of
   its own to require. The frozen V2 protocol lists five `comparison_series`
   and says nothing about how they are paired or aggregated.

## 3. The decisive point: `NOT_COMPARABLE` did not exist

Every pre-existing formula has exactly two outcomes. A swing that one series
detects and the other does not lands in the symmetric difference and in the
union — **whatever the reason**. An availability gap is therefore not treated
one way or another by the frozen protocol; it is counted as a disagreement,
because the vocabulary contains no third thing to count it as.

That behaviour is recoverable. It is also precisely the correctness defect
`BTC019_COMPLETION_GATE_ASSESSMENT_V1` recorded and
`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` closed.

So the question "which denominator did the frozen protocol intend for
not-comparable events?" has no honest answer of the form *A* or *B*. The frozen
protocol intended neither, because it did not know the category existed. The
only reading it supports is the defective one:

```text
recoverable denominator  =  the defect
admissible denominator   =  new statistical semantics
```

There is no third option in which the frozen hash already contained the answer.
That is what makes this a new protocol version rather than a clarification, and
it is a conclusion about the frozen text alone — no verdict was consulted to
reach it.

### The record even pushes the other way

BTC-019B's frozen governance says:

> Exact timestamps are too brittle as a standalone weekly-structure gate, but
> the failure exposed **real omitted-week level and breakout state changes**.

That is pre-existing intent treating a week the candidate itself omitted as an
economically real structural difference — the opposite reading to excluding an
unevaluable event. The two can be reconciled (BTC-019B's omissions were caused
by the *candidate's own* quality policy; the comparison gaps are exogenous raw
provider outages), but no frozen artifact draws that distinction. Drawing it
now is new semantics, not recovery.

## 4. Threshold-validity audit

The audit question is not "is the number still reasonable" but "was the number
chosen knowing what denominator it represented".

| Metric | Hard | Frozen | Threshold-intent evidence | Semantics recoverable |
| --- | --- | --- | --- | --- |
| `exact_timestamp_swing_disagreement_rate` | no | `0.15` | "BTC-019B observed 12.1212%" = **4/33** on the all-detected-event union | **NO** |
| `within_1_week_swing_disagreement_rate` | yes | `0.05` | "diagnostic rate was zero; 5% allows sparse unexplained events" — 0/31 | **NO** |
| `within_2_week_swing_disagreement_rate` | yes | `0.02` | "diagnostic rate was zero; stricter 2% tail allowance" — 0/31 | **NO** |
| `structural_state_disagreement_rate` | yes | `0.05` | "BTC-019B separated structural effects from exact timestamp labels" — concept only; the observation was **2/33 = 6.0606%** | **NO** |
| `breakout_disagreement_rate` | yes | `0.05` | "Economic reasoning using existing deterministic breakout logic" — no artifact | **NO** |
| `reclaim_disagreement_rate` | yes | `0.05` | "Economic reasoning using existing deterministic reclaim logic" — no artifact | **NO** |

Three separate reasons, none of them a verdict:

- **The only numeric anchor is entirely availability.** `0.15` was fixed to sit
  above `4/33`. All four of those numerator events are `NOT_COMPARABLE`
  availability gaps under the comparison contract — the frozen BTC-019B record
  names the two weekly buckets the composite omitted, and each of the four has
  one of them inside its own confirmation window. Under the resolved
  denominator the anchor observation is not rescaled to some other number; it
  is **zero**. A threshold whose sole empirical anchor evaporates cannot be
  said to express the same rule.
- **`structural_state`'s observation already exceeded its own gate.** 6.0606%
  against a frozen `0.05`. The number was therefore never an accommodation of
  the calibration observation — it is a round economic allowance, and both of
  its numerator events are availability-driven too.
- **`breakout` and `reclaim` were never calibrated at all**, and their
  candidate universe was never determinable. There is nothing to carry forward.

For `within_1_week` and `within_2_week` the honest position is narrower and
still sufficient: a zero numerator is denominator-invariant, so the observation
carries no denominator information either way, and `0.05` / `0.02` were round
allowances never bound to a stated universe.

**Keeping the same number is not keeping the same rule.** `0.05` over
"events both series could evaluate" and `0.05` over "events at least one series
detected, outages counted as disagreements" are different statistical tests, and
the repository has already measured how different.

## 5. Materiality — used to show the question matters, never to answer it

From the persisted `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` measurements on the
**already-inspected** 2019-2022 and 2023-2025 samples only. Six pairwise
comparisons per metric.

| Metric | Hard | Verdict flips | Fails on comparable | Fails on all-event |
| --- | --- | ---: | ---: | ---: |
| `exact_timestamp_swing_disagreement_rate` | no | 3/6 | 0 | 3 |
| `within_1_week_swing_disagreement_rate` | yes | 3/6 | 2 | 5 |
| `within_2_week_swing_disagreement_rate` | yes | 2/6 | 4 | 6 |
| `structural_state_disagreement_rate` | yes | 4/6 | 1 | 5 |
| `breakout_disagreement_rate` | yes | 6/6 | 0 | 6 |
| `reclaim_disagreement_rate` | yes | 1/6 | 5 | 6 |

All six metrics, and all five hard ones, change verdict on at least one pair.

### The adversarial test

> If the opposite denominator produced the better gate verdict, would the same
> governance decision follow?

**Yes.** Every load-bearing finding above is a fact about the frozen text and
about code that predates the defect: the definition names no denominator, the
only recoverable reading is the known defect, two pre-existing formulas
disagree, and two of the six metrics have no calibration artifact whatsoever.
None was read off a verdict.

The adopted denominator is also **not** the convenient one. Under it
`reclaim_disagreement_rate` still fails five of six measured pairs and
`within_2_week` four of six. The single most favourable fact available — that
the comparable denominator makes `breakout_disagreement_rate` pass all six —
is admitted for nothing, precisely because it is the fact a contaminated
process would lean on.

## 6. Resolution: `NEW_PROTOCOL_VERSION_REQUIRED`

The frozen `BTC_REFERENCE_COMPOSITE_V2` definition, its hash, its thresholds
and its gate directions stay exactly as they are — the immutable record of what
was frozen, defect included. The new semantics are published as a successor.

**The successor is `BTC_REFERENCE_COMPOSITE_V3`, not a "V2.1".** The frozen
protocol names its own successor tier: `governance.material_change_requires` is
`"BTC_REFERENCE_COMPOSITE_V3 or later"`. A `V2.1` would be a version tier the
frozen governance does not recognise, and the decimal point would imply the
minor clarification this resolution finds it is not.

Status: `PROPOSED_PENDING_THRESHOLD_CALIBRATION`. It is not frozen, not
approved, and not evaluable.

### The resolved semantics

Common to all six: comparison is **pairwise on the two series' common weekly
calendar**, canonicalised by sorted series id, one measurement per pair, worst
admissible pair verdict; no quorum is formed. A `NOT_COMPARABLE` event —
availability gap, pending confirmation, out-of-coverage session, or
non-comparable source level — is **excluded from both numerator and
denominator** and individually recorded with its reason, its side and its exact
missing sessions.

| Metric | Candidate universe | Numerator | Denominator |
| --- | --- | --- | --- |
| `exact_timestamp_swing_disagreement_rate` | swing highs + lows pooled | comparable candidates exactly one series detects | `comparable_detected_event_union` |
| `within_1_week_swing_disagreement_rate` | swing highs + lows pooled | as above, less `2 x` matched opposing pairs within 1 week | `comparable_detected_event_union` less matched pairs |
| `within_2_week_swing_disagreement_rate` | swing highs + lows pooled | as above at 2 weeks | `comparable_detected_event_union` less matched pairs |
| `structural_state_disagreement_rate` | swing highs + lows pooled | comparable one-sided swings whose detecting series also confirmed a breakout/reclaim from them | `comparable_detected_event_union`, unmerged |
| `breakout_disagreement_rate` | breakout candidates keyed by shared source swing high | comparable candidates the pair resolves differently | `comparable_detected_event_union` for the family |
| `reclaim_disagreement_rate` | reclaim candidates keyed by shared source swing low | comparable candidates the pair resolves differently | `comparable_detected_event_union` for the family |

The within-N-week pair merge is **recovered, not invented**: BTC-019B's own
formula subtracts the matched pair count, and a "within N week matched" rate
whose denominator still counts one structure twice is not the quantity its name
claims.

### Why "neither", and not "agreement"

A structurally unevaluable event carries no information about whether two
series read structure the same way. Counting it as agreement makes the rate
monotone in the wrong direction — every extra outage buys a free agreement, so
a series that publishes less scores better. Counting it as disagreement is the
defect. Excluding it is the only treatment that leaves the rate measuring what
its name says.

### Coverage, so exclusion is not erasure

The successor requires, beside every structural rate and per pair and family:

```text
candidate_event_count
all_detected_event_count
comparable_event_count
not_comparable_event_count
structural_comparability_rate = comparable_event_count / all_detected_event_count
not_comparable_rate
not_comparable_reason_counts
availability_gap_side_counts
```

with the completeness invariant that comparable and not-comparable counts sum
to their universe. **No numeric floor is set on comparability here** — that
would be a threshold, and this task may not calibrate one; it is deferred, in
writing, to the calibration task.

One hard requirement is added: `unrecorded_not_comparable_event_count == 0`. It
is not a calibrated rate. It is the parent's own zero-count provenance
principle — `unrecorded_quality_state_count` and
`silent_incomplete_bucket_omission_count` are both hard equal-zero gates —
applied to the category the parent did not have.

The parent's existing hard availability gates (`reference_usable_rate`,
`reference_unavailable_rate`, the daily and weekly bucket usable rates,
`silent_incomplete_bucket_omission_count`) remain the primary defence against
"more outages → fewer comparable events → better-looking source". Their limit
is stated plainly in the record: they bind the *candidate* series only, and the
other side of a comparison is a raw provider nothing gates — which is exactly
why comparability evidence is mandatory.

### Thresholds

All six frozen numbers are carried across **verbatim** and marked
`CARRIED_FORWARD_UNCALIBRATED`. None may be evaluated until a separate
pre-sealed calibration and governance task binds a threshold to each of these
denominators, using the already-inspected samples and predeclared economic
reasoning. **No threshold is optimised, moved or invented here.**

### Hash implications

The parent hash `bc312f3e…6106a` stays as it is, permanently, as the record of
what was originally frozen. The successor carries its own
`definition_sha256` and an explicit `parent_definition_sha256`. When the
sealed validator is eventually built it must bind the **complete executable
definition it uses** — the calibrated successor's hash, not the parent's, and
not this proposal's, which will change when thresholds are bound to it.

## 7. Sequencing

1. Pre-sealed threshold calibration and governance for the six
   `BTC_REFERENCE_COMPOSITE_V3` structural metrics. Already-inspected samples
   only.
2. Freeze the successor definition; build the sealed validator bound to that
   frozen hash.
3. Collect 2015-2019.
4. Open the sealed sample, once.

Steps 2-4 remain refused today: `may_build_sealed_validator`,
`may_collect_sealed_sample` and `may_open_sealed_sample` are all `false` in the
record, and the inherited `guard_untouched_validation_sample` still raises on
any window overlapping `2015-07-20 21:00 .. 2019-11-30 23:00`.

## 8. Preservation

Unchanged by this resolution, and verified by test:

- the `BTC_REFERENCE_COMPOSITE_V2` definition, its bytes, its hash, every gate,
  threshold, direction and hard/soft flag;
- `PRICE_SOURCE_POLICY_V1` and `BITSTAMP = REJECTED`;
- `BTC_REFERENCE_COMPOSITE_V1` at `RESEARCH_INCONCLUSIVE`;
- BTC-019B at `MIXED`, artifacts byte-identical;
- `BTC019_COMPLETION_GATE_ASSESSMENT_V1` and the
  `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` evidence;
- `MEDIAN_OHLC_V2`, `detect_weekly_swing_levels`, `detect_breakout_reclaim_levels`
  and all production strategy semantics;
- the sealed `2015-07-20 .. 2019-11-30` window, unopened and uncollected.

## 9. One discrepancy noted, not corrected

The prose in `COMPARISON_REPORT.md`, the BTC-019 Implementation Notes and the
previous `CURRENT_STATE.md` says the frozen verdict flips "on five of the six
gates — including four hard ones". Recomputed from that measurement's own
`comparison_report.json`, every one of the six flips on at least one pair, and
all five hard ones do; the JSON's own
`classification.denominator_sensitive_hard_gates` already lists all five. The
historical report is left exactly as it was — it is evidence, and its machine-
readable half is correct. The accurate figures are recorded here and in
`CURRENT_STATE.md`.
