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

**Status:** `IMPLEMENTED / AWAITING INDEPENDENT xHIGH REVIEW — CHAMPION_COMPLETION_SPEC_V1 frozen at d9f9b334abfba52b5f5af6a2eefe60616cec170568dbd7c5b310403cef7a80fd under policy V6 §6A; 26 inputs covered (22 defined, 2 omitted by ruling, 2 inert). Both closure-precondition owner rulings were made on 2026-10-03 (policy V7); ruling 2 requires a recorded spec update (guard contract for all three positioning owners, new digest) inside this ticket before closure.`

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

**Status:** `IMPLEMENTED / AWAITING INDEPENDENT xHIGH REVIEW`. Definition digest
`d9f9b334abfba52b5f5af6a2eefe60616cec170568dbd7c5b310403cef7a80fd`, bound to
inventory `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`.
**Two owner rulings are closure preconditions** (see "Surfaced for the owner").
Under AGENTS.md, RBT-002A is not DONE until both are recorded and the
independent review passes.

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
  - The BTC-041 helper returns None for every exactly constant history tested
    (sizes 30–730), so the E1 class cannot recur in spec-defined z-scores.
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

## RBT-001A — `EXTEND_REPLAY_INPUTS_TO_POLICY_V3`

**Status:** `READY — RBT-002 independent R2 re-review PASS under V5 §5A.7; RBT-001 independent review PASS after a9773e7. Policy V4 data rules ADOPTED and governed by V6.`
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

## RBT-003 — `BACKFILL_HISTORICAL_INPUTS_V1`

**Status:** `BLOCKED — awaiting RBT-001A; RBT-002 independent R2 re-review PASS and RBT-001 review PASS`
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

## RBT-004 — `COMPOSE_CHAMPION_ENTRY_DECISION_V1`

**Status:** `BLOCKED — awaiting the RBT-002A review PASS (completion spec)`
**Dependencies:** RBT-002A independent review PASS. Without the spec, every
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
  and `_futures_basis_history`.
- **Declared arithmetic.** It is the complete list of arithmetic the spec allows
  beyond owner calls; "no new formulas" admits exactly that list.
- **E1 guard.** `FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1` (policy V6 §6A.9)
  specifies the futures-basis zero-variance guard, its five tests and its
  prohibitions. Policy V7 §6A.9 extends the guard to `funding_health` and
  `open_interest_growth_health`; the spec's contract is updated within
  RBT-002A before it closes.

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
- The composer-root and runtime completeness guards of policy V6 §5A.6 apply
  to this composer too, with the same regressions.

## RBT-006 — `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1`

**Status:** `BLOCKED — awaiting RBT-003 and RBT-005; closure-table dependency SATISFIED`
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
| RBT-002A | `DEFINE_CHAMPION_COMPLETION_SPEC_V1` | IMPLEMENTED / AWAITING INDEPENDENT xHIGH REVIEW — spec `d9f9b334...a80fd` under V6 §6A (26 inputs; level volume per §6A.8; E1 guard contract per §6A.9); Part 0 `75fc7e6` fixes R2-RR-FS1; both owner rulings made 2026-10-03 (policy V7: Momentum Persistence accepted with a required ablation; zero-variance guard extended to funding and OI growth, needing a recorded spec update with a new digest before closure); next: independent xHigh review, which applies that spec update |
| RBT-001A | `EXTEND_REPLAY_INPUTS_TO_POLICY_V3` | READY — RBT-002 R2 re-review PASS and RBT-001 review PASS; adopted V4 data rules governed by V6 |
| RBT-003 | `BACKFILL_HISTORICAL_INPUTS_V1` | BLOCKED — RBT-001A; RBT-002 review dependency SATISFIED; plan total USD 29, nothing purchased |
| RBT-004 | `COMPOSE_CHAMPION_ENTRY_DECISION_V1` | BLOCKED — RBT-002A review PASS (completion spec) |
| RBT-005 | `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1` | BLOCKED — RBT-004 |
| RBT-006 | `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1` | BLOCKED — RBT-003, RBT-005; POSTP1-002V2A-T1 PASS / table dependency SATISFIED |
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
RBT-002A is now implemented under policy V6 (spec `d9f9b334...a80fd`) and awaits its independent
xHigh review; RBT-001A is also READY; the four adopted data choices stay fixed.

**Answered EPIC Y decision recorded by RBT-001.** Rulebook section 7.5's
positioning score needs futures basis and BTC market cap. Policy V2 gives
neither an availability rule, so as specified every Entry Conviction would be
structurally incomplete. Policy V3 answered this before any run: RBT-002
enumerates the full input surface and RBT-001A extends the reviewed builder.
See the RBT-001 Implementation Notes and review outcome. Next
dependency-satisfied EPIC Y work is the **independent xHigh review of RBT-002A**
(implemented 2026-10-03 under policy V6), with **RBT-001A** also READY. RBT-004
remains blocked on the RBT-002A review PASS.
EPIC X's next ticket remains **POSTP1-001V2R1**.
