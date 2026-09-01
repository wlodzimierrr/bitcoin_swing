# Review an Epic Independently

## Input

Epic identifier:

```text
EPIC X
```

Optional explicit ticket range:

```text
BTC-XXX..BTC-YYY
```

Authoritative execution roadmap:

```text
docs/execution/bitcoin_swing_predictor_structured_tickets_v2_6.md
```

Use:

```text
GPT-5.6 Sol — Extra High (xHigh)
```

This is an **independent epic-level integration and correctness audit**.

The repository is the complete project memory.

Do not rely on previous implementation chats, ticket-review chats, or undocumented reasoning.

Do not assume that individually correct tickets compose into a correct system.

Do not rewrite correct working code without concrete evidence.

---

# Purpose

A ticket review asks:

```text
Is this ticket correct?
```

An epic review asks:

```text
Do all tickets in this epic compose into one coherent,
correct, reproducible subsystem?
```

The primary target is therefore:

```text
CROSS-TICKET INTEGRATION RISK
```

rather than line-by-line re-review of every implementation.

Look especially for defects that can survive all individual ticket tests:

```text
contract mismatch
different assumptions across modules
point-in-time disagreement
duplicated formulas
incompatible units
different strategy/config versions
different cost policies
accounting double counting
event-order disagreement
persistence/replay gaps
stale provenance
optimistic simulation assumptions
research leakage
missing end-to-end invariants
```

---

# Startup Sequence

1. Read `AGENTS.md`.
2. Read `docs/INDEX.md`.
3. Read `docs/CURRENT_STATE.md`.
4. Locate the requested epic in the authoritative roadmap.
5. Identify the exact tickets belonging to that epic.
6. Read the epic introduction/goal.
7. Read each ticket block in that epic using targeted bounded reads.
8. Inspect direct dependencies outside the epic only when needed to understand interfaces.
9. Read only relevant Rulebook sections.
10. Read applicable narrow policy documents.
11. Inspect implementation modules corresponding to the epic.
12. Inspect focused ticket tests and cross-module/integration tests.
13. Inspect ticket Implementation Notes and required review outcomes.
14. Inspect relevant persistence/replay schemas and artifacts.

Do not preload:

```text
entire roadmap
entire Rulebook
archived v1 documents
unrelated epics
```

Expand context only when evidence requires it.

---

# 1. Establish Epic Scope

From the authoritative roadmap, report:

```text
Epic:
Purpose:
Tickets:
External dependencies:
Downstream consumers:
```

For every ticket in the epic report:

```text
Ticket
Status
Model
Review Model, if any
Dependencies
Implementation commit if discoverable
Review-fix commit if applicable
```

Do not infer epic membership solely from ticket number ranges when the roadmap says otherwise.

---

# 2. Verify Epic Readiness

Before auditing integration, determine whether every required ticket is actually ready.

Check:

```text
ticket status
acceptance criteria
required independent reviews
blocking findings
Implementation Notes
dependency completion
```

Classify each ticket:

```text
READY
NOT READY
BLOCKED
```

If a required ticket is incomplete, the epic cannot receive a clean integration PASS.

Continue reviewing everything that can still be evaluated.

---

# 3. Reconstruct the End-to-End Architecture

Produce the actual implemented flow.

For example:

```text
upstream data/state
↓
component A
↓
component B
↓
component C
↓
persistence/accounting/research output
```

Use real module/function ownership.

Identify:

```text
who owns each decision
who owns each formula
who owns state
who owns execution
who owns persistence
who owns replay validation
```

Flag duplicated or ambiguous ownership.

---

# 4. Verify Cross-Ticket Contract Compatibility

For every important interface between two tickets, verify:

```text
input type
output type
units
sign convention
timestamp semantics
missing-value semantics
completion/incomplete semantics
reason codes
version/provenance
```

Example failure:

```text
producer returns fraction
consumer interprets percent
```

or:

```text
producer timestamp = event time
consumer assumes availability time
```

Do not assume matching field names imply matching semantics.

---

# 5. Point-in-Time / Look-Ahead Audit

For any epic touching historical data, features, execution, research, or backtesting, trace:

```text
observation_time
available_at / ingested_at
decision_time
execution_time
event_time
```

Require:

```text
information used at decision time
must have been available at decision time
```

Look for cross-ticket leakage where each module is locally PIT-safe but their composition is not.

Test future-append invariance where relevant.

---

# 6. Shared-Formula / Single-Owner Audit

Identify calculations that must have one authoritative owner.

Examples:

```text
sizing
risk-at-stop
R/R
fees
slippage
funding
weighted entry
P&L
NAV
MFE/MAE
trailing stops
score aggregation
```

Search consuming modules for local replicas.

Do not accept:

```text
owner module is imported
```

as sufficient evidence.

Prove actual delegation where economically or strategically important.

---

# 7. Configuration and Policy Consistency

Verify that all tickets within the epic operate under compatible:

```text
strategy_version
strategy_config_version
parameter_set_id
policy versions
cost policy
comparison policy
risk convention
data-source policy
```

One run/subsystem must not silently mix incompatible policies.

Overrides must be persisted.

Historical replay must not depend on current defaults.

---

# 8. Numerical and Unit Consistency

Audit:

```text
currency vs fraction
fraction vs percent
price vs notional
quantity vs notional
gross vs net
signed vs absolute
Decimal vs float64
NaN vs None
```

Verify centralized tolerances are used where appropriate.

No silent:

```text
NaN → 0
inf
unit conversion
rounding drift
```

should alter decisions.

---

# 9. Long/Short Symmetry

Where short infrastructure exists, test mirrored scenarios.

Check:

```text
PnL sign
stop direction
funding sign
slippage direction
risk-at-stop
trailing stop
entry/exit logic
```

If an epic is intentionally long-only, document that rather than inventing symmetry.

---

# 10. Lifecycle / State Integration

For stateful epics, verify that tickets agree on:

```text
state names
allowed transitions
terminal states
stale actions
refusals
duplicate events
partial operations
```

No ticket should perform an economic mutation that the authoritative lifecycle later rejects.

Require atomicity where relevant:

```text
either all economic/state effects apply
or none apply
```

---

# 11. Event Ordering

For execution/backtesting/paper-trading epics, reconstruct exact ordering.

Challenge ambiguous combinations such as:

```text
STOP + EXIT
STOP + ADD
STOP + TRIM
ENTRY + STOP
funding + fill
stop move + stop trigger
```

Unknown intrabar ordering must not be resolved optimistically.

---

# 12. Accounting Reconciliation

For epics touching economics, establish exact identities.

Examples:

```text
NetPnL
=
GrossPnL
- Fees
- SignedFundingCost
```

and for a flat portfolio without external cash flows:

```text
FinalNAV - InitialNAV
=
sum(CompletedTradeNetPnL)
```

Check:

```text
fees once
funding once
realized P&L once
unrealized P&L once
completed trade summaries not applied twice
```

Use independently computed fixtures rather than only owner-module helpers.

---

# 13. Persistence and Replay

Determine whether the full epic output is reproducible later.

Require sufficient evidence for applicable items:

```text
input/data identity
strategy identity
config identity
policy versions
timestamps
events
reason codes
state transitions
execution evidence
accounting evidence
```

Restore/replay where supported.

Tamper nested records and confirm validation fails.

---

# 14. Reason-Code Integrity

Authoritative reason codes must survive orchestration.

Do not allow consumers to replace useful causes with generic failures.

Verify:

```text
stable ordering
deduplication
source identity
accepted/refused state
```

where relevant.

---

# 15. Error and Failure Semantics

Test failures including:

```text
missing data
invalid numeric data
stale event
duplicate event
out-of-order event
incomplete upstream result
policy mismatch
config mismatch
insufficient capital
terminal state
```

The epic should fail closed where required rather than manufacture a favorable result.

---

# 16. End-to-End Scenarios

Build realistic deterministic scenarios covering the epic's intended purpose.

Do not only test isolated modules.

Each scenario should verify intermediate state as well as final output.

Depending on epic scope, examples may include:

```text
normal success path
refusal/no-action path
boundary case
adverse path
long/short mirror
missing-data path
restart/replay path
```

---

# 17. Cross-Ticket Property Tests

Where practical add properties such as:

```text
same inputs → same outputs

future data append
→ prior decisions unchanged

serialized → restored
→ equivalent state/output

refused action
→ no economic mutation

full close
→ exact cash-flow reconciliation

flat final portfolio
→ NAV reconciliation

producer output
→ direct consumer parity
```

Use independent expected calculations where possible.

---

# 18. Research Integrity

For research/backtest/calibration epics, verify strict separation between:

```text
training/calibration
validation
test
sealed/external samples
```

No result may influence an earlier supposedly frozen decision.

Check for:

```text
look-ahead
threshold selection on test data
repeated test-set reuse
survivorship/selection bias
human filtering of model signals
```

Research outputs must not silently modify production strategy.

---

# 19. Parameter Robustness / Overfitting

When relevant, verify the epic reports:

```text
sample size
trade count
uncertainty
sensitivity
robust plateaus
regime/setup stability
```

Do not accept a single best parameter as evidence of robustness.

---

# 20. Data Provenance

For historical/research epics, confirm exact dataset identity is reproducible.

Examples:

```text
canonical source policy
dataset version/hash
time range
row/bar count
available-at rules
feature contract version
```

Given unresolved source decisions, do not silently treat research-only sources as production-approved.

---

# 21. Dependency Boundary Audit

Inspect important dependencies outside the epic.

Ask:

```text
Did this epic accidentally restate an upstream contract?

Did an upstream dependency change after this epic was implemented?

Is a newer authoritative implementation now available that this epic bypasses?
```

Do not re-review unrelated dependency internals unless evidence requires it.

---

# 22. Downstream Safety

Inspect immediate downstream consumers sufficiently to determine whether this epic exposes a safe contract.

Look for:

```text
ambiguous fields
missing provenance
undocumented units
mutable defaults
missing replay information
```

The epic may be locally correct but unsafe to consume.

---

# 23. Documentation Consistency

Check:

```text
ticket statuses
Implementation Notes
dependencies
CURRENT_STATE
README/INDEX only if relevant
```

Do not modify historical archived documents merely to agree with current state.

Correct stale current documentation narrowly.

---

# 24. Test Architecture

Review whether test coverage includes:

```text
ticket-local unit tests
cross-ticket integration tests
end-to-end scenarios
PIT/look-ahead tests
replay tests
tamper tests
accounting/risk properties
```

Identify important invariants covered only indirectly.

Do not weaken tests to obtain a PASS.

---

# 25. Performance Pathology

Do not optimize prematurely.

Only report performance issues that threaten realistic intended workloads, such as:

```text
O(n²) full-history rescans
unbounded memory growth
repeated database roundtrips
duplicated large matrix computation
```

Correctness dominates speed.

---

# 26. Scope Leakage

Search for behavior implemented inside the epic that belongs to another ticket or policy.

Examples:

```text
backtest engine selecting strategy thresholds
reporting layer making trading decisions
research automatically promoting parameters
quant core persisting DB state
```

Flag architectural leakage.

---

# 27. Independent Review of Existing Reviews

Do not simply trust prior ticket review reports.

Use them as evidence of what was checked, but independently inspect the cross-ticket consequences of their fixes.

A previous `PASS` means:

```text
ticket was reviewed
```

not:

```text
epic composition is proven correct
```

---

# 28. Severity

Use:

```text
P0 Critical
P1 High
P2 Medium
P3 Low
NOT_A_DEFECT
```

Interpret approximately:

```text
P0
Can invalidate strategy/research/accounting correctness broadly.

P1
Material correctness or reproducibility defect affecting realistic use.

P2
Real but bounded defect, ambiguity, or missing integration guarantee.

P3
Low-impact robustness/documentation/maintainability issue.
```

---

# 29. Finding Format

Every genuine finding must include:

```text
Severity:
Tickets/modules:
File/location:
Current behavior:
Expected behavior:
Cross-ticket impact:
Why it matters:
Recommended correction:
Required regression/integration test:
```

Do not create findings merely to produce activity.

---

# 30. Review-Fix Policy

If there are no genuine defects:

```text
do not create a meaningless commit
```

If defects exist:

1. implement the smallest correct fix;
2. preserve ticket/strategy semantics unless correction requires an explicit versioned change;
3. add independent integration regressions;
4. run affected focused tests;
5. run relevant epic integration tests;
6. run the full suite where appropriate;
7. create a separate review-fix commit;
8. update affected ticket Implementation Notes where necessary;
9. update `CURRENT_STATE.md` if project state changes.

Suggested commit:

```text
fix: close EPIC X integration review findings
```

Do not redesign unrelated epics.

---

# 31. Validation

Run:

```text
focused integration tests for the epic
relevant dependency regression suites
relevant replay/persistence suites
```

Then, for critical epics:

```bash
python -m pytest -W error::RuntimeWarning
python -m compileall btc_predictor
git diff --check
```

Use the repository's supported Python version.

Report exact test counts.

---

# 32. Final Epic Review Result

Use one:

```text
PASS

PASS WITH NON-BLOCKING FINDINGS

FAIL — EPIC INTEGRATION BLOCKED
```

`PASS` means:

```text
the epic's implemented tickets compose coherently
for the documented supported scope
```

It does NOT mean future empirical validation has succeeded unless that is the epic's purpose.

---

# Final Report

Report:

```text
Epic:
Ticket range / members:
Review result:

Branch / HEAD:
Implementation/review commits examined:

Purpose of epic:
External dependencies:
Downstream consumers:

Ticket readiness:
- ...

Implemented architecture:
- ...

Cross-ticket interfaces checked:
- ...

Findings:
- ...

Fixes:
- ...

Review-fix commit:
- ...

Point-in-time result:
- ...

Shared-owner / duplicate-formula result:
- ...

Configuration/policy consistency:
- ...

Numerical/unit consistency:
- ...

Long/short symmetry:
- ...

Lifecycle/state integration:
- ...

Event-ordering result:
- ...

Accounting/NAV reconciliation:
- ...

Persistence/replay result:
- ...

Tamper validation:
- ...

Research-integrity result:
- ...

End-to-end scenarios:
- ...

Cross-ticket property tests:
- ...

Documentation consistency:
- ...

Focused integration tests:
- ...

Relevant regression tests:
- ...

Full suite:
- ...

Python version:
- ...

compileall:
- ...

git diff --check:
- ...

Remaining supported limitations:
- ...

Remaining unresolved risks:
- ...

Can this epic be treated as integration-complete?
- YES/NO

May downstream work safely proceed?
- YES/NO, with conditions if applicable

Recommended next epic/ticket:
- ...
```

---

# Mandatory Epic Acceptance Criteria

Before a critical epic receives `PASS`:

* [ ] All required epic tickets are implementation-complete
* [ ] All ticket-level required independent reviews are closed
* [ ] Cross-ticket interfaces have explicit compatible semantics
* [ ] No material formula has conflicting owners
* [ ] Point-in-time semantics are coherent end-to-end
* [ ] Strategy/config/policy provenance is consistent
* [ ] Units and sign conventions agree
* [ ] Missing-value behavior is explicit
* [ ] State/event ordering is deterministic where relevant
* [ ] Refused actions are economic no-ops where required
* [ ] Accounting does not double count economic effects
* [ ] End-to-end reconciliation invariants pass where relevant
* [ ] Persistence/replay reproduces meaningful outputs
* [ ] Tampered evidence fails validation where supported
* [ ] Research outputs cannot silently mutate production strategy
* [ ] Realistic end-to-end scenarios pass
* [ ] Full relevant regression suite passes
* [ ] Remaining limitations are explicit
* [ ] No unresolved P0/P1 finding remains

---

# Review Principle

The central question is:

```text
Could all the tickets pass individually while the epic as a whole
still produce the wrong decision, wrong risk, wrong P&L,
wrong historical result, or unreproducible state?
```

Try to construct such cases.

If you can, fix them and pin them with integration tests.

If you cannot after independent adversarial review, the epic may be considered integration-complete within its documented scope.
