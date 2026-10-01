# EPIC Y — First Research Backtest (Non-Certifying)

Workstream authority for the first real-data backtest of the frozen Phase-1
champion. This document controls EPIC Y (`RBT-xxx`) ticket status, dependencies
and acceptance criteria. It is **not** Phase-1 execution authority: [Structured
Tickets v2.6](bitcoin_swing_predictor_structured_tickets_v2_6.md) keeps that role
and is not modified by this workstream. It is **not** EPIC X or BTC-019 authority.

Governing policy: [`RESEARCH_BACKTEST_POLICY_V3`](../policies/research_backtest_policy_v3.md).
It superseded V2 before any run, adding record-shape availability rules, the
positioning, liquidation and discretionary inputs, and the input-surface
completeness rule. V2 had superseded V1 by naming the market-closure owner.
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
- Persists the inventory under `backtest_evidence/research_backtest_v1/`.
  Nothing is collected by this ticket.

## RBT-001A — `EXTEND_REPLAY_INPUTS_TO_POLICY_V3`

**Status:** `BLOCKED — awaiting RBT-002 only; RBT-001 review PASS / dependency SATISFIED`
**Dependencies:** RBT-001 independent review PASS (SATISFIED, after `a9773e7`), RBT-002
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

**Status:** `BLOCKED — awaiting RBT-001A and RBT-002; RBT-001 review PASS`
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
| RBT-001 | `BUILD_HISTORICAL_REPLAY_INPUTS_V1` | DONE — independent xHigh ticket review PASS after review fix `a9773e7`; implementation `402e120` |
| RBT-002 | `INVENTORY_HISTORICAL_INPUT_COVERAGE_V1` | NOT STARTED / DEPENDENCY-SATISFIED — needs the research database; now includes the policy V3 §5A input-surface enumeration and blocker list |
| RBT-001A | `EXTEND_REPLAY_INPUTS_TO_POLICY_V3` | BLOCKED — RBT-002 only; RBT-001 review dependency SATISFIED |
| RBT-003 | `BACKFILL_HISTORICAL_INPUTS_V1` | BLOCKED — RBT-001A, RBT-002 |
| RBT-004 | `COMPOSE_CHAMPION_ENTRY_DECISION_V1` | NOT STARTED / DEPENDENCY-SATISFIED |
| RBT-005 | `COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1` | BLOCKED — RBT-004 |
| RBT-006 | `FREEZE_RESEARCH_CHAMPION_AND_PREREGISTER_V1` | BLOCKED — RBT-003, RBT-005; POSTP1-002V2A-T1 PASS / table dependency SATISFIED |
| RBT-007 | `RUN_FIRST_RESEARCH_BACKTEST_V1` | BLOCKED — RBT-006 |
| RBT-008 | `EVALUATE_HOLDOUT_ONCE_V1` | BLOCKED — RBT-007 review PASS |

**Answered EPIC Y decision recorded by RBT-001.** Rulebook section 7.5's
positioning score needs futures basis and BTC market cap. Policy V2 gives
neither an availability rule, so as specified every Entry Conviction would be
structurally incomplete. Policy V3 answered this before any run: RBT-002
enumerates the full input surface and RBT-001A extends the reviewed builder.
See the RBT-001 Implementation Notes and review outcome. Next
dependency-satisfied EPIC Y tickets are **RBT-002** (requires the research
database) and **RBT-004**. EPIC X's next ticket remains **POSTP1-001V2R1**.
