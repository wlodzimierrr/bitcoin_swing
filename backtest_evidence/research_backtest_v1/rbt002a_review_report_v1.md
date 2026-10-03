# RBT-002A independent xHigh ticket review

Date: 2026-10-03. Ticket: `DEFINE_CHAMPION_COMPLETION_SPEC_V1`.
Reviewed: Part 0 `75fc7e6`, Part 1 `09d14dc`, documentation `ffce350`,
on branch `claude/etf-worker-prospective-integration-dixlte` at `84a0de1`.
V6 and V7 owner decisions are authority/context, not under review.

Verdict: **PASS**. Ticket status: **DONE** (2026-10-03).

All startup preconditions passed: clean tree, `84a0de1` in history, AGENTS.md
names V7, original spec `d9f9b334...a80fd`, inventory `108ab25b...efe3a`.
No sub-agents were used. The review followed `prompts/review_ticket.md` and
targeted repository authority/owner reads, without archived documents.

| Finding | Severity / final disposition | Location, reproducer and regression | Review-fix commit |
| --- | --- | --- | --- |
| RBT002A-R1 | P1 / FIXED | `completion_spec.UNIFORM_ZSCORE`, `UniformRule.application_contract`. On a 64-bit accumulator the frozen helper returns -1 for 730 identical 1/3 values; annualized 0.015*365/90 returns +1. An explicit original-value equality guard must precede float conversion/helper calls. Contract and independent synthetic witnesses now cover 0.1, 1/3 and annualized basis, equal/different current values, native/64-bit accumulators, full current and original window sizes, no helper invocation, exact tiny differences and nonconstant parity. Original time-selected H maps to `window=len(H)`; after R4 z uses the declared 20-row convention, while percentile keeps time selection. | `352bba0` |
| RBT002A-R2 | P2 / FIXED | `test_research_backtest_database.research_only_imports`. Nested `import_module('..research.btc019_empirical', __package__)` and aliased `import_module` formerly yielded no offenders. Relative resolution and importer-alias discovery fix four independent mutations. No actual guarded import exists. | `496a947` |
| RBT002A-R3 | P2 / FIXED | `database.database_url_from_environment`. A synthetic surrogate-bearing POSIX credential triggered `UnicodeEncodeError` retaining the credential in `.object`. Precheck code points before encoding; refusal now retains names only and no exception context/cause. Separate user/password regressions preserve normal quoting and missing-name behavior. | `5b75882` |
| RBT002A-R4 | P1 / FIXED | `completion_spec.UNIFORM_ZSCORE`, source-precedence/warm-up contract. 180 days cannot fit 30 weekly observations (25 maximum), but the feasible existing Flow/CVD 20-prior-observation/minimum-20 owner rule applies uniformly. Rejecting it for cadence preferences, "recent change" or later warm-up violates V7 §6A.2. Adopt that convention unchanged; retain population/prior/equality/PIT/no-fill rules. Independent signature, synthetic owner-parity and cadence regression; calendar witness checks all 26 entries on all venues. | `42459e6` |

**Part 0:** exactly the five POSTGRES names and the original quoted URL form;
missing/invalid credentials report names only. No printing, logging or
artifact writes. Seven research_backtest modules have no guarded BTC-019
import. Nested, relative, absolute, aliased and importlib string mutations
are detected. The original BTC-019 completion-gate test is byte-unchanged
from before `75fc7e6`, SHA-256
`6e4127b4dd7365cd45bb86cd781e114f653b6c69bc5a54b24ed99ebc260d2d96`.

| A–L | Result and evidence |
| --- | --- |
| A Coverage | PASS: 26 unique entries, 45 inventory occurrences; 22 defined, 2 omitted, 2 inert. Independent in-memory uncovered/duplicate/stale mutations refuse; persisted-digest mutation refuses explicit rebind. |
| B Precedence | PASS after R4. All original 17 parameter elements audited. The z-window bypass is removed; 16 new mapping/quantity/horizon elements remain, with exact scope-specific citations and one-line rationales. Other superficially matching owner numbers do not define those input meanings. Momentum Persistence is explicitly owner-ruled. |
| C Uniformity | PASS after R1/R4: one 20/20 native-observation z rule and one 730-day/365 daily percentile rule. No per-input exceptions. Exact original-value guard precedes numerical owner calls, independent of longdouble width. Row-helper application is explicit; time selection for percentile never backfills gaps. The original 730-day z adapter and its failure were audited before correction. |
| D Predicates | PASS: existing owner outputs/thresholds only. Supportive regime ≥65, supportive Flow ≥60, invalidation <45 with non-bear entry context; DATA_RISK_EXIT=False follows Rulebook §24; CROWDING.flagged if complete else None. The entry-context limitation is disclosed. |
| E Level volume | PASS: Bitstamp 1h only, existing swing records only, no new levels/bins. For each member, Q_L(d)=sum over [d-L,d), using the member's fixed L; Q_L(e) and every prior comparator are the same functional quantity. Daily overlapping sampling is explicit, including month-length-specific L. Current excluded, PIT hours, missing hours refuse. Weekly pivot 2021-01-11 / detection 2021-02-01; monthly detection 2021-04-01. |
| F Optional/inert | PASS: measured move omitted under owner tier precedence; for the same decision/context tiers 1–3 stand and only the omitted tier-4 rescue can disappear. This proves a subset of eligible decisions, not a global trade-count theorem for a path-dependent replay. Capitulation event omitted by optional ruling; CAPITULATION flag/Setup C remain. Distribution and short trigger are inert under long-only. |
| G Positioning | PASS: precise basis guard retained, extended by V7 to funding and OI growth. Exact own prior histories, no tolerance or restated z, no health/z outputs on refusal, structural unevaluability and five required tests per owner. These are RBT-004 implementation contracts, not completed composers. |
| H Roots/arithmetic | PASS: original nine direct helper roots complete; V7 adds five history helpers, total 14. Every declared extra operation is listed; transforms, returns, TR, scores, bands and trailing decisions use their owners. |
| I Availability | PASS: independent calendar bucketing/counting matches all 78 original per-entry dates and the original 2024-03-24 lower bound; it also matches all corrected dates and 2024-03-10 (+29 vs inventory) after R4. Both matrices retained in JSON evidence. Structure remains data-dependent; no actual evaluation start is claimed. |
| J Pre-registration | PASS: inventory/closure availability facts, source code, config/policies and synthetic witnesses only. No connection, environment file, market value, real score/signal/trade/performance computation. Holdout NOT COLLECTED, sealed sample UNOPENED. |
| K Surfaced items | See rulings below. No open correctness-critical ambiguity remains within this spec; downstream composition choices and frozen-owner differences are explicit limitations/obligations. |
| L Determinism | PASS: canonical bytes and digest match fresh processes under seeds 0, 1, 8675309 from alternate cwd. Inventory JSON, checksum and human report rebuild byte-identically. |

K rulings follow the **human spec §6 order**, whose numbering differs from
the machine `surfaced_for_review` list. Items 1–2 remain the V7 owner rulings.

| Item | Ruling |
| --- | --- |
| 3 Regime invalidation | LIMITATION: threshold/output mapping is sound; bear-entered positions are exempt for life. No general fewer-trades theorem is claimed for exits; structural stop/Hold remain active. |
| 4 52-week local high | LIMITATION: defined existing high output, explicitly interpreted as local; weekly lag and row-gap exposure disclosed. No new swing-high detector. |
| 5 730-day z window | DEFECT / FIXED R4: source precedence requires the feasible existing owner convention, not a new value justified by availability preference. |
| 6 Seven-day return | LIMITATION: no applicable owner/Rulebook return horizon exists. Explicit NEW_PARAMETER using the generic return owner; effects are not monotone through CAPITULATION/Setup C, so no global trades-less claim. |
| 7 Range quantity | SOUND with recorded non-monotone flag effects: scale-free fraction of the owner's TR, explicitly new quantity and declared arithmetic; no higher source fixes RANGE_PERCENTILE's quantity. |
| 8 Level families | LIMITATION / future obligation: only swing members supply these two inputs; a VP/AVWAP-only support is incomplete. RBT-004 must fix its family composition before any outcome/freeze. |
| 9 New structure | SOUND: use the existing trail/higher-low outputs and the structure's own timestamp, evaluated before applying STOP_MOVE; last accepted ENTER/ADD gates newness. One add opportunity per consumed structure is explicit. |

**Step 4, owner-ruled V7 conformance:** separate commit `700b924` (not a review
finding), digest `123590d1...3a78fe`. It rebinds policy V7; freezes three owner
guards and each owner's five required cases; adds funding averages/history
and OI aggregation/growth/history to promoted roots; makes their limitation
guarded; records Momentum Persistence ACCEPTED unchanged and its mandatory
RBT-006 freeze / RBT-007 evaluation-only, base-cost, per-venue ablation.
The exact digest chain is in `rbt002a_review_evidence_v1.json` and each commit.

**Final spec SHA-256:**
`9819f84a6ec89f6c39dc1c5215edeae4898f91ebea30eccd5698ca11da65013f`.
Inventory remains `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a`.

Implementation: original `09d14dc` plus the distinct fixes above. Files:
completion_spec.py, database.py; three EPIC Y test modules; spec JSON/checksum;
spec policy, track, CURRENT_STATE; this report, JSON evidence and offline
reproducer. No owner, config, EPIC X-bound module, data/ or research_artifacts/
file changed. Design: declarative contracts, owner math, independent synthetic
witnesses, availability-only calendar arithmetic, explicit limitations.

| Validation | Result |
| --- | --- |
| Final spec/review/database | 146 passed |
| RBT-001 + RBT-002 census/coverage/nine traces + closure table | 630 passed, 1 existing frozen-basis XFAIL |
| BTC-180..185, BTC-220..224 and owner/parity suites | 1,068 passed |
| V5 / corpus / sufficiency suites | 492 passed, 2 existing skips |
| PAD5 preserved-authority subset, unchanged | 5 passed, 112 deselected |
| Database fix / coverage / BTC-019 gate | 113 passed |
| Full repository suite | 7,305 passed, 3 skipped, 1 xfailed, 0 failed in 3023.38s |
| compileall; git diff --check | PASS |

Commands used `.venv312` CPython 3.12.14: `python -m pytest -q` on the named
suites; full run additionally `-W error::RuntimeWarning` and a same-device
scratch `--basetemp`; `python -m btc_predictor.research_backtest.coverage
rebuild --output-dir <scratch>`; completion_spec `write`/`verify` in fresh
processes; offline `rbt002a_review_reproducer_v1.py`; `compileall -q
btc_predictor etf_calendar_worker`; `git diff --check`. Exact validation
families/counts are recorded in JSON evidence. Two earlier full runs were
interrupted after new corrections; no complete baseline is claimed for them.

V5 independently recomputes to
`95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89`.
PAD5 preserves its authority values, predecessor/namespace, child ordering and
frozen source. BTC-019 untouched, sealed sample unopened; EPIC X's next ticket
remains POSTP1-001V2R1. No outcome or collection authorized or performed.

Documentation updated: current spec explanation/digest, complete ticket
review outcome, roadmap status/table/downstream obligations, CURRENT_STATE
frontier/recent review/next/test baseline/commits and the review artifacts.
Remaining risks: frozen-owner score/unit/table/row-gap limitations, recorded
non-monotone effects, data-dependent Structure, future composer guards/census
promotion and the required ablation; all explicitly recorded, none silently
resolved or traded on. Recommended next dependency-satisfied ticket:
**RBT-004 (READY)**, with **RBT-001A also READY**.
