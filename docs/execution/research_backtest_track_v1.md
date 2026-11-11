# EPIC Y — First Research Backtest (Non-Certifying)

Workstream authority for the first real-data backtest of the frozen Phase-1
champion. This document controls EPIC Y (`RBT-xxx`) ticket status, dependencies
and acceptance criteria. It is **not** Phase-1 execution authority: [Structured
Tickets v2.6](bitcoin_swing_predictor_structured_tickets_v2_6.md) keeps that role
and is not modified by this workstream. It is **not** EPIC X or BTC-019 authority.

Governing policy: [`RESEARCH_BACKTEST_POLICY_V7`](../policies/research_backtest_policy_v7.md).
It superseded V6 before any run, on the owner's 2026-10-03 rulings on RBT-002A's
two closure preconditions:
- the spec's Momentum Persistence definition is accepted, and the RBT-007 report
  must include a non-selecting ablation of it (§6A.10, §8);
- the §6A.9 zero-variance equality guard covers all three positioning owners
  that share the Decimal z-score: funding, futures basis and OI growth.

V6 had superseded V5 before any run, on the owner's 2026-10-02 decisions after
the RBT-002 R2 re-review PASS:
- the completion spec defines `LEVEL_VOLUME_PERCENTILE` (§6A.8);
- an RBT-004 composer guard refuses the futures-basis zero-variance case (E1,
  §6A.9);
- EPIC Y code is isolated from the BTC-019 research modules (§9).

The champion's completion spec is
[`CHAMPION_COMPLETION_SPEC_V1`](../policies/champion_completion_spec_v1.md)
(RBT-002A). V5 had superseded V4 before any run. It re-scopes the §5A census to the external input surface with stated limits,
adds the runtime completeness guard binding RBT-004, RBT-005 and RBT-006, and
sets RBT-002's bounded closure standard (§5A.5–§5A.7). V4, on the owner's
RBT-002 decisions, adopted
four data rules verbatim (liquidation hour completeness, futures-basis
contract, STRESS hard-veto mapping, per-window ETF fund universe). It also
makes the pre-registered `CHAMPION_COMPLETION_SPEC_V1` part of the champion
identity. V3 had added record-shape availability rules and the input-surface
completeness rule. V2 had named the market-closure owner.
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
code path:  RBT-001 ─(review)─┐
            RBT-004 ─── RBT-005 ─────────────────────────┤
data path:  RBT-002 (§5A enumeration) ─┴─ RBT-001A ─ RBT-003 ┤
                                                ▼
                         RBT-006 freeze + preregistration
                                                ▼
                         RBT-007 first research backtest
                                                ▼  (review PASS)
                         RBT-008 holdout, opened once
```

## RBT-001 — `BUILD_HISTORICAL_REPLAY_INPUTS_V1`

**Status:** `DONE — independent xHigh ticket review PASS after review fix a9773e7`
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

### Implementation Notes

**Implementation commit:** `402e120`
**Independent review correction (`a9773e7`):** publication timing and revision-history
coverage are separate facts. The review-fix commit adds
`EtfSourcePublicationTime.revision_history_available` (default `False`).
Only source-backed history explicitly declared available clears
`REVISION_HISTORY_UNAVAILABLE`; a timestamp on a final-only value does not.
RBT-003 must persist the supporting source history and timing evidence.
Availability values and owner fields are unchanged. Eight independent review
cases supplement the original 159 tests. The distinct fix commit is identified
in the review outcome below.
**Status:** `DONE — independent xHigh ticket review PASS after a9773e7`
(2026-10-01). The review is an independent xHigh **ticket** review under
`prompts/review_ticket.md`, not an exact-hash proof-architecture review.
**Files:** new only.

- `btc_predictor/research_backtest/__init__.py`
- `btc_predictor/research_backtest/replay_inputs.py` (owner module)
- `btc_predictor/tests/test_research_backtest_replay_inputs.py`

`git diff --diff-filter=MDRT 9752f7b 402e120` is empty.

**What exists.** A pure, deterministic builder over owner records the caller
already holds: `OhlcvBar`, `EtfFlow`, `FundingRate`, `OpenInterest` and
`PerpVolume`. It opens no database or network connection, and a test runs it
with sockets disabled. No loader was added; RBT-003 reads rows through the
existing owners. Entry points:

- `build_shared_replay_snapshot(window=..., volume_bars=..., etf_flows=...,
  etf_source_publication_times=..., funding_rates=..., open_interest=...,
  perp_volumes=..., etf_market_holidays=None)` builds the one non-price
  snapshot that all three venue runs share (policy section 2). It includes the
  retained Bitstamp raw OHLCV for volume and spot participation.
- `build_venue_replay_dataset(venue=..., window=..., price_bars=...,
  shared_snapshot=...)` builds one venue's `1h` replay stream for the unchanged
  `run_backtest`, checked against the engine's own `validate_backtest_bars`.
  Its manifest binds the shared snapshot by digest. The three venue manifests
  carry one shared digest and differ only in `venue` and `price_series`.
- `replay_market_bars_at(replay_bars, decision_at=..., window=...)`, also
  `VenueReplayDataset.market_bars_at`, derives daily, weekly and monthly bars
  by calling BTC-040 `build_canonical_market_bars` with the decision instant as
  its cutoff. It then restamps each bucket with the close of its last
  constituent hour. BTC-040 stamps the cutoff, and `derive_ohlcv_bars` stamps
  one value on every bucket, so the per-bucket value has to be set here. Its
  source bars must be `1h` replay bars of one required venue, admitted by the
  window.
- `HOLDOUT_OPENING_AUTHORIZED = False` is the guard only RBT-008 may lift, in
  its own reviewed commit. `ReplayInputRefused` carries a closed set of refusal
  codes.

**Field placement per owner.** A census of `backtest/`, `portfolio/`,
`risk/`, `features/`, `signals/`, `levels/`, `data/`, `db/`, `quant/`,
`reporting/`, `journal/` and `config/` was adversarially verified. It found
that every bar predicate reads `ingested_at`, and that no predicate reads
`ingested_at` for a non-bar family. The modelled value therefore goes only into
the field each owner reads. Every other field keeps its raw value, including
the ETF and derivative `ingested_at`.

| Family | Point-in-time predicates and the fields they read | `observation_time` | Modelled availability | Replay field |
| --- | --- | --- | --- | --- |
| Reference `1h` price bar (one venue) | BTC-180 `_bar_available_at = max(timestamp+1h, ingested_at)` and `validate_backtest_bars`; BTC-040 `_source_bar_is_point_in_time_available` (close ≤ cutoff and `ingested_at` ≤ cutoff); BTC-161..165 `resolved_at = max(close, ingested_at)`, which sets the ENTER time and so BTC-162's first eligible bar; accounting excursions; volatility, swing, breakout, anchored-VWAP, volume-profile and signal-trigger bar filters (close and `ingested_at`) | bar start | `timestamp + 1h` | `ingested_at` |
| Shared Bitstamp raw OHLCV (volume, spot participation) | the bar predicates above, plus `spot_perp_participation_from_rows` (`available_at := ingested_at`, `observation_time := timestamp`) | bar start | `timestamp + 1h` | `ingested_at` |
| Derived `1d`/`1w`/`1mo` bar | the bar predicates above | bucket start | close of the last constituent hour (BTC-040 at the decision instant, restamped per bucket) | `ingested_at` |
| ETF flow and AUM | `features.flow._latest_available_flows_by_fund_date` (`available_at ≤ as_of`; one row per `(fund, date)` by `(available_at, revision, provider)`); `data.etf_flows.latest_etf_flows_available_at` (`available_at`) | US trading date `T` | `max(T+2 00:00 UTC, supplied source publication time)` | `available_at` |
| Funding rate | `features.positioning.funding_health`; `data.derivatives` SQL and `aggregate_btc_derivatives_available_at`; `data.quality` stale-funding check (`available_at ≤ t` and `observation_time ≤ t`) | settlement instant `S` | `S` | `available_at` |
| Open interest | `open_interest_growth_health`, `open_interest_intensity`; `data.derivatives`; `data.quality` snapshot check (same two fields) | snapshot instant | `observation_time` | `available_at` |
| Perpetual volume | `spot_perp_participation` perp leg; `data.derivatives`; `data.quality` (same two fields) | interval **start** (assumed, see below) | `next_bar_timestamp(start, timeframe)` | `available_at` |

**Interval start/end finding.**

- `FundingRate.observation_time` is the settlement instant. Migration 0012
  calls it the "funding timestamp or period end reported by the exchange".
- The owner defines `OpenInterest` as a snapshot ("market timestamp for the
  open-interest snapshot") with no timeframe field. Policy section 4's
  "interval ending E" is therefore the snapshot instant itself.
- For `PerpVolume` the owner schema is **ambiguous**: it says "bar timestamp or
  period end". The builder reads `observation_time` as the interval **start**
  and computes the end with the OHLCV owner's `next_bar_timestamp`. It refuses
  timeframes the owner cannot close.
  - This is a surfaced assumption, recorded as such in every manifest rule, not
    an owner fact.
  - It is the reading `spot_perp_participation` needs, because it joins perp
    `observation_time` to the start-stamped `OhlcvBar.timestamp` by equality.
  - For an end-stamped series it can only delay availability by one interval,
    never advance it.
  - RBT-003 must persist perpetual volume stamped at the interval start and
    open interest at the snapshot instant.

**Control (checked in).** The fixture is one week, 2024-03-04..10, of 168
Bitstamp `1h` candles. It is produced by the real `BitstampOhlcvProvider`
reading canned `/api/v2/ohlc` payloads, through the real BTC-020
`collect_btc_ohlcv` with one bulk `ingested_at` (2026-09-28 09:15 UTC), and
its raw digest is pinned. A golden-style scripted plan arms one long at the
2024-03-05 23:00 bar and exits at the 2024-03-08 23:00 bar if a position is
open.

| Run | Decisions taken | Executed decisions | Trades | Outcome |
| --- | --- | --- | --- | --- |
| Raw bulk backfill through unchanged `run_backtest` | 1, at the bulk instant | **0** | 0 | `QUEUED` → `UNEXECUTED` (`DATASET_ENDED_BEFORE_ELIGIBLE_BAR`); BTC-040 derives 0 bars at the decision instant |
| Same bars through the replay builder | 2, at 2024-03-06 00:00 and 2024-03-09 00:00 | **2**: entry filled 2024-03-06 01:00, exit 2024-03-09 01:00 | 1 closed | daily bars for 03-04 and 03-05 visible at the decision instant |

**Stops, fills and funding on replayed bars.**

- A stop touched two bars after the fill resolves at that bar's close, and
  BTC-162 does not refuse it.
- An entry bracket touched on its own fill bar resolves at that bar's close.
- The same series with any positive ingestion delay (1 µs, 1 s, or EPIC X's
  5 min) makes BTC-162 refuse the bar after the fill and aborts the run. This is
  the policy section 4 reason for modelling bars at their close.
- Under the `stress` rung, BTC-180 carry is charged on every held bar at its
  close (`effective_at = close − 1 µs`).
- A missing first eligible bar expires the intent
  (`FIRST_ELIGIBLE_BAR_MISSING`); the gap is never filled.

**Design decisions.**

1. **Admission covers the whole observation interval.**
   - The interval is `[t, t+1h)` for a bar, `[start, end)` for perp volume, the
     UTC day `T` for an ETF flow, `(S − funding_interval_hours, S]` for funding
     and the instant for open interest.
   - A record is refused, never dropped, if any part lies outside the window's
     admitted windows. So funding settled 2020-01-01 00:00 is refused, because
     it prices a 2019 period.
   - A weekly perp interval opened in 2025 and closing in the holdout is
     refused.
   - Modelled availability may fall in the holdout (the 2025-12-31 23:00 bar is
     available at 2026-01-01 00:00). That exposes no holdout market content.
2. **Windows.**
   - `PROHIBITED`, `DATA`, `HOLDOUT` and `RESERVE` are half-open and partition
     time. `DATA = [2020-01-01, 2026-01-01)`; its last `1h` bar is 2025-12-31
     23:00.
   - A holdout build would admit data-window warm-up plus holdout observations,
     per RBT-008's "warm-up drawn only from the data window".
   - The guard's state is not written into any manifest, so a DATA dataset's
     digest does not change when RBT-008 flips it. This is pinned by a test.
   - Tests flip the guard only in-process and build no holdout-dated record.
3. **ETF revisions.** The flow owner keeps one row per `(fund, date)` across
   revisions and providers, by `(available_at, revision, provider)`.
   - Several rows for one fund and date replay only if every row carries an
     `EtfSourcePublicationTime` and no two share a publication instant.
   - The owner's own choice at every modelled instant must also be the
     latest-published row available then. Otherwise the build is refused with
     `ETF_REVISION_ORDER_UNAVAILABLE`.
   - The reason: revisions published before `T+2` share the `T+2` floor, and
     the owner then breaks the tie by label. `initial`/`final` would serve the
     superseded value forever.
   - `T+2 00:00` is always the floor. A supplied time before the trading date
     begins is refused as impossible.
   - A raw `EtfFlow.available_at` is never read as a publication time, because a
     backfill stamps it with collection time. A source's own time must be passed
     explicitly; the manifest records the raw value beside it.
   - Rows that differ only in raw `available_at` are refused as duplicates.
4. **`REVISION_HISTORY_UNAVAILABLE`** labels every record whose revision-history
   coverage is unknown. That is every bar and derivative record (the derivative
   schema cannot store revisions), and every ETF row without an explicit
   source-backed `revision_history_available=True` assertion. Publication timing
   alone does not establish revision history. It is informational, counted per
   family, and never changes availability. The original implementation conflated
   these facts; the independent review corrected it before closure.
5. **Gaps are counted per series on each owner's own definition.**
   - `1h` bars and perp volume use the OHLCV owner's bar grid.
   - Funding and open interest use the BTC-031 `data.quality`
     `PROVIDER_DISCONTINUITY` rule: the declared interval plus 1 h for funding,
     3 h for open interest.
   - ETF uses the owner publication calendar, only when `etf_market_holidays` is
     supplied (EPIC Y: `US_EQUITY_MARKET_CLOSURE_TABLE_V1`).
   - An unevaluated or absent family reports `null` with its reasons, never
     zero.
6. **Manifests.** Two canonical-JSON documents with sha256 digests: sorted
   keys, no whitespace, ASCII. Each input's entry carries:
   - its content digest (the owner's `as_record`, with numbers rendered by
     value, not by scale, so collector output and a `NUMERIC(38,18)` read-back
     address identically);
   - every raw time field;
   - any supplied publication time;
   - its observation end;
   - its modelled availability;
   - its labels.

   At real data-window scale the shared manifest is about 78 MB (about 8.5 MB
   gzipped) with one hourly derivatives exchange. RBT-003 should persist the
   canonical bytes compressed (deterministic gzip) and keep the digest over the
   uncompressed bytes.
7. **Refused families.** `FuturesBasis`, `Liquidation` and market-cap
   observations are refused: policy section 4 gives them no availability rule.

**Tests.** 159 deterministic, offline tests, in these groups:

- availability table and boundaries;
- field placement per owner;
- a seeded point-in-time property test over five seeds. It checks the real
  BTC-180, BTC-040, `features.flow`, `data.derivatives` and
  `features.positioning` predicates against an oracle computed from the raw
  records and the policy table, including that the owner keeps the
  latest-published ETF revision;
- the control;
- stops, fills and funding;
- every refusal;
- gaps;
- manifest content;
- determinism: reordering, `PYTHONHASHSEED` 0/1/8675309, an alternate cwd and
  a fresh process.

In-process mutation checks were each killed by the suite (13 mutants): a
consistent +5 min shift, a dropped `T+2` floor, perp at interval start, no revision-order check,
no key sorting, digests ignoring values, scale-dependent numbers, unguarded
decision-instant bars, zero gaps for absent families, an ordering check run
only at the last instant, no distinct-time refusal, and unchecked owner numbers.

**Validation.** All runs used the `.venv312` CPython 3.12.14 interpreter, offline. The
proof suites ran alone and sequentially, with temporary roots under `/tmp`
outside the repository.

| Suite | Result |
| --- | --- |
| Focused `test_research_backtest_replay_inputs.py` | **159 passed** |
| BTC-180..185 (`test_backtest_engine`, `_engine_review`, `_cost_model`, `_walk_forward`, `_regime_performance`, `_setup_performance`, `_threshold_sweeps`, `_epic_s_integration`) | **282 passed** |
| BTC-220..224 (`test_feature_score_boundary`, `test_quant_comparisons`, `test_look_ahead_bias`, `test_risk_invariants`, `test_paper_execution`, `test_golden_scenarios`) | **342 passed** |
| Closure table `test_us_equity_market_closures.py` | **145 passed** |
| Owners the builder calls (flow, positioning, derivatives collector and quality, OHLCV, market bars, Bitstamp adapter, stop and entry execution, market-bar rolling integration) | **243 passed** |
| V5 recomputation (`test_reference_composite_v5`, both prospective-corpus suites, `test_etf_flows`): V5 unchanged at `95e43ee1...775a89` | **407 passed**, 2 pre-existing composite skips |
| Namespace reproductions on the final code: PAD5 (`54675984...f483`) and PAD4-R5 (`b4168dc9...61c7`) | 2/2 each |
| Complete PAD5 and PAD4-R5 suites, run alone during validation | 117/117 and 201/201 |

`python -m compileall btc_predictor etf_calendar_worker` passes, and
`git diff --check` passes on the staged files.
`git diff --diff-filter=MDRT 9752f7b 402e120` is empty: no tracked file was
modified, deleted, renamed or retyped.

The full suite was **NOT RUN**. No production behaviour changed and no existing
module was touched.

**Independent pre-commit review.** Before commit, the implementation went
through an adversarial census of the owners' point-in-time predicates and a
five-lens review. Each lens finding was checked by a skeptic.

- No P0 or P1 defect survived verification.
- One P2 correctness defect, the ETF revision tie at the `T+2` floor, was
  fixed, along with every confirmed P3.
- A second round on those fixes confirmed all of them. It found and fixed
  three P3 residuals: a supplied ETF publication time before its own trading
  date is now refused (`SOURCE_PUBLICATION_BEFORE_OBSERVATION`); decision-instant
  bars now meet the full venue bar contract and duplicate refusal; and the
  property-test generator now draws revision labels independently of
  publication order.
- The remaining items are recorded here: the positioning-input gap, manifest
  size and the ETF publication-time channel.

This does not replace the required independent xHigh ticket review.

**Cross-workstream findings for EPIC Y.** The positioning-input gap below was
**ANSWERED on 2026-10-01 by `RESEARCH_BACKTEST_POLICY_V3`**: record-shape
availability rules, required rows for futures basis, market cap and
liquidations, discretionary inputs not asserted, and the §5A completeness
rule. RBT-001 implemented `HISTORICAL_REPLAY_AVAILABILITY_V1` under V2 and is
reviewed against that scope. Its V3 extension is RBT-001A. The text below is
preserved as the finding that triggered V3.

- **Positioning inputs have no policy rule (material).**
  - Rulebook section 7.5 `PositioningScore` needs `BasisHealth` (futures basis)
    and `LeverageHealth` (OI intensity, which needs BTC market cap). It has no
    Phase-1 fallback, and `calculate_positioning_score` is incomplete if any
    component is missing.
  - Policy V2 sections 4 and 5 give no family or availability rule for futures
    basis or market cap. Section 5 lists perpetual volume under positioning,
    which no positioning owner consumes.
  - As specified, EPIC Y would therefore leave every Entry Conviction
    structurally incomplete, and CROWDING could never be evaluated.
  - This needs an explicit decision before RBT-002 scopes collection and before
    RBT-004. The options are a `RESEARCH_BACKTEST_POLICY_V3` family and rule, or
    a recorded structural finding. RBT-001 invents no rule.
- **RBT-004 must use replay inputs only.**
  - It must feed replay bars, not raw bars, to every level, structure and
    signal producer, because their `detected_at` inherits
    `max(close, ingested_at)`.
  - It should take daily bars from `replay_market_bars_at`, because
    `risk.buffer.atr_from_daily_bars` applies no availability filter.
  - `aggregate_btc_derivatives_available_at` is point-in-time but starts its
    liquidation and perp-notional sums at zero and averages all visible
    history, so it is not a champion feature source.

### RBT-001 review outcome

**Review date:** 2026-10-01. **Result:** **PASS after review fix `a9773e7`**.
Independent xHigh ticket review under `prompts/review_ticket.md`, of
implementation `402e120`, documentation `ac3590a`, base `9752f7b`, on the
required `claude/etf-worker-prospective-integration-dixlte` branch after
fast-forwarding to `7d765c7`. Review scope is the RBT-001 ticket and policy V2
§4; policy V3 §4/§5A and RBT-001A are extension constraints.

**Finding P2 — publication time incorrectly asserted revision-history
coverage (corrected).** At `replay_inputs.py:1299` in `402e120` (now line 1317),
`_availability` cleared `REVISION_HISTORY_UNAVAILABLE` whenever
`source_published_at` was present. A synthetic final-only IBIT row for
2024-03-28, with its final revision genuinely published 2024-04-02 16:30 UTC,
therefore reported zero unavailable-history records despite having no earlier
values. Expected: date availability from that timestamp while retaining the
missing-history disclosure. This matters because policy V2 §4 explicitly
permits final-only research only with that counted limitation; V3 market cap
must not inherit the same conflation.

The independently written
`test_final_only_etf_with_a_real_publication_time_still_lacks_revision_history`
failed on the reviewed implementation (`1 failed, 2 passed` in the initial
three-case probe). The small fix separates the source-history assertion from
publication timing, defaults coverage to unknown, validates the assertion as
a Boolean, and binds the resulting label/count in the manifest. It changes no
availability value, owner record field, raw row, or owner module. The original
availability tests now explicitly declare the two fixture revisions' history;
their mathematical and timing checks remain intact. New regressions check the
final-only case, explicit coverage, changed manifest identity, and refusal of
three non-Boolean assertions. **Distinct review-fix commit:** `a9773e7`.
No other P0–P3 defect remains. RBT-001 is DONE; this ticket review satisfies
RBT-001A's review dependency. It is not an EPIC X review or certification.

**Per-owner field-placement verdict (PASS).** Serialization and UTC validation
can read an ingestion timestamp without using it as a visibility predicate.

| Owner(s) | Actual visibility/resolution fields | Replay placement and verdict |
| --- | --- | --- |
| BTC-180 `run_backtest`, `_bar_available_at`, `validate_backtest_bars`, queued-intent eligibility | `max(next_bar_timestamp(timestamp, timeframe), ingested_at)`; fill bar starts at the decision's next eligible boundary | `1h` `ingested_at = timestamp + 1h`; PASS |
| BTC-040 `build_canonical_market_bars`, `derive_ohlcv_bars` | source close and `ingested_at` both at/before cutoff; exact complete-hour census for each bucket | derived `ingested_at = last constituent hour close`; cutoff first, restamp second; PASS |
| BTC-161/162 and add/trim/exit execution; BTC-165 excursions | resolution `max(close, ingested_at)`; excursions require bar end and ingestion at/before accounting time | close in bar `ingested_at`; entry, resting/touched stop, exit and funding chronology PASS |
| Swing, breakout/reclaim, anchored VWAP, volume profile; higher-low, reclaim and breakout/retest signals; volatility | bar close and ingestion at/before signal; detection uses latest close/ingestion of the confirmation bars | replay hourly and derived bars carry close in `ingested_at`; PASS |
| Structure score from clusters | consumes generated cluster/level results, not raw bar ingestion | RBT-004 must generate those results from replay bars; no second raw timestamp placement; PASS |
| `features.flow._latest_available_flows_by_fund_date`, `_flow_revision_sort_key` | `available_at <= as_of`, greatest `(available_at, revision, provider)` per fund/date | modelled ETF value only in `available_at`; raw ingestion retained; PASS |
| `data.etf_flows.latest_etf_flows_available_at` | SQL visibility uses `available_at`; ranking is per fund/date/provider by availability/revision | same placement; retrieval retains provider candidates, feature owner chooses across providers; PASS |
| Funding and OI positioning owners; every derivative `latest_*` query and aggregate | `available_at <= t` and `observation_time <= t` | settlement/snapshot time in `available_at`; raw ingestion retained; PASS |
| `data.quality` funding freshness and snapshot checks | same availability/observation predicates; no ingestion predicate | same placement; PASS. Structural quality checks operate over all supplied rows, so the future composer must pass the visible prefix |
| Spot/perp participation | spot converts bar ingestion to availability; perp reads availability; observations join by timestamp equality | spot `ingested_at = close`; perp `available_at = interval end`, observation stays start; PASS |

**Six judgement-call rulings.**

1. **Perp starts — NOT_A_DEFECT, explicit acquisition requirement.** Migration
   0012 allows start or end stamps and BTC-021 preserves the provider stamp;
   neither proves starts. The flow join requires starts. Interpreting an
   end-stamped input as a start delays visibility, but also joins the wrong
   spot period. RBT-002/RBT-003 must establish and persist interval-start
   semantics, timeframe, original provider timestamp and any normalization;
   incompatible rows must not silently enter the join. V3 should use a
   generational extension rather than reinterpret V1.
2. **Whole funding period — NOT_A_DEFECT.** Conservative admission protects
   the explicit ban on any pre-2020 represented content. It refuses the
   2020-01-01 00:00 eight-hour settlement, not settlements whose declared
   accrual period lies wholly in DATA. An independent quarter-hour boundary
   regression confirms the first wholly in-window period is accepted. This
   admission rule does not move settlement availability or cost-owner timing.
3. **Revision-history label — P2 corrected.** Absence of source revision
   evidence warrants the conservative label, including bars/derivatives whose
   schemas have no history. A publication time alone is insufficient to remove
   it. Reporting must describe unknown history, not assert that revisions
   definitely happened. Source-backed coverage is now a separate assertion.
4. **ETF tie refusal — NOT_A_DEFECT.** Changes in the selected row occur only
   at modelled availability boundaries. Checking every distinct boundary is
   sufficient between boundaries, and the latest supplied publication must
   win each check. Incomplete dates and equal publication instants fail closed.
   A supplied earlier revision may be served before its successor is visible;
   it is never selected afterward by the flow owner. The SQL loader retaining
   one candidate per provider is not a feature selection rule.
5. **Private flow-owner reuse — NOT_A_DEFECT, maintenance coupling.** This is
   correct reuse of the frozen owner, avoiding a second formula. A future
   owner interface change requires rerunning these parity/visibility tests;
   no present signature or result mismatch exists.
6. **Explicit source times — NOT_A_DEFECT, trusted data boundary.** The builder
   cannot authenticate a caller's timestamp. A caller can explicitly pass bulk
   collection time as a source time; that delays visibility and is accepted.
   It does not happen automatically. RBT-003 must source and bind publication
   evidence and revision-history assertions separately from collection times.
   EPIC Y does not claim EPIC X's adversarial proof architecture.

**Independent probes and acceptance evidence.**

- A separately written canned Bitstamp adapter/collector control reconstructed
  the 168 2024-03-04..10 candles and used the *same callback object* and same
  raw bar fields in both runs. Raw: zero executions, zero trades,
  `DATASET_ENDED_BEFORE_ELIGIBLE_BAR`. Replay: two executions (2024-03-06
  01:00 entry, 2024-03-09 01:00 exit), one closed trade. Every raw field is
  unchanged; only replay ingestion differs. This is a synthetic control,
  not champion performance.
- Independent flat bars resolve a stop touch at 2024-05-06 16:00, its close,
  without BTC-162 refusal. The unchanged stress-cost owner charges four held
  bars with `effective_at = close - 1 microsecond`. This proves owner carry
  timing, not historical funding-rate injection into the engine.
- Independent derivative aggregate and quality probes switch at settlement /
  snapshot instants; perp becomes visible one hour later. Retained raw bulk
  ingestion does not affect those predicates.
- A 168-hour week spanning 2024-12-30..2025-01-06 produces no weekly bar one
  microsecond early, one complete weekly bar at close with volume 336, and no
  weekly bar when an interior hour is missing. Three shuffled ETF revisions
  (`z-original`, `a-final`, `0-correction`) published across March/April select
  10/20/30 at their independent expected instants, including a late supplied
  publication and probes immediately before every change.
- The seeded property test really reaches BTC-180, BTC-040, flow, derivative,
  positioning and participation predicates. Its expected times are computed
  from raw fields without builder helpers. Its refusal generator uses the
  real flow owner; the independent three-revision fixture complements that
  coupling. Derived completeness also follows independently from BTC-040's
  exact-hour census.
- Pre-2020, holdout, reserve, mixed venue, unknown window and unsourced shapes
  fail the whole build; no bad row is dropped. Futures basis, liquidations and
  market cap refusal is correct V1 scope. The false module guard exposes no
  caller authorization parameter; only RBT-008's reviewed change may lift it.
  Runtime monkeypatching is not a claimed security boundary.
- Independently reconstructed venue/shared manifests are byte-identical with
  shuffled inputs under fresh `PYTHONHASHSEED` 0/1/8675309 processes and a
  different cwd. Canonical bytes and gzip decompression reproduce their
  uncompressed digests. A full six-year synthetic shared snapshot (52,608
  hourly rows per family, one derivatives exchange, eight-hour funding,
  164,399 records, no ETF rows) measured **73,938,804 uncompressed bytes /
  8,221,965 gzip bytes**, with exact round-trip and digest checks. The estimate
  of 78 MB / 8.5 MB is plausible and workload-dependent, not a size contract.
  RBT-003 should hash the exact uncompressed canonical
  bytes, store deterministic gzip with zero mtime and no filename, verify after
  decompression, and bind serializer/compressor versions. This plan is sound;
  avoid reparsing/re-encoding as an integrity check.
- Eight independent process-local mutants each fail the focused suite: a bar
  shift of +5 minutes; removing the ETF T+2 floor; perp visibility at interval
  start; unsorted JSON keys; a derived restamp one hour before close; checking
  only the last ETF revision instant; an extra hour from perp start/end
  confusion; and restoring the timestamp/coverage conflation. The last three
  include independently chosen mutations. No source file or owner was mutated
  on disk. The suite stops at the first failure in each fresh process; these
  are expected mutation failures, not unresolved regressions. This samples the
  implementer's claims; it does not claim to rerun all thirteen mutants.

**Commands and independently measured results.** All Python runs used
`.venv312/bin/python` (CPython **3.12.14**). PAD5 and PAD4-R5 ran alone and
sequentially. PAD5 used its sibling `/home/wlodzimierrr/pad5_tmp`; PAD4-R5 used
`--basetemp=/tmp/rbt001-review/pad4-temp`. `stat` independently confirmed that
both temporary roots and the repository have the same device (**2096**), and
both are outside the repository. All evidence is synthetic/offline.

| Command / test-module set (`python -m pytest -q btc_predictor/tests/...`) | Independent result |
| --- | --- |
| `test_research_backtest_replay_inputs.py` + new `test_research_backtest_replay_review.py` | **167 passed** (original **159**, independent **8**); 4.27s |
| `test_backtest_engine`, `_engine_review`, `_cost_model`, `_walk_forward`, `_regime_performance`, `_setup_performance`, `_threshold_sweeps`, `_epic_s_integration` | **282 passed**; final post-fix rerun |
| `test_feature_score_boundary`, `test_quant_comparisons`, `test_look_ahead_bias`, `test_risk_invariants`, `test_paper_execution`, `test_golden_scenarios` | **342 passed**; final post-fix rerun |
| `test_us_equity_market_closures.py` | **145 passed** |
| `test_flow_features`, `test_positioning_features`, `test_derivatives_collector`, `test_derivatives_quality`, `test_ohlcv`, `test_market_bars`, `test_bitstamp_ohlcv`, `test_simulated_stop_execution`, `_stop_execution_review`, `_entry_execution`, `test_market_bar_rolling_integration` | **243 passed** |
| `test_reference_composite_v5`, `test_prospective_integration_corpus`, `_corpus_v2`, `test_etf_flows` | **407 passed, 2 pre-existing composite skips**; 111.48s; V5 **`95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`** |
| Full `test_etf_calendar_replay_verified_evidence.py` | **117 passed**; 442.81s; includes preserved-authority and persisted-namespace checks for PAD5 **`54675984...f483`** and unchanged R5 lineage |
| `test_etf_calendar_isolated_scientific_worker_r5.py::test_persisted_namespace_reproduces_exactly` and `::test_child_order_variation_does_not_change_the_parent` | **2 passed**; 25.84s; PAD4-R5 **`b4168dc9...61c7`** |
| `python -m compileall -q btc_predictor etf_calendar_worker`; `git diff --check` | **PASS** |
| `git diff --diff-filter=MDRT 9752f7b 402e120`; `git diff --name-only 402e120 ac3590a`; review diff against `7d765c7` | implementation has only the three additions; documentation commit only two docs; review changes only replay code/tests and EPIC Y/CURRENT_STATE docs |

Selected passing suite total: **1,705 passed, 2 skipped**. Expected failures
from the before-fix reproducer and eight mutation runs are excluded. The full
repository suite and the full 201-case PAD4-R5 suite were **NOT RUN** in this
review; the historical full-suite baseline is not replaced. All acceptance
criteria now pass, including corrected history disclosure. New scripts used
only local temporary probe outputs; no real dataset or holdout was collected.

**Extension and remaining limitations.** RBT-001A must preserve the reviewed V1
entry points, constants and manifests; add V3 versions and shapes separately,
and retain refusal of unclassified/unsourceable inputs. No owner modification
is needed. RBT-002 remains responsible for source semantics, full input-surface
coverage and source evidence, including the quality owner's need for filtered
inputs. No real-data backtest outcome exists; holdout **NOT COLLECTED**;
BTC-019 untouched and sealed sample unopened; EPIC X unchanged with
`POSTP1-001V2R1` still next; Epic T unchanged.

## RBT-002 — `INVENTORY_HISTORICAL_INPUT_COVERAGE_V1`

**Status:** `DONE — independent R2 re-review PASS under V5 §5A.7 (2026-10-02)` — reviewed correction `812b968` plus docs `ce5cd70`, on base `634d122`. All four bounded closure criteria pass; no R2 defect or new external input. Inventory `108ab25b...efe3a` unchanged. The inherited full-suite test-scope finding is non-blocking and reproduced at the base. See "RBT-002 R2 re-review outcome". Earlier FAIL/blocked outcomes remain historical.

**Owner decision, 2026-10-02 (policy V5 §5A.5–§5A.7).** RBT-002 closes on a
bounded standard, not a proof of universal completeness. The next correction
(R2) must:
- discover nested, local and private callables and classify each one as
  `OWNER_INTERNAL` or external;
- remove the tracer exemption that masked the omission;
- add regressions for both;
- state the census limits with measured coverage;
- keep the external-input classification and the live-database facts.
The re-review then passes or fails on that standard. Gaps in the census method
that reveal no missing external input are recorded as limitations. The runtime
completeness guard in RBT-004, RBT-005 and RBT-006 is the backstop.
Correction R2 and its independent re-review now satisfy these requirements;
see the RBT-002 R2 re-review outcome below.
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
- **Policy V3 §5A input-surface enumeration.** From owner code, mechanically
  enumerate every input on the champion's decision path:
  - every Entry Conviction component;
  - the core regime and the §24 hard flags;
  - the hard vetoes and data quality;
  - risk, sizing and stops;
  - lifecycle, add, trim and exit.
  Map each input to a §4 shape, a §5 family, a historical source and coverage,
  and record the owner's missing-input behaviour. The enumeration is
  test-backed and fails on any unclassified owner input field.
- Pins the persisted semantics of `futures_basis` (snapshot or interval, and
  the contract definition the BTC-021 collector uses) and of `liquidations`
  (events or aggregates). Selects the market-cap provider.
- Produces the §5A **blocker list**. If a blocker would leave an Entry
  Conviction component structurally incomplete on every evaluation date,
  record it as requiring an owner decision; do not proceed to RBT-003 scoping
  for that input.
- **Owner-less derived inputs.** Some inputs have no Phase-1 owner that
  produces them. The known case is `liquidation_percentile`, which only EPIC
  X's certified corpus V1 defines, as
  `PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1`. For each such input:
  - Reuse an existing certified definition, by import or by exact reference;
    never restate or invent one. For liquidations that means:
    - daily long-plus-short USD notional per UTC day;
    - a 730-day prior window with at least 365 prior observations;
    - the midrank percentile convention;
    - the `PROSPECTIVE_LIQUIDATION_CAPTURE_V1` universe, Kraken Futures
      `PI_XBTUSD`;
    - its hourly `LIQUIDATION_UTC_DAY_CENSUS_V1` completeness rule.
  - If there is no certified definition, record a §5A blocker.
- **Liquidation source order** (consistency with the EPIC X universe first,
  cost second). For each candidate, measure history depth and record the cost.
  The evaluation window needs daily observations from no later than
  2023-01-11 (365 days before the first ETF-era decision), and ideally from
  2022.
  1. Kraken Futures public history for `PI_XBTUSD` liquidation fills: the same
     universe, and raw events, so the hourly census applies unchanged.
  2. A raw-trade archive for Kraken Futures (for example Tardis.dev) that keeps
     liquidation flags: the same universe; paid, so record the exact price.
  3. A free aggregator with retained daily history (for example the Coinalyze
     `liquidation-history` daily interval), preferably for the Kraken
     `PI_XBTUSD` series.
  4. A low-cost paid aggregator (for example the CoinGlass Hobbyist plan, about
     $29 for one month at the time of this note).

  Options 3 and 4 give daily aggregates, so the hourly census cannot be applied
  and the universe may differ. If either is the only adequate source, record
  the exact deviation and a proposed daily-completeness rule as a blocker. It
  needs an explicit policy V4 decision before RBT-001A, and is never adopted
  silently.
- Persists the inventory under `backtest_evidence/research_backtest_v1/`.
  Nothing is collected by this ticket, apart from metadata probes (depth,
  schema, pricing) needed to rank sources.

### Implementation Notes

**Implementation commit:** `ab210a5`
**Status:** `DONE — independent R2 re-review PASS under V5 §5A.7`. Reviewed correction `812b968`, documentation `ce5cd70`, inventory `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`; see the R2 re-review outcome below.

**Prior status provenance (superseded):** `CORRECTED (R2) / AWAITING INDEPENDENT RE-REVIEW UNDER V5 §5A.7` — correction R2 `812b968`, inventory `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`; see "Correction (R2)" after the re-review outcome. Before R2: `FAIL — RELEASE BLOCKING` after the completed independent re-review of `906c719` (R1-RR); bounded review-fix `a281378` and inventory `a68e5284...ad765d`. The independent review on `9a90313` failed (`FAIL — RELEASE BLOCKING`, review-fix `0b06a85`). The R1 correction `906c719` is recorded in "Correction (R1)" after the review outcome. The original Implementation Notes below are pre-review provenance: the review outcome and the correction supersede their completeness and undefined-input claims. The reviewed inventory `b4b51fc4e46fee18c4d228f985e2efaeb6db6d577916e2390ac35398aed6a106` remains at `0b06a85`; the R1 correction inventory is `0d5f70403f1df2e3600f307283de982e90e9942d5ff19c73724df0a449987e30`; after this re-review fix the current inventory is `a68e5284e99e39b113c7ed2705ca533c1c2cfc0e0a6432dde9fcd7de40ad765d`.
**Database connection from policy V6 §9 onward (2026-10-02, R2-RR-FS1 fix).**
`coverage.open_research_engine` now reads the database environment through
EPIC Y's own `btc_predictor/research_backtest/database.py`
(`database_url_from_environment`): the same five `POSTGRES_*` names, the same
`postgresql+psycopg://` URL with `quote_plus` user and password, an error that
names missing variables only, and nothing printed, logged or persisted. The
read-only engine option and the `default_transaction_read_only` check are
unchanged. No `research_backtest` module imports a BTC-019 research-only
module any longer, so
`test_btc019_completion_gate.py::test_no_production_module_reads_a_research_reference_candidate`
passes, unedited. The inventory rebuilds byte-identical at
`108ab25b...efe3a`. The mentions of `btc019_empirical._database_url_from_environment`
below are historical: they record how RBT-002 and its reviews connected at the
time. The fix is committed as Part 0 of RBT-002A; see its Implementation Notes.

**Files:** new only.

- `btc_predictor/research_backtest/coverage.py` (owner module)
- `btc_predictor/tests/test_research_backtest_coverage.py`
- `backtest_evidence/research_backtest_v1/rbt002_input_coverage_inventory_v1.json`
  (canonical JSON, SHA-256 `b7b9a20b277310d354a60b0f92165dc8a618b18112397402d19dd0d629be3bf0`), its `.sha256` file and the
  short human report `rbt002_input_coverage_inventory_v1.md`

`git diff --diff-filter=MDRT 1e7c64e ab210a5` is empty: no tracked file was
modified, deleted, renamed or retyped, and no schema migration was run.

**What exists.** One module, imported by nothing else, that measures and
decides nothing on its own. It computes no score, composer, fill or trade.

- `enumerate_input_surface()` is the policy V3 §5A enumeration. It reads every
  field of 36 owner input types with `dataclasses.fields`, and every parameter
  of 68 owner call sites on the RBT-004/RBT-005 decision path with
  `inspect.signature`. That gives **592 inputs**. Each needs exactly one
  `InputClassification`:
  - its §4 shape and §5 family;
  - its producing owner, or `OWNERLESS`;
  - its historical source;
  - the owner's quoted missing-input behaviour;
  - the Entry Conviction components it feeds.

  An unclassified field or parameter raises `UNCLASSIFIED_FIELD` /
  `UNCLASSIFIED_PARAMETER`. A classification for a removed name raises
  `STALE_CLASSIFICATION`.
- `collect_database_coverage(connection, collected_at=...)` takes a coverage
  snapshot using only `SELECT` statements, each checked by
  `require_select_only`. It runs on an engine with
  `execution_options(postgresql_readonly=True)` from
  `btc019_empirical._database_url_from_environment` (imported, never printed),
  and it refuses unless `default_transaction_read_only` is `on`.
  - Rows dated before 2020, in the holdout or in the reserve appear only in
    `COUNT`, `MIN` and `MAX` of time columns.
  - Data-window rows are read as series keys plus observation instants.
  - No value column is named in any statement.
  - Tables whose names mark trusted-acquisition or calendar persistence are
    skipped unread.
- `minimum_history_requirements()` reads every window, minimum and lookback
  from owner constants and keyword defaults, and the liquidation percentile's
  from EPIC X by reference. `earliest_evaluable_inputs()` simulates each rule:
  - lookback rows;
  - a rolling window that includes the current row;
  - a count in the half-open `[t - window, t)` history;
  - an ETF publication-day window;
  - all-of.

  Venue series come from `venue_bar_series()`, which runs BTC-040
  `derive_ohlcv_bars` on timestamp-only stand-in bars, so the exact-hour census
  is reused, not restated. Shared series come from `projected_shared_series()`,
  using the selected sources' measured first instants and cadence.
- `SOURCE_CANDIDATES`, `PROBE_EVIDENCE`, `SEMANTIC_PINS`, `derive_blockers()`,
  `acquisition_plan()`, `build_inventory()` and `render_report()`.
- The CLI has two commands. `python -m btc_predictor.research_backtest.coverage
  collect` runs a read-only collection and writes the artifact. `rebuild`
  regenerates the artifact from its own persisted snapshot, with no database.

**Research database (read-only check, 2026-10-01).**

- Server: PostgreSQL 17.9, database `btc-swing`, `default_transaction_read_only`
  and `transaction_read_only` both `on`, Alembic revision
  `0021_trade_accounting`.
- `research` schema: no tables. No trusted-acquisition table exists in this
  database.

| family | venue | rows 2020–2025 | first / last | gaps (positions) | provider / source | publication or revision times |
| --- | --- | ---: | --- | --- | --- | --- |
| Reference price `1h` | Bitstamp | 52,608 | 2020-01-01 00:00 / 2025-12-31 23:00 | 0 | `bitstamp` | none (`REVISION_HISTORY_UNAVAILABLE`) |
| Reference price `1h` | Coinbase | 52,597 | same | 11 in 5 runs: 2020-01-30 17:00; 2020-09-04 23:00; 2020-10-20 20:00; 2023-03-04 18:00–20:00; 2025-10-25 16:00–20:00 | `coinbase` | none |
| Reference price `1h` | Bitfinex | 52,592 | same | 16 in 7 runs: 2020-02-11 11–12; 2020-08-12 21; 2021-06-30 08–09; 2021-10-13 14–16; 2022-10-12 08–11; 2023-03-06 10–11; 2024-05-05 10–11 (hours UTC) | `bitfinex` | none |
| Shared raw volume | Bitstamp | 52,608 | as above | 0 | `bitstamp` | none |
| ETF flows and AUM | shared | **0** | — | whole span | — | schema: `revision` column, no publication-time column |
| Funding | shared | **0** | — | whole window | — | none |
| Open interest | shared | **0** | — | whole window | — | none |
| Futures basis | shared | **0** | — | whole window | — | none |
| Liquidations | shared | **0** | — | whole window | — | none |
| Perpetual volume | shared | **0** | — | whole window | — | none |
| BTC market cap | shared | **0** (no raw table) | — | whole window | — | — |
| `raw.generic_series` | — | 0 | — | — | — | — |

- Every OHLCV hour is grid-aligned, with no duplicates and one bulk ingestion
  on 2026-08-29 13:55–14:55 UTC.
- **Timestamp semantics.**
  - OHLCV stamps are *consistent with* interval start: every series runs from
    the window start through the last start-grid hour and has no holdout row.
    Stamps alone cannot exclude end stamping, so the BTC-020 adapters' candle
    open time pins it.
  - Perpetual volume, futures basis and liquidations have **no persisted rows**,
    so their semantics cannot be confirmed from data. The schema fixes them, and
    RBT-002 pins them for RBT-001A/RBT-003:
    - `liquidations` is per-side **interval aggregates**, because its primary
      key cannot hold events;
    - `futures_basis` is a **snapshot** (a market timestamp, no timeframe);
    - perpetual volume is the **interval start** (RBT-001's requirement).
- **Exposure recorded, not accepted silently.** 2,232 `raw.btc_ohlcv` rows are
  dated 2019-12-01 00:00 .. 2019-12-31 23:00: 744 per venue, bulk-ingested
  2026-08-29 14:55 UTC. They lie outside the sealed BTC-019 sample, which ends
  2019-11-30 23:00, but inside the policy §3 prohibited window. They were only
  counted. RBT-001 refuses any pre-2020 record, and RBT-003 loaders must bound
  every query to the data window.
- No raw row is dated in the holdout or reserve. `derived.btc_reference_composite`
  has three `available_at` values at 2026-01-01 00:05. These are availability
  instants of its 2025-12-31 observations, and every observation instant of
  that table lies in the data window.

**Input surface (592 inputs).**

| kind | inputs |
| --- | ---: |
| `RAW_HISTORICAL` | 104 |
| `DERIVED_BY_OWNER` | 190 |
| `OWNERLESS_CERTIFIED_DEFINITION` | 3 |
| `OWNERLESS_UNDEFINED` | 36 |
| `DISCRETIONARY` | 7 |
| `ABSENT_RULEBOOK_FALLBACK` | 11 |
| `ENGINE_STATE` | 62 |
| `STRATEGY_CONFIG` | 179 |

Raw leaf inputs by §5 family:

| family | inputs |
| --- | ---: |
| reference price `1h` | 25 |
| shared raw volume | 14 |
| ETF flows and AUM | 11 |
| funding | 12 |
| open interest | 13 |
| futures basis | 12 |
| liquidations | 13 |
| perpetual volume | 13 |
| BTC market cap | 5 |
| US equity market closures | 2 |

The inventory also counts every input drawing on a family transitively.

- Discretionary inputs are `SYSTEMIC_SHOCK`, `SYSTEMIC_EUPHORIA` and
  `MANUAL_RESEARCH_OVERRIDE`. The owners' `None` handling is quoted per field.
- **Owner-less inputs.** 24 have no definition anywhere: no owner, no config
  value, no certified definition and no Rulebook number. One more,
  `LIQUIDATION_PERCENTILE`, has a certified EPIC X definition. The 24 are:
  - trend z-scores (`TREND_Z_M4`, `_M12`, `_20W`, `_52H`);
  - flow z-scores (`FLOW_Z_ETF_NORM_5D`, `_20D`, `_FLOW_ACCEL`);
  - `RANGE_PERCENTILE`, `DOWNSIDE_RETURN` and `UPSIDE_RETURN`;
  - `LEVEL_REACTION_MAGNITUDE` and `LEVEL_VOLUME_PERCENTILE`;
  - `SEVERE_CROWDING_STATE`;
  - Hold/Add components and the add/exit predicates:
    `MOMENTUM_PERSISTENCE_SCORE`, `NEW_STRUCTURE_SCORE`, `ADD_MOMENTUM_SCORE`,
    `NEW_STRUCTURAL_CONFIRMATION`, `REGIME_SUPPORTIVE_PREDICATE`,
    `FLOW_SUPPORTIVE_PREDICATE`, `REGIME_INVALIDATION_PREDICATE` and
    `DATA_RISK_EXIT_PREDICATE`;
  - setup inputs: `CORRECTION_FROM_LOCAL_HIGH`, and `DISTRIBUTION_STATE` /
    `SHORT_TRIGGER` (inert while shorts are disabled).
- `TrendScoreInput` has no `None` handling: `calculate_trend_score` raises
  `RuntimeError` on a `None` component.
- `LIQUIDATION_PERCENTILE` reuses EPIC X corpus V1 by reference. Its three
  definition hashes are recorded in the inventory:
  `PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1` `606e3930...215b7`,
  `PROSPECTIVE_LIQUIDATION_CAPTURE_V1` `d4268aa2...798c8` and
  `LIQUIDATION_UTC_DAY_CENSUS_V1` `7180ad6c...0a4a2`.

**Earliest evaluable date (input completeness only).** Every Entry Conviction
component and the core regime must be complete. On every venue that is
**UNDEFINED**, because the trend, flow, volatility and structure components
each need owner-less inputs. The table gives the lower bound on the available
instant, assuming those inputs were defined with no extra history. Positioning
is the only defined component.

| venue | trend | flow | positioning | volatility | structure | all components and core regime |
| --- | --- | --- | --- | --- | --- | --- |
| Bitstamp | ≥ 2021-01-04 | ≥ 2024-02-10 | 2020-10-02 | ≥ 2022-05-29 | ≥ 2020-02-24 | UNDEFINED, ≥ 2024-02-10 |
| Coinbase | ≥ 2021-01-25 | ≥ 2024-02-10 | 2020-10-02 | ≥ 2022-05-29 | ≥ 2020-03-02 | UNDEFINED, ≥ 2024-02-10 |
| Bitfinex | ≥ 2021-01-18 | ≥ 2024-02-10 | 2020-10-02 | ≥ 2022-05-29 | ≥ 2020-03-02 | UNDEFINED, ≥ 2024-02-10 |

Price-derived dates are measured from each venue's real hour coverage; a
missing hour removes its week's bar, which shifts Coinbase and Bitfinex.
Everything else is projected from the selected sources' measured depth:

- ETF: 20 publication days from 2024-01-11 (excluding MLK day) end on
  2024-02-08; with T+2 availability that gives 2024-02-10 00:00.
- Liquidations: 365 complete days from 2021-05-28.
- Positioning: funding 2020-01-11 08:00, OI growth 2020-09-09 06:00, basis
  2020-08-02 07:00, OI intensity 2020-10-02 00:00.

Any owner-defined normalisation window adds its own warm-up on top of these
lower bounds.

**Source ranking (probed 2026-10-01; each probe's URL, status and response
SHA-256 is recorded, never its values).**

| family | rank | candidate | measured depth | exact cost | notes |
| --- | ---: | --- | --- | --- | --- |
| Liquidations | 1 | Kraken Futures public REST executions, `PI_XBTUSD` | 2021-05-27 11:55 UTC (none before 2020) | USD 0 | Same universe and raw fills; `takerOrder.orderType == "Liquidation"`. Covers all of 2022. Census not applicable unchanged. Licence unverified, so hashes only |
| Liquidations | 1 (corroboration) | Kraken charts `liquidation-volume` hourly | 2020-02-26 | USD 0 | Explicit zero hours; totals only, no events |
| Liquidations | 2 | Tardis.dev Kraken Futures liquidations | 2019-03-30 | USD 4,200 (Academic yearly; eligibility) or 8,400 (Solo yearly), reaching 2022-10-01; USD 36,000 (Business yearly) for 2019-03-30 | Records `wss://futures.kraken.com/ws/v1`, the EPIC X endpoint; one data-window incident on 2021-11-10 05:09–05:19 |
| Liquidations | 3 | Coinalyze daily `liquidation-history` | UNVERIFIED (no `COINALYZE_API_KEY`) | USD 0 | Daily kept forever, intraday 1,500–2,000 points |
| Liquidations | 4 | CoinGlass Hobbyist pair history | all-time at `1d` (plan table) | USD 29 for one month (USD 348 yearly) | Personal use; at least 4h interval; Kraken pair support UNVERIFIED |
| Market cap | 1 | Coin Metrics Community `CapMrktCurUSD` | 2010-07-18 | USD 0 | CC BY-NC 4.0; not reviewable, so final values only; end-of-day close |
| Market cap | 2 | CoinGecko (EPIC X prospective source) | public API: 365 days | UNVERIFIED (paid plan) | — |
| Futures basis | 1 | Binance COIN-M quarterly vs COIN-M `BTCUSD` index | contracts from 2020-08-01; index from 2020-06-09 | USD 0 | CC BY-NC-SA 4.0; contract needs policy V4 |
| Futures basis | 2 | Kraken fixed-maturity via Tardis | UNVERIFIED | in a Tardis subscription | — |
| Funding | 1 | Binance USD-M `BTCUSDT` fundingRate archive | 2020-01-01 00:00 (8 h) | USD 0 | Settlement and interval map onto `FundingRate` |
| Funding | 2 / 3 | Tardis Kraken `derivative_ticker` / Kraken v4 | 2019-03-30 / rolling year from 2025-10-01 | USD 4,200 / 0 | Kraken v4 is too shallow, and its responses carry holdout rows |
| Open interest | 1 | Binance USD-M `metrics` | 2020-09-01 00:00 (5 min) | USD 0 | Early files: 2 rows per slot (de-duplicate) |
| Open interest | 3 | Kraken charts open-interest | 2023-03-07 | USD 0 | Too shallow |
| Perpetual volume | 1 | Binance USD-M `BTCUSDT` `1h` klines | 2020-01-01 00:00 | USD 0 | `open_time` = interval start |
| ETF flows and AUM | 1 | CoinGlass Hobbyist: `etf/bitcoin/flow-history` + `etf/bitcoin/history` | 2024-01-11 (documented) | USD 29 (one month) | Personal use; no publication time or vintages, so `T+2` and `REVISION_HISTORY_UNAVAILABLE` |
| ETF flows and AUM | 2 / 3 | Issuer sites / Farside | UNVERIFIED | USD 0 | 403/406/429 or no daily-history download on every issuer; Farside 403 |

**Pinned semantics for RBT-001A/RBT-003.**

- Perpetual volume: interval start.
- Open interest: hourly `:00` snapshots in USD (the BTC-021 request defaults to
  `1h`), so OI/market cap is dimensionless.
- Funding: settlement at `calc_time`. The 2020-01-01 00:00 settlement is
  refused because it prices 2019.
- Market cap for day D: `observation_time = D+1 00:00`, available `D+2 00:00`,
  first day 2020-01-01. The owner joins OI and market cap by exact instant.
- Liquidations: per-side `1h` aggregates, with event-id digests kept in
  evidence.
- ETF: `T+2 00:00`.

The data-quality owner requires `open_interest` **and** `perp_volume` feeds
(`DerivativesQualityConfig.required_snapshot_feeds`). Perpetual volume is
therefore required even though `ETF_CORE` does not use it.

**Blocker list (policy V3 §5A).** EPIC Y **stops for owner decisions**. Four
blockers leave an Entry Conviction component structurally incomplete on every
evaluation date, whatever data is bought.

- **NEEDS OWNER DECISION** (strategy semantics). For every item the data cost
  is USD 0. The options are:
  - a versioned owner contract or Rulebook decision;
  - an explicitly versioned research strategy variant;
  - no change, which leaves every decision `STRUCTURALLY_UNEVALUABLE`.

  The blockers:
  1. `BLK-TREND-ZSCORE-NORMALISATION`: trend, structural on every date.
  2. `BLK-FLOW-ZSCORE-NORMALISATION`: flow, structural. Its window adds
     warm-up after 2024-01-11.
  3. `BLK-VOLATILITY-RANGE-AND-RETURN`: volatility, structural, through
     orderliness. It also feeds STRESS, CAPITULATION and EUPHORIA.
  4. `BLK-LEVEL-STRENGTH-INPUTS`: structure, structural. Rulebook 9.2 says to
     omit volume, but the owner and config require it.
  5. `BLK-SEVERE-CROWDING-STATE`: the hard veto fails closed, so every new
     trade is vetoed on every date.
  6. `BLK-LIFECYCLE-PREDICATES` (RBT-005): Hold Score is never complete and
     every add fails closed.
  7. `BLK-SETUP-INPUTS`: Bullish Reset can never match; the short-side inputs
     are inert.
- **NEEDS POLICY V4 DECISION.** Each carries a proposed rule:
  1. `BLK-LIQUIDATION-HISTORICAL-CENSUS`. `LIQUIDATION_UTC_DAY_CENSUS_V1` needs
     prospective websocket epoch, liveness, clock and collector-health evidence
     that no historical source can supply. Proposed:
     `HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`, an hour counts as observed
     when it is covered by contiguous pagination and contains at least one
     execution. Universe, quantity, window, minimum and midrank are unchanged.
     Options:
     - Kraken REST: USD 0;
     - Tardis: USD 4,200 or 8,400;
     - a daily aggregate (Coinalyze or CoinGlass): USD 0–29, with a universe
       deviation.
  2. `BLK-FUTURES-BASIS-CONTRACT`. BTC-021 fixes no instrument, spot reference
     or annualisation. Proposed: `FUTURES_BASIS_CONTRACT_V1` on Binance COIN-M
     quarterlies vs the COIN-M index at hourly closes, with simple 365-day
     annualisation, excluding contracts within 7 days of expiry. Cost USD 0.
  3. `BLK-STRESS-HARD-VETO-MAPPING`. STRESS is never complete because
     `systemic_shock` is `DISCRETIONARY`, and no owner maps an incomplete result
     to `stress_flagged`. Passing `None` vetoes every trade. Proposed: pass
     `flagged` and record `STRESS_INPUT_MISSING`. Cost USD 0.
  4. `BLK-ETF-FUND-UNIVERSE`. A fund launched after 2024-01-11 makes every
     window spanning its launch fail closed. Proposed: a per-window universe of
     funds launched on or before the window's first publication date. Cost
     USD 0.
- **Named limitations** (policy §4/§7, no decision needed):
  - EUPHORIA trims never fire, because `trim_rules_from_results` passes `None`
    for an incomplete flag;
  - the pre-2020 exposure above;
  - `REVISION_HISTORY_UNAVAILABLE` for every selected source.

**RBT-003 acquisition plan.** Spans run from the source depth or the data
window start to 2025-12-31 23:00. Nothing outside the data window is requested.

| item | status |
| --- | --- |
| ETF flows and AUM, CoinGlass (USD 29) | READY after RBT-001A |
| Funding, Binance | READY after RBT-001A |
| Open interest, Binance | READY after RBT-001A |
| Perpetual volume, Binance | READY after RBT-001A |
| Market cap, Coin Metrics (evidence files) | READY after RBT-001A |
| Futures basis, Binance | BLOCKED on `BLK-FUTURES-BASIS-CONTRACT` |
| Liquidations, Kraken REST | BLOCKED on `BLK-LIQUIDATION-HISTORICAL-CENSUS` |
| Coinbase/Bitfinex missing hours | Re-requested through the existing adapters (USD 0); any hour still missing stays a preserved gap |

**Total acquisition cost: USD 29** (one CoinGlass Hobbyist month). It would be
USD 4,229 if V4 picks Tardis for liquidations. **Nothing was purchased.** RBT-003
does not scope any owner-less input.

**Design decisions.**

1. The enumeration covers owner types *and* call-site parameters. It is strict
   both ways (unclassified and stale), and duplicate owners are refused.
2. A derived input carries its upstream families. Raw-leaf counts are reported
   separately.
3. Earliest dates are completeness only, and each is labelled
   `MEASURED_FROM_RESEARCH_DATABASE` or `PROJECTED_FROM_SOURCE_DEPTH`. An
   undefined input is never guessed. A composite reports its blocking inputs
   and a lower bound.
4. The read-only discipline has three layers: the statement guard, the
   read-only engine option and the session-setting check.
5. Probes are provenance plus metadata, and no third-party value is stored.
   - Two responses (Kraken v4 funding and v3 recent trades) cannot be
     date-filtered and included holdout or reserve rows. Only their timestamps,
     type labels and uids were inspected. Nothing was printed or stored, and
     neither was re-fetched.
   - One exploratory probe printed `markPrice` strings from 2022-11-09 to the
     session terminal. They were not persisted anywhere.
6. Certified EPIC X liquidation definitions are reused by reference, never
   restated.

**Validation.** All runs used `.venv312` CPython 3.12.14. The proof suites ran
alone, with same-device temporary roots outside the repository.

| Suite | Result |
| --- | --- |
| Focused `test_research_backtest_coverage.py` | **60 passed** |
| RBT-001 `test_research_backtest_replay_inputs.py` + `_replay_review.py` | **167 passed** |
| Closure table `test_us_equity_market_closures.py` | **145 passed** |
| BTC-180..185 (`test_backtest_engine`, `_engine_review`, `_cost_model`, `_walk_forward`, `_regime_performance`, `_setup_performance`, `_threshold_sweeps`, `_epic_s_integration`) | **282 passed** |
| BTC-220..224 (`test_feature_score_boundary`, `test_quant_comparisons`, `test_look_ahead_bias`, `test_risk_invariants`, `test_paper_execution`, `test_golden_scenarios`) | **342 passed** |
| Owners the inventory reads (flow, positioning, volatility, trend, structure, derivatives collector and quality, OHLCV, market bars) | **320 passed** |
| V5 recomputation (`test_reference_composite_v5`, both prospective-corpus suites, `test_etf_flows`) | **407 passed**, 2 pre-existing composite skips. `v5_protocol_definition` recomputes independently to `95e43ee1...775a89`, equal to the persisted protocol |
| PAD5, complete `test_etf_calendar_replay_verified_evidence.py`, run alone | **117 passed** (447 s). On the final code, the authority, namespace and frozen-module subset passed **4/4**, and the namespace restores `54675984...f483` |
| PAD4-R5 `test_persisted_namespace_reproduces_exactly` and `test_child_order_variation_does_not_change_the_parent`, run alone | **2 passed**, twice (once before and once after the final fixes); the namespace restores `b4168dc9...61c7` |
| `python -m compileall -q btc_predictor etf_calendar_worker`; `git diff --check` on the staged files | **PASS** |

The focused suite includes:

- fresh-process determinism under `PYTHONHASHSEED` 0/1/8675309 from another
  cwd;
- the persisted inventory rebuilt byte for byte from its own snapshot, with its
  digest and report;
- owner-parity checks: the real funding, volatility-percentile and ETF-window
  owners are complete at the derived instant and incomplete just before it.

The BTC-180..185, BTC-220..224, owner and V5 suites ran before three
self-review fixes. Those fixes touched only the new module, which none of
those suites import. The full repository suite was **NOT RUN**: no production
module changed.

**Remaining risks and limitations.**

- UNVERIFIED:
  - Coinalyze depth and its Kraken symbol;
  - CoinGlass Kraken pair support;
  - every issuer site and Farside;
  - Tardis and Kraken redistribution terms;
  - the Kraken REST liquidation label's equivalence with the websocket type
    (the probed recent window had no liquidation).
- Shared earliest dates are projections until RBT-003 persists the series.
- CoinGlass ETF flows are aggregator values whose date convention RBT-003 must
  check against an issuer where one is reachable.
- Binance's early `metrics` files carry duplicate slots.
- This is not the independent review.

### RBT-002 review outcome

**Date:** 2026-10-01. **Review:** independent xHigh ticket review under
`prompts/review_ticket.md`, against implementation `ab210a5`, documentation
`d5daa0b`, base `1e7c64e`, and V4 authority at `9a90313`.
**Result: FAIL — RELEASE BLOCKING.** RBT-002 is not DONE. RBT-002A and RBT-001A
remain blocked. The four owner-adopted V4 data rules and the choice of the
completion spec are unchanged; no owner choice was reopened.

**Distinct review-fix:** `0b06a85`. It changes only the unbound coverage module,
its original test module, a new independent review regression module, and the
three inventory artifacts. It adds `MEASURED_MOVE_REFERENCE`, separates the
existing volume fallback from undefined inputs, and strengthens the SQL test.
It does not repair the broader owner registry. The regenerated digest is
`b4b51fc4e46fee18c4d228f985e2efaeb6db6d577916e2390ac35398aed6a106`.
The original `b7b9a20b...be3bf0` remains available at `ab210a5`.

**Findings.** Locations below refer to the reviewed implementation unless a
current owner symbol is named.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer, correction and missing regression |
| --- | --- | --- | --- |
| R1 / **P1 OPEN** | `coverage.py:620`, `:1306`, `:1355`, `:2048`; `test_research_backtest_coverage.py:94` | The enumeration mechanically checks only a hand-selected registry, and its completeness test derives its expected set from that same registry. It omits actual consumed input types and internal default parameters. A complete §5A census must discover or independently account for those owners. The 36/68/592 counts prove registry consistency, not decision-path completeness. RBT-002A cannot be released on that claim. | `AnchoredVwapAnchor` has 13 fields, `OhlcvQualityConfig` 4, and `DerivativesQualityConfig` 6; all are absent. Replace each module's type in memory with a fixture clone carrying one extra defaulted field: enumeration still returns 592. `reward.select_reward_reference.major_timeframes = ('1w', '1mo')` is consumed inside the registered `reward_risk_for_stop`, but has no row. Correct the owner/helper/config census and audit all resulting inputs, then regenerate the inventory. Add regressions that discover these types independently of the registry and fail when each gains a defaulted field or a reached helper gains a parameter. This is larger than the small review-fix. |
| R2 / **P1 FIXED** | `coverage.py:1872` (now `reward_risk_for_stop.measured_move`) | A `DERIVED_BY_OWNER` row claimed the Bull Trend Continuation detector produced a measured-move reward reference. Its result has no target `price`/`level_price` or measured-move geometry. Rulebook §15 names this tier but supplies no target recipe. Hiding it excludes a real owner-less input from the completion spec. | Compare `dataclasses.fields(BullTrendContinuationResult)` with `reward._level_references`; the latter needs a target price and PIT `detected_at`. Review-fix classifies `MEASURED_MOVE_REFERENCE` as undefined and adds it to the setup blocker. Independent regression `test_measured_move_has_no_target_in_the_claimed_producer` checks both the alleged producer and the inventory. `None` omits tier four; the other tiers still evaluate. The spec must explicitly resolve or omit it. |
| R3 / **P2 FIXED; compatibility gap remains** | `coverage.py:1012`, `:1676`, `:2502`, `:3826`; Rulebook §9.2; `levels/strength.py:184` | Volume was grouped with inputs having no Rulebook definition/fallback. §9.2 already supplies core weights without volume. V4 §6A.2 requires that precedence. A new volume-percentile parameter would bypass existing authority. The frozen owner nevertheless requires every component, even one with zero weight. | Call `calculate_level_strength` with valid synthetic non-volume inputs, volume `None`, and core weights plus volume weight 0: it remains incomplete. Review-fix records `OWNERLESS_RULEBOOK_FALLBACK` / `UNIMPLEMENTED_RULEBOOK_FALLBACK`, removes volume from the undefined blocker membership, and preserves its incompleteness. Independent regression checks authority classification and actual owner rejection. RBT-002A must cite the fallback and disclose the owner compatibility problem. It may not zero-fill or copy a scoring formula. Any correction requiring a frozen owner edit needs explicit cross-workstream authorization under §9. |
| R4 / **P2 FIXED** | `test_research_backtest_coverage.py:400` | The claimed no-value-column test recognized only double-quoted names. PostgreSQL accepts bare names, so a real `SELECT close, ...` mutation passed it. Current generated SQL is value-free, but the regression did not protect that claim. | Monkeypatch `data_window_times_sql` to insert `close,` after `SELECT`; the original test passes. The strengthened identifier check rejects quoted, bare, uppercase, qualified and aggregate selections. Five independent mutation cases pass. This is a test guard for the generated SQL, not a general-purpose SQL security parser. |
| R5 / **P3 procedural disclosure** | RBT-002 Implementation Notes, Design decision 5; inventory probe records | Two non-date-filterable Kraken responses included holdout/reserve metadata; one probe printed 2022 mark prices. The reported metadata did not open the economic holdout, but those endpoints/output are unsuitable collection procedures. | The original terminal contents are not independently available; classification is conditional on the disclosed facts. RBT-003 needs endpoint-range verification, timestamp-only projection before value decoding, strict date bounds, and redacted metadata-only logs. Missing regressions: an endpoint ignoring its range must reject out-of-window records before value decoding/persistence, and captured logs must contain no price/quantity fields. See disclosure rulings below. |

**Scope and reproducibility.** Independently checked:
`git diff --diff-filter=MDRT 1e7c64e ab210a5` is empty; the
`ab210a5..d5daa0b` diff contains only the two documentation files. Executing the
original module from `git show ab210a5:...` over the original stored snapshot
reproduces the original canonical JSON and digest byte for byte. The reviewed
CLI `rebuild` reproduces all three artifacts; fresh processes under hash seeds
0/1/8675309 from a temporary cwd reproduce the reviewed JSON exactly.
An independently created fixture input with an extra defaulted field fails
`UNCLASSIFIED_FIELD` when registered. R1 demonstrates that an omitted owner
does not get that protection. Defaults and keyword-only parameters of the
registered owners are included; helper construction is covered only where
manually listed (`VolumeParticipationObservation`, `StructureScoreInput`,
`LevelStrengthInput`), not universally. Hold/add/trim/exit are registered, but
that alone does not close their transitive inputs.

**Per-input rulings.** Each of the original 24 unique IDs was searched in owner
functions/helpers, `config/strategy/default.toml`, relevant Rulebook sections,
Structured Tickets Implementation Notes, certified EPIC X V1 definitions and
research corpus V2. Config weights, bands and trigger thresholds do not define
the missing measurement, horizon or predicate. No original input was found
`DEFINED_ELSEWHERE`. Existing helpers are candidates for the completion spec;
they do not silently supply an unspecified parameter or mapping.

| Input ID | Ruling | Independent reason / definition citation |
| --- | --- | --- |
| `TREND_Z_M4` | CONFIRMED_UNDEFINED | Rulebook §§5.1–5.2 and `TrendScoreInput.z_m4`: raw 28-day momentum exists, but normalization window/minimum is unspecified. |
| `TREND_Z_M12` | CONFIRMED_UNDEFINED | Same distinction for raw 84-day momentum and `z_m12`. |
| `TREND_Z_20W` | CONFIRMED_UNDEFINED | `twenty_week_ma_distance_from_weekly_bars` defines the raw distance, not its z-score history. |
| `TREND_Z_52H` | CONFIRMED_UNDEFINED | `fifty_two_week_high_distance_from_weekly_bars` defines the raw distance, not its z-score history. |
| `FLOW_Z_ETF_NORM_5D` | CONFIRMED_UNDEFINED | Rulebook §6.2 / `five_day_etf_flow` define the normalized flow; `FlowScoreInput` requires a separately supplied z-score. |
| `FLOW_Z_ETF_NORM_20D` | CONFIRMED_UNDEFINED | Same distinction for `twenty_day_etf_flow`. |
| `FLOW_Z_FLOW_ACCEL` | CONFIRMED_UNDEFINED | `etf_flow_acceleration` defines acceleration, not its normalization history. |
| `RANGE_PERCENTILE` | CONFIRMED_UNDEFINED | `OrderlinessScoreInput` and CAPITULATION/EUPHORIA consume it; thresholds 95 etc. do not select a range quantity/window/minimum. |
| `DOWNSIDE_RETURN` | CONFIRMED_UNDEFINED | Orderliness/STRESS/CAPITULATION thresholds exist; no return horizon or producing call exists. Generic simple-return helpers are candidate conventions only. |
| `UPSIDE_RETURN` | CONFIRMED_UNDEFINED | Same horizon gap in `EuphoriaFlagInput`; the 0.12 trigger is not a measurement definition. |
| `LEVEL_REACTION_MAGNITUDE` | CONFIRMED_UNDEFINED | Rulebook §9.2 specifies reaction relative to ATR but leaves `f`/measurement horizon unspecified; the owner consumes a caller-supplied fraction and maps it using `reaction_full_fraction`. No helper measures it. |
| `LEVEL_VOLUME_PERCENTILE` | **RULEBOOK_FALLBACK_EXISTS** | Rulebook §9.2: timeframe 0.30, touches 0.25, reaction 0.25, confluence 0.20, without volume. Removed from the spec's undefined-parameter list; retain the explicitly recorded frozen-owner compatibility gap. |
| `SEVERE_CROWDING_STATE` | CONFIRMED_UNDEFINED | `calculate_crowding_flag` defines CROWDING, not a severe grade or the mapping into `HardVetoInput`. V4 conservatism supplies precedence for the forthcoming spec, not an already executed mapping. |
| `MOMENTUM_PERSISTENCE_SCORE` | CONFIRMED_UNDEFINED | Rulebook §20 / `HoldScoreInput` consume a 0–100 component. The momentum module produces raw momentum only. EPIC X V1's `DERIVED_STATE_INPUTS` module reference is not a formula. |
| `NEW_STRUCTURE_SCORE` | CONFIRMED_UNDEFINED | Rulebook §21 / `AddScoreInput`: ordinary structure is defined; newness/normalization for this component is not. |
| `ADD_MOMENTUM_SCORE` | CONFIRMED_UNDEFINED | Rulebook §21: raw momentum and TrendScore exist; neither establishes this separately supplied 0–100 Add component. |
| `NEW_STRUCTURAL_CONFIRMATION` | CONFIRMED_UNDEFINED | Rulebook §18.1 / `AddRequirementsInput`: trailing structure and higher-low results are candidates, but the qualifying add predicate is not selected. |
| `REGIME_SUPPORTIVE_PREDICATE` | CONFIRMED_UNDEFINED | Regime score/classification bands exist; their mapping into the add predicate is not defined. |
| `FLOW_SUPPORTIVE_PREDICATE` | CONFIRMED_UNDEFINED | Flow scores/bands exist; the add wrapper accepts this explicit bool and does not compute it. |
| `REGIME_INVALIDATION_PREDICATE` | CONFIRMED_UNDEFINED | Rulebook §§20,26 / `exit_rules_for_position`: direction-specific invalidation is an external bool; regime classifications do not select the exit predicate. |
| `DATA_RISK_EXIT_PREDICATE` | CONFIRMED_UNDEFINED | The data-quality gate blocks ENTER/ADD; it does not choose a full exit. The exit owner accepts a separate bool. |
| `CORRECTION_FROM_LOCAL_HIGH` | CONFIRMED_UNDEFINED | Rulebook §12 / `BullishResetInput`: correction bounds exist and swing/high helpers exist, but the local-high selection is unspecified. The original claim that no high owner exists was too broad. |
| `DISTRIBUTION_STATE` | CONFIRMED_UNDEFINED | Bearish Distribution consumes the asserted state; no producing predicate is defined. Inert under long-only scope. |
| `SHORT_TRIGGER` | CONFIRMED_UNDEFINED | Bearish Distribution consumes the asserted trigger; no short trigger mapping is defined. Inert under long-only scope. |
| **`MEASURED_MOVE_REFERENCE` (new)** | CONFIRMED_UNDEFINED | Rulebook §15's fourth reward tier is named without target geometry. `reward._level_references` needs target price and PIT detection time; `BullTrendContinuationResult` produces neither. Optional absence must be explicit in the spec. |

`LIQUIDATION_PERCENTILE` is outside that undefined list: its certified V1
adapter/capture/census references and hashes reproduce. V4 adopts a historical
hour-completeness replacement only. Corpus V2's `_owner_parameters` and
`owner_evaluability_census` offer warm-up/selector candidates; its composite
conjunctions do not define these missing numeric adapters. V2 is failed,
non-certified and unused, and is never cited here as authority. BTC-041
`features.rolling.rolling_zscore` / `rolling_percentile`, positioning's
prior-window helpers, and the volatility percentile conventions are useful
existing-owner candidates under V4 §6A.2.

**Confirmed minimum RBT-002A coverage: 24 undefined IDs** (23 from the original
list, plus the newly discovered measured-move input):

```text
TREND_Z_M4, TREND_Z_M12, TREND_Z_20W, TREND_Z_52H
FLOW_Z_ETF_NORM_5D, FLOW_Z_ETF_NORM_20D, FLOW_Z_FLOW_ACCEL
RANGE_PERCENTILE, DOWNSIDE_RETURN, UPSIDE_RETURN
LEVEL_REACTION_MAGNITUDE, SEVERE_CROWDING_STATE
MOMENTUM_PERSISTENCE_SCORE, NEW_STRUCTURE_SCORE, ADD_MOMENTUM_SCORE
NEW_STRUCTURAL_CONFIRMATION, REGIME_SUPPORTIVE_PREDICATE, FLOW_SUPPORTIVE_PREDICATE
REGIME_INVALIDATION_PREDICATE, DATA_RISK_EXIT_PREDICATE
CORRECTION_FROM_LOCAL_HIGH, DISTRIBUTION_STATE, SHORT_TRIGGER
MEASURED_MOVE_REFERENCE
```

Also cite and account for `LEVEL_VOLUME_PERCENTILE` through the **existing
fallback**, without defining a new percentile. The reviewed registry still has
592 rows / 36 types / 68 call sites: 35 undefined occurrences, two fallback
occurrences, three certified-definition occurrences and 189 derived occurrences.
**This is the final confirmed list from this review, not a completeness sign-off:**
R1 must be fixed and re-reviewed; newly discovered inputs can enlarge it before
RBT-002A becomes dependency-satisfied. No definition/spec work is authorized by
this failed review.

**Missing-input consequences.** Reading the owners independently confirms:
trend's required `Decimal` inputs raise `RuntimeError` on `None`, so a composer
must report structural unevaluability rather than call it with missing values.
Flow core, orderliness/volatility and strength/structure propagate incomplete
scores. Hard veto treats severe-crowding `None` as missing and blocks. Hold's
missing momentum persistence prevents a complete score; missing add components
and required predicates block every add. Bullish Reset's missing local-high
correction prevents detection. The unchanged long-only engine/config rejects
short intents. Structural-stop exits still work: `exit_rules._evaluate` checks
them independently of Hold Score completeness. No real-data outcome was run.

**Database reproduction: UNVERIFIED in this review environment.** No
`POSTGRES_*` or `PGOPTIONS` variables were exported. The mandated environment
URL helper raises `ValueError`; no URL, credentials or `.env` were read or
printed, and no database query was made. The read-only environment was requested
but was not supplied during review. Consequently the following remain stored
snapshot claims, not independent live-database confirmations:

| Snapshot claim | Recorded metadata |
| --- | --- |
| Bitstamp | 52,608 complete hours, no gap |
| Coinbase | 52,597 hours; 11 missing in 5 runs |
| Bitfinex | 52,592 hours; 16 missing in 7 runs |
| Other raw input families / generic series | empty |
| December 2019 | 2,232 rows, 744 per venue, outside the sealed sample but prohibited by §3 |
| Holdout / reserve observations | zero; three composite `available_at` values on 2026-01-01 00:05 belong to 2025-12-31 observations |

The arithmetic and stored gap-run metadata were checked, without reading any
economic value. A closure review must run its own timestamp/identity-only SQL:
first require both read-only settings `on`; then count/min/max observation
instants by venue/window, count all other family tables, use a data-window
`generate_series` anti-join for missing hours/runs, and scan observation versus
availability time columns separately. Connect only through
`btc019_empirical._database_url_from_environment`; do not source `.env`.
The repaired SQL mutation regression is genuine; read-only transaction options
and the refusal of a session with read-only `off` also pass offline tests.

**Independent earliest-date recomputation.** A separate timestamp-bucket census
(not `venue_bar_series` or `earliest_evaluable_inputs`) expanded stored gap
runs, removed incomplete UTC daily/weekly buckets, and indexed windows read
directly from the momentum/trend/swing/volatility/positioning owners. No market
values were used. Because live database reproduction is unavailable, venue
dates are conditional on the stored timestamp snapshot. Shared dates remain
`PROJECTED_FROM_SOURCE_DEPTH`, not acquired complete series or actual scores.

| Venue | Positioning projection | Trend lower bound | Volatility lower bound | Structure lower bound | Flow lower bound |
| --- | --- | --- | --- | --- | --- |
| Bitstamp | 2020-10-02 | 2021-01-04 | 2022-05-29 | 2020-02-24 | 2024-02-10 |
| Coinbase | 2020-10-02 | 2021-01-25 | 2022-05-29 | 2020-03-02 | 2024-02-10 |
| Bitfinex | 2020-10-02 | 2021-01-18 | 2022-05-29 | 2020-03-02 | 2024-02-10 |

The positioning leaves reproduce 2020-01-11 08:00 (30 prior funding
settlements), 2020-09-09 06:00 (7-day OI growth + 30 prior hourly growths),
2020-08-02 07:00 (30 prior basis closes), and 2020-10-02 (30 prior daily
OI/market-cap joins plus publication lag). The source price windows are
28/84 daily lookbacks, 20/52 weekly rows, and the swing owner's left/right
confirmation window. ETF's 20 publication dates, including the reviewed
closure table, end on 2024-02-08 and become available on February 10.
Liquidations start with the first *complete* UTC day, May 28, 2021; 365 prior
days make the May 28, 2022 observation available on May 29. Positioning also
requires nonzero variance: the date is a history-count projection, not a
guarantee of evaluability. New normalization windows, gaps, actual structural
levels and the unimplemented volume fallback can delay these lower bounds.

**Independent source re-probes, metadata only.** Kraken calls used both `since`
and historical `before`; analytics used historical `since`/`to`. Binance requests
named only 2020 archive files. No holdout/reserve observation values were fetched
or inspected. Prices and quantities were never displayed or persisted.

| Source | Independent result | Limits / license |
| --- | --- | --- |
| [Kraken REST executions](https://futures.kraken.com/api/history/v2/market/PI_XBTUSD/executions?since=1577836800000&before=1622160000000&sort=asc) | 1,000 executions; first 2021-05-27 11:55:25.097; original response digest `7f76a621…` reproduces. Bounded November 9, 2022 page has six `takerOrder.orderType = Liquidation` labels, hash `c79c0d03…`. | Adequate depth for V4; full contiguous pagination/hour census is not proven by one metadata page. REST/websocket label equivalence and redistribution terms remain UNVERIFIED. |
| [Kraken hourly liquidation volume](https://futures.kraken.com/api/charts/v1/analytics/PI_XBTUSD/liquidation-volume?interval=3600&since=1582675200&to=1582761600) | Prior-day response has no timestamps; February 26 starts at 12:00 UTC, 13 boundary timestamps through February 27 00:00. Hash `d803c7c8…` reproduces. | Corroborating totals only; timestamp presence does not validate values or side/event coverage. |
| [Binance quarterly archive](https://data.binance.vision/data/futures/cm/monthly/klines/BTCUSD_200925/1h/BTCUSD_200925-1h-2020-08.zip) / [index archive](https://data.binance.vision/data/futures/cm/monthly/indexPriceKlines/BTCUSD/1h/BTCUSD-1h-2020-06.zip) | Quarterlies: 744 first-column timestamps from 2020-08-01. Index: 519 from 2020-06-09 09:00. Both original hashes reproduce. | V4 contract adopted, not re-decided. [Binance public-data license](https://github.com/binance/binance-public-data): CC BY-NC-SA 4.0; attribution, non-commercial scope and applicable share-alike obligations. |
| [Binance USD-M funding](https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2020-01.zip) | 93 settlement timestamps, first 2020-01-01 00:00; hash reproduces. | First settlement prices a prohibited 2019 interval and is refused. |
| [Binance OI metrics](https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2020-09-01.zip) | 576 rows / 288 distinct 5-minute timestamps from 2020-09-01 00:00. Prior-day file 404. Hash `9a9c0518...57722ae3` reproduces. | RBT-003 must resolve duplicate slots without double counting and sample declared hourly instants. Timestamp duplicates alone do not prove identical values. |
| [Binance USD-M perp klines](https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip) | 744 hourly open timestamps from 2020-01-01; hash reproduces. | Interval start; selected source remains required by the derivatives quality owner even with ETF_CORE. |
| [Coin Metrics catalog](https://community-api.coinmetrics.io/v4/catalog-all-v2/asset-metrics?assets=btc&metrics=CapMrktCurUSD) | Catalog metadata confirms daily `CapMrktCurUSD` starts 2010-07-18. No observation values requested. | RBT-003 starts at 2020 only. [Community data license](https://github.com/coinmetrics/data/blob/master/README.md): CC BY-NC 4.0, attribution and non-commercial use. Do not confuse API-code licensing with data licensing. |
| [CoinGlass flow docs](https://docs.coinglass.com/reference/etf-flows-history), [per-fund history docs](https://docs.coinglass.com/reference/etf-history), [pricing](https://www.coinglass.com/pricing) | Both documented for Hobbyist; flow example starts 2024-01-11; plan USD 29/month, USD 348/year. | **DOCUMENTED, actual historical flow/AUM depth UNVERIFIED** without authenticated queries. A sample timestamp and all-time daily plan do not prove complete per-fund AUM from launch. Hobbyist is personal use; do not publish/redistribute purchased data or use it commercially without suitable rights. Publication/vintage coverage is UNVERIFIED. |
| [Tardis pricing](https://tardis.dev/), [billing FAQ](https://docs.tardis.dev/faq/billing-and-subscriptions) | Perpetuals monthly-equivalent Academic 350 / Solo 700 / Professional 1,000 / Business 3,000; annual totals 4,200 / 8,400 / 12,000 / 36,000. Academic/Solo/Pro annual history is four years; Business all available. | At an October 1, 2026 start, four years reaches October 1, 2022, not 2021. Academic eligibility required. Dataset coverage/incident census and redistribution rights remain UNVERIFIED by this review. |
| Other candidates | UNVERIFIED | Coinalyze authenticated depth/symbol; CoinGlass Kraken pair support; issuer/Farside full history; CoinGecko paid depth; Kraken fixed-maturity/Tardis data. None was silently promoted. |

**V4 liquidation feasibility:** confirmed REST depth starts May 27, 2021, so
the 365-day depth requirement is reachable around May 27, 2022, well before
ETF-era decisions. This is source-depth feasibility only. The first fully
admitted daily observation is May 28, 2021, and the strict prior-observation
percentile is projected available May 29, 2022. RBT-003 must prove at least 365
actual fully observed days with an unbroken execution continuation chain,
nonempty executions in every hour, incident exclusions and agreement with the
hourly totals. Neither one-page depth nor an analytics timestamp grid proves
that census. No liquidation value comparison was performed in this review.

**Disclosure classifications:**

| Disclosure | Policy V4 §3 | Policy V4 §6A.1 | Ruling / RBT-003 guard |
| --- | --- | --- | --- |
| Kraken v4 funding / recent v3 trades, non-filterable responses with holdout/reserve timestamps/type labels/IDs only, nothing stored | Record metadata exposure. Conditional on the disclosure, economic values were not read or collected: holdout remains NOT COLLECTED. Do not call this a verified no-response exposure. | No reported real-data score, signal, trade or performance was computed/inspected; no pre-registration violation established. | P3 procedure. Do not repeat these probes. Require server date filters or a reviewed transport projection that rejects/truncates out-of-window records before value parsing/logging/persistence; inability to bound an endpoint makes it unsuitable. |
| Printed November 2022 mark prices | Data-window values, no holdout/reserve exposure. | Raw prices are not a score/signal/trade/performance result; no such result was reported. | P3 breach of this ticket's metadata-only discipline. No strategy conclusion may be drawn from them. Use timestamp/type-only projections, no raw payload printing, response hashes and sanitized failures. |

**Review validation (own runs):** original focused **60**; RBT-001 **167**;
closure table **145** (combined original run **372**); BTC-180..185 **282**;
BTC-220..224 **342**; enumerated owner-module suites **320**;
V5/corpus/ETF suites **407 passed, 2 existing skips**. Independently recomputed
V5 = `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`.
On the review-fix, focused coverage **65** plus new independent review
regressions **2**, total **67 passed**; RBT-001/closure rerun **312 passed**.
CPython `.venv312` is **3.12.14**. PAD5 preserved-authority, predecessor,
namespace, child-order and frozen-module reproductions **5 passed** at
`54675984...f483`; PAD4-R5 namespace and child order **2 passed** at
`b4168dc9...61c7`. The full 117-test PAD5 proof suite and whole-repository suite
were **NOT RUN**; those counts are not claimed. `compileall -q btc_predictor
etf_calendar_worker` and `git diff --check` pass. No frozen source or namespace
was edited. Representative commands are the exact named modules in the
Implementation Notes' validation table, with the new coverage-review module;
namespace tests were selected by their named node IDs above.

**Acceptance verification / next work:** artifact reproducibility, scope,
existing registered-field checks, missing-input consequences, stored-snapshot
date recomputation and safe source depth/cost checks pass with the stated
limits. Full input-surface completeness **FAILS** (R1); live database coverage
and forbidden-window exposure checks are **UNVERIFIED**. No complete
acceptance sign-off is issued. Next dependency-satisfied EPIC Y work is the
RBT-002 registry correction followed by independent re-review in the supplied
read-only database environment. After a PASS, RBT-002A and RBT-001A become ready;
RBT-004 still needs the completion-spec review. EPIC X's next ticket remains
`POSTP1-001V2R1`.

**Safety:** no real-data backtest outcome; holdout **NOT COLLECTED**, its values
never read by this review; BTC-019 untouched, sealed sample unopened; EPIC X
unchanged, `POSTP1-001V2R1` still next; Epic T unchanged. The original disclosures
are retained, not erased by these statements.

### Correction (R1)

**Date:** 2026-10-01. **Correction commit:** `906c719`, on base `f52bcf4`.
**Status:** `CORRECTED / AWAITING INDEPENDENT RE-REVIEW`. It fixes R1 only. R2–R4
stay as fixed by `0b06a85`, R5 is procedural, and no V4 owner choice is reopened.
No new provider probe was made.

**Files.**

- New: `btc_predictor/research_backtest/input_census.py` (roots, discovery,
  tracer, left-out records) and `input_census_registry.py` (pinned snapshot).
- New tests: `btc_predictor/tests/test_research_backtest_coverage_census.py` and
  nine `test_research_backtest_census_trace_g*.py` modules (runtime fixtures).
- Changed: `coverage.py`, `test_research_backtest_coverage.py`, and the three
  inventory artifacts.
- No owner module, EPIC X-bound file, `data/` or `research_artifacts/` file
  changed.

**Roots: the only hand-written list.** `input_census.DECISION_PATH_ROOTS` holds
74 owner entry points the RBT-004/RBT-005 composers (and, for the trailing
write, the BTC-180 engine) call. Each carries its Rulebook area and a
justification. They are the 68 previous call sites plus six new ones:

- `start_position_lifecycle` and `apply_position_event` (Rulebook 26);
- `apply_trailing_stop` (Rulebook 22: the trailing owner's only lifecycle write);
- the three anchored-VWAP anchor builders
  `anchored_vwap_anchor_from_swing_level`, `_from_breakout_level` and
  `_from_capitulation_event` (Rulebook 9.1).

All nine areas the correction names are covered: Entry Conviction and its five
components and their producers; core regime, smoothing and classification; the
four Rulebook 24 flags; hard veto and data quality; setups, triggers and
no-chase; invalidation, ATR, buffer, stop and R/R (reward-reference selection is
reached inside `reward_risk_for_stop`); budget, sizing and risk at stop;
lifecycle, hold, add, add requirements, tranches, trailing, trim and exit; and
the level, structure and AVWAP producers.

**What the roots leave out.** Every function, class and member defined in
`btc_predictor.features`, `.levels`, `.risk` and `.signals`, in
`data.quality` and in `portfolio.state_machine` is either reached or listed in
`LEFT_OUT_OWNER_DEFINITIONS` with a reason. A test requires exact equality.
The 82 entries are:

- batch wrappers;
- the raw-series momentum variants;
- the BTC-041 `rolling_*` helpers (candidate conventions for the completion
  spec, not inputs);
- factor-overlap audit tooling;
- `calculate_volatility_score_from_results` and `rv_7_20_60_from_daily_bars`;
- `volatility_buffer_grid` (BTC-185);
- persistence round-trips (`*_from_record`, lifecycle replay and restore);
- the Rulebook 27 explanation engine;
- their private helpers.

`OUTSIDE_OWNER_SCOPE` gives a reason for every other top-level package.

**Discovery.** `discover_decision_path()` walks btc_predictor from the roots and
resolves every name in the live module namespaces at call time, so an owner
replaced in memory is the one discovered. It reads:

- each function's CPython 3.12 bytecode: globals, closure cells,
  function-local imports, and module/class attribute chains;
- dispatch containers, partials and instances held in globals;
- parameter, return and local annotations (AST);
- defaults;
- for each class: bases, field types and defaults, protocol attributes, and
  every method or property in its body.

Two refusals:

- An in-scope owner name bound to code defined outside the package raises
  `FOREIGN_OWNER_CODE`. Dataclass-generated methods are the only skipped code.
- Two different objects under one path raise `CONFLICTING_OWNER_OBJECTS`.

A call-site analysis of every reached caller's AST decides each defaulted
parameter:

- `NO_REACHED_CALLER_OVERRIDES_THE_DEFAULT`: a fixed constant;
- `A_REACHED_CALLER_PASSES_THIS_ARGUMENT`;
- `A_CALLER_IS_NOT_A_RESOLVED_DIRECT_CALL`: a callback, partial, starred call
  or instance method. This is conservative: such a default is never reported
  as fixed.

**Census.** The census has 74 roots and 882 callables. It has 159 types: 156
dataclasses, 1 protocol (`breakout.SourceLevel`) and 2 exception classes. It
counts 1,412 fields and 1,876 parameters (receivers excluded) over 1,589
resolved call sites. No callable lacks source. The census reaches all three
types the review named:

| type | fields |
| --- | ---: |
| `AnchoredVwapAnchor` | 13 |
| `OhlcvQualityConfig` | 4 |
| `DerivativesQualityConfig` | 6 |

It also reaches the full `StrategyConfig` tree, the config loader (through
owner `config=None` defaults) and `select_reward_reference`.

**Surface and classification.** `enumerate_input_surface()` classifies every
census field and parameter: **3,288 rows**, up from 592. Unclassified owners,
fields and parameters are refused before stale ones. A signature reorder
fails as `SIGNATURE_ORDER_CHANGED`.

| census category | rows | classification |
| --- | ---: | --- |
| `COMPOSER_INPUT_TYPE` | 259 | field by field in `coverage.INPUT_TYPE_FIELD_CLASSIFICATIONS` (the 36 reviewed types, `CapitulationEvent`, `SourceLevel`) |
| `ROOT_PARAMETER` | 367 | field by field in `coverage.ROOT_PARAMETER_CLASSIFICATIONS` |
| `OWNER_OUTPUT` | 948 | `DERIVED_BY_OWNER`. The producer is the reached constructor, and every type has one (tested). Families and components come from the roots that reach it |
| `STRATEGY_CONFIG` | 156 | 28 `StrategyConfig` dataclasses from `default.toml`. The champion config has no unset field |
| `OWNER_CONFIG` | 15 | `OhlcvQualityConfig` 4, `DerivativesQualityConfig` 6, `DecisionTolerance` 2, `RiskBudgetBand` 3 |
| `ENGINE_STATE` | 34 | `PositionLifecycle` 16, `PositionTransition` 14, `Tranche` 4 |
| `INTERNAL_PARAMETER` | 1,407 | new kind `OWNER_INTERNAL_DATAFLOW`: passed by the reached caller, never by the composer |
| `OWNER_DEFAULT_CONSTANT` | 23 | `STRATEGY_CONFIG`: owner keyword defaults that no reached caller overrides |
| `CONFIG_LOADER_PARAMETER` | 79 | `STRATEGY_CONFIG`: `config.strategy` loader internals |

The pinned snapshot `input_census_registry` holds:

- 121 type categories with their field names;
- 808 internal signatures.

It was generated from the discovery and audited. It can neither add nor drop
an owner, because the enumeration requires exact two-way equality.

**Runtime cross-check.** Two independent mechanisms were used.

1. **In-test fixtures.** 202 deterministic synthetic fixture runs drive all 74
   roots under `trace_owner_calls` (`sys.setprofile`, btc_predictor only). Each
   run must trace its root and leave `uncovered_traced` empty. Every root's
   first fixture reaches a complete or accepted result where the owner has
   one. Union: 959 traced functions (nested lambdas and genexprs included) and
   155 constructed dataclasses. **Missed by static discovery: 0.**
2. **Existing owner suites (validation run, not a committed test).** A
   root-scoped tracer, recording only while a root frame is live, ran 1,699
   existing owner tests in 52 modules. All 74 roots were entered: 954
   functions and 124 dataclasses traced. **Uncovered: 0.**

The tracer found no item the static census missed, so no tracer discrepancy
needed a fix. These completeness fixes were made while building the walk,
before the tracer runs:

- skip dataclass-generated and reprlib-wrapped methods;
- enumerate protocol attributes;
- resolve function-local imports;
- treat calls through partials and containers as unresolved, so that a default
  is never falsely fixed;
- refuse foreign code and conflicting objects.

The static audit found no dynamic dispatch outside the census. Every owner
`getattr` reads a field, property or `as_record` of a reached class, or a field
of a fully enumerated config dataclass. No owner uses `TYPE_CHECKING` imports,
and every annotation name in reached code resolves.

**Reviewer reproducers.** The same original-API test file was placed in each
tree's `btc_predictor/tests/`:

| reproducer | `f52bcf4` | `906c719` |
| --- | --- | --- |
| `AnchoredVwapAnchor` clone with an extra defaulted field | FAIL (no error raised; 592 rows) | PASS (`UNCLASSIFIED_FIELD`) |
| `OhlcvQualityConfig` clone | FAIL | PASS |
| `DerivativesQualityConfig` clone | FAIL | PASS |
| `select_reward_reference.major_timeframes` row exists | FAIL (no row) | PASS (`OWNER_DEFAULT_CONSTANT`, `('1w', '1mo')`, no caller overrides) |
| reached helper `reward._level_references` gains a parameter | FAIL (no error raised) | PASS (`UNCLASSIFIED_PARAMETER`) |

The committed census suite also checks:

- reward, quality and quant helpers gaining a parameter;
- a parameter added to any of the 882 reached callables;
- a field added to any of the 157 reached field-bearing types;
- a newly reached callable or type;
- an owner that is no longer reached;
- walk semantics on in-scope fixture code;
- the default-override verdicts.

**Audit of newly discovered inputs.**

- **New owner-less input `CAPITULATION_EVENT`.** Classification
  `OWNERLESS_UNDEFINED`, shape `DERIVED_FROM_UPSTREAM`, family reference price,
  no producer, no Entry Conviction component. It has eight occurrences: the
  seven `CapitulationEvent` fields and the root parameter
  `anchored_vwap_anchor_from_capitulation_event.event`.
  - No owner constructs a `CapitulationEvent`. BTC-093 takes "explicit event
    metadata" from the caller, and the CAPITULATION flag owner returns a flag,
    not an event instant, price or detection time.
  - Rulebook 9.1 names "Anchored VWAPs from important market events" without
    defining the event.
  - AVWAP is an optional Phase 1 enhancement (Rulebook 9.2; BTC-097 "must not be
    required for the Phase 1 score"). Missing behaviour: no event anchor is
    built, while the swing and breakout anchors and every other level still
    evaluate.
  - New blocker `BLK-AVWAP-EVENT-ANCHOR` (`NEEDS_OWNER_DECISION`; under V4 §6A it
    is filled by the completion spec) is not structural and vetoes nothing.
- **No other new owner-less input.**
  - Every new composer-facing item is classified:
    - `SourceLevel`: satisfied by weekly and monthly swing levels;
    - the lifecycle roots: `quantity` and `price` are BTC-180 simulated fills,
      and `stop_price` is the initial or trailing stop;
    - the anchor builders.
  - Every owner-output type a root consumes is produced under another root.
  - The 23 fixed defaults are all defined owner constants, among them
    `select_reward_reference.major_timeframes = ('1w', '1mo')`, the 20- and
    52-week windows, the `1E-12` decision tolerance, transform bounds and
    `nan_policy = 'raise'`. Each `min_periods = None` means the full window.
  - The seven unresolved defaults are the trailing `structure_*` arguments,
    forwarded from the composer-supplied `ConfirmedTrailingStructure`.
- **Changes to existing rows.** All 592 previous rows are kept. Three got more
  precise producers:
  - `cluster_price_levels.levels`: every level producer accepted by
    `_prepare_members`; families price plus volume;
  - `calculate_anchored_vwaps.anchors`: the three anchor builders;
  - `detect_breakout_reclaim_levels.source_levels`: weekly and monthly swings.
- **Unchanged.**
  - The 24 confirmed IDs (including `MEASURED_MOVE_REFERENCE`) keep their
    occurrences and blocker membership.
  - `LEVEL_VOLUME_PERCENTILE` keeps its existing-fallback classification and the
    recorded owner compatibility gap, undecided as instructed.
  - `LIQUIDATION_PERCENTILE` stays certified.
  - Minimum history, earliest dates, family coverage, exposures, sources, the
    acquisition plan (USD 29) and the structural verdict are unchanged.

**RBT-002A coverage list (pending re-review): 25 undefined IDs.**

```text
TREND_Z_M4, TREND_Z_M12, TREND_Z_20W, TREND_Z_52H
FLOW_Z_ETF_NORM_5D, FLOW_Z_ETF_NORM_20D, FLOW_Z_FLOW_ACCEL
RANGE_PERCENTILE, DOWNSIDE_RETURN, UPSIDE_RETURN
LEVEL_REACTION_MAGNITUDE, SEVERE_CROWDING_STATE
MOMENTUM_PERSISTENCE_SCORE, NEW_STRUCTURE_SCORE, ADD_MOMENTUM_SCORE
NEW_STRUCTURAL_CONFIRMATION, REGIME_SUPPORTIVE_PREDICATE, FLOW_SUPPORTIVE_PREDICATE
REGIME_INVALIDATION_PREDICATE, DATA_RISK_EXIT_PREDICATE
CORRECTION_FROM_LOCAL_HIGH, DISTRIBUTION_STATE, SHORT_TRIGGER
MEASURED_MOVE_REFERENCE
CAPITULATION_EVENT (new, R1 census)
```

Plus `LEVEL_VOLUME_PERCENTILE` through the existing Rulebook §9.2 fallback.

**Live database regeneration (read-only, 2026-10-01 20:16 UTC).** The session
exported `POSTGRES_*` and `PGOPTIONS='-c default_transaction_read_only=on'`.
The connection went only through
`btc019_empirical._database_url_from_environment`; no URL, credential or `.env`
was read or printed. The first query returned
`default_transaction_read_only = on` and `transaction_read_only = on`, on
PostgreSQL 17.9, database `btc-swing`.

`coverage collect` used only guarded `SELECT`s. It took counts and
timestamp-only MIN/MAX outside the data window, and series keys and instants
inside it. It named no value column. An independent count-only check
(`generate_series` anti-join, per-window counts) agreed exactly.

| fact | live result | stored snapshot |
| --- | --- | --- |
| Bitstamp `1h` | 52,608 hours, no gap | same |
| Coinbase `1h` | 52,597 hours; 11 missing in 5 runs (2020-01-30 17:00; 2020-09-04 23:00; 2020-10-20 20:00; 2023-03-04 18–20; 2025-10-25 16–20) | same |
| Bitfinex `1h` | 52,592 hours; 16 missing in 7 runs (2020-02-11 11–12; 2020-08-12 21; 2021-06-30 08–09; 2021-10-13 14–16; 2022-10-12 08–11; 2023-03-06 10–11; 2024-05-05 10–11) | same |
| ETF, funding, OI, basis, liquidations, perp volume, generic series | 0 rows each | same |
| Pre-2020 | 2,232 rows: 744 per venue, 2019-12-01 00:00 .. 2019-12-31 23:00, bulk-ingested 2026-08-29 | same |
| Holdout / reserve | 0 raw rows; only `derived.btc_reference_composite.available_at` has 3 values at 2026-01-01 00:05, availability instants of 2025-12-31 observations | same |

**Difference from the stored snapshot: none.** The live snapshot equals the
stored one in every field except `collected_at`.

The new inventory is `0d5f70403f1df2e3600f307283de982e90e9942d5ff19c73724df0a449987e30`.
The live `collect` output equals an in-place `rebuild` byte for byte.

**Validation (`.venv312` CPython 3.12.14).** The PAD proof subsets ran alone.

| suite | result |
| --- | --- |
| Focused: original 65, review 2, census 27, runtime trace 202 | **296 passed** |
| RBT-001 | **167 passed** |
| Closure table | **145 passed** |
| BTC-180..185 | **282 passed** |
| BTC-220..224 | **342 passed** |
| Owner modules (flow, positioning, volatility, trend, structure, derivatives collector/quality, OHLCV, market bars) | **320 passed** |
| V5 / corpus / ETF | **407 passed, 2 existing skips**. `v5_protocol_definition` recomputes to `95e43ee1...775a89` |
| PAD5 authority, predecessor, namespace, child-order and frozen-module subset | **5 passed**; restores `54675984...f483` |
| PAD4-R5 namespace and child order | **2 passed**; `b4168dc9...61c7` |
| Owner suites under the root-scoped tracer | 1,699 passed, 0 uncovered |
| `compileall -q btc_predictor etf_calendar_worker`, `git diff --check` | PASS |
| Rebuild byte-equality; `PYTHONHASHSEED` 0/1/8675309 from another cwd in fresh processes | all three artifacts byte-identical |

The full repository suite and the full 117-test PAD5 suite were **NOT RUN**.

**Disclosures and remaining risks.**

- **Composer contract.** The census is only as complete as the roots. If
  RBT-004/RBT-005 call any other owner function, it must be added as a root,
  because otherwise its parameters are classified as owner-internal.
- **Static limits.** The walk cannot resolve calls through an enclosing
  function's local variables, or methods on objects whose class no reached
  code names. The class-member rule and both tracers mitigate this, and found
  no miss.
- **Digest sensitivity.** The inventory records source locations, so any line
  shift in an owner module changes the digest.
- **Usage limit.** The planned multi-agent audit was cut short by an account
  usage limit. All nine fixture groups landed, but the four audit agents did
  not finish. The composer-facing, default, type-category and completeness
  audits above were therefore done in the main session.
- **Owner observation, not fixed (frozen owner, out of scope).** A fixture
  author reported, and the correction reproduced, that
  `positioning.futures_basis_health` misses its zero-variance guard for a
  constant but non-terminating Decimal series. 60 rows at
  0.015 × 365 / 90 give z = 1 and a complete health score of 83.53. RBT-002A
  and RBT-004 should know this.
- **Rulebook-only level candidates.** Rulebook 9.1 candidates with no owner
  ("previous monthly high/low", "major consolidation boundaries") are not
  owner inputs, so a code census cannot list them.
- **Policy label.** The inventory's policy constant still reads
  `RESEARCH_BACKTEST_POLICY_V3`. The §5A text is identical in V4.

**Safety.**

- No real-data backtest outcome.
- Holdout NOT COLLECTED; its values were never read.
- BTC-019 untouched; sealed sample unopened.
- EPIC X unchanged: `POSTP1-001V2R1` is still its next ticket.
- Epic T unchanged.
- RBT-002A, RBT-001A and RBT-004 were not started.


### RBT-002 re-review outcome

**Date:** 2026-10-01. **Review target:** R1 correction `906c719`, documentation
`4556a01`, previous review-fix `0b06a85` and review record `f52bcf4`, on
`claude/etf-worker-prospective-integration-dixlte` at `4556a01`.
**Attempt result: REVIEW BLOCKED — DATABASE.** This is an incomplete independent
re-review under `prompts/review_ticket.md`, not a replacement verdict. The prior
**FAIL — RELEASE BLOCKING** stands; R1 is not independently closed. RBT-002
remains awaiting re-review, and RBT-002A and RBT-001A remain blocked.

**Mandatory database gate.** The reviewer attempted a connection using only
`btc_predictor.research.btc019_empirical._database_url_from_environment`, with
`current_setting('default_transaction_read_only')` as the intended first query.
The helper raised `ValueError` before an engine or connection could be created.
An independent presence-only check in a non-login shell confirmed that
`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB` and `PGOPTIONS` were all absent. No credential values, URL or
`.env` were read or printed. No database query ran; read-only mode and all live
database facts are **UNVERIFIED**. Per the explicit stop instruction, substantive
review stopped at this gate. The correction's stored snapshot and live-run
claims were not accepted as substitutes.

**Checks completed before stopping.** The worktree was clean at `4556a01` on
the requested branch. `.venv312` reports CPython **3.12.14**.
`git diff --stat f52bcf4 906c719` lists only EPIC Y research-backtest modules,
their tests and three inventory artifacts (17 files).
`git diff --stat 906c719 4556a01` lists only this roadmap and `CURRENT_STATE.md`.
These preliminary scope observations do not establish census correctness or
acceptance completion.

**Not performed.** Inventory re-hash/rebuild/determinism; root and left-out
audits; independent adversarial fixtures; tracer line/branch measurement;
in-memory injection verification; classification sampling; live timestamp-only
database reproduction; the four raised-item rulings; the four audit-area
re-audits; focused/regression/proof suites, namespace digest checks and
compileall. No test counts or additional input classifications are claimed.
The earlier test baseline remains unchanged. Documentation-only
`git diff --check` **passed** for this attempt record.

**Coverage and decisions.** There is no final re-reviewed RBT-002A coverage
list. The previous review's 24 confirmed undefined IDs and separate existing
volume fallback remain its rulings; the correction's proposed addition of
`CAPITULATION_EVENT` (25 total) is pending independent review. The AVWAP
classification, futures-basis zero-variance issue, policy label, line-position
digest sensitivity and composer guard remain unaudited in this attempt.
The fixed V4 owner decisions are unchanged.

**Review-fix:** none. Only this roadmap and `CURRENT_STATE.md` are updated to
record the blocked attempt; no implementation, inventory or test changes.
**Next work:** restore the exported read-only database environment, then
complete the independent xHigh RBT-002 re-review, including its own live
timestamp-only reproduction. Do not start RBT-002A or RBT-001A before a PASS.

**Safety:** no real-data backtest outcome; holdout **NOT COLLECTED**, its values
never read; BTC-019 untouched, sealed sample unopened; EPIC X unchanged,
`POSTP1-001V2R1` still its next ticket; Epic T unchanged.

#### Repeated database-gate attempt at `5ec8535`

**Date:** 2026-10-01, approximately 20:53 UTC. **Target:** unchanged R1
correction `906c719`, documentation `4556a01`, now checked out at blocked-attempt
record `5ec8535` on the requested branch. **Attempt result: REVIEW BLOCKED —
DATABASE.** The prior **FAIL — RELEASE BLOCKING** remains the verdict. This is
another incomplete attempt, not an independent confirmation of the correction.

The reviewer independently invoked
`btc_predictor.research.btc019_empirical._database_url_from_environment` from
`.venv312` CPython **3.12.14**, in a non-login shell. All five required
`POSTGRES_*` variables and `PGOPTIONS` were absent (presence-only output).
The helper raised `ValueError` before engine creation. The intended first
query was `SELECT current_setting('default_transaction_read_only')`; no query
executed. No URL, credentials, `.env` or value columns were read or printed.
This was missing configuration, not a database network failure.

The clean worktree and requested branch were confirmed. The correction diff
lists 17 EPIC Y module/test/inventory files; `906c719..4556a01` lists only the
two documentation files. These scope checks do not establish acceptance.
The explicit stop instruction prevented further substantive review: no
adversarial-pattern table, branch-coverage measurement, classification verdict,
live counts, four raised-item rulings, four independent re-audits, inventory
verification or test-suite counts are claimed. No final RBT-002A coverage list
is approved. The previous 24 confirmed IDs and separate volume fallback remain
the prior review's rulings; the proposed 25-ID list remains pending.

Only this roadmap and `CURRENT_STATE.md` change. **Review-fix: none.**
Documentation-only `git diff --check` passed; the test baseline is unchanged.
RBT-002A and RBT-001A remain blocked. Next: provide the exported read-only
database environment to the command process, then complete the required
independent re-review. Owner V4 decisions remain fixed.

**Safety:** no real-data backtest outcome; holdout **NOT COLLECTED**, its values
never read; BTC-019 untouched, sealed sample unopened; EPIC X unchanged,
`POSTP1-001V2R1` still its next ticket; Epic T unchanged.

#### Completed independent xHigh re-review at `2157aed`

**Date:** 2026-10-01. **Ticket:** RBT-002. **Reviewed implementation:** R1
correction `906c719`, with documentation `4556a01`, previous review-fix
`0b06a85` and review record `f52bcf4`; clean requested branch initially at
`2157aed`. **Result: FAIL — RELEASE BLOCKING. R1 remains OPEN.** This completed
review supersedes the two database-blocked attempts as the latest assessment;
it does not reverse the prior FAIL. RBT-002A and RBT-001A remain blocked.
The fixed V4 data decisions and completion-spec choice were not reopened.

**Distinct review-fix:** `a281378` fixes the optional AVWAP component
mapping and inventory policy identity only, with independent regressions and
regenerated inventory. It does not fix R1 or any frozen owner. Inventory
before: `0d5f70403f1df2e3600f307283de982e90e9942d5ff19c73724df0a449987e30`;
after: `a68e5284e99e39b113c7ed2705ca533c1c2cfc0e0a6432dde9fcd7de40ad765d`.

**Findings and raised-item rulings.** All locations are repository-relative.

| ID / severity / disposition | Location; actual versus required behavior; consequence | Independent reproducer, correction and regression |
| --- | --- | --- |
| R1-RR / **P1 OPEN, release blocking** | `btc_predictor/research_backtest/input_census.py:982`, `:1068`, `:1204`; `btc_predictor/risk/trailing.py:272`. The walker visits nested bytecode but creates parameter records only for live function objects. The real local helper `calculate_trailing_stop.<locals>.held` consumes `reason`, `candidate=None`, `complete=True`, none with a surface row. The tracer accepts any nested callable through its ancestor, masking the omitted input-bearing callable. §5A requires discovery and classification of these inputs, including internal defaults, before claiming completeness. | Recompile the actual trailing owner in memory, preserving filename/line positions, adding `independent_new_input=True` to `held` and using it in the `complete` argument to `_result`. The helper runs; surface stays **3,288 rows, identical**, its new input has no row, and `uncovered_traced` remains empty. New independent tests `test_nested_trailing_helper_parameters_are_enumerated` and `test_new_nested_live_input_is_refused` explicitly XFAIL; the latter run with `--runxfail` fails **DID NOT RAISE InputSurfaceError** after proving execution and equal rows. Required correction: discover named local function code objects/signatures/defaults/call sites and classify them; independently account for lambda/comprehension inputs; remove the unconditional ancestor exemption for input-bearing nested functions; extend live mutations to the enlarged set; regenerate/re-review. This exceeds a small review fix. |
| R6 / **P2 FIXED** | `btc_predictor/research_backtest/coverage.py:1335`, `:2172`. `CAPITULATION_EVENT` claimed no Entry Conviction component because AVWAP is optional. Included event AVWAP changes cluster confluence, LevelStrength and thus Structure Score. Optionality controls requiredness, not dependency. | Synthetic actual event → anchor → closed hourly bar → AVWAP → clusters → LevelStrength → v1.2 Structure chain: adding the event AVWAP increases all three scores with fixed touches/reaction/volume. The old mapping fails the independent regression. All eight event rows now feed `structure`; a separate `BlockerDefinition.required_for_entry_component=False` preserves non-structural omission. Existing census test is corrected to the actual dataflow and strengthened to check both facts. |
| R7 / **P3 FIXED** | `btc_predictor/research_backtest/coverage.py:140`. Artifact policy identity was V3 despite binding V4 and its adopted data rules/champion identity. Identical §5A wording does not make the entire policy identity accurate. | Independent test requiring `INVENTORY_POLICY_VERSION == RESEARCH_BACKTEST_POLICY_V4` fails before the fix and passes after. Label corrected; source/window/owner decisions unchanged. |
| E1 / **P2 OPEN, frozen owner limitation** | `btc_predictor/features/positioning.py:1260`, `:1340`; `futures_basis_health:551`. Decimal sum/mean rounding gives nonzero computed variance for an exactly constant history, yielding a complete score where the owner promises a zero-variance refusal. This can fabricate positioning evaluability and CROWDING input. EPIC Y cannot edit this EPIC X-bound owner. | Independent 60-row synthetic series, annualized rate `Decimal('0.015') * 365 / 90` identical in every row: **z=1**, health **83.52702114112721**, complete **True**, no reason codes. The independent expected-refusal regression explicitly XFAILs. RBT-002A must record the limitation and require an RBT-004 composer-side equality guard on the owner's actual PIT prior annualized-basis history: constant history refuses `FUTURES_BASIS_ZERO_VARIANCE`, supplies no health/z, and records structural unevaluability; never reimplement the z-score or substitute zero. Use owner aggregation/history helpers, promoted to classified roots if called directly; test current-equals-history and current-differs-from-constant-history, PIT exclusion and unaffected nonconstant cases. An owner fix instead needs an explicit cross-workstream decision; no such edit is authorized here. Disclosure alone cannot justify accepting the false score. |
| E3 / **NOT_A_DEFECT** | `btc_predictor/research_backtest/input_census.py:537`; inventory census source positions. Owner line shifts change the inventory digest. | Acceptable conservative identity binding for RBT-002A/RBT-006: freeze the reviewed inventory hash alongside code/spec identity and revalidate/rebind when the source census changes. Do not silently ignore line positions or compare only old counts. A separate semantic digest could be additive later; excluding positions is not required for closure. |
| E4 / **P2 prospective contract risk; required future guard** | RBT-004/RBT-005 acceptance below; `input_census.py:160`. A composer directly calling an internal helper bypasses root-level input classifications even if that helper is already in the static closure. | Require a static, alias-resolving composer-call census and a runtime direct-caller check on all deterministic decision fixtures: every directly called decision owner function must resolve to a `DECISION_PATH_ROOTS` entry; no unresolved owner callback/dict/getattr/partial dispatch. Constructors are limited to explicitly classified composer input/raw types; owner outputs come from roots. Serializers may have an explicit type-bound evidence-only allowance. A new owner call must fail until its root, parameter classifications, left-out records and inventory are reviewed. Apply also to completion-spec-selected rolling helpers, currently deliberately left out. Add a mutation regression that introduces a direct internal-helper call. |

**R1 root and circularity audit.** The 74 roots cover the implementable Rulebook
component → regime/flags → setup/trigger → conviction → veto/R/R → stop →
budget/sizing → lifecycle/management flow. Checked every root's justification
against the owner signature and the required `BacktestIntent` fields:
entry zone/initial stop/conviction, ADD requirements, TRIM signal, TRAIL result,
EXIT reason, direction and provenance. The golden harness's direct
`calculate_initial_stop`, `evaluate_add_requirements`, `evaluate_trim_rules`
and `evaluate_exit_rules` are **not roots** but are reached through the chosen
higher-level root wrappers; a composer using those lower-level APIs must first
promote them to roots. No additional entry point is required by the current
wrapper contract. Completion-spec-selected normalization helpers will require
new roots before composition; the as-yet unimplemented spec cannot establish
that future call contract.

The committed registry is a two-way drift guard, not the discovery source:
static traversal does not read it. No test silently regenerates it (snapshot
writes are absent from the tests). Static discovery plus separate runtime
profiling supplies completeness evidence; that evidence is **insufficient**
for the nested-input omission above. Registry equality is correct but cannot
rescue missing nodes.

**Left-out sampling: 24 of 82 function definitions independently judged.**
Names below are relative to `btc_predictor`; the evidence artifact records each
full path, file:line and stated reason. Each reason is valid for the current
single-decision/wrapper contract; none excuses the reached nested helper.

| Function | Judgment |
| --- | --- |
| `features.add.calculate_add_score_batch` | Correct: batch wrapper; single-decision add root used. |
| `features.entry.calculate_entry_conviction_batch` | Correct: batch wrapper; single-decision entry root used. |
| `features.hold.calculate_hold_score_batch` | Correct: batch wrapper; single-decision hold root used. |
| `features.momentum.four_week_momentum` | Correct: bare series variant; daily-bar root supplies the same 28-day quantity. |
| `features.momentum.twelve_week_momentum` | Correct: bare series variant; daily-bar root supplies the same 84-day quantity. |
| `features.rolling.historical_normalize` | Correct now: unused candidate convention; promote if selected by the completion spec. |
| `features.rolling.rolling_percentile` | Correct now: unused candidate; same promotion obligation. |
| `features.rolling.rolling_volatility` | Correct now: no reached caller; volatility uses its named owner. |
| `features.rolling.rolling_zscore` | Correct now: unused candidate; same promotion obligation. |
| `features.rolling.true_ranges` | Correct: standalone wrapper; reached ATR path uses the shared bar-range helper. |
| `features.volatility.calculate_volatility_score_from_results` | Correct: result-conversion convenience wrapper; composer fills the scored input type. |
| `features.volatility.rv_7_20_60_from_daily_bars` | Correct: convenience triple; roots compute required windows individually. |
| `features.scoring_contracts.audit_factor_overlap` | Correct: reporting/audit, no decision input. |
| `features.scoring_contracts.effective_weights` | Correct: reporting/audit, no decision input. |
| `features.scoring_contracts.effective_weight_report` | Correct: reporting/audit, no decision input. |
| `portfolio.state_machine.position_event_records` | Correct: persistence serialization after state transitions. |
| `portfolio.state_machine.replay_position_lifecycle` | Correct: reconstructs existing engine state; not a newly measured input. |
| `portfolio.state_machine.restore_position_lifecycle` | Correct: validates reconstructed persisted state. |
| `risk.buffer.volatility_buffer_grid` | Correct: sensitivity grid; configured single buffer owner is the root. |
| `risk.exposure.risk_at_stop_from_record` | Correct: persisted-result reconstruction, no measurement. |
| `risk.trailing.trailing_stop_from_record` | Correct: persisted-result reconstruction, no measurement. |
| `signals.exit_rules.exit_signal_from_record` | Correct: persisted-result reconstruction, no measurement. |
| `signals.reason_codes.build_reason_code_engine` | Correct: explanation from already computed decisions. |
| `signals.data_quality.build_recommendation_reason_code_records` | Correct: persistence rows for existing reasons. |

**Independent adversarial fixtures.** Real package-source fixture owners,
loaded under an in-scope module name, cover all requested pattern families.
"Runtime catches" means an executed unknown function/type is actually reported
uncovered, not merely observed. No market data is involved.

| Pattern | Static discovery | Runtime when executed | Neither / real-code follow-up |
| --- | --- | --- | --- |
| Enclosing local holding a callback parameter | Misses concrete callback and its input type | Reports both uncovered | Neither can discover an unexecuted externally supplied callback. Real reached local-function audit finds `trailing...held`: its body is walked but its parameters are omitted, and the ancestor exemption masks that omission. |
| Protocol method on an unnamed concrete class | Reaches Protocol; misses concrete method/input type | Reports both uncovered | Real `breakout.SourceLevel` is a field-only protocol; supported weekly/monthly concrete types are reached. No unclassified concrete implementation found. |
| Global dict dispatch | Catches stored callback and input type | Covered | No real reached callable dispatch table outside the static set found. |
| `getattr(module, name)()` dispatch | Misses concrete callback/input type | Reports both uncovered | If not run, neither catches it. Real reached `getattr` sites read enumerated config/state fields, properties or `as_record`; no undiscovered callable dispatch found. |
| `__post_init__` reading a config | Catches config type/fields and method | Covered | Real quality/config post-init code is reached and classified. |
| Property calling a helper | Catches property/helper/input type | Covered | Real lifecycle `tranche_count`, `is_open`, `is_terminal`, `persisted_status` and result properties are reached. |
| Real named local `held`, including a newly used parameter | Body dependencies caught; helper/signature missing | Function observed; inputs **not** checked, falsely considered covered | R1-RR. Both completeness mechanisms miss the parameter surface, even on execution. |

**Tracer adequacy and unexecuted branches.** My full-thunk trace reproduces
**202 runs, 74 roots, 959 functions, 155 constructed dataclasses, zero path
misses**. My owner selection runs **1,699 tests in 55 named modules** (explicit
list in evidence), reaching all 74 roots, 952 functions and 124 constructed
dataclasses, zero path misses. The correction did not commit its 52-module
selection, so I do not claim to reproduce that exact selection or its 954
function count. I initially selected 52 modules/1,677 tests, then added the
relevant rolling-statistics, market-bar rolling integration and quant decision
boundary suites (22 tests); both selections had zero path misses.

Coverage.py **7.16.0**, branch measurement, all **50 reached source modules**
included, even if a file never executes. Denominators below are computed from
coverage JSON, not from fixture assertions. "Reached" restricts statements/arcs
to source bodies of census callables; module totals also include unreached
wrappers/persistence and initialization. Imports and fixture construction are
included in the module measurement; runtime owner tracing is separately scoped.

| Runs | Entire reached modules: lines / branches | Reached callable bodies: lines / branches |
| --- | --- | --- |
| 202 fixture runs | 4,993/11,539 (**43.27%**); 2,235/4,140 (**53.99%**) | 4,993/7,565 (**66.00%**); 2,235/3,728 (**59.95%**) |
| My 1,699 owner tests | 6,480/11,539 (**56.16%**); 3,149/4,140 (**76.06%**) | 5,855/7,565 (**77.40%**); 2,934/3,728 (**78.70%**) |

There are **1,493** fixture-unexecuted and **794** owner-test-unexecuted
reached-body branch arcs. The complete file:source-line → target-line list,
including the enclosing callable, is committed in
[`rbt002_rereview_evidence_v1.json`](../../backtest_evidence/research_backtest_v1/rbt002_rereview_evidence_v1.json)
under `coverage.runs.{fixtures,owners}.files.*.unexecuted_branches`.
The `reviewer_probe_source` entries preserve the actual independent SQL,
mutation, coverage/tracer and branch-analysis scripts (temporary working paths
are explicit); `owner_test_files` supplies the exact owner selection. Negative
targets mean function exit. This explicitly lists the branches; zero tracer
misses is not interpreted as branch closure. Independent AST resolution of
calls/constructions in never-executed reached statements found **no additional
explicit owner target outside the static set**. Local and object dispatch were
also inspected via the pattern audit. The named local-helper omission is the
positive counterexample despite these zero target misses.

**Injection verification.** Original three cloned-type reproducers and the
reward/helper parameter reproducers genuinely replace live module bindings;
they pass the focused suite. The committed universal tests at
`test_research_backtest_coverage_census.py:284` and `:296` instead mutate census
records, then call `_require_classified_census`: useful non-vacuous drift-guard
tests, **not** 882 live-code / 157 live-type discovery experiments. I separately
recompiled and substituted all **882** live function bodies with one extra
keyword parameter: all refused `UNCLASSIFIED_PARAMETER`. I separately mutated
all **157** live field schemas (156 dataclasses, one Protocol): all refused
`UNCLASSIFIED_FIELD`. The dataclass experiment modifies the actual live
`__dataclass_fields__` mapping; it does not claim to rebuild every constructor.
A separate live `SourceLevel.__annotations__` mutation also refuses. An initial
class-clone sweep stopped on `DecisionTolerance` because old default instances
caused `CONFLICTING_OWNER_OBJECTS`; that partial sweep is not counted as a
successful universal run. The independent by-hand top-level reward mutation
passes its regression; the by-hand nested mutation exposes R1-RR. Mutation
probes are preserved as source strings in the review evidence artifact; none
silently regenerates the registry.

**Classifications and R2–R5.** Independently checked **33 rows** across raw,
derived, undefined, certified, fallback, discretionary, config, engine-state
and internal-dataflow kinds. Full sampled row keys/classifications are in the
evidence artifact. Spot checks include trend and ETF z-score undefinedness;
weekly-structure producer; ETF_CORE absent CVD/participation; basis-health
producer; daily market-cap shape; certified liquidation definition; downside
return; v1.2 diagnostic-only outer confluence; severe crowding; systemic shock;
add/hold/local-high/optional measured-move gaps; settlement/snapshot/interval
stamps; event and SourceLevel; fixed windows; stress/quality/risk config;
lifecycle quantity; cluster/risk/trailing outputs; quant weighted-score inputs;
and config loading. The AVWAP mapping error is fixed as R6. No additional
owner-less measurement ID was found by sampling; the internal nested omission
is **not** a new undefined strategy convention.

All **948 output fields / 84 output types** have a real AST constructor under
a reached owner/root, not merely a registry category or annotation. Independently
spot-checked 11 producers: AnchoredVwapAnchor, AnchoredVwapResult, LevelCluster,
MonthlySwingLevel, VolumeProfileBin, VolumeProfileResult, PositioningScoreResult,
FuturesBasisHealthResult, RegimeScoreResult, RiskBudgetResult, TrailingStopResult.
The evidence records constructor/source/root paths. This output-field check does
not classify the missing local helper's parameters. All **23 reported fixed
defaults** match actual live signatures and defined owner conventions. More than
10 checked individually: full-window `min_periods=None` in rolling mean/ATR/RV,
20/52-week windows, DecisionTolerance `1E-12`, distance/risk/true-range
`nan_policy='raise'`, RV `sample=False`, weighted-score tolerance `1e-6`,
Gaussian maximum 100, normal-CDF bounds/mean/deviation, percentile direction,
and reward major timeframes `('1w','1mo')`. Nested defaults are still outside
this reported count and prevent a completeness PASS.

Bytewise JSON comparisons against the `b4b51fc4...ed6a106` inventory confirm
unchanged minimum histories, earliest dates, family coverage, exposure report,
sources (including semantic pins/probes), and USD 29 acquisition plan. Before
this review fix, exactly three of the original 592 rows had semantic changes:
anchor producer/missing wording, weekly+monthly SourceLevel producers, and all
accepted cluster producers plus volume family; each is justified by actual code.
The review fix additionally changes the event's Structure mapping and policy
label, with derived census-profile consequences, without moving any dates or
source facts. The original 24 IDs, their occurrences and blocker membership,
`MEASURED_MOVE_REFERENCE`, certified liquidations and the §9.2 volume fallback
stay fixed. The frozen strength owner still refuses absent volume even at zero
volume weight; the completion spec must cite the existing fallback and disclose
this owner-compatibility gap, never define a new percentile or zero-fill it.
R4's bare/quoted/qualified/aggregate value-column mutation guards still pass.
R5 remains a historical procedural disclosure; no new provider probe was made.

**Live database reproduction — independently VERIFIED.** Connection only
through `_database_url_from_environment`; first query
`SELECT current_setting('default_transaction_read_only')` returned **on**;
transaction read-only also **on**. No `.env`, URL or credentials were read or
printed. My own SQL uses only series identities, timestamps and counts; missing
hours are a `generate_series` anti-join, grouped by timestamp minus hourly
row-number to derive consecutive runs. Schema time-column metadata and aggregate
scans separately distinguish observations, availability and ingestion. One
initial composite query used a nonexistent timestamp column, failed read-only,
and was corrected to schema-declared `observation_time`; no value query occurred.

| Fact | Independently reproduced |
| --- | --- |
| Bitstamp | **52,608 distinct 1h timestamps**, zero missing. |
| Coinbase | **52,597**, **11 missing in 5 runs**: 2020-01-30 17; 2020-09-04 23; 2020-10-20 20; 2023-03-04 18–20; 2025-10-25 16–20 UTC. |
| Bitfinex | **52,592**, **16 missing in 7 runs**: 2020-02-11 11–12; 2020-08-12 21; 2021-06-30 08–09; 2021-10-13 14–16; 2022-10-12 08–11; 2023-03-06 10–11; 2024-05-05 10–11 UTC. |
| Other raw tables | ETF, funding, basis, generic series, liquidations, OI, perpetual volume: **0 rows each**. Market cap has no raw table. |
| December 2019 | **2,232**, **744 per venue**, December 1 00:00 through December 31 23:00. Count/timestamps only; exposure retained, not accepted. |
| Holdout/reserve | **No raw observation rows**. Three composite availability timestamps at 2026-01-01 00:05 correspond to observations 2025-12-31 23:00. Raw OHLCV ingestion timestamps in August 2026 are provenance, not observations. |

A separate guarded `coverage collect` to a temporary directory, using the
stored collection instant solely to compare metadata, reproduces the **entire
database snapshot exactly**. Thus the inventory comparison is not accepted on
stored data alone. All inventory files re-hash/rebuild byte for byte in fresh
processes, alternate cwd, seeds **0/1/8675309**, before and after the fix.

**Four interrupted audit areas independently re-audited.** The correction's
notes identify **composer-facing inputs, defaults, type categories,
completeness** (not four completed agent verdicts).

| Area | Independent result |
| --- | --- |
| Composer-facing | Root/wrapper/intent/golden contract checked; event undefinedness confirmed, Structure dependency corrected. Future direct-call guard required. |
| Defaults | All 23 recorded defaults independently checked; real local `held` defaults omitted. **FAIL R1-RR.** |
| Type categories | 84 constructor-backed output types, raw/composer types, 28 strategy config records, quality/tolerance/budget config and engine state checked; 33 cross-kind samples, 11 output producers. No new undefined ID beyond the confirmed event. |
| Completeness | Registry independence, 74 roots, 24 left-outs, six adversarial patterns, both tracers, branch gaps and live mutations checked. **FAIL R1-RR** despite zero path misses. |

**Confirmed RBT-002A minimum: 25 undefined IDs; no final completeness sign-off.**

```text
TREND_Z_M4, TREND_Z_M12, TREND_Z_20W, TREND_Z_52H
FLOW_Z_ETF_NORM_5D, FLOW_Z_ETF_NORM_20D, FLOW_Z_FLOW_ACCEL
RANGE_PERCENTILE, DOWNSIDE_RETURN, UPSIDE_RETURN
LEVEL_REACTION_MAGNITUDE, SEVERE_CROWDING_STATE
MOMENTUM_PERSISTENCE_SCORE, NEW_STRUCTURE_SCORE, ADD_MOMENTUM_SCORE
NEW_STRUCTURAL_CONFIRMATION, REGIME_SUPPORTIVE_PREDICATE, FLOW_SUPPORTIVE_PREDICATE
REGIME_INVALIDATION_PREDICATE, DATA_RISK_EXIT_PREDICATE
CORRECTION_FROM_LOCAL_HIGH, DISTRIBUTION_STATE, SHORT_TRIGGER
MEASURED_MOVE_REFERENCE, CAPITULATION_EVENT
```

Also account for `LEVEL_VOLUME_PERCENTILE` via the existing §9.2 fallback and
its frozen-owner compatibility gap. `CAPITULATION_EVENT` is optional but feeds
Structure when included; explicit omission is a completion-spec ruling. The
short-only IDs stay inert. The list may grow during the required census
correction; RBT-002A cannot start on a false final-list claim.

**Commands / own validation counts.** `.venv312` CPython **3.12.14**. Proof
subsets run alone, separately from each other and from other validation.

| Suite / command | Own result |
| --- | --- |
| Original focused coverage/review/census/nine trace modules | **296 passed** before fix. |
| Same focused modules plus independent re-review module after fix | **305 passed, 3 explicit XFAIL** (two release-blocking R1 regressions and the frozen basis owner defect). These are known failures, not closure evidence. |
| New nested mutation with `--runxfail -k new_nested_live_input` | **1 failed as expected: DID NOT RAISE**, 11 deselected. |
| RBT-001 replay inputs/review | **167 passed**. |
| `test_us_equity_market_closures.py` | **145 passed**. |
| BTC-180..185 named engine/cost/walk-forward/regime/setup/sweep/integration modules | **282 passed**. |
| BTC-220..224 feature boundary/comparisons/look-ahead/risk/paper/golden | **342 passed**. |
| Flow/positioning/volatility/trend/structure/derivatives collector+quality/OHLCV/market bars | **320 passed**. |
| Reference V5 / corpus V1+V2 / ETF | **407 passed, 2 existing skips**; V5 `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`. |
| PAD5 preserved authority / failed R5 predecessor / namespace / child order / frozen modules | **5 passed, 112 deselected**; `54675984...f483`. |
| PAD4-R5 namespace / child order | **2 passed, 199 deselected**; `b4168dc9...61c7`. |
| Owner tests under coverage and root-scoped profiling | **1,699 passed**; explicit 55-module list in evidence. |
| `compileall -q btc_predictor etf_calendar_worker`; `git diff --check` | **PASS**. |
| Hash / rebuild / seeds / cwd / fresh process | **PASS**, all three inventory files. |

Whole-repository suite and full 117-test PAD5 proof suite **NOT RUN**; no full
suite success is claimed. Regression counts are my runs, not copied assertions.

**Acceptance / design / documentation / next.** Scope, live coverage/exposures,
source/history preservation, artifact determinism and bounded classification
fixes pass. The mandatory exhaustive input-surface criterion **FAILS**. No ticket
closure is authorized; RBT-002 cannot remain DONE. No additional strategy
semantics or owner formula was invented. Code/test/inventory changes are listed
in the distinct review-fix; this outcome, affected statuses/Next EPIC Y table,
future composer guard and CURRENT_STATE snapshot are updated in the subsequent
documentation commit. The evidence artifact records branch lists, probes and
samples. Next EPIC Y work: another **RBT-002 R1 correction**, followed by an
independent xHigh re-review. RBT-002A/RBT-001A remain blocked. EPIC X's separate
next dependency-satisfied ticket remains **POSTP1-001V2R1**.

**Safety:** no real-data backtest outcome; holdout **NOT COLLECTED**, its values
never read; BTC-019 untouched, sealed sample unopened; EPIC X unchanged,
`POSTP1-001V2R1` still next; Epic T unchanged. Only EPIC Y's own modules, tests,
evidence/inventory and the two handoff/roadmap documents change.

### Correction (R2)

**Date:** 2026-10-02. **Correction commit:** `812b968`, on base `634d122`.
**Status:** `CORRECTED (R2) / AWAITING INDEPENDENT RE-REVIEW UNDER V5 §5A.7`.
This is the last census correction under the bounded closure standard of
[`RESEARCH_BACKTEST_POLICY_V5`](../policies/research_backtest_policy_v5.md)
§5A.5–§5A.7 (owner decision 2026-10-02). It fixes R1-RR only. No database access
or provider probe was made: the inventory was rebuilt from its stored snapshot,
which the 2026-10-01 re-review reproduced live.

**Files.**

- Changed: `input_census.py` (nested discovery and classification, tracer,
  stated limits), `input_census_registry.py` (230 nested entries),
  `coverage.py` (nested rows, refusals, limits, V5 label), the re-review test
  module, and the three inventory artifacts.
- New: `test_research_backtest_coverage_nested.py` (11 tests) and the synthetic
  fixture owner `rbt002_r2_nested_fixture_owners.py`.
- No owner module, EPIC X-bound file, `data/` or `research_artifacts/` file
  changed.

**Nested-callable discovery.** For every reached callable, the walk now reads
the live code object's nested code constants, recursively. CPython compiles
every function, lambda, generator expression and class body defined inside it
into one of these. Each one is paired with its node in the module source by
name and first line, and by span containment when two scopes share a line.
It is then recorded with:

- its qualified name (`co_qualname`) and a census path. A named helper keeps
  its plain path, for example
  `btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held`. An
  anonymous scope, or a repeated name, carries its source-order ordinal, for
  example `...select_reward_reference.<locals>.<lambda>#1`;
- its parameters, from the code object, and its defaults, from the source;
- every call site inside the owner, argument by argument.

CPython 3.12 inlines list, set and dict comprehensions (PEP 709), so they have no
code object or parameter of their own. An independent test enumerates the live
nested code objects of all 882 named callables and requires exact equality
with the census.

**Classification (V5 §5A.1), decided from the call-site AST and recorded per
callable.**

| basis | rule | callables |
| --- | --- | ---: |
| `EVERY_CALL_SITE_IS_A_DIRECT_CALL_PASSING_LITERALS_OR_ENCLOSING_SCOPE_NAMES` | Every use of the local name is a direct call. Every argument is a literal (`ast.literal_eval`) or a name bound in the enclosing owner's scopes, not in an inner function and not global | 2 |
| `KEY_FUNCTION_OF_BUILTIN_SORTED_MIN_OR_MAX_OVER_ENCLOSING_SCOPE_VALUES` | The lambda is only `key=` of an unshadowed builtin `sorted`, `min` or `max`, which applies it to the values the owner passes the builtin | 40 |
| `GENERATOR_EXPRESSION_ITERATOR_BOUND_IN_THE_ENCLOSING_SCOPE` | The only parameter, CPython's `.0`, is the iterator of the first `for` clause, evaluated in the enclosing scope | 188 |

**230 nested callables, all `OWNER_INTERNAL`; 0 `EXTERNAL`.**

- `calculate_trailing_stop.<locals>.held(reason, *, candidate=None,
  complete=True)` has 6 call sites (lines 305–330). Each passes a literal reason,
  the local `candidate`, or the literal `complete=False`. Both defaults are
  passed at some site (`A_REACHED_CALLER_PASSES_THIS_ARGUMENT`).
- `next_tranche_for_position.<locals>.unallocated(reason)` has 2 call sites,
  both literal.
- Example lambda: `select_reward_reference.<locals>.<lambda>#1`, `key=` of
  `sorted` over the owner's filtered tiers.
- Example generator: `_validate_stage_provenance.<locals>.<genexpr>#1` and `#2`,
  two on one line, told apart by span.

Everything else is `EXTERNAL` and fails closed:

- escaping as a value;
- a computed or unpacked argument;
- a decorator;
- a rebound name;
- a local class or its members;
- live code that differs from its source.

An external callable's defaults are never reported as fixed. The enumeration
refuses it (`UNCLASSIFIED_PARAMETER`) until each of its parameters has an entry
in `coverage.EXTERNAL_NESTED_PARAMETER_CLASSIFICATIONS`, which is empty. The
registry pins each classification and basis; a change raises
`NESTED_CLASSIFICATION_CHANGED`. A synthetic fixture owner exercises every rule.

**Masking removed.** `uncovered_traced` no longer accepts a nested frame through
its ancestor. Every executed frame must match its own static record by code
identity (module, `co_qualname`, source line, first column) and parameter names,
less a method's receiver. A path-only trace is still checked, without
exemption.

The reviewer's reproducer was re-run from its preserved source in the evidence
artifact. It adds a used `independent_new_input=True` to `held` in memory, then
executes it:

| | `634d122` (before) | `812b968` (after) |
| --- | --- | --- |
| Surface | 3,288 rows, identical; no `held` row | Census refuses `UNCLASSIFIED_PARAMETER: ...held has unclassified inputs ['independent_new_input']` |
| Tracer | Helper traced, `uncovered` empty | Against the pre-mutation census: reports `held` with its executed parameters differing. Against the current census: covered by its own record, which the census refuses |
| Re-review tests with `--runxfail` | 2 failed (`KeyError`, `DID NOT RAISE`) | 2 passed, no marker |

**XFAILs.**

- `test_nested_trailing_helper_parameters_are_enumerated` passes unchanged.
- `test_new_nested_live_input_is_refused` passes. Its two intermediate
  assertions demonstrated the masked behaviour (`uncovered` empty and surface
  unchanged) and cannot hold once the census is fixed. They are replaced by the
  corrected expectations: the new parameter is recorded; the tracer reports it
  against the pre-mutation census; the census refuses it by name. The mutation
  and the proof of execution are unchanged.
- The frozen-owner `test_nonterminating_constant_basis_refuses_zero_variance`
  XFAIL stays (E1).
- New: all 42 local functions and lambdas are mutated live, one at a time, and
  each refuses `UNCLASSIFIED_PARAMETER`. `unallocated` and a lambda are also
  refused end to end.

**Stated limits (V5 §5A.5).** They are persisted in the inventory
(`input_surface.census.limits`) and the report. The census claims completeness
only for static discovery plus the runtime trace over the exercised paths. The
four known limits are:

- enclosing-local callbacks;
- unnamed Protocol implementations;
- dynamic `getattr` dispatch;
- unexecuted branches.

The backstop is the §5A.6 runtime guard in RBT-004, RBT-005 and RBT-006.
Coverage was re-measured with coverage.py 7.16.0 (branch) on CPython 3.12.14,
using the re-review's preserved scripts. The root-scoped tracer was extended to
the code-identity check.

| run | reached-body lines | reached-body branches | nested callables executed | strict trace |
| --- | ---: | ---: | ---: | --- |
| 202 fixture runs (74 roots) | 4,993/7,565 (**66.00%**) | 2,235/3,728 (**59.95%**) | 224/230 | 0 uncovered |
| 1,699 owner tests (55 modules) | 5,855/7,565 (**77.40%**) | 2,934/3,728 (**78.70%**) | 224/230 | 0 uncovered |

- The totals, module totals and both unexecuted-arc lists (1,493 and 794) are
  identical to the re-review evidence.
- Five generator expressions run in neither suite. Their classification rests
  on source alone:
  - `DerivativesQualityConfig.__post_init__` #1;
  - `EntryConvictionResult.as_record` #1–#3;
  - `trailing._validate_result` #1.

**Inventory.** It was rebuilt from its own stored snapshot:
`108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` (was
`a68e5284...ad765d`).

- Policy label `RESEARCH_BACKTEST_POLICY_V4` → **`_V5`**: the label tracks the
  governing policy (R7). The census version is now
  `DECISION_PATH_STATIC_CENSUS_V2`.
- Rows: all 3,288 previous rows are byte-identical. The 232 new rows are
  `NESTED_OWNER_INTERNAL_PARAMETER`, for **3,520** in all; resolved call sites
  are 1,593 (4 new direct-call shapes).
- New census records: `nested_callables` (paths, parameters, defaults, call
  sites, basis) and `limits`.
- Every external-input classification is unchanged, as are the minimum
  histories, earliest dates, family coverage, exposures, sources, blockers,
  verdict, the USD 29 plan and the database snapshot (all byte-compared).
- `CAPITULATION_EVENT` keeps its Structure dependency from `a281378`.

**RBT-002A list: unchanged.** R2 found no `EXTERNAL` nested callable, so no new
external input. The minimum stays at 25 undefined IDs, plus the
`LEVEL_VOLUME_PERCENTILE` §9.2 fallback and its owner-compatibility gap:

```text
TREND_Z_M4, TREND_Z_M12, TREND_Z_20W, TREND_Z_52H
FLOW_Z_ETF_NORM_5D, FLOW_Z_ETF_NORM_20D, FLOW_Z_FLOW_ACCEL
RANGE_PERCENTILE, DOWNSIDE_RETURN, UPSIDE_RETURN
LEVEL_REACTION_MAGNITUDE, SEVERE_CROWDING_STATE
MOMENTUM_PERSISTENCE_SCORE, NEW_STRUCTURE_SCORE, ADD_MOMENTUM_SCORE
NEW_STRUCTURAL_CONFIRMATION, REGIME_SUPPORTIVE_PREDICATE, FLOW_SUPPORTIVE_PREDICATE
REGIME_INVALIDATION_PREDICATE, DATA_RISK_EXIT_PREDICATE
CORRECTION_FROM_LOCAL_HIGH, DISTRIBUTION_STATE, SHORT_TRIGGER
MEASURED_MOVE_REFERENCE, CAPITULATION_EVENT
```

**Validation (`.venv312` CPython 3.12.14).** The proof subsets ran alone.

| suite | result |
| --- | --- |
| Focused: original 65, review 2, re-review 12, census 27, nested (new) 11, runtime trace 202 | **318 passed, 1 XFAIL** (frozen basis owner) |
| RBT-001 | **167 passed** |
| Closure table | **145 passed** |
| BTC-180..185 | **282 passed** |
| BTC-220..224 | **342 passed** |
| Owner modules | **320 passed** |
| V5 / corpus / ETF | **407 passed, 2 existing skips**; `v5_protocol_definition` recomputes to `95e43ee1...775a89` |
| PAD5 preserved authority, failed R5 predecessor, namespace, child order, frozen modules | **5 passed, 112 deselected**; definition `54675984...f483` |
| PAD4-R5 namespace and child order | **2 passed**; `b4168dc9...61c7` |
| Coverage re-measurement | 202 fixture runs; 1,699 owner tests passed |
| `compileall -q btc_predictor etf_calendar_worker`, `git diff --check` | PASS |
| Rebuild byte-equality; `PYTHONHASHSEED` 0/1/8675309 from another cwd in fresh processes | all three artifacts byte-identical |

The full repository suite and the full 117-test PAD5 suite were **NOT RUN**.

**Design decisions for the re-review.**

- *Direct calls* follow this correction's strict rule: only literals or names
  bound in the owner's scope.
- *Builtin `key=` lambdas and generator expressions* have no call site in the
  owner's AST. They are classified by V5 §5A.1's "owner-computed values": the
  builtin, or the generator protocol, supplies only values that the owner's own
  expression evaluated. The basis records those expressions. The re-review
  should confirm this reading.
- Discovery starts from code objects, the runtime truth. A nested code object
  with no matching source, or a live signature that differs from its source,
  fails closed as `EXTERNAL`.
- Nested defaults are recorded as their source text.

**Disclosures and remaining risks.**

- The four §5A.5 limits stand. The five unexecuted generator expressions are
  classified from source alone.
- Source-order ordinals mean that adding an anonymous scope to an owner renames
  its siblings. The census then refuses until the registry is re-audited. Line
  positions remain in the digest (E3).
- The method depends on CPython 3.12 behaviour: `co_qualname`, `co_positions`
  and inlined comprehensions.
- The E4 composer direct-call guard, the E1 futures-basis guard and the §5A.6
  runtime guard remain RBT-004/005/006 obligations.
- Discovery now takes about 1.4 s, up from 0.8 s.

**Safety.**

- No real-data backtest outcome.
- Holdout NOT COLLECTED; its values were never read.
- BTC-019 untouched; sealed sample unopened.
- EPIC X unchanged: `POSTP1-001V2R1` is still its next ticket.
- Epic T unchanged.
- RBT-002A, RBT-001A and RBT-004 were not started.


### RBT-002 R2 re-review outcome

**Date:** 2026-10-02. **Ticket:** RBT-002. **Review:** independent xHigh
re-review under `prompts/review_ticket.md`, bounded by policy V5 §5A.7.
**Reviewed:** correction `812b968` plus documentation `ce5cd70`, on base
`634d122`, requested branch at `ce5cd70afeacd032edc7347783591cde87598901`.
**Result: PASS WITH NON-BLOCKING FINDINGS. RBT-002 is DONE under V5 §5A.7.**
R1-RR is closed. RBT-002A and RBT-001A are READY. This supersedes the previous
release-blocking verdict for the current correction; historical outcomes stay
unchanged. No genuine defect in R2 and no missing external input was found.
**Review-fix commit: none. No commit was created**, as expressly requested
when nothing in R2 needs correction. Only the review evidence, this roadmap
and CURRENT_STATE are changed in the working tree; the reviewed implementation
and all three inventory artifacts remain unchanged.

**Findings and dispositions.**

| ID / severity / disposition | Location and ruling | Independent reproducer and regression |
| --- | --- | --- |
| R1-RR / **P1 CLOSED** | `input_census.py:1639`, `:1932`; `coverage.py:2294`, `:2382`. Nested callables now have their own signatures, classifications and rows; the ancestor exemption is gone. | Independent recursive `co_consts` enumeration of every reached live callable; own whole-module AST recompilation adding a **used** `independent_new_input=True` to real `held`: execution proved, stale trace reports changed signature, enumeration refuses `UNCLASSIFIED_PARAMETER`. R2's two former XFAIL regressions and nested suite pass. |
| R2-RR-A3 / **NOT_A_DEFECT** | `input_census.py:1481`; builtin key callbacks and generator iterators. For the current owners, the enclosing expression supplies the nested parameter, with all external object fields already classified. | Independent source/read-origin audit of **all 228 lambdas/generator expressions**, **266 attribute/key origin checks**, including indirect record-helper keys. No unenumerated external field. This does not permit classifying a newly consumed external field as internal. |
| R2-RR-FS1 / **P3 INHERITED, NON-BLOCKING** | `test_btc019_completion_gate.py:125–152`; `coverage.py:3698`. The legacy source-isolation test calls EPIC Y research code production and rejects its required read-only environment-helper import. The import already exists at `634d122` and is explicitly required by this review. | Exact failing node executed in an isolated `git archive 634d122` checkout: **1 failed**, same offender `research_backtest/coverage.py: btc_predictor.research.btc019_empirical`. **1 failed, 7158 passed, 3 skipped, 1 xfailed in 2992.82s (0:49:52)**. No production import or frozen owner changed. Record this inherited test-scope discrepancy; it is not a missing external input or a defect introduced by R2. |
| R6 / **P2 CLOSED** | `coverage.py:1335`, `:2176`. All eight event rows retain their Structure dependency; optionality remains a separate requiredness ruling. | The focused regression runs the event → AVWAP → cluster → LevelStrength → Structure chain and checks the eight rows plus optional blocker. Independently inspected surface matches it. |
| R7 / **P3 CLOSED** | `coverage.py:144`. The governing policy identity is V5. | The policy-label regression and nested inventory/report regression pass; independently rebuilt inventory retains the V5 label. |
| E1 / **P2 OPEN, KNOWN FROZEN-OWNER LIMITATION** | `features/positioning.py`, `futures_basis_health`; prior ruling retained. | Existing explicit XFAIL remains. RBT-002A must record the handling; RBT-004 must implement the owner-history equality/refusal guard. No owner edit or formula substitution. |
| E3 / **NOT_A_DEFECT**; E4 / **FUTURE OBLIGATION** | Prior rulings retained; V5 §5A.6 binds RBT-004/005/006. | Source-line digest binding remains conservative identity evidence. Future composers must enforce direct-call roots and account for incomplete results; this review authorizes no composition or freeze. |

**Independent closure checks (A)–(D): all PASS.**

| Criterion | Independent evidence |
| --- | --- |
| **A — method correction** | **882 named callables, 230 nested:** 2 local functions, 40 lambdas, 188 generator expressions. Own recursive code-object enumeration matches the census exactly, without its walker or identity helpers. CPython **3.12.14** compile experiment confirms list/set/dict comprehensions have no separate code objects (PEP 709). In-memory computed-argument, escape, decorator, rebinding and non-builtin `key=` cases classify **EXTERNAL** and refuse **UNCLASSIFIED_PARAMETER**; local classes/their members and deep escaping scopes fail closed. The real held helper has 6 sites, lines 305–330, literal reasons, local candidate and literal `complete=False`; unallocated has 2 literal-reason sites. Own used-input mutation is refused. Removing an allowed helper's own record reports it; an allowed frame's unknown callback callee is reported. No ancestor or other frame exemption remains. |
| **B — external surface** | **3,288 earlier rows byte-identical**, **232 additions** all `NESTED_OWNER_INTERNAL_PARAMETER`, total **3,520**. A3 audit above found no extra external field. R6's eight `CAPITULATION_EVENT` rows feed Structure while the anchor remains optional; R7's governing label is **V5**. The confirmed completion list is exactly the 25 undefined IDs below, plus the existing §9.2 volume fallback and its owner-compatibility gap. |
| **C — stated limits and measurement** | All four limits persist in `input_surface.census.limits` and the human inventory report: enclosing-local callbacks, unnamed Protocol implementations, dynamic getattr dispatch and unexecuted branches. Own coverage.py **7.16.0** runs reproduce fixture lines **4,993/7,565 (66.00%)**, branches **2,235/3,728 (59.95%)**; 1,699 owner tests reproduce lines **5,855/7,565 (77.40%)**, branches **2,934/3,728 (78.70%)**. Strict root-scoped profiling checks all 74 roots with zero uncovered functions/types. All five specified never-executed generator expressions were read: exchange-string validation over classified `expected_exchanges`; EntryConvictionResult's two missing-component selectors and contribution summation over owner-validated maps; trailing provenance-presence validation over a locally assembled tuple of enumerated result fields. All are internal. |
| **D — live database** | Initial gate returned exactly all six names. Connection only through `_database_url_from_environment`, every command through `~/bin/btc-ro .venv312/bin/python`; first query `SELECT current_setting('default_transaction_read_only')` and transaction check both **on**. Own timestamp/count-only SQL reproduces all counts and runs below. Guarded `coverage collect` writes only `/tmp/rbt002-r2-review/collect`; its entire database snapshot equals the stored snapshot, using the stored collection instant solely for comparison. No value column was queried; no credentials, URL or environment file read or printed. |

**A3 ruling.** V5 §5A.1's owner-computed-value reading is correct for these
current nested callbacks/iterators: their arguments come from the enclosing
owner's expression, and they add no caller-supplied parameter. This finding
depends on checking the consumed fields, not simply the syntax `key=` or
`for`. All raw record and Protocol fields, configuration fields, engine-state
fields, typed owner-result fields and serialized keys read by the current
expressions are present in the surface or produced by their reached owners.
Scalar methods, computed numeric arrays, component maps and local indices do
not introduce another external measurement. A future unenumerated field read
would require an inventory/spec update under §5A.6.

**Live database reproduction.** All times UTC, metadata only.

| Fact | Own reproduction |
| --- | --- |
| Bitstamp 1h, 2020–2025 | **52,608**, first 2020-01-01 00:00, last 2025-12-31 23:00; no gaps. |
| Coinbase 1h | **52,597**; 11 missing in 5 runs: 2020-01-30 17; 2020-09-04 23; 2020-10-20 20; 2023-03-04 18–20; 2025-10-25 16–20. Same first/last. |
| Bitfinex 1h | **52,592**; 16 missing in 7 runs: 2020-02-11 11–12; 2020-08-12 21; 2021-06-30 08–09; 2021-10-13 14–16; 2022-10-12 08–11; 2023-03-06 10–11; 2024-05-05 10–11. Same first/last. |
| Other raw tables | ETF, funding, OI, basis, liquidation, perpetual volume and generic series each **0**. |
| December 2019 exposure | **2,232** rows, **744 per venue**, December 1 00:00 through December 31 23:00. Counts/timestamps only; recorded exposure, not accepted for replay. |
| Holdout/reserve observations | **0** in every raw observation-time column, verified with COUNT/MIN/MAX only. Three composite availability stamps at 2026-01-01 00:05 belong to 2025-12-31 23:00 observations. |

**Confirmed final RBT-002A list under bounded V5 §5A.7: 25 undefined IDs.**

```text
TREND_Z_M4, TREND_Z_M12, TREND_Z_20W, TREND_Z_52H
FLOW_Z_ETF_NORM_5D, FLOW_Z_ETF_NORM_20D, FLOW_Z_FLOW_ACCEL
RANGE_PERCENTILE, DOWNSIDE_RETURN, UPSIDE_RETURN
LEVEL_REACTION_MAGNITUDE, SEVERE_CROWDING_STATE
MOMENTUM_PERSISTENCE_SCORE, NEW_STRUCTURE_SCORE, ADD_MOMENTUM_SCORE
NEW_STRUCTURAL_CONFIRMATION, REGIME_SUPPORTIVE_PREDICATE, FLOW_SUPPORTIVE_PREDICATE
REGIME_INVALIDATION_PREDICATE, DATA_RISK_EXIT_PREDICATE
CORRECTION_FROM_LOCAL_HIGH, DISTRIBUTION_STATE, SHORT_TRIGGER
MEASURED_MOVE_REFERENCE, CAPITULATION_EVENT
```

Separately account for **LEVEL_VOLUME_PERCENTILE** through the existing
Rulebook §9.2 fallback. The frozen strength owner still refuses absent volume
even at zero weight. Do not define a new percentile, zero-fill or copy its
formula. **LIQUIDATION_PERCENTILE** remains certified, outside the undefined
list. The event anchor is optional but feeds Structure when included; the
short-side IDs remain inert. Later discoveries enter through the mandatory
reviewed runtime-guard update rather than a universal-completeness claim.

**Own commands/tests and results.** Every Python run used `.venv312` CPython
3.12.14; database runs additionally used `~/bin/btc-ro`.

| Run | Result |
| --- | --- |
| Coverage/review/re-review/census/nested/nine trace suites | **318 passed, 1 XFAIL** (known E1). |
| RBT-001 replay + closure + BTC-180..185 + BTC-220..224 + V5/corpus/ETF suites | **1,343 passed, 2 existing skips** (167 + 145 + 282 + 342 + 407). |
| Flow/positioning/volatility/trend/structure/derivatives collector+quality/OHLCV/market-bar suites | **320 passed**. |
| Own branch measurements/strict traces | **202 fixture runs**, **1,699 owner tests passed**, exact totals above, 0 uncovered. |
| Own discovery/A3/mutation/determinism/scope scripts | **PASS**; complete source and read-origin evidence persisted in `rbt002_r2_rereview_evidence_v1.json`. |
| Full repository suite, `-q -W error::RuntimeWarning --basetemp=.../full` | **1 failed, 7158 passed, 3 skipped, 1 xfailed in 2992.82s (0:49:52)**. |
| PAD5 authority/predecessor/namespace/child-order/frozen-source subset, run separately | **5 passed, 112 deselected in 40.62s**; preserved definition `54675984...f483`. |
| PAD4-R5 namespace/child-order subset, run separately | **2 passed, 199 deselected in 26.59s**; preserved definition `b4168dc9...61c7`. |
| `compileall -q btc_predictor etf_calendar_worker`; `git diff --check` | **PASS**. |

The first full-suite attempt used `/tmp`, whose filesystem differs from the
repository's. Proof fixtures failed `os.link` with EXDEV, so that attempt was
stopped; no complete count or code-regression claim is made from it. The
sampled `test_on_disk_certified_source_mutation_refuses` fails EXDEV at HEAD
with `/tmp` fixtures and passes at `634d122` whose isolated checkout is already
in `/tmp`. The completed run above uses an approved scratch directory outside
the repository **on the same device**. The only failure in the completed full
run is the inherited source-isolation test reproduced at `634d122`; no R2
regression remains.

**Determinism, isolation and identity.** Fresh subprocesses under hash seeds
**0 / 1 / 8675309**, from another cwd, rebuild **all three artifacts byte for
byte**. Inventory digest remains
`108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`;
no regeneration or new digest is needed. `634d122..HEAD` touches no file in
the **120-module** EPIC X universe; every actual source byte independently
matches the frozen entries, whose manifest digest remains
`7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e`.
Nothing under `data/` or `research_artifacts/` is edited.
`v5_protocol_definition` independently recomputes to
`95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`.

**Design, documentation, remaining limitations and next.** No strategy,
owner, provider or policy semantics changed. The four adopted V4 data rules,
completion-spec choice, E1/E3/E4 rulings and V5 bounded standard were not
reopened. The four measured census limits stand; the runtime guards remain
RBT-004/005/006 obligations. CURRENT_STATE retains both open RBT-002A owner
questions: how to handle the §9.2 owner-compatibility gap and how to handle the
frozen E1 basis defect within the required guard/authorization boundary.
Recommended next dependency-satisfied ticket: **RBT-002A**; **RBT-001A** is
also READY. No downstream ticket is implemented here. EPIC X's next ticket
remains **POSTP1-001V2R1**.

**Safety:** no real-data backtest outcome; holdout **NOT COLLECTED**, its values
never queried; BTC-019 untouched, sealed sample unopened; no provider probe or
purchase; EPIC X and Epic T unchanged. Database collect wrote nothing to the
repository. The inherited full-suite finding does not authorize weakening a
test or changing a frozen owner.


## RBT-002A — `DEFINE_CHAMPION_COMPLETION_SPEC_V1`

**Status:** `DONE / INDEPENDENT xHIGH REVIEW PASS — CHAMPION_COMPLETION_SPEC_V1 9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f under V7; four distinct review fixes complete; owner-ruling conformance 700b924 applied; full repository suite has 0 failures (2026-10-03).`

**Prior status provenance (superseded 2026-10-03):** `IMPLEMENTED / AWAITING INDEPENDENT xHIGH REVIEW — CHAMPION_COMPLETION_SPEC_V1 frozen at d9f9b334abfba52b5f5af6a2eefe60616cec170568dbd7c5b310403cef7a80fd under policy V6 §6A; 26 inputs covered (22 defined, 2 omitted by ruling, 2 inert); two owner rulings are closure preconditions (see Implementation Notes).`

**Owner rulings (2026-10-03, policy V7).** The spec's two closure
preconditions are decided:
1. **Momentum Persistence overlap: ACCEPTED** (V7 §6A.10). The spec's
   `MOMENTUM_PERSISTENCE_SCORE = 100 * Phi(TREND_Z_M12)` stands unchanged.
   Rulebook §4.1's validation condition is met by a required, non-selecting
   ablation in the RBT-007 report (V7 §8). No spec change.
2. **Funding and OI-growth zero variance: GUARDED** (V7 §6A.9). The equality
   guard extends to `funding_health` (`FUNDING_HEALTH_ZERO_VARIANCE`) and
   `open_interest_growth_health` (`OI_GROWTH_ZERO_VARIANCE`), beside futures
   basis. The spec's guard contract and its named limitation for these two
   owners must be updated before closure, as a recorded spec change with a new
   digest. The other definitions and the frozen rules are unchanged. RBT-004
   must also promote the funding and OI-growth history helpers it calls to
   census roots.

Items 3–9 that the spec surfaced are not owner preconditions. They are
review items for the independent RBT-002A review, which may fix a genuine
defect or record a limitation.

**Prior status provenance (superseded):** `READY — RBT-002 independent R2 re-review PASS under V5 §5A.7. Confirmed 25 undefined IDs plus the existing LEVEL_VOLUME_PERCENTILE §9.2 fallback and owner-compatibility gap; E1 handling remains an explicit completion-spec obligation.`

**Policy V6 note (2026-10-02, recorded 2026-10-03).** Policy V6 supersedes two
pieces of wording in this ticket's original text below for this champion. The
original text is kept as history.
- "level volume (or the Rulebook §9.2 core weights without volume)" and
  "Separately account for the existing Rulebook §9.2 volume fallback": V6 §6A.8
  makes `LEVEL_VOLUME_PERCENTILE` a spec-defined input. The §9.2 no-volume
  fallback cannot run, because the frozen strength owner refuses a missing
  volume at any weight and §6 forbids weight changes. The spec covers 26 inputs.
- "policy V4 §6A": the binding rules are policy V6 §6A, including §6A.8 (level
  volume) and §6A.9 (E1 guard).
**Dependencies:** RBT-002 independent review PASS (SATISFIED, R2 under V5 §5A.7),
so that the owner-less list is confirmed for the bounded census; later inputs
are handled through the §5A.6 guard
**Implementation effort:** xHigh
**Review:** independent xHigh ticket review, which must also confirm that no
outcome was computed
**Owner:** `docs/policies/champion_completion_spec_v1.md` (new narrow versioned
strategy policy, EPIC Y scope only), plus a hash-bound machine-readable
definition and its coverage test under `btc_predictor/research_backtest/`

Author `CHAMPION_COMPLETION_SPEC_V1` under the binding rules in policy V4 §6A.
The owner chose this option on 2026-10-01.

Acceptance criteria:

- **Coverage.** Every owner-less, undefined input in the reviewed RBT-002
  inventory is covered exactly once. A test fails if the inventory gains an
  input the spec does not cover, or if any input is covered twice. The inputs
  are:
  - trend z-scores (`Z_M4`, `Z_M12`, `Z_20W`, `Z_52H`);
  - flow z-scores (`ETFNorm_5`, `ETFNorm_20`, `FlowAccel`);
  - range percentile, downside return and upside return;
  - level reaction magnitude and level volume (or the Rulebook §9.2 core
    weights without volume);
  - severe crowding;
  - the hold, add and exit predicates;
  - Bullish Reset's local high;
  - the optional measured-move reward reference (explicit omission is a ruling);
  - the optional anchored-VWAP capitulation-event anchor `CAPITULATION_EVENT`,
    found by the R1 census (explicit omission is a ruling);
  - the short-side inputs, listed as inert.
  The independent R2 re-review confirms **25 undefined IDs** under bounded
  policy V5 §5A.7, with the final list in its outcome and the reviewed inventory
  `108ab25b...efe3a`. Separately account for the existing Rulebook §9.2 volume
  fallback and its frozen-owner compatibility gap. `CAPITULATION_EVENT` feeds
  Structure when included but is optional. R1-RR is closed; correction R2
  adds no external ID. The §5A.6 runtime guard requires recorded inventory/spec
  updates for any later missing external input.
- **Frozen basis limitation.** Record the non-terminating constant-series
  zero-variance defect and require the owner-history equality/refusal guard
  specified in the completed re-review; disclosure alone does not authorize
  accepting the false health score. Do not restate the formula or edit the
  frozen owner without a separate cross-workstream decision.
- **Source precedence (§6A.2).** Each definition records its source class:
  Rulebook, Rulebook fallback, owner convention, config, or `NEW_PARAMETER`.
  It cites the exact line or symbol, and each `NEW_PARAMETER` has a one-line
  rationale.
- **Uniformity (§6A.3).** One z-score rule and one percentile rule for every
  undefined case. Exceptions are only where the Rulebook distinguishes inputs,
  and each is listed.
- **Predicates (§6A.4).** Every predicate maps to existing owner outputs and
  thresholds, with no new indicator. Conservative readings follow §6A.5.
- **Warm-up disclosure.** For each definition, give its warm-up and its effect
  on each venue's earliest evaluable date, from RBT-002's coverage facts. No
  outcome is computed.
- **Pre-registration evidence.** The commit contains no real-data score,
  signal or trade computation. State in the notes which data were consulted:
  availability and coverage only.
- **Freezing.** The definition is frozen by hash and byte-identical under
  `PYTHONHASHSEED` 0/1/8675309, an alternate cwd and a fresh process.

### Implementation Notes

**Implementation commits:**
- Part 0, `75fc7e6`: the R2-RR-FS1 BTC-019 isolation fix (policy V6 §9).
- Part 1, `09d14dc`: the spec module, frozen definition, tests, policy document
  and these notes.

**Current status:** `DONE / INDEPENDENT xHIGH REVIEW PASS` (2026-10-03).
Final reviewed digest `9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f`, inventory `108ab25b...efe3a` unchanged.
V7 conformance `700b924`; review fixes `352bba0`, `496a947`, `5b75882`,
`42459e6`. The current contract uses the existing uniform 20/20 observation
z rule, 16 NEW_PARAMETER elements, 14 roots to promote and all three guards.
The corrected lower bound is 2024-03-10; the original 2024-03-24 and all 78
original dates independently reproduced. Final focused checks: 146 passed.
The original implementation snapshot below is retained as provenance; the
current machine definition and review outcome govern the reviewed contract.
Both earlier owner preconditions are answered and applied under V7.

**Part 0 (R2-RR-FS1).**
- **Change.** New `btc_predictor/research_backtest/database.py`, function
  `database_url_from_environment()`:
  - reads the same five `POSTGRES_*` names;
  - builds `postgresql+psycopg://` with `quote_plus` user and password;
  - raises `DatabaseEnvironmentError` (a `ValueError`) naming missing variables
    only;
  - prints, logs and persists nothing.
  - `coverage.open_research_engine` uses it; its read-only behaviour is
    unchanged.
  - No `research_backtest` module imports a BTC-019 research-only module any
    longer.
- **Tests.** `test_research_backtest_coverage.py` patches the new helper and
  asserts it is called once. New `test_research_backtest_database.py` holds 26
  tests:
  - helper quoting;
  - missing names, listed without any value;
  - empty-as-missing;
  - no print, log or write;
  - an AST walk over every `research_backtest` module, covering nested and
    relative imports and `importlib`/`__import__` string imports, self-tested on
    each form.
- **BTC-019 isolation test.** `test_btc019_completion_gate.py` is not edited.
  Its isolation test failed at `0de7d4c` (1 failed) and passes after the fix.
- **Regression.** The inventory rebuilds byte-identical at `108ab25b...efe3a`.
  Full suite after Part 0: **7185 passed, 3 skipped, 1 xfailed, 0 failed**
  (2999.46s). The prior baseline was 1 failed / 7158 passed.

**Files (Part 1, all new except docs):**
- `btc_predictor/research_backtest/completion_spec.py`: the typed definition,
  bound-inventory loader, coverage check, warm-up simulation, writer and CLI
  (`write | verify | digest`);
- `backtest_evidence/research_backtest_v1/champion_completion_spec_v1.json` and
  its `.sha256`: the canonical sorted JSON;
- `btc_predictor/tests/test_research_backtest_completion_spec.py` (82 tests);
- `docs/policies/champion_completion_spec_v1.md`: the narrow versioned policy,
  EPIC Y scope only, research id `swing_v1.2+completion_v1`;
- docs: this block, the track header, RBT-001A/004/005/006 authority references,
  `INDEX.md` and `CURRENT_STATE.md`.

**Coverage (policy V6 §6A.7, §6A.8).**
- **What is covered.** Every row of the bound inventory with kind
  `OWNERLESS_UNDEFINED` (25 IDs, 43 rows) or `OWNERLESS_RULEBOOK_FALLBACK`
  (`LEVEL_VOLUME_PERCENTILE`, 2 rows) is covered exactly once, occurrence by
  occurrence. That is 26 entries and 45 rows.
- **What is excluded.** `LIQUIDATION_PERCENTILE`
  (`OWNERLESS_CERTIFIED_DEFINITION`) is excluded explicitly.
- **What the coverage check refuses**, all tested:
  - an uncovered row;
  - an input or occurrence covered twice;
  - an ID that is not in the inventory;
  - a row without an ID;
  - a kind conflict;
  - a changed certified set;
  - a changed inventory digest (`INVENTORY_DIGEST_MISMATCH`: rebind explicitly,
    never ignore).

| Input | Disposition / governing class | Rule (summary) | Bitstamp | Coinbase | Bitfinex | Moves the earliest date |
| --- | --- | --- | --- | --- | --- | --- |
| `TREND_Z_M4` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over `MOMENTUM_4W` | 2020-02-29 | 2020-03-01 | 2020-03-01 | no |
| `TREND_Z_M12` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over `MOMENTUM_12W` | 2020-04-25 | 2020-04-26 | 2020-04-26 | no |
| `TREND_Z_20W` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over weekly `MA_DISTANCE_20W` | 2020-12-21 | 2021-01-11 | 2021-01-04 | no |
| `TREND_Z_52H` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over weekly `HIGH_DISTANCE_52W` | 2021-08-02 | 2021-08-23 | 2021-08-23 | no (binds Trend) |
| `FLOW_Z_ETF_NORM_5D` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over ETFNorm_5 per publication day | 2024-03-03 | 2024-03-03 | 2024-03-03 | no |
| `FLOW_Z_ETF_NORM_20D` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over ETFNorm_20 | 2024-03-24 | 2024-03-24 | 2024-03-24 | **yes** |
| `FLOW_Z_FLOW_ACCEL` | DEFINED / NEW_PARAMETER | `UNIFORM_ZSCORE_V1` over FlowAccel | 2024-03-24 | 2024-03-24 | 2024-03-24 | **yes** |
| `RANGE_PERCENTILE` | DEFINED / NEW_PARAMETER | `UNIFORM_PERCENTILE_V1` of TR / prior close | 2021-01-02 | 2021-01-08 | 2021-01-06 | no |
| `DOWNSIDE_RETURN` | DEFINED / NEW_PARAMETER | R_7 = P_t / P_(t-7) - 1 (signed) | 2020-01-09 | 2020-01-09 | 2020-01-09 | no |
| `UPSIDE_RETURN` | DEFINED / NEW_PARAMETER | the same R_7 | 2020-01-09 | 2020-01-09 | 2020-01-09 | no |
| `LEVEL_REACTION_MAGNITUDE` | DEFINED / NEW_PARAMETER | min over swing members of net move to the last confirming close / price | 2020-02-24 | 2020-03-02 | 2020-03-02 | no |
| `LEVEL_VOLUME_PERCENTILE` | DEFINED / NEW_PARAMETER | min over swing members of `UNIFORM_PERCENTILE_V1` of pivot-bar Bitstamp volume | 2021-02-01 (lower bound) | 2021-02-01 (lb) | 2021-02-01 (lb) | no |
| `CAPITULATION_EVENT` | OMITTED / POLICY_RULING | no event anchor built | — | — | — | no |
| `SEVERE_CROWDING_STATE` | DEFINED / CONFIG | `CROWDING.flagged if complete else None` | 2020-10-02 | 2020-10-02 | 2020-10-02 | no |
| `MOMENTUM_PERSISTENCE_SCORE` | DEFINED / NEW_PARAMETER | 100 * Phi(TREND_Z_M12) (overlap disclosed) | 2020-04-25 | 2020-04-26 | 2020-04-26 | no |
| `ADD_MOMENTUM_SCORE` | DEFINED / NEW_PARAMETER | 100 * Phi(TREND_Z_M4) | 2020-02-29 | 2020-03-01 | 2020-03-01 | no |
| `NEW_STRUCTURE_SCORE` | DEFINED / NEW_PARAMETER | Structure owner at the add price under the raised stop | 2021-02-01 (lb) | 2021-02-01 (lb) | 2021-02-01 (lb) | no |
| `NEW_STRUCTURAL_CONFIRMATION` | DEFINED / NEW_PARAMETER | trail advanced on a HIGHER_LOW after the last ENTER/ADD | 2020-02-24 | 2020-03-02 | 2020-03-02 | no |
| `REGIME_SUPPORTIVE_PREDICATE` | DEFINED / CONFIG | smoothed regime BULL or STRONG_BULL (>= 65) | 2024-03-24 | 2024-03-24 | 2024-03-24 | no |
| `FLOW_SUPPORTIVE_PREDICATE` | DEFINED / RULEBOOK | FlowScore >= 60 | 2024-03-24 | 2024-03-24 | 2024-03-24 | no |
| `REGIME_INVALIDATION_PREDICATE` | DEFINED / NEW_PARAMETER | smoothed regime < 45 and entry regime was not | 2024-03-24 | 2024-03-24 | 2024-03-24 | no |
| `DATA_RISK_EXIT_PREDICATE` | DEFINED / OWNER_CONVENTION | False (Rulebook 24) | — | — | — | no |
| `CORRECTION_FROM_LOCAL_HIGH` | DEFINED / NEW_PARAMETER | -HIGH_DISTANCE_52W | 2021-01-04 | 2021-01-25 | 2021-01-18 | no |
| `DISTRIBUTION_STATE` | INERT / POLICY_RULING | None | — | — | — | no |
| `SHORT_TRIGGER` | INERT / POLICY_RULING | None | — | — | — | no |
| `MEASURED_MOVE_REFERENCE` | OMITTED / POLICY_RULING | measured_move=None | — | — | — | no |

Dates are each input's first availability (UTC). "lb" marks a data-dependent
lower bound. Every entry records its consumers (owner path and `file:symbol`),
the source class and exact citation of every element, its helpers with their
census status, its point-in-time rule, its missing-input behaviour (never
filled) and its accounted §5A.6 causes.

**Uniform rules (§6A.3), with no exceptions.**
- **`UNIFORM_ZSCORE_V1`:**
  - native owner series, latest visible observation D;
  - history `[D - 730 days, D)`, current excluded, None skipped;
  - at least 30 prior values; population SD;
  - an exactly constant history refuses;
  - helper: BTC-041 `rolling_zscore`.
  - The window is a `NEW_PARAMETER`. On native weekly series the positioning
    180 days holds at most 25 prior weekly values, so the weekly trend
    z-scores could never complete. Two other conventions are recorded as
    rejected alternatives: the flow owner's 20-observation count window, and
    daily-instant sampling.
  - Review correction RBT002A-R1: an explicit original-value equality guard
    must run before float conversion or the BTC-041 helper. The former tests
    characterized the native accumulator only: a 64-bit accumulator returns
    -1 for 730 copies of 1/3. The frozen application contract now refuses
    without a helper call and adapts time-selected H with window=len(H).
    Synthetic independent regressions cover both accumulator widths.
- **`UNIFORM_PERCENTILE_V1`:** `volatility_percentile`'s convention unchanged:
  - daily observations, `[D - 730 days, D)`;
  - at least 365 prior values; midrank; current excluded;
  - helper: BTC-041 `rolling_percentile`.

**Rulings.**
- **Optional inputs.** `MEASURED_MOVE_REFERENCE` is OMITTED: tier 4 is only
  consulted when tiers 1–3 fail, so omitting it provably trades less.
  `CAPITULATION_EVENT` is OMITTED: no owner yields an event, and AVWAP is
  optional under Rulebook 9.2/9.4.
- **Long-only.** `SHORT_TRIGGER` and `DISTRIBUTION_STATE` are INERT (`None`).
- **Severe crowding.** `SEVERE_CROWDING_STATE` is the existing CROWDING flag,
  gated on its completeness.
- **Level volume (§6A.8).**
  - **Source:** Bitstamp 1h volume, the RBT-001 shared snapshot.
  - **Quantity:** from swing-level records only, as the pivot bar's volume,
    against the same-length trailing volume at each prior UTC day. No level
    detection and no volume-profile binning.
  - **Normalisation:** the uniform percentile rule. Weights are unchanged at
    0.20.
  - **Computed warm-up:** a weekly pivot bar closing on or after 2021-01-11
    (369 comparators), detected from 2021-02-01; a monthly pivot from January
    2021, detected from 2021-04-01.
- **E1 (§6A.9).** Recorded as a named limitation. The RBT-004 contract is
  `FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1`:
  - the history comes from `_futures_basis_averages_by_time` and
    `_futures_basis_history`, both promoted to census roots;
  - the refusal is exact Decimal equality, whether or not the current value
    equals the history;
  - it refuses `FUTURES_BASIS_ZERO_VARIANCE` and passes no health or z-score to
    any of positioning, CROWDING, STRESS or EUPHORIA;
  - it records structural unevaluability;
  - it carries five required tests.
  - It does not reimplement the z-score, use a placeholder or tolerance, or edit
    the owner.

**NEW_PARAMETERs (17), each with its one-line rationale in the JSON:**
- the z window (730 days);
- the range quantity (TR / prior close);
- the return horizon of 7 daily bars (used by both DOWNSIDE and UPSIDE);
- for level reaction: price point, member scope and aggregation;
- for level volume: attribution span, comparator series, member scope and
  aggregation;
- the horizons of momentum persistence (M12) and add momentum (M4);
- the evaluation point of new structure;
- the newness reference of new structural confirmation;
- the entry-context condition of regime invalidation;
- the reading of the Setup B local high as the 52-week high.

**Earliest evaluable date** (Entry Conviction plus core regime, all venues):
**no earlier than 2024-03-24**, against the inventory's 2024-02-10 lower bound
(+43 days). The binding entries are `FLOW_Z_ETF_NORM_20D` and
`FLOW_Z_FLOW_ACCEL`. Entry Conviction is a data-dependent lower bound through
Structure. Per policy V6 §6A.8 this is an availability fact, not a stop.

**Composer census roots RBT-004/RBT-005 must promote:**
- `rolling_zscore`
- `rolling_percentile`
- `true_ranges`
- `price_momentum_from_daily_bars`
- `normal_cdf_score`
- `decision_greater_equal`
- `next_bar_timestamp`
- `_futures_basis_averages_by_time`
- `_futures_basis_history`

Input sources to classify: `replay_market_bars_at`,
`build_shared_replay_snapshot` and `load_closures`.

**Surfaced for the owner (AGENTS.md: not silently resolved).**

*Closure preconditions:*
1. **`MOMENTUM_PERSISTENCE_SCORE` overlaps Trend** (Rulebook 4.1/32.17).
   Z_M12 reaches Hold through Trend and directly. The overlap is explicit,
   quantified and versioned here but not validated. No overlap-free owner output
   exists. The owner chooses one of:
   - accept, with validation deferred to `SENSITIVITY_ONLY_NOT_SELECTION`
     reporting;
   - authorise a new persistence indicator;
   - leave Hold incomplete.
2. **The E1 class in `funding_health` and `open_interest_growth_health`.** The
   owner chooses one of:
   - keep it as a named limitation only;
   - extend §6A.9 in a policy V7.

*Recorded rulings open to review:*
- the z window (730 days);
- the 7-day return horizon (§6A.5 is not monotone through CAPITULATION/Setup C);
- the range quantity;
- the regime-invalidation band and entry-context exemption;
- the 52-week local high (weekly resolution);
- level families RBT-004 may cluster (a VP- or AVWAP-only support leaves
  Structure incomplete);
- the trailing-structure producer of `NEW_STRUCTURAL_CONFIRMATION`, with one add
  instant per structure.

**Pre-registration (§6A.1).**
- **Data consulted:** the bound inventory's availability and coverage facts
  (coverage snapshot, selected-source depth, earliest-evaluable facts,
  input-surface rows, census roots); owner code; configuration; Rulebook v1.2;
  policy V6; this track; synthetic fixtures in tests.
- **Not done:** no database connection and no environment read. No market
  value, score, signal, trade or performance figure was computed or inspected.
- **Holdout and BTC-019:** holdout NOT COLLECTED; BTC-019 untouched, sealed
  sample unopened.

**Pre-freeze review (internal; not the required independent review).**
- **Review.** A five-lens adversarial review (policy, citations, owner
  semantics, warm-up, red team), with one refuting skeptic per lens, found 39
  items. 34 were confirmed or partly confirmed. A verification pass and a
  completeness critic followed.
- **Fixes.**
  - the level-volume source helper (`build_canonical_market_bars` cannot yield
    1h bars);
  - `NEW_STRUCTURE_SCORE` missing-input causes under STRUCTURE_SCORE_V1_2;
  - the return-horizon rationale (not monotone);
  - never-filled statements on every entry;
  - helper census statuses;
  - citations;
  - lower-bound propagation and per-entry binding flags;
  - a primitives-drift refusal;
  - synthetic gap and boundary tests;
  - the higher-low structure timestamp mapping.
- **Unchanged after review:** the 730-day window, the range quantity and the
  momentum-persistence rule. Each is recorded and surfaced instead.

**V7 conformance update (owner-ruled, not a review finding).**
- Rebound the spec to `RESEARCH_BACKTEST_POLICY_V7`.
- All three positioning guards are frozen under `positioning_zero_variance_guards`;
  the original basis contract is retained as `e1_guard`. Funding uses
  `_funding_averages_by_time` and `_funding_average_history`; OI growth uses
  `_aggregate_open_interest_by_time`, `_open_interest_growth_by_time` and
  `_oi_growth_history`. These five additional helpers make 14 roots to promote.
- Each contract uses its own PIT prior history and exact Decimal equality,
  refuses its own reason with no health/z passed on, records structural
  unevaluability, and names five RBT-004 tests. The two owners' limitation is
  guarded. Momentum Persistence is ACCEPTED unchanged; V7 §6A.10/§8 and
  RBT-006/RBT-007's required non-selecting evaluation-only ablation are cited.
- New digest: `123590d1d5bf7f33f3748358b10bbf25e854782e065e7c2cd9c9c2df423a78fe`.
- This is separate from review-fix RBT002A-R1; no owner module is edited.

**Independent review corrections (2026-10-03).**
- RBT002A-R4 (P1): the new 730-day/30 z rule bypassed the feasible existing
  Flow/CVD 20-prior-observation/minimum-20 convention (V7 §6A.2). Apply that
  existing rule unchanged and uniformly to all seven native z inputs; retain
  exact equality, population SD, prior exclusion and no fills. Rejecting
  180/30 as weekly-infeasible (25 maximum) is sound, but does not authorize
  rejecting 20/20 for cadence preferences or a later warm-up. Independent
  owner-default/parity/cadence regressions pin the correction.
- Revised warm-up: all 26 per-entry records independently recompute from
  inventory facts; lower bound 2024-03-10, +29 days from inventory. Original
  730/30 dates and 2024-03-24 (+43) are preserved in review evidence.
- R4 resulting spec digest: `9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f`.
  There are now 16 NEW_PARAMETER elements; promoted roots remain 14.

- RBT002A-R3 (P2): a POSIX non-UTF-8 credential reached quote_plus and
  raised UnicodeEncodeError retaining the complete credential in .object.
  Detect surrogate code points before encoding; invalid credentials now
  raise DatabaseEnvironmentError retaining names only, with no context/cause
  exception. Two independent synthetic user/password regressions pin it;
  database/coverage/BTC-019 gate checks: 113 passed. Normal URL quoting is
  unchanged. Resulting spec digest (unchanged by this helper fix):
  `123590d1d5bf7f33f3748358b10bbf25e854782e065e7c2cd9c9c2df423a78fe`.

- RBT002A-R2 (P2): the new AST isolation scan missed relative importlib
  string imports and aliases of import_module. In-memory nested relative and
  aliased-import mutations returned an empty offender list before correction.
  Resolve relative names against the package argument and recognize importer
  aliases; four new mutations pin the correction. No actual guarded import
  exists and the original BTC-019 test stays byte-unchanged.
  Resulting spec digest (unchanged by this test-only fix):
  `123590d1d5bf7f33f3748358b10bbf25e854782e065e7c2cd9c9c2df423a78fe`.

- RBT002A-R1 (P1): uniform exact-constant refusal and time-to-row helper
  application are explicit mandatory stages. Resulting spec digest:
  `6af8bdc94ee963ad76efdb5576c800972da8d4792fe1ff9b3b327bfbed7efc19`.
  Regression: `test_research_backtest_completion_spec_review.py`, full-size
  non-terminating constants on native and 64-bit accumulators; helper-call
  witness, nonconstant parity and time-boundary/gap witness.

**Validation** (`.venv312` CPython 3.12.14; proof subsets run alone):

| Suite | Result |
| --- | --- |
| Focused: spec + database | **108 passed** |
| RBT-002 suites (coverage, census, nested, review, re-review, nine traces) + BTC-019 gate | **317 + 1 xfail** (known E1) and **16 passed** |
| RBT-001 | **167 passed** |
| Closure table | **145 passed** |
| BTC-180..185 | **282 passed** |
| BTC-220..224 | **342 passed** |
| Owner modules | **320 passed** |
| V5/corpus/ETF | **407 passed, 2 existing skips**; `v5_protocol_definition` = `95e43ee1...775a89` |
| PAD5 preserved-authority subset | **5 passed, 112 deselected** |
| PAD4-R5 namespace/child-order | **2 passed** |
| Inventory rebuild from its snapshot | byte-identical, `108ab25b...efe3a` |
| Spec determinism | byte-identical under `PYTHONHASHSEED` 0/1/8675309, another cwd, a fresh process; SHA-256 recomputed |
| `compileall -q btc_predictor etf_calendar_worker`; `git diff --check` | PASS |
| Full repository suite after Part 1 | **7267 passed, 3 skipped, 1 xfailed, 0 failed** (3053.57s) |

**Design decisions.**
- **Typed definition.** The definition is typed and declarative. Each element
  carries its own §6A.2 class, and an entry's governing class is the
  lowest-precedence tier it needs. Choices policy V6 itself fixes are labelled
  `POLICY_V6_MANDATE`. The omitted and inert entries are `POLICY_RULING`.
- **Warm-up.** Warm-up is computed by RBT-002's own primitives over the
  inventory snapshot. Spec series are injected into RBT-002's requirement graph,
  and the computation refuses if those primitives drift from the inventory.
- **Reuse of owner conventions.** Owner conventions are reused verbatim (owner
  constants are read, not restated).

**Remaining risks.**
- the two closure-precondition owner rulings above;
- the level-family choice and the trailing-structure producer, deferred to
  RBT-004/RBT-005 and recorded as obligations in their blocks;
- data-dependent Structure completeness for pre-warm-up pivots;
- the same-class E1 risk in funding and OI growth.


### RBT-002A review outcome

**Date:** 2026-10-03. **Review:** independent xHigh under `prompts/review_ticket.md`.
**Reviewed implementation:** Part 0 `75fc7e6`, Part 1 `09d14dc`, docs `ffce350`,
on owner-policy context `84a0de1`. V6/V7 owner decisions were not reviewed.
**Result: PASS / DONE.** Four genuine defects fixed,
with separate review-fix commits; no known correctness-critical ambiguity remains.

| ID / severity / disposition | Location and reproducer / independent regression | Commit |
| --- | --- | --- |
| RBT002A-R1 / P1 FIXED | `completion_spec.UNIFORM_ZSCORE.application_contract`. With a 64-bit accumulator, 730 equal 1/3 values produce -1 (annualized basis +1) instead of refusal. Explicit original-value equality now precedes float conversion/helper call. Full current/original windows, 0.1/1/3/annualized constants, current equal/different, both widths, no-call witness, exact tiny difference, gap/time adapter and nonconstant parity in `test_research_backtest_completion_spec_review.py`. | `352bba0` |
| RBT002A-R2 / P2 FIXED | `test_research_backtest_database.research_only_imports`. Nested relative `import_module('..research.btc019_empirical', __package__)` and aliased imports returned no offenders. Resolve relative strings and importer aliases; four independent mutations now report guarded identities. No actual guarded import; original BTC-019 test byte-unchanged. | `496a947` |
| RBT002A-R3 / P2 FIXED | `database.database_url_from_environment`. Surrogate-bearing synthetic credentials caused UnicodeEncodeError retaining the full value in `.object`. Precheck before encoding; raised error holds variable names only, no context/cause. User/password independent regressions, unchanged ordinary quoted URL. | `5b75882` |
| RBT002A-R4 / P1 FIXED | `completion_spec.UNIFORM_ZSCORE` source precedence. 180/30 is weekly-infeasible (25 max); the feasible existing Flow/CVD 20/20 convention was nevertheless rejected for cadence/recent-change/availability preferences. V7 §6A.2 does not permit that bypass. Adopt 20 prior defined native observations/minimum 20 uniformly, retain population/prior/PIT/equality/no-fill rules. Independent signature, owner-parity/cadence and 26-entry calendar regressions. | `42459e6` |

**Part 0:** PASS after R2/R3; exactly five POSTGRES names, same quoted URL,
name-only errors, no value-bearing exception chain/log/artifact. Seven EPIC Y
modules pass the mutation-tested AST scan. Original BTC-019 test SHA-256
`6e4127b4dd7365cd45bb86cd781e114f653b6c69bc5a54b24ed99ebc260d2d96` is unchanged.

**A–L acceptance:** A coverage, B precedence after R4, C uniformity/exact
refusal after R1/R4, D owner predicates/thresholds, E same-quantity Bitstamp
level volume, F optional/inert rulings, G all positioning guard contracts,
H 14 roots/complete arithmetic, I independent original+corrected date matrices,
J synthetic/PIT/no-DB pre-registration, K rulings below and L fresh-process
seed/cwd determinism PASS. Original 26 entries/45 occurrences and excluded
LIQUIDATION_PERCENTILE unchanged. Sixteen genuine NEW_PARAMETER elements
remain; all have scope-specific precedence audits and rationales.

**K rulings (human spec §6 numbering):**

| Item | Ruling |
| --- | --- |
| 3 Regime invalidation | LIMITATION: existing band/threshold mapping is sound; the bear-entry lifetime exemption and non-monotone exit/trade-count effect remain explicit. |
| 4 Local high | LIMITATION: existing 52-week high, weekly resolution/row-gap exposure; no new detector. |
| 5 730-day z window | DEFECT / FIXED R4: the existing feasible 20/20 owner convention has priority. It is not an owner question. |
| 6 Seven-day return | LIMITATION: explicit new horizon, no higher-tier source fixes this return input; CAPITULATION/Setup C prevents a global trades-less theorem. |
| 7 Range fraction | SOUND with recorded non-monotone flag effects: owner TR/prior close is an explicit new scale-free quantity, with no applicable higher-tier RANGE_PERCENTILE quantity. |
| 8 Level families | LIMITATION / RBT-004 obligation: VP/AVWAP-only support has no swing member; composition is fixed before any run/freeze. |
| 9 New structure | SOUND: trail/higher-low owner outputs, own structure timestamp, strict last ENTER/ADD newness; evaluate before STOP_MOVE; one opportunity per consumed structure. |

Items 1–2 stay owner-ruled under V7, never reopened. Measured-move omission
provably removes only tier-4 rescue eligibility at the same decision/context;
it is not claimed to prove a global path-dependent replay trade count.
LEVEL_VOLUME_PERCENTILE compares the same Q_L(d)=sum([d-L,d)) quantity,
member-specific fixed L, prior daily observations, current excluded; overlapping
comparators are declared, no new detector/binning or zero-fill.

**Step 4:** owner-ruled conformance commit **`700b924`**, separate from findings.
V7 rebind; three own-PIT-history exact equality contracts, five tests per owner,
no health/z on refusal, structural unevaluability; funding/OI guarded limitation;
five extra named history helpers (14 roots total); Momentum Persistence ACCEPTED
unchanged with mandatory RBT-006 freeze / RBT-007 evaluation-only base-cost
per-venue `SENSITIVITY_ONLY_NOT_SELECTION` ablation. Step-4 digest
`123590d1d5bf7f33f3748358b10bbf25e854782e065e7c2cd9c9c2df423a78fe`.

**Final spec digest:**
`9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f`.
Inventory unchanged `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`.
Original dates independently match the exact d9f9b334 artifact: lower bound
2024-03-24 (+43 days). Corrected dates independently match the final artifact:
2024-03-10 (+29), still DATA_DEPENDENT_LOWER_BOUND through Structure.

**Validation:** final focused **146 passed**; RBT-001/RBT-002/closure **630 passed,
1 existing E1 XFAIL**; BTC-180..185/BTC-220..224/owners/parity **1,068 passed**;
V5/corpus **492 passed, 2 existing skips**; final PAD5 preserved-authority subset
**5 passed**; compileall/diff check PASS. **Full: 7,305 passed, 3 skipped, 1 xfailed, 0 failed in 3023.38s.**
Spec deterministic under 0/1/8675309, fresh process/alternate cwd; all three
inventory artifacts byte-identical. V5 independently remains
`95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`.
Earlier full attempts interrupted for new corrections are not complete baselines.

Complete report, exact digest chain, A–L evidence, commands and both 78-record
calendar matrices: [review report](../../backtest_evidence/research_backtest_v1/rbt002a_review_report_v1.md),
[JSON evidence](../../backtest_evidence/research_backtest_v1/rbt002a_review_evidence_v1.json),
[offline reproducer](../../backtest_evidence/research_backtest_v1/rbt002a_review_reproducer_v1.py).
No database, environment file or real-data value/outcome; holdout NOT COLLECTED;
BTC-019 untouched/sealed sample unopened; no owner/config/bound-module/data/
research_artifacts edit. EPIC X's next remains POSTP1-001V2R1.
Recommended next dependency-satisfied ticket: **RBT-004 (READY)**, with **RBT-001A also READY**.


## RBT-001A — `EXTEND_REPLAY_INPUTS_TO_POLICY_V3`

**Status:** `DONE (2026-11-04) — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS; review FAIL (2026-11-03) fixed in f674284, 9171d63, 7cb11e0, 3b88daf and f785d81; N1 fixed in 6e2433e — rulings 4453b5c, implementation 524fcbf (2026-11-01); owner review rulings 4-6 (2026-11-03). RBT-002 independent R2 re-review PASS under V5 §5A.7; RBT-001 independent review PASS after a9773e7; policy V4 data rules ADOPTED and governed by V7.`
**Dependencies:** RBT-001 independent review PASS (SATISFIED, after `a9773e7`),
RBT-002 independent R2 re-review PASS (SATISFIED under V5 §5A.7)
**Implementation effort:** high
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/replay_inputs.py` (extended in a
new generational module or additively; the reviewed RBT-001 behaviour must not
change)

Extend the reviewed builder from `HISTORICAL_REPLAY_AVAILABILITY_V1` to `_V2`
(policy V3 §4). Acceptance criteria:

- Applies the record-shape rules to every input RBT-002's enumeration
  classifies, including futures basis, liquidations and market cap (as
  hash-bound evidence files) at their pinned semantics.
- `DISCRETIONARY` inputs are supplied as not asserted (`None`) and listed.
- Inputs the RBT-002 blocker list marks unsourceable are refused, not
  approximated.
- Every RBT-001 test still passes unchanged; V1-built manifests remain
  reproducible.
- New tests cover each shape's boundaries and a point-in-time property test
  through the real owners.

**Owner rulings (2026-11-01, asked before implementation; the recommended
option each time).** Policy V7 and the adopted data rules left these points
open:

1. **RBT-001A produces `LIQUIDATION_PERCENTILE`.** No executable owner
   computes it; EPIC X froze it only as the contract
   `PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1`. The builder shapes the
   hourly per-side Kraken Futures `PI_XBTUSD` rows (`INTERVAL`, available at
   the hour's end), applies `HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1` day
   completeness, and executes that contract by reference: its window (730
   days, half-open), minimum (365 prior observations), current day excluded
   from its own history, unusable days excluded from both value and history,
   and the midrank convention through the volatility owner's
   `_percentile_rank`, all imported, nothing restated. It emits the entry
   composer's `LiquidationPercentileObservation`: day D is observed at
   D 00:00 (the owner's bar-start convention, so 730 prior days) and available
   at D+1 00:00.
2. **A corroboration disagreement refuses the build.** RBT-003's Kraken
   adapter supplies one typed record per hour (status, the result of the
   comparison with Kraken's hourly liquidation-volume series, an evidence
   digest), and the builder checks them against the liquidation rows. The rule
   says the series "must agree within rounding", so any disagreeing hour fails
   the build with a refusal code; nothing is approximated, and RBT-003 must
   resolve or re-acquire before a dataset can freeze.
3. **Basis rows within 7 days of expiry are excluded and recorded.**
   `FUTURES_BASIS_CONTRACT_V1` excludes them and the raw table may hold them,
   so the builder drops each from the replay inputs (the owner averages every
   row sharing an `observation_time`) and lists it in the manifest with
   `FUTURES_BASIS_WITHIN_7D_OF_EXPIRY`. Rows that break the rest of the
   contract are refused: not at an hour close, not a Binance COIN-M `BTCUSD`
   quarterly, or an annualized rate that does not equal
   `basis_rate * 365 days / (expiry - t)` at the raw table's 18 decimal
   places.

**Owner review rulings (2026-11-03, on the independent review's findings and
questions; the recommended option each time).** They amend ruling 3 as
stated; the review outcome below records the findings.

4. **"Listed at t" comes from a listing evidence file (F2).** RBT-003 writes a
   hash-bound evidence file, like the market-cap file: for each contract, its
   Binance symbol, its delivery instant and its listing window (the open time
   of its first `1h` kline in the `data.binance.vision` archive), with the
   retrieved responses' SHA-256 values. A basis row is admitted only inside its
   contract's window and with that delivery instant as its `expiry`. The
   last-Friday calendar check and the `BTCUSD_YYMMDD` name check, which no
   policy authorises, are dropped: the evidence replaces them.
5. **One row per contract per instant.** A second copy of a contract at the
   same `observation_time` is refused whatever its provider, as the builder
   already does for liquidations, so `futures_basis_health` averages one row
   per listed contract.
6. **The annualisation stays strict, from the stored rate.** The
   `annualized_basis_rate` must equal the stored 18-place `basis_rate` times
   `365 days / (expiry - t)`, rounded half away from zero to 18 places.
   RBT-003's adapter must persist the basis rate first and derive the
   annualised rate from that persisted value.

The owner also chose to fix all four findings (F1-F4) in distinct review-fix
commits, followed by an independent xHigh re-review.

### RBT-001A Implementation Notes

**Status:** `DONE (2026-11-04)`: independent xHigh re-review PASS WITH
NON-BLOCKING FINDINGS. This block is the implementer's record of `413126b`;
the RBT-001A review and re-review outcomes below record the findings, the
review-fix (which supersedes design decision 2's name and calendar checks),
the N1 fix and the closure.

**Commits:**
- Rulings record, `4453b5c`: the three owner rulings above.
- Implementation, `524fcbf`: `btc_predictor/research_backtest/replay_inputs_v2.py`
  (new), the fixtures `btc_predictor/tests/rbt001a_replay_fixtures.py` (new)
  and `btc_predictor/tests/test_research_backtest_replay_inputs_v2.py` (new,
  90 tests).
- Docs, `413126b`: this block, the tasks table and `CURRENT_STATE.md`.
- Review FAIL and owner review rulings 4-6, `802a77a`.
- Review-fix, `f674284`, `9171d63`, `7cb11e0`, `3b88daf` and `f785d81`, with docs `7c48585`: the
  review outcome below.
- Non-blocking fix, `6e2433e`: re-review N1, a negative liquidation quantity
  refused.
- Docs, this documentation commit: the re-review outcome, N2's correction
  and the closure.

Every file is new. `replay_inputs.py` (the reviewed RBT-001 builder), every
owner, configuration, the RBT-002 inventory, the completion spec, the evidence
files, `data/` and `research_artifacts/` are unchanged, and so are the RBT-004
and RBT-005 composers.

**What the builder does.** `build_extended_replay_snapshot(shared_snapshot=...,
futures_basis=..., market_cap_evidence=..., liquidations=...,
liquidation_hours=...)` takes a finished V1 `SharedReplaySnapshot`, binds its
manifest by digest and never rebuilds it, and adds the families policy V3
introduced under `RESEARCH_BACKTEST_POLICY_V7` and
`HISTORICAL_REPLAY_AVAILABILITY_V2`. Its manifest is
`HISTORICAL_REPLAY_SHARED_SNAPSHOT_MANIFEST_V2` (builder
`EXTEND_REPLAY_INPUTS_TO_POLICY_V3`); it records the V1 snapshot's version,
builder, availability policy and digest, with the V1 families' rules
`rules_unchanged_under` V2 (policy V7 section 4 keeps them). As in V1, the
modelled value goes only into the availability field each owner reads, every
other field keeps its raw value, and the manifest keeps the raw times beside
it.

| family | shape | replay record | observation | modelled availability |
| --- | --- | --- | --- | --- |
| Futures basis | `SNAPSHOT` | `FuturesBasis.available_at` | the hour close t | `t` |
| Liquidations | `INTERVAL` | `Liquidation.available_at` | per-side `1h` aggregate stamped at the hour start h | `h + 1h` |
| BTC market cap | `DAILY_PUBLISHED` | `MarketCapObservation` | UTC day D, stamped `D+1 00:00` | `D+2 00:00` |
| `LIQUIDATION_PERCENTILE` | derived | `LiquidationPercentileObservation` | UTC day D at `D 00:00` | `D+1 00:00` |
| `MANUAL_RESEARCH_OVERRIDE`, `SYSTEMIC_EUPHORIA`, `SYSTEMIC_SHOCK` | `DISCRETIONARY` | none | n/a | never: not asserted (`None`), listed |
| US equity closures | `DAILY_PUBLISHED` | none (the composer loads the table) | the frozen table | required and recorded |

`REPLAY_SHAPES_V2` gives one shape to each of the eleven families, matching
every single-family raw and discretionary row of the RBT-002 inventory.
`ExtendedReplaySnapshot.entry_composer_inputs(dataset)` gives a venue run its
`EntryComposerInputs` (basis, market caps, liquidation percentiles) and refuses
a dataset over another shared snapshot.

**Design decisions** (each an implementation choice inside the rulings,
surfaced for the review):

1. *Additive generation.* V2 is a new module whose refusal class subclasses
   V1's and whose code set extends V1's closed set (twelve new codes). The V1
   builder still has no parameter for the new families.
2. *The basis contract as the replay accepts it.* `exchange="binance"`,
   `symbol="BTCUSD"`, `instrument="BTCUSD_YYMMDD"` (the delivery date, Binance's
   naming) and an expiry on the last Friday of March, June, September or
   December. RBT-003's adapter must write rows in this form. "Within 7 days" is
   `expiry - t <= 7 days`, so a row exactly 7 days out is excluded. The
   annualisation is recomputed from the stored `basis_rate` at 80 digits and
   rounded half away from zero to 18 places, as `NUMERIC(38,18)` rounds, so
   RBT-003 must derive the annualized rate from the stored basis rate. A
   duplicate is refused even when both copies would be excluded.
3. *Market-cap evidence file.* `BTC_MARKET_CAP_EVIDENCE_V1` is canonical JSON
   with exactly ten keys: version, provider `coinmetrics_community`, asset
   `btc`, metric `CapMrktCurUSD`, frequency `1d`, source, licence,
   `retrieved_at`, the retrieved responses' SHA-256 values, and rows of
   `{date, market_cap_usd}` (positive canonical decimals, strictly increasing
   dates). It is bound by the SHA-256 of its bytes, and
   `market_cap_evidence_bytes` writes it. The source supplies no publication
   time, so the `D+2 00:00` floor applies, and every value is labelled
   `REVISION_HISTORY_UNAVAILABLE` (final values only). A day is admitted when
   the whole day lies in the data window: 2025-12-31 is admitted, stamped
   2026-01-01 00:00 and available 2026-01-02, which exposes no holdout content,
   as for V1's last bar.
4. *Liquidation hour evidence.* `LiquidationHourEvidence(hour_start,
   feed_status, corroboration, evidence_sha256)` uses EPIC X's feed statuses
   `OBSERVED_WITH_EVENTS`, `OBSERVED_ZERO_EVENTS` and `SOURCE_UNAVAILABLE`
   (`LATE` and `INVALID` are refused: the historical rule has no such state).
   Corroboration is `AGREES`, `DISAGREES` or `SERIES_UNAVAILABLE` for an
   observed hour and `NOT_APPLICABLE` for an unavailable one. Ruling 2 refuses
   `DISAGREES`. An observed hour whose series has no value
   (`SERIES_UNAVAILABLE`) is refused too, because the rule's "must agree"
   cannot be shown; this extends ruling 2 and is surfaced. Rows must agree with
   their hour: an `OBSERVED_WITH_EVENTS` hour needs positive notional, an
   `OBSERVED_ZERO_EVENTS` hour has none (zero rows are allowed), and a
   `SOURCE_UNAVAILABLE` hour has no row. Every row needs its hour's evidence,
   `notional_usd` (the adapter's quantity is USD notional), the universe
   `kraken_futures` / `PI_XBTUSD` / `1h`, and a side named as the derivatives
   owner names positions (`long`, `short`). One row per hour and side, across
   providers, so nothing is counted twice.
5. *The percentile.* A day is complete when all 24 hours are observed; its
   quantity is the long-plus-short notional. Every day from the first to the
   last evidence day yields one observation: an incomplete day gives `None`
   with `LIQUIDATION_FEED_UNAVAILABLE` and enters no history; a complete day
   with fewer than 365 complete days in `[D - 730 days, D)` gives `None` with
   `LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY`. Both codes are the frozen
   contract's own. The value is `volatility._percentile_rank` (the contract's
   named convention owner, a private owner function imported by reference). A
   day is appended to the history only after its own value, so it is never in
   its own history; a mutation that widens the comparison to `<= D` is
   therefore equivalent.
6. *Unsourceable inputs.* CVD, spot dominance, macro, on-chain and liquidity
   (the inventory's `ABSENT_RULEBOOK_FALLBACK` set) are listed as
   `REFUSED_NOT_APPROXIMATED` with the policy fallback, and a `CvdObservation`
   supplied to any parameter is refused (`UNSOURCEABLE_INPUT_REFUSED`). Macro,
   on-chain and liquidity have no owner record to refuse.
7. *The closure table.* The V1 snapshot must have been built with
   `US_EQUITY_MARKET_CLOSURE_TABLE_V1` over its whole coverage (the composer
   loads the same range), so its ETF gap count is evaluated; the manifest
   records the table's version, definition and file digests and coverage.
8. *Manifest size.* Like V1, the manifest lists every record, plus every hour
   of evidence and every day's digest. A synthetic 800-day history with two
   rows an hour gives 24 MB; at real scale (Kraken depth from 2021-05-27)
   expect tens of MB. RBT-003 should store it compressed, as V1 advised.

**Tests (one new module, 90 tests, all passing).**

| area | what is pinned |
| --- | --- |
| shapes and declarations | the eleven-family shape table equals the inventory's; discretionary and unsourceable sets equal the inventory's; V1 versions, rules and codes unchanged; the refusal class and closed code set; the adapter's own reason codes; the closure table required (absent or partial refused) and recorded |
| futures basis | `SNAPSHOT` at t with raw times kept; the annualisation against an independent computation and a one-unit error refused; exactly 7 days excluded and recorded, never reaching `futures_basis_health`; nine contract breaches refused; duplicates; gaps across contracts |
| market cap | `D+1` stamp and `D+2` availability; the data-window edges (2020-01-01, 2025-12-31 admitted; 2019-12-31, 2026-01-01 refused); eleven malformed or unbound files refused; loading from a file; `open_interest_intensity` sees day D only from `D+2` |
| liquidations | `INTERVAL` at the hour's end through `aggregate_btc_derivatives_available_at`; ten row refusals; duplicates; eleven hour-evidence refusals including both corroboration rulings; eight status-and-rows cases |
| percentile | one observation per day at its end; every day against an independent oracle (more than 400 valued); incomplete days (an unavailable hour, a missing hour) excluded from history; the first value after 365 complete days; a zero-event day enters history; the window's edge (D-730 counts, D-731 does not); the composer reads day D at `D+1` |
| point in time | over five seeds, perturbing every value not yet available at a random cut changes no result of `futures_basis_health`, `open_interest_intensity`, `aggregate_btc_derivatives_available_at` or the visible percentiles at the cut, and changes a later one |
| manifest | binds the V1 snapshot without changing it; versions and shapes; declared inputs; the adapter by reference; identical under input reordering, in fresh processes under three hash seeds from another cwd; no socket opened; the composer inputs and a mismatched dataset refused |

Mutations of the builder (window 731 days, a 7-day row kept, market cap at
`D+1`, liquidation at the hour start, a disagreement accepted, a minimum of
364, an incomplete day entering history) each fail the module; the one survivor
is the equivalent mutation of decision 5.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-02).**
- The new module with the RBT-001 modules: 257 passed (31 s).
- RBT-001's own tests unchanged, the database isolation scan, the coverage
  guards and both spec modules: 380 passed in 46.61s before commit.
- V5 definition `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89` unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `524fcbf`, alone: 7,722 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `compileall` and `git diff --check` PASS.

**Acceptance criteria.**
- *Record-shape rules for every input RBT-002 classifies, including futures
  basis, liquidations and market cap (as hash-bound evidence files) at their
  pinned semantics:* the shape table test and the per-family groups above.
- *`DISCRETIONARY` inputs supplied as not asserted and listed:* the manifest
  test.
- *Unsourceable inputs refused, not approximated:* the unsourceable test and
  the manifest listing.
- *Every RBT-001 test still passes unchanged; V1-built manifests stay
  reproducible:* `replay_inputs.py` and its tests are untouched, they pass, and
  a V2 build leaves the V1 manifest bytes identical.
- *Each shape's boundaries and a point-in-time property test through the real
  owners:* the groups above.

**Limitations and surfaced points.** The decisions above, especially the basis
identity format (2), the evidence-file schema (3) and the `SERIES_UNAVAILABLE`
refusal (4), are formats RBT-003 must write. The ETF fund universe and launch
dates are `ENGINE_STATE` in the inventory with no shape; they stay inputs the
caller passes to `entry_composer_inputs` (RBT-003 source plan, RBT-006 freeze).
No real-data value, score, signal, trade or outcome was computed; no database
connection; holdout NOT COLLECTED; BTC-019 untouched, sealed sample unopened;
EPIC X unchanged (`POSTP1-001V2R1` remains its next ticket).

Recommended next dependency-satisfied ticket: **RBT-003** (READY); RBT-006
stays blocked on RBT-003.

### RBT-001A review outcome

**Date:** 2026-11-03. **Review:** independent xHigh ticket review, run at the
owner's request by the OpenAI Codex CLI (0.162.1, model `gpt-6.1-sol`,
reasoning `xhigh`) in a detached worktree at `413126b`, against the rulings
record `4453b5c`, implementation `524fcbf` and documentation `413126b` (base
`a8b253d`). Report-only: a workspace-write sandbox with network disabled, no
database, no `.env*` file, synthetic fixtures only; its worktree stayed clean.
**Result: FAIL.** RBT-001A is not DONE and RBT-003 stays blocked. The review's
three owner questions and the listing correction were answered the same day
(owner review rulings 4-6 in the ticket block).

**Findings.** Locations refer to `524fcbf`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| F1 / **P1 FIXED** | `replay_inputs_v2.py:475` | The builder checks that the market-cap evidence is a `MarketCapEvidence`, then trusts its fields: values changed after parsing keep the original file digest. An invalid digest string and duplicate dates also pass this path. | `dataclasses.replace(evidence, rows=...)` with a market cap of `600000000000` changed to `1`: accepted, claiming the original file's hash. Re-verify the whole payload against its digest at admission. |
| F2 / **P1 FIXED** (ruling 4) | `replay_inputs_v2.py:305` | "Listed at t" is checked only as `expiry > t` plus a name and quarterly-calendar heuristic; nothing shows the contract existed at t. | A synthetic `BTCUSD_991225` quote at `2024-02-01 13:00` (delivery December 2099) is accepted and reaches `futures_basis_health`. Require source-backed listing and delivery metadata. |
| F3 / **P2 FIXED** (ruling 6) | `replay_inputs_v2.py:307` | The recomputed rate uses precision 80, but the stored rate is quantised under the caller's decimal context. | A valid `NUMERIC(38,18)` row with basis rate `100000000000` raises `decimal.InvalidOperation` under the default precision 28 and is accepted under 80. Compare both sides in a sized local context. |
| F4 / **P3 FIXED** | `test_research_backtest_replay_inputs_v2.py:507` | `test_the_composer_reads_day_d_at_d_plus_1` checks timestamps only and never calls the composer. | With the frozen consumer replaced by an always-raising function, the test still passes. Exercise the real consumer with builder-produced observations. |

The review also asked the three questions that rulings 4-6 answer: the
authority for the last-Friday calendar, cross-provider duplicates (a second
provider's copy changed a synthetic `basis_rate_avg` from `0.015` to
`0.013333...`), and the persistence order of the two rates (for basis `1/3`,
rounding both from full precision gives `2.142333088774761555` where the
builder requires `...553`).

**Checks that passed.** Availability lands only in the fields the frozen
owners read and never precedes an observation's end; the market cap's `D+1`
stamp, `D+2` availability, last-day admission and the exact-instant OI join
(probed independently). The liquidation universe, sides, non-negative USD
notional, hour-status consistency and both corroboration refusals (refusing
`SERIES_UNAVAILABLE` "is consistent with requiring agreement"). The
percentile's completeness, observed zeros, unusable-day exclusion,
`[D-730, D)` history, 365 minimum, current-day exclusion, reason codes and
day-end availability match the frozen adapter. The 7-day boundary and the
exclusion manifest; the closure-table requirement; V2 canonical form,
reordering and hash-seed determinism; the V1 manifest binding; V1 code and
tests byte-unchanged. Codex's runs (`.venv312`, one process at a time): the
new module with both RBT-001 modules 257 passed in 33.08s; PAD5 subset 5
passed in 41.32s; PAD4-R5 2 passed in 26.21s;
`test_research_backtest_entry_composer_pit.py` 9 passed in 86.03s; `git diff
--check` clean. Its V5 recomputation differed only because the worktree has no
`data/` directory (six census files absent, all 42 present files matching
their frozen digests); the implementer's run in the full checkout reproduced
`95e43ee1...775a89`. The full suite was not rerun.

**Implementer's verification.** All four findings were confirmed from the
code before the rulings were asked. The caller's decimal context also governs
the daily liquidation sums and the percentile division, so the F3 correction
covers those too.

**Distinct review-fix:** `f674284`, `9171d63`, `7cb11e0`, `3b88daf` and `f785d81` (2026-11-03), each a
separate commit on top of the FAIL record `802a77a`. Only
`replay_inputs_v2.py`, its fixtures and its test module change; V1, every
owner, configuration, the inventory, the spec and the composers are unchanged.

- `f674284` (F1): admission writes the market-cap evidence record back as its
  canonical `BTC_MARKET_CAP_EVIDENCE_V1` bytes and parses them against the
  digest the record claims, then uses the verified copy (the manifest's
  evidence section too). A changed field, a malformed or other digest, a wrong
  type or an invalid row is `MARKET_CAP_EVIDENCE_REFUSED`; a changed record
  carrying its own new digest is a different bound file, named as such.
- `9171d63` (F3, ruling 6): two explicit decimal contexts. Sums and the
  annualisation run at 80 digits; the volatility owner's `_percentile_rank`
  runs under the decimal module's documented default (28 digits, half-even),
  stated so a caller's context cannot change a percentile. The implementer
  found the same dependence in the daily liquidation sums and the percentile
  division. The stored annualised rate must equal the stored rate's
  annualisation exactly (compared by value, never quantised), and every basis
  rate, annualised rate, liquidation quantity and notional must fit the raw
  tables' `NUMERIC(38,18)` (`RECORD_TYPE_REFUSED`): within that range every
  sum is exact. A 19th decimal place on the annualised rate, previously
  accepted, is refused.
- `7cb11e0` (F1 follow-up, found by the implementer): the parser accepted
  other spellings of a valid instant or date (`Z`, a space, another offset,
  `20240201`), which F1's write-back then refused at admission. The parser now
  requires the writer's spellings, so a file it accepts is one admission
  accepts.
- `3b88daf` (F2, rulings 4-5): `FUTURES_BASIS_CONTRACT_LISTING_EVIDENCE_V1`,
  a hash-bound canonical JSON file with exactly eight keys (version, exchange
  `binance`, symbol `BTCUSD`, source, licence, `retrieved_at`, the responses'
  SHA-256 values, and `contracts`), each contract exactly `{instrument,
  first_kline_open_at, delivery_at}`: instruments unique, the first kline on
  the hour and before delivery, deliveries strictly increasing. A basis row is
  admitted only for a listed contract, with its `expiry` equal to the listed
  delivery, and only at hour closes `first_kline_open_at + 1h <= t <
  delivery_at` (the basis at t uses the kline closing at t); otherwise
  `FUTURES_BASIS_CONTRACT_NOT_LISTED` or, for the expiry,
  `FUTURES_BASIS_CONTRACT_REFUSED`. Basis rows without the evidence are
  `FUTURES_BASIS_LISTING_EVIDENCE_REFUSED`. The calendar and name checks are
  removed. The listing is re-verified at admission like the market cap and
  recorded in the manifest. Ruling 5: the duplicate key is (t, instrument), so
  a second provider's copy is `DUPLICATE_RECORD_REFUSED`. The two evidence
  parsers share their digest, canonical-form and provenance checks.
- `f785d81` (F4): the composer test builds an `EntryComposer` from the
  snapshot's `entry_composer_inputs` and calls
  `_DecisionRun._liquidation_percentile` directly, as the RBT-004 boundary
  tests call the run's steps: for every day D the consumer returns D's
  percentile at `D+1 00:00`, a missing value records the composer's cause and
  carries the builder's reason code, and nothing is read before the first
  evidence day.

**Tests.** The module has 161 tests (90 before): F1 16 (15 changed-record
variants, the re-digested file), F3 13, the F1 follow-up 4 spelling variants,
F2 and ruling 5 38 (the reviewer's 2099 contract refused until listed, the
listing window's edges, a name and calendar no dropped rule would allow
admitted when listed, rows need the evidence, 22 malformed listing files,
8 listing records changed after parsing, ruling 5, one breach case for an
expiry that is not the listed delivery). Three breach cases now expect
`FUTURES_BASIS_CONTRACT_NOT_LISTED` as ruling 4 requires (the perpetual, an
unlisted instrument, a delivered contract); no assertion was weakened. Each
fix's new cases fail without it: F1's 15 with the re-verification disabled,
F3's 12 against the previous builder, the follow-up's spellings parse then
refuse under `9171d63`; seven mutations of the F2 and ruling 5 checks each
fail the module; F4's test fails with the consumer replaced in memory two
ways (raising, reading day t). The third mutation claimed here, a consumer
ignoring availability, does not fail it: every builder observation is
available at the first instant the consumer reads it (corrected after
re-review N2).

**Validation (`.venv312`, CPython 3.12.14, 2026-11-04).**
- The new module with the RBT-001 modules: 328 passed.
- V5 definition `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89` unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `f785d81`, alone: 7,793 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean.

**Surfaced for the re-review.** The listing evidence schema and its window
convention (`first_kline_open_at + 1h`) are formats RBT-003 must write, with
`BTC_MARKET_CAP_EVIDENCE_V1`'s now-strict spellings. The percentile's context
is the documented default, stated, not a new formula. The `NUMERIC(38,18)`
range check is new refusal behaviour taken from the raw schema
(`0012_create_derivatives_raw_schemas`). The basis gap series is still grouped
by provider, a manifest diagnostic only. The re-review outcome below records
the result.

### RBT-001A re-review outcome

**Date:** 2026-11-04. **Review:** independent xHigh re-review by the same Codex
CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in a new detached
worktree at `7c48585` under the same report-only rules; its worktree stayed
clean. **Reviewed:** `413126b..7c48585`, that is the FAIL record `802a77a`,
review-fix `f674284`, `9171d63`, `7cb11e0`, `3b88daf` and `f785d81` and documentation `7c48585`, against the review FAIL of
`4453b5c`, `524fcbf` and `413126b` and owner review rulings 4-6.
**Result: PASS WITH NON-BLOCKING FINDINGS. RBT-001A is DONE.** F1-F4 are fixed
(F2 and F3 as ruled) and rulings 4-6 are met; no new blocking defect was found.

| Finding | Re-review status and evidence |
| --- | --- |
| F1 | **FIXED.** A changed value, an invalid digest and a duplicate date each refuse admission; ten canonical evidence round trips succeed; the verified copy supplies the replay values and the manifest's evidence section. |
| F2 | **FIXED as ruled** (rulings 4-5). The 2099 contract is refused without matching listing evidence, and altered listing records fail re-verification. Probes confirm the window `first_kline_open_at + 1h <= t < delivery_at`, the exact expiry match, and that the names and delivery dates the evidence defines are admitted. A second provider's copy of a contract and instant is refused. |
| F3 | **FIXED as ruled** (ruling 6). The original large valid row gives identical manifests at precisions 3, 5, 28 and 80; a one-unit annualisation error is refused; 500 further cases match independent rational calculations. |
| F4 | **FIXED.** The test calls the frozen consumer: an always-raising consumer and a wrong-day lookup each fail it. See N2 for the third claimed mutation. |

The `NUMERIC(38,18)` bounds match the raw schema: the maximum magnitude,
representable trailing zeros, and refusal of a nonzero nineteenth decimal
place. Exact liquidation sums and default-context percentiles matched
independent calculations across 397 synthetic days. Market-cap timing,
liquidation completeness and corroboration, the percentile windows and
minimum, the closure-table requirement, manifest determinism and the isolation
checks still pass. The V1 files are byte-unchanged and their 167 tests pass.
No test function was removed and the original assertions remain; exactly
three refusal expectations changed, as ruling 4 requires. The documentation
was found accurate apart from N2.

| ID / severity | Location (`7c48585`) | Finding | Disposition |
| --- | --- | --- | --- |
| N1 / **P2 FIXED** | `replay_inputs_v2.py:900` | Admission checked the sign of `notional_usd` but not of `quantity`, which the raw table constrains (`0012_create_derivatives_raw_schemas.py:240`, `ck_liquidations_quantity_non_negative`): an observed-with-events hour carrying quantity `-1` and notional `100` was admitted and replayed with quantity `-1`. It predates the review-fix. Persisted rows already carry the constraint, and the percentile reads only the USD notional, so no admissible build's output changes. | Fixed in `6e2433e`: either field below zero is `RECORD_TYPE_REFUSED`, matching the raw table's two sign constraints. A new breach case (quantity `-1`, notional `100`) fails without the check. |
| N2 / **P3 FIXED** | `research_backtest_track_v1.md:3287` | The review-fix record claimed that F4's test fails when the consumer ignores availability. Removing only the consumer's `item.available_at > self.t` check leaves it passing: every builder observation of day D is available at `D+1 00:00`, the first instant the consumer reads it, so that check never fires on builder output. | Corrected in this documentation commit: the record names the two mutations the test kills and why the third survives. The consumer's check is unchanged and correct. No delayed-observation case was added, since the builder produces none. |

Codex's runs (`.venv312`, one process at a time, `-p no:cacheprovider`): the
V2 module with both RBT-001 modules 328 passed in 37.14s; the PAD5 subset
5 passed; PAD4-R5 2 passed; `test_research_backtest_entry_composer_pit.py`
9 passed; its recreated probes of the prior findings, the numeric and listing
boundaries, the evidence round trips, the consumer test and the remaining
checks confirmed the fixes and reproduced N1 and N2; `git diff --check` clean. Its worktree has no `data/`, so the V5
definition recomputed there to `09a4361b...5195355`, with six frozen census
files absent and all 42 present files matching their frozen hashes; the main
checkout reproduces `95e43ee1...75a89` (below). It did not run the full suite.
No owner question was raised.

**Non-blocking fixes**, made after the PASS as the owner chose (2026-11-04),
without a further re-review: `6e2433e` (N1) changes `replay_inputs_v2.py` and
its test module only (162 tests); no V1, owner, configuration, inventory, spec
or evidence change. The N2 correction is in this documentation commit.
Validation at `6e2433e` (`.venv312`, CPython 3.12.14): the V2 module with the
RBT-001 modules 329 passed; V5 definition `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89` unchanged; PAD5 subset 5 passed, 112 deselected;
PAD4-R5 2 passed; full repository, alone: 7,794 passed, 3 skipped, 1 xfailed, 0 failed (79 min). Synthetic fixtures only: no
database, no real-data value or outcome.

Recommended next dependency-satisfied ticket: **RBT-003** (READY). RBT-006
stays blocked on RBT-003.

## RBT-003 — `BACKFILL_HISTORICAL_INPUTS_V1`

**Status:** `DONE (2026-11-11) — independent xHigh closure review PASS WITH NON-BLOCKING FINDINGS (one P3, C1, corrected in the docs); Part B dataset built, verified and indexed 2026-11-11 (re-request: every scheduled hour still missing, kept as gaps; build at 5e78ab7, verify passed; private commit f36ad14; public index 98d8e14); Part B re-request and dataset build second re-review PASS 2026-11-11 (no new finding; the re-request and dataset build code review closed; the owner's re-request run and the build next on 5e78ab7's code); Part B re-request and dataset build re-review fixes DR1-DR3 committed 2026-11-11 (9175a9c..5e78ab7); Part B re-request and dataset build review-fix re-review FAIL 2026-11-11 (one P2, DR1, and two P3, DR2 and DR3; D1, D2, D4 and D6 fixed, D3 and D5 in part; owner: fix all three and two test gaps, the manifests' text owner-accepted); review fixes D1-D6 committed 2026-11-10 (0219a41..2d0307b); Part B re-request and dataset build code review FAIL 2026-11-10 (five P2, D1-D5, and one P3, D6; rulings 15 and 16 implemented as ruled; owner: fix all six, then re-review); Part B re-request and dataset build code 7e4f871 committed 2026-11-10; Part B owner ruling 16 2026-11-10 (14 Kraken hours disagreeing with the series withheld, their 13 days incomplete); Part B owner ruling 15 2026-11-10 (the 27 missing Coinbase/Bitfinex hours re-requested before the dataset build, written and reviewed with it); Part B CoinGlass collected 2026-11-10 on d9e611f (every Part B source collected; evidence committed privately; dataset build next); Part B R14-1 re-review PASS 2026-11-10 (no new finding; ruling 14's code review closed; CoinGlass to be collected on d9e611f); Part B R14-1 fix d9e611f committed 2026-11-10; Part B ruling 14 code review FAIL 2026-11-10 (R14-1 P2: a CoinGlass number no decimal can hold raises instead of refusing; ruling 14 implemented as ruled; owner: fix, then re-review); Part B ruling 14 code 87dc505 committed 2026-11-09; Part B Kraken liquidations complete (four refused days collected on 3041d0c 2026-11-09); CoinGlass's first live responses omit two members; owner ruling 14 (the envelope's msg and a fund day's btc_holdings may be absent) to implement and re-review; Part B ruling 13 code review PASS 2026-11-09 (no new finding; ruling 13's code review closed; four refused Kraken days to be collected); Part B ruling 13 code 3041d0c committed 2026-11-09; Part B refused Kraken days collected on c5fa819 2026-11-09 except four (an identical repeated block of executions); owner ruling 13 (identical copies collapse and are counted, a differing repeat still refuses) to implement and re-review; CoinGlass may run meanwhile; Part B ruling 12 fourth re-review PASS WITH NON-BLOCKING FINDINGS 2026-11-09 (R12-6 to R12-8 fixed, R12-9 in part; one P3, R12-10, owner-accepted; ruling 12's code review closed; refused days to be collected); Part B ruling 12 third review-fix c5fa819 committed 2026-11-08; Part B ruling 12 third re-review FAIL 2026-11-08 (two P2, R12-6 and R12-7, with the implementer-found R12-8 and R12-9; owner: fix all four, then re-review; refused days wait); Part B ruling 12 second review-fix 7808213 committed 2026-11-08; Part B ruling 12 second re-review FAIL 2026-11-08 (two P2, R12-2 and R12-3, with the implementer-found R12-4; owner: fix all three, then re-review; refused days wait); Part B ruling 12 review-fix 029057e committed 2026-11-08; Part B ruling 12 re-review FAIL 2026-11-08 (one P2, R12-1; owner: sum each side exactly, then re-review; refused days wait); Part B ruling 12 code fd702fe committed 2026-11-08; Part B Kraken liquidation collection stopped 2026-11-08 at a day listed out of time order; owner ruling 12 (count such steps, do not refuse); collection continued past refused days; CoinGlass and the dataset build next; Part B fifth re-review PASS 2026-11-07 (no new finding), Part B code review closed; Part B fifth review-fix 197c8c5 committed 2026-11-07; Part B fourth re-review FAIL 2026-11-07 (one P2, BR7; owner: fix value-blind, then re-review; Kraken liquidations and CoinGlass wait); Part B fourth review-fix e866317 committed 2026-11-07; Part B third re-review FAIL 2026-11-07 (one P2, BR6; owner: fix value-blind, then re-review; Kraken liquidations and CoinGlass wait); Part B third review-fix 25e4bcd, 9875a7c, 9644715 committed 2026-11-06; Part B second re-review FAIL 2026-11-06 (three P2, BR3-BR5; owner: fix all three, then re-review; Kraken liquidations and CoinGlass wait); Part B second review-fix 15f0d92, 75a60f8 committed 2026-11-06; Part B re-review FAIL 2026-11-06 (two P2, BR1-BR2; owner: fix both, then re-review; Kraken liquidations and CoinGlass wait); Part B review-fix 43ddb46..7a9de7d committed 2026-11-05; non-CoinGlass collection done on 4cf0993 (evidence 76496db, private); Part B code review FAIL 2026-11-05 (one P1, five P2, two P3; owner: fix all eight, then re-review; Kraken liquidations and CoinGlass wait); Part B code committed 2026-11-05 (3301b16..4cf0993), first step's live checks done, owner Part B rulings 9-11; Part A third independent xHigh re-review PASS (2026-11-05; no new finding), Part A review closed; third review-fix 3f3a801; second re-review FAIL 2026-11-05 (one P2, N3); second review-fix 85cfc8f, d7d43a0 (owner re-review ruling 8); re-review FAIL 2026-11-05 (two P2); review-fix a3bfa6e..00ba499 (owner review rulings 6-7); review FAIL 2026-11-04; Part A IMPLEMENTED (2026-11-04, 1427053), offline; owner rulings 2026-11-04; Part B (collection) awaits database write access, network access, the CoinGlass purchase with the documented ETF date bounds, and the evidence-storage decision. RBT-001A DONE (2026-11-04); RBT-002 independent R2 re-review PASS and RBT-001 review PASS`
**Dependencies:** RBT-001A, RBT-002
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

**Owner rulings (2026-11-04, asked before implementation; the recommended
option each time).** The session has no database variables, no CoinGlass key
and a public repository, and the rulings so far leave these points open:

1. **Two parts; Part A is offline.** Part A builds the new provider adapters
   (Binance USD-M funding, open interest and perpetual volume; Binance COIN-M
   basis and the contract listing; Kraken Futures executions and the hourly
   liquidation-volume corroboration; Coin Metrics market cap; CoinGlass ETF
   flows and AUM) and the RBT-001A evidence writers, written to the providers'
   documented formats and tested on synthetic fixtures only: no network, no
   database, no purchase. Part B, the collection run, waits until the owner
   provides database write access and network access, buys the CoinGlass
   Hobbyist month (USD 29), and decides where value-bearing evidence files
   live, since the repository is public.
2. **A contract's delivery instant is its symbol date at 08:00 UTC, checked.**
   Ruling 4 of RBT-001A gives no source for it, and a contract delivering after
   2025-12-31 (for example `BTCUSD_260327`, which trades inside the data
   window) has its last archive kline in the holdout. `delivery_at` is the
   `YYMMDD` date in the Binance symbol at 08:00 UTC, Binance's documented COIN-M
   delivery time, recorded as the rule. For every contract delivered inside the
   data window, the adapter checks it against the archive (the last `1h`
   kline's open plus one hour) and refuses a mismatch. Nothing from 2026 is
   read.
3. **"Within rounding" means equal at the series' precision.** An hour AGREES
   when its long-plus-short liquidation quantity (USD notional: quantity times
   EPIC X's 1 USD contract size) rounded half-even to the decimal places of
   Kraken's published hourly value equals that value; anything else DISAGREES,
   which refuses the build (RBT-001A ruling 2). Part B first checks the
   series' unit on one live in-window hour and stops to ask if it is not USD
   contracts.
4. **Differing duplicate open-interest rows leave a gap.** Binance's early
   daily metrics files hold two rows per 5-minute slot. Byte-identical
   duplicates of the `hh:00` row collapse to one; differing duplicates leave
   that hour with no snapshot, recorded as a gap in the collection evidence,
   never a choice between them.
5. **Unverified response shapes are built strictly.** The CoinGlass flow and
   per-fund history responses and the Kraken liquidation-volume response
   cannot be checked offline. Their adapters follow the shapes RBT-002 recorded
   and the providers' documented examples; any unexpected field or shape
   refuses the response. Both stay UNVERIFIED until Part B's first step checks
   one live in-window response each. CoinGlass's first live responses
   (2026-11-09) differ in two members, which owner Part B ruling 14 makes
   optional: the envelope's `msg` and a fund history day's `btc_holdings`.
6. **A listing start needs a month-start check (review ruling, 2026-11-04).**
   The independent review found that an absent earlier archive month is taken
   as proof that a contract did not yet exist, and no authority says so. A
   contract's first archived month is accepted as its listing month only when
   the month before it is absent and the first archived kline does not open at
   `00:00` on the 1st of its month: a contract already trading would have that
   kline. Otherwise the read refuses as `LISTING_START_UNPROVEN` (fail closed).
7. **`ingested_at` is the persistence instant (review ruling, 2026-11-04).** The
   existing collectors, which RBT-003 may not change, stamp every row's
   `ingested_at` with one instant per call. A persisted row's `ingested_at` is
   therefore the instant it entered the database, as the collector stamps it;
   its `available_at` is the retrieval instant of the responses the row was
   read from. No replay owner reads `ingested_at` on a derivative or ETF row.
8. **An empty archive does not prove absence (re-review ruling, 2026-11-05).**
   The independent re-review found that a contract month whose archive is
   present and verified but holds no kline, before the first month that holds
   one, is treated like an absent month. Every requested month before the
   first archived kline must be absent: a present archive without a kline
   does not prove that the contract was not trading, so the read refuses as
   `LISTING_START_UNPROVEN` (fail closed).
9. **Value-bearing files live in a private repository (Part B ruling,
   2026-11-05).** This repository is public and the providers' terms forbid
   publication (Coin Metrics CC BY-NC, Binance CC BY-NC-SA, CoinGlass personal
   use, Kraken unverified). Every value-bearing file Part B writes (the
   evidence files, the frozen datasets and their manifests, which carry every
   record) lives in the owner's private repository
   `wlodzimierrr/backtest_evidence`, checked out at `~/backtest_evidence`,
   under the same `research_backtest_v1/` layout. This repository keeps only
   value-free records under `backtest_evidence/research_backtest_v1/`:
   digests, sizes, counts, the gap census, provenance and the private
   repository's commit.
10. **CoinGlass is read through a reviewed projection (Part B ruling,
    2026-11-05).** Neither CoinGlass ETF endpoint takes a date bound:
    `flow-history` documents no parameter and `history` only `ticker`, so
    every response holds the full history, holdout and reserve included.
    Ruling 1's refusal of an unbounded request stands for every other
    provider. For these two endpoints only, Part B requests the full history
    and reads it through a projection that drops every record dated outside
    the requested in-window days before any of its values is parsed, as the
    RBT-002 disclosure ruling allows ("a reviewed transport projection that
    rejects/truncates out-of-window records before value
    parsing/logging/persistence"). The full response is never saved, printed
    or logged (only its digest and size are recorded), only the projected
    in-window records are kept, and each response is recorded as a metadata
    exposure. The projection is implemented, tested and independently
    reviewed before the first CoinGlass request. No out-of-window value is
    parsed or kept: the holdout remains NOT COLLECTED.
11. **The delivery instant is checked by volume (Part B ruling, 2026-11-05;
    amends ruling 2's check).** In the live archives of all 22 contracts
    delivered inside the window, the delivery day's `08:00` kline exists (with
    volume in 9 of them) and some archives continue with zero-volume klines
    to the month's end, so no last kline closes at delivery. The delivery
    instant stays the symbol date at `08:00` UTC. For every contract delivered
    inside the data window, the last kline with non-zero volume must close at
    `08:00` or `09:00` on the symbol date, so every later kline has zero
    volume; anything else refuses as `DELIVERY_INSTANT_MISMATCH`. Basis rows
    still use only hour closes before delivery, so no basis value changes.
12. **A Kraken execution day listed out of time order is counted, not
    refused (Part B ruling, 2026-11-08; amends Part A's liquidation rule 9).**
    The live execution log is not always in time order: on 2021-07-15 one
    execution is listed 1 ms before the one above it, inside a page, between
    two ordinary trades, while the day's chain is otherwise whole. A day's log
    is kept in the provider's order; an execution listed before an earlier one
    is counted, not refused, and the unit's summary records the day's count
    (`out_of_order_steps`). An execution outside the day, a repeated
    continuation token or uid, the page cap and the window guards still
    refuse. The hour records do not depend on the order (each hour selects its
    own executions, the sums are exact and the liquidation uids are sorted),
    so no liquidation value changes.
13. **A Kraken execution repeated as an identical copy collapses to one
    (Part B ruling, 2026-11-09; amends ruling 12 and Part A's liquidation
    rule 9, as ruling 4 does for open interest).** The live execution log
    repeats executions: on 2022-12-15, 2023-02-14, 2023-02-20 and 2023-03-17
    one contiguous block of executions is listed twice, back to back inside
    one page; every repeated element is identical to its first listing, with
    the same timestamp, and none is a liquidation. An execution whose uid was
    listed earlier in the day and whose element is identical to that first
    listing (the same JSON value, every number spelled the same way) is a
    copy: it is dropped, and the unit's summary records the day's count
    (`duplicate_copies`). A dropped copy is not part of the day's log, so it
    is not counted in `out_of_order_steps`. A repeated uid whose element
    differs in any way still refuses (`DUPLICATE_PROVIDER_RECORD`), never a
    choice between them; a repeated continuation token, an execution outside
    the day, the page cap and the window guards still refuse.
14. **Two CoinGlass members the live responses omit may be absent (Part B
    ruling, 2026-11-09; amends Part A's ruling 5 for CoinGlass and review
    F5).** CoinGlass's first live responses (the flow history and the
    history of each of its 11 funds) differ from the documented examples in
    two members only: no envelope carries `msg`, and 459 of IBIT's 479
    in-window history days omit `btc_holdings`, which no row uses. The
    envelope is `code` and `data`, with `msg` optional: when present it is
    a JSON string, kept in the projection as before. A fund history day's
    `btc_holdings` is optional: when present it is a finite JSON number.
    Every other member, kind and check is unchanged. An envelope whose
    `code` is not `"0"` refuses, naming the provider's code and, when
    present, its message (a status, never a record).
15. **The missing Coinbase and Bitfinex hours are re-requested before the
    dataset build (Part B ruling, 2026-11-10).** RBT-002's acquisition plan
    re-requests, through the existing adapters, the in-window `1h` hours its
    census found missing: 11 Coinbase hours in 5 runs and 16 Bitfinex hours
    in 7 runs (Bitstamp has none). A read-only check on 2026-11-10 found the
    same 27 hours still missing. The dataset build freezes each venue's
    price series in its manifest, so filling an hour after the build would
    change a frozen dataset. The re-request therefore comes first. A new
    collection source requests exactly those hours through the unchanged
    BTC-020 Coinbase and Bitfinex adapters over the backfill transport,
    whose allowlist gains those two hosts only. It persists through BTC-020's
    collector with its insert-only statement and no derived bars. An hour
    still missing stays a preserved gap. The source is written with the
    dataset build code, and one independent review covers both. The owner
    then runs the re-request, and the build follows.
16. **A Kraken hour that disagrees with the series is withheld, so its day is
    incomplete (Part B ruling, 2026-11-10; amends RBT-001A ruling 2 for the
    dataset build).** A dry build found 14 disagreeing hours on 13 days,
    from 2021-05-27 to 2024-02-26. It was read-only, ran in memory and wrote
    nothing. Each of the 14 hours is observed with liquidations, but its
    total differs from Kraken's published hourly series. Every other
    observed hour (39,865) agrees exactly, and none lacks a series value. In
    13 of the hours the executions total more than the series, and no
    neighbouring hour offsets the difference.
    The 14th, 2021-05-27 11:00, totals less: it is the first hour of the
    execution log's depth, so it is likely only partly covered. Under RBT-001A
    ruling 2, any disagreement refuses the build. Instead, the dataset build
    withholds each disagreeing hour from the V2 builder, both its hour
    evidence and its liquidation rows. Its day is then incomplete, exactly
    as an unavailable hour already makes it: it has no percentile value
    (`LIQUIDATION_FEED_UNAVAILABLE`) and enters no later day's history.
    Nothing is approximated. The frozen inputs keep every row as read, and
    the reviewed V2 builder is unchanged, so it still refuses a disagreement
    from any other caller. The withheld hours are listed in the build record,
    in the public index and here.

### RBT-003 Part A Implementation Notes

**Status:** `PART A IMPLEMENTED (2026-11-04)`, offline. This block is the
implementer's record, not a closure: the ticket's independent xHigh review and
Part B are outstanding.

**Commits:**
- Rulings record, `239578c`: the five owner rulings above.
- Part A, `1427053`: six new modules under `btc_predictor/research_backtest/`
  (`backfill_sources`, `backfill_binance`, `backfill_kraken`,
  `backfill_coinmetrics`, `backfill_coinglass`, `backfill_persistence`), the
  fixtures `btc_predictor/tests/rbt003_backfill_fixtures.py` and
  `btc_predictor/tests/test_research_backtest_backfill_adapters.py` (117 tests).
- Docs, this documentation commit: this block, the tasks table and
  `CURRENT_STATE.md`.

Every file is new. The collectors, the raw schema, the RBT-001 and RBT-001A
builders, every owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged. No network transport exists in Part A:
each adapter takes a caller-supplied `Transport`, and the tests supply fakes
(a module-wide guard fails any test that opens a socket).

**What Part A provides.**

| source (RBT-002 rank 1) | module | produces | rule |
| --- | --- | --- | --- |
| Binance USD-M `BTCUSDT` monthly `fundingRate` | `backfill_binance` | `FundingRate` at `calc_time` | pin `FUNDING_SETTLEMENT`; the settlement pricing 2019 excluded |
| Binance USD-M daily `metrics` | `backfill_binance` | `OpenInterest` at `hh:00`, USD | pin `OPEN_INTEREST_HOURLY_SNAPSHOT_USD`; ruling 4 |
| Binance USD-M monthly `1h` klines | `backfill_binance` | `PerpVolume` at the interval start | pin `PERP_VOLUME_INTERVAL_START` |
| Binance COIN-M quarterly and index `1h` klines | `backfill_binance` | `FuturesBasis` at the hour close, the listing evidence file | `FUTURES_BASIS_CONTRACT_V1`; RBT-001A rulings 4-6; ruling 2 |
| Kraken Futures `PI_XBTUSD` executions and hourly liquidation volume | `backfill_kraken` | per-side `1h` `Liquidation`, `LiquidationHourEvidence`, the hour evidence file | `HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`; RBT-001A rulings 1-2; ruling 3 |
| Coin Metrics Community `CapMrktCurUSD` `1d` | `backfill_coinmetrics` | the `BTC_MARKET_CAP_EVIDENCE_V1` file | pin `MARKET_CAP_END_OF_DAY` |
| CoinGlass `etf/bitcoin/flow-history` and `history` | `backfill_coinglass` | `EtfFlow` with the same day's net assets | pin `ETF_FLOW_DAILY_PUBLISHED`; ruling 5 (UNVERIFIED) |

`backfill_persistence` serves a finished collection to the existing
`collect_btc_derivatives` and `collect_etf_flows` through their provider
protocols, so Part B persists through the reviewed collectors unchanged.

**Design decisions** (implementation choices inside the rulings, surfaced for
the review):

1. *The window guard.* Every request is checked before the transport is
   called: each instant it names lies in `[2020-01-01 00:00, 2026-01-01 00:00)`
   (`REQUEST_OUTSIDE_DATA_WINDOW`). A returned observation outside that window is
   refused as `OBSERVATION_OUTSIDE_DATA_WINDOW` before any other check, never
   filtered, because it is an exposure to record. Archives are requested only
   for months or days inside the window; the Kraken chart is asked for `to` =
   the day's last hour start, so nothing past the day is requested.
2. *Provenance.* A raw row's `available_at` and `ingested_at` are the
   retrieval instant of the response it came from (the later of two for a
   basis row), as V1 notes a backfill does; the replay builders model
   availability. The retrieval log records URL, status, size and SHA-256 per
   response, never a header or a value, so the CoinGlass key is never
   persisted. Twelve refusal codes form one closed set.
3. *Names.* USD-M rows are `binance` / `BTCUSDT` with instrument `BTCUSDT`;
   basis rows use the V2 builder's `binance` / `BTCUSD` and the contract symbol;
   liquidations use V2's `kraken_futures` / `PI_XBTUSD` / `1h`. Providers are
   `binance_public_data`, `kraken_futures_rest_history` and `coinglass`.
4. *Archives.* Every Binance archive is checked against its published
   `.CHECKSUM` before it is read; an archive holds exactly its one named CSV,
   with or without a header row (two klines header spellings are accepted);
   millisecond epochs are exactly 13 digits; a kline closes one millisecond
   before the next hour.
5. *Funding.* The settlement at 2020-01-01 00:00 prices 2019 (the prohibited
   window) and V1 refuses it, so it is excluded and only its instant is
   recorded. An interval must be a positive whole number of seconds.
6. *Open interest and perpetual volume.* `sum_open_interest_value` is the USD
   open interest (RBT-002's pin) and the klines' quote volume the USD notional
   (the column RBT-002 named); both are quoted in USDT. A missing `hh:00` row or
   a missing day archive is a recorded gap.
7. *Contracts and the listing.* Contracts are the `BTCUSD_YYMMDD` directories
   the archive listing shows (paged by marker; a repeated marker refuses).
   Months are requested from twelve before delivery, clipped to the window,
   through the delivery month or December 2025: the first requested month must
   be absent (`LISTING_START_UNPROVEN` otherwise) and every month after the
   first archived one must exist (`ARCHIVE_MONTH_MISSING`). A contract first
   archived in 2026 is not listed inside the window. The listing file cites the
   listing pages' and contract archives' digests.
8. *Basis.* One row per hour close `t` with `first_kline_open_at + 1h <= t <
   delivery_at` and `t` inside the window, from the futures and index klines
   that open at `t - 1h`; a missing kline is a recorded gap. Rows within 7 days
   of expiry are written, and the builder excludes and records them (RBT-001A
   ruling 3).
9. *Liquidations.* One continuation chain per UTC day with `since` and
   `before`; a page outside the day, with a repeated token or a repeated uid
   refuses. A page out of order refused until owner Part B ruling 12
   (2026-11-08): an execution listed before the one above it is now counted,
   not refused, and the unit's summary records the day's count
   (`out_of_order_steps`). Since owner Part B ruling 13 (2026-11-09), a
   repeated uid whose element is identical to its first listing is a copy,
   dropped and counted (`duplicate_copies`); one that differs still
   refuses. Rows exist only for a side with liquidations in an
   observed hour: the hour evidence carries the status, so no zero row is
   written. An unknown taker direction refuses the day. Incidents are an input;
   `RBT002_RECORDED_INCIDENTS` holds the one RBT-002 recorded
   (2021-11-10 05:09-05:19), and Part B re-reads the incident list.
10. *The hour evidence file.* `HISTORICAL_LIQUIDATION_HOUR_EVIDENCE_V1`,
    canonical JSON with twelve keys (version, rule, corroboration rule,
    exchange, symbol, liquidation order type, contract size, source, licence,
    `retrieved_at`, incidents, hours); each hour holds its status,
    corroboration, execution count, sorted liquidation uids, per-side
    quantities, series value and response digests, and its canonical SHA-256
    is the hour's `evidence_sha256`. The parser recomputes every digest.
11. *Market cap.* One bounded request (`end_inclusive`, a page size covering
    the window), a next page followed only on the provider's own URL, missing
    days recorded; the file is written by the V2 builder's own writer.
12. *ETF.* A missing net-assets value leaves `aum_usd` `None` and is recorded,
    never zero-filled; rows are `FINAL_AS_RETRIEVED` with no publication time.

**Corrections after the review (2026-11-04).** The review-fix below
supersedes parts of decisions 1, 2, 6, 7, 10 and 11 and the persistence
paragraph; the rest stand as written.

- Decision 1: the window is also enforced at every Binance archive URL
  builder, at the archive fetch itself and at both Kraken URL builders (F7),
  and a Coin Metrics continuation is rebuilt from the bounded query (F1).
- Decision 2: a row's `available_at` is the retrieval instant of its own
  responses (a basis row: the later of the two archives holding its klines,
  F3). A persisted row's `ingested_at` is the collector's persistence instant
  (owner review ruling 7), not the retrieval instant.
- Decision 6: every hour of a perpetual-volume month without a kline is a
  recorded gap (F8); ruling 4 compares duplicate records by their bytes
  (F10).
- Decision 7: the first archived kline must also not open at `00:00` on the
  1st of its month (owner review ruling 6, F9), and every requested month
  before it must be absent, not archived without a kline (owner re-review
  ruling 8, N2).
- Decision 10: the series value keeps its published spelling, and the parser
  re-derives every hour and checks every declaration (F6), with no arithmetic
  in the caller's decimal context (N1); the spelling itself never depends on
  that context (N3).
- Decision 11: a next page is requested only as the bounded query plus its
  validated token (F1).
- Persistence: rows are persisted only through `persist_derivatives` and
  `persist_etf_flows`, which refuse a renamed request (F2).

**Tests.** 117 (56 functions). Each rule and guard has refusal cases, and the
integration tests feed adapter output to the builders it is written for: the
V2 builder admits the basis rows with their listing (and excludes the last
seven days), the liquidation rows with their hour records (and refuses a
disagreeing hour), and the market-cap file; V1 admits the funding, open
interest and perpetual volume; the BTC-021 and BTC-022 collectors persist
through the wrappers into a recording connection. The rounding rules are
checked against an independent rational computation. 24 in-memory mutants of
the rulings and guards (delivery check, listing start, month contiguity,
ruling 4, the 2019 settlement, basis rounding, window and kline offset,
checksum, a 2026 request, ruling 3 half-up and tolerance, incidents, side
mapping, chain span, series end, notional, evidence digest, the market-cap
window, an unbounded CoinGlass request, AUM zero-fill, row renaming, the
request span, an error read as empty) each fail the module.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-04).**
- The new module with the replay and database modules: 478 passed.
- The guard suites (database isolation, coverage, coverage census, BTC-019
  completion gate) with the replay modules: 593 passed.
- V5 definition `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89` unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `1427053`, alone: 7,911 passed, 3 skipped, 1 xfailed.
- `git diff --check` clean.

**Acceptance criteria (Part A).**
- *Existing collectors and protocols; adapters in new modules; no collector,
  schema or migration change:* met offline (the wrappers and both collectors
  are exercised); the persisting run is Part B.
- *Every persisted row keeps its true provider, source and ingestion
  provenance:* met for the rows Part A produces; a wrapper refuses a request
  that would rename them.
- *Frozen per-venue and shared-input datasets with manifests; a rebuild from
  the database reproduces them:* Part B.
- *Nothing outside the data window is requested:* enforced by the window guard
  and tested; Part B confirms it live.

**Part B prerequisites (owner).** Database write access (`POSTGRES_*`) and
network access; the CoinGlass Hobbyist month (USD 29) and key, together with
the documented date-bound parameters of both ETF endpoints (without them no
ETF request is built, since an unbounded one would return 2026 rows); and
where value-bearing evidence files live, since the repository is public
(Coin Metrics CC BY-NC, Binance CC BY-NC-SA, Kraken unverified, CoinGlass
personal use).

**Part B's first step, before any build.** One live in-window response each:
the CoinGlass flow and fund history field names; the Kraken chart's value
type, unit and whether `to` is inclusive; that Kraken honours `before`; the
Coin Metrics page shape; and the `orderType` `Liquidation` label against the
websocket's `liquidation` (RBT-002's open note). Any difference is a reviewed
adapter change, not a workaround.

**Surfaced points.** The USDT-quoted open interest and quote volume stored as
USD follow RBT-002's pins and named columns; under `ETF_CORE` the perpetual
notional is unused, while open interest feeds the OI/market-cap ratio. The
CoinGlass field names and date-bound parameters are unverified. The dataset
build and its compressed manifests are Part B. No real-data value, score,
signal, trade or outcome was computed; no database connection; holdout NOT
COLLECTED; BTC-019 untouched, sealed sample unopened; EPIC X unchanged
(`POSTP1-001V2R1` remains its next ticket).

Recommended next: the owner's choice of an independent xHigh review of Part A,
and the Part B prerequisites above.

### RBT-003 Part A review outcome

**Date:** 2026-11-04. **Review:** independent xHigh ticket review, run at the
owner's request by the OpenAI Codex CLI (0.162.1, model `gpt-6.1-sol`,
reasoning `xhigh`, session `01a1a849-79f7-7e90-a3f2-73727c6b1c35`) in a
detached worktree at `5ec5cad`, against the rulings record `239578c`,
implementation `1427053` and documentation `5ec5cad` (base `95b9cfb`).
Report-only: a workspace-write sandbox with network disabled, no database, no
`.env*` file, synthetic fixtures only; its worktree stayed clean.
**Result: FAIL.** Part B must not run this implementation unchanged. The
review's one owner question (finding 9) and the provenance question of
finding 3 were answered the same day (owner review rulings 6-7 above).

**Findings.** Locations refer to `1427053`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| F1 / **P1 FIXED** | `backfill_coinmetrics.py:77`, `:128` | A provider's `next_page_url` is followed after only its prefix is checked, so a continuation can name 2019, 2026 or no date bound: the request reaches the transport before any row is checked. | Synthetic first pages whose continuations ask for 2019, 2026-H1 or no bounds: all three reached the fake transport, and an empty continuation let the read finish. Rebuild or fully validate each continuation from the original bounded query before the transport. |
| F2 / **P2 FIXED** | `backfill_persistence.py:69`, `:110` | The collectors take `provider` from the request, which the wrappers never see: a request with only its provider changed persisted Binance and ETF rows under that name. | Validate the whole request, provider included, at a persistence entry point before the unchanged collectors run. |
| F3 / **P2 FIXED** (ruling 7) | `backfill_persistence.py:62`, `backfill_binance.py:623` | The collectors overwrite `ingested_at` with one call-level instant, contradicting design decision 2; and a basis row's `available_at` is the latest retrieval of any index month, not of the archives it was read from. | With an advancing clock, a row read by `10:00:12` was stamped `10:00:14`. Stamp each basis row from its own two archives; document `ingested_at` per ruling 7 and test it. |
| F4 / **P2 FIXED** | `backfill_kraken.py:390` | A liquidation row's notional is multiplied in the ambient decimal context. | The valid `NUMERIC(38,18)` quantity `12345678901234567890.123456789012345678` became notional `12345678901234567890.12345679`; the hour still AGREED and V2 admitted it. Multiply in the controlled context. |
| F5 / **P2 FIXED** | `backfill_coinglass.py:157`, `:178` | Ruling 5 is met for key sets only: the day's `flow_usd`, `price_usd` and a fund's `btc_holdings` may hold any value. | `{"unexpected":[]}` in any of them was accepted. Check every declared field's type. |
| F6 / **P2 FIXED** | `backfill_kraken.py:355`, `:439`, `:462` | The hour evidence stores the published value canonicalised (`1500.0` as `1500`), so ruling 3 cannot be recomputed from the file; the parser accepts a contract size of `100`, an order type `Limit`, an observed incident hour with zero executions that AGREES with `999`, and hours outside the window. | Keep the published exponent; validate the declarations, the window and each hour's status, count, incident and corroboration before returning typed evidence. |
| F7 / **P2 FIXED** | `backfill_binance.py:122`, `:156`; `backfill_kraken.py:146`, `:237` | The readers clip their periods, but the URL builders and the archive fetch accept any period: synthetic 2019 and 2026 archive requests went through. | Enforce the window at the callable request boundary. |
| F8 / **P2 FIXED** | `backfill_binance.py:381` | An empty or partial perpetual klines archive returns its present rows only: missing hours leave no gap record. | Compare each month with its hourly census and record the gaps. |
| F9 / **P2 FIXED in part** PLAUSIBLE (ruling 6; residual N2 in the re-review) | `backfill_binance.py:483`, `:492`, `:507` | A missing archive month before a contract's first archived month is read as proven absence: removing a synthetic contract's first month moved `first_kline_open_at` a month later without refusal. | Distinguish unavailable history from proven absence; the owner ruled the month-start check. |
| F10 / **P3 FIXED** | `backfill_binance.py:286` | Ruling 4 compares decoded CSV fields, not bytes: `1000000` and `"1000000"` collapse. | Compare the raw records. |

The review's mutation runner caught 12 of 17 mutants; the five survivors
removed either Coin Metrics date bound, made its end exclusive, or disabled
either CoinGlass duplicate check, and each passed all 117 tests.

**Checks that passed.** The normal basis path's listing-window inequalities,
one row per contract and instant, the 18-place rate and the builder-owned
annualisation; ruling 2 in the normal reader (a 2026 delivery read nothing
from 2026); funding at `calc_time` and the excluded settlement pricing 2019;
hourly USD open interest; interval-start perpetual volume; the market-cap
writer integration; the ETF final-value replay semantics. Every adapter
refused synthetic 2019 and 2026 observations; the Kraken day reader bounds its
chain and its final-day `before` is the exclusive `2026-01-01`; the CoinGlass
bound refuses before the transport. Pagination is bounded (listing 100 pages,
execution day 10,000, market cap 10). Checksum, single-member, epoch-width and
close-offset checks were exercised; the retrieval log holds no header; no
network transport or database connection exists. Codex's runs (`.venv312`,
one process at a time): the adapter module 117 passed; with the V1/V2 replay,
replay-review and database modules 478 passed; its own probes 47 passed;
PAD5 subset 5 passed, 112 deselected; `git diff --check` clean. The full suite
was not rerun.

**Implementer's verification.** All ten findings were confirmed from the code
before the owner was asked. F7 concerns the callable boundary below the
readers; the readers themselves request only in-window periods.

**Distinct review-fix:** `a3bfa6e`, `22bef37`, `09ba259`, `d7bd11c`,
`894bcc1`, `be01997`, `58e1248`, `ca09376`, `1b96bbf`, `423fb13` and
`00ba499` (2026-11-04), each a separate commit on top of the FAIL record
`7faea78`. Only the six new modules, the fixtures and the test module change.
The collectors, the raw schema, the RBT-001 and RBT-001A builders, every
owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.

- `a3bfa6e` (F1): a continuation's `next_page_url` must name the endpoint and
  repeat the bounded query exactly plus the page's own `next_page_token`. The
  request is rebuilt locally from that query and token, and a repeated token
  refuses. The continuation is checked after the page's rows, so a returned day
  outside the window is still refused as the exposure.
- `22bef37` (F7): each Binance archive URL builder refuses a month or day
  outside the window (a month is its first day, a `date`, not a `datetime`).
  `verified_archive` refuses, before the transport, any URL that is not a
  Binance archive naming an in-window period. The Kraken builders check
  `[since, before)` and `[since, to + 1h)`.
- `09ba259` (F2): `persist_derivatives` and `persist_etf_flows` check, before
  the unchanged collectors run, that the request names the rows' own exchange,
  symbol and provider and lies inside the window.
- `d7bd11c` (F3, ruling 7): each contract and index archive month keeps its
  retrieval instant, and a basis row at `t` takes the later of the two months
  holding the klines that open at `t - 1h`. The modules document ruling 7.
- `894bcc1` (F4): the hour's per-side sums, its total and each row's notional
  run in an 80-digit context that traps `Inexact`, so they are exact or
  refused. The implementer found the same ambient-context flaw in the funding
  interval's whole-second check, which is now an exact fraction; an interval
  too long for a `timedelta` refuses.
- `be01997` (F5): every declared CoinGlass field is type-checked (`msg` a
  string; a day's total `flow_usd` and `price_usd` and a fund's
  `btc_holdings` finite JSON numbers). The implementer added refusals for a
  repeated flow day and for a ticker repeated within a day, even without a
  value.
- `58e1248` (F6): the series value is stored as its exact published spelling.
  The parser checks every declared constant, canonical instants, the
  incidents, each hour inside the window, its incident flag, counts, uids,
  quantities and digests, and recomputes its status and corroboration. The
  collection's typed hours are read back through the parser.
- `ca09376` (F8): `read_perp_volume` returns rows and, from each month's
  hourly census, a `PERP_VOLUME_KLINE_MISSING` gap for every missing hour.
- `1b96bbf` (F9, ruling 6): a first archived kline at `00:00` on the 1st of
  its month refuses as `LISTING_START_UNPROVEN`.
- `423fb13` (F10): metrics records are read with their exact text (each line
  without its terminator). A record must be one line, and duplicates collapse
  only when their text is identical.
- `00ba499` (F9 follow-up, found by re-running the mutants): the
  first-requested-month case lists mid-month, so only that rule refuses it.

**Tests.** The module has 187 tests in 79 functions (117 in 56 before). No
expected refusal code changed. These expectations moved with the fixes:
- The synthetic contracts that listed at `2020-08-01 00:00`, now an unproven
  start under ruling 6, list at `2020-08-10 08:00`, and their first rows,
  counts and listing records follow. The contiguity case lists at
  `2020-06-10 08:00`, and the first-requested-month case lists mid-month.
- The perpetual-volume tests read `.rows` and now also assert the gaps.
- The market-cap follow test was replaced: its old continuation
  `?next_page_token=token` is now refused, and the foreign-URL refusal is kept
  with its code.

56 in-memory mutants each fail the module, among them the review's five
survivors. They are the 24 earlier mutants (three re-aimed at changed lines),
30 that each undo a fix, and the two CoinGlass duplicate checks.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-04).**
- The adapter module with the replay and database modules: 548 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `00ba499`, alone: 7,981 passed, 3 skipped, 1 xfailed, 0
  failed (79 min).
- `git diff --check` clean. Synthetic fixtures only: no network, no
  database, no real-data value or outcome.

The re-review outcome below records the result.

### RBT-003 Part A re-review outcome

**Date:** 2026-11-05. **Review:** independent xHigh re-review by the same Codex
CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in a new detached
worktree at `ed7f83a` under the same report-only rules; its worktree stayed
clean. **Reviewed:** `5ec5cad..ed7f83a`, that is the FAIL record `7faea78`,
review-fix `a3bfa6e`..`00ba499` and documentation `ed7f83a`, against owner
review rulings 6-7.
**Result: FAIL.** Nine prior findings are fixed (F3 as ruled); F9 is fixed in
part, and the new evidence parser added a regression. Part B must not run this
implementation unchanged. No owner question was raised; the owner ruled the
reading of ruling 6 that N2 turns on (re-review ruling 8 above).

| Finding | Re-review status and evidence |
| --- | --- |
| F1 | **FIXED.** Prohibited, holdout, unbounded and exclusive-end continuations refuse before a second transport call; valid continuations are rebuilt locally, safely encoded tokens included. |
| F2 | **FIXED.** Both persistence entry points refuse a renamed request before any statement reaches the recording connection. |
| F3 | **FIXED as ruled** (ruling 7). Advancing-clock probes confirm each basis row's own archive pair, month-boundary closes included; persistence keeps `available_at` and stamps `ingested_at` with the persistence instant. |
| F4 | **FIXED.** Full-width quantities and sums stay exact at caller precisions 3, 6, 28 and 80 (see N1). |
| F5 | **FIXED.** Objects in the formerly unchecked fields refuse; repeated days, fund histories and null-valued tickers refuse. |
| F6 | **FIXED** for the original defects. Published exponents survive the round trip; contradictory declarations, statuses, incidents and outside-window hours refuse; a matrix of valid hours passes (see N1). |
| F7 | **FIXED.** The archive builders, hand-built archive fetches and the Kraken builders refuse outside-window requests with no transport call. |
| F8 | **FIXED.** Empty and partial archives return exactly the missing-hour census with its reasons. |
| F9 | **FIXED in part** (ruling 6). The removed-first-month case refuses; a present but empty earlier archive does not (N2). |
| F10 | **FIXED.** Quoted and unquoted decoded-equal records leave a gap; identical ones collapse. |

| ID / severity | Location (`ed7f83a`) | Finding | Required correction |
| --- | --- | --- | --- |
| N1 / **P2 FIXED** | `backfill_kraken.py:565` | The evidence parser's check `uids and long + short == 0` adds in the caller's decimal context. Through `read_liquidations`, the valid quantity `12345678901234567890.123456789012345678` raises `decimal.Inexact` at precision 28 with `Inexact` trapped; `1E-18` at precision 3 and `Emin=-5` rounds to zero and refuses as "liquidations without a quantity"; the ordinary fixture fails at precision 3 with `Inexact` trapped. The writer accepts these hours, so the mandatory read-back refuses valid output. | Compare the two validated non-negative quantities with zero individually, or add in a controlled context; add trapped-context and underflow regressions. |
| N2 / **P2 FIXED** (residual F9, ruling 8) | `backfill_binance.py:567`, `:577` | The listing loop tracks whether klines have accumulated, not whether an archive was present. With January-April absent, May present with a valid checksum and an empty CSV, and June starting `2020-06-10 08:00`, `BTCUSD_201225` is accepted with June's start, though May was not absent. | Keep archive presence and refuse a present archive without a kline before the first kline as `LISTING_START_UNPROVEN` (ruling 8); test it apart from the first-requested-month case. |

The five mutants that survived the first review are caught, and Codex's own
runner caught all 24 of its mutants. Its test audit found only the documented
expectation changes and no changed refusal-code expectation, and it found the
new tests meaningful. `ed7f83a` records the fixes, the moved expectations and
the validation counts accurately, apart from the complete-fix claims that N1
and N2 qualify. Holdout probes of every adapter and the evidence parser found
no request built or sent, and no row admitted, outside the window; the holdout
remains NOT COLLECTED. Codex's runs (`.venv312`, one process at a time,
`-p no:cacheprovider`): the adapter module 187 passed; its recreated probes 90
passed; with the V1/V2 replay, replay-review and database modules 548 passed;
four edge probes failed, reproducing N1 and N2; PAD5 and PAD4-R5 7 passed;
`git diff --check` clean. It did not run the full suite.

**Implementer's verification.** Both findings were confirmed from the code
before the owner was asked: the parser's check adds outside `_EXACT_CONTEXT`,
and an empty CSV parses to no klines, which the loop cannot tell from an
absent month.

**Distinct review-fix:** `85cfc8f` and `d7d43a0` (2026-11-05), each a
separate commit on top of the re-review FAIL record `f931981`. Only
`backfill_kraken.py`, `backfill_binance.py` and the test module change; the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/` are
unchanged.

- `85cfc8f` (N1): the parser asks each stored quantity whether it is zero, so
  no arithmetic runs in the caller's context. Found by the implementer: the
  parser's exact corroboration sum refuses, rather than raising
  `decimal.Inexact`, when a malformed file stores quantities too wide to add
  exactly.
- `d7d43a0` (N2, ruling 8): a verified archive without a kline (no record, or
  the header only) before the first archived kline refuses as
  `LISTING_START_UNPROVEN`, and a contract whose only archives are empty is
  refused rather than read as unlisted.

**Tests.** The module has 193 tests in 81 functions (187 in 79 before): a
valid hour read back under three caller contexts (full width with `Inexact`
trapped, underflow at precision 3, an ordinary quantity with `Inexact`
trapped); a too-wide stored quantity refused; ruling 8 with an empty and a
header-only month (not the first requested month), the empty-only contract,
and the same history with that month absent still accepted. Each new case
fails with its fix reverted. No existing test or expectation changed.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-05).**
- The adapter module with the replay and database modules: 554 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `d7d43a0`, alone:
  7,987 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only: no network, no
  database, no real-data value or outcome.

The second re-review outcome below records the result.

### RBT-003 Part A second re-review outcome

**Date:** 2026-11-05. **Review:** the second independent xHigh re-review by
the same Codex CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in a
new detached worktree at `091c8cd` under the same report-only rules; its
worktree stayed clean. **Reviewed:** `ed7f83a..091c8cd`, that is the re-review
FAIL record `f931981`, review-fix `85cfc8f` and `d7d43a0` and documentation
`091c8cd`, against owner rulings 6-8.
**Result: FAIL.** N1, N2 and F1-F10 are fixed (F3 as ruled, F9 under rulings
6 and 8) and rulings 6-8 are met; one new P2. Part B must not run this
implementation unchanged. No owner question was raised.

| Finding | Second re-review status and evidence |
| --- | --- |
| N1 | **FIXED.** The four earlier edge probes pass, and so do 192 further arithmetic-context combinations of precision, exponent limits, rounding and traps. |
| N2 | **FIXED** (ruling 8). Empty and header-only months before the first kline refuse, empty-only contracts included; an all-absent contract stays unlisted, and an empty archive after the listing stays a recorded gap. |
| F1-F10 | **FIXED** (F3 as ruled; F9 under rulings 6 and 8; F6 for its original defects, see N3). The recreated probes of every finding pass. |

| ID / severity | Location (`091c8cd`) | Finding | Required correction |
| --- | --- | --- | --- |
| N3 / **P2 FIXED** | `backfill_kraken.py:387`, `:575` | `published_spelling` writes the series value with `str(value)`, whose exponent letter follows the caller's decimal `capitals` setting, and the parser requires that same spelling. A provider value of `0.00000000` is stored as `"0e-8"` under `capitals=0` and `"0E-8"` under `capitals=1` (likewise `1.5e+3`): identical responses give different evidence bytes and hashes, and a correctly hashed file is refused as `RESPONSE_SHAPE_REFUSED` when parsed under the other setting. | Spell the value independently of the caller's context, keeping its exponent and trailing zeros; add cross-context writer and parser tests. |

Codex's targeted mutation runner caught all 8 of its mutants (the five
first-review survivors, the N1 zero check, its too-wide refusal and the N2
guard). No existing test function body changed or was removed, the only
changed decorator adds the too-wide case, and the two new test functions fail
with their guards reverted. `091c8cd` describes the N1 and N2 fixes
accurately. Holdout probes of every adapter and the evidence parser found no
request or admission outside the window; the holdout remains NOT COLLECTED.
Codex's runs (`.venv312`, one process at a time, `-p no:cacheprovider`): the
adapter module with its 90 recreated probes and the four earlier edge probes
287 passed; with the V1/V2 replay, replay-review and database modules 554
passed; its expanded probes 208 passed and 6 failed, reproducing N3; an
in-memory counterfactual 501 passed; PAD5 and PAD4-R5 7 passed;
`git diff --check` clean. It did not run the full suite.

**Implementer's verification.** N3 was confirmed before the owner was asked:
`str(Decimal("0.00000000"))` is `0e-8` under `capitals=0` and `0E-8` under
`capitals=1`, while `Context(capitals=1).to_sci_string` gives `0E-8` under
both. It is the only Decimal-to-text conversion in the adapters whose output
follows the context: the other `str()` calls round-trip a number exactly or
accept digits only.

**Distinct review-fix:** `3f3a801` (2026-11-05), on top of the second
re-review FAIL record `ae5a1a1`. Only `backfill_kraken.py` and the test module
change; the collectors, the raw schema, the RBT-001 and RBT-001A builders,
every owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.

- `3f3a801` (N3): `published_spelling` spells the value through a fixed
  context with a capital `E`, keeping its exponent and trailing zeros, so the
  caller's `capitals` setting changes neither the evidence bytes nor what the
  parser accepts. Under the default context the bytes are unchanged.

**Tests.** The module has 196 tests in 82 functions (193 in 81 before): the
same responses collected under `capitals` 0 and 1 give identical evidence
bytes, and each file reads back under the other setting, for `0.00000000`,
`1.5e+3` and the exponent-free control `1500.0`. Both exponent cases fail with
the fix reverted. No existing test or expectation changed.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-05).**
- The adapter module with the replay and database modules: 557 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `3f3a801`, alone:
  7,990 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only: no network, no
  database, no real-data value or outcome.

The third re-review outcome below records the result.

### RBT-003 Part A third re-review outcome

**Date:** 2026-11-05. **Review:** the third independent xHigh re-review by
the same Codex CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in a
new detached worktree at `1881a8a` under the same report-only rules; its
worktree stayed clean. **Reviewed:** `091c8cd..1881a8a`, that is the second
re-review FAIL record `ae5a1a1`, review-fix `3f3a801` and documentation
`1881a8a`, against owner rulings 1-8.
**Result: PASS. Part A's independent review is closed.** N3, N1, N2 and
F1-F10 are fixed (F3 as ruled, F9 under rulings 6 and 8), rulings 6-8 are met
and no new finding was raised. RBT-003 stays IN PROGRESS: the frozen
datasets, manifests and reproducible database rebuild are Part B's, which
remains blocked on its prerequisites. No owner question was raised.

| Finding | Third re-review status and evidence |
| --- | --- |
| N3 | **FIXED.** `published_spelling` uses the fixed context's `to_sci_string`; the six failing cross-context probes of the second re-review pass, exponents and trailing zeros survive, and reverting the line reproduces those six failures and both new exponent cases. |
| N1 | **FIXED.** Each stored quantity is checked with `is_zero()`; the full-width, underflow and trapped-context probes pass, and a too-wide stored sum is refused under control. |
| N2 | **FIXED** (ruling 8). Verified empty or header-only archives before the first kline refuse, empty-only contracts included; an all-absent contract stays unlisted, and an empty archive after the listing stays a recorded gap. |
| F1-F10 | **FIXED** (F3 as ruled; F9 under rulings 6 and 8). The recreated probes of every finding pass. |

**Decimal-context audit.** Across 192 caller contexts varying precision,
exponent limits, rounding, traps, `capitals` and clamp, every adapter gave
identical evidence bytes, digests, decimal values, persisted results and
recording-connection parameters, and the liquidation, contract-listing and
market-cap evidence each read back under the other contexts. Eight
default-context comparisons against the `091c8cd` function gave identical
evidence bytes, hashes, typed hours and rows. No remaining dependency on the
caller's context was found.

Acceptance criteria for Part A: the existing collectors and provider
protocols are used with no collector, schema or migration change; provider,
source and ingestion provenance are true; nothing outside the data window is
requested or admitted in offline verification. Holdout probes of every
adapter's request and response guards, all with synthetic responses, found no
request or admission outside the window; the holdout remains NOT COLLECTED.
An AST comparison with `091c8cd` found every earlier test function and
decorator unchanged and one test function added, whose two exponent cases
fail with N3 reverted. `1881a8a` describes the fix accurately.

Codex's runs (`.venv312`, one process at a time, `-p no:cacheprovider`): the
adapter module with the V1/V2 replay, replay-review and database modules 557
passed under `-W error::RuntimeWarning`; its earlier probe modules 308 passed;
its new cross-context probes 200 passed; its mutation runner caught 28 of 28
mutants; its formatting counterfactual 704 passed; PAD5 and PAD4-R5 7 passed;
`git diff --check` clean. It did not run the full suite or recompute the V5
definition, whose bound inputs the diff leaves unchanged.

Next: RBT-003 Part B (below).

### RBT-003 Part B first step (live checks, 2026-11-05)

**Readiness, checked without printing any credential or value.** The five
`POSTGRES_*` variables and `COINGLASS_API_KEY` are exported and `PGOPTIONS` no
longer forces read-only. A read-only connection reached PostgreSQL 17.9 at
migration `0021_trade_accounting`; the repository's `0022` to `0025` change
only the `portfolio` and `research` schemas. The six raw tables the collectors
write (`funding_rates`, `open_interest`, `futures_basis`, `liquidations`,
`perp_volume`, `etf_flows`) match the code's definitions column for column and
hold no rows. The database role is a superuser. All six provider hosts answer
over TLS. The private repository `wlodzimierrr/backtest_evidence` (ruling 9) is
private and empty.

**Live checks.** One small in-window span per source through the reviewed
Part A adapters; the output was statuses, counts, labels, timestamps and
refusal codes, never a value, and nothing was written to disk or the
database. CoinGlass was not called (ruling 10).

| Source | Result |
| --- | --- |
| Binance USD-M funding (2020-02), `metrics` (2020-09-01, ruling 4's duplicate slots), `1h` klines (2020-01); COIN-M index klines (2020-09) | **Match.** 87 settlements, 24 snapshots, 744 and 720 klines, no gap. |
| Binance COIN-M listing and contract archives | **Differs from ruling 2's check** for all 22 contracts delivered inside the window; ruling 11 replaces the check. The listing pages and archive checksums match. |
| Kraken executions | **Match.** `before` is honoured (a 5-minute page returned only executions inside it); the `Liquidation` order-type label occurs live (2021-11-10); pages hold up to 1,000 executions. |
| Kraken hourly liquidation volume | **Differs in value type:** values are JSON strings of digits, not numbers; the parser change follows ruling 5. `to` is inclusive (24 points for `00:00` to `23:00`). **Unit (ruling 3):** both hours with liquidations on 2021-11-10 13:00-15:00 AGREE exactly with the execution totals, so the series is in USD contracts. |
| Coin Metrics `CapMrktCurUSD` (2020-01) | **Match.** 31 days, none missing. |
| CoinGlass ETF endpoints (documentation only) | `flow-history`: fields match Part A, no parameter. `history`: only `ticker`; its records carry `assets_date`, `btc_holdings`, `market_date`, `market_price`, `name`, `nav`, `net_assets`, `premium_discount`, `shares_outstanding` and `ticker`, not Part A's `net_assets_usd`: the parser change follows ruling 5 and is checked live after the projection's review. |

**Surfaced for Part B.**
- *Scale.* `PI_XBTUSD` executions run from 2021-05-27 at roughly 30,000 to
  60,000 a day, about 813 bytes each: about 40 GB in about 50,000 requests.
  The run must resume per day; no raw page is stored, only its digest.
- *Coverage.* Two 5-minute samples in later crash windows (2024-08-05 03:00
  and 2025-10-10 21:00) held 0 and 26 executions and no liquidation:
  `PI_XBTUSD` may be thin in 2024-2025. The completeness rule records any
  empty hour as `SOURCE_UNAVAILABLE`; the census will show the extent.
- *Incidents.* The incident list Part B re-reads is Tardis's public exchange
  metadata (`api.tardis.dev/v1/exchanges/cryptofacilities`), the source of
  RBT-002's recorded incident; it is metadata only.

Next: the Part B code (below), then the collection run.

### RBT-003 Part B Implementation Notes (code)

**Status:** `PART B CODE COMMITTED (2026-11-05)`; nothing collected or
persisted yet. This block is the implementer's record, not a closure: the
collection run, the dataset build and the independent review are
outstanding, and CoinGlass is not called before that review (ruling 10).

**Commits** (each a separate change, on top of the Part B start record
`7ab24be`):
- `3301b16`, ruling 5: Kraken's liquidation-volume values are read as JSON
  strings holding a non-negative decimal numeral, the live shape; a JSON
  number is refused. The published digits are kept, so ruling 3 and the hour
  evidence are unchanged.
- `d561cc7`, ruling 11: a contract delivered inside the window must have its
  last kline with non-zero volume close at delivery or one hour after it
  (`is_zero`, no arithmetic); klines opening at or after delivery are not
  returned, so no basis row can read one.
- `4f22106`, ruling 10: the new `backfill_projection` module and the CoinGlass
  adapter reworked around it (below); `1e195d6` adds the fund-identity tests a
  mutant run asked for.
- `4cf0993`: the new `backfill_transport` and `backfill_run` modules and their
  test module `test_research_backtest_backfill_run.py`.

The collectors, the raw schema, the RBT-001 and RBT-001A builders, every
owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.

**The projection (ruling 10).** `project_records` walks a response's JSON
bytes with a grammar check that converts no number and decodes no string
value. For each record of `data` it reads only the member names and the date
members (13-digit epoch milliseconds: `timestamp` for the flow history,
`assets_date` and `market_date` for a fund's history), keeps the record's
exact bytes when every date lies in the requested in-window days, and counts
the records it drops from the prohibited window, from unrequested in-window
days and from the holdout and reserve. Any malformed byte refuses the whole
response, and a refusal names a position or a member, never content. The
projected response (`code`, `msg` and the kept records) is the only thing the
parsers accept and the only CoinGlass body kept; the full response leaves its
digest and size. `DateBoundParameters` is gone: the URLs carry no date and
only the ticker, and days outside the window, a bad ticker or a repeated fund
refuse before any request. A fund's history follows the documented record
(`assets_date`, `btc_holdings`, `market_date`, `market_price`, `name`, `nav`,
`net_assets`, `premium_discount`, `shares_outstanding`, `ticker`): `net_assets`
is the AUM, every field is type-checked, the ticker must be the requested one
and both dates must be requested days. `read_etf_flows(funds=None)` reads
every ticker the projected flow history names: the policy's fund universe is
chosen per decision at replay, not at collection. The shapes stay UNVERIFIED
until one live response of each endpoint passes, after the review.

**The transport.** `backfill_transport.UrllibTransport` is the only backfill
module that opens a connection. It sends a `GET` only to the six Part B hosts
and refuses any other URL before connecting; a connection error, a timeout,
HTTP 429 or a 5xx is retried with a growing pause and a `Retry-After` capped
at two minutes; any other status, and the last attempt's, is returned for the
fetcher to refuse. Headers, the CoinGlass key among them, are never logged or
put in a message.

**The run.** `backfill_run` (`python -m
btc_predictor.research_backtest.backfill_run <sources>`) splits each source
into units over RBT-002's spans, from the source's depth or the window start
to 2025-12-31: funding, perpetual volume and open interest by month (open
interest from 2020-09-01), the basis, the market cap, the incident list and
CoinGlass as one read each, and Kraken by day from 2021-05-27. Each unit is
read through the reviewed adapters, its rows are persisted through the
unchanged collectors in monthly slices inside one transaction (one collector
call is one `INSERT`, and PostgreSQL caps one statement's parameters), and
its files go to the private repository (ruling 9) under
`research_backtest_v1/rbt003/<source>/<unit>/`: the value-free
`retrievals.json` (URL, instant, status, size and SHA-256 per response) and
`summary.json` (counts, gaps, exclusions, exposure), the evidence files (the
basis listing, the market-cap file, each Kraken day's hour evidence as
deterministic gzip, the CoinGlass projections), and `DONE.json`, written last,
binding every file by SHA-256. A unit whose `DONE.json` verifies is skipped,
so the run resumes; a unit read with `--no-persist` is read again by a
persisting run. The store must be a git work tree outside this repository.
Progress lines and refusals are value-free (every digit masked). The Kraken
days need the incident list first: Tardis's public exchange metadata, read for
instants only (never the free-text details) and clipped to the window.
CoinGlass runs only with `--allow-coinglass` and `COINGLASS_API_KEY`.

**Tests.** The adapter module has 267 tests (196 before Part B) and the new
run module 29. Changed expectations, each following a ruling:
- the Kraken `string-value` refusal case becomes `number-value`, and the
  series fixture spells values as strings (ruling 5's verified shape); seven
  malformed-string cases and five accepted spellings are added;
- the delivery contradiction test's second case moves from an `08:00` to a
  `09:00` kline with volume, since ruling 11 accepts the former; four
  accepted and five refused live-like archives and a context case are added;
- the CoinGlass date-bound test becomes a no-date-URL test; the flow cases
  `holdout` and `unrequested-day`, which ruling 10 turns from refusals into
  counted drops, move to the 45 projection tests (one a `json.loads` spy
  proving no dropped value is ever decoded); the fund fixture and template
  follow the documented record.
No other test or expectation changed. Mutants: 20 of the projection, the
adapters and the Kraken parser, 19 caught; the survivor (the fund ticker
check) is caught after five fund-identity tests, with the name and market-date
checks. 15 of the run and the transport, 14 caught; the survivor (the store
lying inside the public repository) is caught after a test that isolates it,
with its two variants.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-05).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 779 passed, 1 xfailed (the recorded
  frozen-owner xfail); the BTC-019 completion gate and the coverage review: 18
  passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `4cf0993`, alone:
  8,090 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; the only network reads
  were the first step's checks and one read of Tardis's exchange metadata.

**Metadata exposure, recorded.** Inspecting the Tardis incident list's shape
printed every reported incident's start and end, among them four in 2019
(the prohibited window) and one on 2026-06-23 (the holdout): times only, no
market value, the class RBT-002 recorded as metadata exposure. The run reads
the list for in-window instants only.

**Surfaced.**
- RBT-002's plan also re-requests Coinbase's 11 and Bitfinex's 16 missing
  hours through the existing OHLCV adapters, from two hosts the transport
  does not allow; it is not yet scheduled.
- The dataset build (a window-bounded database reader, the V1 and V2
  builders, the manifests in the private repository and a value-free index
  here) is the next code, after the collection.

Next: the collection run of every source but CoinGlass, then the independent
review of the Part B code (the projection before the first CoinGlass
request), then CoinGlass and the dataset build.

### RBT-003 Part B code review outcome

**Date:** 2026-11-05. **Review:** independent xHigh review of the Part B code,
run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a detached worktree at
`b6c4ef3`, over `7ab24be..b6c4ef3` (the code `3301b16`..`4cf0993` and its
documentation). Report-only: a workspace-write sandbox with network disabled,
no database, no `.env*` file, no read of the private evidence repository, and,
because the collection run was using `.venv312` at the same time, no PAD4 or
PAD5 suite and no test that tampers with installed packages; its worktree
stayed clean. **Result: FAIL**, with one P1, five P2 and two P3 findings, all
CONFIRMED with synthetic probes. Rulings 5 and 11 are met; rulings 9 and 10
are not met completely (B5, B2). The review asked no owner question.

**Findings.** Locations refer to `b6c4ef3`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| B1 / **P1** | `backfill_transport.py:80` | Only the requested URL is checked; the default `urllib` opener follows redirects, so a redirect's target is requested before any adapter check, whatever its host, scheme or period. | A fake handler redirected an allowed CoinGlass URL to another host and to plain HTTP, both carrying `CG-API-KEY`, and a February 2020 Binance archive to a January 2026 one: each second request was made. Refuse redirects, or validate each before following it. |
| B2 / **P2** | `backfill_coinglass.py:109` | The parsers check only that they were given a `ProjectedResponse` before `json.loads`. | `project_records` with `date_keys=("assets_date",)` kept a fund record whose `market_date` was in 2026, and `parse_fund_history` decoded its synthetic `market_price` before refusing the date. The production reader passes both keys. Verify the endpoint's projection contract before decoding. |
| B3 / **P2** | `backfill_run.py:469` | Persistence commits before the evidence files and `DONE.json` are written. After an interruption there, the unit is fetched again with a later `available_at`; `etf_flows`' key includes `available_at`, so insert-or-ignore inserts a second `FINAL_AS_RETRIEVED` revision. | An interruption probe produced two INSERTs with distinct keys for one fund, day and provider; V1 then refused with `DUPLICATE_RECORD_REFUSED`. The five derivative tables' keys exclude `available_at`, so their retry is idempotent. Keep the prepared unit and its retrieval instants before persisting, and resume that unit. |
| B4 / **P2** | `backfill_run.py:136` | `done()` verifies only the files its marker names: not the marker's version, source or unit, the required files, or whether its persistence state is consistent. | February's completed directory copied to March made March `SKIPPED`; an unpersisted marker edited to `persisted: {}` was skipped by a persisting run; wrong versions or sources and empty bindings were accepted. Validate identity, schema, required files and persistence consistency before skipping. |
| B5 / **P2** | `backfill_run.py:145` | The store's root is resolved once; a destination below it is not. | With a source directory symlinked into a synthetic public tree, `write()` put value-bearing evidence there. Keep every resolved destination inside the store. |
| B6 / **P2** | `backfill_coinglass.py:85` | The key check admits an internal newline; `http.client` then raises `ValueError` quoting the header value, which neither the transport nor the run handles, so a traceback can print the key. | The real header validator raised `Invalid header value b'synthetic-secret\ncontinued'` (no connection was opened). Refuse a header value HTTP does not allow, generically, before `urllib`. |
| B7 / **P3** | `backfill_projection.py:151` | `string_end` checks escapes and control bytes but accepts any byte at or above `0x80`. | Dropped strings holding `FF`, the overlong `C0 AF` or the truncated `E2 82` were accepted (no value was decoded), against the documented whole-response refusal of malformed bytes. Validate UTF-8 byte sequences without decoding. |
| B8 / **P3** | `backfill_run.py:343` | `run_unit` does not check a unit against its source's span. | A direct call for `2021-05-26` requested Kraken executions and the chart and returned `DONE`; scheduled runs stay bounded. Validate the unit before reading. |

The Implementation Notes overstate host confinement, unconditional
idempotence, completion verification and the refusal of malformed bytes, in
the ways above. Codex's mutation runner caught 15 of 18 mutants; the survivors
showed no test of the completion marker's identity and none of the individual
`nav` type check.

**Checks that passed.** Ruling 11: the last kline with volume must close at
delivery or one hour after it, other closes refuse, and no kline opening at or
after delivery is returned. Ruling 5: JSON numbers and malformed strings
refuse, and accepted decimal strings keep their exponent and trailing zeros
through the evidence. The projection's ordinary path: key order, whitespace,
duplicate and escaped names, nested dates, Unicode, number spellings and both
fund dates; no discarded sentinel reached decoded input, projected bytes or
exposure records. Each source's request and response guards (Binance funding,
open interest, perpetual volume, basis and listing; Kraken executions and
chart; Coin Metrics, its continuations included; CoinGlass's dateless URLs,
refused before the transport for a bad ticker or range); the incident list
keeps clipped in-window instants without the details. Part A: F1-F10 and
N1-N3 held under the adapted probes, and 192 caller-context combinations gave
identical evidence, digests, rows and connection parameters. The collectors,
the raw schema, the migrations, the builders and the owners are unchanged.
Codex's runs (`.venv312`, one process at a time): the adapter, run, V1/V2
replay, replay-review and database modules 657 passed; the four coverage
modules, the coverage review and the completion gate 132 passed, 1 xfailed
and 8 failed, because the worktree has no local data manifests (not this
change); its probes reproduced B1-B8. The full suite and the V5 digest were
not recomputed.

**Implementer's verification.** All eight findings were confirmed from the
code before the owner was asked. The derivative tables' keys
(`observation_time`, `exchange`, `symbol`, instrument or timeframe, side or
expiry, `provider`) were read from the database's catalog: B3 concerns
`etf_flows` only. For the collection already under way, a no-redirect request
for two archive URLs the run had fetched was answered `200` at the same URL,
and the adapters check every archive's checksum and that its contents lie in
the requested period.

**Owner decision (2026-11-05):** fix all eight, one commit each with its
tests, correct the Implementation Notes, validate, then re-review. The
collection of the incident list, Binance's funding, perpetual volume, open
interest and basis, and Coin Metrics' market cap, which started before the
review on `4cf0993`, runs to its end; its units stay recorded as collected by
`4cf0993`. Kraken's liquidations and CoinGlass wait for the re-review PASS.

### RBT-003 Part B review-fix (B1-B8)

**Status:** `REVIEW-FIX COMMITTED (2026-11-05)`; awaiting the independent
xHigh re-review. CoinGlass is not called and Kraken's liquidations are not
collected before its PASS.

**Distinct review-fix:** one commit per finding on top of the FAIL record
`f3e6119`, then one test commit. Only `backfill_transport`, `backfill_run`,
`backfill_projection`, `backfill_coinglass` and the two test modules change;
the collectors, the raw schema, the RBT-001 and RBT-001A builders, every
owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.
- `43ddb46` (B1): the default opener returns a `3xx` as the response
  (`RefuseRedirects`), which the fetcher refuses, and a response whose URL is
  not the requested one refuses before its body is read. No redirect is
  followed, so no request leaves the six hosts, `https` or the requested
  period.
- `704bd82` (B6): the CoinGlass key must be 1-256 visible ASCII characters;
  the transport checks every header name and value before `urllib` and
  refuses without quoting either; any other error from the opener leaves its
  type only (no text, no chained cause) and is not retried.
- `dbdfe33` (B7): every byte at or above `0x80` in a projected string must
  begin a well-formed UTF-8 sequence under RFC 3629's table (no overlong
  form, no surrogate, nothing above U+10FFFF), checked byte by byte and never
  decoded.
- `e9cfc75` (B2): `backfill_projection.verified_body` proves, before either
  parser decodes anything, that the bytes are exactly a projection on the
  endpoint's own date members (`timestamp`; `assets_date` and `market_date`)
  and the projection's days: the same members, every record kept on a
  second value-blind projection, byte-identical bytes, the same count, typed
  days and bytes.
- `e244ebf` (B8): `run_unit` refuses an unknown source and any unit its
  source does not schedule before the store or the transport is touched.
- `1573ee7` (B5): every directory from the store's root down, and every file
  it reads or writes, must be real, never a symbolic link; files are written
  through a fresh `O_NOFOLLOW` partial file; source, unit and file names are
  plain names. The store is consulted before any request.
- `5f1717c` (B4): a `DONE.json` verifies only with exactly its keys, this run
  version, its own source and unit, a UTC completion instant, non-negative
  integer counts, and `summary.json` and `retrievals.json` bound under plain
  names; the run also requires the source's evidence files and that the
  marker records the summary's rows persisted (`not_persisted`, or nothing
  for a source that persists nothing). A marker that exists but does not
  verify refuses the unit for reconciliation by hand, since the unit may
  already be persisted: it is never silently read again.
- `0187e09` (B3): a unit's files and `PREPARED.json` (binding them, and
  recording whether the run persists) are written before any row is
  persisted; `DONE.json` then binds the same files and replaces it. A unit a
  persisting run prepared is never read afresh: CoinGlass rebuilds its rows
  from the prepared projections, each of which must reproduce its exposure
  record (`backfill_coinglass.etf_flows_from_projections` shares the live
  read's row builder), and every other source reads again with the prepared
  retrieval instants replayed and must reproduce the prepared files byte for
  byte. The rows are then the prepared read's, so the unchanged collectors'
  insert-or-ignore adds nothing already committed. A no-persist run never
  completes a persisting run's unit, and a unit prepared without persistence
  is read afresh.
- `7a9de7d`: each of the six fund numbers is type-checked on its own (30
  cases), the gap the review's mutation runner found for `nav`.

**Implementation Notes corrected.** The Part B Implementation Notes above
said that the transport sends a `GET` "only to the six Part B hosts" (true
only since B1: redirects were followed), that a unit "whose `DONE.json`
verifies is skipped, so the run resumes" (before B4 a marker's identity and
persistence were not checked, and before B3 a CoinGlass unit interrupted
after its commit was read again with a later `available_at`; the run
module's docstring said such a unit "re-persists nothing new", true then for
the five derivative tables only) and that "any malformed byte refuses the
whole response" (before B7, malformed UTF-8 inside a string did not). They
stand as the record of `4cf0993`; this section and the modules' docstrings
are current.

**Tests.** The adapter module has 349 tests (267 before) and the run module
107 (29 before): B1 16, B2 2, B3 7, B4 16, B5 20, B6 20, B7 39, B8 10, the
fund numbers 30. Changed fixtures, each following B4: two store tests now
bind `summary.json` and `retrievals.json`, which every completed unit binds.
No other test or expectation changed. Mutants (`mutate.py`, one textual
change at a time against the finding's tests): B1 3 of 3, B6 4 of 4, B7 9 of
9, B2 6 of 6 after two cases were added for the two first survivors (a
forged count, re-framed bytes), B8 2 of 2, B5 6 of 6, B4 12 of 13, B3 10 of
10, the fund numbers 5 of 5. The B4 survivor removes the digest-format and
self-binding checks, which no real file can pass anyway (a digest must
equal the file's lower-case SHA-256): an equivalent mutant kept as an
explicit guard.

**Collection so far (2026-11-05, on `4cf0993`, before the review).** The
incident list (one in-window incident, as RBT-002 recorded), Binance funding
(72 months, 6,575 rows; the 2020-01-01 00:00 settlement excluded as pricing
2019), perpetual volume (72 months, 52,608 rows, no gap), open interest (64
months from 2020-09-01, 46,708 rows, 44 gap records), the basis (one unit,
96,730 rows from 2020-06-11, 192 gap records, two contracts unlisted in the
window; 593 requests, of which 148 contract-month archives answered `404`
and were read as absent months by Part A's reviewed listing proof) and Coin
Metrics' market cap (one request; no missing day). Each source's database
rows equal its units' summary rows (read-only count), every unit's marker
verifies under B4, and none is left prepared. The evidence (635 files,
4.5 MB) is committed to the private repository as `76496db` (ruling 9).
Every progress line and summary is value-free; no value was printed.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-05).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 939 passed, 1 xfailed; the BTC-019 completion gate and
  the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `7a9de7d`, alone:
  8,250 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; the only network reads
  were the collection run's and two no-redirect requests for Binance archive
  URLs the run had fetched.

Next: the independent xHigh re-review of `f3e6119..` this record; on PASS,
Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build.

### RBT-003 Part B re-review outcome

**Date:** 2026-11-06. **Review:** independent xHigh re-review of the Part B
review-fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a detached worktree at
`264f3fb` (recreated after a machine restart), over `b6c4ef3..264f3fb`.
Report-only: a workspace-write sandbox with network disabled, no database, no
`.env*` file, no read of the private evidence repository; its worktree stayed
clean. **Result: FAIL**, with two P2 findings, both CONFIRMED with synthetic
probes. B1, B2, B5, B6, B7, B8 and the `nav` test gap are FIXED; B3 and B4
are FIXED IN PART. Rulings 5, 9, 10 and 11 are met. The review asked no owner
question.

**Findings.** Locations refer to `264f3fb`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| BR1 / **P2** | `backfill_run.py:759` (the check at `:201`) | `PREPARED.json`'s `persisting` flag decides whether a prepared unit must be resumed from its prepared read, but only its type is verified: nothing the run trusts establishes its value, so a unit a persisting run may already have committed can be read afresh. | A synthetic ETF unit was interrupted after its commit and only `persisting` was changed from `true` to `false`, every bound file and digest unchanged. Against changed responses, a persisting run returned `DONE` after a fresh read whose rows carried another value and a later `available_at` (their keys differ, and V1 refused the two histories with `DUPLICATE_RECORD_REFUSED`); a `--no-persist` run returned `DONE` recording `not_persisted`. Bind the persistence decision to verified metadata, or refuse automatic replacement when it cannot be established. |
| BR2 / **P2** | `backfill_run.py:704` (CoinGlass's evidence at `:662`) | A completed CoinGlass unit must bind only `flow_history.projected.json`; the fund histories its summary's projection records describe are not required. | `history_IBIT.projected.json` was deleted with only its entry in `DONE.json`'s files, the summary, exposure records, retrieval log, counts and other digests unchanged: the marker verified and `run_unit` returned `SKIPPED`. Require the fund-history files the unit's projection records describe. |

The documentation's corrections of the earlier Implementation Notes are
accurate; its current B3 and B4 completion claims are too broad because of
these residuals.

**Checks that passed.** B1: fifteen redirect probes across five status codes
made only the original request, and a response whose URL differs refuses
before its body is read. B2: partial date proofs, forged counts and
unprojected bodies refused before a held-out sentinel was decoded, in the
rebuild too. B3 on an ordinary resume: all six persisting sources reproduced
their original `INSERT` parameters and `available_at`. B4: copied identities,
other versions, inconsistent counts and altered bound files refuse, and
markers in `4cf0993`'s format verify. B5: directory, file, marker and
partial-file symbolic links left every outside destination unchanged. B6:
invalid headers refuse before the opener, and four unexpected exception
classes gave tracebacks without the synthetic key. B7: the byte check agreed
with Python's strict UTF-8 decoder on 20,392 adversarial sequences. B8:
unscheduled and pre-depth units refuse before the store or the transport.
`nav`: removing its check failed five of the new tests. Each source's request
and response guards held, the resume paths included; no new holdout exposure.
Part A's F1-F10, N1-N3 and rulings 1-8 held, and 192 decimal-context
combinations gave identical evidence, digests, rows and `INSERT` parameters.
The collectors, the raw schema, the migrations, the builders and the owners
are unchanged, and no test was weakened beyond the two documented fixture
bindings. Codex's runs (`.venv312`, one process at a time): the focused
modules 939 passed, 1 xfailed; its independent probes 72, 192, 42 and 1
passed, and 3 failed, reproducing BR1 and BR2; its mutation runner caught 22
of 22 mutants. The full suite, the PAD suites and the V5 digest were not
rerun.

**Implementer's verification.** Both findings were confirmed from the code
before the owner was asked: `EvidenceStore.prepared` checks only that
`persisting` is a boolean, and `_read_or_resume` reads afresh when it is
`false`; CoinGlass's `Source` names only the flow projection as evidence,
while `coinglass_resume` needs every history its summary records. Neither
reaches the units collected on `4cf0993`: that run wrote no `PREPARED.json`
(B3 came later), and CoinGlass was not called.

**Owner decision (2026-11-06):** fix both, one commit each with its tests,
validate, then re-review. BR1: for a source that persists, a prepared unit
counts as possibly committed, whatever any flag says, so a persisting run
always resumes it from its prepared read and a `--no-persist` run refuses
it; the `persisting` flag is dropped, and a source that persists nothing is
read afresh. BR2: a completed CoinGlass unit must bind every projection file
its summary's projection records describe. Kraken's liquidations and
CoinGlass wait for the re-review PASS.

### RBT-003 Part B second review-fix (BR1, BR2)

**Status:** `REVIEW-FIX COMMITTED (2026-11-06)`; awaiting the independent
xHigh re-review. CoinGlass is not called and Kraken's liquidations are not
collected before its PASS.

**Distinct review-fix:** one commit per finding on top of the FAIL record
`56b819f`. Only `backfill_run` and its test module change; the adapters, the
projection, the transport, the collectors, the raw schema, the RBT-001 and
RBT-001A builders, every owner, configuration, the inventory, the spec,
`data/` and `research_artifacts/` are unchanged.
- `15f0d92` (BR1): for a source that persists, no marker can prove that a
  saved read was not committed, so a saved read is never replaced by a fresh
  one. `PREPARED.json` records no `persisting` flag (a marker carrying one no
  longer verifies); a persisting run resumes any prepared unit from its saved
  read, whichever run prepared it, and a `--no-persist` run refuses it. The
  same rule covers the two other ways a fresh read could replace a saved
  one: a persisting run resumes a unit completed with `not_persisted` from
  its saved read (`EvidenceStore.reopen` writes `PREPARED.json` over the same
  files before it drops `DONE.json`), so a completion marker edited to claim
  no persistence adds nothing new; and a unit holding files under no marker
  it resumes (a deleted marker, a partial first write) refuses for
  reconciliation by hand. Only an empty unit is read afresh. A source that
  persists nothing (the incident list, the market cap) is read afresh as
  before. Deleting a unit's directory stays the operator's reconciliation,
  after checking the database.
- `75a60f8` (BR2): a completed CoinGlass unit must bind every projection file
  its summary records, the flow and each fund history (`Source.described`;
  CoinGlass's `coinglass_evidence` shares `coinglass_resume`'s reading of the
  summary), and a summary without projection records refuses.

**Earlier record corrected.** The B3 entry of the review-fix above says that
"a unit prepared without persistence is read afresh"; since BR1 a persisting
run resumes it and a `--no-persist` run refuses it. That entry stands as the
record of `0187e09`; this section and the run module's docstrings are
current.

**Tests.** The run module has 121 tests (107 before): BR1 10, BR2 4. Two B3
expectations change with the owner's BR1 decision: the ETF interruption test
now checks that `PREPARED.json` makes no persistence claim (it checked that
`persisting` was `true`), and the test of a unit a `--no-persist` run
prepared now expects a persisting run to resume it with the prepared
instants and a `--no-persist` run to refuse it (it expected a fresh read).
No other test or expectation changed. Mutants (`mutate.py`, one textual
change at a time against the run module's tests): BR1 11 of 11, BR2 6 of 6.

**Store check.** Names and markers only: each of the private store's 211
units holds a `DONE.json`, and none a `PREPARED.json` or a partial file, so
every collected unit is still skipped.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-06).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 953 passed, 1 xfailed; the BTC-019 completion gate and
  the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `75a60f8`, alone:
  8,264 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `56b819f..` this record; on PASS,
Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build.

### RBT-003 Part B second re-review outcome

**Date:** 2026-11-06. **Review:** independent xHigh second re-review of the
Part B second review-fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a detached worktree at
`7400832`, over `264f3fb..7400832`. Report-only: a workspace-write sandbox
with network disabled, no database, no `.env*` file, no read of the private
evidence repository; its worktree stayed clean. **Result: FAIL**, with three
P2 findings, all CONFIRMED with synthetic probes. BR1 and BR2 are FIXED IN
PART (their reproducers now refuse); B3 and B4 as a whole are FIXED IN PART.
Rulings 5, 9, 10 and 11 are met in the collection, resume and reopen paths.
The review asked no owner question.

**Findings.** Locations refer to `7400832`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| BR3 / **P2** | `backfill_run.py:840` (`has_files` at `:192`) | An existing empty unit directory is treated as a new unit, so deleting a unit's markers and files while keeping its directory removes every obstacle to a fresh read. | A synthetic ETF unit was interrupted after its commit and its files deleted, its directory kept. Against changed responses, a persisting run returned `DONE` after a fresh read whose row carried another value, a later retrieval instant and another key (V1 refused the two histories with `DUPLICATE_RECORD_REFUSED`); a `--no-persist` run read afresh and completed with `not_persisted`. An existing empty directory must require reconciliation, or another lifecycle record must tell it from a new unit. |
| BR4 / **P2** | `backfill_run.py:610` (`coinglass_evidence`, used by `_complete` at `:744`) | Completion checks the projection file names a CoinGlass summary records, not that each file matches its exposure record's `projected_sha256` and `projected_size`. | IBIT's projection was replaced with GBTC's bytes and only its digest in `DONE.json`'s files updated, the summary unchanged: `run_unit` returned `SKIPPED`, while `_projection_from_exposure` rejects the same bytes. Swapped fund files, a replaced flow projection and a contradictory exposure digest also skipped. No transport call or value decoding was observed. Verify each projection against its exposure record, by digest and size, without decoding. |
| BR5 / **P2** | `backfill_run.py:750` | `_complete` trusts a `DONE.json` recording `not_persisted` for a `--no-persist` run before it looks at `PREPARED.json`. | A unit completed without persistence was reopened by a persisting run interrupted after its commit, leaving `PREPARED.json`; the old `DONE.json` bytes were restored beside it. A `--no-persist` run returned `SKIPPED`, trusting `not_persisted`, where the owner's BR1 rule requires a refusal. The new reopen test expects `SKIPPED` for that two-marker state. Resolve `PREPARED.json` before a no-persist completion claim is accepted. |

**Checks that passed.** The removed `persisting` flag cannot bypass
verification; prepared and reopened units of all six persisting sources
reproduced their saved reads, rows, values and `available_at`. Deleting a
fund history with its marker binding now refuses. Identity, counts, required
files and digests still refuse when altered, and markers in `4cf0993`'s
format verify. Each source's request and response guards held through the
ordinary, prepared-resume and reopen paths; CoinGlass's rebuild still needs
the complete date proof before any value is decoded; no new holdout
exposure. Part A's F1-F10, N1-N3 and rulings 1-8, B1, B2, B5-B8 and the
`nav` tests held, with 192 decimal-context combinations giving identical
evidence, digests, rows and `INSERT` parameters. The adapters, transport,
projection, collectors, raw schema, migrations, builders and owners are
unchanged. Only the two documented B3 expectations changed; the new tests
are not vacuous but miss BR3 and BR4 and encode BR5's state as `SKIPPED`.
Codex's runs (`.venv312`, one process at a time): the focused modules 953
passed, 1 xfailed; its independent regressions 306 passed; a lifecycle
matrix 46 passed and 2 failed (an interruption before a unit's first file
leaves an empty directory that is read afresh); the reproducers and new
edges 3 passed and 7 failed (BR3-BR5); reopen probes 8 passed; impact
probes 12 passed; its mutation runner caught 15 of 15 mutants. The full
suite, the PAD suites, the V5 digest and the private-store check were not
rerun.

**Implementer's verification.** All three were confirmed from the code before
the owner was asked: `has_files` is false for an existing empty directory, so
`_read_or_resume` reads afresh; `_complete` checks the names `coinglass_evidence`
returns, while only `coinglass_resume` compares a projection with its exposure
record; and `_complete` returns `ctx.connect is None` for a `not_persisted`
completion without looking for `PREPARED.json`. None reaches the units
collected on `4cf0993`: the private store holds no empty directory and no
`PREPARED.json`, and CoinGlass was not called.

**Owner decision (2026-11-06):** fix all three, one commit each with its
tests, validate, then re-review. BR3: for a source that persists, an
existing unit directory holding no marker the run resumes refuses, empty or
not; only a unit without a directory is read afresh, and an interruption
before a unit's first file leaves an empty directory the operator deletes
(nothing was persisted). BR4: a completed CoinGlass unit's every recorded
projection must match its exposure record's digest and size, checked
without decoding a value. BR5: a `not_persisted` completion is trusted only
when no `PREPARED.json` is present; with one, a `--no-persist` run refuses
and a persisting run resumes the prepared read, so the BR1 reopen test's
expectation for that state changes from `SKIPPED` to `REFUSED`. Kraken's
liquidations and CoinGlass wait for the re-review PASS.

### RBT-003 Part B third review-fix (BR3, BR4, BR5)

**Status:** `REVIEW-FIX COMMITTED (2026-11-06)`; awaiting the independent
xHigh re-review. CoinGlass is not called and Kraken's liquidations are not
collected before its PASS.

**Distinct review-fix:** one commit per finding on top of the FAIL record
`eade370`. Only `backfill_run` and its test module change; the adapters, the
projection, the transport, the collectors, the raw schema, the RBT-001 and
RBT-001A builders, every owner, configuration, the inventory, the spec,
`data/` and `research_artifacts/` are unchanged.
- `25e4bcd` (BR3): for a source that persists, a unit whose directory
  exists under no marker the run resumes refuses for reconciliation by hand,
  even when the directory is empty, so emptying a unit while keeping its
  directory no longer leads to a fresh read. Only a unit without a directory
  is read afresh. An interruption before a unit's first file leaves an empty
  directory with nothing persisted, which the operator removes. A source
  that persists nothing is read afresh as before.
  `EvidenceStore.has_files` becomes `has_directory`.
- `9875a7c` (BR4): a completed CoinGlass unit is skipped only when every
  projection file its summary records matches the SHA-256 and the integer
  size its exposure record gives it. A substituted, swapped or replaced
  projection, or a summary recording another digest or size, refuses.
  Completion compares digests and sizes only: it decodes no projection and
  makes no request. `Source.described` returns each recorded file with its
  digest and size.
- `9644715` (BR5): a `DONE.json` recording `not_persisted` lets a
  `--no-persist` run skip the unit only when no `PREPARED.json`, verifying
  or not, lies beside it. Otherwise the prepared-unit rule applies: a
  `--no-persist` run refuses, a persisting run resumes the prepared read, and
  a `PREPARED.json` that does not verify refuses for reconciliation.

**Earlier record corrected.** The second review-fix above says that "only an
empty unit is read afresh"; since BR3 only a unit without a directory is.
That entry stands as the record of `15f0d92`; this section and the run
module's docstrings are current.

**Tests.** The run module has 137 tests (121 before): BR3 4, BR4 9, BR5 3.
Three expectations of the second review-fix's own tests change with the
owner's decisions. The BR1 empty-unit test, renamed for BR3, now expects an
emptied directory to refuse and a removed one to be read afresh (it expected
an empty directory to be read afresh). The BR1 reopen test now expects a
`--no-persist` run to refuse the two-marker state an interruption inside
`reopen` leaves (it expected a skip) and checks that state after a committed
resume. The BR2 helper reads `coinglass_evidence`'s new return shape and
asserts the same names. No other test or expectation changed. Codex's
reproducers from the second re-review now pass: the edge probes 10 of 10
and the lifecycle matrix 48 of 48. Mutants (`mutate.py`, one textual change
at a time against the run module's tests): BR3 6 of 6, BR4 7 of 7, BR5 5 of
5. One BR4 mutant, which dropped the integer check on a recorded size,
first survived; a float-size case was added and catches it.

**Store check.** Names and markers only: the private store holds 211 unit
directories, each with a `DONE.json` recording rows persisted. None holds a
`PREPARED.json` or a partial file, none is empty, none records
`not_persisted`, and none is CoinGlass's, so every collected unit is still
skipped.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-06).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 969 passed, 1 xfailed; the BTC-019 completion gate and
  the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `9644715`, alone:
  8,280 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `eade370..` this record; on PASS,
Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build.

### RBT-003 Part B third re-review outcome

**Date:** 2026-11-07. **Review:** independent xHigh third re-review of the
Part B third review-fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a detached worktree at
`fa1770b`, over `7400832..fa1770b`. Report-only: a workspace-write sandbox
with network disabled, no database, no `.env*` file, no read of the private
evidence repository; its worktree stayed clean. **Result: FAIL**, with one P2
finding, CONFIRMED with synthetic probes. BR3, BR4 and BR5 are FIXED; BR1
and B3 as a whole are FIXED; BR2 and B4 as a whole are FIXED IN PART.
Rulings 5, 9, 10 and 11 are met. The review asked no owner question.

**Finding.** Locations refer to `fa1770b`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| BR6 / **P2** | `backfill_run.py:600` (`coinglass_evidence` at `:620`, `_complete` at `:758`) | Completion checks the files a CoinGlass summary's projection records declare, with their digests and sizes, but not that the declaration is complete and consistent: the first record need not be the flow history's, a fund may be declared twice or not at all, and a record's projection proof (kept count, date keys, days, rule) is not checked. The rebuild refuses the same units. | IBIT's exposure record, history file and `DONE.json` binding were removed and the summary's digest updated, `tickers_seen`, the counts and the other records unchanged: `run_unit` returned `SKIPPED`, while rebuilding the same files refused with `PROVIDER_REQUEST_MISMATCH`. The first record's URL changed to a fund or foreign URL, a duplicated fund record, and a falsified kept count, date-key proof, day range or rule also skipped (a falsified kept count refuses the rebuild with `PROVIDER_RESPONSE_REFUSED`). Check the flow endpoint, a unique fund-history census and each record's value-blind projection proof; no market value need be decoded. |

**Checks that passed.** An emptied directory refuses in both persistence
modes and an interruption before a unit's first file requires
reconciliation; only a missing directory permits a fresh read. Substituted
projections, other digests or sizes and non-integer sizes refuse without
value decoding, transport or database access, and six valid completion
shapes are accepted. A restored `not_persisted` `DONE.json` beside a
`PREPARED.json` refuses a `--no-persist` run and a persisting run resumes
the prepared read. All six persisting sources passed ordinary resume and
reopen checks, and the 48-case lifecycle matrix passed; a write-boundary
sweep (34 file failpoints, directory creation, partial marker replacement)
found no fresh-read path for a persisting source with an existing unit
directory. Each source's request and response guards held, the resume and
reopen paths included; no new holdout exposure. Part A's F1-F10, N1-N3 and
rulings 1-8, B1, B2, B5-B8 and the `nav` tests held. The adapters,
transport, projection, collectors, raw schema, migrations, builders and
owners are unchanged; only the three authorized expectations changed, and
the new tests omit BR6's cases. Codex's runs (`.venv312`, one process at a
time): the focused modules 969 passed, 1 xfailed; its retained edge,
lifecycle and impact probes 60 passed; its independent regressions 314
passed; valid completion shapes 6 passed; the write-boundary sweep 26
passed; BR6's declaration-consistency regressions 8 failed; its
completion and rebuild comparison 2 passed; an in-memory guard closing BR6
kept the 137 run tests and the six valid shapes passing (151 passed); its
mutation runner caught 19 of 19 mutants. The full suite, the PAD suites, the
V5 digest and the private-store check were not rerun.

**Implementer's verification.** Confirmed from the code before the owner was
asked: `_projection_file` names the first record the flow history's file
whatever its URL, and completion checks no record's URL, fund uniqueness or
census, or projection proof; `_projection_from_exposure`, `verified_body`
and `etf_flows_from_projections` do so only when a unit is rebuilt. It does
not reach the units collected on `4cf0993`: CoinGlass was not called.

**Owner decision (2026-11-07):** fix it value-blind, one commit with its
tests, validate, then re-review. Completion checks each CoinGlass record
without decoding a value: each projection is rebuilt from its exposure
record (rule, URL, days, date keys, counts, digest and size reproduced) and
its bytes re-projected exactly to its kept count and days (`verified_body`);
the first record is the flow history's URL and the others are one fund
history per ticker, in order, exactly the summary's `tickers_seen`. Kraken's
liquidations and CoinGlass wait for the re-review PASS.

### RBT-003 Part B fourth review-fix (BR6)

**Status:** `REVIEW-FIX COMMITTED (2026-11-07)`; awaiting the independent
xHigh re-review. CoinGlass is not called and Kraken's liquidations are not
collected before its PASS.

**Distinct review-fix:** one commit on top of the FAIL record `b90c454`. Only
`backfill_run` and its test module change; the adapters, the projection, the
transport, the collectors, the raw schema, the RBT-001 and RBT-001A
builders, every owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.
- `e866317` (BR6): completion checks a CoinGlass unit's projection records
  as its rebuild does, without decoding a value (`coinglass_proven`, wired
  as `Source.proven`). The records must declare the flow history first and
  then one fund history per ticker of the summary's `tickers_seen` (sorted,
  each once), in order. Each record must be reproduced by the projection
  rebuilt from its file over the unit's own days (2024-01-11 to
  2025-12-31), with integer counts and sizes and text fields, so `3.0` or
  `true` is no count. Each file must re-project, value-blind, to exactly that
  projection on its endpoint's date members (`verified_body`). An omitted or
  duplicated fund, another first URL, a falsified kept count, date-key
  proof, day span or rule, or a broken census refuses instead of skipping.
  The rebuild (`coinglass_resume`) runs the same proof before it decodes
  anything, so the stricter record check applies to a resume too.

**Tests.** The run module has 164 tests (137 before), all BR6: 22 edits of
a completed unit's records or census (Codex's eight reproducers and
fourteen more; the commit message says eleven, written before the last
three were added), each refused in both persistence modes with the value
parsers patched to fail; four of them on a prepared unit's resume; and a
control that every unit the code completes is proven without decoding.
Removing the proof from completion turns all 22 refusals into skips. One
helper changes: the BR4 tests' no-decoding guard now patches the value
parsers (`parse_flow_history`, `parse_fund_history`) and the rebuild entry
instead of `_projection_from_exposure`, which reads only metadata and which
completion now calls. No other test or expectation changed. Mutants
(`mutate.py`, one textual change at a time against the run module's tests):
BR6 13 of 13; two first survived (the unit's-days check and the flow
history's proof), and cases isolating each were added. BR4's seven mutants,
re-run against the new guard, 7 of 7. Codex's saved probes: its eight BR6
reproducers, six valid completion shapes and the 26-case write-boundary
sweep pass, as do its earlier edge (10), lifecycle (48), regression (72),
reopen (8), boundary-resume (42) and decimal-context (192) probes; its two
completion-and-rebuild probes now fail, as they assert the old skip.

**Store check.** Names and markers only, unchanged: 211 unit directories,
each with a `DONE.json` recording rows persisted; no `PREPARED.json`,
partial file, empty directory, `not_persisted` claim or CoinGlass unit.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-07).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 996 passed, 1 xfailed; the BTC-019 completion gate and
  the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `e866317`, alone:
  8,307 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `b90c454..` this record; on PASS,
Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build.

### RBT-003 Part B fourth re-review outcome

**Date:** 2026-11-07. **Review:** independent xHigh fourth re-review of the
Part B fourth review-fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a new detached worktree at
`995fc03`, over `fa1770b..995fc03`, with its saved probes from the third
re-review restored. Report-only: a workspace-write sandbox with network
disabled, no database, no `.env*` file, no read of the private evidence
repository; its worktree stayed clean. **Result: FAIL**, with one P2
finding, CONFIRMED with synthetic probes. BR1, BR3, BR4 and BR5 are FIXED;
BR6 and BR2 are FIXED IN PART; B3 and B4 as a whole are FIXED IN PART.
Rulings 5, 9, 10 and 11 are met. The review asked no owner question.

**Finding.** Locations refer to `995fc03`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| BR7 / **P2** | `backfill_run.py:622` (`coinglass_proven`; the record's instant at `:681`; `_resume` at `:870`) | A CoinGlass unit's projection records are not checked against the unit's own `retrievals.json`. The rebuild takes each record's retrieval instant, which sets the rows' `available_at`, part of an ETF row's key, while `_resume` copies the saved retrieval log unchanged, so the comparison with the saved files cannot see a difference. A prepared retry can therefore insert ETF rows under keys the first attempt did not. | A synthetic ETF unit interrupted after its commit; IBIT's exposure `retrieved_at` moved from `10:00:03` to `11:00:03` and only the summary's digest in `PREPARED.json` updated; every projection and `retrievals.json` byte-identical. The resume returned `DONE` with no request, and two rows took another `available_at`: the retry named five distinct raw keys where the first attempt named three, and V1 refused that history with `DUPLICATE_RECORD_REFUSED`. The same edit of a completed unit skips, and of a `not_persisted` unit reopens to `DONE`; completion also accepts another response digest or size, retrieval URL or status, a missing retrieval record, and a fund removed from the records and census while its retrieval stays logged. Before completion or a rebuild decodes anything, compare the records one-to-one, in order, with the successful retrieval records (URL, instant, response digest and size, and their number); no value need be decoded. |

**Checks that passed.** All eight of the third re-review's BR6 reproducers
now refuse; the endpoint, census, day, count and projection proofs held over
170 malformed variants in both completed modes and a prepared one, and seven
valid units of other fund sets and day coverage were accepted. Value-parser
guards and a separate JSON-decoding spy found the completion checks
value-blind, with no transport or database access. Prepared units follow the
owner's rule in both persistence modes; only a missing directory permits a
fresh read; projection digests and integer sizes are checked; a restored
`not_persisted` completion cannot override a `PREPARED.json`. Ordinary
resume passed for all six persisting sources. Each source's request and
response guards held, the resume and reopen paths included; no new market
value or holdout exposure. Part A's F1-F10, N1-N3 and rulings 1-8, B1, B2,
B5-B8, the `nav` tests and the 192 decimal-context combinations held. The
adapters, transport, projection, persistence wrappers, collectors, raw
schema, migrations, builders and owners are unchanged. An AST comparison
found no existing test function or decorator changed or removed; only the
`no_decoding` guard changed, which the review found appropriate, and the
new tests are not vacuous. The documentation describes the implemented
checks accurately; its completeness claims need qualifying by BR7. Codex's
runs (`.venv312`, one process at a time): the focused modules 996 passed,
1 xfailed; its retained regression, lifecycle, boundary, context and
completion probes 414 passed; its new proof probes 12 passed; its adapted
completion and rebuild probes with the BTC-019 completion gate and coverage
review 12 passed, 8 failed, each failure a `FileNotFoundError` for the
collection manifests under `data/`, absent from its worktree (those tests
and inputs are unchanged); its retrieval-consistency matrix 9 failed, and
its impact probe passed, confirming BR7; its mutation runner caught 24 of
24 mutants; an in-memory comparison of the records with the retrieval log
kept 595 tests passing and passed all nine cases. The full suite, the PAD
suites, the V5 digest and the private-store check were not rerun.

**Implementer's verification.** Confirmed from the code before the owner was
asked: for CoinGlass `_resume` binds the saved `retrievals.json` to the
rebuilt files unchanged, `coinglass_proven` reads no retrieval record, and
`etf_flows_from_projections` sets each row's `available_at` from the records'
instants. In every unit the code writes, `retrievals.json` holds exactly one
record per projection, in the same order, each with status 200 and the
projection's URL, instant, response digest and size, since a CoinGlass read
refuses any other status. Codex's matrix, run against `995fc03`, failed all
nine cases; its prepared-after-commit case resumed to `DONE` without a
request and with other insert parameters. It does not reach the units
collected on `4cf0993`: CoinGlass was not called.

**Owner decision (2026-11-07):** fix it value-blind, one commit with its
tests, validate, then re-review. Before completion or a rebuild decodes
anything, each CoinGlass projection record is matched one-to-one, in order,
with the unit's `retrievals.json` records: the same number of records, each
retrieval with status 200 and the record's URL, retrieval instant, response
digest and size. Kraken's liquidations and CoinGlass wait for the re-review
PASS.

### RBT-003 Part B fifth review-fix (BR7)

**Status:** `REVIEW-FIX COMMITTED (2026-11-07)`; awaiting the independent
xHigh re-review. CoinGlass is not called and Kraken's liquidations are not
collected before its PASS.

**Distinct review-fix:** one commit on top of the FAIL record `3aaca84`. Only
`backfill_run` and its test module change; the adapters, the projection, the
transport, the collectors, the raw schema, the RBT-001 and RBT-001A
builders, every owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.
- `197c8c5` (BR7): `coinglass_proven` also requires the unit's
  `retrievals.json` to be exactly the log a read of its proven projections
  writes: one retrieval with status 200 per projection record, in order,
  with the record's URL, retrieval instant, response digest and size,
  compared byte for byte with that log's canonical form. Completion and the
  rebuild both run it before any value is decoded, so a prepared or
  `not_persisted` unit whose records disagree with its log is refused
  instead of resumed with other retrieval instants (and so other
  `available_at` keys), and a completed one is refused instead of skipped.
  Every unit the code writes satisfies it: a CoinGlass read refuses any
  status but 200, and each projection carries its response's URL, instant,
  digest and size.

**Tests.** The run module has 207 tests (164 before), all BR7. Thirteen
edits of a completed unit's records or retrieval log, covering the review's
cases (a record's instant, response digest or size; a fund removed from the
records and census with its retrieval still logged; the log's instant, URL
or status; a retrieval missing, an extra refused attempt, the log
reordered, a size as a float, an extra field), each refused in both
persistence modes with the value parsers patched to fail and without a
request or a connection; five of them on a unit prepared after its commit;
a `not_persisted` unit neither reopened nor skipped; each of BR6's 22 edits
refused by BR6's own checks with the log forged to match the edited
records; and units of one and of four other funds, on other days, resumed
with the committed keys and then skipped without decoding. No existing test
or helper changed. Mutants (`mutate.py`, one textual change at a time
against the run module's tests): BR7 11 of 11 (the check removed, reduced
to a count, each of its five fields ignored, compared parsed instead of
byte for byte, its order ignored, the proof skipped on completion or on
resume); BR6's 13, re-run with the log check in place, 13 of 13, each also
caught by BR6's original tests alone, so the log check masks none; BR4's
seven, 7 of 7. Codex's saved probes: its nine retrieval-consistency cases
now pass, as do its retained regression, lifecycle, boundary, context,
completion and proof probes (426); its impact probe now fails, as it
asserts the old resume.

**Store check.** Names and markers only, unchanged: 211 unit directories,
each with a `DONE.json` recording rows persisted; no `PREPARED.json`,
partial file, empty directory, `not_persisted` claim or CoinGlass unit.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-07).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,039 passed, 1 xfailed; the BTC-019 completion gate and
  the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `197c8c5`, alone:
  8,350 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `3aaca84..` this record; on PASS,
Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build.

### RBT-003 Part B fifth re-review outcome

**Date:** 2026-11-07. **Review:** independent xHigh fifth re-review of the
Part B fifth review-fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a new detached worktree at
`2c03121`, over `995fc03..2c03121`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository or the sealed sample; its
worktree stayed clean. **Result: PASS**, with no new finding. BR1 to BR7
are FIXED; B3 and B4 as a whole are FIXED. Rulings 5, 9, 10 and 11 are met.
The review asked no owner question. **Part B's code review is closed.**

**Checks.** All nine BR7 reproducers refuse: a completed, prepared or
`not_persisted` CoinGlass unit can no longer carry projection records that
contradict its retrieval log. The proof builds the expected log with the
collection's own `Retrieval.as_record()` and canonical serializer, so the
byte comparison enforces order, number, status, fields and canonical form;
it accepted every valid history tried: other funds, sparse coverage, missing
net assets, resumes after a commit, reopened units, and transport retries
after 429, 503 and timeouts (six attempts, three logged retrievals). 140 log
edits in three lifecycle states and both persistence modes (840 cases)
refused without a traceback, value decoding, request or connection, and 42
valid resume and reopen paths passed. The former duplicate-key reproducer
now refuses before any collector call. Each source's request and response
guards held, the resume and reopen paths included; no request or admitted
observation outside the window was found. Part A's F1-F10, N1-N3 and rulings
1-8, B1, B2, B5-B8, the `nav` tests and the 192 decimal-context
combinations held. The adapters, transport, projection, persistence
wrappers, collectors, raw schema, migrations, builders and owners are
unchanged; an AST comparison found no existing test, decorator or helper
changed or removed, and the new tests fail when the log check or any of its
fields is removed. Codex's runs (`.venv312`, one process at a time): the
focused modules 1,039 passed, 1 xfailed; its retained probes, the nine BR7
reproducers included, 437 passed; its new log and lifecycle probes 47
passed; its retry and former duplicate-key probes 4 passed; 21 distinct
mutations in 23 runs, all caught. The full suite, the PAD suites, the V5
digest, the completion gate and coverage review (their `data/` inputs are
absent from its worktree) and the private-store check were not rerun.

**Fifth review-fix record corrected.** The record above says BR6's 13
mutants, re-run with the log check in place, are each also caught by BR6's
original tests alone, so the log check masks none; `197c8c5`'s commit
message says the same. That run selected tests by `br6`, which also matched
the new matched-log test. The re-review found that removing the census's
sorted-and-unique clause passes the 27 original BR6 tests. Re-run against
those 27 tests only, 10 of the 13 mutants are caught: the log check masks
three, the text-type check and the census's sorted-and-unique clause
(removed whole, or only its uniqueness). The matched-log tests catch each of
them, so the run module's tests catch 13 of 13, as recorded. That entry
stands as the record of `197c8c5`; this section is current.

Next: Kraken's liquidations, then CoinGlass (`--allow-coinglass`), then the
dataset build; RBT-003 stays IN PROGRESS until they are done and the ticket
closes.

### RBT-003 Part B Kraken liquidation collection stop and owner ruling 12

**Date:** 2026-11-08. The Kraken liquidation collection ran on `4d6b14d`,
started from the owner's shell (the database and provider credentials come
from the environment and are never printed). A one-day trial on 2026-11-07
and the run on 2026-11-08 collected 49 days, 2021-05-27 to 2021-07-14, each
with its database rows matching its summary, and the run stopped at its first
refused unit, 2021-07-15: `CONTINUATION_CHAIN_REFUSED`, the log is not in
ascending order. The refused unit wrote nothing: no unit directory, no row.

**Diagnosis (metadata only).** One re-read of that day's execution pages,
with the same URLs and allowlisted transport, keeping and persisting
nothing and printing no market value, found the chain whole: it ended
normally, with no repeated continuation token or uid, every execution inside
the day, and each element's timestamp equal to its execution's. Exactly one
execution is listed before the one above it, by 1 ms, inside one page,
between two ordinary (`IoC`) trades; no liquidation is involved. The hourly
liquidation records do not depend on the order.

**Owner decisions (2026-11-08, asked; the recommended option each time).**
- Ruling 12 (above, with the owner rulings): count such steps, do not
  refuse; the other chain checks stay. Its code change is a separate commit
  with its own tests, validation and independent re-review; no day is
  collected with it before the re-review PASS.
- Meanwhile the collection continues past refused units on the reviewed
  code (`--keep-going`, the run's reviewed option). A refused day writes
  nothing and is collected after the re-review PASS.

Next: ruling 12's code change, its validation and its independent re-review,
while the remaining days are collected; then the refused days, CoinGlass
(`--allow-coinglass`) and the dataset build.

### RBT-003 Part B ruling 12 code change

**Status:** `COMMITTED (2026-11-08)`; awaiting the independent xHigh
re-review. No refused day is collected with it before its PASS.

**One commit** on top of the ruling's record `8aed7af`. Only
`backfill_kraken`, `backfill_run` and their two test modules change; the
other adapters, the projection, the transport, the persistence, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`
are unchanged.
- `fd702fe`: `read_execution_day` keeps a day's log in the provider's order
  and counts each execution listed before the one above it
  (`ExecutionDay.out_of_order_steps`; equal instants are not a step)
  instead of refusing the day with `CONTINUATION_CHAIN_REFUSED`. Its other
  checks are unchanged: every execution inside the day, a uid once, a
  continuation token never repeated, the page cap and the window guards.
  `read_liquidations` sums the days' counts
  (`KrakenLiquidationCollection.out_of_order_steps`) and the liquidation
  unit's summary records it after `disagreeing_hours`. Each hour still
  selects its own executions, its sums are exact and its liquidation uids
  sorted, so the rows and hour records do not depend on the listing order.

**Tests.** The adapter module has 356 tests (349 before), the run module
210 (207). One case changes: `test_a_broken_execution_chain_is_refused`
loses its `descending` case, the behaviour the ruling reverses; its other
cases stay. Added: a day with steps back inside a page, across pages, by an
hour and by 1 ms is read whole in the provider's order with three steps
counted, equal instants not counted; a day in order counts none; a day out
of order still refuses an execution before or past the day, a repeated uid
and a repeated continuation token, each by its own message and at the page
that breaks the chain; an execution out of order in the holdout is still an
exposure; the rows, the hours' status and corroboration, and the hour
evidence apart from its response digests are equal for one day's executions
listed in order, reversed, and reversed across pages; a liquidation unit
listed out of order is collected with a summary count of 1 (0 in order) and
then skipped, and one interrupted after its commit is read again with its
instants and completes with identical files. Mutants (`mutants_r12.py`, one
textual change at a time against both modules, with an unchanged control
passing): 11 of 11 (refusing again, counting equal instants, resetting the
count per page, comparing with the day's first execution, sorting the log,
not summing the days, dropping the summary key or fixing it at 0, admitting
an execution before the day, a repeated uid, a repeated token). The last
mutant showed a gap in the earlier tests: with the repeated-token check
removed, the page cap refused the same day with the same code, so the
broken-chain test still passed. The new chain test asserts each refusal's
message and number of reads.

**The collection.** The owner's `--keep-going` run started from the owner's
shell on `4d6b14d`, before the repository moved to `fd702fe`. Its modules
load at start, so it runs the reviewed code (the units it completes carry
no `out_of_order_steps`) and passes refused days, writing nothing for them.
A unit it completes is skipped under `fd702fe`: completion checks the
marker against the saved files and the summary's rows, and re-derives no
summary. A unit it prepared but did not complete would not resume under
`fd702fe`: the re-read adds the summary key, differs from the saved read
and refuses for reconciliation by hand. So any restart before the PASS
runs `4d6b14d`'s code, and no prepared unit may remain when `fd702fe`
collects the refused days after the re-review PASS.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-08).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules, in the fix's checkout at `fd702fe`:
  1,049 passed, 1 xfailed; the BTC-019 completion gate and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `fd702fe`, while the collection ran:
  8,360 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `4d6b14d..` this record; on PASS,
the refused days, then CoinGlass (`--allow-coinglass`), then the dataset
build.

### RBT-003 Part B ruling 12 re-review outcome

**Date:** 2026-11-08. **Review:** independent xHigh re-review of ruling 12's
code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in a new detached worktree at
`e3b69b5`, over `4d6b14d..e3b69b5`, with its saved probes restored.
Report-only: a workspace-write sandbox with network disabled, no database,
no `.env*` file, no read of the private evidence repository, the owner's
running collection untouched; its worktree stayed clean. **Result: FAIL**,
with one P2 finding, CONFIRMED with synthetic probes. The counter, the
provider order, the chain and window guards and the cross-version units
follow the ruling; Part B's earlier fixes and rulings 5, 9, 10 and 11 still
hold. The review asked no owner question.

**Finding.** Locations refer to `e3b69b5`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| R12-1 / **P2** | `backfill_kraken.py:372` (`hour_record`) | An hour's liquidation quantities are added one at a time in the 80-digit context that traps `Inexact`, so a partial sum can need more digits than the final total: the same quantities are accepted in one listing order and refused in another. The arithmetic predates ruling 12, but the ruling relies on the hour records not depending on the order. | Three same-side quantities `1`, `1E-80` and `1 - 1E-80`, each admitted by the execution parser, exact total `2`: listed `[1E-80, 1 - 1E-80, 1]` the hour holds `2` and agrees with the series; listed `[1, 1E-80, 1 - 1E-80]` the day refuses with `RESPONSE_SHAPE_REFUSED` ("the liquidation quantities do not sum exactly"). Over the six orders of an otherwise fully observed day, four refuse and two pass. Sum each side's quantities exactly, independently of their order, before the bounded representation, with permutation regressions. |

**Checks that passed.** Every adjacent step back is counted, across empty
pages too, and equal instants are not; the provider's order is kept; the
counts are summed over the days and reach the unit's summary. An execution
before or past the day, a repeated uid, a repeated token, the page cap and
an unknown liquidation side still refuse, each with its own reason and read
count, and the window and holdout guards keep their priority; no new
exposure. Ordinary shuffled days give identical rows and hour evidence apart
from the response digests (incidents, corroboration, sorted uids,
availability). With `4d6b14d`'s implementation run in memory, its persisted
completed units skip under `fd702fe` without a request, persistence or file
change; its prepared units refuse on the saved-read comparison before any
persistence, their files unchanged; its `not_persisted` units skip under
`--no-persist`, and a persisting run's reopen refuses on the same summary
difference. B1-B8, BR1-BR7, rulings 5, 9, 10 and 11, Part A's F1-F10, N1-N3
and rulings 1-8 held. Only the authorized test case changed (`descending`
removed; its body and every other test and helper identical); the new tests
pin each refusal's message and read count. The documents describe the
change accurately and carry no collected value or population count; their
order-independence claims need qualifying by R12-1. Codex's runs
(`.venv312`, one process at a time, no full suite, PAD, ETF proof or
BTC-019 module): the focused modules 1,049 passed, 1 xfailed; its retained
probes 488 passed; its ruling-12, order, guard and compatibility probes 83
passed; its 20 in-memory mutants all caught; its precision probes failed as
above; an exact-accumulation counterfactual passed 842 regression cases and
its seven precision cases.

**Noted, not a finding.** Structural checks cannot prove a provider's log
exhaustive: a chain restarted with fresh uids passes with its step back
counted, and a shortened final response was accepted by both versions. A
replay with the same uids refuses, and a synthetic replay that changes the
totals disagrees with the independent chart; the review does not treat
this as a defect against the ruling's explicit allowance.

**Implementer's verification.** Confirmed from the code and with plain
Python `decimal` before the owner was asked: four of the six orders refuse,
two give `2`. Only `hour_record`'s loop is order-dependent: the stored-record
check and the rows each apply one operation to fixed values. No collected
day is affected: a day accepted on `4d6b14d` summed with no inexact step, so
its sums are exact, and the evidence spells quantities by value, so an
exact sum gives the same bytes. The owner's run had then refused no day
for its sums; every refusal so far is a day listed out of order.

**Owner decision (2026-11-08):** fix it, one commit with its tests,
validate, then re-review. Each side's quantities are summed exactly, at a
precision computed from the quantities and never from their order, so that
no partial sum rounds; a set whose exact sum would need more digits than a
fixed cap refuses instead of using that much memory; the 80-digit exact
check then applies once to each side's total. Acceptance then depends only
on the set of quantities. The collection continues past refused days on
`4d6b14d`'s code; the refused days wait for the re-review PASS.

### RBT-003 Part B ruling 12 review-fix (R12-1)

**Status:** `REVIEW-FIX COMMITTED (2026-11-08)`; awaiting the independent
xHigh re-review. No refused day is collected before its PASS.

**Distinct review-fix:** one commit on top of the FAIL record `724b488`.
Only `backfill_kraken` and its adapter test module change; `backfill_run`,
the other adapters, the projection, the transport, the persistence, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`
are unchanged.
- `029057e` (R12-1): `hour_record` first finds every liquidation's side, in
  uid order, so an unknown side refuses before any sum and names the same
  liquidation in every order. It then sums each side with `exact_sum`, at a
  precision equal to the span from the lowest non-zero digit among the
  side's quantities to the largest one's leading place plus the digits of
  their count, with no exponent limit. Every partial sum of positive values
  is a multiple of that lowest digit and at most the total, so none rounds;
  the span is taken from the values, never from their order. A span above
  `EXACT_SUM_MAX_DIGITS` (10,000) refuses (`RESPONSE_SHAPE_REFUSED`) instead
  of using that much memory. The 80-digit exact context then applies once
  to each side's sum and to the hour's total, as before, and any trapped
  signal refuses. Acceptance and the hour's record therefore depend only on
  the hour's set of executions. An hour accepted before summed with no
  inexact step, so its sums are exact and, the evidence spelling quantities
  by value, its record, digests and rows are unchanged (unless its
  quantities spanned more than 10,000 digits). The change newly accepts an
  hour whose partial sums needed more than 80 digits in the listing order
  while each side's total fits them. An hour with both an unknown side and
  a side too wide to sum now refuses for the side in every order.

**Tests.** The adapter module has 374 tests (356 before), the run module
210 (unchanged); no existing test or helper changed. The 18 new tests:
every listing order (all of them for up to four liquidations, two for
twelve) of quantities whose carries cancel a last digit (`1`, `1E-80`,
`1 - 1E-80`, the review's case), of a value wider than 80 digits whose
total fits, of carries into new leading digits (twelve `9`s) and of a value
spelled with 20,000 trailing zeros gives the same rows, the same hours'
status and corroboration, and the same hour evidence apart from its
response digests, agreeing with the series; sums wider than 80 digits (81
and 162 digits, and 81 over three values) and a sum past the largest
exponent refuse in every order, and so does a side wider than 80 digits
when the hour's total would fit; the span cap admits a span of exactly its
size and refuses one more digit, in both orders; `exact_sum` equals the
exact `Fraction` total in every order under a 3-digit caller context that
traps `Inexact`, below and above the 80-digit context's exponent range too,
gives 0 for no value and nothing past the cap; an unknown side refuses
before any sum and names the same liquidation in every order. Mutants
(`mutants_r121.py`, one textual change at a time against both modules, with
an unchanged control passing): 12 of 12 (the pre-fix sum, the precision
fixed at 80, no per-side 80-digit check, no cap, the cap off by one,
trailing zeros counted in the span, the count's digits dropped or fixed at
1, the 80-digit context's exponent limits, sides checked in listing order,
the sums outside the refusal guard, an empty side not zero). Ruling 12's 11
mutants, re-run on the fix: 11 of 11. The review's seven precision probes:
7 passed.

**The collection.** The `--keep-going` run on `4d6b14d`'s code ran to its
end on 2026-11-08: every day it refused was listed out of order, none
refused for its sums, and no unit is left prepared. The refused days wait
for the re-review PASS and are then collected with the fix.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-08).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,067 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `029057e`, while the collection ran:
  8,378 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `e3b69b5..` this record; on PASS,
the refused days, then CoinGlass (`--allow-coinglass`), then the dataset
build.

### RBT-003 Part B ruling 12 second re-review outcome

**Date:** 2026-11-08. **Review:** independent xHigh second re-review of
ruling 12's code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`863ef06`, over `e3b69b5..863ef06`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: FAIL**, with two P2 findings, both
CONFIRMED with synthetic probes and both older than ruling 12 (each
reproduces on `e3b69b5`'s code too). **R12-1 is FIXED:** the precision
bound is sound for positive quantities, every partial sum fits it in any
order, the cap applies before the summing context is built, and each side
then meets its own 80-digit check. Ruling 12, Part B's earlier fixes and
rulings 5, 9, 10 and 11 still hold. The review asked no owner question.

**Findings.** Locations refer to `863ef06`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| R12-2 / **P2** | `backfill_kraken.py:347` (`corroborates`) | Ruling 3's comparison rounds the hour's total to the published value's places in a fixed 80-digit context, while the series parser admits a value spelled with any number of places. A total that agrees under ruling 3 raises an uncaught `decimal.InvalidOperation` instead; the exception leaves `run_unit` before anything is prepared or persisted. | A fully observed synthetic day with liquidation quantity `1` and the series publishing `1.` followed by 80 zeros raises; the 79-place control agrees. Give the comparison the precision the published value needs, keeping ruling 3's half-even rounding. |
| R12-3 / **P2** | `backfill_kraken.py:618` (`_stored_quantity`, calling `replay_inputs.canonical_decimal`) | A quantity the execution parser admits, such as `1E+4300`, sums exactly and is written to the hour evidence as a 4,301-digit numeral; reading the new evidence back converts that coefficient with `int`, past Python's default 4,300-digit limit, and raises an uncaught `ValueError` before anything is prepared or persisted. | A fully observed synthetic day with that quantity and a matching series value raises; the `1E+4299` control reads back. Refuse an unsupported quantity at the adapter, without changing the frozen replay owner. |

**Implementer-found, the same kind (R12-4).** While preparing the fix:
`parse_liquidation_volume` (`backfill_kraken.py:312`) builds a published
value with `Decimal` outside any guard, so a value the numeral pattern
admits but `decimal` cannot hold (an exponent above about 10^18, such as
`1e+1000000000000000000`) raises an uncaught `decimal.InvalidOperation`
instead of refusing the day. Reproduced with a synthetic response; it also
predates ruling 12.

**Checks that passed.** The seven original precision probes, the six
complete-day permutations among them; exact totals against an independent
fraction oracle over 100 datasets in five orders each; hostile precision,
exponent, rounding, trap and `capitals` contexts; both sides, incidents and
empty sides; the cap before the summing context and at its boundary;
exponent extremes and subnormal values; up to 100,000 trailing zeros;
12,000 liquidations in one hour. Hours accepted before keep their record,
digests and rows; `4d6b14d`'s completed units skip unchanged and its
prepared units refuse before persistence; units from ruling 12's code
before the fix resume or reopen with their saved bytes and availability.
The execution and series request and response window and holdout guards:
no regression. No existing test or helper changed (an AST comparison); the
new tests are meaningful, and the record matches the fix. Codex's runs
(`.venv312`, one process at a time, no full suite, PAD, ETF proof or
BTC-019 module): the focused modules 1,067 passed, 1 xfailed; its retained
probes 488 passed; its precision, ruling-12 and adversarial probes 268
passed; its 14 summation mutants and 20 ruling-12 mutants all caught; its
two regression expectations for R12-2 and R12-3 failed as above.

**Implementer's verification.** Both reproduced with plain synthetic calls
before the owner was asked: a published `1` with 80 zero places raises
(79 places agree), and `1E+4300`'s stored spelling fails to read back
(`1E+4299`'s reads back). No collected day comes near either: over the
completed units, no stored per-side quantity falls outside the liquidation
table's `NUMERIC(38,18)` (at most 20 integer and 18 fractional digits) and
no published value has more than 30 digits or an exponent beyond 30 either
way (counted from the private evidence; no value printed). Each exception
leaves before anything is prepared or persisted, and the owner's run ended
without one.

**Owner decisions (2026-11-08):** fix both, one commit with its tests,
validate, then re-review. R12-2: the comparison never runs out of digits.
When the published value's places reach the total's lowest digit or below,
nothing rounds and the exact values are compared; otherwise the total is
rounded half-even at a precision computed from the values. Wherever the
earlier comparison returned, it returns the same answer. R12-3: an hour
refuses when a side's quantity or notional does not fit the liquidation
table's `NUMERIC(38,18)`, the rule V2 applies to these rows; the stored
spellings then stay short, so the evidence always reads back, and the
database never rounds or rejects a row. The owner added R12-4 to the same
review-fix: the series parser refuses such a value instead of raising. The
refused days wait for the re-review PASS.

### RBT-003 Part B ruling 12 second review-fix (R12-2 to R12-5)

**Status:** `REVIEW-FIX COMMITTED (2026-11-08)`; awaiting the independent
xHigh re-review. No refused day is collected before its PASS.

**Distinct review-fix:** one commit on top of the FAIL record `49ca348`.
Only `backfill_kraken` and its adapter test module change; `backfill_run`,
the other adapters, the projection, the transport, the persistence, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`
are unchanged.
- `7808213` (R12-2): `corroborates` keeps ruling 3 and never runs out of
  digits. When the published value's last place is at or below the total's
  lowest non-zero digit, rounding to it changes nothing, so the exact values
  are compared. Otherwise the rounded total has at most one digit more than
  the total has above that place; it is rounded half-even at that precision
  (at least one digit, at most 80 for a total the hour admits), with
  `decimal`'s widest exponent limits, never a fixed context. Wherever the
  earlier 80-digit comparison answered, the answer is the same; it now also
  answers where that one raised (a published value with more places than 80
  digits allow, or an exponent past its context's limits). The evidence
  parser re-derives corroboration with the same function.
- `7808213` (R12-3): `fits_raw_numeric` holds a non-negative value to the
  liquidation table's `NUMERIC(38,18)` (below 10^20, no digit past the 18th
  place) by exact comparisons only, the rule V2's builder applies to these
  rows. `hour_record` refuses (`RESPONSE_SHAPE_REFUSED`) an hour whose long
  or short quantity, or its notional, does not fit, after the exact-sum
  checks; only each side's exact sum must fit, not each liquidation. A value
  that fits is spelled in at most 39 characters, so the evidence always
  reads back, and no row the database would round or reject is stored. The
  evidence parser holds each stored quantity to the same rule before
  checking its spelling, so a stored numeral too long for `int` refuses
  instead of raising.
- `7808213` (R12-4): `parse_liquidation_volume` converts a published numeral
  in the exact context, so a value whose exponent `decimal` cannot hold
  refuses its day ("has an exponent no decimal can hold") whatever the
  caller's traps; the window guard and the hour check keep their priority.
- `7808213` (R12-5, implementer-found while the fix was first validated;
  the owner added it to this review-fix on 2026-11-08): the JSON reader
  shared by the execution pages, the series and the hour evidence read
  every JSON number with `Decimal` and caught only `ValueError`, so a
  number whose exponent `decimal` cannot hold (`1e+1000000000000000000`)
  anywhere in those bodies raised `InvalidOperation`. It now reads in the
  exact context and refuses (`RESPONSE_SHAPE_REFUSED`, "holds a number no
  decimal can hold") whatever the caller's traps. CoinGlass's reader has the
  same pattern; by the owner's decision it is recorded here as a known
  limitation outside this Kraken review: such a number in a CoinGlass
  response raises before anything is stored, stopping the run.
- The fixed 80-digit comparison context, now unused, is removed.

Every hour accepted before the fix whose side quantities fit the column is
accepted with the same record, digests and rows; an hour whose side
quantity or notional does not fit now refuses. Over the completed units no
stored quantity falls outside the column (counted; no value printed), and
completed units are skipped, not re-read.

**Tests.** The adapter module has 417 tests (374 before), the run module
210 (unchanged); no existing test or helper changed. The 43 new tests: the
comparison equals ruling 3 in exact fractions, and the earlier comparison
wherever it answered, over 13 totals, 16 published exponents from -200 to
200 and the agreeing value with its neighbours, under a 3-digit caller
context with narrow exponent limits that traps `Inexact`; it answers at the
extremes (20,000 places, the largest exponent, an exponent below the
smallest a context may set, a carry into a new digit); a complete day
publishing `1` with 79, 80, 200 and 20,000 zero places agrees, one unit in
its last place disagrees, and the evidence reads back; on either side, the
column's largest and smallest values and two values past 18 places whose
sum is not are accepted with their rows, while 10^20, a sum reaching it, a
19th place, `1E+4300` (the review's case) and `1E+999999` refuse; a notional
past the column refuses when the quantity fits (a larger contract size
patched in); a stored quantity of 4,301 or 100,001 digits, 10^20, or 19 or
5,001 places refuses as not fitting; the rule equals V2's on 14 values;
published exponents `decimal` cannot hold refuse with the same message
whether or not the caller traps `InvalidOperation`, and the largest it holds
compares and reads back; a JSON number `decimal` cannot hold, in an
execution page, the series or the hour evidence, refuses with the same
message whether or not the caller traps it. Mutants (`mutants_r122.py`, one
textual change at a time against both modules, with an unchanged control
passing): 17 of 17
(the pre-fix comparison, no exact comparison, the precision one short of a
carry, no precision floor, the default exponent limits, half-up rounding,
no column check, the notional unchecked, the limit admitted, the 18th place
refused, a 19th admitted, no check on a stored quantity, the spelling
checked first, no guard on a published numeral, the caller's context for
it, the JSON reader not catching `InvalidOperation`, the JSON reader in the
caller's context).
R12-1's 12 mutants (anchored past the new notional line) and ruling 12's 11,
re-run on the fix: 12 of 12 and 11 of 11. The review's two regression
expectations for R12-2 and R12-3 and its seven precision probes pass; its
probes that characterised the old exceptions now fail as intended.

**The collection.** Unchanged: the run on `4d6b14d` ended, no unit is
prepared, and the refused days wait for the PASS.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-08).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,110 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `7808213`:
  8,421 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `863ef06..` this record; on PASS,
the refused days, then CoinGlass (`--allow-coinglass`), then the dataset
build.

### RBT-003 Part B ruling 12 third re-review outcome

**Date:** 2026-11-08. **Review:** independent xHigh third re-review of
ruling 12's code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`490c1f0`, over `863ef06..490c1f0`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: FAIL**, with two P2 findings, both
CONFIRMED with synthetic, digest-matching evidence files and both in the
hour evidence parser; neither admits a wrong row or exposes the holdout.
**R12-2 is FIXED** (corroboration equals an independent exact-fraction
oracle and the earlier answers, at zero values, carries, extreme exponents,
100,000 published places and hostile caller contexts). **R12-3 is FIXED IN
PART:** every emitted quantity and notional meets V2's `NUMERIC(38,18)`
rule and an oversized stored value refuses before its spelling is checked,
but a long spelling of a value that fits still raises (R12-6). **R12-4 is
FIXED**, and **R12-5 is FIXED** for the exponent it named; a separate
encoding failure remains (R12-7). R12-1, ruling 12, Part B's earlier fixes
(B1-B8, BR1-BR7) and rulings 5, 9, 10 and 11 still hold; `4d6b14d`'s
completed units skip unchanged, and the ordinary resume of all six
persisting sources passes. The review asked no owner question.

**Findings.** Locations refer to `490c1f0`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| R12-6 / **P2** | `backfill_kraken.py:682` (`_stored_quantity`, calling `replay_inputs.canonical_decimal`) | The column check bounds a stored quantity's value but not its spelling: a non-canonical spelling of a value that fits reaches `canonical_decimal`, whose `int` conversion of a coefficient past Python's 4,300-digit limit raises an uncaught `ValueError` instead of refusing the malformed evidence. | A digest-matching evidence file storing `long_quantity` as `1.` followed by 4,300 zeros (exactly `1`, so it fits) raises; six spellings and caller trap settings reproduce it. Refuse such a spelling with `BackfillRefused`. |
| R12-7 / **P2** | `backfill_kraken.py:610` (`parse_liquidation_hour_evidence`) | The parser re-encodes the decoded payload canonically before checking any field's type. A JSON fraction decodes as a `Decimal`, which the canonical writer cannot write (`TypeError`), and `NaN` or an infinity is refused by it (`ValueError`); either escapes instead of refusing the malformed evidence. | A digest-matching file with `"execution_count":1.0` raises `TypeError: Object of type Decimal is not JSON serializable`; `1.0` and `1e1` in four fields, and the non-finite cases, give 16 such cases. Refuse them. |

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,110
passed, 1 xfailed; its two regression expectations for R12-2 and R12-3
passed; its independent probes 307 passed (exact-fraction corroboration
over 100 totals and fifteen exponents with hostile caller contexts,
parity with the earlier comparison wherever it answered, decimal's
exponent extremes, the column rule against V2's over eighty datasets and
its boundaries, the numeric-conversion refusals of all three JSON readers,
the window and hour guards' priority, published spellings through 100,000
places, 240 old-against-new comparisons of in-column records, digests and
rows); its retained Part B probes 488 passed and numeric probes 157
passed; its new parser probes 22 failed (6 for R12-6, 16 for R12-7), and
with in-memory diagnostic guards the same cases refuse and the adapter and
run modules still pass (649 passed). Its 17 mutants of the fix and 20
ruling-12 mutants were all caught, and 13 of its 14 summation mutants: the
survivor drops the explicit per-side 80-digit `plus`, which the exact
notional multiplication still enforces, so the same hour refuses with the
same message. The execution and series request and response window and
holdout guards: no regression. No existing test or helper changed (an AST
comparison); the record matches the fix, except that its claim that a long
stored numeral refuses needs R12-6's qualification; the CoinGlass
limitation is recorded.

**Implementer's verification.** Both reproduced with plain synthetic calls
before the owner was asked: a stored `1.` with 4,300 zero places raises
`ValueError`, and a digest-matching body holding `1.0`, `1e1`, `NaN`,
`Infinity` or `-Infinity` raises `TypeError` or `ValueError`. Two more of
the same kind were found while checking the readers' other conversions:
- **R12-8:** the JSON reader shared by the execution pages, the series and
  the hour evidence (`backfill_kraken.py:151`) catches neither the decoder's
  `RecursionError`, so a body nested 100,000 levels deep raises instead of
  refusing in all three readers. Every other JSON reader in the package
  (CoinGlass's and Coin Metrics' responses, the run's own marker and
  summary files, the builders' inputs) has the same pattern.
- **R12-9:** an execution quantity (`_quantity`, `backfill_kraken.py:163`)
  or a stored published value (`backfill_kraken.py:717`) written as text
  with an exponent `decimal` cannot hold always refuses with the same
  code, but its message depends on the caller's `InvalidOperation` trap
  ("is not a decimal" or "must be positive"; for the published value, two
  different messages), as the series parser's did before R12-4. The run
  uses the default context, so in practice the message never varies.

No collected day is affected: the evidence files are written by the code
itself, every stored quantity in its canonical spelling (over the completed
units none falls outside the column, counted; no value printed), and
completed units are skipped, not re-read. Each exception would leave before
anything is prepared or persisted.

**Owner decisions (2026-11-08):** fix all four in one review-fix with its
tests and mutants, validate, then re-review. R12-6: a stored quantity
spelled in more than 39 characters, the longest canonical spelling of a
value the column holds, refuses as non-canonical before the spelling is
converted. R12-7: the canonical-file check refuses when the canonical writer
cannot write the decoded body (a JSON fraction, `NaN`, an infinity, or
nesting too deep for it). R12-8: the JSON reader refuses a body nested too
deeply to decode; the same pattern in every other JSON reader is recorded as
a known limitation outside this Kraken review (at worst such a body stops
that run with an exception instead of a refusal). R12-9: the execution
quantity and the stored published value convert in the exact context, like
the series parser, so the same text gets the same refusal under any caller
context. The refused days wait for the re-review PASS.

### RBT-003 Part B ruling 12 third review-fix (R12-6 to R12-9)

**Status:** `REVIEW-FIX COMMITTED (2026-11-08)`; awaiting the independent
xHigh re-review. No refused day is collected before its PASS.

**Distinct review-fix:** one commit on top of the FAIL record `fda90ed`.
Only `backfill_kraken` and its adapter test module change; `backfill_run`,
the other adapters, the projection, the transport, the persistence, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`
are unchanged.
- `c5fa819` (R12-6): `RAW_NUMERIC_SPELLING_MAX` is 39, the length of the
  longest canonical spelling of a value the column holds (20 integer
  digits, the point and 18 places). After the column check, the evidence
  parser refuses a stored quantity spelled in more characters as
  non-canonical before `canonical_decimal` converts its digits, so a
  stored spelling of any length either reads back or refuses. This
  completes R12-3's read-back guarantee, which the second review-fix's
  record stated without that qualification. The collection path is
  unchanged: it stores each side in its canonical spelling, including a
  quantity published with any number of trailing zeros.
- `c5fa819` (R12-7): the hour evidence's canonical-file check
  (`_is_canonical`) fails, and the file refuses as "not the canonical file
  with exactly its keys", when the canonical writer cannot write the
  decoded body: a JSON number with a fraction or an exponent (decoded as a
  `Decimal`, `TypeError`), `NaN` or an infinity (`ValueError`), or nesting
  too deep for the writer (`RecursionError`). Only the writer's call is
  guarded; a body it writes is compared byte for byte as before.
- `c5fa819` (R12-8, implementer-found): the JSON reader shared by the
  execution pages, the series and the hour evidence refuses a body nested
  deeper than the decoder reads ("is nested too deeply to read") instead of
  raising `RecursionError`. By the owner's decision, the same pattern in
  every other JSON reader in the package is recorded as a known limitation
  outside this Kraken review: such a body stops that run with an exception
  instead of a refusal.
- `c5fa819` (R12-9, implementer-found): an execution quantity and a stored
  published value are read with `_numeral_value`, in the exact context, as
  the series parser has read a published value since R12-4. The same text
  gets the same refusal under any caller context. Under the default
  context, which the run uses, every message is unchanged. A stored hour's
  corroboration now compares against that value instead of converting the
  published text a second time.

Every hour accepted before is accepted with the same record, digests and
rows, and every evidence file read back before still reads back.
Completed units are skipped, not re-read.

**Tests.** The adapter module has 484 tests (417 before), the run module
210 (unchanged); no existing test or helper changed. The 67 new tests:
- **R12-6:** the limit is the length of the column's largest value's
  canonical spelling, and the canonical spellings of fitting values are
  within it. On either side, under the default and a hostile caller
  context, five long spellings of values that fit refuse as
  non-canonical: the review's `1.` with 4,300 zeros, `1.` with 100,000
  zeros, the column's smallest and largest values each followed by 4,300
  zeros, and `1.` with 5,000 leading and 5,000 trailing zeros. A day whose
  liquidation quantity is spelled with 4,300 or 100,000 trailing zeros
  stores `1`, agrees and reads back.
- **R12-7:** `1.0`, `1e1`, `0.5`, `NaN`, `Infinity` and `-Infinity` in
  five evidence fields (a declared constant, the execution count, a stored
  quantity, the published value and the incident flag) refuse the file. A
  canonical writer that runs out of depth refuses it too.
- **R12-8:** in each of the three readers, a body nested one level past
  the decoder's deepest, 100,000 or 1,000,000 levels deep refuses as
  nested too deeply, and every depth within ten levels of the decoder's
  deepest refuses.
- **R12-9:** an execution quantity or a stored published value that
  `decimal` cannot read refuses with the same message whether or not the
  caller traps `InvalidOperation`.

On `7808213`, 60 of the 67 fail. The seven that pass are the two parity
tests for long-spelled quantities and the five R12-9 cases in which the
caller traps. Mutants (`mutants_r123.py`, one textual change at a time
against both modules, with an unchanged control passing): 12 of 12 (no
length check; the limit one short, one long or far too long; the spelling
converted before its length is checked; the direct canonical comparison;
the canonical check not catching `TypeError`, `ValueError` or
`RecursionError`; the JSON reader not catching `RecursionError`; the
execution quantity or the stored published value read in the caller's
context). The second review-fix's 17 mutants, R12-1's 12 and ruling 12's
11, re-run on the fix: 17 of 17, 12 of 12 and 11 of 11. The review's 22 parser probes (all
failing on `7808213`), its two R12-2/R12-3 regression expectations and its
307 independent probes pass.

**The collection.** Unchanged: the run on `4d6b14d` ended, no unit is
prepared, and the refused days wait for the PASS.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-08).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,177 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `c5fa819`:
  8,488 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `490c1f0..` this record; on PASS,
the refused days, then CoinGlass (`--allow-coinglass`), then the dataset
build.

### RBT-003 Part B ruling 12 fourth re-review outcome

**Date:** 2026-11-09. **Review:** independent xHigh fourth re-review of
ruling 12's code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`cbee5d4`, over `490c1f0..cbee5d4`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: PASS WITH NON-BLOCKING FINDINGS**,
with one P3. **R12-6, R12-7 and R12-8 are FIXED**; R12-6 closes R12-3.
**R12-9 is FIXED IN PART** (R12-10 below). R12-1 to R12-5, ruling 12,
Part B's earlier fixes (B1-B8, BR1-BR7) and rulings 5, 9, 10 and 11 still
hold; accepted records, digests and rows keep their parity; `4d6b14d`'s
completed units skip unchanged, and the ordinary resume of all six
persisting sources passes. The review asked no owner question. **Ruling
12's code review is closed:** the refused days may be collected with
`c5fa819`'s code.

**Finding.** Locations refer to `cbee5d4`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer |
| --- | --- | --- | --- |
| R12-10 / **P3** | `backfill_kraken.py:176` (`_quantity`) and `:532` (`published_spelling`) | Two refusal messages print a decimal with `repr`, whose exponent letter follows the caller's `capitals`. R12-9's same-message guarantee therefore holds across trap settings but not across that flag. The refusal, its code, the accepted data and every default-context message are unchanged; only the diagnostic text differs, and the run uses the default context. | An execution quantity `-1e20` (a JSON number) refuses with `Decimal('-1e+20') must be positive` under `capitals=0` and with `Decimal('-1E+20')` under `capitals=1`; a stored published value of `-1E+20` varies the same way. |

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,177
passed, 1 xfailed; its original parser probes with new nesting probes 292
passed (270 depth and shape combinations across the three readers); its
independent spelling, numeric, compatibility and precision probes 447
passed; its retained Part B probes 488 passed; its additional numeric,
resume and parity regressions 163 passed. Its five message-invariance
probes failed, confirming R12-10; with an in-memory formatting control they
pass, together with the adapter and run modules (699 passed). 64 mutants
were caught; one retained mutation is equivalent, because the exact notional
multiplication still enforces the per-side check it removes. Against
`7808213`, the 67 new tests gave 60 failures and seven passes, as recorded.
The execution and series request and response window and holdout guards
showed no regression. No existing test, helper or decorator changed (an AST
comparison). The record matches the fix, except that its claim of the same
message under any caller context needs R12-10's qualification; the known
limitation in the other JSON readers stays outside this review.

**Implementer's verification.** R12-10 was reproduced with direct
synthetic calls before the owner was asked: under `capitals=0` and
`capitals=1` both values refuse with `RESPONSE_SHAPE_REFUSED`, and the
messages differ only in the exponent letter.

**Owner decision (2026-11-09):** R12-10 is accepted as a non-blocking
finding and not fixed, because it changes only diagnostic spelling, and
only under a non-default caller context. The refused days are now
collected with the reviewed code `c5fa819` (`kraken-liquidations
--keep-going`, which skips the completed units). CoinGlass
(`--allow-coinglass`) and the dataset build follow.

### RBT-003 Part B collection of the refused Kraken days and owner ruling 13

**Date:** 2026-11-09. The owner collected the refused days on `c5fa819`'s
code (the main checkout at `f65426d`), started from the owner's shell (the
database and provider credentials come from the environment and are never
printed). A first attempt lost `--keep-going` when the command was pasted
across lines: it ran in the foreground, completed four days and was
interrupted by hand while reading the fifth, which wrote nothing (no unit
directory, no prepared marker, no row). The run with `--keep-going` then
completed every remaining day but four, which it refused with
`DUPLICATE_PROVIDER_RECORD` (an execution uid appears twice): 2022-12-15,
2023-02-14, 2023-02-20 and 2023-03-17. No unit is left prepared and the
run's error log is empty. Of the window's 1,680 days (2021-05-27 to
2025-12-31), 1,676 are complete. A read-only database check, comparing
counts only, found every completed unit's rows equal to its summary and to
its completion marker, one ingestion instant per unit, no row on a day
without a completed unit, and no unit directory or row for the four refused
days.

**Diagnosis (metadata only).** One re-read of each refused day's execution
pages and series, with the same URLs and allowlisted transport, keeping
and persisting nothing and printing no uid or market value, found each
chain whole (it ended normally, with no repeated continuation token) and,
on each day, one contiguous block of executions listed twice, back to back
inside one page. Every repeated element is identical to its first listing,
with the same timestamp; none is a liquidation (each is an ordinary `Limit`
or `IoC` trade). Replaying the same pages through the reviewed reader, with
the copies dropped and with them kept under renamed uids, every hour of
each day agrees with the published series both ways: the copies change no
hourly liquidation total.

**Owner decision (2026-11-09, asked; the recommended option).** Ruling 13
(above, with the owner rulings): an identical copy collapses to one and is
counted; a repeat that differs still refuses. Its code change is a separate
commit with its own tests, validation and independent re-review; the four
refused days are collected after the re-review PASS. CoinGlass
(`--allow-coinglass`) does not depend on it and may run meanwhile.

Next: ruling 13's code change, its validation and its independent
re-review, with CoinGlass meanwhile; then the four refused days and the
dataset build.

### RBT-003 Part B ruling 13 code change

**Status:** `COMMITTED (2026-11-09)`; awaiting the independent xHigh
re-review. No refused day is collected with it before its PASS.

**One commit** on top of the ruling's record `b55261d`. Only
`backfill_kraken`, `backfill_run` and their two test modules change; the
other adapters, the projection, the transport, the persistence, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`
are unchanged.
- `3041d0c`: the execution page parser also gives each element an identity
  (`_element_identities`), from two more readings of the page already read:
  one with every JSON number as its spelling, one with every number as
  `null`, each written with sorted keys. Two identities are equal exactly
  when the elements are the same JSON value with every number spelled the
  same way; whitespace, key order, string escapes and the earlier values of
  a key repeated inside one object (which the page's own reading drops too)
  do not count. A page
  too deeply nested to compare refuses (`RESPONSE_SHAPE_REFUSED`) instead
  of raising. `parse_execution_page` keeps its shape.
- `3041d0c`: `read_execution_day` keeps each uid's first identity. An
  execution whose uid was listed before is, after the window and day
  checks, dropped and counted (`ExecutionDay.duplicate_copies`) when its
  identity equals the first listing's, and refused as before
  (`DUPLICATE_PROVIDER_RECORD`, "appears twice") otherwise. A dropped copy
  is not part of the log, so it is not compared for order and is no step
  back. `read_liquidations` sums the days' counts
  (`KrakenLiquidationCollection.duplicate_copies`), and the liquidation
  unit's summary records it after `out_of_order_steps`. The hour records,
  the evidence file and the rows are unchanged: a copy adds no execution.

**Tests.** The adapter module has 559 tests (484 before), the run module
214 (210); no existing test or helper changed. Added: a block listed twice
back to back collapses to one listing with its copies counted and no step
back; copies across pages and a third listing are each counted, with only
the log's own step back; a day without copies counts none; whitespace, key
order and an escaped string do not make a copy differ; a repeat refuses
when one field differs in value, type or number spelling (26 pairs, such as
`1` and `1.0`, `1e0` and `1E0`, `0` and `-0`, `1` and `"1"`, `null` and
`"null"`, `NaN` and `"NaN"`, `true` and `1`, `[1,2]` and `[2,1]`, each in
both orders), and when anything else in its element differs (12 changes to
the execution, its orders or the element's own fields), also after an
identical copy and on a later page; a repeat stamped outside the day or in
the holdout refuses by that guard first; copies of liquidations and trades
in a page and across pages leave the rows, the hours' status and
corroboration and the hour evidence (apart from its response digests)
equal to the plain listing's; an element nested to any depth near the
decoder's limit is compared or refused, never raised; a comparison that
runs out of depth refuses. In the run module a liquidation unit listing a
block, its liquidation among it, twice is collected with 4 copies counted,
then skipped; a unit without copies records 0, in order or not; a unit
whose repeat differs is refused and writes nothing. On `c5fa819`'s code, 23
of the 79 new tests fail: the 56 that pass assert refusals, which the old
code gave for every repeat. Mutants (`mutants_r13.py`, one textual change
at a time against both modules, with an unchanged control passing):
14 of 14 (numbers compared by value or every number equal; no typed
reading; key order counting; every repeat collapsing or refusing; a copy
kept, not counted, or counted as a step back; the days' copies not summed;
the summary fixed at 0; the depth guard not catching `RecursionError`; the
repeat checked before the window guards; a repeat compared with the latest
listing). The depth-guard mutant is caught by the nesting test itself: near
the decoder's limit the comparison can run out of depth where the page's
first reading did not. Ruling 12's 11 mutants (re-anchored on the new
code), R12-1's, the second review-fix's and the third review-fix's, re-run
on the fix: 11 of 11, 12 of 12, 17 of 17 and 12 of 12.

**The collection.** The refused days' run ended on `c5fa819`'s code with no
unit prepared, so no prepared unit meets the new summary key. A completed
unit is skipped, not re-read; its summary keeps no `duplicate_copies`. The
four refused days wait for the re-review PASS.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-09).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,256 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `3041d0c`:
  8,567 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `b55261d..` this record; on PASS,
the four refused days, then the dataset build.

### RBT-003 Part B ruling 13 code review outcome

**Date:** 2026-11-09. **Review:** independent xHigh review of ruling 13's
code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`b076e15`, over `b55261d..b076e15`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: PASS**, with no new finding. **Ruling
13 is implemented as ruled:** the element identity keeps every number's
spelling and tells numbers, strings, nulls, booleans and structures apart
(an independent tagged-number oracle found no collision and no false
difference), and duplicate keys, escapes, lone surrogates and the supported
encodings read the same as in the page's own reading; an identical repeat
is compared with the first listing, dropped, counted once and never
compared for order; a differing repeat refuses with the old code and
message; the days' counts are summed and recorded in the unit's summary.
Ruling 12, R12-1 to R12-9, Part B's earlier fixes and rulings 5, 9, 10 and
11 still hold; R12-10 stays the owner-accepted limitation. The review asked
no owner question. **Ruling 13's code review is closed:** the four refused
days may be collected with `3041d0c`'s code.

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,256
passed, 1 xfailed; its retained Part B probes 488 passed; its retained
numeric, parser, decimal-context and window probes 744 passed, with one
deselected probe that expected an identical repeat to refuse, the behavior
ruling 13 reverses (its other copy and chain cases were run separately);
its new ruling 13 probes 241 passed (all-pairs number, type, structure and
string variants, the decoder's integer-digit limit, hostile decimal
contexts, random copy insertion across pages, a large synthetic copy page,
nesting to 100,000 levels, multi-day totals, every chain guard, and units
completed, prepared or not persisted by the pre-change code). A day without
repeats gives evidence, digests, hours and rows byte-identical to
`c5fa819`'s; inserted copies leave the rows and the hour evidence
(normalized for its response digests) unchanged; completed units skip
unchanged, and a prepared unit refuses before any database access without
replacing its saved files. Its mutation control passed (85 passed) and 18
of 18 independent mutants were caught; the pre-change code, loaded in
memory, gave the recorded 23 failures and 56 passes on the 79 new tests. No
existing test, helper or decorator changed (an AST comparison). The
execution and series request and response window and holdout guards showed
no regression; copies did not mask a repeated token, the page cap, a
differing repeat or an unknown liquidation side, and no out-of-window
execution was admitted or hidden by dropping a copy. The records match the
change and hold no collected value and no execution or liquidation count;
the live collection claims and the full-suite result were not re-observed.

Next: the owner's collection of the four refused Kraken days with the
reviewed code `3041d0c` (`kraken-liquidations --keep-going`, which skips the
completed units), with CoinGlass (`--allow-coinglass`) before or after it;
then the dataset build.

### RBT-003 Part B Kraken completion, CoinGlass's live check and owner ruling 14

**Date:** 2026-11-09. Every run below was started from the owner's shell
(credentials come from the environment and are never printed), each on a
clean detached checkout of reviewed code.

**Kraken liquidations complete.** The four refused days were collected on
`3041d0c`'s code (`kraken-liquidations --keep-going`, skipping the 1,676
completed units): all four completed, and the run's error log is empty.
All 1,680 days of the window (2021-05-27 to 2025-12-31) are complete. A
read-only database check, comparing counts only, found every unit's rows
equal to its summary and to its completion marker, one ingestion instant
per unit, no row on a day without a completed unit and no prepared unit.
Each of the four units' summaries records the copies it dropped
(`duplicate_copies` above zero).

**CoinGlass's first live run** (`c5fa819`'s code, `coinglass-etf
--allow-coinglass`) refused `RESPONSE_SHAPE_REFUSED` at the flow history's
envelope, which held `code` and `msg` but no `data`. One diagnostic request,
printing only the envelope's status, found code `"401"` and message
`"Upgrade plan"`: the key in use was not the owner's paid-plan key (the
provider documents the flow history as callable on every API plan). With
the right key the run refused again at the envelope, now `code` and `data`
without `msg`. Neither run wrote a unit directory or a row; `etf_flows`
holds no row.

**Live shape survey (value-blind).** One owner-run read of the flow history
and of each in-window fund's history (12 requests, nothing kept), walked
with the reviewed projection's own tokenizer: a record dated outside the
requested days was counted and skipped as bytes, and an in-window record
gave only its member names and each member's JSON kind. Every envelope's
`code` is `"0"` and none carries `msg`. Every in-window flow day carries
exactly `timestamp`, `flow_usd`, `price_usd` and `etf_flows`, the numbers as
JSON numbers and every stamp at `00:00` UTC; each ticker entry is
`etf_ticker` with or without `flow_usd`, as Part A reads it. The flow
history names 11 funds: ARKB, BITB, BRRR, BTC, BTCO, BTCW, EZBC, FBTC, GBTC,
HODL and IBIT. Every in-window fund history day carries exactly the ten
documented members with the documented kinds, except that 459 of IBIT's 479
omit `btc_holdings`; every stamp is at `00:00` UTC and every day names the
requested ticker. Each response's holdout and reserve records were dropped
unread; none precedes the data window.

**Net assets' date (measured at the owner's request).** A second value-blind
read compared each in-window fund history day's `assets_date` with its
`market_date` and with the flow days, reading dates only. For BRRR, BTC,
BTCO, BTCW, EZBC, FBTC, GBTC and HODL the two dates are equal on almost
every day. For ARKB and BITB `assets_date` is mostly the trading day after
`market_date`; for IBIT mostly the trading day before. Each date matches
about as many flow days as the other. Net assets stay keyed by
`assets_date`, the date of the figure (Part A): the figure joined to flow
day D is dated D, never later, and every ETF row keeps the `T+2 00:00`
floor. Keyed by `market_date`, a weekend gap would join to a Friday flow a
figure dated the next Monday, after that floor. Some BITB days are dated on
a Sunday, which is no flow day, so they join no flow. No point-in-time issue
was found, so no further owner decision was needed.

**Owner decision (2026-11-09, asked; the recommended option).** Ruling 14
(above, with the owner rulings): the envelope's `msg` and a fund history
day's `btc_holdings` may be absent; everything else stays strict. Its code
change is a separate commit with its own tests, validation and independent
re-review; CoinGlass is collected after the re-review PASS.

Next: ruling 14's code change, its validation and its independent
re-review; then CoinGlass and the dataset build.

### RBT-003 Part B ruling 14 code change

**Status:** `COMMITTED (2026-11-09)`; awaiting the independent xHigh
re-review. CoinGlass is not collected with it before its PASS.

**One commit** on top of the ruling's record `321487e`. Only
`backfill_projection`, `backfill_coinglass` and the adapter and run test
modules change; the other adapters, the run, the transport, the
persistence, the collectors, the raw schema, the RBT-001 and RBT-001A
builders, every owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.
- `87dc505`, the projection: the envelope must be exactly `code`, `msg` and
  `data`, or `code` and `data`; a repeated, unknown or missing `code`
  member still refuses. A present `msg` must still be a JSON string and is
  kept byte for byte, as before; an absent one is not invented, so the
  projected response is `code` and `data` alone. A `code` other than `"0"`
  now refuses naming the code and the `msg`, if any, before `data` is
  required, so an error reply without `data` names its status (the first
  live run's `401` refusal named only member names); its records are
  never walked. Every other check, the date members, the counts and
  `verified_body` are unchanged.
- `87dc505`, the parser: the envelope may lack `msg` (checked as a string
  when present), and a fund history day may lack `btc_holdings`, which,
  when present, is still a finite JSON number. The other nine fund members
  and the four flow-day members stay required, and an unknown member still
  refuses. Two refusal messages now say "msg optional" and "btc_holdings
  optional"; the refusal codes are unchanged.

**Tests.** The adapter module has 637 tests (559 before), the run module
217 (214); no existing test or helper changed. Added: an envelope without
`msg` is projected without one, with the same kept records and drop counts
as the documented envelope, and `verified_body` accepts it, in any member
order or whitespace; a present `msg` (plain, empty, escaped) is kept byte
for byte; 23 envelopes still refuse (empty, `code` or `data` alone, `msg`
without `code`, extra, repeated or misspelt members, a non-string `code` or
`msg`, a non-array `data`, trailing bytes, a malformed record); both
envelopes are read; six error replies name their code and any message,
with or without `data`, never a record; a live-shaped read, with and
without `btc_holdings`, gives the documented read's rows, tickers, missing
net assets and projection counts; one history may mix days with and
without `btc_holdings`; each other fund member is still required, with and
without `btc_holdings` (18 cases); an unknown or misspelt fund member still
refuses; a present `btc_holdings` and a present `msg` (on either endpoint)
are still type-checked; each flow-day member is still required. In the run
module a live-shaped unit (no `msg`, IBIT without `btc_holdings`) is
collected with the documented unit's rows, summary counts and completion
marker, its projections without `msg`, then skipped; such a unit
interrupted after its commit resumes from its projections without a
request; an error reply refuses naming its status (digits masked, as in
every report) and writes nothing. On `321487e`'s code, 14 of the 81 new
tests fail: the 67 that pass assert refusals, which the old code gave more
broadly, a present `msg` kept byte for byte, or the documented error
message. Mutants (`mutants_r14.py`, one textual change at a time against
both modules, with an unchanged control passing): 16 of 17 caught (`msg`
or `btc_holdings` required again; `data` not required; a repeated, unknown
or missing envelope member admitted; a present `msg` unchecked in the
projection; `data` required before the code is read; the error's message
dropped; a present `msg` dropped or an absent one written empty; every
fund number but `net_assets` optional; an unknown fund member admitted; a
present `btc_holdings` unchecked or an absent one read). The survivor is
equivalent: the parser's own `msg` check stands behind the projection's,
and `verified_body` re-projects every body a parser reads. Part B's 22
projection and CoinGlass mutants (`partb/mutants_b.py`, `mutants_c.py`),
three re-anchored on the changed or moved lines, are all still caught.

**The collection.** No CoinGlass unit exists: both refused runs wrote
nothing. CoinGlass waits for the re-review PASS.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-09).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,337 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `87dc505`:
  8,648 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `321487e..` this record; on PASS,
CoinGlass, then the dataset build.

### RBT-003 Part B ruling 14 code review outcome

**Date:** 2026-11-10. **Review:** independent xHigh review of ruling 14's
code change, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`cdbcb81`, over `321487e..cdbcb81`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: FAIL**, on one P2 finding, CONFIRMED:
the CoinGlass numeric-decoder limitation the owner had recorded outside the
Kraken review (R12-5, above), which this review's requirement that every
body parse or refuse no longer excludes. It is not a regression of ruling
14's change, admits no row and exposes no holdout value. **Ruling 14 is
implemented as ruled:** the envelope is `code` and `data` with `msg`
optional, a JSON string kept byte for byte when present; a fund history
day's `btc_holdings` is optional, a finite JSON number when present; every
other member, the unknown-member and repeated-member refusals are
unchanged; a provider error refuses naming its code and any message before
`data` is required. A documented unit gives byte-identical projections,
rows, summary, evidence files and completion marker to `c5fa819`'s, and a
live-shaped unit completes, resumes, reopens, proves and skips like a
documented one. Ruling 12, R12-1 to R12-9, ruling 13, Part B's earlier
fixes and rulings 5, 9, 10 and 11 still hold; R12-10 stays the
owner-accepted limitation. Its owner question: does the recorded
limitation remain an accepted exception for this review?

**Findings.** The location refers to `cdbcb81`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| R14-1 / **P2** | `backfill_coinglass.py:122` (`_envelope`) | The reader decodes every JSON number with `Decimal` and catches only `UnicodeDecodeError` and `ValueError`. A well-formed numeral whose exponent `decimal` cannot hold (`1e+1000000000000000000`) in an in-window record passes the value-blind projection and `verified_body`, then raises `InvalidOperation` under the default context, leaving `run_unit` before any unit directory or database write; with the caller's `InvalidOperation` trap off it refuses instead. | Such a numeral in a flow day's `flow_usd` or `price_usd`, a ticker's `flow_usd`, a fund day's `net_assets` or a present `btc_holdings`, with or without `msg`: 10 parser cases and one run case raise. Refuse it whatever the caller's traps, as Kraken's reader does since R12-5. |

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,337
passed, 1 xfailed; its retained Part B probes 488 passed; its Kraken,
numeric and CoinGlass regression probes 1,154 passed, with the one probe
ruling 13 reverses deselected; its new ruling 14 probes (169) cover both
envelope forms, records before the window, unrequested, in the holdout or
in the reserve, either fund date outside the window, unreadable numerals in
dropped records (never decoded), old-against-new byte parity, the optional
members' types, malformed, repeated, escaped and missing envelope members,
structured statuses refused undecoded, nesting to 100,000 levels on every
path, live-shaped completion, resume, reopen and proof with the parsers
blocked, the exact `assets_date` join, missing net assets and the
`T+2 00:00` and later publication floors. Its 21 numeric expectations
failed 11 times (R14-1), and with an in-memory guarded decode the adapter
and run modules and all its probes passed (1,044). Of its 17 mutants, 16
were caught; the survivor, removing the parser's own `msg` check, is
equivalent behind `verified_body` (1,023 passed without it). The
pre-change code, loaded in memory, gave the recorded 14 failures and 67
passes on the 81 new tests. No existing test, helper or decorator changed
(an AST comparison). The net assets' date: the join uses exactly
`assets_date`, a missing figure stays `None` and is listed in
`missing_aum`, and the replay builder applies `T+2 00:00` or a later
supplied publication time; no lookahead was found under that model (the
surveys do not establish actual publication times). The records match the
change and hold no collected value; the live collection claims and the
full-suite result were not re-observed.

**Owner decision (2026-11-10, asked; the recommended option):** fix R14-1
now, in its own commit with its tests and mutants, validate, then
re-review: CoinGlass's reader decodes in a context that traps
`InvalidOperation` and refuses such a number (`RESPONSE_SHAPE_REFUSED`, "holds
a number no decimal can hold") whatever the caller's traps, as Kraken's
does. CoinGlass waits for the re-review PASS.

Next: the R14-1 fix, its validation and its independent re-review; then
CoinGlass and the dataset build.

### RBT-003 Part B R14-1 fix

**Status:** `COMMITTED (2026-11-10)`; awaiting the independent xHigh
re-review. CoinGlass is not collected with it before its PASS.

**One commit** `d9e611f` on top of the review's record `d3f0619`. Only
`backfill_coinglass` and the adapter and run test modules change; the
projection, the other adapters, the run, the transport, the persistence,
the collectors, the raw schema, the RBT-001 and RBT-001A builders, every
owner, configuration, the inventory, the spec, `data/` and
`research_artifacts/` are unchanged.
- CoinGlass's reader (`_envelope`) decodes the verified projection in its
  own decimal context, which traps `InvalidOperation`, so a JSON number
  whose exponent `decimal` cannot hold refuses (`RESPONSE_SHAPE_REFUSED`,
  "the flow history holds a number no decimal can hold", or "the IBIT
  history ...") whatever the caller's traps, as Kraken's reader does since
  R12-5; before, it raised under the default context and, with the trap
  off, refused as not finite. Decoding is exact in any precision, so every
  number `decimal` holds decodes as before; the other refusals, the
  envelope and member rules (ruling 14) and the projection are unchanged.
  Deep nesting needs no new guard: the projection refuses a body nested
  past its depth limit before any decoding.

**Tests.** The adapter module has 695 tests (637 before), the run module
219 (217); no existing test or helper changed. Added: such a number in
every numeric member of both endpoints (a flow day's `flow_usd` and
`price_usd`, a ticker's `flow_usd`, a fund day's `net_assets`,
`btc_holdings`, `market_price`, `nav`, `premium_discount` and
`shares_outstanding`), with and without `msg`, with the caller trapping
`InvalidOperation` or not, refuses with the exact message (36 cases); five
such exponents (zero and negative coefficients, a fraction, a capital `E`)
refuse on either endpoint; the largest exponent `decimal` holds, a smaller
one, a 4,001-digit integer and a negative zero still decode, with the same
rows; an integer too long for Python still refuses; a read under a hostile
caller context (precision 1, exponent limits of one, every signal trapped)
gives the same rows and the same refusal; such a number in a record before
the window or in the holdout is never decoded, with or without `msg` (every
`json.loads` call is watched). In the run module the unit refuses, with
the caller trapping or not, and writes no unit directory and no row. On
`d3f0619`'s code, 49 of the 60 new tests fail; the 11 that pass are the
numbers that still decode, the integer too long for Python and the dropped
records. Mutants (`mutants_r141.py`, one textual change at a time, with an
unchanged control passing): 7 of 8 caught (the caller's context decoding;
a context trapping nothing; `InvalidOperation` not caught, refused as not
JSON, without naming what was read, or with another code; `ValueError` not
caught). The survivor, catching every `ArithmeticError`, is equivalent:
decoding raises no other. Ruling 14's 17 mutants (16 caught, the same
equivalent survivor) and Part B's 22 are unchanged.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-10).**
- The adapter and run modules with the V1/V2 replay, replay-review, database
  and four coverage guard modules: 1,397 passed, 1 xfailed; the BTC-019 completion gate
  and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `d9e611f`:
  8,708 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only; no network read, no
  database connection.

Next: the independent xHigh re-review of `d3f0619..` this record; on PASS,
CoinGlass, then the dataset build.

### RBT-003 Part B R14-1 re-review outcome

**Date:** 2026-11-10. **Review:** independent xHigh re-review of the R14-1
fix, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`2005d7c`, over `d3f0619..2005d7c`, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, no collection touched;
its worktree stayed clean. **Result: PASS**, with no new finding. **R14-1
is FIXED:** the projection is verified before any decoding, and a private
context trapping `InvalidOperation` turns a number no decimal can hold into
`RESPONSE_SHAPE_REFUSED` naming the reader, under any caller context; all
21 of the review's numeric regression expectations now pass, and
`run_unit` refuses without a unit directory or a database connection.
Every number `decimal` holds keeps its exact value and spelling (exponent
limits, long coefficients and integers, signed zeros); the caller's flags
and traps are unchanged and later parser operations use the caller's
context; documented and live-shaped units are byte-identical to `87dc505`'s
(rows, summaries, evidence, exposure records and completion markers).
Ruling 14, rulings 12 and 13, R12-1 to R12-9, Part B's earlier fixes and
rulings 5, 9, 10 and 11 still hold; R12-10 stays the owner-accepted
limitation. The review asked no owner question. **Ruling 14's code review
is closed:** CoinGlass may be collected with `d9e611f`'s code.

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,397
passed, 1 xfailed; its retained Part B probes 488 passed; its final
independent regressions (Kraken, numeric, ruling 13, ruling 14 and the new
R14-1 probes) 1,353 passed, with two obsolete scratch characterizations
deselected (one expects the pre-fix exception, one an identical Kraken
repeat to refuse, which ruling 13 reverses). Its new probes cover
unrepresentable numerals in numeric and other members of both endpoints,
both envelopes, caller traps on and off, hostile precision, exponent
limits, rounding, `capitals` and clamping, the caller's flags and traps
preserved, the constructor's boundaries, representable extremes, body and
row parity with `87dc505`, byte-identical full units, the other refusal
messages unchanged, the decoding context's scope, and unrelated
programming errors left visible. The pre-fix code, loaded in memory, gave
the recorded 49 failures and 11 passes on the 60 new tests. Its mutants:
nine caught, including rounded and binary-float decoding, and the one
equivalent survivor the record names (catching every `ArithmeticError`;
its control passed 1,282 tests); ruling 14's mutants rerun on the fix gave
16 caught and the same equivalent survivor. No existing test, helper or
decorator changed (an AST comparison). The holdout guards held with and
without `msg`: records before the window, unrequested, in the holdout or
in the reserve are dropped before any value is decoded, and an
unrepresentable numeral in a dropped record never reaches `json.loads`, a
parser, the projected evidence or a row; malformed, extreme and deeply
nested inputs found no other exception path. The record matches the fix;
the collection status and the full-suite result were not re-observed.

Next: the owner's CoinGlass collection with the reviewed code `d9e611f`
(`coinglass-etf --allow-coinglass`); then the dataset build.

### RBT-003 Part B CoinGlass collection

**Date:** 2026-11-10. The owner started the run from their shell
(credentials come from the environment and are never printed) on a clean
detached checkout of the reviewed code `d9e611f`: `coinglass-etf
--allow-coinglass`. Its one unit, `all`, completed: 12 requests (the flow
history and the history of each of the 11 funds it names: ARKB, BITB, BRRR,
BTC, BTCO, BTCW, EZBC, FBTC, GBTC, HODL and IBIT), each answered `200`;
the run's error log is empty.

**Holdout guard.** Every response was read only through the projection
(owner ruling 10): each saved projection covers days inside 2024-01-11 to
2025-12-31, on the flow history's `timestamp` or the funds' `assets_date`
and `market_date`; every response's holdout and reserve records were
dropped unread, and none held a record before the data window. Only the
projections are kept.

**Checks (read-only, counts compared, none printed).** The unit's rows
equal its summary and its completion marker; the database's CoinGlass rows
equal the summary, with one ingestion instant, exactly the 11 funds the
summary names, every date inside the window and no repeated fund day; the
rows without net assets are exactly the fund days the summary lists as
missing them (net assets are keyed by `assets_date`, so a fund whose
`assets_date` runs a trading day off its flow days lacks some, as the date
survey measured); `etf_flows` holds no other provider. The persisted
counts include the fund trading days without a published flow, which BTC-022's
collector reports and does not store.

**Evidence.** The Kraken liquidation units (all 1,680 days, completed
2026-11-07 to 2026-11-09 on `4d6b14d`, `c5fa819` and `3041d0c`) and the
CoinGlass unit are committed to the private evidence repository (owner Part
B ruling 9), after the incident list, Binance and Coin Metrics evidence;
each unit's completion marker binds its files by SHA-256.

**Every Part B source is collected.** The dataset build is the next code: a
window-bounded database reader, the V1 and V2 builders, the manifests in
the private repository and a value-free index here.

Next: the dataset build.

### RBT-003 Part B owner ruling 15 (missing hours before the build)

**Date:** 2026-11-10. Before writing the dataset build, a read-only database
census was run, bounded to the data window (series identities and counts
only, no value). Every in-window row of the seven raw tables belongs to one
of two groups. The first is the three venues' `1h` OHLCV series. The second
is the series RBT-003 collected: Binance funding, open interest, perpetual
volume and COIN-M basis, Kraken Futures liquidations, and CoinGlass ETF
flows. Each collected table's rows equal the sum of its units' summaries. One
item of RBT-002's acquisition plan is still open: re-requesting the missing
Coinbase and Bitfinex hours. The same 27 hours are still missing. The owner
chose to re-request them first, under the same review as the dataset build
code (ruling 15 above).

**Dry build, read-only, in memory (2026-11-10), and owner ruling 16.**
Before the tests were written, the draft build code ran once against the
database. Every query was bounded to the data window, nothing was written and
the output was value-free; the missing-hours units were stood in by the
incident unit. The reader's queries ran, and each collected series held
exactly the rows its units record persisted. The V1 builder accepted the
real rows. The V2 builder refused at the first Kraken hour whose total
disagrees with Kraken's hourly series (RBT-001A ruling 2): 14 such hours on
13 days, characterized above. The owner chose to withhold them, so their
days are incomplete (ruling 16 above).

Withheld hours (UTC): 2021-05-27 11:00, 2021-08-19 04:00, 2022-02-11 05:00,
2022-08-08 22:00, 2022-11-11 02:00 and 07:00, 2023-06-23 16:00, 2023-09-19
08:00, 2023-11-01 21:00, 2023-12-04 22:00, 2023-12-12 17:00, 2023-12-20 19:00,
2024-02-04 22:00 and 2024-02-26 20:00.

Next: the re-request source and the dataset build code, their validation and
their independent review; then the owner's re-request run and the build.

### RBT-003 Part B re-request and dataset build code

**Status:** `COMMITTED (2026-11-10)`; awaiting the independent xHigh review.
Neither the re-request nor the build runs before it passes.

**One commit** `7e4f871` on top of ruling 16's record `3665152`. It adds the
modules `backfill_ohlcv`, `dataset_reader` and `dataset_build` and their test
modules, and makes additive changes to `backfill_persistence`, `backfill_run`
and `backfill_transport`. Unchanged: the projection, the other adapters, the
collectors, the raw schema, the RBT-001 and RBT-001A builders, every owner,
configuration, the inventory, the spec, `data/` and `research_artifacts/`.

**The re-request (ruling 15).** The new source `ohlcv-missing-hours` has one
unit per venue (`bitfinex`, `coinbase`) and requests exactly the hours
RBT-002 recorded, one adapter call per run, through the unchanged BTC-020
`CoinbaseOhlcvProvider` and `BitfinexOhlcvProvider`.
- Their JSON requester is replaced by one that reads through the backfill
  fetcher, so every response is logged as the other sources' are and comes
  from the transport's allowlist. The allowlist gains `api.exchange.coinbase.com`
  and `api-pub.bitfinex.com` only.
- Before an adapter sees a response, the requester refuses a body that is not
  a JSON list of candle rows (no `NaN` or `Infinity` literal, no nesting too
  deep to decode). Each row must start with the integer epoch its venue
  documents: ten digits of seconds for Coinbase, thirteen of milliseconds for
  Bitfinex.
- A candle dated outside the data window is refused, never filtered (Part A's
  decision 1). The adapter keeps only the requested hours and checks each
  candle; its own errors refuse by type, never by text.
- A value is kept only when `raw.btc_ohlcv`'s `NUMERIC(38,18)` holds it
  exactly.
- Rows are persisted per run through BTC-020's `collect_btc_ohlcv` (its
  insert-only statement), via the new `RecordedOhlcvProvider` and
  `persist_ohlcv`. These refuse a request that renames the rows, asks for a
  derived bar or reaches outside the window.
- The unit's summary lists the hours requested, returned and still missing,
  and the row count. An hour still missing stays a preserved gap. The
  collection run's markers, resume and value-free output apply unchanged.

**The window-bounded reader (`dataset_reader`).** It reads nine series by
identity: the three venues' `1h` OHLCV (Bitstamp's is also the shared
volume), Binance funding (`BTCUSDT`), open interest (USD), perpetual volume
(BTC) and COIN-M basis (`BTCUSD`), Kraken `PI_XBTUSD` liquidations
(contracts), and CoinGlass ETF flows.
- Each query selects a row only when the whole interval it observes lies in
  the data window, as the builders admit it: `[t, t + 1h)` for a bar or a
  `1h` aggregate, `(S - interval, S]` for a funding settlement, the instant
  for a snapshot, the UTC day for an ETF flow. No query reaches the
  prohibited window, the holdout or the reserve.
- A guard then counts each table's in-window rows, reading no value, and
  refuses (`DATASET_ROWS_UNREAD`) if the series left any row unread.
- The read runs in one read-only, repeatable-read transaction and refuses
  otherwise. Rows become the owners' records unchanged, with instants
  normalized to UTC.

**The build (`dataset_build`, `python -m
btc_predictor.research_backtest.dataset_build build | verify | index`).**
1. Every unit the build depends on must be completed and persisted, judged
   by the collection run's own `_complete` (reviews B4, BR2, BR4, BR6, BR7):
   every scheduled unit of the six persisting sources, the market cap and
   the re-request.
2. The basis listing and the market-cap file are parsed against the digests
   their summaries record. Each Kraken day's hour evidence is decompressed,
   parsed against its summary's digest, and must be exactly that day's 24
   hours.
3. Each collected series must hold exactly the rows its units record
   persisted (`EVIDENCE_MISMATCH` otherwise).
4. The V1 shared snapshot is built with `US_EQUITY_MARKET_CLOSURE_TABLE_V1`
   and no ETF publication time (CoinGlass publishes none, so the `T+2 00:00`
   floor applies). Then the three venue datasets and the V2 extended
   snapshot.
5. Ruling 16 withholds each disagreeing Kraken hour, its evidence and its
   rows, from the V2 builder.
6. The build writes `research_backtest_v1/datasets/rbt003_v1/` in the
   private repository:
   - `inputs/<series>.json.gz`: each series' rows as read, canonical, numbers
     by value, so a `NUMERIC` read-back gives the same bytes;
   - `manifests/<name>.json.gz`: the five builders' manifest bytes;
   - `BUILD.json` last, binding every file by its gzip and uncompressed
     SHA-256 and size, with the code commit (a clean public checkout), the
     reader's series and every evidence unit's markers.
   An existing dataset is never overwritten, and nothing is written through
   a link.

`verify` rebuilds from the database (identical input files and manifests)
and from the frozen input files alone (identical manifests). A frozen file
that is not exactly the canonical file of its records refuses. That includes
an exponent numeral, which is refused before any decimal is built. `index`
writes this repository's value-free index once the private repository holds
the dataset in a commit:
- digests, sizes and versions;
- the code and private commits;
- the reader's series and the evidence units, with the withheld and
  still-missing hours;
- per family, the first and last observation and the gap census.
It holds no value, no record count and no liquidation or ETF activity.

**Dry build (read-only, in memory, 2026-11-10).** On the database and the
private units, the build took 26 s: manifests of 76, 19, 19, 19 and 67 MB
and 134 MB of input files. The input files parsed back byte-identically, and
the manifests rebuilt from them alone were identical. Peak memory was 2.9 GB.
The re-request is not collected, so the venue datasets will change before
the real build.

**Tests.** Two new modules: `test_research_backtest_backfill_ohlcv.py` (65)
and `test_research_backtest_dataset_build.py` (61). The world is synthetic:
every unit is produced by the real collection run against fake transports,
and the rows its collectors insert are captured. Every socket is refused,
and no database is used. No existing test or helper changed.
- *Re-request:* the schedule against RBT-002's census; requests in the
  window; the adapters' own requester never used; persisted rows, names,
  instants and summaries; an empty answer; resume; candles outside the
  window; fifteen malformed Coinbase and five malformed Bitfinex bodies;
  values the table cannot hold; non-200 answers; the persistence refusals;
  the transport's hosts.
- *Reader:* each query's exact bound and identity; the unread-row guard per
  table; the read-only refusal; UTC normalization and refusals.
- *Build:* the files and `BUILD.json`; parsing back; verification from both
  sources, and a changed row detected; order independence; numbers by value;
  fresh processes under two hash seeds from another directory.
- *Ruling 16:* the hour and its rows withheld, the day incomplete, the frozen
  inputs whole, the V2 builder still refusing.
- *Evidence and files:* missing, unpersisted, changed and mismatched units;
  the persisted-rows check; six tampered stored datasets and a linked file;
  sixteen non-canonical input files.
- *Index and commits:* the index value-free and bound to its private commit;
  both commit checks; the command line, with value-free refusals.

Mutants (`mutants_build.py`, one textual change at a time, with an unchanged
control passing): 39 of 40 caught (17 on the re-request, 7 on the reader, 16 on the build). The survivor, `persist_ohlcv_rows`' every-row check, is equivalent: the adapter keeps only the requested hours, so every row lies in a run and is persisted by that run's collector call.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-10).**
- The adapter, run and two new modules with the V1/V2 replay, replay-review,
  database and four coverage guard modules: 1,523 passed, 1 xfailed; the BTC-019
  completion gate and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `7e4f871`:
  8,834 passed, 3 skipped, 1 xfailed, 0 failed (80 min).
- `git diff --check` clean. Synthetic fixtures only in the tests; the only
  database reads were the read-only census, the missing-hours check and the
  dry build, each bounded to the data window with value-free output; no
  network read.

Next: the independent xHigh review of `545ad32..` this record; on PASS, the
owner's re-request run (`ohlcv-missing-hours`), then the build, its
verification, the private commit and the index.

### RBT-003 Part B re-request and dataset build code review outcome

**Date:** 2026-11-10. **Review:** independent xHigh review of the re-request
and dataset build code, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree moved to
`6acc12c`, over `545ad32..6acc12c` (rulings 15 and 16, the code `7e4f871`
and its record), with its saved probes. Report-only: a workspace-write
sandbox with network disabled, no database, no `.env*` file, no read of the
private evidence repository, neither command line run, no collection or
build touched; its worktree stayed clean. **Result: FAIL**, on five P2
findings and one P3, all CONFIRMED. None exposes a holdout or prohibited
value: the request, response and query window guards held. Nothing has run
on this code: no re-request, no build.

**Rulings 15 and 16 are implemented as ruled.** The re-request asks exactly
the 27 recorded hours, one adapter call per run, through the unchanged
BTC-020 adapters and insert-only collector, with no derived bar (D1 and D2
block its end-to-end integrity). Ruling 16 withholds both the evidence and
the rows of each disagreeing hour, its day becomes incomplete, the frozen
inputs keep the rows, and the unchanged V2 builder still refuses a
disagreement supplied directly. A rebuild from unchanged database rows
reproduces identical manifests (database and frozen-input rebuilds, numeric
scale, ordering, hash seeds and another directory), and nothing outside the
data window is requested or selected, including at every interval boundary
and in the count-only completeness queries. The frozen datasets are not yet
fully met: persistence verification, the private commit's provenance and
malformed-file handling have the defects below. The record overstated exact
OHLCV preservation and the private commit's provenance (D1 to D3).

**Findings.** Locations refer to `6acc12c`, under `btc_predictor/research_backtest/` unless stated.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| D1 / **P2** | `backfill_ohlcv.py:143` (`bounded_requester`) | The requester decodes JSON fractions as binary floats; the BTC-020 adapters' `Decimal(str(value))` then holds the float's shortened spelling, so the exact-storage check sees an altered value. An eighteen-place fraction loses its last digit, a nineteen-place one is rounded and accepted, `1e-324` underflows to a zero volume that is persisted and completes, and the largest value `NUMERIC(38,18)` holds rounds up to `10^20` and is refused. | Synthetic Coinbase and Bitfinex candles with those numerals. Decode fractions exactly before the unchanged adapters see them. |
| D2 / **P2** | `dataset_build.py:341` (`require_persisted_rows`) | The persisted-rows check covers the six collected series only: a re-request unit's returned hours are never reconciled with the venue bars read from the database. | A genuinely completed synthetic Coinbase unit recorded one hour returned and persisted; a database view without that hour still loaded and built. Check the returned hours against the venue's rows before freezing. |
| D3 / **P2** | `dataset_build.py:643` (`private_commit`) | Only `BUILD.json` must be tracked, and `git status` does not list ignored files: a commit can hold `BUILD.json` without the payloads it binds. | In a throwaway repository ignoring `*.gz`, committing `BUILD.json` alone returned a valid private commit; its clone cannot load the dataset. Check every bound file in the named commit against the stored bytes. |
| D4 / **P2** | `dataset_build.py:518` (`load_dataset`), and `:313` (the hour evidence) | `gzip.decompress` expands the whole output before the recorded size is compared. | A file matching its gzip digest and size, declaring one uncompressed byte, expanded to 8 MiB before refusing; a larger one can exhaust memory first (not attempted). Bound the expansion by the recorded size. |
| D5 / **P2** | `dataset_build.py:500` (`load_dataset`) | The `BUILD.json` decode is guarded, but its canonical re-encoding is not: `NaN`, `Infinity`, `-Infinity` or the valid numeral `1e999` raise `ValueError` instead of `DATASET_FILE_REFUSED`, past the command line's handler. | Each value in place of a metadata value. Guard the encoding and check the metadata's types. |
| D6 / P3 | `docs/execution/research_backtest_track_v1.md:3555` (owner ruling 16) | The ruling's public rationale states how many withheld hours hold one liquidation: collected activity beyond the public gap census. | Keep the rule and the hours public; keep the quantitative diagnosis private. |

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module; the dataset command-line
test deselected so as not to run its entry point): the focused modules
1,522 passed, 1 xfailed; its retained Part B probes 489 passed; its new
edge, storage, integrity, boundary and resume probes gave 17 corrective
failures (the findings) and 58 passes, among them the nine series'
predicates evaluated without a database across the prohibited, holdout and
reserve boundaries (fractional funding intervals included), both venues'
resume of an interrupted read from its saved log, value-free masking of an
extreme frozen quantity's refusal, and deeply nested `BUILD.json`
metadata. Its in-memory corrective controls (exact decimals, a guarded
encoding, a bounded expansion, payloads in the commit, returned hours
checked) passed all 73 corrective expectations. Of its 20 mutants, 19 were
caught; the survivor, removing the every-row persistence check, is
equivalent on the adapter's path, as the record states. No existing
adapter, projection, collector, schema, V1 or V2 builder, owner, test or
helper changed; R12-10 stays the owner-accepted limitation. The full-suite,
PAD, gate and dry-build results were not re-observed.

**Owner decision (2026-11-10, asked; the recommended option):** fix all
six, each in its own commit with its tests and mutants, validate, then
re-review:
- D1: the requester decodes every JSON fraction as the exact decimal it
  spells, in a context that refuses an exponent no decimal can hold (as
  R14-1);
- D2: every hour a re-request unit returned must be among its venue's rows
  read, and every hour it left missing must not be;
- D3: every file `BUILD.json` binds, and `BUILD.json` itself, must be in the
  named commit with exactly the stored bytes, and the commit's dataset
  directory must hold nothing else;
- D4: gzip expansion stops past the recorded size (the hour evidence past a
  fixed bound), refusing;
- D5: `BUILD.json` with a non-finite or mistyped value refuses;
- D6: the count is removed from ruling 16's rationale, fixed forward; the
  pushed history is not rewritten.
The re-request and the build wait for the re-review's PASS.

Next: the six fixes, their validation and the independent re-review; then
the owner's re-request run and the build.

### RBT-003 Part B re-request and dataset build review fixes

**Status:** `COMMITTED (2026-11-10)`; awaiting the independent xHigh
re-review. Neither the re-request nor the build runs before its PASS.

**One commit per finding**, on top of the review's record `d0efcff`:
D6 `0219a41` (documentation), D1 `8b25fc9`, D2 `8c98be8`, D3 `9bf4421`, D4 `18edd58` and D5 `2d0307b`. They change only `backfill_ohlcv`, `dataset_build`, their two test
modules and ruling 16's rationale. Unchanged: the BTC-020 adapters and
collector, `backfill_persistence`, `backfill_run`, `backfill_transport`,
`dataset_reader`, the projection, the other adapters, the raw schema, the
RBT-001 and RBT-001A builders, every owner, configuration, the inventory,
the spec, `data/` and `research_artifacts/`.

- **D1** (`backfill_ohlcv`). The requester decodes every JSON fraction as the
  decimal it spells (`parse_float=Decimal`), in a context that traps
  `InvalidOperation`: a numeral whose exponent no decimal can hold refuses
  ("holds a number no decimal can hold") whatever the caller's context, as
  R14-1 fixed for CoinGlass. The adapters' `Decimal(str(value))` then keeps
  the venue's value exactly, so the `NUMERIC(38,18)` check sees the value
  sent: a value the column holds is persisted as spelled, one it cannot hold
  refuses, never rounded or underflowed. Integers and the epoch checks are
  unchanged.
- **D2** (`dataset_build`). The build evidence carries, per venue series, the
  hours its re-request returned and the hours it left missing. They come from
  the unit's summary, which must list exactly the venue's scheduled hours as
  requested, split into returned (one row each) and still missing. Before any
  builder runs, each venue's rows must hold every returned hour and none left
  missing (`EVIDENCE_MISMATCH`), from the database and from the frozen inputs
  alike.
- **D3** (`dataset_build`). `private_commit` takes the dataset as loaded.
  `BUILD.json` and every file it binds must be in the named commit as regular
  files whose blobs are exactly the stored bytes (computed in the
  repository's object format), each payload re-read must still be the file
  loaded, the commit's dataset directory must hold nothing else, and the
  working tree must not differ from it, ignored files included.
- **D4** (`dataset_build`). A stored file and a day's hour evidence are
  expanded as exactly one gzip member through zlib, at most one byte past the
  declared size: output past it, a stream without its end and trailer, or
  bytes after it refuse. The size comes from `BUILD.json` or the day's
  summary (`evidence_size`, recorded by every collected day) and must be an
  integer from zero to `MAX_FILE_SIZE` (1 GiB; the dry build's largest file
  was 76 MB), or the file refuses unexpanded.
- **D5** (`dataset_build`). The canonical re-encoding of `BUILD.json` runs
  inside the guard, so `NaN`, `Infinity`, `-Infinity` or `1e999` refuse
  (`DATASET_FILE_REFUSED`), never raise. Its metadata must then be this
  build's: its version, ticket, evidence class, window and reader, a commit
  id, the gzip settings, the evidence section's exact shape (each source's
  unit count, first and last unit and marker digest; the withheld and
  still-missing hours as text; the two evidence digests) and each input
  entry's record count. Each entry's digests and sizes stay checked against
  its file.
- **D6** (documentation). The count of withheld hours holding one
  liquidation is removed from ruling 16's rationale; the rule, the hours and
  the comparison with the series stay. Fixed forward: the pushed history is
  not rewritten.

**Dry build on the fixes (read-only, in memory, 2026-11-10).** On the
database and the private units, with the re-request not yet collected (its
two venues taken as returning nothing): every Kraken day's hour evidence
loaded through D4's bounded expansion; no venue's rows hold any of the 27
scheduled missing hours (D2); the five manifests and the input files were
the earlier dry build's sizes; each input and manifest expanded back exactly
at its size and refused one byte less; the build record met D5's metadata
check; the input files parsed back byte-identically and the manifests
rebuilt from them alone were identical. Peak memory was 2.9 GB. Nothing was
written.

**Tests.** `test_research_backtest_backfill_ohlcv.py` 65 to 82 and
`test_research_backtest_dataset_build.py` 61 to 131. No test or helper
outside these two modules changed; in them, the two `private_commit` calls
take the loaded dataset, and one case's comment is corrected.
- *D1:* four exact volumes persisted as spelled through `run_unit` and the
  BTC-020 collector, and four the column cannot hold refused with nothing
  persisted, for both venues; decoding under a three-digit, trap-free caller
  context.
- *D2:* a Coinbase re-request collected through the real run returns one
  hour; the build proceeds with it in the rows and refuses without it; a
  Bitfinex hour left missing in the rows refuses; nine summaries that do not
  split the scheduled hours refuse; a consistent rewrite loads.
- *D3:* payloads ignored and left out refuse, forced in pass; an ignored
  stray file refuses as an untracked one does; a committed extra file, a
  payload committed with other bytes (the working tree as stored) and a
  dataset other than the one loaded refuse; the blob ids are git's own.
- *D4:* a 96 MiB file declaring one byte, stored or as a day's hour evidence,
  refuses with peak traced memory under a twelfth of it; a declared size
  beyond the (lowered) bound, negative, boolean, text or absent refuses
  unexpanded, with the bound's control; two members, a trailing byte and a
  cut trailer refuse.
- *D5:* six numerals (non-finite, a fraction, an exponent) in two metadata
  members refuse, and the command line's `verify` and `index` refuse them
  value-free; twenty-five metadata values the build never writes refuse; a
  canonical rewrite loads.

Mutants (`mutants_build.py`, one textual change at a time in a separate
worktree, with an unchanged control passing): 56 of 57 caught: all 17 on the fixes (f1-f17) and 39 of the earlier 40 (m6, b12 and b14 re-anchored to the moved code). The survivor, `persist_ohlcv_rows`' every-row check, is equivalent, as before: every row lies in a run.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-10).**
- The adapter, run and two new modules with the V1/V2 replay, replay-review,
  database and four coverage guard modules: 1,610 passed, 1 xfailed; the BTC-019
  completion gate and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `2d0307b`:
  8,921 passed, 3 skipped, 1 xfailed, 0 failed (80 min).
- `git diff --check` clean. Synthetic fixtures only in the tests; the only
  database read was the read-only dry build, bounded to the data window with
  value-free output; no network read.

Next: the independent xHigh re-review of `6acc12c..` this record; on PASS,
the owner's re-request run (`ohlcv-missing-hours`), then the build, its
verification, the private commit and the index.

### RBT-003 Part B re-request and dataset build review-fix re-review outcome

**Date:** 2026-11-11. **Review:** independent xHigh re-review of the review
fixes D1 to D6, run by the OpenAI Codex CLI in the same session
(`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree recreated at
`e5051a0`, over `d0efcff..e5051a0` with `545ad32..d0efcff` as its base, with
its saved probes. Report-only: a workspace-write sandbox with network
disabled, no database, no `.env*` file, no read of the private evidence
repository, neither command line run from a shell, no collection or build
touched; its worktree stayed clean. **Result: FAIL**, on one P2 and two P3,
all CONFIRMED; the implementer reproduced all three with the reviewer's
probes at `e5051a0` (eight failures). None exposes a holdout or prohibited
value: the request, response, read and completeness-query guards held.
Nothing has run on this code: no re-request, no build.

**The six findings.** D1, D2, D4 and D6 are FIXED; D3 and D5 are FIXED IN
PART (DR3; DR1 and DR2). Rulings 15 and 16 stay met. The builders'
integration, the identical-manifest rebuild and the window guards pass
synthetic verification, and valid dataset files are byte-identical to
`7e4f871`'s. The value-free index is not met (DR1). The 1 GiB bound limits
each expansion (not the process's memory as a whole), and `evidence_size`
is the uncompressed evidence length the collector already recorded. The fix
record overstated D5's metadata check and the completeness of the refusals.

**Findings.** Locations refer to `e5051a0`, under `btc_predictor/research_backtest/`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| DR1 / **P2** | `dataset_build.py:611` (`_well_formed_evidence`), also `:606-607`, `:634` and the index, `:761-762` | The metadata check requires the withheld hours, the still-missing hours, each source's first and last unit and the zlib version only to be text, and the index copies them. | Five synthetic datasets, each with a price-bearing string in one of those fields of `BUILD.json`, loaded, passed the private-commit proof and were published by `index`. Validate each field as the timestamp, scheduled unit or version it names before publication. |
| DR2 / P3 | `dataset_build.py:686` (`_well_formed_entry`) | An entry's `gzip_size` is not type-checked: an integer-valued fraction (`N.0`) equals the file's length and is accepted. The D5 draft had this check; it was removed as redundant because no test failed without it, where a test with `N.0` would have shown it was not. | An input entry and a manifest entry with `gzip_size` `N.0` loaded. Require an integer. |
| DR3 / P3 | `dataset_build.py:840` (`private_commit`), through `_git`, `:793` | `ls-tree -z` prints raw file names, which `_git` decodes strictly as text. | A committed stray file whose name holds the byte `0xff` raised `UnicodeDecodeError` instead of `PRIVATE_COMMIT_REFUSED`. Refuse instead. |

**Test gaps (no defect).** Removing only the compressed digest's comparison
in `load_dataset`, or only the committed-mode check in `private_commit`,
leaves all 131 dataset tests passing. The code rejects both cases (the
reviewer's probes: a valid gzip of the same bytes with another header; a
committed symbolic link behind a regular working file).

**Checks that passed.** Codex's runs (`.venv312`, one process at a time, no
full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,610
passed, 1 xfailed; its original corrective expectations 73 passed (two
obsolete characterizations of the old defect deselected); 104 new positive
controls with its 489 retained Part B probes 593 passed, among them
seventy-two decimal-context combinations, an unholdable exponent at every
candle position for both venues, SHA-1 and SHA-256 repositories, the
returned and missing hours checked from the frozen inputs, and the dataset
files' parity with `7e4f871`; its eight new corrective expectations failed
(the findings); its in-memory corrective control passed 112. Of its 39
mutants, the repository tests caught 36; the every-row persistence check's
removal is equivalent, as recorded, and the other two are the gaps above.
No existing test or helper changed beyond the two recorded private-commit
callers, whose assertions are not weakened. The full-suite, PAD, gate and
dry-build results were not re-observed.

**The manifests' text (the implementer's finding, owner-accepted).** While
preparing DR1, the implementer found that `index` likewise publishes text
from the stored manifests (series identities, observation times, gap
methods and reasons) checked against nothing but the digests `BUILD.json`
binds: a synthetic manifest changed with its digests and committed was
published. This dates from `7e4f871`, and neither review reported it. Its
identities come from the data rows, so closing it would need a per-family
allowlist.

**Owner decisions (2026-11-11, asked; the recommended options):**
- fix DR1, DR2 and DR3, each in its own commit with its tests and mutants,
  add the two missing tests in one test-only commit, validate, then
  re-review;
- DR1: `load_dataset` validates each text field of `BUILD.json`'s metadata
  as what it names: the withheld and still-missing hours as canonical
  whole-hour UTC timestamps inside the data window, sorted and distinct,
  the still-missing ones among their venue's scheduled re-request hours;
  each source's first and last unit among its scheduled units; the zlib
  version as a version. Nothing is read from the units at index time;
- the manifests' text: an accepted limitation, with no code. `index` trusts
  the manifests as builder output (bound by `BUILD.json`'s digests,
  committed privately and checked against the database by `verify`); the
  index is written only after `verify` passes, and the owner reviews its
  diff before committing it publicly.

Next: the three fixes and the test-only commit, their validation and the
second re-review; then the owner's re-request run and the build.

### RBT-003 Part B re-request and dataset build re-review fixes

**Status:** `COMMITTED (2026-11-11)`; awaiting the second independent xHigh
re-review. Neither the re-request nor the build runs before its PASS.

**One commit per finding**, on top of the re-review's record `2189575`:
DR1 `9175a9c`, DR2 `dea5ae0`, DR3 `4caa174` and the two tests `5e78ab7` (test-only). They change only `dataset_build` and its test module.
Unchanged: `backfill_ohlcv` and its tests, the BTC-020 adapters and
collector, `backfill_persistence`, `backfill_run`, `backfill_transport`,
`dataset_reader`, the projection, the other adapters, the raw schema, the
RBT-001 and RBT-001A builders, every owner, configuration, the inventory,
the spec, `data/` and `research_artifacts/`.

- **DR1** (`dataset_build`). `load_dataset`'s metadata check requires every
  text in `BUILD.json`'s metadata to be what it names. The withheld and
  still-missing hours must be canonical whole-hour UTC instants (the build's
  one spelling, a zero offset checked before any conversion) inside the data
  window, ascending and distinct, and the still-missing ones among their
  venue's scheduled re-request hours. Each source's first and last unit must
  be among the units the collection schedules for it. The zlib version must
  be a version: two to four parts of one or two digits, with an optional
  lower-case suffix such as `-motley` or `.zlib-ng`. The check reads no
  unit, so the index stays independent of the units, as the owner decided.
- **DR2** (`dataset_build`). A file entry's `gzip_size` must be an integer,
  so a fraction equal to the file's length (`N.0`) refuses.
- **DR3** (`dataset_build`). `_git` decodes git's output as strict UTF-8
  (it used the locale's text decoding) and refuses output that is not: a
  committed file name that is not UTF-8 refuses `PRIVATE_COMMIT_REFUSED`
  instead of raising.
- **The two tests** (test-only). The gzip digest's comparison in
  `load_dataset` and the committed-mode check in `private_commit` are each
  pinned by a test only they pass.
- **The manifests' text** is unchanged: the owner-accepted limitation
  recorded with the re-review.

**Real metadata check (2026-11-11, no database).** On the private units,
with the re-request not yet collected (its two venues' units named as the
build will name them, and their hours taken both as all still missing and
as all returned), the evidence section the build would write passes DR1's
check: every source's first and last unit is scheduled, the 14 withheld
hours are canonical, in the window and ascending, and this interpreter's
zlib version passes. DR1 to DR3 change only the loaded dataset's checks
and the private commit's reading of git, so no manifest or input file
changes and the second dry build's results stand. Nothing was written.

**Tests.** `test_research_backtest_dataset_build.py` 131 to 179. No other
test module and no existing test or helper changed.
- *DR1:* five price-bearing strings (a withheld hour, a still-missing hour,
  a first unit, a last unit, the zlib version), in a dataset committed as
  stored, refuse through the command line's `index` with nothing written,
  against a control the same path indexes. Twenty-six malformed texts
  refuse: hours in Z notation, at another offset, without one, spelling
  microseconds, a day, a half hour, a second past, before the window, at
  its end, past the calendar's end, no date, repeated or descending; a
  still-missing hour the re-request never schedules or the other venue's,
  or descending; a unit before or after the window or another source's;
  zlib versions with a space, a prefix, five parts, three digits, capitals
  or empty. Nine of the build's own forms load.
- *DR2:* an input entry and a manifest entry whose gzip size is written as
  the equal fraction refuse.
- *DR3:* a committed non-UTF-8 name beside the dataset refuses through
  `private_commit` and the command line's `index`, with nothing written; a
  UTF-8 non-ASCII stray refuses as another file; a non-UTF-8 name outside
  the dataset's directory does not concern it.
- *The two tests:* a stored file with another valid gzip header (the same
  bytes and length) refuses by its gzip digest; a payload committed as a
  symbolic link to its own bytes, hidden behind the regular working file,
  refuses.

Each new refusal failed on the code before its fix, and each control passed
on both. Mutants (`mutants_dr.py`, one textual change at a time in a
separate worktree, with an unchanged control passing): 73 of 74 caught: all 17 on the fixes and the two tests (g1-g17) and the earlier 56 of 57. The survivor, `persist_ohlcv_rows`' every-row check, is equivalent, as before: every row lies in a run.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-11).**
- The adapter, run and two new modules with the V1/V2 replay, replay-review,
  database and four coverage guard modules: 1,658 passed, 1 xfailed; the BTC-019
  completion gate and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `5e78ab7`:
  8,969 passed, 3 skipped, 1 xfailed, 0 failed (79 min).
- `git diff --check` clean. Synthetic fixtures only in the tests; no
  database or network read (the metadata check read the private units
  only), value-free output.

Next: the second independent xHigh re-review of `e5051a0..` this record; on
PASS, the owner's re-request run (`ohlcv-missing-hours`), then the build,
its verification, the private commit and the index.

### RBT-003 Part B re-request and dataset build second re-review outcome

**Date:** 2026-11-11. **Review:** independent xHigh second re-review of the
re-review fixes DR1 to DR3 and the two tests, run by the OpenAI Codex CLI
in the same session (`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its
worktree recreated at `eee2841`, over `e5051a0..eee2841` with
`545ad32..e5051a0` as its base, with its saved probes. Report-only: a
workspace-write sandbox with network disabled, no database, no `.env*`
file, no read of the private evidence repository, neither command line run
from a shell, no collection or build touched; its worktree stayed clean.
**Result: PASS**, with no new finding and no owner question. Nothing has
run on this code: no re-request, no build.

- **DR1 FIXED.** `load_dataset` requires the withheld and still-missing
  hours to be canonical whole-hour UTC instants inside the data window,
  ascending and distinct, the still-missing ones among their venue's
  scheduled re-request hours; each source's first and last unit among its
  scheduled units; the zlib version a version. The review's five
  text-injection probes refuse; the valid schedules, current zlib versions
  and every canonical hour of the window pass; `index` succeeds with no
  unit read and no database. Seven thousand deterministic malformed or
  mutated timestamp spellings (offsets, calendar extremes, non-canonical
  forms) raised no uncaught exception.
- **DR2 FIXED.** `gzip_size` must be a non-negative integer; the equal
  fraction refuses for an input and a manifest entry.
- **DR3 FIXED.** Git output that is not UTF-8 refuses, and `private_commit`
  turns it into `PRIVATE_COMMIT_REFUSED`, through the API and the command
  line's `index` (driven with a fake database), with no traceback and no
  index written; valid names are still compared with the bound files.
- **The two tests FIXED.** The gzip-header test changes only the header
  (the same length and decompressed bytes), and the committed-mode test
  commits a symbolic link behind an unchanged regular working file: removing
  only the gzip digest's comparison or only the mode check now fails.

D1 to D6 remain fixed. Rulings 15 and 16 stay implemented as ruled. The
acceptance criteria this code serves are met by the code and synthetic
verification: the datasets come from the reviewed builders, a rebuild
reproduces identical manifests, requests and reads stay inside the data
window, and the public index validates `BUILD.json`'s metadata. The
manifests' text stays the owner-accepted limitation, unchanged. **The
re-request and dataset build code review is closed:** the re-request and
the build may run with `5e78ab7`'s code.

**Checks that passed.** Codex's runs (`.venv312`, one process at a time, no
full suite, PAD, ETF proof or BTC-019 module): the focused modules 1,658
passed, 1 xfailed; its corrective expectations (DR1 to DR3 among them),
new metadata and git probes and retained build controls 248 passed, with
two obsolete characterizations of the old defects deselected; its retained
Part B resume and proof probes with its current controls 553 passed; its
in-memory mutants 50 of 51 caught (the survivor the record's equivalent
every-row persistence check), with an unchanged control of 261 passing.
The 48 added dataset tests are not vacuous, and no existing test or helper
changed (the diff and an AST comparison). Valid synthetic dataset files,
`BUILD.json` and index bytes match `e5051a0`'s, and its retained parity
checks against `7e4f871` pass. The request, response, read, frozen-input
and published-metadata guards held under its probes; the other adapters,
the projection, the transport and the run are unchanged. The record matches
the fixes; the real metadata check, the full suite, PAD, the ETF proofs,
the V5 hash and the BTC-019 gate were not re-observed.

Next: the owner's re-request run (`ohlcv-missing-hours`) with the reviewed
code `5e78ab7`; then the build, its verification, the private commit, and
the index, written only after `verify` passes and committed publicly after
the owner reviews its diff.

### RBT-003 Part B re-request run, dataset build and index

**Status:** `DATASET BUILT, VERIFIED AND INDEXED (2026-11-11)`, on the
reviewed code `5e78ab7`. Value-free record: no collected value and no count
of executions, liquidations or ETF rows.

- **Re-request (owner ruling 15).** The owner ran `ohlcv-missing-hours
  --keep-going` through a launcher on a clean detached worktree at
  `5e78ab7`. Both units, `bitfinex` and `coinbase`, completed (`DONE`), in 7
  and 5 requests. Every response was HTTP 200 with an empty list: neither
  venue holds a candle for any of the hours. No row was persisted, and all
  27 scheduled hours (16 Bitfinex, 11 Coinbase) stay preserved gaps, listed
  in each unit's summary as still missing. Each unit requested exactly its
  venue's scheduled hours.
- **Build.** `dataset_build build` ran from the same clean worktree, so
  `BUILD.json` names the code commit `5e78ab7`. It used one read-only,
  repeatable-read connection from the environment's variables (no URL
  printed). It verified 1,893 completed units:
  - Binance: funding 72, open interest 64, perpetual volume 72, basis 1;
  - Kraken liquidations 1,680;
  - CoinGlass ETF 1;
  - Coin Metrics 1;
  - the re-request 2.

  It read the nine series bounded to the data window and wrote the nine
  frozen input files, the five manifests and `BUILD.json`. The 14
  disagreeing Kraken hours are withheld (owner ruling 16). The manifests'
  SHA-256 digests:
  - shared snapshot
    `a59ff0ebf8a0c50441b76042d3ed685c31c06313846dec9a761d9b70c26c2145`;
  - Bitstamp venue
    `aeec209c8d64ec828a384af40c771f2a1a7a729110ff2da7f51abc33ce26422a`;
  - Coinbase venue
    `c1155e0212527d2dc7dd8ff86f1cb31964ca0fa309a177bd2d8199e2c5e414f1`;
  - Bitfinex venue
    `1aea6b2627352cc6cb15734591134c1a2f97dd94ad8e4b56aa7e01e2f45b872d`;
  - extended snapshot
    `04d664f4c1c05a7cde5009607d53fdba7bebb7b2cbce4fd23f1a3a50d3c6cf85`.
- **Verification.** `dataset_build verify` passed every check.
  - Against the database: the evidence is unchanged, the manifests rebuild
    identically from the frozen inputs, and the inputs and manifests rebuilt
    from a fresh database read match the stored ones.
  - With `--no-database`: the evidence is unchanged and the manifests
    rebuild from the frozen inputs.

  Re-running the build from the database therefore reproduces identical
  manifests.
- **Private commit.** `f36ad14` in the private evidence repository (owner
  ruling 9), pushed. It holds the two re-request units and the dataset
  directory `research_backtest_v1/datasets/rbt003_v1` (`BUILD.json`, the
  inputs and the manifests). Its working tree is clean, ignored files
  included.
- **Index.** `index` ran only after `verify` passed, from the main checkout
  at `38e6c5a`, whose code is identical to `5e78ab7`. It wrote
  `backtest_evidence/research_backtest_v1/rbt003_replay_dataset_index_v1.json`,
  bound by its private-commit proof to `f36ad14`, whose tree holds exactly
  the dataset's files as stored.
  - The implementer's check: every date lies inside the data window except
    two instants equal to its end, `2026-01-01T00:00:00+00:00`: the
    window's exclusive bound, and the Coin Metrics market cap's last
    observation. That observation is day 2025-12-31's end-of-day value,
    stamped `D+1 00:00` by the V2 builder (`market_cap_observation_time`,
    RBT-002's pinned stamp). The builder admits a day only when its whole
    span lies in the window, and a 2026-01-01 day refuses. (Corrected by the
    closure review's C1: this record first said the end appeared only as
    the window's bound.) Its
    numbers are only gap and missing-slot counts, file sizes, unit counts,
    gap lengths in seconds and the gzip settings: no market value and no
    row count of any series.
  - The owner reviewed the index and approved it before this commit
    (2026-11-11).

**Acceptance criteria.**
- The collection used the existing collectors and protocols through new
  adapter modules, with no collector, schema or migration change.
- Every persisted row keeps its provider, source and ingestion provenance.
- The frozen per-venue and shared replay datasets come from the RBT-001
  builders. Their manifests sit in the private repository's
  `research_backtest_v1/` (owner ruling 9), indexed publicly under
  `backtest_evidence/research_backtest_v1/`.
- A rebuild from the database reproduces identical manifests.
- Nothing outside the data window was requested.

The holdout is NOT COLLECTED, and BTC-019 and its sealed sample stay
untouched and unopened.

Next: RBT-003's closure.

### RBT-003 closure review outcome

**Date:** 2026-11-11.

**Review:** the independent xHigh closure review of RBT-003, which the
owner asked for before DONE.
- **Reviewer:** the OpenAI Codex CLI, in the same session
  (`01a1a849-79f7-7e90-a3f2-73727c6b1c35`), in its worktree recreated at
  `98d8e14`.
- **Scope:** `38e6c5a..98d8e14` (the public index, the run's record and
  `CURRENT_STATE.md`). Its authority was the code at `5e78ab7` and the
  whole RBT-003 block.
- **Report-only:** a workspace-write sandbox with network disabled; no
  database, no `.env*` file and no read of the private evidence
  repository; neither command line run from a shell; no collection or
  build touched. Its worktree stayed clean.

**Result: PASS WITH NON-BLOCKING FINDINGS.** One P3, C1, CONFIRMED; no
owner question. The reviewer: RBT-003 may be marked DONE with C1 corrected.

**The index and the record.**
- **No code change after the reviewed code:** `git diff
  5e78ab7..98d8e14 -- btc_predictor` is empty, and the later commits touch
  only documentation and the index.
- **The index is what the reviewed writer produces:**
  - canonical JSON whose fields and types match the writer, compared field
    by field with a synthetic index;
  - the full code commit `5e78ab7e40d520be66a99a980f18dcade867d41e` and
    the private commit `f36ad14edcdfae0dd0d805aaace216e6d0bb9bea`;
  - the window and the reader's series as the code defines them.
- **Evidence:**
  - the eight sources' unit counts and first and last units equal their
    schedules, 1,893 units;
  - the still-missing hours equal both venues' whole re-request schedules;
  - the 14 withheld hours pass the metadata checks, match the owner's
    published list and equal the hour evidence's gap census.
- **Manifests and coverage:** the five manifest digests match the record's
  labelled entries and their file bindings; gap methods, totals, span
  lengths, calendars and bounds are consistent.
- **Value-free:** every number is permitted metadata. There is no market
  value and no count of executions, liquidations or ETF rows.
- **The record matches the commands:** clean-commit enforcement,
  `verify`'s four checks (two with `--no-database`) and the private
  commit's file binding behave as described, apart from C1. Nothing public
  contradicts the empty re-request responses.
- **Not re-observed:** the private payloads, the raw responses, the private
  commit's contents and the live verification. The public metadata is
  consistent with them.

**Acceptance criteria:**
- **The existing collectors and protocols:** met. The ticket's code adds
  modules and tests, with no collector, schema or migration change.
- **Provenance kept:** met.
- **The frozen per-venue and shared datasets through the reviewed
  builders:** met on the closure evidence, as owner ruling 9 places them:
  nine inputs and five manifests in the private repository, bound by the
  public index.
- **Identical manifests on a rebuild from the database:** met on the
  closure evidence, with the synthetic rebuild regressions passing.
- **Nothing outside the data window requested:** met under the owner's
  rulings, including CoinGlass's reviewed projection.

Every required code review is closed and every blocking finding is fixed.
R12-10 and the manifests' text stay owner-accepted limitations.

**Finding.** The location is the run's record above.

| ID / severity | Location | Defect | Correction |
| --- | --- | --- | --- |
| C1 / P3 | `research_backtest_track_v1.md`, "RBT-003 Part B re-request run, dataset build and index", the implementer's check | The record said 2026-01-01 appears in the index only as the window's exclusive bound. It is also `coverage.extended_snapshot.BTC_MARKET_CAP.series[0].last_observation`, `2026-01-01T00:00:00+00:00`: the reviewed builder stamps day D's end-of-day value at `D+1 00:00`, so this is day 2025-12-31's value. A synthetic 2025-12-31 observation reproduces the field, and a 2026-01-01 source day refuses with `HOLDOUT_RECORD_REFUSED`. | The sentence is corrected above. The index and the dataset are unchanged. The implementer confirmed the stamp in `replay_inputs_v2.market_cap_observation_time` and in the index. |

**Holdout and prohibited windows.** A recursive calendar scan found only
those two boundary instants. Every other date, instant and gap span lies
inside the window. Synthetic boundary probes confirmed that the market
cap's stamp is the last admitted source day and that a holdout source day
refuses. No prohibited, holdout or reserve value is exposed, and no sealed
artifact was opened.

**Checks that passed.** Codex's runs (`.venv312`, one process at a time,
no full suite, PAD, ETF proof or BTC-019 module):
- the focused modules: 1,658 passed, 1 xfailed;
- its closure probes with its retained metadata probes: 97 passed. These
  cover the canonical format, the schedules, the digest labels, the
  coverage arithmetic, the value-free fields, the window bounds, the
  comparison with the synthetic writer and single metadata corruptions;
- the git checks and `git diff --check`: clean.

**Owner decisions (2026-11-11, asked; the recommended options):**
- a Codex closure review before DONE;
- after its PASS WITH NON-BLOCKING FINDINGS, correct C1 in this record and
  close RBT-003 without a further review.

**RBT-003 is DONE (2026-11-11).**
- **Part A:** the offline adapters `1427053`; review closed by the third
  re-review on 2026-11-05.
- **Part B code:** `3301b16`..`4cf0993`; review closed by the fifth
  re-review on 2026-11-07.
- **The rulings' code reviews:**
  - ruling 12's, closed on 2026-11-09 with R12-10 owner-accepted;
  - ruling 13's, closed on 2026-11-09;
  - ruling 14's, closed with the R14-1 re-review on 2026-11-10.
- **Collection:** every Part B source, with the private evidence in
  `76496db` and `b00e885`.
- **Rulings 15 and 16;** the re-request and dataset build code `7e4f871`,
  with its fixes through `5e78ab7`; review closed by the second re-review
  on 2026-11-11.
- **The dataset:** built at `5e78ab7`, verified, committed privately at
  `f36ad14` and indexed publicly in `98d8e14`.

No real-data outcome was produced. The holdout is NOT COLLECTED, and
BTC-019 and its sealed sample stay untouched and unopened.

Next: RBT-006 (READY).

## RBT-004 — `COMPOSE_CHAMPION_ENTRY_DECISION_V1`

**Status:** `DONE — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS (2026-10-31); review-fix 514449c, non-blocking fix 6318234; review FAIL 2026-10-31; implemented Part A 8ce3e74, Part B 910dec7 + e158de9 (2026-10-25); completion spec rebound 787ddfa2...ca2620f0, inventory 250f9470...a061cb17`
**Dependencies:** RBT-002A independent review PASS (SATISFIED, 2026-10-03). Without the spec, every
composed Entry Conviction is structurally incomplete.
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

**Completion-spec obligations (RBT-002A, recorded 2026-10-03; binding once its
review passes).** `CHAMPION_COMPLETION_SPEC_V1`
(`backtest_evidence/research_backtest_v1/champion_completion_spec_v1.json`)
fixes what this composer must do for the 26 owner-less inputs:
- **Rules.** Each input's rule, helpers and accounted §5A.6 causes are given
  per entry.
- **Census roots to promote** before any direct call:
  `features.rolling.rolling_zscore`, `rolling_percentile`, `true_ranges`;
  `features.momentum.price_momentum_from_daily_bars`;
  `quant.transforms.normal_cdf_score`; `quant.comparisons.decision_greater_equal`;
  `data.ohlcv.next_bar_timestamp`; `features.positioning._futures_basis_averages_by_time`
  and `_futures_basis_history`; `features.positioning._funding_averages_by_time`,
  `_funding_average_history`, `_aggregate_open_interest_by_time`,
  `_open_interest_growth_by_time` and `_oi_growth_history` (14 total).
- **Declared arithmetic.** It is the complete list of arithmetic the spec allows
  beyond owner calls; "no new formulas" admits exactly that list.
- **E1 guard.** `FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1` (policy V6 §6A.9)
  specifies the futures-basis zero-variance guard, its five tests and its
  prohibitions. Policy V7 §6A.9 extends the guard to `funding_health` and
  `open_interest_growth_health`; the spec's contract is updated within
  RBT-002A, V7 conformance commit `700b924`; all three owner-specific contracts
  are frozen in `positioning_zero_variance_guards`, each with five required tests.

Acceptance criteria:

- **No new formulas.** Every numeric value comes from an owner call. Review
  verifies there is no restated threshold, weight or transform.
- **Census call boundary.** A static alias-resolving call census and runtime
  direct-caller check across deterministic fixtures must prove that every
  decision owner function directly called by the composer is a census root.
  Unresolved owner callback/dict/getattr/partial dispatch is refused. Explicitly
  classified input/raw constructors and type-bound evidence serializers may be
  separately allowed; owner output records come from roots. Promote and classify
  any completion-spec helper before calling it, regenerate/review the inventory,
  and add a mutation test introducing a new direct internal-helper call.
- **Basis zero variance.** Enforce the re-review's composer-side constant-prior-
  history refusal using the owner's PIT aggregation/history outputs, with no
  restated z-score. Promote directly called helpers into the census. Record
  structural unevaluability and no health/z value, with deterministic constant,
  nonconstant and PIT boundary regressions.
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
- **Composer-root guard (policy V6 §5A.6).** Every owner function the composer
  calls directly is a census root. This is checked statically and at runtime,
  with a regression in which a newly added direct call fails.
- **Runtime completeness guard (V6 §5A.6).** In every fixture replay, any owner
  result that is incomplete or carries a missing-input reason code maps to a
  cause accounted for in the reviewed inventory or the completion spec. An
  unaccounted one fails the test.
- **Frozen basis defect.** `positioning.futures_basis_health` returns
  `complete` with z = 1 on a constant history (RBT-002 re-review). The
  composer refuses a constant owner basis history with an equality guard on
  owner outputs, without restating the z-score, and records the refusal.
- **Positioning zero-variance guard (policy V7 §6A.9).** The same exact-equality
  guard applies to `funding_health` and `open_interest_growth_health`. Each
  refuses with its owner's own reason code (`FUNDING_HEALTH_ZERO_VARIANCE`,
  `OI_GROWTH_ZERO_VARIANCE`). Each owner gets the five required tests. Every
  history helper the composer calls is promoted to a census root.

### Implementation Notes

**Status:** `IMPLEMENTED / AWAITING INDEPENDENT xHIGH REVIEW` (2026-10-25). The
required independent xHigh ticket review follows separately; this block is the
implementer's record, not a closure.

**Commits:**
- Part A, `8ce3e74` (2026-10-03): census roots, classified input sources,
  re-measured coverage, offline inventory regeneration and spec rebind.
- Part B, `910dec7`: `btc_predictor/research_backtest/entry_composer.py` and
  `composer_boundary.py` (new), the fixtures `rbt004_composer_fixtures.py`,
  eight `test_research_backtest_entry_composer*` modules, and one RBT-002 test
  narrowed to name the composer (below).
- Part B follow-up, `e158de9`: the Setup B reclaim freshness test on a natural
  reclaim (test only; no production change).
- Docs, `1b0d83d`: this block, the tasks table and `CURRENT_STATE.md`.
- Review-fix, `514449c` (2026-10-31): findings F1-F4 and F6 of the review below,
  and F5's pinning test.
- Non-blocking fix, `6318234` (2026-10-31): re-review findings N1 and N2; the
  statements below are current after it.
- RBT-005 Part A, `0856352` (2026-11-01): the composition hand-off to the
  management composer (see the RBT-005 notes); behaviour-preserving, entry
  ledgers byte-identical.

**Digests (RBT-002 E3 rebind):**

| Artifact | Before | After |
| --- | --- | --- |
| Inventory `rbt002_input_coverage_inventory_v1.json` | `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` | `250f9470b0586f091744c65bcb3d7e48c25ec4fe01ec7bcc79a9fda1a061cb17` |
| Spec `champion_completion_spec_v1.json` | `9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f` | `787ddfa26391a1956ed8ee92209308b95797536e0906844d9811f9e8ca2620f0` |

- **Rebind proof** (`rbt004_spec_rebind_evidence_v1.json`): 2,327 leaves with
  identical paths. Exactly two leaves changed, `bound_inventory.sha256` and the
  inventory citation text, each only by the inventory digest. Every entry,
  rule, guard, cause and warm-up fact is byte-identical; every other top-level
  section keeps its hash. The coverage test still covers exactly 26 entries.
- **Inventory regeneration**: `coverage rebuild` from its own snapshot, sockets
  refused. Only the input-surface census, rows and summary changed: 46 root
  rows added, 27 internal rows removed, 36 provenance-only changes. No new
  external input; the owner-less set is identical.
- Both artifacts rebuild byte-identical under `PYTHONHASHSEED` 0, 1 and 8675309,
  from an alternate working directory, in fresh processes with network
  connections refused (re-checked 2026-10-25).

**Census roots (Part A).** 74 → 88 `DECISION_PATH_ROOTS`: the 14 spec section 8
helpers (`features.rolling.rolling_zscore`, `rolling_percentile`,
`true_ranges`; `features.momentum.price_momentum_from_daily_bars`;
`data.ohlcv.next_bar_timestamp`; the seven positioning history helpers;
`quant.transforms.normal_cdf_score`; `quant.comparisons.decision_greater_equal`).
Every new parameter maps to a spec-declared value (new kind
`COMPLETION_SPEC_VALUE`: `window=len(H)`, minimum 20, `sample=False`; percentile
`window=len(H)`, minimum 365; `lookback_periods=7`; the Flow Supportive 60), a
fixed owner default, or an input the inventory already enumerates. The three
`CLASSIFIED_INPUT_SOURCE` helpers (`replay_market_bars_at`,
`build_shared_replay_snapshot`, `load_closures`) stay non-roots with classified,
drift-checked parameters. The registry has 888 callables, 230 nested and 159
types; coverage is re-measured for 88 roots
(`rbt004_census_coverage_evidence_v1.json`). RBT-004 calls 12 of the 14 directly;
`normal_cdf_score` and `decision_greater_equal` serve RBT-005's Hold/ADD inputs.

**Owner rulings (2026-10-03, asked under the ticket's STOP rule; the
recommended option each time).** No Rulebook, policy or spec text fixed these
composition points:

1. **Entry zone.** The `ARM_ENTRY` zone is the point `[P_t, P_t]`. `P_t` is the
   close of the hourly bar that closes at the decision instant, and the owner's
   initial stop has `entry_price == P_t`. The next bar fills only if it trades
   through `P_t`; otherwise the entry is `MISSED`.
2. **Setup C.** CAPITULATION reaches Setup C through the V4 mapping (`flagged`
   when the only missing input is the DISCRETIONARY `systemic_shock`; `None` if
   any other input is missing), with a 14-day (`max_confirmation_lag_days`)
   episode memory. `capitulation_detected_at` is the first instant of the
   consecutive flagged run.
3. **Data quality.** The last completed UTC day: the venue's hourly bars over
   `[t - 24h, t - 1h]`; funding, OI and perp-volume rows observed in
   `(t - 24h, t]`; the BTC-031 owner default configurations.
4. **No stop.** When no long archetype yields a complete initial stop, a data
   cause (`STRUCTURAL_INVALIDATION_INPUT_MISSING`,
   `VOLATILITY_BUFFER_INPUT_MISSING`, `INITIAL_STOP_INPUT_MISSING`) gives
   `STRUCTURALLY_UNEVALUABLE`; otherwise the cause is geometry, giving
   `NO_TRADE / NO_VALID_STRUCTURAL_STOP` (when Structure is the only incomplete
   component).
5. **Setup clash.** Setup C with A or B gives `NO_TRADE /
   SETUP_GEOMETRY_CONFLICT`. A and B share one geometry and trade once,
   labelled A.
6. **Triggers fire fresh at the decision instant.** Setup B: the latest reclaim
   level detected by `t`, true only when its trigger confirmed with
   `detected_at == t`, `None` while pending, otherwise false. Setup C: the latest
   weekly swing low's higher-low trigger, with `confirmation_at = R.detected_at`
   and `detected_at == t`; `HIGHER_LOW_SOURCE_BAR_MISSING` gives `None`.
7. **Setup B histories use native cadence**: funding and OI health at the prior
   daily instants, recomputed by the owners (with the guard); FlowAccel at the
   prior US publication days.
8. **Accepted composition defaults**, each a design decision for the review:
   level families are weekly and monthly swings plus breakout/reclaim levels
   (Rulebook 9.4's Phase-1 list; no volume-profile or AVWAP members);
   `cluster_atr=None`; R/R references are resistance clusters, weekly swing
   highs and breakout/reclaim levels as range highs, with no measured move; the
   no-chase zone is the invalidation-selected support cluster; veto booleans are
   `X if complete else None`; the V4 STRESS mapping covers the veto and Setups A
   and D; decisions run at 00:00 UTC; the liquidation percentile is a typed
   point-in-time input; EC below 80 is `NO_TRADE`; breakout-retest is not called
   (no setup consumer); Setup D is called with inert inputs and never trades.

**Composition order** (`_DecisionRun.run`; the ticket's steps 1–6 in the order
the owners' inputs force):

0. *Point in time.* Only replay inputs with modelled availability `<= t` are
   read: hourly bars by `ingested_at` (the RBT-001 modelled availability),
   shared rows by `available_at`, the owners' own two-field predicate for the
   guards. `replay_market_bars_at` derives the 1d/1w/1mo bars. `P_t` is the
   close of the hourly bar closing at `t`; without it the instant is
   `STRUCTURALLY_UNEVALUABLE / DECISION_INSTANT_PRICE_BAR_MISSING`.
1. *Components.*
   - Trend: momentum, MA-distance, 52-week-high and weekly-structure owners;
     `UNIFORM_ZSCORE_V1` on each native series; `calculate_trend_score` only
     when all four z-scores and the structure score exist (the owner has no
     `None` path).
   - Flow, `ETF_CORE` with CVD absent: D is the owner's own latest visible
     publication date; the publication calendar is paged from the owner's
     `included_observation_dates`; every window passes the funds launched by its
     first included publication date and the loaded
     `US_EQUITY_MARKET_CLOSURE_TABLE_V1`; the three z-scores follow
     `UNIFORM_ZSCORE_V1` over prior publication days.
   - Positioning: `funding_health`, `futures_basis_health`,
     `open_interest_growth_health` (USD) behind the three §6A.9 guards, plus
     `open_interest_intensity`.
   - Volatility: RV 7/20/60, `volatility_percentile` over the RV_20 history,
     compression, orderliness from `RANGE_PERCENTILE`, `DOWNSIDE_RETURN` (R_7)
     and the last completed UTC day's `LIQUIDATION_PERCENTILE`.
2. *Regime and flags.* Core regime (macro and on-chain declared unavailable:
   `CORE_MARKET_ONLY`), smoothing from the previous ledger row's smoothed score,
   classification (persisted on every row as RBT-005's `K_entry`); STRESS,
   CROWDING (`SEVERE_CROWDING_STATE = flagged if complete else None`),
   CAPITULATION and EUPHORIA, with every DISCRETIONARY input `None`.
3. *Geometry, then Structure.* For A, B and C: clusters → invalidation
   (NEAREST for A/B, FARTHEST for C) → volatility buffer → initial stop →
   BTC-143 R/R. The structure owner needs a stop, so Structure follows: its own
   support selection, the spec's level inputs (`LEVEL_REACTION_MAGNITUDE`,
   `LEVEL_VOLUME_PERCENTILE`), level strength, then the score per complete stop
   (STRUCTURE_SCORE_V1_2 is stop-independent; a difference is a composer
   defect).
4. *Entry Conviction and band*; an incomplete EC is `STRUCTURALLY_UNEVALUABLE`
   with each incomplete component and its accounted causes (or ruling 4's
   `NO_TRADE`), whether or not a position is open. An open position replaces
   only a complete decision, with `NO_TRADE / POSITION_ALREADY_OPEN` after the
   regime chain and flags.
5. *Setups and gates.* Triggers, the four detectors, the clash rulings; then
   no-chase, the hard veto (with `DATA_QUALITY_FAIL`) and the data-quality gate.
6. *Intent.* `BacktestIntent(ARM_ENTRY, long, [P_t, P_t], initial stop, EC)`;
   the composer refuses a stop whose entry price, direction or identity
   disagrees with the decision.

**Decision ledger (`CHAMPION_ENTRY_DECISION_LEDGER_V1`).** One
`EntryDecisionRow` per daily instant: `decision_at`, `venue`, `outcome`
(`ARM_ENTRY`, `NO_TRADE`, `STRUCTURALLY_UNEVALUABLE`), `reasons`, `position_open`,
`setup`, `detected_setups`, `entry_conviction`, `entry_action`, `regime`
(model, score, smoothed, previous smoothed, classification, complete),
`components` (five, `None` when incomplete), `flags` (STRESS/CROWDING/
CAPITULATION/EUPHORIA with the mapped values and reason codes), `unevaluable`
(component → accounted causes), `guard_refusals`, `owner_reason_codes` (every
consumed owner result: feature id, completeness, reason codes), `unaccounted`,
`features` (the 33 BTC-048 columns), `data_quality` (window, failures, gate),
`intent`, `input_reason_codes` (the reason codes a typed replay input carried
for the record visible at `t`, as provenance: today the liquidation
percentile's), `capitulation_flag_state`. Nothing is zero-filled: a missing
value is JSON `null`. `ledger_bytes()` is canonical JSON with a header naming the ledger,
composer, research strategy id, spec version and digest, champion identity,
venue and closure table. `decide()` is engine-agnostic (Rulebook invariant 15);
`__call__` is the BTC-180 adapter.

**Positioning guards (policy V7 §6A.9, the three frozen contracts).** When the
owner result has a z-score, the composer rebuilds the owner's own prior history
from the visible rows with the promoted helpers, asserts
`len(H) == history_observation_count` and the owner's latest observation time,
and refuses an exactly constant `H` (`all(h == H[0] for h in H)`, Decimal, no
tolerance) with the owner's own code. A refusal passes no health score or
z-score to any consumer and records a `GuardRefusal` (guard, owner, code,
history count, observation time, and the per-field `withheld_inputs` of clause
6, which attributes each downstream `None` to the guard's cause). Positioning
is then `STRUCTURALLY_UNEVALUABLE` with that accounted cause. An owner's own
refusal stands unchanged. The Setup B prior-instant health histories apply the
same guard at each instant.

**Census boundary (RBT-002 E4, §5A.6; `composer_boundary.py`,
`COMPOSER_CENSUS_CALL_BOUNDARY_V1`).** The static alias-resolving census of the
composer finds 0 refusals: 65 roots, 2 classified input sources, 18 classified
constructors (the composer-facing owner input types, each classified field by
field, and `BacktestIntent`), the `run_metadata` accessor, `as_record`
serializers and the EPIC Y `canonical_json_bytes`/`sha256_hex`. Refused: a
non-root owner function, an unclassified owner constructor, any callable held in
a local, container or subscript, `getattr`/`partial`/`operator`/`importlib`/
`eval` dispatch, an owner callable used as a value, and any binding the module
namespace does not show (a function-local import, `global`/`nonlocal`, a local
binding, dunder-named or not, shadowing a module-level or builtin callable, an
assignment to a name the census trusts for an unresolved method call, and any
dunder attribute except a `__name__`/`__qualname__` read and
`super().__init__`). The runtime
direct-caller profile over the warm-up, `NO_TRADE`, `ARM_ENTRY`, guard-refusal
and BTC-180 engine paths finds no violation, and every static root is
exercised there except, at most, `evaluate_reclaim_trigger` (called only when a
reclaim level exists; its freshness rule is tested separately, on a natural
reclaim). The
composer reads a replay record's `available_at` and `observation_time` through
its `as_record`, exactly as the positioning owners' inline predicate does.

**Runtime completeness guard (§5A.6).** `CAUSE_ACCOUNTING` (113 entries) maps
every reason code the composition can emit to a spec entry's accounted cause, a
spec guard, an inventory row whose missing behaviour names it, or an inventory
minimum-history input; a test verifies each against the bound artifacts. Every
consumed and auxiliary owner result is checked: an incomplete result needs an
accounted code, and any missing-input code must be accounted. Every fixture
replay in the eight modules asserts `unaccounted == ()`, except one test that
pins the owner-accepted `VOL_COMPRESSION_ZERO_DENOMINATOR` of exactly constant
closes, one case of a zero 60-day realized volatility, as unaccounted (review
F5); injected unknown codes are reported.

**Design decisions beyond the rulings (for the review).**
- *ETF anchor and calendar pages.* D comes from one owner call with
  `end_date=None`, and the calendar from 20-day owner windows; both run without
  a fund list and their window values are never consumed, so the anchor is
  audited with the auxiliary results, not ledgered.
- *Setup C unknowns.* An instant with no ledger row, or a `None` flag state, is
  unknown, never "not flagged": with no flag in the window an unknown gives
  `None`; a run preceded by an unknown instant has no determined start, so
  `capitulation_detected_at` is `None` and the detector reports its input
  missing (it trades less). The first 14 days of any ledger therefore cannot
  confirm Setup C.
- *Liquidation percentile.* Only the UTC day ending at `t` (an `INTERVAL`
  value modelled available at its end, §4); an older day is never substituted.
- *Engine adapter.* A decision instant strictly between two engine callbacks
  (no bar closes at it) is recorded at the first callback after it as the
  missing-bar row, with the position the previous callback reported, which is
  the position at that instant; this holds at the start and the end of a run,
  and engine callbacks must strictly increase (review F1/F2). A skipped
  midnight whose decision bar the composer can see is a `COMPOSER_DEFECT`
  rather than a silently dropped decision. Hourly availability must be
  nondecreasing in bar order. A missing-bar row keeps the ledger schema, and the
  regime chain then re-seeds under the owner's own missing-previous handling.
- *VOL_PERCENTILE history.* RV_20 is computed only for daily bars inside a
  superset of the owner's own default window (plus one day); the owner selects
  its history, and parity with the full history is tested.
- *RBT-002 test.* `test_no_production_code_produces_the_owner_less_entry_inputs`
  now exempts exactly `research_backtest/entry_composer.py`, stays strict for
  every other production module, and asserts the composer contains each
  pattern.

**Tests (eight modules, 197 tests, all passing; four added by RBT-005 Part A).**

| Module | Proves |
| --- | --- |
| `…_guards` | per owner: the frozen owner's complete z on a non-terminating constant; the five required tests (constant, current equal, current different, point-in-time exclusion of rows observed or available after `t` and of another OI unit, non-constant pass-through); no downstream health/z and per-field attribution; CROWDING/STRESS fail closed; exact-equality without tolerance; no restated z; owner refusals stand; the Setup B history guard; an open position keeps each guard's structural refusal (F3); `UNIFORM_ZSCORE_V1` (0.1, 1/3, 0.015·365/90 at 20 and 730 observations, both accumulator widths, the 64-bit counterexample, no helper call on refusal, gaps, last-20 selection, parity) and `UNIFORM_PERCENTILE_V1` (time window boundaries, minimum, missing) |
| `…_boundary` | the static census, allowed constructors/accessors/value methods, traced runtime calls on every outcome path, static/runtime agreement, and mutations (direct helper, alias, module attribute, getattr, dict, partial, callback, local alias, unclassified constructor, importlib) that fail statically and at runtime; the review F4 bindings (function-local import, local assignment shadowing a root or a builtin, a shadowing parameter, `global` rebinding, a trusted method name rebound) fail statically, as do the re-review N1 forms (a dunder-named local shadowing a root, a trusted name rebound through `self.__dict__` or `object.__setattr__`) |
| `…_flow` | every ETF window gets the loaded closure table; the listed-holiday window is complete with it and `ETF_FLOW_INPUT_MISSING` without; the per-window fund universe; pre-launch windows never invented; an unrecorded fund is refused; independent z recomputation over publication days; `ETF_CORE` with CVD absent; Setup B's native FlowAccel history; a late revision never changes `t` |
| `…_pit` | the point-in-time property over four seeds and every family, including an armed entry, with converse controls |
| `…_entry_composer` | one row per instant; nothing zero-filled; canonical, deterministic ledger (two composers; fresh processes under three hash seeds from another cwd); decision API refusals; the engine adapter at midnights; missed-midnight backfill and the skipped-bar defect; engine-prefix independence; cause accounting against the artifacts and injected unknown codes; identity and input refusals; liquidation handling and its producer reason codes as provenance (F6); the owner-accepted unaccounted compression code of constant closes (F5); missed midnights at either end of a run (F2) and strictly increasing callbacks; regime chaining; open positions; the Setup C episode cases |
| `…_archetypes` | Setup A arms end to end (point zone, owner stop, EC, `K_entry`) and fills through BTC-180; NEAREST/FARTHEST geometry; A+B trades once as A; B reaches the gates on its own geometry (no-chase veto); C arms on its episode and FARTHEST zone with STRESS mapped but non-blocking; C with A is a conflict; Setup D inert, never short; higher-low freshness on real owner output; reclaim freshness on real owner output (one natural reclaim: pending `None`, fresh `True`, stale `False`); a missed midnight keeps the open position a later stop ends (F1) |
| `…_vetoes` | the `HardVetoInput` mapping and V4 STRESS evidence; STRESS fail-closed and non-blocking config; derivatives and OHLCV `DATA_QUALITY_FAIL` (veto and gate, window bounds); no-chase; the R/R filter and no-reward-reference cause; severe crowding against A and as a veto for B; EC below band; no-stop geometry (`NO_TRADE`) and data cause (`STRUCTURALLY_UNEVALUABLE`) |
| `…_parity` | BTC-048 column order, matrix reproduction, batch Entry Conviction equal to each single score, and 25 single-owner features equal to direct owner calls |

*Input interventions.* A smooth synthetic market does not produce a fresh
reclaim, or a 12 % capitulation, together with EC >= 80 and R/R >= 2 (an offline
scan of 48 parameter sets and 13,440 decisions found natural Setup A entries, 83
fresh higher-low confirmations with Setup C R/R at most 0.74, and one fresh
reclaim with every other Setup B condition failing, which the reclaim freshness
test uses without intervention). The B and C fixtures
therefore substitute only named inputs at named instants and always call the
real owners: `BullishResetInput.entry_trigger_confirmed`;
`CapitulationFlagInput` values at three earlier instants (the composer's own
mapping, ledger and episode do the rest); the higher-low result's `triggered`
and `detected_at` (the composer's freshness rule then confirms);
`StressFlagInput` (to make Setup A ineligible); `CapitulationReversalInput` for
the C-with-A clash; and `CrowdingFlagInput` for severe crowding.

**Validation (2026-10-25, `.venv312` CPython 3.12.14).**

- Composer: the eight `test_research_backtest_entry_composer*` modules
  together, **174 passed** in 1151s (guards 65, core 32, boundary 28, vetoes
  13, flow 12, archetypes 9, point in time 9, parity 6). A first combined run
  exposed a test-isolation leak (an intervention patch entered before the
  recording context restored a recording wrapper into the composer
  namespace); the context order is fixed and the boundary test now names any
  such leak. The follow-up reclaim freshness test (`e158de9`) then passed with
  the archetypes and boundary modules together (**38 passed**: archetypes 10,
  boundary 28), and two crude substitutes of the composer's rule (a stale
  confirmation counted as True; a pending one as False) each fail it.
- Other EPIC Y suites (census, nine traces, coverage, spec, spec review,
  database, replay, RBT-001): **659 passed, 1 known frozen-basis XFAIL**;
  RBT-001 alone **167 passed**.
- Closure table **145**; BTC-180..185 **282** (the recorded eight modules; 330
  with `test_backtest_parameter_surfaces`); BTC-220..224 including the golden
  scenarios **342**; owner modules **320**; all passed.
- Full repository (alone, `-W error::RuntimeWarning`) at `e158de9`:
  7,508 passed, 3 skipped, 1 xfailed, 0 failed in 4124.31s.
  Collected tests 7,309 at `15c235f` -> 7,512: the 175 composer tests plus 28
  in Part A's census, trace and spec tests. A first full run, at `910dec7`
  with an uncommitted draft of the reclaim test whose instants were wrong (one
  never reached the setups and none confirmed), gave 7,507 passed, 3 skipped,
  1 xfailed and that draft's 1 failure; the corrected test is `e158de9`.
- EPIC X V5 definition recomputes to
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`; PAD5
  preserved-authority subset **5 passed, 112 deselected** and PAD4-R5 **2
  passed**, each run alone.
- Inventory (three artifacts) and spec rebuild byte-identical under
  `PYTHONHASHSEED` 0, 1, 8675309, from an alternate cwd, in fresh processes
  with network connections refused: `250f9470...a061cb17`,
  `787ddfa2...ca2620f0`.
- `compileall -q btc_predictor etf_calendar_worker` and `git diff --check` PASS.
- An offline exploratory scan of 48 `trending_close` parameter sets (13,440
  synthetic decisions) found no unaccounted cause; it chose the fixtures and
  is not a test.

**Remaining risks and ambiguities (surfaced for the review).**
- *Spec text.* The frozen spec's `rolling_zscore` helper `use` text still says
  `min_periods=30` / `len(H) >= 30`, while the rule statement, application
  contract and elements say 20. The composer follows the controlling statement
  and contract (20); the frozen spec is not edited.
- *STRESS fail-closed branch.* Every non-DISCRETIONARY STRESS input also feeds
  an Entry Conviction component, so in composition a missing one makes the
  instant unevaluable before the veto; the fail-closed veto is proven at the
  owner level (`STRESS_NON_DISCRETIONARY_MISSING`).
- *Setup C completeness.* The owner reports `CAPITULATION_REVERSAL_INPUT_MISSING`
  whenever there is no capitulation or confirmation (their times are `None`), so
  Setup C is incomplete at nearly every instant; accounted.
- *Liquidation feed.* No producer of the typed `LIQUIDATION_PERCENTILE` exists
  yet (RBT-001A/RBT-003); the futures-basis and market-cap families also have no
  reviewed replay builder yet.
- *Accepted limitation (review F5, owner ruling 2026-10-31).* A zero 60-day
  realized volatility gives the frozen volatility owner's
  `VOL_COMPRESSION_ZERO_DENOMINATOR`, which no bound artifact names; the
  completeness guard keeps reporting it as unaccounted. Exactly constant closes
  are the pinned case; one identical daily return across the window, such as
  doubling closes, is another (re-review N2).
- *Tooling.* `coverage rebuild`'s default `--artifact` is relative to the
  working directory; the determinism check passes it explicitly.
- No real-data value, score, signal, trade or outcome was computed; no database
  connection; holdout NOT COLLECTED; BTC-019 untouched, sealed sample unopened;
  EPIC X unchanged (`POSTP1-001V2R1` remains its next ticket); no owner, config,
  EPIC X-bound, `data/` or `research_artifacts/` edit.

Recommended next dependency-satisfied ticket: the **independent xHigh RBT-004
review**; **RBT-001A** remains READY. RBT-005 stays blocked until that review
passes.

### RBT-004 review outcome

**Date:** 2026-10-31. **Review:** independent xHigh ticket review, run at the
owner's request by the OpenAI Codex CLI (0.162.1, model `gpt-6.1-sol`,
reasoning `xhigh`) in a detached worktree at `1b0d83d`, against Part A
`8ce3e74`, Part B `910dec7`, follow-up `e158de9`, documentation `1b0d83d` and
base `15c235f`. Report-only: a workspace-write sandbox with network disabled,
no database, no `.env*` file, synthetic fixtures only; its worktree stayed
clean. The session stopped once at a usage limit (2026-10-25) and was resumed
on 2026-10-31, when every interim finding was re-run.
**Result: FAIL.** RBT-004 is not DONE and RBT-005 stays blocked. No owner
ruling was reopened; no frozen owner edit or new formula is needed.

**Findings.** Locations refer to `1b0d83d`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| F1 / **P1 FIXED** | `entry_composer.py:747`, `:754` | The engine adapter backfills a missed midnight only at the next midnight callback, with the `position_open` reported just before that later midnight. A position open at the missed instant and stopped afterwards is recorded flat: the row uses state from after its decision instant. | Remove the 2024-04-01 23:00 bar from a market whose Setup A entry fills 2024-03-31 01:00 and whose stop executes 2024-04-02 13:00: the 2024-04-02 row says `position_open=False`. Backfill each crossed instant with the state known at that instant; regression: a later stop cannot change the earlier row. |
| F2 / **P1 FIXED** | `entry_composer.py:749`, `:751` | Backfill needs an earlier ledger row and a later midnight callback, so a missed midnight at the start or end of an engine run never gets a row, against one row per decision instant. | Engine run from 2024-04-07 20:00 without the 04-07 23:00 bar: the ledger has only 04-09. Run to 2024-04-09 05:00 without the 04-08 23:00 bar: only 04-08. Process crossed midnights on every callback; regressions at both boundaries. |
| F3 / **P1 FIXED** | `entry_composer.py:882`, `:2064` | With `position_open=True` the decision returns `NO_TRADE / POSITION_ALREADY_OPEN` before the completeness decision, and `_finish` drops the component causes, so a guard refusal leaves `unevaluable` empty. The criterion requires `STRUCTURALLY_UNEVALUABLE` wherever an Entry Conviction component is incomplete. Health and z stay withheld. | Constant basis (0.015·365/90) at 2024-04-09: flat gives `STRUCTURALLY_UNEVALUABLE / POSITIONING_INCOMPLETE` with the refusal; open gives `NO_TRADE` with an empty `unevaluable`. Keep the structural status and its causes while suppressing entry; open-position cases for all three guards. |
| F4 / **P2 FIXED** (residual N1 fixed in `6318234`) | `composer_boundary.py:296` | The static census resolves every called name against module globals. A function-local import (`from btc_predictor.features.flow import _trailing_publication_dates as five_day_etf_flow`) or a local assignment reusing a root's name is classified as that root, with no refusal; only the runtime trace sees the real helper. | Either mutation inside `_DecisionRun._trend`: static refusals `()`, runtime violation `FUNCTION btc_predictor.features.flow._trailing_publication_dates`. Refuse function-local imports and local bindings that shadow module-level names; add both mutations to the static tests. |
| F5 / **P2 — owner ruling 2026-10-31: accepted limitation, fail loud** | `entry_composer.py:384` (cause accounting) | Constant closes give the frozen owner's incomplete `VOL_COMPRESSION_ZERO_DENOMINATOR`. Neither the inventory nor the spec names that code, so the completeness guard reports it as unaccounted. The guard is conservative; no unsafe score results. | Flat OHLC (100/101/99/100) at 2024-04-09: `unaccounted = ("volatility_compression:VOL_COMPRESSION_ZERO_DENOMINATOR",)`. Owner ruling: no frozen-artifact change; the code stays reported as unaccounted, a test pins that, and the limitation is recorded (it needs a zero 60-day realized volatility, of which constant prices are one case; re-review N2). |
| F6 / **P2 FIXED** | `entry_composer.py:1317` | A typed liquidation record with `liquidation_percentile=None` maps to `LIQUIDATION_PERCENTILE_INPUT_MISSING`, but the record's own reason codes are dropped: two different producer causes give byte-identical ledgers. | A 2024-04-08 record carrying `LIQUIDATION_FEED_UNAVAILABLE` or any other code. Preserve the supplied codes in the row as provenance; the missing value stays accounted under the existing cause. |

**Checks that passed.** No new formulas; the hard vetoes, archetypes and
long-only direction; BTC-048 parity; the loaded closure table and per-window
fund universe; the reusable `decide`/`record` API; the frozen-basis guard
without a restated z-score. The Setup B/C input interventions are accepted as
scoped branch fixtures using the real owners, with the natural reclaim and
higher-low fixtures verifying trigger freshness. The narrowed RBT-002 test
still refuses a mutation in another production module. Inventory and spec
rebuilt byte-identical under three hash seeds from an alternate cwd; the
rebind changed only the inventory digest and its citation. No protected path
changed. Codex's runs (`.venv312`, one process at a time): guards and boundary
93 passed; flow and parity 18 passed; archetypes, vetoes and point in time 32
passed; selected core and census contracts 36 passed, 3 deselected;
`git diff --check` clean. The full suite was not rerun.

**Distinct review-fix:** `514449c` (2026-10-31). It changes only
`entry_composer.py`, `composer_boundary.py` and four composer test modules; no
owner, configuration, spec, inventory or evidence artifact.
- F1/F2: the adapter records every decision instant strictly between two
  engine callbacks at the first callback after it, with the position the
  previous callback reported, and refuses non-increasing callbacks.
- F3: completeness is classified before the open-position check, so an
  incomplete component stays `STRUCTURALLY_UNEVALUABLE` with its causes; an
  open position replaces only a complete decision.
- F4: the static census also refuses function-local imports, `global`/
  `nonlocal`, local bindings shadowing a module-level or builtin callable, and
  assignments to the names it trusts for unresolved method calls.
- F5: pinned by `test_constant_prices_leave_the_compression_refusal_unaccounted`.
- F6: the row field `input_reason_codes` keeps the visible liquidation record's
  own codes; a record not yet available at `t` contributes none, and the
  value's accounting is unchanged.

Regressions: `test_a_missed_midnight_keeps_the_position_it_had_then` (F1),
`test_a_missed_midnight_at_either_end_of_a_run_gets_its_row` at both boundaries
(F2), `test_an_open_position_keeps_the_structural_refusal` for all three guards
(F3), six static binding mutations (F4), the F5 pin and
`test_a_liquidation_records_own_reason_codes_are_kept_as_provenance` (F6). The
F1, F2 and F3 regressions were run against `1b0d83d` and fail there; F4 and F6
test refusal codes and a field the fix adds, and their cases reproduce the
review's probes. `test_engine_callbacks_must_strictly_increase` pins the new
ordering refusal the backfill relies on (before the fix, a repeated callback
without a midnight was accepted silently). Validation: the eight composer
modules 190 passed in 1214.88s; full repository 7,523 passed, 3 skipped,
1 xfailed, 0 failed in 4239.22s (the 7,508 baseline plus the 15 new tests).

### RBT-004 re-review outcome

**Date:** 2026-10-31. **Review:** independent xHigh re-review by the same Codex
CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in its detached
worktree at `3e0571d` under the same report-only rules; its worktree stayed
clean. **Reviewed:** review-fix `514449c` and documentation `3e0571d`, against
the FAIL at `1b0d83d`.
**Result: PASS WITH NON-BLOCKING FINDINGS. RBT-004 is DONE.** F1, F2, F3 and F6
are fixed and F5 is pinned as ruled; no new blocking defect was found. RBT-005
is READY.

| Finding | Re-review status and evidence |
| --- | --- |
| F1 | **FIXED.** The March 31 entry / April 2 13:00 stop probe: the missed April 2 row now says `position_open=True` (`False` at `1b0d83d`). |
| F2 | **FIXED.** Both boundary probes now give the April 8 and April 9 rows; each loses its missed row at `1b0d83d`. |
| F3 | **FIXED.** The three open-position guard regressions pass; an independent basis probe keeps `STRUCTURALLY_UNEVALUABLE` and its causes; ruling 4's `NO_TRADE / NO_VALID_STRUCTURAL_STOP` is unchanged. |
| F4 | **FIXED for the reviewed probes**; residual N1 below. |
| F5 | **PINNED AS RULED.** The pin keeps exactly `volatility_compression:VOL_COMPRESSION_ZERO_DENOMINATOR` unaccounted; no frozen artifact changed. Its record is corrected by N2. |
| F6 | **FIXED.** Visible producer codes survive in `input_reason_codes`; a record available after `t` contributes none; the missing value's accounting is unchanged. |

Further probes: consecutive missed midnights are appended at the first later
callback; duplicate and backward callbacks fail; a skipped visible decision bar
fails before the next midnight; flat and open-position chains keep identical
features, regime smoothing, flags and Setup C episode state. The new F1, both
F2, F3, F6 and callback-ordering regressions detect the old implementation.

| ID / severity | Location (`3e0571d`) | Finding | Disposition |
| --- | --- | --- | --- |
| N1 / **P2 FIXED** | `composer_boundary.py:259` | The F4 binding check exempted dunder names: a root imported at module scope as `__root__` and rebound in `_trend` to a non-root helper gave no static refusal and was classified as `five_day_etf_flow`. Assigning a helper through `self.__dict__['_keep']` also passed statically. The runtime trace caught both. | Fixed in `6318234`: a dunder name is shadowed like any other, and every dunder attribute except a `__name__`/`__qualname__` read and `super().__init__` is refused (`REFLECTIVE_DUNDER_ATTRIBUTE`). Three static mutations (Codex's two and `object.__setattr__`) give no refusal at `514449c` and the targeted refusal after the fix. |
| N2 / **P3 FIXED** | this block, F5 record | The F5 record said the limitation needs exactly constant prices; closes `2**i` (one constant return) also give `RV60 = 0` and the same code. | The record, the accepted-limitation bullet and the composer docstring now name a zero 60-day realized volatility, with constant closes as the pinned case. No behaviour change. |

Codex's runs (`.venv312`, one process at a time): core module, open-position
guards, F1 regression, static mutations and census checks 59 passed;
archetypes, both no-stop classifications, selected point-in-time and boundary
controls 18 passed; four probe scripts passed; `git diff --check` clean. It
did not rerun the full suite. No owner question was raised.

**Non-blocking fix:** `6318234` (2026-10-31), made after the PASS as the owner
chose, without a further re-review. It changes `composer_boundary.py`, the
composer docstring and the boundary tests only; no owner, configuration, spec,
inventory or evidence artifact. It only adds static refusals; the composer's
own census stays refusal-free. Validation: the eight composer modules
193 passed in 1241.27s; full repository at `6318234`, alone:
7,526 passed, 3 skipped, 1 xfailed, 0 failed in 4295.40s.

Recommended next dependency-satisfied tickets: **RBT-005** (READY) and
**RBT-001A** (READY).

## RBT-005 — `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1`

**Status:** `DONE (2026-11-01) — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS; review FAIL fixed in 56ab0ca, f69140f and 5052cbb; N1 fixed in dddd6a6 — Part A 0856352, Part B 8fdd5a3; owner rulings 1b52760; owner review rulings 4-7 (2026-11-01)`
**Dependencies:** RBT-004
**Implementation effort:** xHigh
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/management_composer.py` (new)

The in-position half. From the hold score and lifecycle state it emits `TRAIL`,
`ADD`, `TRIM` or `EXIT` intents, or none, through the existing owners:

- BTC-156 trailing-stop progression;
- BTC-150..158 lifecycle, pyramiding and add requirements;
- exit and trim rules.

**Completion-spec obligations (RBT-002A, recorded 2026-10-03; binding once its
review passes).**
- **Inputs.** `CHAMPION_COMPLETION_SPEC_V1` defines the Hold and Add components
  and the add/exit predicates this composer consumes.
- **Add sequencing.** Evaluate an add on the lifecycle before the same instant's
  `STOP_MOVE`. One trailing-structure producer serves both the trail and
  `NEW_STRUCTURAL_CONFIRMATION`. The structure's `level_timestamp` is its own
  bar's timestamp, never a source swing's.
- **Regime invalidation.** `REGIME_INVALIDATION_PREDICATE` needs the
  entry-instant regime classification persisted in the decision ledger.

Acceptance criteria:

- The same no-new-formula, point-in-time, decision-ledger, determinism and
  census direct-call boundary criteria as RBT-004. Its own fixtures and mutation
  regression must cover the management composer as well.
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
  **Amended by owner review ruling 5 (2026-11-01):** before the RBT-006 freeze
  these are plumbing replays only (no champion value on real prices); RBT-007
  reports the decisions next to the scripted ones. RBT-005 proves the composed
  path end to end on a synthetic replay.
- The composer-root and runtime completeness guards of policy V6 §5A.6 apply
  to this composer too, with the same regressions.

**Owner composition rulings (2026-11-01, asked before implementation; the
recommended option each time).** No Rulebook, policy or spec text fixed these
points:

1. **Add with its trail.** Every add that passes comes with a trailing stop
   that advances on the same higher low, and the engine queues one intent per
   decision. At the daily decision t the add is evaluated on the lifecycle
   before the stop moves (spec `NEW_STRUCTURAL_CONFIRMATION`) and the `TRAIL`
   is emitted. At the first engine callback after the raised stop is
   installed, the `ADD` follows, carrying the requirements evaluated at t. If
   the trail is refused or held, the position closes, or its state changes
   first, the `ADD` is dropped and the reason recorded (Rulebook 26 "Raise Stop
   -> ADD"; risk stays bounded at the raised stop).
2. **One intent per decision: `EXIT` > `TRIM` > `TRAIL`/`ADD`.** An exit
   overrides everything. A trim precedes a trail or add, and an add that would
   otherwise pass is recorded as suppressed. A trail deferred by a trim does
   not consume its higher low, so it can still apply at the next decision.
3. **Unmodelled add and reduce rules: recorded, not enforced.** Rulebook 21
   "hold quality", 7.5 "PositioningScore >= 70 to add" and 23 "distribution" as
   a reduce reason (spec limitation `UNMODELLED_ADD_AND_REDUCE_RULES`) have no
   owner consumer. The composer applies exactly BTC-154's eight add
   requirements plus policy V7 §7's Rulebook 24 NO ADDING, records the three as
   a named limitation, and leaves exposure counts to RBT-007. Enforcing them
   would need a new versioned spec and policy.

**Owner review rulings (2026-11-01, on the independent review's questions; the
recommended option each time).** They amend ruling 1 and the BTC-224
criterion as stated; the review outcome below records the findings.

4. **The ADD re-checks its risk at the callback that emits it (F1).** At that
   callback the projected risk at the stop is recomputed with the same owners
   (`next_tranche_for_position`, then `calculate_risk_at_stop`) at the latest
   closed bar's close, with the installed stop and that callback's NAV. Over
   the ceiling, or incomplete, the ADD is dropped with its recorded reason:
   one more drop condition for ruling 1. A gap at the fill bar's own open is
   beyond any composer under the frozen engine (it fills at the next bar's
   open with no fill-time ceiling check); it is pinned by a test and recorded
   as a limitation.
5. **The BTC-224 golden replays are met after the freeze (F3).** The golden
   fixture is six real periods of BTC history, daily prices only. No champion
   score or signal is computed on real prices before the RBT-006 freeze, so
   RBT-005's golden tests are plumbing replays only: the engine runs the
   composed champion over each golden bar sequence without refusal, and every
   instant is structurally unevaluable. The criterion's meaningful form, the
   frozen champion's decisions on the golden periods next to the scripted
   ones, moves to RBT-007: all six periods (2023-08 to 2025-10) lie in the
   evaluation window, none in the holdout. RBT-005 instead adds a synthetic
   end-to-end replay through entry, trail, add, trim and a composed `EXIT`,
   with a mutation that fails it.
6. **Two implementer choices ratified.** (a) An UNKNOWN STRESS or EUPHORIA
   state blocks the add (`RULEBOOK_24_FLAG_STATE_UNKNOWN`), fail closed, as
   BTC-154 treats an unknown CROWDING and the entry hard veto treats unknown
   flags. (b) A pending ADD whose first callback is itself a daily decision
   instant is dropped (`ADD_SUPERSEDED_BY_DECISION`) and the fresh decision
   decides.
7. **An exhausted tranche schedule is a named limitation (F5).** Once a
   position holds every tranche of the frozen schedule,
   `next_tranche_for_position` returns `TRANCHE_SIZING_SCHEDULE_EXHAUSTED` and
   no add is possible. No inventory or spec text accounts for it, so a recorded
   update adds it to `CHAMPION_COMPLETION_SPEC_V1` as a named limitation and
   rebinds the spec digest, as RBT-004 Part A did. No owner or configuration
   change.

### RBT-005 Implementation Notes

**Status:** `DONE (2026-11-01)`: independent xHigh re-review PASS WITH
NON-BLOCKING FINDINGS. This block is the implementer's record, current after
the review-fix (`56ab0ca`, `f69140f`, `5052cbb`) and the N1 fix (`dddd6a6`); the
RBT-005 review and re-review outcomes below record the findings, the fixes and
the closure.

**Commits:**
- Rulings record, `1b52760`: the three owner composition rulings above.
- Part A, `0856352`: the RBT-004 entry composer hands its composition to the
  in-position half (`EntryComposer.step`, `EntryDecision.composition`,
  `structure_score_at`, `latest_higher_low`, public `strategy_config`, `venue`,
  `next_decision_instant`); `composer_boundary` classifies `HoldScoreInput`,
  `AddScoreInput` and `ConfirmedTrailingStructure` as constructors (fields
  classified in the inventory). Behaviour-preserving: entry ledgers are
  byte-identical before and after on the decide and engine paths.
- Part B, `8fdd5a3`: `btc_predictor/research_backtest/management_composer.py`,
  the fixtures `rbt005_management_fixtures.py` and six
  `test_research_backtest_management_composer*` modules.
- Docs, `d81d4b4`: this block, the RBT-004 commit list, the tasks table and
  `CURRENT_STATE.md`.
- Review FAIL record, `14665aa`: the findings and owner review rulings 4-7.
- Review-fix, `56ab0ca`: the spec named limitation and rebind (ruling 7).
- Review-fix, `f69140f`: the composer and test corrections (F1-F5, rulings 4-6).
- Review-fix, `5052cbb`: the owner-less input guard scoped to the every-input-missing
  flow input (F2).
- Docs, `2431246`: the review-fix record and these notes.
- Non-blocking fix, `dddd6a6`: re-review N1, the runtime check of the prior flow
  the trim owner receives.
- Docs, this documentation commit: the re-review outcome and the closure.

No inventory, owner, configuration, `data/` or `research_artifacts/` change:
every management root was already a census root, so no Part A promotion was
needed. The review-fix rebinds the spec once, for one appended named
limitation (ruling 7; `787ddfa2...ca2620f0` -> `9a619596...15f6313`, proof in
`rbt005_spec_rebind_evidence_v1.json`).

**What the composer does.** `ManagementComposer(EntryComposer(...))` is the
champion's BTC-180 strategy: the entry composer decides while flat, this
composer while a position is open. The entry ledger keeps its row at every
instant; the management ledger (`CHAMPION_MANAGEMENT_DECISION_LEDGER_V1`) adds
one row per daily decision instant with an open position, and its header names
the entry ledger's digest. At t, from the entry run's own composition (nothing
is composed twice):

1. *Hold* (`calculate_hold_score`): Trend, Flow and Positioning from the
   composition; Structure is the entry path's Structure Score at `P_t` under
   the standing stop; `MOMENTUM_PERSISTENCE_SCORE = 100 * Phi(TREND_Z_M12)`.
2. *Exit* (`exit_rules_for_position`): the decision bar's low as the
   direction-appropriate extreme; `REGIME_INVALIDATION_PREDICATE` against
   `K_entry`, the classification persisted on the position's `ARM_ENTRY` row;
   `DATA_RISK_EXIT_PREDICATE = False`; the manual research override never
   asserted (`None`, the inventory's replay value); the data-quality gate's
   codes as evidence.
3. *Trim* (`trim_rules_from_results`): the prior decision instant's
   `FlowScoreResult` as the prior flow; when that instant had no decision bar,
   the flow owner's own result with every input missing (`TRIM_INPUT_MISSING`;
   the owner's other triggers still evaluate, review F2).
4. *Trail* (`trail_stop_for_position`): `C_t` from the one BTC-122 higher-low
   producer Setup C reads, identified by its own bar; the BTC-141 buffer of a
   structure with no zone.
5. *Add*, on the lifecycle before this instant's stop move:
   `NEW_STRUCTURAL_CONFIRMATION`, `ADD_MOMENTUM_SCORE = 100 * Phi(TREND_Z_M4)`,
   `NEW_STRUCTURE_SCORE` under the raised stop, the BTC-153 risk improvement,
   the projected post-add risk at the raised stop (`next_tranche_for_position`
   at `P_t`), the regime/flow/positioning predicates,
   `add_requirements_from_results`, the `ADD` data-quality gate and Rulebook 24
   NO ADDING.

Outcomes: `EXIT`, `TRIM`, `TRAIL` (with `ADD_PENDING_TRAIL` when the add goes
ahead), `HOLD`, or `STRUCTURALLY_UNEVALUABLE` (a missing decision bar, or an
incomplete Hold with no action). Each row records the position and its armed
entry, the regime predicates, the Hold inputs, the exit, trim, trail and add
records, the unevaluable Hold inputs with their accounted causes, every owner
result's reason codes, the unaccounted codes and the intent. An `ADD` follow-up
record keeps what became of each pending `ADD`.

**Owner rulings applied (2026-11-01).**
1. `TRAIL` at t; the `ADD` (requirements evaluated at t) at the first engine
   callback after the raised stop is installed. Dropped, with its reason, if
   the trail was not applied (`ADD_TRAIL_NOT_APPLIED`), the position closed
   (`ADD_POSITION_CLOSED`) or changed (`ADD_POSITION_CHANGED`: any accepted
   transition but its own trail, review F4), or that callback is itself a
   decision instant (`ADD_SUPERSEDED_BY_DECISION`, ratified by review ruling
   6). Review ruling 4 adds a risk re-check at that callback:
   `ADD_RISK_AT_STOP_EXCEEDED_AT_CALLBACK` or `ADD_RISK_RECHECK_INCOMPLETE`
   drops the ADD, and the follow-up records the re-check.
2. `EXIT` > `TRIM` > `TRAIL`/`ADD`: a suppressed add records
   `ADD_SUPPRESSED_BY_EXIT`/`ADD_SUPPRESSED_BY_TRIM`, a deferred trail
   `TRAIL_DEFERRED_BY_EXIT`/`TRAIL_DEFERRED_BY_TRIM`, and a deferred trail's
   higher low stays unused for the next decision.
3. Rulebook 21 "hold quality", 7.5 "PositioningScore >= 70 to add" and 23
   "distribution" are recorded, not enforced (spec limitation
   `UNMODELLED_ADD_AND_REDUCE_RULES`).

**Design decisions (for the review).**
- *One composition per instant.* The management half reads the entry run's
  `EntryComposition` (Part A) rather than composing the shared inputs again.
- *Rulebook 24 NO ADDING* (policy V7 section 7) reads each flag as the hard veto
  does: STRESS through the V4 mapping, CROWDING as `SEVERE_CROWDING_STATE`, and
  EUPHORIA through the same V4 mapping (`flagged` when only its DISCRETIONARY
  `systemic_euphoria` is missing). An active flag records
  `RULEBOOK_24_NO_ADDING_ENFORCED`; an unknown one also blocks the add (fail
  closed, as BTC-154 and the hard veto do) and records
  `RULEBOOK_24_FLAG_STATE_UNKNOWN` (ratified by owner review ruling 6). Each gate (BTC-154, data quality, Rulebook
  24) is recorded independently.
- *Hold Structure.* STRUCTURE_SCORE_V1_2 carries no R/R weight, so the score at
  `P_t` does not depend on the stop the owner requires; the standing stop is
  passed. `NEW_STRUCTURE_SCORE` passes the raised stop, as the spec says.
- *The trail buffer `B_t`.* The spec names it without a definition. A higher
  low is a single price: no zone, so the buffer owner's own ATR-only path, as
  the BTC-224 scripted trail does.
- *Position size.* The BTC-145 size is recomputed at the `ARM_ENTRY` decision
  exactly as the engine sizes the entry (`calculate_risk_budget` on the
  decision bar's NAV, then `initial_position_size_for_trade`); a test checks
  the engine's first tranche against it. The position is linked to its armed
  row through the `ENTER` transition's source id.
- *An exhausted tranche schedule* is the frozen schedule's own limit, not a
  missing input: `TRANCHE_SIZING_SCHEDULE_EXHAUSTED` is accounted to the spec
  named limitation `TRANCHE_SCHEDULE_EXHAUSTED` (review ruling 7; it first
  cited the schedule's "never missing" inventory row, review F5), and the add
  is `NOT_EVALUATED` with `ADD_NO_FURTHER_TRANCHE`. A missing stop on an open
  position is accounted nowhere and fails loud (review F5).
- *The prior flow* is the previous decision instant's `FlowScoreResult`; when
  that instant had no decision bar, no flow was composed for it and the trim
  owner receives the flow owner's own result with every input missing: it maps
  it to `prior_flow_score = None`, gives `TRIM_INPUT_MISSING` and still
  evaluates its Hold-band and CROWDING triggers, as the bound inventory rows
  state (review F2). The row's trim record names the missing bar in
  `prior_flow_causes`.
- *The golden replays are plumbing only* (owner review ruling 5). The BTC-224
  fixture is real history with daily prices only, and no champion value is
  computed on real prices before the RBT-006 freeze, so the champion's replay
  inputs hold nothing for those dates: every golden instant is the accounted
  `STRUCTURALLY_UNEVALUABLE` row and the tests show only that the engine runs
  the composed champion over each sequence without refusal. RBT-007 reports
  the frozen champion's golden decisions next to the scripted ones; RBT-005
  proves the composed path on the synthetic end-to-end replay.

**Defect found and fixed before commit.** The data-quality gate's
`reason_codes` are `RecommendationReasonCode` records, not strings; the
composer passes their codes as exit and add evidence. The flags test
(`DATA_QUALITY_FAIL`) caught it; the natural replays never failed the gate.

**Surfaced for the review (frozen owner behaviour, not changed).**
- Once a trailed stop reaches the average entry, risk at the stop is zero under
  the floored convention, BTC-153's risk improvement is undefined (0 of 0),
  the Add Score is incomplete (`ADD_SCORE_INPUT_MISSING`, accounted) and no
  later add can pass. The synthetic replays show it right after the first
  trail above the entry.
- BTC-157's provisional flow-deterioration trim (any decline from the prior
  decision's Flow Score; `PROVISIONAL_PENDING_BTC_185`) fires on most days of
  the synthetic market.
- `trim_rules_from_results` passes EUPHORIA only when complete, which it never
  is (policy V7 section 7 limitation): `TRIM_INPUT_MISSING` at every instant.
  The manual research override is never asserted: `EXIT_INPUT_MISSING` at
  every instant. Both are accounted; both triggers' other reasons still
  evaluate.

**Tests (six modules, 100 tests, all passing; 16 added by the review-fix; plus one coverage guard test, `5052cbb`).**

| Module | Proves |
| --- | --- |
| `…_management_composer` | one management row per open instant beside the entry row; HOLD/TRIM with every trim executed; the position and its armed entry (K_entry, source id, opened at); the armed BTC-145 size equals the engine's first tranche; Hold read from the composition (Structure equals the entry path's; persistence `100 * Phi(Z_M12)`); the prior flow; a missing decision bar while open and the trim that still evaluates; a missing prior flow leaving the Hold-band trim to the owner, with no value in the prior flow it receives (F2, re-review N1); canonical ledger naming both halves; digest stable across hash seeds and working directories; decide API refusals; regime invalidation (bear now, not bear at entry; exempt; unknown `K_entry` never False); a Hold collapse exit; the exit's bar extreme, data risk and override; the spec values against the frozen spec; accounting backed by the bound artifacts (each inventory citation names its code, the one phrase citation shown through the owners, the named limitation), injected unknown and silent incomplete codes reported, a missing open-position stop unaccounted (F5), the exhausted schedule |
| `…_rulings` | the TRAIL at t, the trail applied at t+1h, the ADD queued then and executed at t+2h with the requirements evaluated at t; on the post-move lifecycle the same higher low is already used (the spec's sequencing note); the next decision needs a newer structure; the three drop reasons through the engine; a trim defers the trail and suppresses the add; an exit overrides a trim and a trail and suppresses an add; a deferred trail's higher low applies at the next decision; hold 60-70 and Positioning below 70 do not block an add; a state change after the trail drops the ADD (F4); an installed trail at a decision callback is superseded (ruling 6); the ADD's risk re-check recorded at its callback, a price rise by the callback dropping it, and the fill-bar gap pinned as the limitation (ruling 4, F1) |
| `…_flags` | the baseline add goes ahead; STRESS, CROWDING and EUPHORIA each block it with `RULEBOOK_24_NO_ADDING_ENFORCED`; an unknown STRESS or EUPHORIA blocks it with `RULEBOOK_24_FLAG_STATE_UNKNOWN`, an unknown CROWDING through BTC-154 too; `DATA_QUALITY_FAIL` blocks the add and is not an exit; through the engine no ADD reaches it while STRESS is active |
| `…_invariants` | over the natural, trail-and-add and end-to-end replays: never average down, stops never widen, risk at the stop within the configured ceiling at every bar, no engine refusal; the end-to-end replay (entry, TRAIL, ADD, TRIMs, a composed EXIT) and two mutations of the management half that fail it; each of the six BTC-224 golden sequences as plumbing (ruling 5) |
| `…_boundary` | the static census (no refusal, exactly the 16 roots, the five classified constructors, bounded value methods), the runtime trace over a composed replay, TRIM/EXIT decisions, a trim without a prior flow and the ADD's risk re-check (no violation, every static root exercised), and nine static and seven runtime mutations that fail |
| `…_pit` | every family perturbed after the cutoff (RBT-004's `perturb_after`, two seeds) leaves every management row, entry row and engine event up to the cutoff byte-identical, and changes what follows; the pending add is composed from its instant alone; the ADD's risk re-check reads nothing after its callback |

Part A adds four tests to the RBT-004 core module (the adapter step and its
composition, a missing-bar decision composes nothing, Structure at a stop,
the trailing producer), so the RBT-004 modules count 197.

**Validation (`.venv312`, CPython 3.12.14).**
- Review-fix (`f69140f`): the six management modules 100 passed in 521.30s; all fourteen
  composer modules 297 passed in 1750.47s; the two spec modules 115 passed in 20.12s; full repository
  at `f69140f`, alone: 7,630 passed, 1 failed, 3 skipped, 1 xfailed in 4695.76s; the one failure, `test_no_production_code_produces_the_owner_less_entry_inputs`, is the owner-less input guard, tripped by the F2 construction and scoped by `5052cbb` (the full suite was not rerun after it). After `5052cbb`: the coverage module 66 passed in 22.69s.
- Implementation (`8fdd5a3`), below.
- All fourteen composer modules together: 281 passed in 1632.48s.
- V5 definition: 95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89 unchanged.
- PAD5 preserved-authority subset: 5 passed, 112 deselected in 40.28s; PAD4-R5: 2 passed in 25.31s.
- Full repository at `8fdd5a3`, alone:
  7,614 passed, 3 skipped, 1 xfailed, 0 failed in 4569.77s.
- `compileall` and `git diff --check` PASS.

**Acceptance criteria.**
- *No new formulas, point in time, decision ledger, determinism, census
  boundary:* the core, boundary and point-in-time modules above.
- *Rulebook 24 NO ADDING:* the flags module; the `DEFEND` mapping is not chosen.
- *BTC-222 invariants over composed replays:* the invariants module, over
  three composed replays including the end-to-end one. The ADD's risk
  re-check (ruling 4) holds the ceiling up to its callback; a gap at the fill
  bar's open is the recorded limitation.
- *BTC-224 golden replays (amended by owner review ruling 5):* plumbing
  replays without engine refusal in the invariants module; the composed path
  end to end on the synthetic replay; RBT-007 reports the golden decisions
  next to the scripted ones.
- *Composer-root and runtime completeness guards with the same regressions:*
  the boundary module and the core module's accounting tests.

**Limitations.** The three unmodelled rules (ruling 3); the frozen owner
behaviours above; the golden replays are plumbing only until RBT-007
(ruling 5); the ADD's projected risk is tested at `P_t` and again at its
callback's bar (ruling 4), while the frozen engine fills at the next bar's
open, so a gap at that open (or the cost model's slippage) can carry risk at
the stop above the ceiling, pinned by a test. No real-data value,
score, signal, trade or outcome was computed; no database connection; holdout
NOT COLLECTED; BTC-019 untouched, sealed sample unopened; EPIC X unchanged
(`POSTP1-001V2R1` remains its next ticket).

Recommended next dependency-satisfied ticket: **RBT-001A** (READY); RBT-006
stays blocked on RBT-003.

### RBT-005 review outcome

**Date:** 2026-11-01. **Review:** independent xHigh ticket review, run at the
owner's request by the OpenAI Codex CLI (0.162.1, model `gpt-6.1-sol`,
reasoning `xhigh`) in a detached worktree at `d81d4b4`, against the rulings
record `1b52760`, Part A `0856352`, Part B `8fdd5a3` and documentation
`d81d4b4` (base `d728bcd`). Report-only: a workspace-write sandbox with network
disabled, no database, no `.env*` file, synthetic fixtures only; its worktree
stayed clean.
**Result: FAIL.** RBT-005 is not DONE and RBT-006 stays blocked. The review's
four owner questions were answered the same day (owner review rulings 4-7 in
the ticket block); no correction needs a frozen owner edit or a new formula.

**Findings.** Locations refer to `d81d4b4`.

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| F1 / **P1 FIXED** (ruling 4) | `management_composer.py:851`, `:526` | The ADD is authorized on projected risk at `P_t`, and the pending ADD carries that authorization unchanged, while the engine sizes and fills the tranche at a later bar's open. No frozen owner checks the ceiling at the fill; BTC-222 tests adds only at the projected price. | Trail/add fixture with every bar from `TRAIL_AT + 1h` scaled by 1.10: projected risk at t 0.2877% of NAV, the ADD executes, realized risk 1.5569% against the 1% ceiling. Ruling 4: re-check at the callback that emits the ADD; pin the fill-bar gap as a limitation. |
| F2 / **P1 FIXED** | `management_composer.py:732` | When the prior instant had no decision bar, `_trim` returns before calling the owner, so the Hold-band and CROWDING triggers are suppressed with the flow comparison. The bound row `trim_rules_from_results.prior_flow` reads "None -> TRIM_INPUT_MISSING; complete False, the other triggers still evaluate"; `test_a_missing_decision_bar_while_open_gets_its_row_and_the_next_trim_waits` pins the suppression. | Hold 45 with prior flow None: the owner signals `TRIM_HOLD_SCORE_BAND`, the composer records `HOLD` with the trim not evaluated and nothing unaccounted. Pass None to the owner. |
| F3 / **P1 FIXED as ruled** (ruling 5) | `test_research_backtest_management_composer_invariants.py:84` | The golden replays' inputs hold nothing for the golden dates and the test requires an empty management ledger: no management decision or intent reaches the engine. The composed invariant replays execute no `EXIT`. | With `_ManagementRun.run` replaced by a function that raises, all six golden tests still pass. Ruling 5: plumbing replays only before the freeze, the golden decisions in RBT-007, and a synthetic end-to-end replay with a failing mutation in RBT-005. |
| F4 / **P2 FIXED** | `management_composer.py:517` | The pending-ADD resolver checks quantity and opening only, not lifecycle state; ruling 1 drops the ADD when the position's state changes first. | Trail installed, then an accepted `DEFEND` at the same quantity and stop: the resolver emits the ADD. Drop on any accepted transition after t other than the ADD's own trail. |
| F5 / **P2 FIXED** (ruling 7) | `management_composer.py:213`, `:215`; `test_research_backtest_management_composer.py:334` | Two accounted causes cite text that does not establish them: `RISK_AT_STOP_INPUT_MISSING` the closed-lifecycle "fail closed", `TRANCHE_SIZING_SCHEDULE_EXHAUSTED` the schedule's "never missing". The backing test checks substrings only. | A missing stop in the open position's risk calculation gives `unaccounted=()`. Drop the risk-at-stop entry, so a missing stop on an open position fails loud; ruling 7 makes the exhausted schedule a named limitation of the spec. |

**Checks that passed.** Every numeric value comes from an owner or a declared
spec helper (Hold and Add transforms, structure, risk improvement, projected
risk, the `ARM_ENTRY` size). Point in time over both perturbation seeds, with a
pending ADD carrying only its t requirements. The ledger, missed midnights,
determinism and no zero-filling. The static and runtime census with all 15
roots exercised, and the supplied mutations detected. Rulebook 24 for all three
active flags, with no `DEFEND` mapping. The add evaluated before the same
instant's `STOP_MOVE`; one higher-low producer with its own bar's timestamp;
`K_entry` persisted. Rulings 2 and 3. Part A: old and new entry ledger bytes
equal on five direct decisions and a three-row engine replay, engine events
equal. The ATR-only trail buffer, the standing-stop Hold Structure and the
exhausted schedule follow owner behaviour; a stop between the TRAIL and the ADD
executes first and leaves the queued ADD stale. Spec and inventory digests
matched. Codex's runs (`.venv312`, one process at a time): the six management
modules 84 passed in 421.16s; an entry core/static-boundary selection plus six
scratch golden mutations 73 passed, 11 deselected in 159.35s; `git diff
--check` clean. The full suite was not rerun.

**Distinct review-fix:** `56ab0ca`, `f69140f` and `5052cbb` (2026-11-01).
- `56ab0ca` (ruling 7, F5): `TRANCHE_SCHEDULE_EXHAUSTED` is appended to the
  spec's named limitations and the spec rebound `787ddfa2...ca2620f0` ->
  `9a619596...15f6313`. Two leaves were added and nothing else changed
  (`rbt005_spec_rebind_evidence_v1.json`, pinned by
  `test_the_rbt005_rebind_only_appended_the_exhausted_schedule_limitation`);
  the entry composer's spec pin follows, with the accounting authority
  `SPEC_NAMED_LIMITATION`. No inventory, owner or configuration change.
- `f69140f` changes only `management_composer.py`, the RBT-005 fixtures and five
  RBT-005 test modules:
  - F1 (ruling 4): at the callback that emits the ADD,
    `next_tranche_for_position` and `calculate_risk_at_stop` run again at that
    callback's closed bar, installed stop and NAV. Over the ceiling
    (`ADD_RISK_AT_STOP_EXCEEDED_AT_CALLBACK`) or incomplete
    (`ADD_RISK_RECHECK_INCOMPLETE`), the ADD is dropped. The follow-up records
    the re-check, and its unaccounted codes join the guard.
  - F2: the trim owner always runs. When the prior instant had no decision
    bar, no flow was composed for it, and the frozen owner refuses a literal
    `None` (it takes a `FlowScoreResult` and maps an incomplete one to
    `prior_flow_score = None`). The composer passes the flow owner's own
    result with every input missing (`calculate_flow_score`, a census root,
    now the composer's 16th direct root; `FlowScoreInput` its fifth
    constructor), so the owner gives `TRIM_INPUT_MISSING` and evaluates its
    other triggers, as the bound inventory rows state. No value is improvised;
    the row's trim record names the missing bar in `prior_flow_causes`.
    Surfaced for the re-review: the call-site row
    `trim_rules_from_results.prior_flow` reads "None -> TRIM_INPUT_MISSING"
    although the owner refuses `None`; it describes the mapped
    `TrimRuleInput.prior_flow_score`. The inventory is not changed.
  - F3 (ruling 5): the golden tests are relabelled as plumbing; the end-to-end
    replay (entry, TRAIL, ADD, four TRIMs, a composed `HOLD_SCORE_COLLAPSE`
    EXIT) joins the BTC-222 replays, and two mutations of the management half
    fail it (one is the review's).
  - F4: any accepted transition after t other than the ADD's own trail is
    `ADD_POSITION_CHANGED`.
  - F5: `RISK_AT_STOP_INPUT_MISSING` leaves the accounting table, so an open
    position's missing stop fails loud; the exhausted schedule cites the named
    limitation. The accounting test now requires each inventory citation to
    name its own code; the one phrase citation (the trail buffer's "None -> no
    trail candidate") is shown through the real owners.
  - The runtime boundary trace now covers the re-check, and a point-in-time
    test shows it reads nothing after its callback.
- `5052cbb` changes only `test_research_backtest_coverage.py`. The full suite at
  `f69140f` failed only the owner-less input guard
  `test_no_production_code_produces_the_owner_less_entry_inputs`: the F2
  construction puts `FlowScoreInput(` in the management composer. The guard's
  production scan now exempts that composer from the flow pattern only (the
  trend, orderliness and level patterns still scan it), and the new
  `test_the_management_composer_constructs_only_the_every_input_missing_flow_input`
  requires every `FlowScoreInput` construction the composer census finds
  (aliases resolved) to take no positional argument and name every field with
  the literal `None`. Five mutations fail it: a value, an omitted field, a
  positional call, an aliased construction and a trend pattern. This is a
  change to an existing RBT-002 test (amended once before by RBT-004),
  surfaced for the re-review.

Regressions: `test_a_missing_prior_flow_leaves_the_other_trim_triggers_to_the_owner`
and the corrected missing-bar test (F2);
`test_a_state_change_after_the_trail_drops_the_add` (F4);
`test_a_missing_stop_on_an_open_position_is_unaccounted` and the strengthened
accounting test (F5); `test_an_add_whose_risk_exceeds_the_ceiling_at_its_callback_is_dropped`
and `test_the_add_rechecks_its_risk_at_the_callback_that_emits_it` (F1);
`test_a_gap_at_the_fill_bars_open_is_the_recorded_limitation` (ruling 4's
residual, the review's own probe); the end-to-end replay and its two mutations
(F3); `test_a_decision_instant_supersedes_an_add_whose_trail_is_installed`
(ruling 6b, with the trail applied as the review asked). The F2, F4 and F5
regressions were run against the pre-fix composer and fail there; the F1 tests
read the re-check record the fix adds. Validation: the six management modules
100 passed in 521.30s; all fourteen composer modules 297 passed in 1750.47s; the two spec modules 115 passed in 20.12s;
full repository at `f69140f`, alone: 7,630 passed, 1 failed, 3 skipped, 1 xfailed in 4695.76s; the one failure, `test_no_production_code_produces_the_owner_less_entry_inputs`, is the owner-less input guard, tripped by the F2 construction and scoped by `5052cbb` (the full suite was not rerun after it); the coverage module at `5052cbb`
66 passed in 22.69s.

### RBT-005 re-review outcome

**Date:** 2026-11-01. **Review:** independent xHigh re-review by the same Codex
CLI session (`gpt-6.1-sol`, reasoning `xhigh`), resumed in its detached
worktree at `2431246` under the same report-only rules; its worktree stayed
clean. **Reviewed:** review-fix `56ab0ca`, `f69140f` and `5052cbb` and
documentation `2431246`, against the FAIL at `d81d4b4` and owner review
rulings 4-7.
**Result: PASS WITH NON-BLOCKING FINDINGS. RBT-005 is DONE.** F1-F5 are fixed
(F1 and F3 as ruled); no new blocking defect was found.

| Finding | Re-review status and evidence |
| --- | --- |
| F1 | **FIXED as ruled** (ruling 4). A 10% rise during the callback's bar now drops the ADD with `ADD_RISK_AT_STOP_EXCEEDED_AT_CALLBACK`; an incomplete re-check also drops it and keeps its unaccounted causes. The re-check reads that callback's closed bar, installed stop and NAV. The review's own gap at the fill bar's open still executes, at 1.556898% of NAV: the ruled residual, pinned by a test. |
| F2 | **FIXED.** Before/after probes change HOLD -> TRIM for both a Hold of 45 and an active CROWDING with no prior flow. The every-input-missing `FlowScoreInput` gives the owner's incomplete result, which the trim owner maps to `prior_flow_score = None`: a faithful reading of the two inventory rows, with no invented value or fallback. |
| F3 | **FIXED as ruled** (ruling 5). The synthetic replay runs ENTER -> STOP_MOVE -> ADD -> four TRIMs -> EXIT, and both management mutations fail it. The golden tests are plumbing only, and RBT-007 carries the reporting obligation. |
| F4 | **FIXED.** An accepted `DEFEND` probe changes ADD_EMITTED -> `ADD_POSITION_CHANGED`; the trail-only control still emits the ADD, and a stress-cost replay with 50 funding events executes it, so funding does not trip the transition check. |
| F5 | **FIXED.** A missing open-position stop is unaccounted; the exhausted schedule cites `TRANCHE_SCHEDULE_EXHAUSTED`. An independent comparison with the previous JSON confirms only that named limitation was appended; the other sections and the inventory are unchanged. |

The before/after probes loaded the pre-fix composer from `56ab0ca` and
reproduced the F2, F4 and F5 failures. The resolver's runtime boundary is
exercised, all 16 direct roots are covered, and the point-in-time tests pass.
The documentation was found accurate, including the full suite's failure at
`f69140f` and the absence of a full rerun after `5052cbb`.

| ID / severity | Location (`2431246`) | Finding | Disposition |
| --- | --- | --- | --- |
| N1 / **P2 FIXED** | `test_research_backtest_coverage.py:352`, `:365` | The guards check only how the every-input-missing `FlowScoreInput` is constructed: wrapping that construction in `dataclasses.replace` inserts values with neither guard nor the static census failing (three core fields at 1 gave a complete flow, score 84.13; one field also passed both guards). The current composer supplies five literal `None`s, so this is a test-protection gap, not a current unsourced value. | Fixed in `dddd6a6`: the runtime F2 regression records the trim owner's call and asserts the prior `FlowScoreResult` it received is incomplete, holds `None` in every input field and has no raw score, score, interpretation or contribution value, whatever route built it. A replace of one core field, of the three core fields or of one P1 field each fails it. |

Codex's runs (`.venv312`, one process at a time): the six management modules
100 passed in 539.39s; both spec modules and the coverage module 181 passed in
44.83s; the before/after findings probes and the guard probes passed (the five
reported mutations rejected, the replacement bypass reproduced); the spec
rebuilds to `9a619596...15f6313` with the inventory at
`250f9470...a061cb17`; `git diff --check` clean. It did not rerun the full
suite. No owner question was raised.

**Non-blocking fix:** `dddd6a6` (2026-11-01), made after the PASS as the owner
chose, without a further re-review. It changes
`test_research_backtest_management_composer.py` only; no composer, owner,
configuration, spec, inventory or evidence change. Validation: the six
management modules and the coverage module 166 passed in 546.55s; full repository at
`dddd6a6`, alone: 7,632 passed, 3 skipped, 1 xfailed, 0 failed in 4711.30s.

Recommended next dependency-satisfied ticket: **RBT-001A** (READY). RBT-006
stays blocked on RBT-003.

## RBT-006 — `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1`

**Status:** `IN PROGRESS — Part A review FAIL 2026-11-11 (four P2, F1-F4, two P3, F5-F6; owner ruling 3d and fix all), review fixes next; Part A committed 2026-11-11 (b167d90); owner rulings 1-4 and clarifications 3a-3c and 4a (2026-11-11) — RBT-003 DONE (2026-11-11); RBT-005 DONE (2026-11-01); closure-table dependency SATISFIED`
**Dependencies:** RBT-003, RBT-005, `POSTP1-002V2A-T1` PASS (closure table,
**SATISFIED 2026-09-30** at `2292388e4a91c1617275ac20ed9d6b45e4b9678525c020e1ccc6fc36a01d1710`)
**Implementation effort:** high
**Review:** independent xHigh ticket review
**Owner module:** `btc_predictor/research_backtest/preregistration.py` (new)

Freeze everything before any result exists.

The independent exact-hash T1 review verified coverage `2023-01-01..2026-12-31`
against retrieved official exchange publications. Every 5-/20-day flow window
from the first ETF flows (`2024-01-11`) through the `2026-06-30` holdout end
lies inside coverage, including the earliest trailing lookback `2023-12-13`.
This satisfies only the table prerequisite. It authorizes no preregistration
before RBT-003/RBT-005, no backtest outcome and no holdout opening. Any 2027
flow window needs a new frozen, reviewed table version before use.

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
- Freezes the Momentum Persistence ablation variant (policy V7 §6A.10, §8)
  with the champion: Hold Score without that term, the other four weights
  re-normalized proportionally, labelled `SENSITIVITY_ONLY_NOT_SELECTION`.
- Review confirms that no evaluation-window outcome was produced before the
  freeze.
- **Runtime completeness guard (V6 §5A.6).** During the completeness-only
  real-data pass, any incomplete owner result whose cause is not accounted for
  in the inventory or the spec blocks the freeze.

**Owner rulings (2026-11-11, asked before implementation; the recommended
option each time).** These are the points the ticket and the policy leave
open:

1. **ETF fund launch dates (policy V7 §5).** The fund universe passes, per
   window, the funds whose first US trading date is on or before the window's
   first included publication date. Every fund needs a launch record with
   source evidence, and the composer refuses an unrecorded fund. For each
   fund in the frozen CoinGlass history:
   - its launch date is the date of its first row in that history: RBT-003's
     frozen `etf_flows` input, in private commit `f36ad14`, bound by its
     digest in the dataset's `BUILD.json`;
   - the record names that evidence by its digest;
   - the record also cites the publicly documented first US trading date,
     and the freeze refuses any mismatch;
   - GBTC's launch under this rule is its ETF conversion day, 2024-01-11.

   Only dates are read; no value is.
2. **The walk-forward fold scheme (BTC-182, policy V7 §8).** The configured
   split (expanding; 730 training, 182 test and 182 step periods) needs 912
   periods before one fold exists, and each venue's evaluation window starts
   near 2024. The ruling:
   - the configured expanding scheme, with 182-period test windows, a
     182-period step and no embargo, counted in daily decision instants;
   - per venue, the training periods are every daily decision instant before
     its evaluation-window start, computed mechanically, so the first
     out-of-sample window begins at the evaluation start;
   - a tail shorter than 182 periods is reported as untested periods, as
     BTC-182 does;
   - the champion is never refitted: folds measure stability through time
     under `INDEPENDENT_FOLD_CAPITAL_V1`.
3. **The threshold-sweep grid (BTC-185, sensitivity only).**
   - All ten parameters the owner supports: entry conviction; the trend,
     flow, positioning and structure minimums; the minimum reward-to-risk;
     the stop buffer; the hold and add thresholds; and the risk budget.
   - Each at its configured value and at ±10% and ±20% of it: five
     candidates, one uniform rule, with no per-parameter tuning.
   - Objective: BTC-185's `mean_return_fraction`, with a plateau tolerance
     of 0.005.
   - The `base` cost rung only.
   - Labelled `SENSITIVITY_ONLY_NOT_SELECTION`; a sweep never selects a
     value.

   Two clarifications of ruling 3, asked the same day once the
   configuration showed them (the recommended option each time):
   - **3a. Invalid candidates are dropped and recorded.** The configuration
     requires strictly ordered entry and hold bands and scores within
     0-100, so some candidates cannot be configured. Examples: entry
     conviction 80 keeps only 72; hold 70 loses 56; add 85 loses 102. A
     candidate the configuration or the BTC-185 owner refuses is left out
     and recorded with its reason. There is no clipping, no re-spacing and
     no moving of a neighbouring band, so every sweep stays
     one-dimensional. A parameter left with fewer than two valid candidates
     is recorded as not swept.
   - **3b. One sweep per distinct configured value.** Where a parameter
     holds different values across the long setups, each distinct value is
     its own one-scalar sweep, and the paths sharing that value move
     together:
     - trend minimum: 70 and 55;
     - structure minimum: 70, shared by two setups, and 60;
     - risk budget: one sweep per schedule row, 0.0035, 0.005 and 0.006.

     That makes 14 sweeps. The short-only setup's values stay fixed,
     because the champion is long-only.
4. **The metric definitions and the report version (policy V7 §8).**
   - RBT-006 freezes a hash-bound metric-definition spec. Each Rulebook §28
     primary metric maps to its existing BTC-180..185 owner where one
     exists. Otherwise it gets a declared formula labelled as new, for
     example Sortino over daily NAV returns, annualised by √365 with a zero
     risk-free rate.
   - The spec names the report version.
   - RBT-007 builds the report generator to that spec, and its review checks
     conformance.

**The plan (the implementer's, not a ruling).** Two parts, as for RBT-003,
each independently reviewed:
- **Part A, offline.**
  - The preregistration module and the frozen definitions (rulings 1-4 and
    the Momentum Persistence ablation variant).
  - The completeness-only driver. It records, per venue and daily decision
    instant, only whether each Entry Conviction component and the core
    regime score are complete, with their missing-input causes and whether
    each cause is accounted for. It composes no Entry Conviction total, no
    setup, veto or intent, and no trade.
  - Synthetic fixtures only.
- **Part B, real data.**
  - The completeness pass over RBT-003's frozen datasets, read from the
    private repository, with value-free output.
  - Each venue's evaluation-window start, and the runtime guard.
  - The preregistration artifact under
    `backtest_evidence/research_backtest_v1/`, then its freeze.

**Owner clarifications during Part A (2026-11-11, asked; the recommended
option each time).** Implementation surfaced two more points:
- **3c. The stop buffer uses the configuration's own grid.** The
  configuration accepts `stop_buffers.atr_multiplier` only from its own
  `sweep_atr_multipliers` (0.25, 0.3, 0.5, 0.75), so every uniform candidate
  (0.24, 0.27, 0.33, 0.36) is refused and, under 3a, the stop buffer would
  go unswept. It is swept over that configured grid instead: the one
  exception to the uniform rule, recorded with its reason.
- **4a. The cross-venue measures are pre-registered.** Policy V7 §8 also
  requires cross-venue source sensitivity. The metric spec now defines
  trade-set overlap, matched-trade divergence, stop-touch divergence and
  metric dispersion, each labelled as new.

### RBT-006 Part A Implementation Notes (offline)

**Status:** `PART A COMMITTED (2026-11-11)`; its independent xHigh review
FAILED on 2026-11-11 (see the review outcome below); review fixes next. Nothing has run on real data: no completeness pass, no freeze.

**Commits:** the rulings `74d6720`, the clarifications 3a and 3b `0d8acd8`,
the code `b167d90` and this record. They add one module and one test module:
`btc_predictor/research_backtest/preregistration.py` and
`btc_predictor/tests/test_research_backtest_preregistration.py`. No owner,
composer, configuration, inventory, spec, builder or other test changed.

**What it does.**
- **ETF launches (ruling 1).** `etf_fund_launches` reads only each frozen
  `EtfFlow` row's fund and date. A fund's launch is its first row, named by
  the `etf_flows` input's uncompressed SHA-256 and cross-checked against
  the documented first US trading dates: ten funds on 2024-01-11, after the
  SEC's approval of the US spot bitcoin ETP listings the day before, and
  Grayscale's mini trust on 2024-07-31. GBTC's launch is its conversion. A
  mismatch, an undocumented fund or a documented fund absent from the
  evidence refuses.
- **The decision schedule.** Every UTC midnight strictly inside the data
  window, from 2020-01-02 to 2025-12-31: 2,191 instants. The midnight at
  the window's end is excluded, because its decision would execute on the
  next bar, in the holdout.
- **Folds (ruling 2).** `fold_plan` calls the BTC-182 owner with the
  configured expanding scheme, 182-period test and step windows and no
  embargo. The training periods are the instants before the venue's
  evaluation start, so fold 1 begins there. For example, a start on
  2024-03-15 gives three folds and 104 untested periods.
- **Sweeps (ruling 3, 3a-3c).** `sweep_grid` builds the 14 sweeps from the
  long setups' configuration paths, one sweep per distinct configured value.
  It checks every candidate by building the real configuration and the
  BTC-185 owner's value check. Dropped candidates and their reasons:
  - entry conviction keeps only 72 and 80; 64, 88 and 96 break the strictly
    increasing entry bands;
  - hold loses 56, because the hold bands must strictly decrease;
  - add loses 102, outside the BTC-185 owner's 0-100;
  - the stop buffer uses its configured grid (3c).

  All 14 sweeps are swept. Each is a BTC-185 `ThresholdSweepSpec` against
  the champion's identity, with `mean_return_fraction`, a 0.005 plateau
  tolerance, the `base` rung and `SENSITIVITY_ONLY_NOT_SELECTION`.
- **The ablation (§6A.10).** The Hold weights without Momentum Persistence,
  divided by the remaining 0.8666667 and rounded half-even to the
  configuration's seven decimals: 0.3076923, 0.3076923, 0.2307692 and
  0.1538461, with Momentum Persistence at 0. They sum to 0.9999999, inside
  both the configuration's and the Hold owner's tolerance of 0.000001. A
  test shows the Hold owner accepts the weights and ignores the term.
- **Metrics (ruling 4, 4a).** `metric_definitions` freezes the 16 Rulebook
  §28 primary metrics in the Rulebook's order, a test reading them from the
  Rulebook.
  - Owner conventions (7): expectancy, average R, Sharpe, Calmar, max
    drawdown, profit factor and number of trades, each naming its owner.
  - New definitions (9), consistent with those conventions (per equity
    point, unannualized, zero risk-free rate): Sortino, return per trade,
    win rate, average winner and loser, time in market, turnover, and the
    longest drawdown and losing streak.
  - The four §8 cross-venue measures (4a).

  The spec names `RESEARCH_BACKTEST_REPORT_V1`, and its canonical JSON is
  pinned by digest.
- **The completeness-only pass.** `completeness_pass` runs the reviewed
  RBT-004 composer's own steps through a subclass of its decision run. No
  composer changes.
  - Computed: trend, flow, positioning, volatility, the core regime score
    and the structure.
  - Recorded per instant: each component's completeness, the core regime's,
    the accounted causes, any unaccounted cause, the guard refusals and the
    span of the ETF publication calendar. Nothing else.
  - Never composed: Entry Conviction, the entry action, the Rulebook 24
    flags, regime smoothing and classification, a setup, a gate or an
    intent.

  A venue's evaluation start is its first instant at which all five
  components and the core regime score are complete. A structure left
  incomplete by a missing valid stop counts as incomplete, as the policy
  reads.
- **The freeze.** `preregistration_record` refuses unless every condition
  holds:
  - every venue's pass covers exactly the schedule;
  - no venue has an unaccounted cause (the runtime guard) or an ETF
    calendar date outside the closure table's coverage;
  - every venue has an evaluation start;
  - the code commit is a full id;
  - the configuration is the champion's.

  It binds:
  - the code commit, the champion and its spec;
  - both composers' versions and the closure table's hash;
  - the dataset index's digest, the build record, the private commit and
    the manifests;
  - the cost ladder with `base` as the headline;
  - the schedule, the ETF launches, each venue's completeness summary and
    fold plan;
  - the sweeps, the ablation and the metric spec.

  Its canonical bytes carry no time.
- **The command (Part B runs it).** `python -m
  btc_predictor.research_backtest.preregistration freeze --store …` runs on
  a clean commit. It loads the private dataset, proves the private commit
  holds it as stored, and requires the public index to equal the stored
  dataset's index byte for byte and the frozen inputs to rebuild the stored
  manifests. Then it runs the three passes and writes into
  `backtest_evidence/research_backtest_v1/`:
  - the value-free completeness ledgers;
  - `rbt006_preregistration_v1.json` with its `.sha256`.

  A refusal writes nothing.

**Surfaced for the review and RBT-007.**
1. Entry conviction 72 is a valid configuration, but the risk schedule's
   first band starts at 80, so an entry between 72 and 80 has no risk band.
   RBT-007 must report how that candidate runs.
2. Both composers refuse any configuration other than the champion's, so
   RBT-007 needs an explicit composer path for the sweep candidates and the
   ablation.
3. The pass depends on the composer's decision-run internals. A test pins
   its completeness, causes, unaccounted codes and guard refusals to the
   full composer's ledger rows on the RBT-004 world, across the week in
   which flow completes.
4. On the synthetic world the pass takes about 0.75 s per instant. Three
   venues over 2,191 instants is at least 80 minutes, likely longer on real
   data.

**Tests.** `test_research_backtest_preregistration.py`, 70 tests, all
synthetic: the RBT-004 composer world, and the RBT-003 dataset tests' private
store in a throwaway git repository. They cover:
- the launches and their refusals, with value-blindness;
- the schedule;
- the folds, including a start with no fold and the scheme check;
- every sweep record, each kept candidate building a configuration and each
  dropped one refused, each spec rebuilt through the BTC-185 owner, and a
  value left with one candidate recorded as not swept;
- the ablation, against the Hold owner;
- the metric list read from the Rulebook, every owner reference resolved,
  and the digest pinned;
- the cross-venue measures;
- the pass, against the full composer across the week flow completes and at
  the world's first instants (structure and the long windows still warming
  up), with no call to a forbidden owner, the missing-bar case, an
  unaccounted cause and a value-free ledger;
- the freeze's 12 refusals and its bindings;
- the command line's success and five refusals (an index of another commit,
  a dataset not committed as stored, manifests that do not rebuild, an
  unaccounted cause, code not on a clean commit), with nothing written, and
  a real pass on the stored dataset.

Mutants (`mutants_a.py`, one textual change at a time in a separate
worktree, with an unchanged control passing): 40 of 40 caught: 37 on the first run; the three survivors (a parameter left with one valid candidate still recorded as swept, the structure component always counted complete, the public index not compared with the stored one) were caught after two added tests and one strengthened test.

**Validation (`.venv312`, CPython 3.12.14, 2026-11-11).**
- The adapter, run, dataset and new modules with the V1/V2 replay,
  replay-review, database and four coverage guard modules: 1,728 passed, 1 xfailed; the
  BTC-019 completion gate and the coverage review: 18 passed.
- V5 definition
  `95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`
  unchanged; PAD5 preserved-authority subset 5 passed, 112 deselected;
  PAD4-R5 2 passed.
- Full repository at `b167d90`:
  9,039 passed, 3 skipped, 1 xfailed, 0 failed (80 min).
- `git diff --check` clean. Synthetic fixtures only; no database, network
  or private-evidence read; no real-data value.

Next: Part A's independent xHigh review; then Part B, the freeze command
on the private dataset.

### RBT-006 Part A review outcome

**Date:** 2026-11-11. **Review:** independent xHigh ticket review, run at the
owner's request by the OpenAI Codex CLI (0.162.1, reasoning `xhigh`) in a
detached worktree at `265c7e8`, over `98d8e14..265c7e8` (the rulings
`74d6720`, the clarifications `0d8acd8`, the code `b167d90` and its record
`265c7e8`). Report-only: a workspace-write sandbox with network disabled, no
database, no `.env*` file, no private evidence, synthetic fixtures only; its
worktree stayed clean.
**Result: FAIL.** Part B waits for the review fixes, the owner's ruling on the
Hold sweep, and a re-review.

**Findings.** Locations refer to `265c7e8` (the code is `b167d90`'s).

| ID / severity | Location | Current versus expected behavior; impact | Reproducer and required correction |
| --- | --- | --- | --- |
| F1 / **P2** (ruling 3d) | `preregistration.py:325` | The Hold-threshold sweep moves `hold_thresholds.hold_min`, which only the configuration's ordering check reads: no decision owner in the champion reads it. The artifact declares `[63, 70, 77, 84]` `SWEPT`, so RBT-007 would report apparent stability for an inert parameter. | A captured synthetic management decision at Hold 75 gave byte-identical rows for all four candidates; the implementer confirmed no reader outside the configuration. Ruling 3d below; add a check that a swept value has a decision reader. |
| F2 / **P2** | `preregistration.py:1107` | Each destination is checked only as it is written, so a refused later destination leaves the earlier files written, contradicting "a refusal writes nothing". | The Coinbase ledger's destination a symbolic link: `main` returned `REFUSED PROVIDER_REQUEST_MISMATCH` after writing the Bitfinex and Bitstamp ledgers. Check every destination before writing, and test a refusal at a later destination against the whole output set. |
| F3 / **P2** | `preregistration.py:635` | Longest drawdown runs from each new peak to the first later point at or above it, without requiring NAV to fall below the peak, and leaves the initial peak unstated. | Hourly NAV 100, 101, 102 gives a one-hour drawdown with no decline. Freeze the underwater, recovery, initial-peak, plateau and unrecovered rules with worked examples. |
| F4 / **P2** | `preregistration.py:158` | The documented first trading dates carry generic text, not an identifiable publication, order or source; the tests take their expected dates from the same table. The review found no date wrong. | Matching frozen evidence passes with no auditable public check. Cite identifiable primary sources. |
| F5 / **P3** | `preregistration.py:762` | At a missing decision bar the pass records a `DECISION_PRICE_BAR_MISSING` cause on each of the five components; the composer records one, on `decision_instant`. Completeness agrees; the causes and the census do not. | Pre-history and missing-hour probes; the existing test asserts the pass's own form. Record the composer's attribution and compare with it. |
| F6 / **P3** | `preregistration.py:564` | Max drawdown's undefined statuses read `NO_EQUITY_CURVE` and `NON_POSITIVE_NAV`; its owner returns `UNAVAILABLE_NO_EQUITY_CURVE` and `UNDEFINED_NON_POSITIVE_NAV`. The owner-reference test checks only that the symbols exist. | An empty-curve probe. Use the owner's exact statuses. |

**Checks that passed.**
- Ruling 1's reader takes only each row's fund and date (an attribute-access
  probe), names the evidence digest and refuses a mismatch.
- Ruling 2, 3a, 3b, 3c, 4a and the ablation are met as ruled. The seven-decimal
  half-even rounding follows Rulebook 20's recorded precision; its sum
  `0.9999999` is recorded.
- Every refusal is genuine, nothing is clipped, and each spec is a valid
  BTC-185 spec against the champion.
- The completeness pass reuses the composer's own steps for the five
  components and the core regime score. Runtime tracing found no Entry
  Conviction, flag, smoothing, classification, setup, gate, intent, trade or
  accounting call.
- Completeness and causes agree at the earliest daily instants, and all
  three positioning guard refusals agree with the full composer.
- An unknown missing-input code refuses the freeze, even on an otherwise
  complete owner result. The flow-calendar bounds enclose every flow-window
  date, and the ledger is value-free.
- The evaluation-start rule is the policy's §3 reading.
- The 2,191-instant schedule correctly excludes the window-end midnight.
- The artifact binds every required identity, version, manifest, cost,
  definition, fold, sweep and the ablation. It is deterministic and
  value-free.
- The command verifies the committed private dataset, the exact public
  index and the rebuilt manifests before any pass. No path substitutes
  another dataset.
- The surfaced points are described accurately, and none needs an owner
  decision before Part B.
- Two grouped paths are redundant but leave their sweeps effective: Setup A's
  detector ignores its `entry_conviction_min`, and `price_levels.rr_minimum`
  feeds the v1.2 structure diagnostics.
- Synthetic probes refused pre-2020, holdout and reserve records. No database,
  network, `.env*`, private store or sealed sample was read, and no real-data
  value computed.
- Codex's runs (`.venv312`, one process at a time): the new module 70 passed;
  twelve selected dataset, replay, census and metric-owner modules 762
  passed, 1 xfailed; its final probes and mutation controls 23 passed. Seven
  in-memory mutants were caught, and `git diff --check` was clean. The full
  suite was not rerun.

**Owner review rulings (2026-11-11, asked; the recommended option each
time).**
- **3d. The Hold-threshold sweep moves the Hold Score thresholds the champion
  reads.** These are `defensive_min` (50) and the shared 40 of `trim_min` and
  `exit_below`, read by the trim and exit owners the management composer
  calls. As in 3b, each distinct value is its own sweep.
  - 50 keeps 45, 50 and 55. 40 and 60 are refused, because the bands must
    stay strictly decreasing.
  - 40 moves both paths together over 32, 36, 40, 44 and 48.
  - `possible_add_min` (85), `hold_min` (70) and `no_add_min` (60) have no
    decision reader in the champion. They are recorded as such and not swept.

  That makes 15 sweeps. It is still sensitivity only, and the champion is
  unchanged.
- **Fix F2-F6.**
  - F2: check every destination before anything is written, and refuse if
    any exists or is a link. A freeze is never overwritten, as with the
    dataset build. The preregistration is written last.
  - F3: freeze longest drawdown as the longest time underwater, from the
    starting-NAV peak, with worked examples.
  - F4: cite SEC Release No. 34-99306 and No. 34-100610 and each fund's own
    filing. The dates are unchanged.
  - F5: record a missing bar exactly as the composer does.
  - F6: use the owner's exact statuses, with a test over every owner-cited
    metric.

  Each fix is a distinct commit, followed by mutants, the full validation and
  a re-review.

Next: the review fixes, then Part A's re-review; Part B after a PASS.

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
- **Momentum Persistence ablation (policy V7 §8).** The report includes the
  frozen variant, on the evaluation window only, per venue, under `base`. It
  shows the count of Hold evaluations whose §20 action band differs, and a
  full variant replay beside the champion's §28 metrics with trade counts,
  labelled `SENSITIVITY_ONLY_NOT_SELECTION`. It never runs on the holdout and
  never selects a variant.
- **BTC-224 golden replays (carried from RBT-005, owner ruling 5,
  2026-11-01).** The frozen champion, on the frozen replay inputs, is run over
  each BTC-224 golden period (all six lie in the evaluation window) without
  engine refusal, and the report shows its decisions next to the scripted
  ones, which they need not match. A period before the first evaluable
  decision reports its structurally unevaluable rows as they are.
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
| RBT-001 | `BUILD_HISTORICAL_REPLAY_INPUTS_V1` | DONE — independent xHigh ticket review PASS after review fix `a9773e7`; implementation `402e120` |
| RBT-002 | `INVENTORY_HISTORICAL_INPUT_COVERAGE_V1` | DONE — independent R2 re-review PASS under V5 §5A.7; correction `812b968`, docs `ce5cd70`, inventory `108ab25b...efe3a` unchanged; all four criteria independently verified |
| RBT-002A | `DEFINE_CHAMPION_COMPLETION_SPEC_V1` | DONE — independent xHigh review PASS under V7; final spec `9819f84a...5013f`, inventory unchanged; fixes `352bba0`, `496a947`, `5b75882`, `42459e6`; owner-ruled guard/ablation conformance `700b924`; 26 inputs, 16 new parameter elements, 14 roots; full suite 0 failures |
| RBT-001A | `EXTEND_REPLAY_INPUTS_TO_POLICY_V3` | DONE — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS (2026-11-04); review FAIL (two P1, one P2, one P3) fixed in `f674284`, `9171d63`, `7cb11e0`, `3b88daf` and `f785d81`, N1 in `6e2433e`, N2 corrected in the docs — rulings `4453b5c`, implementation `524fcbf`; owner review rulings 4-6; 162 tests; full suite at `6e2433e` 7,794 passed, 3 skipped, 1 xfailed, 0 failed (79 min) |
| RBT-003 | `BACKFILL_HISTORICAL_INPUTS_V1` | DONE — independent xHigh closure review PASS WITH NON-BLOCKING FINDINGS (2026-11-11; one P3, C1, corrected in the docs); Part B dataset built, verified and indexed 2026-11-11 (re-request: every scheduled hour still missing, kept as gaps; build at `5e78ab7`, verify passed; private commit `f36ad14`; public index `rbt003_replay_dataset_index_v1.json` in `98d8e14`); Part B re-request and dataset build second re-review PASS 2026-11-11 (no new finding; the re-request and dataset build code review closed; the owner's re-request run and the build next on `5e78ab7`'s code); Part B re-request and dataset build re-review fixes DR1-DR3 `9175a9c`..`5e78ab7` committed 2026-11-11 (full suite 8,969 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B re-request and dataset build review-fix re-review FAIL 2026-11-11 (one P2, DR1, and two P3, DR2 and DR3; owner: fix all three and two test gaps, the manifests' text owner-accepted); review fixes D1-D6 `0219a41`..`2d0307b` committed 2026-11-10 (full suite 8,921 passed, 3 skipped, 1 xfailed, 0 failed in 80 min); Part B re-request and dataset build code review FAIL 2026-11-10 (five P2, D1-D5, and one P3, D6; rulings 15 and 16 implemented as ruled; owner: fix all six, then re-review); Part B re-request and dataset build code `7e4f871` committed 2026-11-10 (full suite 8,834 passed, 3 skipped, 1 xfailed, 0 failed in 80 min); Part B owner ruling 16 2026-11-10 (14 Kraken hours disagreeing with the series withheld, their 13 days incomplete); Part B owner ruling 15 2026-11-10 (the 27 missing Coinbase/Bitfinex hours re-requested before the dataset build, written and reviewed with it); Part B CoinGlass collected 2026-11-10 on d9e611f (every Part B source collected; evidence committed privately; dataset build next); Part B R14-1 re-review PASS 2026-11-10 (no new finding; ruling 14's code review closed; CoinGlass to be collected on d9e611f); Part B R14-1 fix `d9e611f` committed 2026-11-10 (914 tests; full suite 8,708 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B ruling 14 code review FAIL 2026-11-10 (R14-1 P2: a CoinGlass number no decimal can hold raises instead of refusing; ruling 14 implemented as ruled; owner: fix, then re-review); Part B ruling 14 code `87dc505` committed 2026-11-09 (854 tests; full suite 8,648 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B Kraken liquidations complete (four refused days collected on 3041d0c 2026-11-09); CoinGlass's first live responses omit two members; owner ruling 14 (the envelope's msg and a fund day's btc_holdings may be absent) to implement and re-review; Part B ruling 13 code review PASS 2026-11-09 (no new finding; ruling 13's code review closed; four refused Kraken days to be collected); Part B ruling 13 code `3041d0c` committed 2026-11-09 (773 tests; full suite 8,567 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B refused Kraken days collected on c5fa819 2026-11-09 except four (an identical repeated block of executions); owner ruling 13 (identical copies collapse and are counted, a differing repeat still refuses) to implement and re-review; CoinGlass may run meanwhile; Part B ruling 12 fourth re-review PASS WITH NON-BLOCKING FINDINGS 2026-11-09 (one P3, R12-10, owner-accepted; ruling 12's code review closed; refused days to be collected); Part B ruling 12 third review-fix `c5fa819` committed 2026-11-08 (694 tests; full suite 8,488 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B ruling 12 third re-review FAIL 2026-11-08 (two P2, R12-6 and R12-7, with the implementer-found R12-8 and R12-9; owner: fix all four, then re-review); Part B ruling 12 second review-fix `7808213` committed 2026-11-08 (627 tests; full suite 8,421 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B ruling 12 second re-review FAIL 2026-11-08 (two P2, R12-2 and R12-3, with the implementer-found R12-4; owner: fix all three, then re-review); Part B ruling 12 review-fix `029057e` committed 2026-11-08 (584 tests; full suite 8,378 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B ruling 12 re-review FAIL 2026-11-08 (one P2, R12-1; owner: sum each side exactly, then re-review); Part B ruling 12 code `fd702fe` committed 2026-11-08 (566 tests; full suite 8,360 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B Kraken liquidation collection stopped 2026-11-08 at a day listed out of time order; owner ruling 12 (count such steps, do not refuse); collection continued past refused days; CoinGlass and the dataset build next; Part B fifth re-review PASS 2026-11-07 (no new finding), Part B code review closed; Part B fifth review-fix `197c8c5` committed 2026-11-07 (556 tests; full suite 8,350 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B fourth re-review FAIL 2026-11-07 (one P2, BR7; owner: fix value-blind, then re-review); Part B fourth review-fix `e866317` committed 2026-11-07 (513 tests; full suite 8,307 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B third re-review FAIL 2026-11-07 (one P2, BR6; owner: fix value-blind, then re-review); Part B third review-fix `25e4bcd`, `9875a7c`, `9644715` committed 2026-11-06 (486 tests; full suite 8,280 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B second re-review FAIL 2026-11-06 (three P2, BR3-BR5; owner: fix all three, then re-review); Part B second review-fix `15f0d92`, `75a60f8` committed 2026-11-06 (470 tests; full suite 8,264 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B re-review FAIL 2026-11-06 (two P2, BR1-BR2; owner: fix both, then re-review); Part B review-fix `43ddb46`..`7a9de7d` committed 2026-11-05 (456 tests; full suite 8,250 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); non-CoinGlass collection done on `4cf0993` (evidence `76496db`, private); Part B code review FAIL 2026-11-05 (one P1, five P2, two P3; owner: fix all eight, then re-review); Part B code `3301b16`..`4cf0993` committed 2026-11-05 (296 tests; full suite 8,090 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); Part B started 2026-11-05 (live checks done; owner rulings 9-11: private evidence repository, CoinGlass projection, volume-based delivery check); Part A third independent xHigh re-review PASS 2026-11-05 (no new finding), Part A review closed; third review-fix `3f3a801` (196 tests; full suite 7,990 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); second re-review FAIL 2026-11-05 (one P2, N3); second review-fix `85cfc8f`, `d7d43a0` (owner re-review ruling 8; 193 tests; full suite 7,987 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); re-review FAIL 2026-11-05 (two P2); review-fix `a3bfa6e`..`00ba499` (owner review rulings 6-7; 187 tests; full suite 7,981 passed, 3 skipped, 1 xfailed, 0 failed in 79 min); review FAIL 2026-11-04 (one P1, eight P2, one P3); Part A IMPLEMENTED `1427053` (offline; 117 tests; full suite 7,911 passed, 3 skipped, 1 xfailed); owner rulings 2026-11-04; Part B collection awaits access, the purchase and the evidence-storage decision; plan total USD 29, nothing purchased |
| RBT-004 | `COMPOSE_CHAMPION_ENTRY_DECISION_V1` | DONE — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS (2026-10-31); review FAIL (three P1, three P2, F5 owner-accepted) fixed in `514449c`, N1/N2 in `6318234` — Part A `8ce3e74` (14 roots, inventory `250f9470...a061cb17`, spec rebound `787ddfa2...ca2620f0`), Part B `910dec7` + `e158de9`; 193 composer tests; full suite 7,526 passed, 3 skipped, 1 xfailed, 0 failed in 4295.40s |
| RBT-005 | `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1` | DONE — independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS (2026-11-01); review FAIL (three P1, two P2) fixed in `56ab0ca`, `f69140f` and `5052cbb`, N1 in `dddd6a6` — rulings `1b52760`, Part A `0856352`, Part B `8fdd5a3`; spec rebound `9a619596...15f6313`; 100 management tests (+4 RBT-004, +1 coverage guard); full suite at `dddd6a6` 7,632 passed, 3 skipped, 1 xfailed, 0 failed in 4711.30s |
| RBT-006 | `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1` | IN PROGRESS — owner rulings 1-4 (2026-11-11: ETF launch dates from the frozen CoinGlass history, cross-checked; 182-period folds from each venue's evaluation start; a uniform ±10/±20% sweep grid on all ten BTC-185 parameters; frozen metric definitions); clarifications 3a-3c and 4a; Part A review FAIL 2026-11-11 (four P2, F1-F4, and two P3, F5-F6; owner ruling 3d: sweep the Hold Score thresholds the champion reads; owner: fix all, then re-review); Part A `b167d90` committed 2026-11-11 (full suite 9,039 passed, 3 skipped, 1 xfailed, 0 failed in 80 min); RBT-003 DONE (2026-11-11); RBT-005 DONE; POSTP1-002V2A-T1 PASS / table dependency SATISFIED |
| RBT-007 | `RUN_FIRST_RESEARCH_BACKTEST_V1` | BLOCKED — RBT-006 |
| RBT-008 | `EVALUATE_HOLDOUT_ONCE_V1` | BLOCKED — RBT-007 review PASS |

**Pre-review findings recorded by RBT-002 (2026-10-01).** The section 5A
enumeration finds that four Entry Conviction components (trend, flow,
volatility and structure) consume inputs that no owner, configuration value,
certified definition or Rulebook number defines. They are structurally
incomplete on every evaluation date whatever data is acquired, so EPIC Y
stops for owner decisions (`BLK-TREND-ZSCORE-NORMALISATION`,
`BLK-FLOW-ZSCORE-NORMALISATION`, `BLK-VOLATILITY-RANGE-AND-RETURN`,
`BLK-LEVEL-STRENGTH-INPUTS`). `BLK-SEVERE-CROWDING-STATE` would veto every new
trade, and `BLK-LIFECYCLE-PREDICATES` and `BLK-SETUP-INPUTS` affect RBT-005
and the setup path. Four source and composer semantics need a
`RESEARCH_BACKTEST_POLICY_V4` decision before RBT-001A/RBT-004:
`BLK-LIQUIDATION-HISTORICAL-CENSUS`, `BLK-FUTURES-BASIS-CONTRACT`,
`BLK-STRESS-HARD-VETO-MAPPING` and `BLK-ETF-FUND-UNIVERSE`. Each blocker lists
its proposed rule and its resolution options with their costs in the RBT-002
Implementation Notes. The owner adopted the four V4 data rules and chose the
completion spec on 2026-10-01. The independent review above failed the census,
and so did the re-review of the R1 correction (`906c719`). Correction R2
(`812b968`) passed independent re-review under the policy V5 bounded standard.
RBT-002A is DONE / independent xHigh review PASS under policy V7 (final spec
`9819f84a...5013f`, rebound by RBT-004 Part A to `787ddfa2...ca2620f0` and by
RBT-005's named limitation to `9a619596...15f6313`). RBT-004 is
DONE after its independent xHigh re-review PASS WITH NON-BLOCKING FINDINGS
(2026-10-31); RBT-005 is DONE after its independent xHigh re-review PASS WITH
NON-BLOCKING FINDINGS (2026-11-01); RBT-001A is DONE after its independent
xHigh re-review PASS WITH NON-BLOCKING FINDINGS (2026-11-04); RBT-003 is
DONE after its independent xHigh closure review PASS WITH NON-BLOCKING
FINDINGS (2026-11-11);
the four
adopted data choices stay fixed.

**Answered EPIC Y decision recorded by RBT-001.** Rulebook section 7.5's
positioning score needs futures basis and BTC market cap. Policy V2 gives
neither an availability rule, so as specified every Entry Conviction would be
structurally incomplete. Policy V3 answered this before any run: RBT-002
enumerates the full input surface and RBT-001A extends the reviewed builder.
See the RBT-001 Implementation Notes and review outcome. Next
dependency-satisfied EPIC Y work is **RBT-006** (IN PROGRESS: Part A
committed 2026-11-11, awaiting its independent xHigh review).
RBT-002A closed after independent xHigh review PASS and the separate V7
owner-ruled conformance update (2026-10-03).
EPIC X's next ticket remains **POSTP1-001V2R1**.
