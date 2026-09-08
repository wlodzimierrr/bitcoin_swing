# Current Project State

> [!NOTE]
> This file is a compact project handoff snapshot.
>
> It is NOT an independent source of strategy or ticket authority.
>
> If it disagrees with the authoritative Structured Tickets document or an
> applicable policy, the authoritative document wins and this file must be
> corrected.

BTC-019 = TERMINALLY BLOCKED

terminal reason =
MISSING FROZEN DETERMINISTIC INTEGRATION EVIDENCE

V5 =
95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89

V5 validator = NOT ISSUED
Stage-A builder = NOT ISSUED
executor = NOT ISSUED

sealed sample = NOT COLLECTED / NOT OPENED
candidate = NOT EVALUATED
canonical production reference = UNRESOLVED

no further BTC-019 calibration/evidence-design work authorized

PROSPECTIVE_INTEGRATION_CORPUS_V1 =
FROZEN_PRE_DATA_PROTOCOL

protocol hash =
aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326

collection = NOT AUTHORIZED until independent xHigh review passes
qualifying observations collected = NONE
real Stage-B outcomes evaluated = NONE
BTC-019 sealed sample = STILL NOT COLLECTED / NOT OPENED

## Snapshot

- **Last updated:** 2026-09-08
- **Current phase:** Phase-1 deterministic implementation is COMPLETE. Every
  Phase-1 implementation ticket except BTC-019 is DONE, and BTC-019 itself is
  terminal at `BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE`: its
  V3 protocol and certified V1 validator are frozen and reviewed, but the
  sealed executor failed repeat review twice, V4's stage correction left ten
  Stage-A hard gates without a conforming owner, and V5 found that eight of
  those need a deterministic integration corpus that does not exist. Work has
  moved to the new post-Phase-1 EPIC X, whose first task freezes that corpus
  prospectively
- **Authoritative execution roadmap:** [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
- **Current implementation frontier:** Phase-1 implementation is complete and
  BTC-019 is terminal, so the frontier has moved to the new post-Phase-1
  workstream [EPIC X](execution/post_phase1_prospective_integration_evidence_v1.md).
  Its first task, POSTP1-001, has frozen
  `PROSPECTIVE_INTEGRATION_CORPUS_V1` as a pre-data protocol and awaits
  independent xHigh review. Historically, BTC-019 stopped because ten Stage-A
  hard gates had no conforming executable owner; V4 deterministically moved only
  `live_shadow_days >= 90` from historical validation to post-certification
  promotion, and certified V1, frozen V3, V4 and V5 remain unchanged
- **Last completed ticket:** BTC-224, golden historical scenarios. Its
  required independent xHigh review has now passed with one review fix, as
  have BTC-221's and BTC-222's; no Phase-1 ticket review remains outstanding
- **Last epic integration audit:** EPIC T, research and learning loop
  (2026-09-04), PASS WITH NON-BLOCKING FINDINGS after two P2 review fixes.
  EPIC S2 was audited earlier the same day; EPIC S, EPIC Q, EPIC P, EPIC O,
  EPIC E and EPIC E2 were audited on 2026-09-03
- **Current IN_PROGRESS ticket:** POSTP1-001, implemented and awaiting its
  independent xHigh review. BTC-019 is terminal and is not in progress
- **Current BLOCKED tickets:** None recorded in Structured Tickets v2.6
- **Next dependency-satisfied ticket:** POSTP1-002,
  `FORMAL_XHIGH_REVIEW_PROSPECTIVE_INTEGRATION_CORPUS_V1`, against protocol hash
  `aaa05c72...d37326`. Prospective collection may not begin until it passes, and
  BTC-019 does not reopen whatever the review concludes. The failed V2 hash
  `7fda8ac3...ad8be6` and its predecessors remain immutable lineage
- **Other ready tickets:** None
- **Latest verified test baseline:** 4526 passed with Python 3.12.14 and
  `RuntimeWarning` treated as an error on 2026-09-08
- **Last relevant implementation/review commit:** POSTP1-001 freezes
  `PROSPECTIVE_INTEGRATION_CORPUS_V1` at
  `aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326`. It follows
  `a50efcc7d9861cae6a2c9f69958fd39d73fcdc25`, which staged
  `BTC_REFERENCE_COMPOSITE_V5` and terminated BTC-019. Frozen V3, V4, V5 and
  certified V1 remain valid and immutable; the 2015-2019 sample stays
  uncollected and unopened

## Price-Reference State

```text
BTC-019 = TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE
Bitstamp sole canonical candidate = REJECTED
BTC_REFERENCE_COMPOSITE_V1 = RESEARCH_INCONCLUSIVE
BTC-019B = MIXED
BTC_REFERENCE_COMPOSITE_V2 = FROZEN_RESEARCH_PROTOCOL
production canonical reference = UNRESOLVED
BTC-019 completion gate = BLOCKED_BY_UNRESOLVED_CORRECTNESS_DEFECT
CROSS_PROVIDER_STRUCTURE_COMPARISON_V2 = RESEARCH_INCONCLUSIVE
STRUCTURAL_GATE_DENOMINATOR_RESOLUTION = NEW_PROTOCOL_VERSION_REQUIRED
V3 structural threshold calibration = CALIBRATION_INSUFFICIENT
V3 gate architecture convergence = V3_FROZEN_READY_FOR_VALIDATOR
BTC_REFERENCE_COMPOSITE_V3 = FROZEN_RESEARCH_PROTOCOL
V3 frozen-definition independent review = PASS_WITH_NON_BLOCKING_FINDINGS
hash-bound V3 validator
  = VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION
V3 validator independent review = PASS_WITH_NON_BLOCKING_FINDINGS
V3 validator definition hash
  = 8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7
one-shot V3 sealed executor
  = SEALED_EXECUTOR_REQUIRES_FIX
V3 sealed-executor independent review
  = FAIL_SEALED_EVIDENCE_BUILDER_INCOMPLETE
V3 executing validator definition hash
  = 7fda8ac31f92de6a4adfc547260c0fb8f221564de34982ff8a72e85c07ad8be6
BTC_REFERENCE_COMPOSITE_V4 stage correction
  = V4_EVIDENCE_PIPELINE_INCOMPLETE
V4 definition hash
  = 670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501
V4 validator definition hash
  = 8cf091fb8c0374f876dc54237d0226cea3f11a3d7554f6abae5ba5c1df498c28
V4 live builder / executor hash = NOT ISSUED
BTC_REFERENCE_COMPOSITE_V5 certification pipeline
  = TERMINALLY_BLOCKED_MISSING_INTEGRATION_EVIDENCE
V5 definition hash
  = 95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89
V5 validator / Stage-A builder / executor = NOT ISSUED
V3 sealed execution state = NOT_PREPARED
candidate final V3 result = NOT EVALUATED
sealed sample = NOT COLLECTED, NOT OPENED
PROSPECTIVE_INTEGRATION_CORPUS_V1 = FROZEN_PRE_DATA_PROTOCOL
prospective corpus protocol hash
  = aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326
prospective collection = NOT AUTHORIZED
```

Normal Phase-1 implementation may continue through injectable, versioned
reference-price boundaries. Final authoritative strategy calibration and
certification remain blocked until the production canonical reference is
resolved. See [PRICE_SOURCE_POLICY_V1](policies/price_source_policy_v1.md).

`BTC019_COMPLETION_GATE_ASSESSMENT_V1` under
`research_artifacts/btc019_completion_gate/` records why no candidate can be
approved yet. Cross-provider weekly structural comparison indexes its
confirmation window by row, so a session a provider outage removed is read as
if the weeks either side of it were neighbours; 24 of the 40 recomputed
structural differences across both collected samples sit inside that reach.
Six `BTC_REFERENCE_COMPOSITE_V2` approval gates, five hard, are computed from
that comparison, so the sealed 2015-2019 sample stays shut. The frozen
`COMPLETION_GATE_REPORT.md` reads "four of them hard"; the frozen V2
definition makes only `exact_timestamp_swing_disagreement_rate` soft, so the
count is five. The historical report is left as it stands. The frozen
`BITSTAMP = REJECTED` decision is unaffected: its 10 October 2025 consensus
stop and its MFE/MAE sensitivities are Tier 4 comparisons on synchronized
hourly bars.

`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` under
`research_artifacts/btc019_structure_comparison_v2/` closes the comparison
defect. A versioned research adapter in front of the unchanged production
detectors requires every calendar week of a candidate's own confirmation reach
to be present in both compared series before their verdicts may be compared, so
an absent session becomes `NOT_COMPARABLE` with the side and the missing weeks
named instead of a venue disagreement. Both already-inspected samples were
re-measured and the sealed sample stayed shut. The V1 comparison still
reproduces its frozen counts beside it. 26 of the 40 prior differences are not
comparable and 14 remain genuine -- 1 swing high, 5 swing lows, 8 reclaims, no
breakouts -- and all four BTC-019B exact-timestamp disagreements fall away.
Every affected gate is now measurable on an explicit denominator, but the
outcome is `RESEARCH_INCONCLUSIVE`: the frozen thresholds were calibrated over
an undeclared denominator, and the verdict against the identical frozen number
changes between the comparable-event and all-event denominators on every one of
the six structural gates, all five hard ones included.

`BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1` under
`research_artifacts/btc019_structural_threshold_calibration/` is the pre-sealed
governance and calibration task that had to precede any freeze. Outcome:
`CALIBRATION_INSUFFICIENT`. Phase A settles every semantic the predecessor's
review left open and hashes them as
`BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_CALIBRATION_GOVERNANCE_V1`
(`503ec795...67e6e6`), which Phase B verifies before computing anything. The
gate pair universe is the three {candidate, independent raw provider} pairs;
provider-versus-provider pairs become source-dispersion calibration evidence and
`MEDIAN_OHLC_V1` is excluded from both, so the series the thresholds are
calibrated on are disjoint from the series they will be applied to. Worst-pair
aggregation reads its direction from each gate and turns any missing,
inadmissible or undefined required pair into `UNDEFINED_INSUFFICIENT_EVIDENCE`;
a zero comparable denominator is null, never `0.0`; and
`MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1` replaces
"nearest-admissible-pair first", pinning the review's `{W0, W4}` against
`{W2, W6}` case at two matched pairs. The objective was predeclared: the
smallest interpretable grid value whose family-wise false rejection against the
pooled independent band is at most 0.10 and whose power against three times that
band is at least 0.80, on both samples' own denominators, in exact rational
arithmetic. Two metrics calibrate --- `exact_timestamp` (soft) at 0.25 and
`structural_state` (hard) at 0.20, neither on a knife edge, each with a derived
minimum of 13 and 17 comparable events per gate pair. Four do not, and all four
are hard: `within_1_week` and `within_2_week` because no measurement in either
sample ever merges a pair, so they are numerically identical to `exact_timestamp`
and not separately identified; `breakout` on 0/39 comparable events and
`reclaim` on 3/21, where no threshold is both achievable by an independent
provider pair and able to detect a materially worse reference. The frozen V2
numbers stay `CARRIED_FORWARD_UNCALIBRATED`, hard/soft statuses are inherited
unchanged, the candidate was never built or measured, and the sealed sample was
neither collected nor opened. `BTC_REFERENCE_COMPOSITE_V3` therefore stays
`PROPOSED`, and validator construction is still not authorised.

`STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1` under
`research_artifacts/btc019_gate_denominator_resolution/` settles that
denominator as governance. Outcome: `NEW_PROTOCOL_VERSION_REQUIRED`. The frozen
V2 artifact declares only metric, threshold, direction, hard flag and rationale
for the six -- no numerator, denominator, candidate universe or comparison
basis; the two formulas that predate the defect disagree with each other; the
breakout and reclaim gates have no calibration artifact at all; and the only
denominator recoverable from the record is the one that counts an availability
gap as a disagreement, which is the defect. `BTC_REFERENCE_COMPOSITE_V2`, its
hash `bc312f3e...6106a`, its thresholds and its gate directions are unchanged
and stay the immutable record of what was frozen. The successor is
`BTC_REFERENCE_COMPOSITE_V3`, the tier the frozen V2 governance clause already
names, proposed and not frozen: it defines each metric's numerator, denominator
and pairwise aggregation, excludes a `NOT_COMPARABLE` event from both, requires
comparability and coverage evidence beside every rate, and carries the six
frozen numbers across verbatim and explicitly uncalibrated. No threshold moved
and none was optimised. The sealed sample stays shut: a separate pre-sealed
threshold calibration and governance task must bind a threshold to each of the
six new denominators before the hash-bound validator is built, 2015-2019 is
collected, and the sample is opened once.

`BTC_REFERENCE_COMPOSITE_V3_GATE_ARCHITECTURE_CONVERGENCE_V1` under
`research_artifacts/btc019_v3_gate_architecture_convergence/` is the bounded
final convergence the calibration review's
`FINAL_CONVERGENCE_WITH_EXISTING_EVIDENCE` classification called for. Outcome:
`V3_FROZEN_READY_FOR_VALIDATOR`. No evidence was collected, no candidate was
constructed or measured, no frozen artifact moved, and 2015-2019 is still
neither collected nor opened. The four review findings are reverified from the
repository's own measurements before anything rests on them, and the module
refuses to proceed if one is refuted; all four hold, and the scalar-minimum
defect is worse than reported -- family power is not monotone in the
denominator, so `structural_state` at 0.20 scores 0.8032 at `[17,17,17]` but
0.7270 at `[30,30,30]`. Six structural rate gates, five hard, become one hard
gate, one soft gate and four diagnostics: `structural_state` stays hard,
`exact_timestamp` becomes a soft warning and mandatory-review trigger that can
never reject alone, and `within_1_week`, `within_2_week`, `breakout` and
`reclaim` become diagnostics that no verdict path can consult. The relative
`3 x pi_bar` alternative is gone, replaced by one absolute economic limit of
`0.20` declared ahead of any measurement from strategy impact, structural
meaning, the Tier-4 consequences and Phase-1 tolerance philosophy, with
`max(observed) + epsilon`, any multiple of the observed band, and anything
involving the candidate persisted as refused derivations. Threshold and
minimum-n become one rule, `PER_PAIR_WILSON_UPPER_BOUND_V1`, valid on any
denominator vector because it is evaluated on one pair's own counts, and it
separates a reference that is measurably bad from one that is merely
unmeasured. No band is pooled across pairs and no family-wise probability is
multiplied: approval is a deterministic conjunction over three enumerated
candidate-versus-provider pairs. The review's missing guard is
`RAW_PROVIDER_STRUCTURAL_DISPERSION_CEILING_V1`, hard and computed only on
provider-versus-provider pairs, so candidate construction cannot influence it.
Derived-level protection survives the demotions through the surviving hard
gate, the hard comparability floor, a new zero-count reviewed census of every
breakout and reclaim disagreement, and the thirteen inherited Tier-4 hard
gates. `BTC_REFERENCE_COMPOSITE_V3` is therefore `FROZEN_RESEARCH_PROTOCOL`
with definition hash
`4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a` and an
unchanged `parent_definition_sha256` of `bc312f3e...6106a`. Validator
construction is authorised only after this frozen definition receives its own
independent xHigh review, and the validator must bind the V3 hash, not the
parent's.

That review is now done. Result: `PASS WITH NON-BLOCKING FINDINGS`. The hash
recomputes from the persisted artifact and from the module and is invariant to
working directory, `PYTHONHASHSEED`, ambient `Decimal` context, pair and
dictionary order and process restart; the parent reverifies independently; no
historical frozen artifact has moved since its own freeze commit; the candidate
is never constructed and 2015-2019 exists nowhere on disk. All four convergence
premises were reproduced from the repository's own event records rather than
from the module, the derived minima of 16/25/33/40 were recomputed from the
textbook Wilson formula at 60 digits, and 27 independently tampered
verdict-affecting fields all moved the hash and were refused on restore. One P2
review fix closed a fail-open in the reference implementation: `certify_pair`
and `evaluate_soft_gate` treated an absent admissibility state or comparability
rate as satisfying the requirement the frozen policy states as *carrying*
complete evidence. Because every measurement the repository produces carries
both fields, the definition hash and the record digest `01328399...5b313` are
unchanged and no artifact byte moved. That validator now exists.

`BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1` under
`btc_predictor/research/reference_composite_v3_validator.py`, with its contract
persisted at `research_artifacts/btc019_v3_validator/`, is an executable
interpretation contract bound to `4232e886...bf71a` and hashed itself as
`b9a1d878c98fbda7f6ef93186262fb1d7e5825d93249fa1157c3f0856aa15194`, so a future
sealed execution record binds both. It is not a new price-reference protocol:
it authors no threshold and moves no frozen byte. It closes the review's three
unbound items. Operative precedence: `gate_architecture`, `materiality` and the
other nine operative blocks govern, and `frozen_threshold`, `frozen_hard`,
`frozen_direction` and `frozen_validation_stage` are parent provenance no
verdict path reads, so `structural_state` is read at `0.20` beside its
historical `0.05` and the four demoted metrics stay diagnostics beside their
historical `frozen_hard: true`. Composition: seven hard requirements recovered
from the freeze rather than from `approval_verdict`'s signature, including the
two the review found missing --- the NOT_COMPARABLE census, which that function
has no parameter for, and the required pair count of 3, which
`evaluate_hard_structural_gate` never checked. Precedence is material failure
first, lifted from the frozen aggregation's own words and confirmed by parity
with `approval_verdict` on all 72 states it can express; four requirements can
fail, the other three can only refuse, and the composition raises rather than
let one of them condemn. The Wilson variant is written out, uncorrected, on the
hash-bound quantile, checked against an independent 60-digit solution of the
score equation, and the continuity-corrected reading is computed beside it and
refuses all four certifying boundaries, so it cannot substitute. One fail-open
beyond the frozen review is closed: the derived-level census was self-declared,
so a bundle reporting no observed breakout or reclaim disagreements satisfied a
hard requirement by omission; it is now verified against the frozen diagnostics'
own mandatory `count`, which consults a diagnostic count through a frozen
completeness rule and never a diagnostic rate. The accepted risks are
preserved: the transfer guard still returns
`GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE` on a 2/28 provider pair, no threshold
moved, and the within-pair dependence limitation travels on every record stated
correctly rather than repeating the frozen artifact's wrong-direction claim.
`SEALED_EXECUTION` raises unconditionally at this revision, `DRY_RUN_SYNTHETIC`
is the only mode that runs, and the inherited guard refuses any bundle reaching
into the sealed window; a regression watches every filesystem read a complete
validation performs and proves it opens nothing under `data/`. 299 focused
tests. Outcome: `VALIDATOR_READY_FOR_INDEPENDENT_REVIEW`.

That review is now done. Result: `PASS WITH NON-BLOCKING FINDINGS`,
classification `VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION`. Both
hashes recompute from the persisted artifacts under an independently written
canonical serialization and are invariant to working directory,
`PYTHONHASHSEED`, ambient `Decimal` context, pair, series and reason order and
process restart. The seven hard requirements were re-derived by walking every
`hard: true` assertion in the freeze: none is omitted and none is invented, and
a tracking read proves `metric_definitions` -- the sole carrier of
`frozen_threshold` and `frozen_hard` -- is never read at all. The 648-state
space was rebuilt independently rather than rerun, with exactly one `PASS` and
all 1539 illegal states refused. The uncorrected Wilson bound was reimplemented
and cross-checked against the quadratic root of the score equation to 40
digits; Newcombe's corrected limit refuses all four certifying boundaries.
Tier-4 parity is exact on all 33 gates. 49 contract tampers all moved the hash
and were all refused. A complete validation opens exactly two files, both
frozen protocol artifacts. The derived-level census cross-check is
`FROZEN_SEMANTIC_INTEGRITY_CHECK`, not a new rule: the frozen requirement is
that *every observed* comparable breakout and reclaim disagreement carries a
review, and the frozen diagnostics' mandatory `count` is the only in-protocol
record of what was observed, so a conforming bundle cannot declare zero beside
a nonzero count. It reads a count and never a rate, and can only refuse.

Three review fixes were made and the validator contract hash moved from
`b9a1d878...15194` to `8e6254e0...c7ffe7`; no frozen V3 byte moved and
`4232e886...bf71a` is unchanged. Two P2 fail-opens were closed. A pair's
`denominator` and `structural_comparability_rate` were read as declared rather
than verified against the counts the same record carries, so a pair with 40
comparable of 440 detected events could declare a comparability rate of `0.90`
and clear the hard `0.50` floor, and a pair with 2 comparable events could
declare a denominator of 40 and certify at `0/40`; both produced a `PASS` in
review. Both are defined identities in the bound
`STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1` over evidence the bundle already
carries, and all 36 real persisted measurements satisfy them. Separately, the
eight hash-bound Wilson boundary vectors were asserted but never re-evaluated,
so substituting the continuity-corrected limit flipped `0/16` while both hashes
stayed identical; they are now enforced through `certify_pair` itself before
any contract is built. A P3 closed two blocks that accepted unknown fields the
contract declares `REFUSED`. Every fix adds only refusals: the state space, the
one `PASS` state, the precedence, every threshold and the pair universes are
unchanged. 312 focused tests, 4146 in the full suite.

Two findings are recorded rather than fixed. Enabling the one sealed execution
requires a new validator hash, because `sealed_execution_authorized` sits inside
the hashed contract and `validate_v3_candidate` refuses `SEALED_EXECUTION`
unconditionally -- so the certified contract cannot be the executing one, and
the next task must ship a minimal `_V2` whose only semantic delta is the
authorization flag, reviewed on its own (P2). `restore_validator_definition`
claims to refuse "every meaningful tamper" but a re-digested tamper of the
limit, quantile, pair set or a Tier-4 threshold passes it;
`verify_validator_artifacts` is the complete check and the runtime never trusts
the persisted file, so no verdict is reachable through it (P3).

The accepted risks are preserved: the guard still returns
`GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE` on a 2/28 provider pair, so a sealed
sample resembling 2023-2025 returns an unresolved result for any candidate
however good. The candidate was never constructed or evaluated and the sealed
sample was neither collected nor opened at any point in the review. The next
task is `PREPARE_AND_EXECUTE_ONE_SHOT_V3_SEALED_VALIDATION`; certification
authorises preparing the one-shot execution mechanism and no further evidence
round is authorised.

`BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2` under
`btc_predictor/research/reference_composite_v3_sealed_executor.py`, with its
contract at `research_artifacts/btc019_v3_sealed_executor/`, is that mechanism.
It hashes to
`e21e6ad8e8a40e4ee0763d7f3176efc168dacc0701f8e1199ae8a25ee5f9d784` and exists
because the certified V1 cannot be the executing validator: its own review
recorded that `sealed_execution_authorized` sits inside the hashed contract, so
enabling the one opening necessarily moves the hash. V1 is not mutated --- it is
byte-identical, still hashes to `8e6254e0...c7ffe7` and still refuses
`SEALED_EXECUTION`. V2 derives its contract from the parent's at build time,
applies one enumerated delta, computes the actual field-level diff and refuses
`REFUSE_TO_FREEZE_EXECUTING_VALIDATOR` if the two disagree in either direction,
so drift cannot reach the hash. The one verdict-affecting change is
`sealed_execution_authorized`, false to true; the rest of the delta is the
record and contract schema versions and four new blocks carrying the one-shot
controls. All 23 other top-level blocks are byte-identical, and every
verdict-affecting computation is the parent's own function object, asserted by
identity rather than by resemblance. A 27-bundle differential corpus spanning
all three verdicts shows the two records differ in four changed and three added
fields and in nothing else, all 648 legal hard states compose identically with
exactly one `PASS`, and all eight Wilson boundaries still resolve uncorrected
through `certify_pair` itself.

Authorization is necessary and never sufficient. Every control-plane operation
now holds `fcntl.flock(LOCK_EX)` on the fixed executor lock while it reads,
validates and atomically persists the path-bound authority. Exact histories,
state-earned fields, artifact/digest checkpoints and canonical artifacts are
verified independently of the record's self-hash. The canonical manifest is
persisted only after every fixed raw provider file has been securely reopened,
schema-checked, byte-hashed and reconciled to its technical metadata. Normal
`execute_sealed_validation` accepts only `COLLECTED_FROZEN`, durably persists
`EXECUTION_STARTED` before its first raw read, revalidates the persisted
manifest and raw bytes, and invokes evidence construction only beneath that
consumed authority. Public in-memory validation is synthetic-only and cannot
enter sealed mode.

`EXECUTION_STARTED` permanently consumes the one-shot authority. It cannot be
retried even after a crash. Evidence and result artifacts are immutable,
atomically published and fsynced before the authority reaches `FINALIZED`.
Recovery never reopens raw data or reruns evidence construction: it reports
`EXECUTION_INTERRUPTED_NO_RESULT` when no durable result exists, or verifies an
already-published evidence/result pair and finalizes it. Finalized restore
replays certified V1 validation over the persisted evidence only and refuses a
re-digested semantic result tamper. `PASS`, `FAIL` and
`UNDEFINED_INSUFFICIENT_EVIDENCE` remain the only scientific verdicts;
operational interruption and integrity refusal stay separate.

Nothing was collected, opened or evaluated. No live authorization record exists
--- the one-shot clock starts in the execution task, not this one --- the
candidate was never constructed, and beyond per-run watchers a suite-level
regression re-runs the whole module under `sys.addaudithook` and proves that of
the thousands of opens the interpreter performs, none is under `data/` and none
names a 2015-2019 path, with a positive control so an empty result cannot mean
"saw nothing". 18 semantic tampers of the module moved the hash or were
refused, 5 parent-semantic tampers refuse the successor outright, and 12
persisted-contract tampers are caught. Outcome:
`SEALED_EXECUTOR_READY_FOR_INDEPENDENT_REVIEW`. The next task is
`FORMAL_XHIGH_REVIEW_ONE_SHOT_V3_SEALED_EXECUTOR`; once it passes the contract
is frozen --- no edit, no rebuild, no new hash --- and the one permitted run must
bind exactly the reviewed V2 hash.

The formal independent xHigh review of that executing validator failed with
classification `SEALED_EXECUTOR_REQUIRES_FIX`. The V3, certified V1 and claimed
V2 hashes all recompute, V1 and V3 remain byte-identical, the complete 648-state
composition has exactly one `PASS`, the 27 real-shaped synthetic bundles retain
full V1/V2 verdict parity, and the eight Wilson boundaries remain unchanged.
Certified V1 semantics are therefore not reopened. The executor control plane
is invalid: `validate_v3_candidate` accepts sealed mode with a forged in-memory
three-field authorization; a self-rehashed prepared record can jump to
`EXECUTION_STARTED` without a frozen manifest because state history and
state-earned fields are not cross-checked; `record_frozen_collection_manifest`
accepts nonexistent raw files and does not persist the manifest; a crash before
the final authorization write leaves `EXECUTION_STARTED` reusable; and two
concurrent `begin_sealed_execution` calls both succeed because the JSON
read-modify-write has no exclusive lock. The result itself is returned but not
durably persisted, so no deterministic finalized-result restore exists. The
review made no executor, V1 or V3 code change. The sealed sample remains
uncollected and unopened, and `EXECUTE_ONE_SHOT_V3_SEALED_VALIDATION` is not
authorized until a corrected executing contract receives a new hash and passes
the repeated formal review.

Correction implementation `9ca2b5bfdb129441d0b6857b496b526f7d5685df`
closes those four executor-control families with a path-bound canonical root,
real cross-process lock, atomic/fsynced state and artifact publication, exact
state/artifact checkpoints, persisted-manifest and raw-byte revalidation,
executor-owned sealed capability, permanent consumption at
`EXECUTION_STARTED`, immutable evidence/result artifacts, and recovery that
never reopens raw data. The corrected V2 definition hashes to
`49abd68975217bb78affc0b6bd6f5e2ba066e84ec745dc5b9bdf82d3bea99729` and
records `e21e6ad8...9d784` plus review commit `daa6647...8fd` as failed
lineage. 236 focused tests, 950 focused-plus-relevant regressions and the full
4382-test Python 3.12 suite pass. This is
`CORRECTED_SEALED_EXECUTOR_READY_FOR_REPEAT_XHIGH_REVIEW`, not certification:
sealed collection and opening remain refused until the repeat review passes.

That repeat independent xHigh review is now complete and the corrected hash
also fails, with classification `SEALED_EXECUTOR_REQUIRES_FIX`. V3, certified
V1 and corrected V2 independently recompute to `4232e886...bf71a`,
`8e6254e0...c7ffe7` and `49abd689...99729`; V3 and V1 are unchanged, and the
648-state, 27-bundle, 20-malformed-bundle, eight-Wilson-boundary, 33-gate and
seven-hard-requirement demonstrations retain exact V1/V2 scientific parity.
The state machine, exact artifact checkpoints, cross-process lock, atomic
persistence, no-retry rule, crash recovery and result replay also pass. The
failure is confined to two live provenance boundaries.

First, `execute_sealed_validation` accepts an arbitrary caller-supplied Python
callable as `evidence_builder`. The callable may ignore the verified raw
collection and return a prebuilt internally valid bundle; the executor trusts
the bundle's claim that its builder version is
`BTC019_V3_SEALED_EVIDENCE_BUILDER_V1`. In a synthetic run, three raw files with
two rows each produced `PASS` from an unrelated prebuilt bundle declaring a
40-event denominator. No module/function identity or implementation hash is
bound by the V2 contract. Second, live execution validates the canonical
manifest while reading `COLLECTED_FROZEN`, persists `EXECUTION_STARTED`, then
reloads the manifest without validating its self-digest or comparing the
reloaded content to the authority-bound digest. A deterministic synthetic
mutation at that boundary replaced a raw file and its manifest row, retained
the old manifest digest, delivered the changed bytes to the builder and still
produced `PASS` under the old frozen-manifest identity.

No review fix was made: the repository has no trusted live evidence-builder
owner to bind, so inventing its complete raw-to-evidence and manual-review
boundary is not a uniquely correct local review edit. The smallest correction
is executor-only: remove the caller-supplied live callable; implement one fixed
owner that deterministically consumes `VerifiedRawCollection`; bind its exact
module/function identity and definition or implementation hash into the V2
contract, evidence artifact and runtime check; and validate the exact manifest
snapshot used for raw reads against the authority digest after
`EXECUTION_STARTED` (or carry forward the already validated immutable snapshot)
before opening any raw file. The correction must issue a new V2 hash and receive
another formal xHigh review. No V1 or V3 semantic may move. The actual sealed
sample remains uncollected and unopened, the candidate remains unevaluated, and
`EXECUTE_ONE_SHOT_V3_SEALED_VALIDATION` is not authorized.

Provenance correction implementation
`c6ae1b30c10562e991cf292fd668d9bd1084bc39` closes both remaining findings
without changing V3 or certified V1. Live `execute_sealed_validation` no longer
has a caller-supplied builder parameter. The new repository owner
`btc_predictor.research.reference_composite_v3_sealed_evidence.build_sealed_evidence`
consumes the executor's exact `VerifiedRawCollection`; its module, function,
version and transitive source definition hash `d8ff41f7...eabb85` are checked at
runtime and bound into the V2 contract and durable evidence artifact. After
`EXECUTION_STARTED` is durable and before any raw open, the executor reloads the
canonical persisted manifest, validates its exact schema, self-digest and all
authority bindings, compares its recomputed digest to
`authority.collection_manifest_digest`, and passes that validated snapshot to
raw verification. The new V2 definition hash is `7fda8ac3...ad8be6`; the exact
`49abd689...99729` artifacts are retained beneath a hash-keyed history directory
and both failed predecessors remain in lineage. The 253 focused executor tests,
967 relevant BTC-019/price-reference regressions and complete 4399-test Python
3.12.14 suite pass with `RuntimeWarning` as an error. Classification:
`V2_EXECUTION_PROVENANCE_READY_FOR_REPEAT_XHIGH_REVIEW`, not certification.
The actual sealed sample remains uncollected and unopened, the candidate remains
unevaluated, and collection/execution remain refused pending that review.

The repeat formal GPT-5.6 Sol xHigh review of `7fda8ac3...ad8be6` is now
complete with result `FAIL — SEALED EVIDENCE BUILDER INCOMPLETE` and execution
classification `SEALED_EXECUTOR_REQUIRES_FIX`. The executor control plane passes:
the V3, certified V1, V2 and builder-definition hashes independently recompute;
the post-start four-way manifest mutation tests refuse before any raw read or
builder call; state transitions, permanent consumption, process races, crash
recovery, durable evidence/result checkpoints and finalized V1 replay pass. The
253 focused tests, 967 relevant tests and complete 4399-test Python 3.12.14 suite
pass with `RuntimeWarning` as an error. No actual sealed-sample byte was
collected, opened or inspected.

The live scientific path nevertheless cannot return `PASS`. The fixed builder
emits only 15 of certified V1's 33 inherited measurements and intentionally
omits 18; 16 omissions are hard gates. A complete synthetic three-provider
hourly fixture over the sealed window therefore returns
`UNDEFINED_INSUFFICIENT_EVIDENCE` with those 16 blocking gates even when every
emitted inherited metric passes. A sparse synthetic fixture can still return
`FAIL`, so execution is not constant-result in the narrow sense, but no raw
input can make the live path pass. There is no execution-time source or merge
path for the missing evidence, including 90 prospective live-shadow days,
strategy/trade comparisons, stop-path preservation and deterministic rerun
evidence.

Four additional P1 defects independently prevent certification. The builder's
interpolated ATR p95 differs from the authoritative nearest-rank BTC-019 owner
and flips the hard gate on synthetic boundary vectors. Its claimed transitive
definition hash omits material runtime owners including `quant.rolling`,
`quant.arrays`, `levels.swing`, `levels.breakout`, `price_source_policy` and
`structural_gate_denominator_resolution`; a synthetic monkeypatch changed ATR
evidence while both recorded hashes and runtime verification stayed unchanged.
The live candidate and percentile arithmetic depend on the process-global
Decimal context. Finally, daily/weekly construction uses the generic complete-
bucket-only owner, discards the V2-required incomplete-bucket metadata and then
records `silent_incomplete_bucket_omission_count = 0` without evidence.

No review fix was made. Supplying the 16 missing hard-gate evidence sources and
their sequencing crosses the review boundary: some require pre-existing
prospective or strategy evidence and the repository defines no authorized
execution-time owner. The correction must define and validate that evidence
boundary, use the frozen statistic owner, make arithmetic context-independent,
preserve V2 bucket-quality records and bind the exact transitive implementation.
It must issue a new V2 and builder hash and receive another independent xHigh
review. No V1/V3 methodology or threshold change is authorized. The actual
sealed sample remains uncollected and unopened, the candidate remains
unevaluated, and neither another evidence round nor
`EXECUTE_ONE_SHOT_V3_SEALED_VALIDATION` is authorized.

Bounded V4 stage-correction implementation
`0143cbf2251b3f099dccf05453538e043700c9d9` creates
`BTC_REFERENCE_COMPOSITE_V4` at
`670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501`
and its successor two-stage validator at
`8cf091fb8c0374f876dc54237d0226cea3f11a3d7554f6abae5ba5c1df498c28`.
The persisted 33-gate census proves that `live_shadow_days` is the only
prospective-only gate and the only stage relocation. Its hard minimum remains
exactly 90 days, all other thresholds/directions/hard-soft roles remain byte-
derived from frozen V3/V2 authority, Stage A contains 28 hard and four soft
historical gates, and Stage B contains only the unchanged live-shadow gate.
Synthetic validator fixtures reach PASS, FAIL and
`UNDEFINED_INSUFFICIENT_EVIDENCE` without consulting live shadow.

The same audit refuses a live V4 executor. Ten Stage-A hard gates do not have
exactly one conforming executable measurement owner: cross-market-confirmed
stop preservation, deterministic rerun, gap-through stop consensus, isolated-
venue stop suppression, provenance completeness, and the five reserved
Phase-1 regime/risk/setup/trade consequence rates. Related development or
Phase-1 components exist, but authority does not freeze the required sealed
event/decision universe, complete non-price inputs, comparison reference and
denominator; the failed builder also hardcodes provenance and never performs a
real rerun. Inventing those contracts would be a new methodology/evidence
decision, not implementation completeness. Therefore no new builder or
executor hash is issued and classification is
`V4_EVIDENCE_PIPELINE_INCOMPLETE`. Twenty focused tests, 2,003 relevant
regressions and the complete 4,419-test Python 3.12.14 suite pass with
`RuntimeWarning` as an error; compileall and scoped diff checks pass. The
actual sealed sample remains uncollected and unopened and the candidate remains
unevaluated.

`PROSPECTIVE_INTEGRATION_CORPUS_V1` under
`prospective_evidence/prospective_integration_corpus_v1/` and
`btc_predictor/research/prospective_integration_corpus.py` is the first task of
the new post-Phase-1 workstream
[EPIC X](execution/post_phase1_prospective_integration_evidence_v1.md). It does
not repair BTC-019 and is not `BTC_REFERENCE_COMPOSITE_V6`: no frozen V3, V4,
V5 or certified V1 byte moves, and the eight thresholds, directions, hard roles
and stated intents are imported verbatim from `V2_APPROVAL_GATES` and
re-verified on every build, so the persisted semantic diff proves zero
threshold, direction, hard-role and metric-intent changes. What it supplies is
what the record lacked: a scheduled decision universe at two cadences on the
existing canonical sessions, with both decision instants at bar close plus the
reference-composite owner's own five-minute delay and availability under the
frozen `AVAILABLE_AT_LTE_DECISION_TIME_V1`; a point-in-time input snapshot
bound to the frozen BTC-048 feature contract's own families and their existing
PIT raw tables; two deterministic portfolio tracks from one frozen flat
`1,000,000` NAV state, sharing every exogenous input except the reference under
test, diverging naturally and never resynchronized; and a mechanical stop-event
taxonomy that replaces `KNOWN_DEVELOPMENT_EVENTS` so no timestamp is
hand-selected. Every universe predicate reads inputs and per-track state only,
so no timestamp can enter or leave a denominator because the two tracks
agreed. A zero denominator is `UNDEFINED_INSUFFICIENT_EVIDENCE`, never a PASS
and never `0`. The protocol hash is
`aaa05c7288971ecb60e331c750fa728db13a3f2046cd597ffe4957a2f3d37326` and binds
nine child contract hashes; 86 focused tests cover gate parity, universe
determinism, PIT refusal, duplicate refusal, the three event classifications,
divergence, hash tamper and ordering/seed/cwd/Decimal-context invariance, and a
suite-level `sys.addaudithook` run proves the module opens nothing under
`data/` and nothing on a 2015-2019 path.

Three things are deliberately not decided there. Per-metric certification
minimums are marked
`REPORTABLE_BUT_NOT_CERTIFIABLE_WITHOUT_SEPARATE_PRE_DATA_GOVERNANCE` and
deferred to `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1`,
because choosing a rate gate's minimum n is its own pre-data governance task in
this repository and `PER_PAIR_WILSON_UPPER_BOUND_V1` controls only the V3
structural scope; no calendar minimum is imported from Stage-C's
`live_shadow_days >= 90`. The `CONTROL_REFERENCE` and `CANDIDATE_REFERENCE`
identities are not named, because no production candidate legitimately exists,
so the raw corpus stays candidate-neutral and a separately frozen evaluation
contract supplies them later without rewriting one historical observation. And
the PostgreSQL schema is a complete contract rather than a migration, so this
task cannot accidentally create a collection target. One repository gap is
recorded rather than papered over: `CVD_SPREAD` consumes
`features.flow.CvdObservation`, which has no raw PIT table and no collector, so
its capture is declared and marked
`REQUIRES_NEW_COLLECTOR_IN_FIRST_COLLECTION_TICKET`. A second is why the
artifacts sit under `prospective_evidence/` rather than `research_artifacts/`:
V5's terminal assessment hashes an inventory of every JSON under `data/` and
`research_artifacts/`, so persisting these ten there recomputed V5 to
`c67fd3a4...456c9d` instead of `95e43ee1...775a89`. V5 is immutable, so the new
program stays outside that census and a regression pins V5's recomputation to
its frozen hash; V5's terminal classification is unaffected either way.
Classification:
`PROSPECTIVE_INTEGRATION_CORPUS_V1_READY_FOR_XHIGH_REVIEW`. Collection is not
authorized, no qualifying observation was collected, no real Stage-B outcome
was evaluated, EPIC T was not touched, and the BTC-019 sealed sample stays
uncollected and unopened with no automatic dependency that would ever open it.

## Important Unresolved Decisions

- Production canonical BTC reference selection remains unresolved under
  BTC-019, but the research branch that was blocking it has now converged. The
  calendar-contiguity contract, the re-measurement of the already-inspected
  2019-2022 and 2023-2025 samples, the denominator declaration, the pre-sealed
  threshold calibration and the final gate-architecture convergence are all
  done, and `BTC_REFERENCE_COMPOSITE_V3` is frozen at
  `4232e886...bf71a` and has passed its independent xHigh review. So has the
  hash-bound validator, now at `8e6254e0...c7ffe7`. What is outstanding is no
  longer evidence, semantics, or the certified validator. The one-shot sealed
  executor `BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2` was corrected again at
  `7fda8ac3...ad8be6` after `49abd689...99729` and `e21e6ad8...9d784` failed.
  Its unrestricted live-builder boundary and post-start manifest/raw TOCTOU gap
  are closed, but repeat formal xHigh review rejects the new hash because the
  live builder cannot source 16 hard gates and has four additional scientific
  provenance/semantics defects. V4 resolves only the stage contradiction by
  moving the still-mandatory `live_shadow_days >= 90` gate after historical
  approval. Its complete ownership invariant then refuses certification because
  ten remaining historical hard gates lack one conforming owner. Those missing
  measurement contracts must be authoritatively resolved before a new builder,
  executor hash or repeat review is possible. Nothing about the candidate has
  been decided --- `MEDIAN_OHLC_V2`
  has still never been constructed or measured against any gate, so its V3
  outcome is unknown, and the 2015-07-20..2019-11-30 sample is still sealed.
  The absolute materiality limit of `0.20` is argued from consequence --- one
  in five economically consequential weekly structural events --- and not
  fitted; the review classified it `DEFENSIBLE_PHASE1_GOVERNANCE` and found no
  leakage path, since the limit is a module constant no observed rate can move
  and the realism check runs after it and may only veto the architecture. It
  happens to coincide with the number the discredited relative objective
  produced; the derivation and the coincidence are recorded here and against
  the ticket, though not in the frozen artifact itself. Two residual
  governance risks are now recorded rather than open. The Wilson bound treats
  one pair's own comparable events as exchangeable, which weekly structure is
  not, and the frozen disclosure's claim that the violation is conservative is
  wrong in direction: clustering widens the count's distribution in both
  tails, so a pair whose true rate is `0.30` certifies with probability 0.115
  at n=30 under an intra-cluster correlation of 0.2 against 0.0003 under
  exchangeability. It is not verdict-affecting --- the rule stays deterministic
  and the assumption-free point-rate test is a floor the bound only tightens
  --- and it is classified `ACCEPTABLE_WITH_EXPLICIT_LIMITATION` for Phase 1.
  And the transfer guard is `GUARD_UNDEFINED_INSUFFICIENT_EVIDENCE` on the
  2023-2025 development sample, where `bitfinex_vs_bitstamp` is 2/28 with a
  bound of 0.2265, so a sealed sample resembling it returns an unresolved
  result for any candidate however good. That is fail-closed and correct, but
  the sample opens once. The demotions themselves rest on an ordering that
  holds across the whole assumption neighbourhood: `structural_state` can carry
  a hard gate from `0.15`, `breakout` only from `0.30`, `reclaim` nowhere.
- The eight prospective Stage-B measurements are defined but not yet
  certifiable. `PROSPECTIVE_INTEGRATION_CORPUS_V1` freezes each one's universe,
  numerator, denominator, owner and PIT inputs without moving a threshold, but
  the minimum denominator that would let any of them certify is a separate
  pre-data governance decision that has not been made. Until
  `PROSPECTIVE_INTEGRATION_EVIDENCE_SUFFICIENCY_GOVERNANCE_V1` exists, Stage-B
  collection has no predeclared terminating condition and Stage-B results are
  reportable but not certifiable. Two further inputs are outstanding for the
  first collection ticket: the `CONTROL_REFERENCE`/`CANDIDATE_REFERENCE`
  identities, which need their own frozen evaluation contract, and a raw PIT
  capture for `CvdObservation`, without which `CVD_SPREAD` cannot be reproduced
  point-in-time.
- BTC-223 surfaced two paper-execution composition gaps. The BTC-165 half is
  now closed: the EPIC Q audit made the position walk exact rational
  arithmetic, so an add-then-trim trade on a non-terminating BTC-155 tranche
  quantity accounts normally, and the BTC-223 and BTC-224 tests that pinned the
  refusal are now positive regressions. Still open with its owner: the BTC-180
  discretionary-exit boundary shapes no `paper_orders` row.
- The EPIC E/E2 integration audit left three non-blocking items with their own
  owners. `atr_from_daily_bars` (EPIC O) is now closed: it delegates to the
  BTC-041 bar boundary. Still open with their owners:
  `realized_volatility_from_daily_bars` (EPIC I) reads a gapped daily series as
  contiguous and BTC-048 feature/target matrices serialize but have no restore
  or tamper-validation path. The three BTC-019 research helpers that restate the
  true-range formula are now measured rather than only noted: 348 published
  observations across the two collected samples cross a session the BTC-041
  owner leaves undefined, and they are preserved deliberately so the frozen
  BTC-019 artifacts stay reproducible. `detect_weekly_swing_levels` (EPIC E) has
  the same row-versus-session reading and is still pinned by test rather than
  changed; BTC-019 research now reads around it through the
  `CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` adapter, but a production swing-gap
  policy remains a strategy-semantics decision for its own owner.
- The EPIC P integration audit left one non-blocking item with a strategy
  owner: rulebook 24 gives STRESS / CROWDING / EUPHORIA the shared effect
  `NO ADDING`, and BTC-150 makes `DEFENSIVE` the state that enforces it, but no
  module emits `DEFEND` and BTC-154 has no hard-flag requirement, so the
  composed chain permits an add while CROWDING is active. Pinned by test rather
  than closed in review, because choosing the mapping is a strategy decision.
  BTC-152 through BTC-158 also still have no production consumer; only BTC-150
  and BTC-155 are reached from BTC-180.
- The EPIC S integration audit left two non-blocking items. BTC-180 treats
  `ingested_at` as per-bar live availability, but `derive_ohlcv_bars` and
  `build_canonical_market_bars` stamp one ingestion time on a whole backfill,
  so a dataset built the repository's own way replays with no executable
  decision at all. The engine now says so plainly, and BTC-182 and BTC-185
  already carry the empty result up as `WALK_FORWARD_NO_TRADES` and
  `THRESHOLD_SWEEP_NO_TRADES`, but nothing yet produces backtest bars carrying
  live availability; BTC-224 synthesises it. Separately, a fill on a bar whose
  ingestion lags past the following bar's start would stamp the lifecycle ahead
  of bars the run still replays; BTC-162 refuses it, which is fail-closed but
  attributes the cause to the stop owner, and choosing between refusing the
  execution and refusing the dataset is a BTC-180 policy decision. Both are
  pinned by test.
- The EPIC S2 integration audit left three non-blocking items. BTC-186's
  frozen fifth candidate binds `FUNDING_RESET`, `OI_DELEVERAGING` and
  `FLOW_IMPROVEMENT`, which the versioned BTC-048 feature contract does not
  declare and no module produces, so the epic's own default candidate set
  fails closed on the repository's own feature matrix; the binding is
  deliberate, because reinterpreting the existing health features would invent
  their lag and direction semantics. BTC-186, BTC-187 and BTC-188 record
  BTC-193 as their required promotion boundary, but the BTC-193 packet accepts
  only BTC-182, BTC-185, BTC-189 and BTC-192 evidence, matching its own
  declared dependencies, so that boundary is presently a statement rather than
  an enforced gate for those three. BTC-189's two bucket cutters and its four
  statistics helpers restate BTC-186's; the formulas agree and are pinned by
  test.
- The EPIC T integration audit left five non-blocking items with their owners.
  BTC-190 is the one EPIC T output BTC-193 cannot accept, so the
  `BTC_193_REQUIRED_V1` boundary it persists is a statement rather than an
  enforced gate; BTC-191's is enforced transitively through the BTC-192 paper
  comparison. Relatedly, BTC-190 is the epic's only evidence that a campaign's
  traded dates are all of them, but BTC-192 paper scope stays caller-declared,
  so a paper arm may be an unrepresentative subset of the trades its scope
  covers; binding the two is a versioned BTC-192 policy decision. BTC-165's
  `r_multiple` is the one accounting output resolved in the caller's ambient
  decimal context, so a BTC-191 dataset built under a narrowed precision
  carries a differently rounded R -- every other outcome is exact and no
  EPIC T restore path re-executes the accounting, but pinning that division is
  a repository-wide accounting convention change. BTC-193's packet reason codes
  are a fixed tuple that asserts `EVIDENCE_CHAIN_COMPLETE` even when both
  comparisons hold zero trades, though the embedded BTC-192 records still carry
  `STRATEGY_COMPARISON_NO_TRADES`; and BTC-193 binds evidence to the candidate
  identity without requiring its stages to cover comparable periods or bars.
  The same ambient-context `abs` the audit fixed in BTC-192 also stands in
  `reporting/model_human_comparison.py` and `backtest/setup_performance.py`,
  with their own epics' owners.
- The EPIC Q integration audit left two non-blocking items with their owners.
  BTC-163 adds and BTC-164 trims have no restore/replay function, unlike
  BTC-161, BTC-162 and BTC-180, because their records embed BTC-154, BTC-155
  and BTC-157 decision objects that have no restore path of their own; a
  persisted ADD or TRIM order row therefore has no tamper validator, though the
  trade's economics remain replayable through BTC-165. BTC-163 also has no
  canonical `add_execution_for_position` the way BTC-162 has
  `stop_execution_for_position`, so an add's `average_entry_price` is
  caller-supplied rather than read from the BTC-150 ledger.
- The EPIC O integration audit left three non-blocking items. BTC-141 still
  carries its ATR multiplier and window as module literals rather than reading
  the versioned `stop_buffers` config the way BTC-144 reads `risk.schedule`;
  they are pinned equal by test, and `stop_buffers.minimum_level_noise_multiplier`
  is consumed nowhere. `entry_thresholds.short_valid_trade_min` duplicates
  `setup_requirements.bearish_distribution.entry_conviction_min` and is
  likewise unused; only the setup-requirements copy is enforced. BTC-140
  through BTC-143 have no production consumer yet -- the backtest engine takes
  a ready-made BTC-142 stop from its intent -- so the invalidation-to-stop
  chain is exercised only by tests.

## Important Active Invariants

- Every decision and research row must remain point-in-time correct.
- Missing numerical inputs are surfaced; they are never silently zero-filled.
- Shared quant, risk, execution, and accounting owners must be reused across
  advisory, paper-trading, and backtesting paths.
- Never average down; stops never widen; aggregate risk-at-stop remains bounded.
- Strategy, configuration, policy, and provenance versions remain persisted for
  deterministic replay.

## Update Policy

When implementation or review materially changes project state, update only
the affected snapshot fields above. Detailed ticket truth stays in Structured
Tickets v2.6; this file must not become a second roadmap or ticket ledger.
