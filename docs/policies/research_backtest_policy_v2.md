# Research Backtest Policy V2

Policy identifier: `RESEARCH_BACKTEST_POLICY_V2`

Status: **ADOPTED 2026-09-29 — documentation-only governance decision.
Supersedes [`RESEARCH_BACKTEST_POLICY_V1`](research_backtest_policy_v1.md)
before any EPIC Y run.**

Scope: historical, **non-certifying** research backtests of the frozen Phase-1
champion executed under [EPIC Y](../execution/research_backtest_track_v1.md)
(`RBT-xxx` tickets). This policy controls nothing outside that scope.

## Change from V1

V1 did not name an owner for the ETF flow owner's `market_holidays`
parameter. With its empty default, any 5- or 20-publication-day window that
spans a US market holiday expects flow records for the holiday. None exist, so
the owner correctly returns `ETF_FLOW_INPUT_MISSING`, the flow score is
incomplete and the champion cannot trade on that date. A V1 run would have
reported most real decision dates as unevaluable, for a data-plumbing reason
rather than a strategy one.

V2 binds `US_EQUITY_MARKET_CLOSURE_TABLE_V1` (EPIC X `POSTP1-001V2A-T1`) as that
owner (§5), after its independent review passes. Nothing else changes. No
EPIC Y run happened under V1.

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
  It adds no strategy semantics.
- [EPIC X](../execution/post_phase1_prospective_integration_evidence_v1.md) and
  BTC-019 are **untouched**. No EPIC X ticket depends on EPIC Y. EPIC Y depends
  on exactly one EPIC X output: the reviewed `US_EQUITY_MARKET_CLOSURE_TABLE_V1`
  artifact. It does not depend on any other EPIC X ticket, status or evidence.

## 1. Evidence class and prohibited uses

Every EPIC Y artifact carries:

```text
evidence_class       = RESEARCH_BACKTEST_NON_CERTIFYING
canonical_reference  = UNRESOLVED
policy               = RESEARCH_BACKTEST_POLICY_V2
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

## 4. Historical replay availability — `HISTORICAL_REPLAY_AVAILABILITY_V1`

Backfilled records carry a bulk ingestion time. Treated as live availability,
that time makes a correctly built dataset replay with no executable decision
(EPIC S audit). EPIC Y therefore models availability explicitly:

| Input family | Modelled availability |
| --- | --- |
| `1h` price bar, reference venue | its close boundary (`timestamp + 1h`) |
| Derived daily bar | the close boundary of its last constituent hour |
| ETF flow and AUM, fund `f`, US trading date `T` | `00:00` UTC on calendar day `T+2`, or the source's own later publication/revision time if it supplies one |
| Funding rate, settlement `S` | `S` |
| Open interest / perpetual volume, interval ending `E` | `E` |

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
- The `T+2 00:00` ETF rule is deliberately conservative: a daily flow is first
  usable one full day after the US session it describes. It is **not**
  `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` and makes no claim about it.
- If a source provides only final (revised) values with no revision history,
  each affected record is labelled `REVISION_HISTORY_UNAVAILABLE` and counted
  in the report. For non-certifying research this is an accepted limitation.
- Modelled availability is never earlier than the observation's close or end.

## 5. Input families and Rulebook fallbacks

| Family | EPIC Y V1 treatment |
| --- | --- |
| Reference price (`1h`) | Required, per venue |
| Raw volume / spot participation | Bitstamp raw OHLCV, shared across all runs |
| ETF flows + AUM | Required for any trade; backfilled with §4 availability |
| Funding, open interest, perpetual volume | Required: positioning is an Entry Conviction component |
| US equity market full-day closures (the flow owner's `market_holidays`) | **`US_EQUITY_MARKET_CLOSURE_TABLE_V1`**, loaded and hash-verified by its owner module and passed to the existing `market_holidays` parameter. Required, and only after the `POSTP1-002V2A-T1` review passes. A date on which a flow window is evaluated that falls outside the table's coverage blocks the RBT-006 freeze. |
| CVD (`SPOT_CVD`, `PERP_CVD`, `CVD_SPREAD`) | **Absent**: no persisted PIT source exists. The Rulebook §6.2 Phase-1 fallback applies mechanically: `FLOW_MODEL = ETF_CORE`. |
| Macro, on-chain, liquidity | **Declared unavailable.** Vintage-correct point-in-time history is not established, and revised series would leak. The Rulebook core regime fallback applies. |

Missing values are never zero-filled. Where the frozen owner code returns an
incomplete result, that result propagates as the owner defines it.

## 6. Champion identity and the no-tuning rule

- The champion is the repository strategy configuration
  (`strategy_version = swing_v1.2`, `config_version = strategy_config_v2`,
  `parameter_set_id = default_phase1`) at the code commit frozen by RBT-006,
  composed by the RBT-004/RBT-005 composer.
- No parameter, threshold, weight or rule changes during EPIC Y. BTC-185
  threshold sweeps may be reported as sensitivity, labelled
  `SENSITIVITY_ONLY_NOT_SELECTION`, and never select a value.
- Any post-result change creates a new strategy version. Such a version can
  never claim evidence from the evaluation window or the opened holdout.

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
  test modules. A need that can only be met by editing a bound module is
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

Any change to §2–§8 requires a new policy version (`RESEARCH_BACKTEST_POLICY_V3`)
recorded before the affected run. The holdout rule in §3 cannot be relaxed for
any strategy version that has already been evaluated on the evaluation window.
