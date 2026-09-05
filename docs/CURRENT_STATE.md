# Current Project State

> [!NOTE]
> This file is a compact project handoff snapshot.
>
> It is NOT an independent source of strategy or ticket authority.
>
> If it disagrees with the authoritative Structured Tickets document or an
> applicable policy, the authoritative document wins and this file must be
> corrected.

## Snapshot

- **Last updated:** 2026-09-05
- **Current phase:** Phase 1, EPIC W testing is implemented; every Phase-1
  implementation ticket except BTC-019 is now DONE. BTC-019's successor
  reference protocol is frozen and awaiting its independent review
- **Authoritative execution roadmap:** [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
- **Current implementation frontier:** None; no Phase-1 implementation ticket
  remains open
- **Last completed ticket:** BTC-224, golden historical scenarios. Its
  required independent xHigh review has now passed with one review fix, as
  have BTC-221's and BTC-222's; no Phase-1 ticket review remains outstanding
- **Last epic integration audit:** EPIC T, research and learning loop
  (2026-09-04), PASS WITH NON-BLOCKING FINDINGS after two P2 review fixes.
  EPIC S2 was audited earlier the same day; EPIC S, EPIC Q, EPIC P, EPIC O,
  EPIC E and EPIC E2 were audited on 2026-09-03
- **Current IN_PROGRESS ticket:** BTC-019
- **Current BLOCKED tickets:** None recorded in Structured Tickets v2.6
- **Next dependency-satisfied ticket:** None. BTC-019 is the only remaining
  Phase-1 work
- **Other ready tickets:** None
- **Latest verified test baseline:** 3830 passed with Python 3.12.14 on 2026-09-05
- **Last relevant implementation/review commit:** the bounded
  `BTC_REFERENCE_COMPOSITE_V3_GATE_ARCHITECTURE_CONVERGENCE_V1` task. Outcome:
  `V3_FROZEN_READY_FOR_VALIDATOR`. `BTC_REFERENCE_COMPOSITE_V3` is now a frozen
  research protocol with its own definition hash `4232e886...bf71a`; six
  structural rate gates, five hard, become one hard gate, one soft gate and
  four diagnostics, on an absolute economic materiality limit with no
  independence assumption left in the approval rule. Its own required
  independent xHigh review is outstanding, and until it passes no validator may
  be built

## Price-Reference State

```text
BTC-019 = IN_PROGRESS
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

## Important Unresolved Decisions

- Production canonical BTC reference selection remains unresolved under
  BTC-019, but the research branch that was blocking it has now converged. The
  calendar-contiguity contract, the re-measurement of the already-inspected
  2019-2022 and 2023-2025 samples, the denominator declaration, the pre-sealed
  threshold calibration and the final gate-architecture convergence are all
  done, and `BTC_REFERENCE_COMPOSITE_V3` is frozen at
  `4232e886...bf71a`. What is outstanding is no longer evidence or semantics: it
  is the independent xHigh review of that frozen definition. Nothing about the
  candidate has been decided --- `MEDIAN_OHLC_V2` has still never been
  constructed or measured against any gate, so its V3 outcome is unknown, and
  the 2015-07-20..2019-11-30 sample is still sealed. Two judgements in the
  frozen protocol are governance rather than measurement and are the right
  place for a reviewer to push. The absolute materiality limit of `0.20` is
  argued from consequence --- one in five economically consequential weekly
  structural events --- and not fitted; it happens to coincide with the number
  the discredited relative objective produced, and both the derivation and the
  coincidence are recorded. And the Wilson bound still treats one pair's own
  comparable events as exchangeable, which weekly structure is not; the
  disclosure notes that clustering pushes a maximum gate towards insufficient
  or failure rather than towards a pass, so the violation is conservative for
  approval, but it is an assumption and not a proof. The demotions themselves
  rest on an ordering that holds across the whole assumption neighbourhood:
  `structural_state` can carry a hard gate from `0.15`, `breakout` only from
  `0.30`, `reclaim` nowhere.
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
