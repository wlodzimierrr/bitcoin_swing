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

- **Last updated:** 2026-09-03
- **Current phase:** Phase 1, EPIC W testing is implemented; every Phase-1
  implementation ticket except BTC-019 is now DONE
- **Authoritative execution roadmap:** [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
- **Current implementation frontier:** None; no Phase-1 implementation ticket
  remains open
- **Last completed ticket:** BTC-224, golden historical scenarios. Its
  required independent xHigh review has now passed with one review fix, as
  have BTC-221's and BTC-222's; no Phase-1 ticket review remains outstanding
- **Last epic integration audit:** EPIC S, backtesting (2026-09-03), PASS
  WITH NON-BLOCKING FINDINGS after one P2 and two P3 review fixes. EPIC Q,
  EPIC P, EPIC O, EPIC E and EPIC E2 were audited earlier the same day
- **Current IN_PROGRESS ticket:** BTC-019
- **Current BLOCKED tickets:** None recorded in Structured Tickets v2.6
- **Next dependency-satisfied ticket:** None. BTC-019 is the only remaining
  Phase-1 work
- **Other ready tickets:** None
- **Latest verified test baseline:** 3514 passed with Python 3.12 on 2026-09-03
- **Last relevant implementation/review commit:** `EPIC_S_FIX`
  (`fix: close EPIC S integration review findings`)

## Price-Reference State

```text
BTC-019 = IN_PROGRESS
Bitstamp sole canonical candidate = REJECTED
BTC_REFERENCE_COMPOSITE_V1 = RESEARCH_INCONCLUSIVE
BTC-019B = MIXED
BTC_REFERENCE_COMPOSITE_V2 = FROZEN_RESEARCH_PROTOCOL
production canonical reference = UNRESOLVED
```

Normal Phase-1 implementation may continue through injectable, versioned
reference-price boundaries. Final authoritative strategy calibration and
certification remain blocked until the production canonical reference is
resolved. See [PRICE_SOURCE_POLICY_V1](policies/price_source_policy_v1.md).

## Important Unresolved Decisions

- Production canonical BTC reference selection remains unresolved under
  BTC-019.
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
  contiguous, three BTC-019 research helpers restate the true-range formula
  instead of using the BTC-041 owner, and BTC-048 feature/target matrices
  serialize but have no restore or tamper-validation path.
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
