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

- **Last updated:** 2026-09-01
- **Current phase:** Phase 1, EPIC S backtesting and validation research
- **Authoritative execution roadmap:** [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
- **Current implementation frontier:** BTC-183, regime performance breakdown
- **Last completed ticket:** BTC-182, walk-forward validation, including its
  required independent xHigh review
- **Current IN_PROGRESS ticket:** BTC-019
- **Current BLOCKED tickets:** None recorded in Structured Tickets v2.6
- **Next dependency-satisfied ticket:** BTC-183, first by V2 execution order
- **Other ready tickets in the current epic:** BTC-184, BTC-185
- **Latest verified test baseline:** 2409 passed with Python 3.12 on 2026-09-01
- **Last relevant implementation/review commit:** `a7998e52b0a33efd69930b63a765deadda2a104d`
  (`fix: close BTC-182 independent review finding`)

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
