# EPIC Y — First Research Backtest (Non-Certifying)

Workstream authority for the first real-data backtest of the frozen Phase-1
champion. This document controls EPIC Y (`RBT-xxx`) ticket status, dependencies
and acceptance criteria. It is **not** Phase-1 execution authority: [Structured
Tickets v2.6](bitcoin_swing_predictor_structured_tickets_v2_6.md) keeps that role
and is not modified by this workstream. It is **not** EPIC X or BTC-019 authority.

Governing policy: [`RESEARCH_BACKTEST_POLICY_V2`](../policies/research_backtest_policy_v2.md),
which superseded V1 before any run by naming the market-closure owner.
Every rule in that policy binds every ticket below.

## Why this workstream exists

Phase-1 built an event-driven backtester (BTC-180..185), but it has never
replayed real market data. Three concrete gaps stand in the way, independent of
any price-source question:

1. **No replay availability.** Backfilled rows carry a single bulk
   `ingested_at`, and the engine treats that as live availability. A dataset
   built the repository's own way therefore replays with no executable decision
   (EPIC S audit). Only the BTC-224 golden scenarios synthesize availability.
2. **No champion composer.** No production code turns point-in-time inputs into
   a `BacktestIntent`. The golden scenarios script their decisions by hand, and
   BTC-140..143 and BTC-152..158 have no production consumer (EPIC O and EPIC P
   audits).
3. **No historical input dataset** covering ETF flows and derivatives with
   modelled availability.

On top of that, no canonical price reference is approved. The policy resolves
this by running each required venue separately and declaring every output
non-certifying.

## Boundaries

- EPIC X, BTC-019 and EPIC T are untouched. The sealed sample stays unopened:
  EPIC Y reads nothing before 2020-01-01.
- EPIC Y's only dependency on EPIC X output is the reviewed
  `US_EQUITY_MARKET_CLOSURE_TABLE_V1` (`POSTP1-001V2A-T1`, review
  `POSTP1-002V2A-T1`). It is passed to the flow owner's existing
  `market_holidays` parameter.
- **Additive-only (policy §9).** No EPIC Y ticket edits a file bound by an EPIC X
  frozen candidate or certified authority, or any file under `data/` or
  `research_artifacts/`. EPIC Y code lives in the new package
  `btc_predictor/research_backtest/` and new `btc_predictor/tests/test_research_backtest_*.py`
  modules. If a ticket finds a need that can only be met by editing a bound
  module, it stops and records a cross-workstream blocker.
- Every implementation ticket's validation includes:
  - its focused suite;
  - the BTC-180..185 and BTC-220..224 regressions;
  - the V5 recomputation regression (`95e43ee1...775a89` unchanged);
  - the current EPIC X candidate's focused suite, unchanged;
  - `compileall` and `git diff --check`.
- Reviews are independent xHigh **ticket** reviews under
  [`prompts/review_ticket.md`](../../prompts/review_ticket.md). EPIC Y does not use
  the EPIC X exact-hash proof-architecture review model.
- Data tickets (RBT-002, RBT-003, RBT-008) need an environment with the research
  PostgreSQL database and outbound provider access. Code tickets need neither.

## Critical path

```text
code path:  RBT-001 ─┬──────────────────────────┐
            RBT-004 ─┴─ RBT-005 ────────────────┤
data path:  RBT-002 ─── RBT-003 (needs RBT-001) ┤
                                                ▼
                         RBT-006 freeze + preregistration
                                                ▼
                         RBT-007 first research backtest
                                                ▼  (review PASS)
                         RBT-008 holdout, opened once
```

## RBT-001 — `BUILD_HISTORICAL_REPLAY_INPUTS_V1`

**Status:** `NOT STARTED / DEPENDENCY-SATISFIED`
**Dependencies:** none
**Implementation effort:** xHigh
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/replay_inputs.py` (new)

Implement `HISTORICAL_REPLAY_AVAILABILITY_V1` (policy §4) as a pure,
deterministic builder. It turns persisted raw records, or equivalent fixtures,
into derived replay inputs plus a content-addressed dataset manifest.

Acceptance criteria:

- Applies the policy §4 availability table exactly. Modelled availability is
  never earlier than the observation close. ETF flows use `T+2 00:00` UTC, or
  the source's later publication/revision time when supplied. Records without
  revision history are labelled `REVISION_HISTORY_UNAVAILABLE`.
- The engine's inputs: derived replay `OhlcvBar` objects carry modelled
  availability in `ingested_at`, and the manifest records every bar's raw
  ingestion time beside it. No raw row is modified.
- One venue per bar series. No splicing and no fallback. Gaps are preserved and
  counted.
- Refuses any record before `2020-01-01 00:00` UTC.
- Windows form a closed enumeration. The `HOLDOUT` window is refused by a guard
  that only RBT-008 may lift, in its own reviewed commit.
- The manifest records the policy versions, venue, window, per-input content
  digests and both timestamps. It is byte-identical under `PYTHONHASHSEED`
  0/1/8675309, input reordering and an alternate cwd.
- **Control reproduced:** a real-shaped bulk-backfilled fixture replayed
  through `run_backtest` as-is yields no executable decision, while the same
  fixture through the replay builder yields decisions. The control is checked
  in.
- A replayed stop touch resolves at its bar's close boundary and is not refused
  by BTC-162. Fills, stops and funding run through the unchanged owners.
- Point-in-time property test: no replay input is visible to a decision before
  its modelled availability.

## RBT-002 — `INVENTORY_HISTORICAL_INPUT_COVERAGE_V1`

**Status:** `NOT STARTED / DEPENDENCY-SATISFIED`
**Dependencies:** none
**Implementation effort:** high
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/coverage.py` (new)

Measure what exists and what must be collected, before any backfill.

Acceptance criteria:

- For each policy §5 family and each venue, over the data window: coverage,
  gap counts and positions, source identity, and whether the source supplies
  publication or revision times.
- For each family: the minimum history its owner windows require (z-score,
  rolling and ETF windows), read from the owner modules and configuration, not
  restated.
- Identifies the provider for each missing span. That is either an existing
  `DerivativesProvider` / `EtfFlowProvider` / OHLCV adapter or a new adapter
  specified for RBT-003.
- Confirms that the research database holds no observation dated in the holdout
  window or before 2020-01-01. Any exposure found is recorded, not silently
  accepted.
- Persists the inventory under `backtest_evidence/research_backtest_v1/`.
  Nothing is collected by this ticket.

## RBT-003 — `BACKFILL_HISTORICAL_INPUTS_V1`

**Status:** `BLOCKED — awaiting RBT-001 and RBT-002`
**Dependencies:** RBT-001, RBT-002
**Implementation effort:** high
**Review:** independent xHigh ticket review
**Owner modules:** new provider adapters under `btc_predictor/research_backtest/`

Collect exactly the spans RBT-002 marked missing, within the data window only.

Acceptance criteria:

- Collection uses the existing collectors and their provider protocols.
  Additional adapters live in new modules and implement the existing protocols.
  No collector, schema or migration changes.
- Every persisted row keeps its true provider, source and ingestion provenance.
- Produces the frozen per-venue and shared-input replay datasets through the
  RBT-001 builder, with their manifests under `backtest_evidence/research_backtest_v1/`.
- Re-running the build from the database reproduces identical manifests.
- Nothing outside the data window is requested from any provider.

## RBT-004 — `COMPOSE_CHAMPION_ENTRY_DECISION_V1`

**Status:** `NOT STARTED / DEPENDENCY-SATISFIED`
**Dependencies:** none (uses existing owner input types)
**Implementation effort:** xHigh
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/entry_composer.py` (new)

The flat-state half of the champion. At each daily decision instant it turns
point-in-time inputs into either one `ARM_ENTRY` `BacktestIntent` or a recorded
`NO TRADE`, by calling the existing owners in Rulebook order:

1. trend, flow (`ETF_CORE` via the §6.2 fallback), positioning, volatility and
   structure scores;
2. the core regime score and §24 hard flags;
3. setup detection and the entry trigger;
4. Entry Conviction and thresholds;
5. hard vetoes, including `DATA_QUALITY_FAIL` and no-chase, and the BTC-143
   R/R filter;
6. invalidation, the volatility buffer and the initial stop (BTC-140..142).

Acceptance criteria:

- **No new formulas.** Every numeric value comes from an owner call. Review
  verifies there is no restated threshold, weight or transform.
- The composer reads only `BacktestContext` and replay inputs whose modelled
  availability is at or before the decision instant. A point-in-time property
  test covers this.
- Every decision instant writes one decision-ledger row: its outcome, the reason
  codes from the owners, and `STRUCTURALLY_UNEVALUABLE` where an Entry
  Conviction component is incomplete. Nothing is zero-filled.
- Covers every setup archetype and direction the owner modules define.
  Deterministic fixtures exercise each hard veto and each archetype.
- Batch/single parity: composer feature values equal the BTC-048 feature-matrix
  values for the same inputs.
- **Market closures:** every ETF flow-window call receives the loaded
  `US_EQUITY_MARKET_CLOSURE_TABLE_V1` set through `market_holidays`, never the
  empty default. Until the table's review passes, tests inject a fixture set
  labelled non-authoritative. A fixture test shows that a window spanning a
  listed holiday is complete with the set and `ETF_FLOW_INPUT_MISSING` without
  it.
- The same composer can later drive the advisory and paper paths (Rulebook
  invariant 15). Adopting it there is out of scope.

## RBT-005 — `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1`

**Status:** `BLOCKED — awaiting RBT-004`
**Dependencies:** RBT-004
**Implementation effort:** xHigh
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/management_composer.py` (new)

The in-position half. From the hold score and lifecycle state it emits `TRAIL`,
`ADD`, `TRIM` or `EXIT` intents, or none, through the existing owners:

- BTC-156 trailing-stop progression;
- BTC-150..158 lifecycle, pyramiding and add requirements;
- exit and trim rules.

Acceptance criteria:

- The same no-new-formula, point-in-time, decision-ledger and determinism
  criteria as RBT-004.
- **Rulebook §24 NO ADDING (policy §7):** no `ADD` intent is issued while
  STRESS, CROWDING or EUPHORIA is active. Each suppression is recorded as
  `RULEBOOK_24_NO_ADDING_ENFORCED`. The lifecycle-state (`DEFEND`) mapping is
  **not** chosen. Tests cover all three flags.
- New composer tests assert the BTC-222 risk invariants over composed replays:
  never average down, stops never widen, and aggregate risk-at-stop stays
  bounded.
- End-to-end: the composed champion replays the BTC-224 golden bar sequences
  without engine refusal. Its decisions are reported next to the scripted ones.
  They are not required to match, because the scenarios are scripted.

## RBT-006 — `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1`

**Status:** `BLOCKED — awaiting RBT-003, RBT-005 and the POSTP1-002V2A-T1 review PASS`
**Dependencies:** RBT-003, RBT-005, `POSTP1-002V2A-T1` PASS (closure table)
**Implementation effort:** high
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/preregistration.py` (new)

Freeze everything before any result exists.

Acceptance criteria:

- A preregistration artifact binds:
  - the code commit and the champion identity;
  - the `US_EQUITY_MARKET_CLOSURE_TABLE_V1` hash, whose coverage must span
    every date on which a flow window is evaluated;
  - the composer versions and the RBT-003 dataset manifests;
  - the cost ladder and the policy versions;
  - the report-generator version and the metric definitions.
- Computes each venue's evaluation-window start mechanically: the first daily
  decision instant where every Entry Conviction component and the core regime
  score are complete. This step evaluates completeness only. No trade, fill or
  outcome is computed or inspected.
- Pre-registers the BTC-182 walk-forward fold scheme and the threshold-sweep
  grid (sensitivity only) from the evaluation-window lengths, before any run.
- Review confirms that no evaluation-window outcome was produced before the
  freeze.

## RBT-007 — `RUN_FIRST_RESEARCH_BACKTEST_V1`

**Status:** `BLOCKED — awaiting RBT-006`
**Dependencies:** RBT-006
**Implementation effort:** high
**Review:** independent xHigh review, including a look-ahead audit and full
reproduction
**Owner module:** `btc_predictor/research_backtest/runner.py` (new)

Run the frozen pipeline:

- three venues × three cost rungs;
- walk-forward;
- regime and setup breakdowns;
- sensitivity-only threshold sweeps.

Produce the policy §8 report under `backtest_evidence/research_backtest_v1/`.

Acceptance criteria:

- Every policy §8 item is present, with trade counts next to every rate.
- Reproduces byte-for-byte from the preregistration artifact in a fresh process.
- The look-ahead audit samples decisions and proves every input they read was
  available at the decision instant.
- The report states the evidence class, its prohibited uses and every named
  limitation in its first section.
- No parameter changes, whatever the result.

## RBT-008 — `EVALUATE_HOLDOUT_ONCE_V1`

**Status:** `BLOCKED — awaiting RBT-007 review PASS`
**Dependencies:** RBT-007 independent review PASS
**Implementation effort:** high
**Review:** independent xHigh ticket review

Lift the RBT-001 holdout guard in this ticket's own commit, then:

- collect `2026-01-01 00:00` .. `2026-06-30 23:00` through the frozen RBT-003
  path, plus warm-up drawn only from the data window;
- run the unchanged frozen pipeline on all three venues;
- record the result, whatever it is, beside the evaluation-window result.

This closes EPIC Y V1. The holdout can never again evaluate this strategy
version or any version derived from inspecting its result.

## Next EPIC Y tasks

| ticket | task | status |
| --- | --- | --- |
| RBT-001 | `BUILD_HISTORICAL_REPLAY_INPUTS_V1` | NOT STARTED / DEPENDENCY-SATISFIED — recommended first |
| RBT-002 | `INVENTORY_HISTORICAL_INPUT_COVERAGE_V1` | NOT STARTED / DEPENDENCY-SATISFIED — needs research database |
| RBT-003 | `BACKFILL_HISTORICAL_INPUTS_V1` | BLOCKED — RBT-001, RBT-002 |
| RBT-004 | `COMPOSE_CHAMPION_ENTRY_DECISION_V1` | NOT STARTED / DEPENDENCY-SATISFIED |
| RBT-005 | `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1` | BLOCKED — RBT-004 |
| RBT-006 | `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1` | BLOCKED — RBT-003, RBT-005, POSTP1-002V2A-T1 PASS |
| RBT-007 | `RUN_FIRST_RESEARCH_BACKTEST_V1` | BLOCKED — RBT-006 |
| RBT-008 | `EVALUATE_HOLDOUT_ONCE_V1` | BLOCKED — RBT-007 review PASS |
