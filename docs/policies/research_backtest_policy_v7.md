# Research Backtest Policy V7

Policy identifier: `RESEARCH_BACKTEST_POLICY_V7`

Status: **ADOPTED 2026-10-03 — documentation-only owner decision.
Supersedes [`RESEARCH_BACKTEST_POLICY_V6`](research_backtest_policy_v6.md)
before any EPIC Y run.** (V5, V4, V3, V2 and V1 were superseded the same way.)

## Changes from earlier versions

**V6 → V7 (owner rulings on RBT-002A's closure preconditions).**
`CHAMPION_COMPLETION_SPEC_V1` (implementation `09d14dc`, digest
`d9f9b334abfba52b5f5af6a2eefe60616cec170568dbd7c5b310403cef7a80fd`) raised two
questions for the owner. Both are answered before its independent review:

1. **Momentum Persistence overlap: accepted, with a required ablation
   (§6A.10, §8).**
   - Rulebook §20 gives `MomentumPersistence` 0.1333333 of Hold Score but
     never defines it. The spec defines it as `100 * Phi(TREND_Z_M12)`.
   - `Z_M12` already reaches Hold through Trend, so the factor is counted
     twice.
   - Rulebook §4.1 allows that overlap only when it is explicitly
     intentional, quantified, versioned and validated by ablation or
     sensitivity research. The spec supplies the first three.
   - V7 accepts the definition unchanged. It makes validation a required,
     non-selecting ablation in the RBT-007 report.
2. **The zero-variance guard covers the whole owner class (§6A.9).** Three
   positioning owners share the Decimal z-score helper that causes E1:
   - `funding_health`;
   - `futures_basis_health`;
   - `open_interest_growth_health`.

   V6 guarded only futures basis. V7 applies the same exact-equality guard to
   all three, each with the owner's own zero-variance reason code. That
   follows the RBT-002 re-review's E1 ruling: disclosing a false complete
   score does not justify accepting it.

**Effect on the spec.** Ruling 1 needs no spec change. Ruling 2 changes:
- the spec's guard contract, which must cover all three owners;
- its named limitation for funding and OI growth, which becomes a guarded
  case.

That update is applied inside RBT-002A, before it closes, as a recorded spec
change with a new digest. No real-data outcome exists, so pre-registration
(§6A.1) is unaffected.

**V5 → V6 (owner decisions after RBT-002 closed).** The independent re-review
of RBT-002 correction R2 passed under V5 §5A.7. It left two owner questions open
for RBT-002A and found one inherited test failure. V6 settles all three before
RBT-002A starts:

1. **Level volume is defined by the completion spec (§6A.8).** V5 §6A.2 named
   the Rulebook §9.2 core weights without volume as the example fallback. That
   fallback cannot be used for this champion:
   - the champion's configuration (`strategy_config_v2`,
     `price_levels.level_strength_weights`, from BTC-096) scores volume at
     0.20, and §6 forbids weight changes;
   - the frozen level-strength owner reports a missing volume input as
     incomplete at any weight, by design (BTC-096). It cannot run the
     fallback without a placeholder value, which would be a zero-fill.

   `LEVEL_VOLUME_PERCENTILE` is therefore an owner-less input that
   `CHAMPION_COMPLETION_SPEC_V1` defines, for 26 defined inputs in all.
2. **The futures-basis zero-variance defect (E1) is handled by a composer
   guard (§6A.9).** The frozen `futures_basis_health` owner scores an exactly
   constant basis history as complete. The RBT-004 composer refuses that case
   instead. No owner is changed.
3. **EPIC Y code is isolated from BTC-019 research modules (§9).** Since its
   first commit (`ab210a5`), `research_backtest/coverage.py` has imported the
   database helper from `btc019_empirical`. The BTC-019 isolation test forbids
   that import outside `btc_predictor/research/`, so the full suite has one
   failure (R2-RR-FS1). EPIC Y reads the database environment through its own
   helper instead. The BTC-019 test is not edited.

The reviewed RBT-002 inventory
`108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` stays the
reviewed inventory and is not regenerated for V6:
- its `RESEARCH_BACKTEST_POLICY_V5` label records the policy it was reviewed
  under;
- its `RULEBOOK_FALLBACK_EXISTS` row for `LEVEL_VOLUME_PERCENTILE` is
  superseded for the champion by §6A.8, and the spec covers that row;
- no §4 or §5A rule the inventory applies has changed.

EPIC Y ticket text that cites the §9.2 fallback for `LEVEL_VOLUME_PERCENTILE`
is superseded by §6A.8. RBT-002A brings that text into line.

**V4 → V5 (owner decision on how RBT-002 closes).** RBT-002 failed review twice
on the same ground: its census could not prove it had found every parameter of
every callable it reached. The latest miss was a nested result-builder inside
the trailing-stop owner. Every call to it supplies a fixed reason string and
values the owner computed itself, so no caller can supply its parameters.

The reviews also established that static analysis of Python code cannot prove
universal completeness. It cannot see enclosing-local callbacks, unnamed
Protocol implementations or `getattr` dispatch, and code that never runs gives
no evidence at all. A missed input also cannot silently corrupt a run:
- a missed *undefined* input reaches its owner as `None`, so the owner
  returns an incomplete result and the decision is unevaluable;
- a missed *defaulted* input runs the owner's own defined default.

V5 therefore re-scopes §5A:
- the census covers the **external input surface**, with its limits stated;
- a **runtime completeness guard** in RBT-004, RBT-005 and RBT-006 backs it at
  the point that matters;
- RBT-002 closes on a **bounded standard** (§5A.5–§5A.7).

**V3 → V4 (owner decisions on the RBT-002 blocker list).** RBT-002's
mechanical enumeration (inventory `b7b9a20b…be3bf0`) found two kinds of gap:

1. **Four data-plumbing rules**, adopted here verbatim as proposed (all $0):
   - `HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1` (§4A);
   - `FUTURES_BASIS_CONTRACT_V1` (§4A);
   - the STRESS hard-veto mapping (§7);
   - the per-window ETF fund universe (§5).
2. **Undefined strategy inputs.** About 24 inputs that the Entry Conviction
   components, the hard veto, the lifecycle owners and one setup consume have
   no definition in any owner, config, certified contract or Rulebook text.
   Trend, flow, volatility and structure can therefore never be complete. The
   owner chose to fill them with a **pre-registered, versioned completion
   spec**, `CHAMPION_COMPLETION_SPEC_V1`, authored by RBT-002A under the binding
   rules in §6A. The champion identity (§6) now includes that spec.

**V2 → V3.** RBT-001 found that the policy named no rule for inputs the
champion cannot do without. Positioning (Rulebook §7.5) needs futures basis
(`BasisHealth`) and BTC market cap (`LeverageHealth`, through OI intensity),
and the Rulebook gives positioning **no** fallback. The volatility orderliness
owner and the STRESS / CAPITULATION / EUPHORIA flags also consume liquidation,
basis and manually asserted inputs that V2 never mentioned. Adding the missing
inputs one at a time would cost a policy version per gap, so V3 instead:

1. replaces the per-family availability list with **record-shape rules**
   (`HISTORICAL_REPLAY_AVAILABILITY_V2`, §4), which every current and future
   input falls under;
2. adds explicit rows for futures basis, liquidations, market cap and
   discretionary assertions (§4, §5);
3. adds an **input-surface completeness rule** (§5A). RBT-002 must enumerate,
   mechanically, every input the champion's decision path consumes, map each
   one to a shape, a source and coverage, and stop on any gap, before anything
   is collected.

**V1 → V2.** V2 bound `US_EQUITY_MARKET_CLOSURE_TABLE_V1` as the flow owner's
`market_holidays` set (§5).

No EPIC Y run has happened under V1 or V2.

## Why this policy exists

The repository contains a complete event-driven backtester (BTC-180..185) but has
never run it on real market data. The only route to such a run in the existing
plan is the end of EPIC X: certification of the ETF publication calendar, then
the V2 corpus correction, sufficiency governance, collectors, open-ended
prospective collection, Stage-B evaluation, a separately governed promotion
protocol and finally a `PRICE_SOURCE_POLICY_V2` canonical reference. The ETF
calendar alone had consumed 18 frozen candidates by the date of this decision.
Waiting on that chain would leave the core research question —
*what did the Phase-1 champion actually do on real data?* — unanswered for an
indefinite period.

This policy opens a separate, bounded, explicitly non-certifying path to that
answer without weakening any certification gate.

## Authority basis

- [Structured Tickets v2.6](../execution/bitcoin_swing_predictor_structured_tickets_v2_6.md)
  (BTC-019, V2 protocol note) already states: *"Normal Phase-1 implementation may
  continue with an injectable/versioned reference price abstraction, but final
  authoritative strategy calibration/certification remains blocked until the
  production canonical reference is resolved."* This policy operates strictly
  inside that permission: every run is per-reference-venue research, and nothing
  here calibrates or certifies.
- [PRICE_SOURCE_POLICY_V1](price_source_policy_v1.md) is **not modified**. No
  canonical source is approved, implied or ranked. `BTC_REFERENCE_COMPOSITE_V1`
  remains not approved and is not used.
- [Rulebook v1.2](../strategy/bitcoin_swing_predictor_rulebook_v1_2.md) is **not
  modified**. This policy only invokes the Rulebook's own Phase-1 fallbacks
  (§6.2 flow `ETF_CORE`; the core regime fallback) and its §24 hard-flag effects.
  It adds no strategy semantics of its own. Owner-less inputs are completed only
  by the pre-registered `CHAMPION_COMPLETION_SPEC_V1` (§6A), which belongs to a
  research strategy version (§6).
- [EPIC X](../execution/post_phase1_prospective_integration_evidence_v1.md) and
  BTC-019 are **untouched**. No EPIC X ticket depends on EPIC Y. EPIC Y depends
  on exactly one EPIC X output: the reviewed `US_EQUITY_MARKET_CLOSURE_TABLE_V1`
  artifact. It does not depend on any other EPIC X ticket, status or evidence.

## 1. Evidence class and prohibited uses

Every EPIC Y artifact carries:

```text
evidence_class       = RESEARCH_BACKTEST_NON_CERTIFYING
canonical_reference  = UNRESOLVED
policy               = RESEARCH_BACKTEST_POLICY_V7
```

EPIC Y output may **never** be used to:

- certify Phase 1.5 or any champion;
- approve, rank or promote a price reference, composite or venue;
- calibrate, select or tune a production parameter or threshold;
- serve as BTC-019, V3/V4/V5 or EPIC X evidence of any kind;
- authorize prospective collection, live shadow or capital deployment.

A later certifying backtest must re-run the EPIC Y pipeline on the approved
canonical reference under its own certification authority; EPIC Y results do
not carry over.

## 2. Reference series: one venue per run, never combined

- Each run replays exactly one required venue from `PRICE_SOURCE_POLICY_V1`:
  Bitstamp `BTC/USD` (`btcusd`), Coinbase `BTC-USD`, or Bitfinex `tBTCUSD`.
  All three are run; none is labelled canonical or primary.
- No composite, no splicing, no fallback. A venue gap remains a gap (the engine
  already refuses provider splicing).
- The replay stream is the venue's persisted `1h` series. Daily, weekly and
  monthly bars derive from it at each decision instant through the existing
  BTC-040 owner (`build_canonical_market_bars`), with the decision instant as
  its point-in-time cutoff.
- Execution is modelled on the same venue's bars under the BTC-181 cost ladder.
  This is a modelling convention, not an execution-venue selection.
- **Only the reference price varies between the three runs.** Every other input
  — ETF flows, derivatives, raw volume — is one shared snapshot. Volume and
  spot-participation inputs use the retained primary raw OHLCV source named by
  `PRICE_SOURCE_POLICY_V1` (Bitstamp) in all three runs.

## 3. Windows

| Window | Bounds (UTC) | Rule |
| --- | --- | --- |
| Prohibited | everything before `2020-01-01 00:00` | Contains the sealed BTC-019 sample (`2015-07-20 21:00` .. `2019-11-30 23:00`). Nothing before 2020 may be collected, read or used, including indicator warm-up. |
| Data window | `2020-01-01 00:00` .. `2025-12-31 23:00` | All warm-up and evaluation data come from here. |
| Evaluation window | first evaluable decision .. `2025-12-31 23:00` | The start is computed mechanically (RBT-002), never chosen: it is the first daily decision instant at which every Entry Conviction component and the core regime score are complete on that venue. |
| Holdout | `2026-01-01 00:00` .. `2026-06-30 23:00` | **NOT COLLECTED.** It may be collected and evaluated exactly once, by RBT-008, after the RBT-007 review passes. |
| Reserve | `2026-07-01 00:00` onward | Not used by EPIC Y. It is kept as a further untouched sample for any later strategy version. |

**Structural finding recorded by this decision.** Entry Conviction has a flow
component, and the Rulebook §6.2 core flow model requires ETF-flow inputs
(`etf_norm_5`, `etf_norm_20`, `flow_accel`). US spot bitcoin ETFs began trading
on 2024-01-11, so before then the champion's flow score cannot be complete.
The owner code returns an incomplete score rather than a zero, so every
decision before ETF-flow warm-up completes is structurally `NO TRADE`. This is
correct fail-closed behaviour, not a defect, and it bounds the champion's own
backtestable history to roughly 2024 onward. Reports must count those decision
dates as `STRUCTURALLY_UNEVALUABLE`, never as "the strategy chose not to trade".

The holdout was chosen because no 2026 market observation has been persisted in
the repository's research or evidence artifacts: the price-source study ends at
2025-12-31, and its only 2026 timestamps are collection times. The holdout
includes ETF flows, and its data is complete as of this decision. RBT-002 must
confirm that no holdout-window observation already sits in the research
database; if one does, it records that exposure instead of silently accepting
it.

## 4. Historical replay availability — `HISTORICAL_REPLAY_AVAILABILITY_V2`

Backfilled records carry a bulk ingestion time. Treated as live availability,
that time makes a correctly built dataset replay with no executable decision
(EPIC S audit). EPIC Y therefore models availability explicitly, by **record
shape**. Every input the champion consumes must be assigned exactly one shape
(§5A).

| Shape | Meaning | Modelled availability |
| --- | --- | --- |
| `INTERVAL` | an aggregate over `[s, e)` (a bar, a volume or liquidation total) | `e` |
| `SNAPSHOT` | a value as of instant `t` (open interest, a basis quote) | `t` |
| `SETTLEMENT` | a value fixed at settlement `S` (funding) | `S` |
| `EVENT` | an instantaneous event at `t` (a single liquidation) | `t` |
| `DAILY_PUBLISHED` | a value for date `D` published by a third party (ETF flows and AUM, market cap) | `00:00` UTC on calendar day `D+2`, or the source's own later publication or revision time if it supplies one |
| `DISCRETIONARY` | a manual or judgemental assertion (`systemic_shock`, `systemic_euphoria`) | **never back-filled.** It is supplied as not asserted (`None`), the owner's documented handling applies, and it is reported as a named limitation, because any historical value would be chosen with hindsight |

Current assignments:

| Input family | Shape | Modelled availability |
| --- | --- | --- |
| `1h` price bar, reference venue | `INTERVAL` | its close boundary (`timestamp + 1h`) |
| Derived daily / weekly / monthly bar | `INTERVAL` | the close boundary of its last constituent hour |
| ETF flow and AUM, fund `f`, US trading date `T` | `DAILY_PUBLISHED` | `00:00` UTC on `T+2`, or the source's later time |
| Funding rate | `SETTLEMENT` | settlement time `S` |
| Open interest | `SNAPSHOT` | snapshot instant |
| Perpetual volume | `INTERVAL` | interval end. If the persisted timestamp is the interval start, the end is computed from the interval length; never earlier |
| Futures basis (`futures_basis` raw table) | `SNAPSHOT` or `INTERVAL`, by its persisted semantics, which RBT-002 determines | the snapshot instant, or the interval end |
| Liquidations (`liquidations` raw table) | `EVENT`, or `INTERVAL` if persisted as aggregates | event time, or the interval end |
| BTC market cap (`MarketCapObservation`) | `DAILY_PUBLISHED` | `00:00` UTC on `D+2`, or the provider's later time |
| `systemic_shock`, `systemic_euphoria` and any other manual assertion | `DISCRETIONARY` | not asserted (`None`) |

Rules:

- Raw persisted facts are immutable. `ingested_at` in the database is never
  rewritten. The replay builder produces **derived replay inputs** and records,
  for every input, both the true raw ingestion time and the modelled
  availability, plus this policy version, in the dataset manifest.
- The frozen engine's only availability input for a bar is
  `OhlcvBar.ingested_at`. A derived replay bar therefore carries its modelled
  availability in that field, and the same applies wherever a frozen owner's
  point-in-time predicate reads an ingestion field. That field meaning holds
  only inside EPIC Y replay inputs; the manifest keeps the raw value beside it.
- Price bars are modelled as available at their close boundary. This is the
  engine's native convention, the same one the BTC-224 golden scenarios use.
  EPIC X's `bar close + 5 minutes` decision instant is **not** adopted here: the
  frozen BTC-162 stop owner resolves a stop at `max(close, ingested_at)`, so any
  positive delay would stamp every stop resolution after the following bar's
  start, and modifying that owner is prohibited by §9. Exchange `1h` candles
  are final at close, and every decision still executes only on a later bar, so
  this convention introduces no look-ahead.
- The `DAILY_PUBLISHED` `D+2 00:00` rule is deliberately conservative. For
  ETF flows, the `T+2 00:00` rule: a daily flow is first
  usable one full day after the US session it describes. It is **not**
  `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` and makes no claim about it.
- If a source provides only final (revised) values with no revision history,
  each affected record is labelled `REVISION_HISTORY_UNAVAILABLE` and counted
  in the report. For non-certifying research this is an accepted limitation.
- Modelled availability is never earlier than the observation's close or end.

## 4A. Adopted data rules

**`HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`**, adopted verbatim:

> An hour [h, h+1) of PI_XBTUSD is OBSERVED when the paginated REST execution
> log was read contiguously across it (unbroken continuation chain, no error)
> and at least one execution of any order type is stamped in it; zero
> Liquidation-typed fills then make OBSERVED_ZERO_EVENTS. An hour with no
> execution at all, or a Tardis-reported incident hour, is SOURCE_UNAVAILABLE.
> Kraken's hourly liquidation-volume series must agree within rounding. Days
> still need all 24 OBSERVED hours; the percentile adapter is otherwise
> unchanged.

It replaces, for historical replay only, the live-capture evidence that EPIC
X's `LIQUIDATION_UTC_DAY_CENSUS_V1` requires. Everything else is reused by
reference, unchanged, from EPIC X's certified definitions:
- the universe (Kraken Futures `PI_XBTUSD`);
- the quantity (daily long-plus-short USD);
- the window and minimum (730 days, 365 observations);
- the midrank percentile convention.

The source is Kraken Futures REST execution history (`$0`, measured depth
from 2021-05-27). This rule makes no claim about EPIC X.

**`FUTURES_BASIS_CONTRACT_V1`**, adopted verbatim:

> Binance COIN-M BTCUSD quarterly delivery contracts listed at t, basis_rate =
> futures 1h close / COIN-M BTCUSD index 1h close - 1 at the hour close t
> (SNAPSHOT), annualized_basis_rate = basis_rate * 365 days / (expiry - t),
> contracts within 7 days of expiry excluded; expiry = the contract's delivery
> instant.

The BTC-021 collector defines no contract, so this rule is the definition for
EPIC Y. The owner `futures_basis_health` averages every row that shares an
`observation_time`, unchanged.

## 5. Input families and Rulebook fallbacks

| Family | EPIC Y treatment |
| --- | --- |
| Reference price (`1h`) | Required, per venue |
| Raw volume / spot participation | Bitstamp raw OHLCV, shared across all runs. It is also the only volume source for the spec-defined `LEVEL_VOLUME_PERCENTILE` (§6A.8) |
| ETF flows + AUM | Required for any trade; backfilled with §4 availability. **Fund universe (adopted verbatim):** per decision, pass funds = the funds with a first US trading date on or before the window's first included publication date; record each fund's launch date with its source evidence. Pre-launch rows are never invented |
| Funding, open interest | Required. Positioning (an Entry Conviction component) has no Rulebook fallback |
| Futures basis | **Required.** It feeds `BasisHealth` (positioning, no fallback) and the STRESS / EUPHORIA flags. It comes from the existing `futures_basis` raw table under `FUTURES_BASIS_CONTRACT_V1` (§4A), sourced from Binance COIN-M quarterly and index history ($0) |
| BTC market cap | **Required.** It feeds `LeverageHealth` through OI intensity (positioning, no fallback) and the EUPHORIA flag. No raw table or collector exists. It is one declared provider series, shared across all venue runs (never derived from a per-venue reference price), persisted as hash-bound evidence files under `backtest_evidence/` because §9 forbids a schema migration. RBT-002 selects the provider; a public, reproducible source is preferred |
| Liquidations | **Required** wherever an Entry Conviction component consumes them (the volatility orderliness owner's liquidation component) and for the STRESS / CAPITULATION flags. It comes from the existing `liquidations` raw table, as per-side hourly aggregates for Kraken Futures `PI_XBTUSD`, under `HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1` (§4A). `liquidation_percentile` reuses EPIC X's certified adapter by reference |
| Perpetual volume | A flow spot/perp participation input. Under `ETF_CORE` it does not enter the flow score. It is retained for any owner RBT-002 finds consuming it; no positioning owner consumes it |
| Discretionary assertions (`systemic_shock`, `systemic_euphoria`) | Not asserted (`DISCRETIONARY`, §4), and reported as named limitations together with the owner's documented handling of `None` |
| US equity market full-day closures (the flow owner's `market_holidays`) | **`US_EQUITY_MARKET_CLOSURE_TABLE_V1`**, loaded and hash-verified by its owner module and passed to the existing `market_holidays` parameter. Required, and only after the `POSTP1-002V2A-T1` review passes. A date on which a flow window is evaluated that falls outside the table's coverage blocks the RBT-006 freeze. |
| CVD (`SPOT_CVD`, `PERP_CVD`, `CVD_SPREAD`) | **Absent**: no persisted PIT source exists. The Rulebook §6.2 Phase-1 fallback applies mechanically: `FLOW_MODEL = ETF_CORE`. |
| Macro, on-chain, liquidity | **Declared unavailable.** Vintage-correct point-in-time history is not established, and revised series would leak. The Rulebook core regime fallback applies. |

Missing values are never zero-filled. Where the frozen owner code returns an
incomplete result, that result propagates as the owner defines it.

## 5A. Input-surface completeness

The policy may never again learn of a required input piecemeal. Before any
collection:

1. **Mechanical enumeration of the external input surface.** RBT-002
   enumerates, from owner code and not from this document, everything a
   caller of the champion's decision path must or can supply:
   - every parameter of each declared census root (the owner entry points a
     composer calls);
   - every field of every input-bearing type reachable from those parameters,
     followed transitively through fields;
   - every configuration value the reached owners read;
   - every defaulted parameter of a reached public callable, classified as a
     fixed owner default.

   Nested, local and private helpers must still be **discovered**. Each is
   classified `OWNER_INTERNAL` when every call site inside the owner supplies
   only owner-computed values or literals. Otherwise it is classified as part
   of the external surface. Nothing may be exempted from discovery.

   The enumeration is a test-backed artifact that fails if a root's parameters,
   a reachable input type's fields or a reached helper's signature change
   without being classified.
2. **Mapping.** Each input is mapped to a §4 shape, a §5 family, a historical
   source (an existing raw table and collector, or a named provider adapter)
   and coverage over every date on which it is evaluated.
3. **Missing-input semantics.** For each input, record what the owner does when
   it is missing: incomplete, a reason code, or a documented `None` handling.
   Fallbacks exist only where the Rulebook defines them (§6.2 flow `ETF_CORE`;
   the core regime). No implementer may add or infer a fallback.
4. **Blockers.** Any input with no shape, no family, no historical source or
   insufficient coverage is a **blocker**, recorded before RBT-003 starts. If a
   blocker would leave an Entry Conviction component structurally incomplete
   on every evaluation date, EPIC Y stops for an **owner decision**. The
   options are to acquire the data (including a paid source), or to define an
   explicitly versioned research strategy variant. The second is a
   strategy-semantics change under AGENTS.md and is never made silently.
5. **Stated limits, not a universal proof.** The census claims completeness
   for static discovery plus the runtime trace over the paths actually
   exercised. It must list its known limits:
   - enclosing-local callbacks;
   - unnamed Protocol implementations;
   - dynamic `getattr` dispatch;
   - unexecuted branches, with their measured line and branch coverage.
   No tracer exemption may hide an omission. An exempted frame's callees are
   still checked against the static set.
6. **Runtime completeness guard (binding on RBT-004, RBT-005 and RBT-006).**
   - Every owner function a composer calls directly must be a census root.
     This is checked statically and at runtime, with a regression in which a
     newly added direct call fails.
   - In every composed replay, any owner result that is incomplete or carries
     a missing-input reason code must map to a cause accounted for in the
     reviewed inventory or in `CHAMPION_COMPLETION_SPEC_V1`. Examples are
     ETF warm-up (`STRUCTURALLY_UNEVALUABLE`), a named limitation, or a
     discretionary input that is not asserted. The replays are the
     RBT-004/RBT-005 fixtures and RBT-006's completeness-only real-data pass.
   - An unaccounted incomplete result **fails the test** in RBT-004/RBT-005,
     and **blocks the freeze** in RBT-006.
   - When the guard finds a missing external input, it is added to the
     inventory and the spec through a recorded update, never by improvising a
     value.
   - The guard computes no outcome beyond what each ticket already allows.
7. **Bounded closure of RBT-002.** RBT-002 closes when an independent
   re-review confirms all of the following:
   - the two R1 method defects are fixed, with regressions: nested callables
     are discovered and classified, and no tracer exemption masks an
     omission;
   - the external input surface is correctly classified;
   - the §5A.5 limits are stated, with measured coverage;
   - the live database facts are reproduced read-only.
   Further gaps in the census *method* that do not reveal a missing external
   input are recorded as limitations, not blockers.

## 6. Champion identity and the no-tuning rule

- The champion is the repository strategy configuration
  (`strategy_version = swing_v1.2`, `config_version = strategy_config_v2`,
  `parameter_set_id = default_phase1`) **plus `CHAMPION_COMPLETION_SPEC_V1`**,
  at the code commit frozen by RBT-006, composed by the RBT-004/RBT-005
  composer.
- Its research identifier is `swing_v1.2+completion_v1`. It is a research
  strategy version. It does not replace `swing_v1.2` for advisory, paper or
  EPIC X use. Adopting the spec anywhere else needs that workstream's own
  decision.
- No parameter, threshold, weight or rule changes during EPIC Y. BTC-185
  threshold sweeps may be reported as sensitivity, labelled
  `SENSITIVITY_ONLY_NOT_SELECTION`, and never select a value.
- Any post-result change creates a new strategy version. Such a version can
  never claim evidence from the evaluation window or the opened holdout.

## 6A. Binding rules for `CHAMPION_COMPLETION_SPEC_V1`

The spec defines every input that RBT-002's inventory (as confirmed by its
independent review) marks owner-less and undefined. It must follow these rules,
which are the owner's decision:

1. **Pre-registration.**
   - The spec is authored, frozen by hash and reviewed before any backtest
     output exists.
   - No real-data score, signal, trade or performance figure may be computed
     or inspected while drafting it. Input-availability facts, such as warm-up
     and coverage dates, are allowed.
   - Considering how a window affects the evaluation span is allowed, because
     that is data availability, not outcome.
2. **Source precedence.** For each input, use the first that applies:
   1. explicit Rulebook formulas or numbers;
   2. explicit Rulebook fallbacks that the champion's configuration and its
      frozen owners can run without a placeholder value. The §9.2 core
      level-strength weights without volume do not qualify (§6A.8);
   3. existing owner conventions and helpers (the BTC-041 prior-window z-score
      and percentile helpers; `volatility_percentile`'s 730-day window with a
      365-observation minimum; the positioning 180-day funding z-score; EPIC X
      certified definitions);
   4. existing configuration thresholds and interpretation bands;
   5. only then a new value, labelled `NEW_PARAMETER`, with a one-line
      rationale.
3. **Uniformity.**
   - One normalisation rule for every undefined z-score (window, minimum,
     degrees of freedom, prior-window exclusion).
   - One rule for every undefined percentile.
   - Exceptions only where the Rulebook distinguishes inputs.
   - No per-input tuning.
4. **Predicates.** Qualitative predicates (hold, add, exit, regime and flow
   "supportive", new structure, data-risk exit) map to existing owner outputs
   and thresholds. No new indicator is introduced.
5. **Conservatism.** Where the Rulebook is ambiguous, choose the reading that
   trades less. For example, severe crowding = the existing CROWDING flag.
6. **Scope.** Long-only, as `backtest.allow_short_trades = false`; short-only
   inputs stay inert and are listed.
7. **Form.** A frozen, hash-bound definition maps every covered input to its
   rule and the owner helpers it uses. A test fails if any owner-less input in
   the reviewed inventory is uncovered, or covered twice. The composers
   (RBT-004/RBT-005) implement the spec by calling owner helpers; the spec
   itself adds no executable formula beyond what it declares.
8. **Level volume (`LEVEL_VOLUME_PERCENTILE`, owner decision 2026-10-02).**
   The spec defines the `volume_percentile` input of the frozen level-strength
   owner (`btc_predictor.levels.strength`). The configured weights stay as they
   are: 0.20 each for timeframe, touches, reaction, volume and confluence.
   - **Source.** Bitstamp raw `1h` volume, the shared volume source of §2, in
     all three venue runs. No other venue's volume and no composite is used.
   - **Quantity.** The spec defines once which hours' volume is attributed to
     a level. It may use only:
     - the level, touch and reaction records the existing level owners
       produce;
     - the shared volume series.
     It adds no price-level detection and no volume-profile binning. A choice
     that §6A.2 tiers 1–4 do not supply is labelled `NEW_PARAMETER`, with its
     one-line rationale.
   - **Normalisation.** The quantity becomes 0–100 through the spec's single
     uniform percentile rule (§6A.3), computed against the prior window of the
     same quantity, with the current value excluded. There is no separate
     window, minimum or tuning for volume.
   - **Point in time.** Only hours available at the decision instant under §4
     are used.
   - **Missing values.** Volume is never zero-filled. Until the percentile's
     minimum history is met, the owner's incomplete result stands. That case
     is a declared warm-up cause for the §5A.6 guard.
   - **Pre-registration.** The definition is fixed before any outcome exists
     (§6A.1). RBT-002A states its computed warm-up date. That date is an
     availability fact; it is expected to fall well before the ETF warm-up
     that already bounds the evaluation start (§3).
9. **Positioning zero variance (E1; owner decisions 2026-10-02 for futures
   basis, extended 2026-10-03 to the whole class).**
   - *The defect.* Three frozen owners in `btc_predictor/features/positioning.py`
     call the same Decimal `_zscore` helper:

     | owner | prior history it z-scores | its own zero-variance reason code |
     | --- | --- | --- |
     | `funding_health` | the 7-day funding averages | `FUNDING_HEALTH_ZERO_VARIANCE` |
     | `futures_basis_health` | the annualized-basis averages | `FUTURES_BASIS_ZERO_VARIANCE` |
     | `open_interest_growth_health` | the OI growth values | `OI_GROWTH_ZERO_VARIANCE` |

     Decimal sum and mean rounding can leave a nonzero variance on an exactly
     constant history. The owner then returns a complete score (z = 1) where
     it promises a zero-variance refusal. The RBT-002 re-review reproduced
     this for futures basis. The other two share the helper and the risk.
   - *Spec duty.* The spec defines the guard contract for all three owners,
     as one generalized contract or one contract per owner. Each owner's
     residual risk is recorded as a guarded limitation.
   - *Guard.* The RBT-004 composer applies an equality guard to each of the
     three owners. At each decision instant it reads that owner's own
     point-in-time prior history, through the owner's aggregation and history
     helpers. A helper it calls directly becomes a classified census root
     (§5A.6). If every value in that prior history is exactly equal, the
     guard:
     - refuses with that owner's own reason code from the table;
     - passes on no health score or z-score;
     - records the positioning component as structurally unevaluable at that
       instant, which is an accounted cause under §5A.6.

     This holds whether or not the current value equals that history.
   - *Prohibited.* The guard never reimplements the z-score and never
     substitutes zero. It uses no tolerance: only exact Decimal equality.
   - *Tests.* RBT-004 tests these cases for each of the three owners:
     - a constant history;
     - a current value equal to that constant history;
     - a current value that differs from it;
     - point-in-time exclusion of later rows;
     - unchanged results on non-constant histories.
   - *Owner fix.* Fixing any of the owners would need a separate
     cross-workstream decision. None is authorized.
10. **Momentum Persistence (owner decision 2026-10-03).**
    - *Ruling.* The spec's `MOMENTUM_PERSISTENCE_SCORE = 100 * Phi(TREND_Z_M12)`
      is accepted unchanged.
    - *Overlap.* The factor reaches Hold twice:
      - through Trend: Hold weight 0.2666667 on Trend, whose argument
        carries `0.30 Z_M12`;
      - directly: Hold weight 0.1333333.

      The overlap is intentional, quantified by these weights, and versioned
      by `CHAMPION_COMPLETION_SPEC_V1`.
    - *Validation.* Rulebook §4.1's fourth condition is met by the required
      ablation in §8. The ablation is reported, never selected.
    - *Changes.* Changing the definition after any result exists creates a
      new strategy version (§6).

## 7. Known strategy-semantics limitations

The EPIC E, EPIC I and EPIC S audits already pin these behaviours by test. EPIC
Y freezes them unchanged and reports each one as a named limitation, with its
exposure counts per venue:

- the weekly swing detector's row-versus-session reading across gaps;
- `realized_volatility_from_daily_bars` reading a gapped series as contiguous;
- the BTC-186 fifth candidate's undeclared features (irrelevant to the champion,
  which EPIC Y does not extend).

**Rulebook §24 NO ADDING.** STRESS, CROWDING and EUPHORIA each carry the explicit
effect `NO ADDING`. The EPIC P audit found that the composed Phase-1 chain can
permit an ADD while CROWDING is active, because nothing emits `DEFEND`. It left
the *lifecycle-state mapping* open as a strategy decision. The EPIC Y composer
does not choose that mapping. It enforces the Rulebook's stated effect directly:
no ADD intent is issued while any of those three flags is active. Each
suppressed ADD is recorded as `RULEBOOK_24_NO_ADDING_ENFORCED`.

**STRESS hard-veto mapping (adopted verbatim, V4).** Pass
`StressFlagResult.flagged` and record `STRESS_INPUT_MISSING` in
`source_reason_codes` when the only missing input is DISCRETIONARY. Because
`trim_rules_from_results` passes `None`, EUPHORIA trims never fire. That is a
named limitation.

## 8. Required report contents (per venue and cost rung)

- Every Rulebook §28 primary metric under the BTC-181 `optimistic`, `base` and
  `stress` cost rungs. `base` is the headline.
- The trade count next to every rate. No performance statement appears without
  its trade count, and no significance claim is made that the sample cannot
  support.
- A decision ledger for every daily decision instant: its outcome and reason
  (trade intent, `NO TRADE` with the hard-veto or data-quality reason, or
  `STRUCTURALLY_UNEVALUABLE`).
- BTC-182 walk-forward under `INDEPENDENT_FOLD_CAPITAL_V1`, using the fold
  scheme pre-registered by RBT-006. The champion is not re-fitted per fold;
  folds measure stability through time.
- BTC-183 regime and BTC-184 setup breakdowns.
- Cross-venue source sensitivity (Rulebook §28): trade-set overlap, per-matched-trade
  entry/stop/exit/MFE/MAE divergence, stop-touch divergence and metric
  dispersion across the three venues.
- Input coverage: per-family coverage and gap counts, `REVISION_HISTORY_UNAVAILABLE`
  counts and the §7 limitation exposure counts.
- **Momentum Persistence ablation (§6A.10).** This is the validation that
  Rulebook §4.1 requires. It is labelled `SENSITIVITY_ONLY_NOT_SELECTION`.
  - *The variant.* Hold Score without the `MomentumPersistence` term, with the
    other four weights re-normalized proportionally. That is the same
    re-normalization Rulebook §20 used when it removed Regime. RBT-006 freezes
    the variant together with the champion.
  - *What is reported.* For the evaluation window only, per venue, under the
    `base` cost rung:
    1. the number of Hold evaluations whose §20 action band differs between
       the champion and the variant;
    2. a full replay with the variant, beside the champion's §28 primary
       metrics, with trade counts.
  - *Limits.* The ablation never runs on the holdout, never replaces the
    champion and never selects a variant. A later change in response to it is
    a new strategy version (§6).

## 9. Integrity, isolation and review standard

- **Additive-only rule.** EPIC Y may not modify:
  - any file bound by an EPIC X frozen candidate or certified authority: the
    120-module worker source universe at `7ffbf157...a44e8e` (this includes
    `btc_predictor/backtest/`, `portfolio/`, `features/`, `risk/`, `signals/`,
    `levels/`, `data/`, `db/`, `quant/` and `config/` modules), the 116-module
    PRE-I2 fixture, the four bootstrap files and `etf_calendar_worker/`;
  - any file under `data/` or `research_artifacts/`, because the V5 terminal
    assessment hashes every JSON there.

  EPIC Y code lives in new modules that import the existing owners, and in new
  test modules.
- **Isolation from BTC-019 research modules.** EPIC Y modules outside
  `btc_predictor/research/` and `btc_predictor/tests/` may not import the
  research-only modules that
  `btc_predictor/tests/test_btc019_completion_gate.py::test_no_production_module_reads_a_research_reference_candidate`
  guards. These are `reference_composite`, `btc019_empirical`,
  `btc019b_diagnostics`, `price_source_policy` and `btc019_completion_gate`.
  The ban covers function-local imports too.
  - EPIC Y reads the database environment through its own helper in
    `btc_predictor/research_backtest/`. That helper reads the same five
    `POSTGRES_*` names and never prints or persists them.
  - The BTC-019 test is never edited, exempted or bypassed (for example by an
    `importlib` string import). A need that can only be met by editing a bound module is
  recorded as a cross-workstream blocker for an explicit decision, never worked
  around. No database schema migration is performed.
- Every EPIC Y implementation ticket must show that V5 still recomputes to
  `95e43ee1...775a89` and that the current EPIC X candidate's focused suite still
  passes unchanged.
- The Phase-1 integrity standard applies in full: point-in-time correctness,
  deterministic replay, persisted provenance and versions, no zero-fill, and
  shared owner formulas across the advisory, paper and backtest paths.
- EPIC Y does **not** adopt EPIC X's same-process adversarial proof-architecture
  threat model. Its tickets receive independent xHigh ticket reviews under
  [`prompts/review_ticket.md`](../../prompts/review_ticket.md), not exact-hash
  proof-architecture reviews.

## 10. Artifact location

EPIC Y artifacts are persisted under `backtest_evidence/research_backtest_v1/`.
That location is outside `data/` and `research_artifacts/`, for the same reason
EPIC X uses `prospective_evidence/`. Each run persists a dataset manifest and a
run manifest (code commit, champion identity, policy versions, cost rung, venue,
windows) and is reproducible byte-for-byte from them.

## 11. Change control

Any change to §2–§8 requires a new policy version (`RESEARCH_BACKTEST_POLICY_V8`)
recorded before the affected run. The holdout rule in §3 cannot be relaxed for
any strategy version that has already been evaluated on the evaluation window.
