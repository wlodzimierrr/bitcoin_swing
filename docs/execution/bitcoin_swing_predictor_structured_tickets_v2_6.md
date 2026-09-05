# Bitcoin Swing Predictor — Structured Tickets v2.6

This file is the execution-ticket plan for the Bitcoin Swing Predictor.

Version 2 preserves the completed data, persistence, feature, and price-structure work from v1 while introducing a dedicated **NumPy/SciPy quantitative core** before the remaining risk, lifecycle, paper-trading, and backtesting work is implemented.

Completed tickets remain `DONE`; where a completed implementation is moved behind the new quantitative layer, the existing implementation becomes the **reference/parity oracle** until the NumPy implementation is proven equivalent.


Status values:

```text
TODO / IN_PROGRESS / BLOCKED / DONE
```

### Authoritative Roadmap / Dependency Policy

This v2.6 document is the **authoritative Phase-1 execution roadmap**.
[Project Roadmap & Tickets v1](../archive/bitcoin_swing_predictor_project_tickets_v1.md)
is retained only as historical
provenance and must **not** be used to determine current execution order or
ticket dependencies.

Dependency rules:

- Every executable `TODO` / `IN_PROGRESS` ticket declares its current prerequisites in this document.
- `Dependencies` is the single authoritative dependency field; the legacy `V2 Dependencies` field is retired.
- Ticket ranges such as `BTC-150..158` are inclusive.
- Completed tickets whose old v1 dependency detail was never reconstructed are marked as historical/completed and carry no remaining execution dependency.
- The `V2 Execution Order` below is the scheduling/tie-break authority when multiple dependency-satisfied tickets are available.
- A dependency change must be made in this file rather than by pointing to an older roadmap.

### Codex Model Selection Policy

This roadmap is now optimized for **maximum implementation quality and
correctness**, even if Phase 1 takes several additional days.

Model efficiency is secondary to:

```text
point-in-time correctness
numerical parity
risk correctness
portfolio-accounting correctness
state-machine correctness
execution realism
backtest integrity
reproducibility
```

Use only the following implementation tiers:

```text
GPT-5.6 Sol — High
    DEFAULT MINIMUM for all normal implementation work.

    Use for:
    - schemas and persistence
    - collectors and adapters
    - deterministic feature calculations
    - scoring modules
    - setup / trigger logic
    - reporting
    - configuration
    - ordinary tests
    - documentation
    - low-ambiguity integrations

GPT-5.6 Sol — Extra High (xhigh)
    REQUIRED for correctness-critical implementation.

    Use for:
    - point-in-time and no-look-ahead logic
    - parity-sensitive NumPy migrations
    - shared risk / portfolio mathematics
    - structural invalidation and risk-at-stop
    - lifecycle state machines
    - trailing-stop invariants
    - stop / gap execution simulation
    - paper-trade accounting
    - event-driven backtesting
    - walk-forward validation
    - parameter-robustness research
    - final historical / invariant validation
```

### Quality-First Workflow

For ordinary Sol High tickets:

```text
Implement on Sol High
        ↓
Run focused tests
        ↓
Run relevant regression tests
        ↓
Verify acceptance criteria
        ↓
DONE
```

For xHigh tickets:

```text
Implement on Sol xHigh
        ↓
Run focused tests
        ↓
Run parity / invariant / regression tests
        ↓
Independent xHigh audit if Review Model is present
        ↓
Fix defects
        ↓
Re-run full relevant test suite
        ↓
DONE
```

### Review Model

A ticket containing:

```text
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
```

requires a separate audit pass after implementation.

The review pass should **not rewrite working code without evidence**. It should
inspect:

```text
mathematical assumptions
point-in-time semantics
look-ahead leakage
edge cases
risk invariants
long/short symmetry
state transitions
fill assumptions
portfolio accounting
batch-vs-single parity
test coverage
historical reproducibility
```

### Escalation Rule

Any Sol High ticket must be escalated to xHigh if:

```text
tests disagree unexpectedly
strategy semantics are ambiguous
point-in-time behavior is uncertain
risk or stop behavior changes
portfolio accounting changes
execution assumptions change
historical fixtures cannot be reproduced
the implementation requires repeated failed attempts
```

### Quality Rules

1. Do not use a weaker model merely to save Plus allowance.
2. Do not reduce test coverage to save model usage.
3. Do not combine unrelated correctness-critical tickets into one Codex task.
4. Keep completed implementations as parity/reference oracles during refactors.
5. Require deterministic tests for all mathematical and lifecycle invariants.
6. Prefer one extra review pass over accepting an unresolved ambiguity.
7. Phase 1 is complete only when the completion gate and validation suites pass.

## V2 Architecture Decision

### Core Boundary

```text
PostgreSQL
    │
    ▼
Data access / point-in-time alignment
pandas or Polars
    │
    ▼
NumPy / SciPy Quant Core
    │
    ├── rolling statistics
    ├── nonlinear transforms
    ├── vectorized scoring
    ├── volatility-normalized distances
    ├── risk mathematics
    ├── portfolio mathematics
    └── statistical primitives
    │
    ▼
Domain Engines
    │
    ├── Features
    ├── Levels
    ├── Signals
    ├── Risk Rules
    └── Portfolio State Machine
    │
    ▼
Recommendation / Paper Portfolio
    │
    ▼
PostgreSQL
```

### Architectural Rule

```text
PostgreSQL stores durable truth.
pandas / Polars aligns point-in-time observations.
NumPy computes numerical results.
SciPy provides statistical primitives.
Python domain logic decides what action to take.
PostgreSQL records the decision and resulting state.
```

### Target Package Layout

```text
btc_predictor/
├── config/
├── data/
│   ├── collectors/
│   ├── quality/
│   ├── canonical/
│   └── adapters/
├── db/
│   ├── models/
│   ├── repositories/
│   └── migrations/
├── domain/
│   ├── enums.py
│   ├── types.py
│   ├── events.py
│   ├── recommendations.py
│   └── reason_codes.py
├── quant/
│   ├── arrays.py
│   ├── rolling.py
│   ├── transforms.py
│   ├── scoring.py
│   ├── distances.py
│   ├── risk.py
│   ├── portfolio.py
│   ├── statistics.py
│   └── simulation.py
├── features/
├── levels/
├── signals/
├── risk/
├── portfolio/
├── backtest/
├── research/
├── reporting/
└── tests/
```

### Quant-Core Rules

- Quant functions must be pure or effectively pure.
- `quant/` must not depend on PostgreSQL, SQLAlchemy, recommendation persistence, or paper-trade state.
- Internal numerical calculations use `numpy.float64`.
- Missing numerical values use `np.nan`; missing values must never be silently converted to zero.
- `inf` and `-inf` may not escape the quant layer.
- Domain modules remain responsible for completion state, interpretation, reason codes, hard vetoes, and persistence.
- Existing domain APIs should remain stable during the migration wherever practical.
- Completed pure-Python implementations are retained as reference implementations until NumPy parity is demonstrated.

### Migration Policy

For an existing calculation:

```text
Existing tested implementation
        ↓
Reference / parity oracle
        ↓
New NumPy implementation
        ↓
Parity + look-ahead tests
        ↓
Domain API switched internally
        ↓
Old implementation retained for tests or retired
```

Required numerical parity:

\[
|Reference - NumPy| < \epsilon
\]

using centrally defined tolerances appropriate to each calculation.

### V2 Execution Order

```text
Existing completed foundation
        ↓
BTC-019  Validate canonical BTC price-source policy
        ↓
BTC-042  Quant package and numerical conventions
BTC-043  NumPy rolling/statistics parity
BTC-044  Nonlinear transform library
BTC-045  Volatility-normalized distance engine
BTC-046  Generic vectorized scoring engine
BTC-047  Vectorized risk / portfolio mathematics
BTC-048  Point-in-time feature matrix
BTC-049  Quant parity and batch/single validation
        ↓
BTC-098  Structure Score v1.2 de-nesting migration
        ↓
BTC-084  Volatility Score
        ↓
BTC-129  Factor-overlap / de-nested scoring contract audit
        ↓
BTC-130..133  Entry Conviction / thresholds / vetoes / reasons
        ↓
BTC-140..146  Risk Engine
        ↓
BTC-150..158  Position Lifecycle / Pyramiding
        ↓
BTC-160..166  Paper Trader
        ↓
BTC-170..172  Advisory Output
        ↓
BTC-180..185  Backtesting / walk-forward / threshold research
        ↓
BTC-186..189  Extended Quant Research
        ↓
BTC-190+     Research & controlled learning loop
        ↓
BTC-220+     Full validation / invariants / historical scenarios
```

## EPIC A — Project Foundation

#### BTC-001 Create Python project structure
- **Description:**
  Create:

  ```text
  btc_predictor/
  ├── config/
  ├── data/
  ├── db/
  ├── features/
  ├── levels/
  ├── signals/
  ├── risk/
  ├── portfolio/
  ├── backtest/
  ├── research/
  ├── reporting/
  └── tests/
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Installable Python package
  - Central configuration loader
  - Structured logging
  - Test runner works
  - No secrets committed
  - Environment-specific configuration supported
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-002 Define strategy configuration schema
- **Description:**
  Create versioned configuration for:

  - Entry thresholds
  - Hold thresholds
  - Add thresholds
  - Risk schedule
  - Maximum risk-at-stop
  - Stop buffers
  - Setup requirements
  - Regime thresholds
  - Price-level parameters
  - Backtest assumptions
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Strategy parameters are externalized
  - Config validated at startup
  - Invalid configs fail fast
  - Config version is persisted with every run
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-003 Add database migration framework
- **Description:**
  Use Alembic.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Fresh database can be built from migrations
  - Upgrade and downgrade tested
  - Schema state can be reproduced exactly
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

## EPIC B — PostgreSQL Data Model

#### BTC-010 Create core PostgreSQL schemas
- **Description:**
  Create:

  ```text
  raw
  derived
  signals
  portfolio
  research
  system
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Schemas created through migration
  - Application DB user has correct permissions
  - Research and runtime connections verified
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

#### BTC-011 Create raw OHLCV schema
- **Description:**
  Store:

  - timestamp
  - exchange
  - symbol
  - timeframe
  - open
  - high
  - low
  - close
  - volume
  - provider
  - ingestion timestamp
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Unique primary key
  - UTC timestamps
  - Duplicate ingestion is idempotent
  - Missing bars can be detected
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **BTC-019 Policy Note:**
  - Keep raw OHLCV rows as immutable provider facts. Policy-dependent source
    roles, policy version, and fallback state belong to versioned research/run
    provenance so a future V2 does not mutate V1 history.

#### BTC-012 Create derivatives raw schemas
- **Description:**
  Tables for:

  - Funding
  - Open interest
  - Futures basis
  - Liquidations
  - Perp volume
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Exchange/source preserved
  - Units documented
  - Timestamp semantics documented
  - Point-in-time availability supported
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-013 Create ETF flow raw schema
- **Description:**
  Store:

  - fund
  - observation date
  - flow
  - AUM if available
  - source
  - available_at
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Historical revisions can be represented
  - Signal jobs query only data available at signal time
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-014 Create macro and on-chain generic series schema
- **Description:**
  Support generic time series:

  ```text
  series_id
  observation_time
  value
  available_at
  provider
  revision
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Can store VIX, yields, DXY proxies, liquidity measures, and on-chain metrics
  - Revisions do not overwrite historical availability state
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.

#### BTC-015 Create predictor and recommendation schemas
- **Description:**
  Persist:

  - Regime
  - Setup
  - Direction
  - Component scores
  - Entry Conviction
  - Hold Score
  - Add Score
  - Entry zone
  - Invalidation
  - Stop
  - R/R
  - Risk
  - Suggested size
  - Action
  - Reason codes
  - Strategy version
  - Parameter set
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  Every recommendation is reconstructable later.
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-016 Create paper portfolio schemas
- **Description:**
  Create entities for:

  - Paper account
  - Position
  - Tranche
  - Order
  - Stop
  - Position event
  - Completed trade
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  Support:

  ```text
  ENTER
  HOLD
  ADD
  STOP_MOVE
  TRIM
  EXIT
  MISSED
  ```
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-017 Create manual trade journal schema
- **Description:**
  Store:

  - linked recommendation
  - actual entry
  - actual size
  - actual stop
  - manual decision
  - override reason
  - actual exit
  - notes
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  Can compare recommendation vs actual execution.
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `portfolio.manual_trade_journal` in Alembic revision `0017_manual_trade_journal`.
  - Linked journal entries to `signals.recommendations` for suggested-versus-actual execution comparison.
  - Captured actual entry, size, stop, exit, manual decision, override reason, and notes.


## Phase 1 BTC Price-Data Policy

### Why the project separates price roles

The system must not assume that the exchange used for raw market observations,
the reference price used for strategy structure, and the user's eventual live
execution venue are the same thing.

Use three explicit concepts:

```text
canonical_reference_price
market_data_sources
execution_venue
```

Their responsibilities are:

```text
Canonical reference price
    ↓
Trend
Structure
ATR / volatility
Breakouts / reclaims
Structural invalidation
Stops
Backtest reference price
MFE / MAE

Raw exchange market data
    ↓
OHLCV
Volume
Volume profile
Spot participation
Cross-exchange validation

Execution venue
    ↓
Actual manual fills
Actual slippage
Actual fees
Live execution comparison
```

The execution venue is intentionally independent from the canonical reference
price source.

### Phase 1 source-policy research state

BTC-019 rejected Bitstamp as the sole permanent `PRICE_SOURCE_POLICY_V1`
reference after the persisted three-year empirical study. Bitstamp remains a
raw OHLCV source, but no provider is currently approved as strategy-canonical.

| Role | Research source | Instrument | Purpose |
|---|---|---|---|
| Rejected canonical candidate + primary raw exchange OHLCV | Bitstamp | BTC/USD (`btcusd`) | 1h raw OHLCV and exchange volume; blocked from strategy-canonical promotion |
| Required validation | Coinbase Exchange | BTC-USD | Independent cross-venue evidence |
| Required validation | Bitfinex | BTC/USD (`tBTCUSD`) | Independent cross-venue evidence |
| Optional institutional benchmark | Coin Metrics Community | BTC/USD pair candles (`btc-usd`) | Future V2 reference research when entitled history is available |
| Research convenience only | yfinance | BTC-USD | Quick sanity checks / macro convenience |
| Derivatives / secondary market context | Binance and other derivatives venues | Venue-specific | Funding, OI, liquidations, perp activity |

### Bitstamp — rejected canonical candidate and raw BTC/USD OHLCV

Collection rationale and empirical outcome:

- Official public BTC/USD spot API.
- OHLC endpoint supports 1-hour candles and exchange volume.
- Up to 1,000 candles can be requested per call.
- Retains the primary raw-data role while remaining separate from the eventual
  execution venue. The canonical candidate was rejected because rare range
  disagreements changed structural and stop outcomes.

Official documentation:

- https://www.bitstamp.net/api/

### Coinbase Exchange and Bitfinex — required validation venues

Current rationale:

- Both provide official public spot candle endpoints.
- Coinbase uses `BTC-USD` and pages at a maximum of 300 candles per request.
- Bitfinex uses `trade:1h:tBTCUSD`, millisecond boundaries, ascending sort, and
  at most 10,000 candles per request.
- Together with Bitstamp they provide the three independent venues required by
  the Phase 1 empirical completion gate.

Official documentation:

- https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles
- https://docs.bitfinex.com/reference/rest-public-candles

### Coin Metrics Community — optional institutional benchmark

Current rationale:

- Pair candles remain useful institutional reference research.
- Catalog visibility and historical timeseries entitlement are separate access
  facts and must be persisted separately.
- Coin Metrics credentials or entitlement are not a Phase 1 completion blocker.
- Any later promotion to canonical status requires a new policy version and
  fresh empirical validation.

Official documentation:

- https://docs.coinmetrics.io/api/v4/

### yfinance — not canonical BTC intraday data

`yfinance` remains useful for convenience research and selected macro/market
series, but it must not be the canonical BTC 1-hour historical source.

Current reason:

- yfinance documentation states that intraday data cannot extend beyond the
  most recent 60 days.
- That is incompatible with a multi-year 1-hour BTC backtest and structural
  research dataset.

Official documentation:

- https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html

### Source hierarchy

Current role hierarchy:

```text
PRODUCTION STRUCTURAL / REFERENCE PRICE
UNRESOLVED — no provider/composite is promoted yet

FROZEN RESEARCH CANDIDATE
BTC_REFERENCE_COMPOSITE_V2
(Bitstamp + Coinbase + Bitfinex median-OHLC protocol)

RAW OHLCV / VOLUME
Bitstamp BTC/USD
Coinbase BTC-USD
Bitfinex BTC/USD

OPTIONAL INSTITUTIONAL BENCHMARK
Coin Metrics BTC/USD pair candles

RESEARCH SANITY CHECK
yfinance BTC-USD
```

A fallback does **not** silently splice itself into an existing historical
series. Any provider substitution must be explicit and provenance must remain
queryable.

### Exchange-specific wick policy

A structural break should not automatically be declared solely because one
exchange prints an isolated abnormal wick. BTC-019 now uses the versioned
`PRICE_SOURCE_WICK_ANOMALY_V1` rule: an isolated wick must be materially extreme
in ATR units and stand clear of the runner-up venue; `CROSS_VENUE_CONFIRMED`
requires meaningful corroboration by a second venue. The materiality threshold is
`0.30 ATR`, deliberately reused from the frozen two-provider range-disagreement
threshold rather than introduced as an unversioned magic constant. Research
output continues to record cross-venue median high/low/close and ATR-normalized
high/low divergence distributions.

BTC-019 must quantify cross-source divergence and define the exact rule for:

```text
isolated exchange wick
reference-price break
confirmed multi-source break
provider anomaly
WICK_ANOMALY_CANDIDATE
CROSS_VENUE_CONFIRMED
CROSS_VENUE_UNCONFIRMED
```

Raw observations remain immutable. The final approved canonical series will
determine strategy structure, while exchange-specific data remains available
for diagnostics and execution analysis.

### Reference-composite research governance

The price-reference research line has progressed beyond the original BTC-019
provider comparison, but **no production canonical reference has been approved**.
Current authoritative state:

```text
BTC-019 = IN_PROGRESS
Bitstamp sole canonical candidate = REJECTED
BTC_REFERENCE_COMPOSITE_V1 = RESEARCH_INCONCLUSIVE
BTC-019B diagnostic conclusion = MIXED
BTC_REFERENCE_COMPOSITE_V2 = FROZEN_RESEARCH_PROTOCOL
production canonical reference = UNRESOLVED
```

`BTC_REFERENCE_COMPOSITE_V1`, BTC-019B, and BTC-019C/V2 are separate, versioned
research artifacts. They do not rewrite `PRICE_SOURCE_POLICY_V1` history and do
not imply production promotion. The frozen V2 protocol definition SHA-256 is:

```text
bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a
```

The candidate V2 validation period `2015-07-20 21:00 UTC` through
`2019-11-30 23:00 UTC` remains sealed until the preregistered validation stage.
Normal Phase-1 implementation may continue with an injectable/versioned reference
price abstraction, but final authoritative strategy calibration/certification
remains blocked until the production canonical reference is resolved.

The `BTC019_COMPLETION_GATE_ASSESSMENT_V1` record under
`research_artifacts/btc019_completion_gate/` states the current blocker:
`BLOCKED_BY_UNRESOLVED_CORRECTNESS_DEFECT`. Cross-provider weekly structural
comparison indexes its confirmation window by row, so a week a provider outage
removed is read as if the weeks either side of it were neighbours. Six V2
approval gates, five of them hard, are computed from that comparison, so the
sealed sample must not be opened until the comparison carries an explicit
calendar-contiguity contract and the already-inspected samples have been
re-measured under it.

`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2` under
`research_artifacts/btc019_structure_comparison_v2/` has now done both, without
changing a frozen threshold, gate or artifact and without opening the sealed
sample. 26 of the 40 prior structural differences are `NOT_COMPARABLE` rather
than disagreements and 14 remain genuine. The remaining blocker moved: every
affected gate is measurable, but the frozen thresholds were calibrated over an
undeclared denominator, and the verdict against the identical frozen number
changes between the comparable-event and all-event denominators on every one of
the six structural gates, all five hard ones included.

`STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1` under
`research_artifacts/btc019_gate_denominator_resolution/` resolves that
denominator as a governance decision, changing no frozen artifact and leaving
the V2 definition hash exactly as it stands. Outcome:
`NEW_PROTOCOL_VERSION_REQUIRED`. The frozen protocol declares no numerator,
denominator, candidate universe or comparison basis for any of the six; the two
pre-existing formulas disagree with each other; `breakout_disagreement_rate`
and `reclaim_disagreement_rate` have no calibration artifact at all; and the
only reading recoverable from the record is the one that counts an availability
gap as a disagreement — the defect itself. The successor is
`BTC_REFERENCE_COMPOSITE_V3`, as the frozen V2 governance clause
`material_change_requires` already prescribes, proposed and not frozen. It
defines every metric's numerator, denominator and aggregation, excludes a
`NOT_COMPARABLE` event from both, requires comparability/coverage evidence
beside every rate, and carries the six frozen numbers across unchanged and
explicitly uncalibrated. A separate pre-sealed calibration task must bind them
before any validator is built.

### Persistence requirements

Every raw/canonical price observation must preserve enough provenance to answer:

```text
Which provider produced this value?
Which instrument was used?
Which exchange, if any?
What timeframe?
When was the observation available?
Which source-policy version was active?
Was the value primary or fallback?
```

Add or retain fields equivalent to:

```text
provider
exchange
symbol
timeframe
observation_time
available_at / ingested_at
price_source_role
price_source_policy_version
fallback_used
```

Do not overwrite raw history when the preferred provider changes.


## EPIC C — Data Ingestion

#### BTC-019 Define and validate canonical BTC price-source policy
- **Description:**
  Validate the provisional Phase 1 source policy before treating it as the
  permanent strategy reference-price definition.

  Candidate sources:

  ```text
  Bitstamp BTC/USD
  Coinbase BTC-USD
  Bitfinex BTC/USD
  Coin Metrics Community BTC/USD pair candles as an optional institutional benchmark
  yfinance BTC-USD as non-canonical sanity check
  ```

  Compare the sources historically using synchronized 1-hour windows.

  Required comparisons:

  ```text
  missing bars
  duplicate bars
  close-price divergence
  high/low divergence
  extreme wick divergence
  daily return divergence
  ATR divergence
  swing-high / swing-low differences
  breakout / reclaim differences
  stop-touch differences
  MFE / MAE differences
  provider outages / continuity
  historical coverage
  API pagination / rate-limit practicality
  ```
- **Status:** IN PROGRESS
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Canonical reference-price provider is explicitly selected
  - Primary raw OHLCV provider is explicitly selected
  - At least two independent validation providers are explicitly selected
  - Instrument naming is fixed (`BTC/USD`, `BTC-USD`, etc.) per provider
  - Reference-price role is separated from execution venue
  - At least three required independent providers are compared across an overlapping period of at least two years
  - Missing-bar rates are measured
  - Distribution of close-price differences is reported
  - Distribution of high/low differences is reported
  - Top historical source-divergence events are reviewed manually
  - Structural swing detection is compared across providers
  - Backtest stop-touch sensitivity to source choice is measured
  - Rules for isolated exchange wicks are documented
  - Provider outage/fallback behavior is documented
  - Provider diagnostics distinguish catalog visibility from historical entitlement
  - Historical fallback splicing is prohibited unless explicitly versioned
  - `price_source_policy_version` is defined
  - Final decision is persisted/documented as `PRICE_SOURCE_POLICY_V1`
  - Tests cover provenance and explicit fallback behavior
- **Dependencies:** BTC-011, BTC-020, BTC-040
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Rejected canonical candidate and retained primary raw source: Bitstamp BTC/USD (`btcusd`).
  - Required validation sources: Coinbase BTC-USD and Bitfinex BTC/USD (`tBTCUSD`).
  - Coin Metrics `btc-usd` remains an optional institutional benchmark and a
    future V2 candidate; its entitlement is not a Phase 1 blocker.
  - yfinance is restricted to convenience research/sanity checks for BTC intraday
    because documented intraday history is limited to the most recent 60 days.
  - The current BTC-020 collector is provider-injected, which allows this source
    decision to be implemented without coupling strategy logic to one provider.
  - Added a deterministic Bitfinex public-candle adapter with UTC normalization,
    pagination, idempotent collector integration, provenance, and focused tests.
  - Added the versioned `PRICE_SOURCE_POLICY_V1` policy record with a
    policy-driven required provider set, fixed roles and instruments, endpoint
    provenance, pagination/rate-limit practicality, access diagnostics, and
    candle semantics.
  - Added `compare_price_sources` for synchronized point-in-time `1h` research.
    Reports separate Tier 1 price, Tier 2 indicator, Tier 3 decision, and Tier 4
    portfolio divergence. They include missing/duplicate bars, continuity,
    close/high/low and ATR-normalized cross-venue wick distributions,
    daily-return and ATR divergence, structural swing and breakout/reclaim
    differences, stop-touch sensitivity, and MFE/MAE sensitivity.
  - Persisted `price_source_policy_version`, source roles, and `fallback_used`
    per analyzed provider series without changing immutable raw candle facts.
  - Top divergence events require exact structured manual reviews before a
    report can become decision-ready. Reviews persist source snapshots,
    cross-venue medians, ATR-normalized divergence, classification, and
    strategy/portfolio impact. Missing required providers and less than two
    years of common Bitstamp/Coinbase/Bitfinex bars fail explicitly.
  - A decision-ready report also requires an explicit persisted approval or
    rejection of the Bitstamp canonical candidate.
  - Historical fallback splicing is rejected by V1 policy validation. Optional
    Coin Metrics and yfinance observations are compared over their available
    overlap but do not shorten the required three-provider multi-year window.
    Coin Metrics catalog and entitlement states are recorded separately.
  - Focused tests cover policy provenance, fallback rejection, a synchronized
    two-year three-venue gate, optional-provider entitlement behavior,
    missing/duplicate data, manual-review enforcement, source divergence,
    decision/portfolio sensitivity, and missing required-provider behavior.
  - Final completion remains gated on an approved canonical source. The
    implementation and architecture do not depend on Coin Metrics historical
    credentials.
  - Completed the empirical stage over `2023-01-01 00:00 UTC` through
    `2025-12-31 23:00 UTC`: 26,292 synchronized bars, 78,900 raw provider bars
    persisted in PostgreSQL, no duplicates/conflicts, and source-persistent
    gaps classified `UNKNOWN` rather than silently repaired.
  - Persisted 82 structured review records covering the 25 gate-required price
    events, top ATR-normalized wick diagnostics, every structural disagreement,
    and every material or stop-sensitive path comparison.
  - **Canonical decision: `BITSTAMP = REJECTED`.** Bitstamp had perfect
    continuity and no material close bias versus Coinbase, but it alone created
    one swing and breakout and missed one stop hit confirmed by both validators.
    Maximum MFE/MAE sensitivities were 2.433/4.605 percentage points.
  - BTC-019 remains **IN PROGRESS** because rejection does not satisfy the
    approved-canonical-reference criterion. Coinbase and Bitfinex are not
    automatically promoted.
  - Evidence is persisted under
    `research_artifacts/btc019/PRICE_SOURCE_POLICY_V1/`.
  - Separate follow-up research has since implemented and preserved
    `BTC_REFERENCE_COMPOSITE_V1` (`RESEARCH_INCONCLUSIVE`), BTC-019B (`MIXED`),
    and BTC-019C / `BTC_REFERENCE_COMPOSITE_V2` (`FROZEN_RESEARCH_PROTOCOL`).
    These artifacts are versioned research only; none rewrites V1 or promotes a
    production canonical reference.
  - The BTC-019 correctness/reproducibility audit corrected implementation defects
    without changing the governing conclusions: Bitstamp remains `REJECTED`, V1
    remains `RESEARCH_INCONCLUSIVE`, BTC-019B remains `MIXED`, and the V2 protocol
    remains byte-identical with SHA-256
    `bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`.
  - **Completion-gate assessment (`BTC019_COMPLETION_GATE_ASSESSMENT_V1`).** The
    remaining acceptance criterion — an explicitly approved canonical
    reference-price provider — is **not satisfied**, and the assessment
    persisted under `research_artifacts/btc019_completion_gate/` records why
    without moving a threshold, gate, comparison definition or frozen artifact.
    Outcome: `BLOCKED_BY_UNRESOLVED_CORRECTNESS_DEFECT`. Bitstamp stays
    `REJECTED`; Coinbase and Bitfinex have never been affirmatively evaluated as
    sole references; `BTC_REFERENCE_COMPOSITE_V1` stays `RESEARCH_INCONCLUSIVE`
    on two missed external gates; `BTC_REFERENCE_COMPOSITE_V2` stays an
    unvalidated frozen protocol.
  - **The sealed V2 sample was not opened, and must not be yet.** Three
    conditions of its own governance fail: no validator is bound to the frozen
    definition hash, the 2015-07-20..2019-11-30 history is not collected, and an
    unresolved implementation defect would invalidate the evaluation.
  - **The defect, measured.** `build_canonical_market_bars` drops an incomplete
    bucket, so a provider outage removes a whole canonical session, but
    `detect_weekly_swing_levels` indexes its confirmation window by row. Removing
    one week from a contiguous series therefore confirms a swing the complete
    calendar does not contain. On the collected samples Coinbase omits 2 and 3
    weekly sessions and Bitfinex 2 and 5, while Bitstamp omits none. Recomputing
    BTC-019's own structural comparison reproduces the corrected frozen counts
    exactly — 4 swing highs, 7 swing lows, 4 breakouts, 9 reclaims — and 24 of
    the 40 differences across both samples sit inside the detector's own
    ±3-week reach of a week one compared series does not have. Two are
    unambiguous: Bitstamp's swing lows at `2023-03-06` and `2024-04-29` fall on
    the exact weeks Bitfinex omits. The same mechanism explains BTC-019B's four
    exact-timestamp swing disagreements, which are two adjacent-week pairs around
    the two weekly buckets the composite omitted. Six V2 approval gates, five of
    them hard, are computed from this comparison. The frozen
    `COMPLETION_GATE_REPORT.md` reads "four of them hard"; only
    `exact_timestamp_swing_disagreement_rate` is soft in the frozen V2
    definition, so the count is five. That report is left as it stands.
  - **What the defect does not overturn.** `BITSTAMP = REJECTED` stands. Only the
    first two pillars of its rationale are adjacency-exposed; the 10 October 2025
    consensus stop and the 2.433/4.605 percentage-point MFE/MAE sensitivities are
    Tier 4 comparisons on synchronized hourly bars, and BTC-224's golden scenario
    corroborates the stop independently. Tier 1 divergence, the wick diagnostics
    and the 82 manual reviews all normalize on the gap-free Bitstamp baseline.
    Rejecting a venue remains sound; approving one is what depends on the
    structural evidence.
  - **Shared-formula ownership.** `_atr_fraction_series`, `_atr_value_series` and
    `_baseline_atr_before` restate true range, and `_daily_returns` restates the
    close-to-close move, over `zip(ordered, ordered[1:])`. 348 published
    observations across the two samples cross a session the BTC-041 owner reports
    as undefined. Where no session is absent they agree with the owner to the
    digit, and Bitstamp bridges nothing, so the duplication is preserved to keep
    the frozen artifacts reproducible rather than corrected in place. Any future
    canonical-selection run must read the BTC-041 owner or carry parity evidence
    before its result can support an approval.
  - **Owner boundary.** `btc_predictor/levels/swing.py` is EPIC E's and feeds
    structure scores, stops and setups, so it is proven and pinned, not changed
    here. BTC-019 also owns no part of the historical-availability finding:
    `derive_ohlcv_bars` and `build_canonical_market_bars` stamp one `ingested_at`
    per backfill, which stays with BTC-020 and BTC-180, and there is no approved
    canonical path here to supply per-bar availability from.
  - **Smallest legitimate next step**, in order: give cross-provider structural
    comparison an explicit calendar-contiguity contract under its own version;
    re-measure structural disagreement on the already-inspected 2019-2022 and
    2023-2025 samples; and only then build the hash-bound validator, collect
    2015-2019, and open the sealed sample once.
  - Added `btc_predictor/research/btc019_completion_gate.py` and 16 focused tests
    in `test_btc019_completion_gate.py` covering the non-approval, sealed-sample
    containment, collected-artifact digests, the weekly-row/week defect and all
    four restated helpers, BTC-041 parity where no session is absent, the
    uncontaminated Bitstamp baseline, deterministic recomputation of the
    persisted assessment, and production/research separation.
  - **`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2`.** Step 1 and step 2 of that
    sequence are now done. `btc_predictor/research/cross_provider_structure_comparison.py`
    adds a versioned research adapter in front of the unchanged production
    detectors: a candidate swing at week `T` is comparable between two series
    only when both hold every calendar week of the detector's own `T-3 .. T+3`
    reach, and a derived breakout/reclaim only when both hold every week from
    the source level through the later confirmation -- or through the end of the
    shared calendar when either series never confirms. Sessions are canonical
    UTC Monday buckets classified `PRESENT`, `ABSENT`, `PENDING` or
    `OUT_OF_COVERAGE` at the sample's own latest ingestion instant, so a week
    that has not arrived is never read as a week a provider lost. Comparison is
    pairwise on the shared calendar, canonicalised by sorted series id, so
    provider order cannot change a record. Outcomes are `STRUCTURAL_AGREEMENT`,
    `STRUCTURAL_DISAGREEMENT` or `NOT_COMPARABLE` with the side and the exact
    missing sessions named, and every rate declares whether its denominator is
    the comparable event union or the V1 all-event union.
  - **Both already-inspected samples re-measured; the sealed sample untouched.**
    The V1 comparison still reproduces its own frozen numbers -- 4 swing highs,
    7 swing lows, 4 breakouts, 9 reclaims on 2023-2025, and both samples'
    completion-gate counts, 40 in total -- and runs beside the new contract
    rather than being replaced by it. Under V2, 26 of those 40 differences are
    `NOT_COMPARABLE` (13 an absent required week, 10 a derived level whose
    source swing is blocked by one, 3 a derived level the pair has no shared
    source swing for) and 14 remain genuine: 1 swing high, 5 swing lows, 8
    reclaims and no breakouts. None became an agreement. `2023-03-06` and
    `2024-04-29` are the exact weeks Bitfinex omits; the `2023-02-13` swing and
    its `2023-03-13` breakout are blocked by Coinbase's `2023-02-27` and
    Bitfinex's `2023-03-06`; and all four BTC-019B exact-timestamp
    disagreements -- `2020-03-09`/`2020-03-16` and `2021-04-05`/`2021-04-12` --
    have one of the composite's own two omitted buckets inside their
    confirmation window. The contract also moves events the other way: the
    `2025-09-01` reclaim that Bitstamp confirms on `2025-10-13` and Coinbase on
    `2025-10-06` is comparable and genuinely disagrees, because Coinbase's
    omitted `2025-10-20` is not in its required calendar.
  - **V2 gate measurability: `RESEARCH_INCONCLUSIVE`.** All six affected frozen
    gates are now defined on an explicit comparable denominator across all six
    pairwise comparisons, and none is availability-dominated: 230 comparable
    structural events against 83 not-comparable. No threshold, gate, direction
    or protocol was changed; they are read from the frozen definition only. The
    unresolved item is which denominator those frozen numbers were ever defined
    over. They were calibrated on BTC-019B's all-event denominator, and on five
    of the six gates -- four of them hard -- the verdict against the identical
    frozen number flips when the denominator changes; every one of the six
    `breakout_disagreement_rate` measurements fails on the prior denominator and
    passes on the comparable one, because all 14 breakout disagreement
    candidates turn out to be availability. Declaring that denominator under its
    own version, bound to the frozen definition hash, is the next step, and it
    must precede validator construction. The classification rule is predeclared
    in the module, so the outcome is read off the evidence.
  - Evidence is persisted under `research_artifacts/btc019_structure_comparison_v2/`
    (`CROSS_PROVIDER_STRUCTURE_COMPARISON_V2_REPORT_V1`). Added 48 focused tests
    in `test_cross_provider_structure_comparison.py` covering the calendar
    contract derived independently from the detector's reach, agreement and
    genuine disagreement on contiguous series, a missing disqualifying week, a
    missing week outside the reach, missing weeks either side, per-side and
    both-side attribution, series-edge coverage, point-in-time pending
    confirmation, future-append invariance, provider-order invariance, derived
    breakout/reclaim from a non-comparable swing, the full derived confirmation
    calendar, denominator completeness, an undefined rate reported as `None`,
    ambient-Decimal independence, the named historical cases, artifact
    restore/recompute parity, tamper rejection, and every fail-closed boundary.
  - `btc_predictor/levels/swing.py` and `breakout.py` are untouched. A
    production swing-gap policy remains a separate certification concern for
    EPIC E's owner.
  - **`STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1`.** Step 1 of that sequence is
    now done as governance, not as measurement.
    `btc_predictor/research/structural_gate_denominator_resolution.py` reads the
    frozen V2 definition, the two formulas that predate the defect and the
    frozen BTC-019B calibration evidence, and asks of each of the six metrics
    whether a denominator was ever intended. Outcome:
    **`NEW_PROTOCOL_VERSION_REQUIRED`**. The frozen artifact declares only
    metric, threshold, direction, hard flag and rationale — no numerator, no
    denominator, no candidate universe, no comparison basis, and no treatment of
    an unevaluable event. `reference_composite_empirical.py::_structural_comparison`
    measures per category against a two-of-three consensus;
    `btc019b_diagnostics.py::_swing_metric_summary` pools the swing families and
    uses two denominators of its own, 33 for exact/structural-state and 31 for
    the within-N-week metrics. They disagree, and neither computes a breakout or
    reclaim rate, so those two V2 gates have no pre-existing candidate universe
    and no calibration artifact whatsoever. Decisively, no pre-existing formula
    has a third outcome: an availability gap lands in the symmetric difference
    and in the union because nothing else exists to put it in. The only
    recoverable denominator is therefore the correctness defect itself, so
    writing an admissible one down is new statistical semantics rather than a
    clarification.
  - **Threshold semantics: not recoverable, on all six.** The one numeric anchor
    the frozen thresholds have is `exact_timestamp`'s 12.1212% = 4/33, and all
    four of those numerator events are `NOT_COMPARABLE` availability gaps, so
    under the resolved denominator the anchor is zero rather than rescaled.
    `structural_state`'s BTC-019B observation was 2/33 = 6.0606%, already above
    the 0.05 that was frozen for it, so that number never accommodated its own
    calibration observation either. `within_1_week` and `within_2_week` observed
    zero, which is denominator-invariant and therefore carries no denominator
    information; their 0.05 and 0.02 were round allowances never bound to a
    universe. Breakout and reclaim were never calibrated. Every frozen number is
    carried across verbatim and marked `CARRIED_FORWARD_UNCALIBRATED`; none is
    moved, optimised or replaced here.
  - **Successor: `BTC_REFERENCE_COMPOSITE_V3`, proposed, not frozen.** The
    frozen V2 governance clause `material_change_requires` already reads
    `BTC_REFERENCE_COMPOSITE_V3 or later`, so a "V2.1" would be a tier the
    frozen protocol does not recognise and a decimal point implying a minor
    clarification this is not. Status
    `PROPOSED_PENDING_THRESHOLD_CALIBRATION`, with its own definition hash and
    an explicit `parent_definition_sha256` of `bc312f3e…6106a`, which is
    unchanged and stays the immutable record of what was frozen. It inherits
    every parent gate, threshold, direction, MEDIAN_OHLC_V2, the quality-state
    and higher-timeframe contracts, the provider set and the sealed-sample
    guard. It adds: pairwise comparison on the two series' common weekly
    calendar canonicalised by sorted series id with no quorum formed; per-metric
    numerator, denominator and candidate universe; `NOT_COMPARABLE` excluded
    from both numerator and denominator, because an unevaluable event is
    neither an agreement nor a disagreement — counting it as agreement would
    make every extra outage buy a free agreement; the within-N-week pair-merged
    denominator, recovered from BTC-019B's own formula rather than invented; and
    mandatory comparability/coverage evidence. One hard requirement is new,
    `unrecorded_not_comparable_event_count == 0`, derived from the parent's own
    zero-count provenance gates rather than calibrated. No comparability floor
    is set, because that would be a threshold this task may not choose.
  - **Not outcome-driven.** The already-inspected 2019-2022 and 2023-2025
    measurements are admitted only to show materiality — every one of the six
    gates, and all five hard ones, flips verdict against the identical frozen
    number on at least one of six pairwise comparisons. They are refused for
    choosing the denominator, and the adopted denominator is not the favourable
    one: `reclaim_disagreement_rate` still fails five of six measured pairs and
    `within_2_week` four of six. The earlier prose reading "five of the six
    gates, four of them hard" understates its own artifact, whose
    `classification.denominator_sensitive_hard_gates` already lists all five;
    the historical report is left unchanged as evidence and the accurate figures
    are recorded in the new artifact.
  - Evidence is persisted under
    `research_artifacts/btc019_gate_denominator_resolution/`
    (`denominator_resolution.json`, `successor_protocol_definition.json`,
    `DENOMINATOR_RESOLUTION_REPORT.md`). Added 39 focused tests in
    `test_structural_gate_denominator_resolution.py` covering the unchanged
    frozen V2 hash, bytes, thresholds and directions, the sealed-sample guard,
    explicit denominator and `NOT_COMPARABLE` semantics on all six metrics, the
    refusal of a silently defaulted denominator, unknown schema and
    denominator-semantics versions, a wrong parent hash, tampered record and
    successor artifacts, ambient-Decimal independence, deterministic rebuild in
    an isolated root that contains no collected history at all, and the fact
    that the adopted denominator is not the uniformly favourable one.
  - **Sealed sample still shut.** Validator construction, 2015-2019 collection
    and opening all remain refused. The exact prerequisite is a separate
    pre-sealed threshold calibration and governance task binding a threshold to
    each of the six `BTC_REFERENCE_COMPOSITE_V3` structural denominators, using
    the already-inspected samples only; the validator must then bind the frozen
    successor's own complete executable definition hash, not the parent's.
  - **Review finding: four V3 semantics the calibration task must settle first.**
    The required `STRUCTURAL_GATE_DENOMINATOR_RESOLUTION` xHigh review confirmed
    `NEW_PROTOCOL_VERSION_REQUIRED` and every preservation claim, and found no
    outcome-driven selection, but recorded four under-specified items in the
    proposed successor, each able to move a hard gate verdict by itself. They are
    governance choices, so the review did not make them.
    (1) **Pair universe.** Every metric's `aggregation` reads "one measurement per
    unordered pair of declared comparison series", but the successor never says
    which set that is: the frozen parent's `comparison_series` lists five entries
    -- three raw providers, `MEDIAN_OHLC_V1` and `BTC_REFERENCE_COMPOSITE_V2` --
    while `inherits_from_parent_unchanged` carries over "the provider set", and
    the measured evidence is six provider-vs-provider measurements with the
    candidate on neither side. Three raw-provider pairs, ten pairs among five
    series, and candidate-vs-provider only are all conformant readings, and only
    the last two say anything about a candidate.
    (2) **Admissibility and worst-pair aggregation.** "The gate verdict is the
    worst admissible pair verdict" defines neither *admissible* nor *worst*.
    Direction recovers "worst" for these six -- all are `maximum` -- but nothing
    states it, there is no tie rule, and an undefined pair has no stated status.
    (3) **Zero comparable events.** `_rate` returns `None` and the comparison
    contract carries `UNDEFINED_NO_COMPARABLE_EVENTS`, but the successor states
    the null convention only for `structural_comparability_rate`, not for the six
    gate rates. All six measured pairs have `undefined_measurement_count == 0`, so
    no evidence exercises it; a conformant implementation could read an undefined
    rate as `0.0` and pass a hard maximum gate on no evidence at all.
    (4) **Within-N-week matching.** "Nearest-admissible-pair first" fixes no
    tie-break and requires no maximum-cardinality matching. Under the pinned
    `BTC_PREDICTOR_WEEKLY_LEVELS_V1` detector -- strict inequality over +/-3 bars,
    so same-family swings in one series are at least four weekly sessions apart --
    the shipped greedy is maximum-cardinality on every realisable input, and
    `within_1_week` is determinate (0 of 3,379,360 enumerated configurations
    ambiguous). `within_2_week` is not: 97,414 of the same configurations admit
    both a maximal and a sub-maximal count under orderings that all satisfy
    "nearest first". The smallest is left `{W0, W4}` against right `{W2, W6}`,
    where matched pairs are 1 or 2 -- enough to move the hard 0.02 gate.
    The review's other conclusions stand: the frozen V2 hash, bytes, thresholds,
    directions and hard flags are unchanged and independently recomputed; the
    successor is deterministic across working directory, key order, ambient
    `Decimal` context and process restart, and refuses a re-digested tamper of
    `denominator_id`, `not_comparable_treatment`, `aggregation`,
    `candidate_universe` or `frozen_threshold`; no threshold was calibrated; and
    the sealed sample was neither collected nor opened.
  - **`BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_THRESHOLD_CALIBRATION_V1`.** The
    pre-sealed calibration and governance task that had to precede any freeze is
    now done, in two strictly ordered phases, under
    `btc_predictor/research/structural_threshold_calibration.py`. Outcome:
    **`CALIBRATION_INSUFFICIENT`**. `BTC_REFERENCE_COMPOSITE_V3` stays
    `PROPOSED_PENDING_THRESHOLD_CALIBRATION`, the validator is still not
    authorised, and 2015-2019 is still neither collected nor opened.
  - **Phase A settled all four review findings before a single rate was
    computed**, and is hashed as
    `BTC_REFERENCE_COMPOSITE_V3_STRUCTURAL_CALIBRATION_GOVERNANCE_V1`
    (`503ec795...67e6e6`), which Phase B verifies before it runs.
    (1) *Pair universe.* The gate universe is the three unordered
    {candidate, independent raw provider} pairs -- `MEDIAN_OHLC_V2` against
    Bitstamp, Coinbase and Bitfinex -- because only a pair with the candidate on
    one side is evidence about the candidate. Provider-versus-provider pairs
    become `SOURCE_DISPERSION_CALIBRATION_PAIR`s that set the tolerance rather
    than the verdict, and `MEDIAN_OHLC_V1` is excluded from both: it is a
    research composite of the same three providers, so its agreement with any of
    them measures the median formula, not the market. The three rejected
    readings -- provider pairs as gates, all ten pairs among the parent's five
    declared series, and the six-pair mixture -- are persisted with the reason
    each fails. The split has a second effect that is the point of it: the series
    the thresholds are calibrated on and the series they will be applied to are
    disjoint, so the calibration cannot see a candidate outcome.
    (2) *Admissibility and aggregation.* Three explicit states with reason codes,
    and no pair is ever dropped. `WORST_ADMISSIBLE_PAIR_V1` reads "worst" from
    each gate's own declared direction, breaks ties on the lexicographically
    smallest `comparison_id`, and turns a missing, inadmissible or undefined
    required pair into `UNDEFINED_INSUFFICIENT_EVIDENCE` for the whole gate.
    (3) *Zero comparable events.* `UNDEFINED_NO_CANDIDATE_EVENTS` and
    `UNDEFINED_NO_COMPARABLE_EVENTS` are distinct, both carry a null rate, and
    neither can pass or fail a threshold. No evidence is not zero disagreement.
    (4) *Within-N matching.* `MAX_CARDINALITY_MIN_DISTANCE_LEXICOGRAPHIC_V1`
    replaces "nearest-admissible-pair first": maximum-cardinality bipartite
    matching inside the tolerance with the swing families separated, then minimum
    total calendar distance, then the lexicographically smallest matched-pair
    tuple. The review's adversarial case, left `{W0, W4}` against right
    `{W2, W6}` at the two-week tolerance, is pinned at two matched pairs with the
    optimum asserted independently of the implementation.
    Phase A also fixes the comparability sufficiency policy -- a
    `0.50` structural-comparability floor, derived as "the measured set must be
    at least as large as the excluded set" and kept separate from every
    disagreement threshold; all three gate pairs required; insufficient evidence
    cannot approve -- and the uncertainty method, a two-sided 95% Wilson score
    interval in an explicit `Decimal` context.
  - **The calibration objective was predeclared**, not fitted:
    `ACHIEVABLE_AND_DISCRIMINATING_TOLERANCE_V1`. Pool the admissible
    provider-pair measurements, take the Wilson upper limit as the band level
    `pi_bar`, set the detectable alternative at `3 x pi_bar`, and select the
    *smallest* value on a coarse interpretable grid at which, on both samples'
    own pair-denominator regimes, family-wise false rejection is at most `0.10`
    and power against the alternative is at least `0.80`. Binomial tails are
    exact rational arithmetic. `0.10` rather than `0.05` on false rejection is
    the asymmetry BTC-019 actually faces: a false rejection costs more research,
    a false approval installs an unreliable canonical reference under every
    level, stop and setup. Pass-count optimisation, `max(observed) + epsilon`,
    reproducing a V2 verdict, and any use of the candidate or the sealed sample
    are all persisted as prohibited criteria.
  - **Result: two of six calibrated, four unresolved, all four hard.**
    `exact_timestamp_swing_disagreement_rate` (soft) calibrates to `0.25` and
    `structural_state_disagreement_rate` (hard) to `0.20`, on pooled independent
    bands of 7/156 and 4/156 and worst observed pair rates of 0.1071 and 0.0714;
    neither adjacent grid value moves a historical pair verdict, and each carries
    a *derived* minimum of 13 and 17 comparable events per gate pair, so the gate
    is never zero-tolerance in disguise. `within_1_week` and `within_2_week` are
    `INSUFFICIENT_EVIDENCE`: their defining mechanism never fires. All six
    provider-pair measurements across both samples have a matched-pair count of
    zero at both tolerances, so the two metrics are numerically identical to
    `exact_timestamp` on every observation the repository holds and their
    thresholds are not separately identified. `breakout_disagreement_rate` is
    `INSUFFICIENT_EVIDENCE` on 0/39 comparable events with admissible pair
    denominators of 5 to 12: no grid value is simultaneously achievable and
    discriminating. `reclaim_disagreement_rate` is worse -- 3/21, `pi_bar` of
    0.346, so `3 x pi_bar` saturates at 1 and the alternative degenerates; even a
    `0.50` threshold would falsely reject an independent pair most of the time.
  - **What that finding is.** Under worst-pair aggregation the sampling noise of
    one legitimate pair measurement, on denominators this small, is wider than
    the whole economically meaningful range of a derived-level gate. That is a
    property of the evidence, not of the objective: the honest next step is more
    comparable structural evidence -- longer inspected history or more
    independent providers -- or an explicitly versioned change of aggregation,
    not a looser number. Worst-pair conservatism is kept precisely because it is
    the fail-closed reading for a hard gate on a canonical price reference.
  - **Disclosed limitation.** The tolerance is estimated on provider-versus-
    provider pairs and will be applied to candidate-versus-provider pairs. The
    candidate is the element-wise median of the same three providers, so its
    agreement with any one of them is expected to be at least as good as two
    providers' agreement with each other: the band is conservative against
    falsely rejecting a sound reference and lenient against falsely approving a
    poor one. That is the price of calibrating without consulting the candidate,
    and it is recorded in the governance artifact rather than corrected, because
    correcting it would make the threshold candidate-dependent.
  - **Nothing was frozen and nothing moved.** Hard/soft statuses are inherited
    from the parent unchanged and recorded beside every threshold; the six frozen
    V2 numbers stay `CARRIED_FORWARD_UNCALIBRATED`; the frozen V2 hash, bytes,
    thresholds and directions are read and independently reverified; the
    `STRUCTURAL_GATE_DENOMINATOR_RESOLUTION_V1` artifacts and the proposed V3
    definition (`1ac5438a...17baa`) are untouched and bound by hash. The
    candidate reference was not built, not measured and not evaluated against any
    gate in this task.
  - Evidence is persisted under
    `research_artifacts/btc019_structural_threshold_calibration/`
    (`calibration_governance.json`, `threshold_calibration.json`,
    `THRESHOLD_CALIBRATION_REPORT.md`). Added 97 focused tests in
    `test_structural_threshold_calibration.py` covering the exact pair
    universes and their disjointness, pair-order invariance, an unexpected pair,
    a role mismatch, an unknown series, one and all pairs undefined, worst-pair
    on maximum and minimum directions, the deterministic tie, the maximum- and
    minimum-gate equality boundaries just below/at/just above, both undefined
    states, every matching case including `{W0, W4}` against `{W2, W6}` with the
    optimum asserted independently, equidistant and crossing choices, min-distance
    selection among maximal matchings, side and input-order invariance, family
    separation, the oversized-input refusal, the comparability floor just below/at/
    above `0.50`, Wilson behaviour at 0/3 versus 0/300, exact binomial tails,
    ambient-`Decimal` independence of intervals, governance and record, a
    knife-edge surface that cannot be published as calibrated, evidence-free
    calibration that cannot be, and every integrity boundary: a wrong parent
    hash, a wrong comparison contract, a tampered governance payload, pair
    universe, matching algorithm, comparability policy, threshold and record, a
    re-digested record promoting an insufficient metric or claiming sealed
    access, a corrupted sample digest, and the sealed-window guard.
  - **Sealed sample still shut.** With four hard gates unresolved the successor
    is not frozen, so validator construction, 2015-2019 collection and opening
    all remain refused. The exact prerequisite is now narrower: comparable
    breakout and reclaim evidence sufficient to resolve those two gates, and a
    within-N matching observation that actually merges a pair, all from
    already-inspected or newly collected non-sealed history.

#### BTC-020 Implement BTC OHLCV collector
- **Description:**
  Collect at minimum:

  - 1h data
  - derive daily
  - derive weekly
  - derive monthly
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Idempotent ingestion
  - UTC normalization
  - Retry support
  - Missing interval detection
  - Daily, weekly, and monthly bars derive from point-in-time source data
  - Raw records never silently changed
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added provider-injected BTC OHLCV collection with retry support.
  - Collected canonical raw `1h` bars with UTC validation and conflict-do-nothing inserts.
  - Derived complete daily, weekly, and monthly bars from available `1h` source bars.
  - Reported missing source intervals and skipped incomplete derived periods.
  - Added a Bitfinex `tBTCUSD` historical `1h` provider adapter for the BTC-019
    required validation set.
  - **V2.1 price-source note:** keep the collector provider-injected. BTC-019 determines which adapter supplies canonical/reference and raw OHLCV roles; strategy modules must not hard-code a provider.

#### BTC-021 Implement derivatives collector
- **Description:**
  Collect:

  - funding
  - OI
  - futures basis
  - liquidations
  - perp volume
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Provider-specific raw data normalized
  - Aggregate BTC view can be generated
  - No future timestamps leak into derived data
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added provider-injected derivatives collection with retry support across funding, open interest, futures basis, liquidations, and perpetual volume.
  - Normalized provider rows into typed raw records with UTC timestamps and point-in-time availability validation.
  - Persisted each feed with conflict-do-nothing inserts to keep raw records immutable.
  - Added point-in-time raw feed queries and an aggregate BTC derivatives view that excludes future or unavailable observations.

#### BTC-022 Implement ETF flow collector
- **Description:**
  Complete the ticket scope for implement etf flow collector.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Daily flow loaded
  - AUM normalization supported where available
  - available_at correctly captured
  - Missing publication days handled explicitly
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added provider-injected ETF flow collection with retry support.
  - Loaded daily fund flows into typed records with UTC `available_at` capture.
  - Normalized flow and optional AUM values to USD while rejecting unsupported currencies.
  - Persisted ETF flow revisions with conflict-do-nothing inserts.
  - Reported missing expected publication days by fund, excluding weekends and configured holidays.

#### BTC-023 Implement macro data collector
- **Description:**
  Initial candidate data:

  - VIX
  - DXY or equivalent
  - Nasdaq proxy
  - US 2Y yield
  - real yield proxy
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added provider-injected macro data collection with retry support.
  - Configured deterministic initial series IDs for VIX, DXY, Nasdaq proxy, US 2Y yield, and real-yield proxy.
  - Persisted observations as immutable `raw.generic_series` revisions with series type, unit, provider, source, revision, `available_at`, and `ingested_at`.
  - Added missing business-day observation reporting with configurable holiday exclusions.
  - Tightened point-in-time generic-series queries to require both `available_at` and `observation_time` at or before signal time.
  - Reason codes are not applicable at the raw macro collector stage.

#### BTC-024 Implement on-chain collector
- **Description:**
  Initial candidates:

  - SOPR
  - MVRV
  - realized P/L
  - short-term holder realized price
  - exchange flows
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added provider-injected on-chain data collection with retry support.
  - Configured deterministic initial series IDs for SOPR, MVRV, realized P/L, short-term holder realized price, and exchange flows.
  - Persisted observations as immutable `raw.generic_series` revisions with series type, unit, provider, source, revision, `available_at`, and `ingested_at`.
  - Added missing calendar-day observation reporting because on-chain metrics are not business-day-only.
  - Reused point-in-time generic-series queries that require both `available_at` and `observation_time` at or before signal time.
  - Reason codes are not applicable at the raw on-chain collector stage.

#### BTC-025 Build ingestion audit log
- **Description:**
  Track:

  - job start/end
  - records fetched
  - records inserted
  - failures
  - gaps
  - provider response metadata
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added migration-controlled `system.ingestion_audit_log`.
  - Captured job start/end, fetched and inserted record counts, failures, gaps, provider response metadata, config version, and collector-level reason codes where applicable.
  - Added deterministic `IngestionAuditRecord` helpers with validation for status, UTC timestamps, non-negative counts, and job time order.
  - Persisted audit rows with conflict-do-nothing inserts keyed by stable `job_run_id`.

## EPIC D — Data Quality

#### BTC-030 Implement OHLCV quality checks
- **Description:**
  Detect:

  - duplicate bars
  - impossible OHLC
  - missing periods
  - stale data
  - extreme malformed values
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added deterministic OHLCV quality reporting with stable reason codes for duplicate bars, impossible OHLC, missing periods, stale data, and extreme malformed values.
  - Added typed quality configuration for staleness, close-change, bar-range, and volume thresholds with fast validation of invalid thresholds.
  - Kept extreme-value checks scoped per exchange/symbol/timeframe/provider series so multi-provider inputs are reproducible.
  - Verified ordered reason codes can be persisted through the existing ingestion audit log.
  - **BTC-019 Policy Note:** run quality checks independently for Bitstamp,
    Coinbase, and Bitfinex before the synchronized comparison. A critical
    required-provider failure must remain visible and prevent source-policy
    promotion; optional benchmark entitlement is an access diagnostic, not a
    missing-bar quality failure.

#### BTC-031 Implement derivatives quality checks
- **Description:**
  Detect:

  - stale funding
  - impossible negative OI
  - sudden provider discontinuities
  - missing exchange snapshots
  - unit changes
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added deterministic derivatives quality reporting with stable reason codes for stale funding, negative open interest, provider discontinuities, missing exchange snapshots, and unit changes.
  - Added typed quality configuration for expected exchanges, required snapshot feeds, funding staleness, snapshot freshness, and provider gap thresholds.
  - Treated open interest and perpetual volume as required exchange snapshot feeds by default while avoiding false failures for liquidation feeds that can legitimately be empty.
  - Verified ordered reason codes can be persisted through the existing ingestion audit log.

#### BTC-032 Implement DATA_QUALITY_FAIL flag
- **Description:**
  ### Rule

  If critical inputs fail quality checks:

  ```text
  NO NEW TRADE
  NO ADD
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Predictor can still report existing position state
  - Failure reasons are persisted
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added a `DATA_QUALITY_FAIL` recommendation gate that converts failed OHLCV and derivatives quality reports into ordered predictor reason codes.
  - Vetoed new `ENTER` recommendations to `NO_TRADE` and `ADD` recommendations to `HOLD` so no new risk is introduced when critical inputs fail.
  - Preserved existing-position state on gated recommendations so HOLD/TRIM/EXIT reporting can still continue.
  - Added helpers to build ordered `signals.recommendation_reason_codes` records for persisting the fail flag and underlying data-quality reasons.

## EPIC E — Derived Market Data

#### BTC-040 Build daily, weekly, and monthly market bars
- **Description:**
  Generate canonical BTC daily, weekly, and monthly bars.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Consistent session definition
  - Weekly boundaries documented
  - Monthly boundaries documented
  - Reproducible aggregation
  - Point-in-time correct
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added a canonical BTC market-bar session definition using UTC daily, Monday-start weekly, and first-calendar-day monthly boundaries.
  - Added `build_canonical_market_bars` to generate daily, weekly, and monthly bars only from closed `1h` source bars ingested by the point-in-time `data_available_at` cutoff.
  - Reused the existing complete-bucket OHLCV aggregation logic for reproducible open/high/low/close/volume calculations.
  - Documented daily, weekly, and monthly session boundaries in the README and pinned them with focused tests.
  - **BTC-019 Policy Note:** derive each provider series independently. Only the
    provider approved by the persisted `PRICE_SOURCE_POLICY_V1` decision may be
    exposed as the strategy-canonical series; do not splice validation venues
    into historical gaps.
  - **EPIC E integration review:** only complete buckets are emitted, so a source
    outage removes that whole session and the canonical series may be
    non-contiguous. That is the intended `PRICE_SOURCE_POLICY_V1` behaviour, and
    BTC-041 now keeps the omission explicit instead of measuring across it.

#### BTC-041 Build rolling statistics framework
- **Description:**
  Reusable functions for:

  - rolling means
  - rolling volatility
  - z-scores
  - percentiles
  - ATR
  - historical normalization
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  All rolling calculations use only past information.
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added pure-Python rolling statistics helpers for rolling means, volatility, z-scores, percentiles, ATR, and historical normalization.
  - Kept rolling means, volatility, and ATR on trailing windows through the current completed observation.
  - Kept z-scores, percentiles, and historical normalization on prior-history windows that exclude the current value from the baseline.
  - Added lookahead-safety tests proving earlier outputs do not change when future values or bars are appended.
  - **V2 migration note:** BTC-043 replaced the pure-Python arithmetic with the
    NumPy production kernel. The independent Decimal reference oracle now lives
    in `test_quant_rolling_parity.py`, and `btc_predictor/features/rolling.py`
    is the Decimal-facing boundary over the kernel.
  - The public behavior and point-in-time semantics of BTC-041 must not change during vectorization.
  - **EPIC E integration review:** the kernels index observations, not sessions,
    so the bar-accepting boundary owns the adjacency precondition. `true_ranges`
    and `average_true_range` refuse a series that is not one regularly spaced
    timeframe, and report the range of a bar whose preceding session is absent
    from a BTC-040 series, plus any ATR window covering it, as missing rather
    than as a range measured against a several-sessions-older close.


## EPIC E2 — Quantitative Core Refactor

This epic is a controlled internal refactor. It must not change strategy behavior merely because calculations become vectorized.

#### BTC-042 Introduce NumPy/SciPy quantitative core
- **Description:**
  Create the `btc_predictor.quant` package and establish numerical conventions.

  Initial modules:

  ```text
  quant/
  ├── arrays.py
  ├── rolling.py
  ├── transforms.py
  ├── scoring.py
  ├── distances.py
  ├── risk.py
  ├── portfolio.py
  ├── statistics.py
  └── simulation.py
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - NumPy is a declared core runtime dependency
  - SciPy is available for statistical primitives
  - `quant/` has no database or domain-action dependencies
  - Internal numeric dtype convention is `float64`
  - NaN, infinity, tolerance, and array-shape policies are documented
  - Public helpers are typed and deterministic
  - Tests confirm invalid numeric inputs fail or propagate according to policy
- **Dependencies:** BTC-001, BTC-041
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added the complete `btc_predictor.quant` namespace and declared NumPy and
    SciPy as core runtime dependencies.
  - Frozen the `FLOAT64_V1` policy for owned `float64` arrays, exact shapes,
    explicit NaN propagation, infinity rejection, and `1e-12` tolerances.
  - Added typed array/vector/matrix validation helpers and explicitly seeded
    deterministic PCG64 simulation without database or domain-action imports.
  - Kept rolling, transforms, scoring, distances, risk, portfolio, and
    statistics mathematics reserved for BTC-043 through BTC-047.
  - Added 34 focused tests; the complete Python 3.12 suite passes with 609 tests.
  - Implemented in commit `c53a547c075e8a075bdbe8bbfefb7fe93ae7a3a4`.

#### BTC-043 Vectorize rolling statistics with parity
- **Description:**
  Implement NumPy versions of the BTC-041 numerical primitives:

  - rolling mean
  - rolling volatility
  - rolling z-score
  - rolling percentile
  - returns
  - true range
  - ATR
  - realized volatility
  - historical normalization
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - NumPy outputs match the BTC-041 reference implementation within defined tolerances
  - Past-only / no-look-ahead semantics are identical to BTC-041
  - Batch calculations and single-observation calculations agree
  - Missing values are never silently zero-filled
  - Earlier historical outputs do not change when future observations are appended
  - Existing feature APIs remain stable after internal migration
- **Dependencies:** BTC-042
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added vectorized NumPy kernels for rolling mean, rolling volatility,
    prior-window z-score, prior-window percentile, simple returns, true range,
    ATR, realized volatility, and prior-window historical normalization.
  - Froze Decimal-oracle parity at `1e-12` absolute and relative tolerance.
  - Preserved inclusive windows for mean/volatility/ATR and prior-only windows
    for z-score/percentile/normalization, with no future-data access.
  - Added explicit `raise`, `propagate`, and reduction-only `omit` behavior;
    warm-up and missing results remain NaN and are never zero-filled.
  - Migrated existing rolling and realized-volatility feature calculations to
    the NumPy kernels while retaining their Decimal/`None` public APIs.
  - Added 17 focused parity tests; the complete Python 3.12 suite passes with
    626 tests.

#### BTC-044 Implement nonlinear quantitative transform library
- **Description:**
  Centralize reusable transformations currently or potentially duplicated across feature engines.

  Implement:

  ```text
  gaussian_health
  sigmoid
  normal_cdf_score
  bounded_linear
  smooth_penalty
  exponential_decay
  clip_score
  percentile_to_health
  winsorize
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Functions accept scalars and NumPy arrays where appropriate
  - Scalar and vector results agree
  - Gaussian health can reproduce existing Funding/OI/Basis behavior
  - `normal_cdf_score` can reproduce existing Trend Score conversion
  - Boundary, NaN, zero-width, and extreme-value cases are tested
  - No domain interpretation or reason-code logic exists inside `quant.transforms`
- **Dependencies:** BTC-042
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added typed scalar/array `float64` implementations of all nine requested
    transforms in the domain-free `btc_predictor.quant.transforms` module.
  - Defined explicit validation for NaN propagation, infinity, score and
    percentile bounds, probabilities, non-negative decay distances, and
    degenerate or zero-width parameters.
  - Used stable SciPy logistic and normal-CDF primitives and deterministic
    NumPy linear-interpolation quantiles for winsorization.
  - Migrated Funding, OI growth, futures-basis, and OI-intensity health plus
    Trend and Flow CDF conversion without changing their Decimal-facing or
    persisted feature APIs.
  - Added 34 focused tests covering scalar/vector parity, formula parity,
    boundaries, NaN handling, zero-width inputs, and extreme values; the full
    Python 3.12 suite passes with 660 tests.

#### BTC-045 Implement volatility-normalized distance engine
- **Description:**
  Create reusable price-distance mathematics for structure, entry quality, clustering, no-chase rules, and stop research.

  Primary measure:

  \[
  D_{ij}=\frac{|P_i-P_j|}{ATR}
  \]

  Implement:

  ```text
  pairwise_price_distance
  atr_normalized_distance
  distance_to_support
  distance_to_resistance
  cluster_distance_matrix
  entry_distance_score
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Supports scalar and vector inputs
  - Handles zero/missing ATR explicitly
  - Produces deterministic pairwise distance matrices
  - Can reproduce existing static/fractional clustering behavior as a compatibility mode
  - BTC-095 can optionally use ATR-normalized clustering without changing its persistence API
  - Entry/no-chase distance can be represented in ATR units
- **Dependencies:** BTC-042, BTC-043, BTC-095
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added typed scalar/vector absolute and ATR-normalized distance helpers,
    nearest support/resistance lookup, deterministic pairwise cluster matrices,
    and entry-distance scoring.
  - Added absolute/static, fractional, and ATR matrix modes. Fractional mode
    matches BTC-095's lower-price denominator for sorted adjacent levels.
  - Enforced strictly positive prices and ATR, explicit missing ATR failures,
    exact shape matching with scalar-only expansion, and explicit NaN results
    when no directional level exists.
  - Added optional ATR-normalized clustering to BTC-095 through `cluster_atr`
    and `cluster_atr_distance_threshold` without changing its result dataclasses
    or serialized record keys; fractional clustering remains the default.
  - Added 23 focused distance and compatibility tests; the complete Python 3.12
    suite passes with 683 tests.

#### BTC-046 Implement generic vectorized scoring engine
- **Description:**
  Implement reusable weighted scoring:

  \[
  S=Xw
  \]

  for both individual observations and historical matrices.

  Intended consumers include:

  - Trend Score
  - Flow Score
  - Positioning Score
  - Volatility Score
  - Structure Score
  - Regime Score
  - Entry Conviction
  - Hold Score
  - Add Score
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Supports scalar row and matrix calculations
  - Validates weight names, shape, and total according to config policy
  - Returns per-component contributions
  - Missing inputs are surfaced by masks rather than zero-filled
  - Batch and single-row output are numerically equivalent
  - Existing completed composite-score outputs can be reproduced
- **Dependencies:** BTC-042, BTC-044
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added typed named weighted scoring for individual component rows and
    historical matrices using one `float64` contribution and reduction path.
  - Added exact mapping-name and shape validation, non-negative and positive-
    total weight policy, and configurable expected-total tolerance.
  - Added per-component missing masks and row-completeness masks; incomplete
    rows retain NaN scores and are never partially summed or zero-filled.
  - Added a feature-layer Decimal compatibility boundary and migrated Trend,
    Flow, Positioning, Structure, Regime, and Orderliness weighting without
    changing their model selection, reason codes, Decimal scale, or persisted
    payloads.
  - Added 25 focused tests for row/matrix parity, contribution output, name and
    weight validation, missing masks, empty histories, and determinism; the
    complete Python 3.12 suite passes with 708 tests.

#### BTC-047 Implement vectorized risk and portfolio mathematics
- **Description:**
  Build the shared numerical primitives used by live recommendations, paper trading, and backtesting.

  Implement:

  ```text
  stop_distance
  reward_risk_ratio
  position_notional
  capital_at_risk
  risk_at_stop
  risk_contribution_by_tranche
  risk_improvement
  weighted_average_entry
  unrealized_pnl
  realized_pnl
  gross_exposure
  net_exposure
  max_allowed_notional
  ```

  For long tranches:

  \[
  RiskAtStop =
  \sum_i N_i
  \max\left(\frac{E_i-S}{E_i},0\right)
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Supports arbitrary tranche counts
  - Handles long and short positions explicitly
  - Scalar and vector calculations agree
  - Risk is never negative
  - Empty portfolios are handled explicitly
  - Same functions can be called from risk engine, paper trader, and backtester
  - Numerical layer does not decide ENTER/HOLD/ADD/TRIM/EXIT
- **Dependencies:** BTC-042
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added all thirteen requested typed `float64` risk and portfolio primitives
    with explicit scalar expansion and exact non-scalar shape matching.
  - Frozen unsigned quantity/notional plus explicit `long`/`short` conventions,
    directional reward/risk, and signed realized/unrealized P&L.
  - Implemented arbitrary-tranche risk-at-stop using the rulebook formula and
    symmetric short risk, flooring profitable stop outcomes at zero downside.
  - Defined empty aggregates as zero risk/exposure and empty or zero-quantity
    weighted-average entry as NaN; zero stop-distance sizing fails fast.
  - Kept recommendation actions and lifecycle decisions outside the quant
    modules so advisory, paper-trading, and backtest consumers share one API.
  - Added 29 focused cases covering long/short parity, arbitrary tranches,
    scalar/vector agreement, risk non-negativity, NaN policy, invalid shapes,
    empty portfolios, deterministic recomputation, and Structure R/R parity;
    the complete Python 3.12 suite passes with 737 tests.

#### BTC-048 Build point-in-time feature matrix
- **Description:**
  Build a reproducible matrix representation for quant research and batch scoring.

  Conceptually:

  \[
  X_{t,f}
  \]

  where rows are decision timestamps and columns are features.

  Initial columns include component scores plus important raw/normalized predictors.

  Target data should support:

  ```text
  future_1w_return
  future_2w_return
  future_4w_return
  future_8w_return
  future_MFE
  future_MAE
  hit_2R_before_1R
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Every row has an explicit decision timestamp
  - Only information available by that timestamp enters X
  - Feature names and ordering are persisted or reproducibly defined
  - Missing-value masks are retained
  - Matrix can be generated for a date range deterministically
  - Matrix supports NumPy/scikit-learn/statsmodels consumers without database knowledge
  - Forward targets are stored separately from contemporaneous features
- **Dependencies:** BTC-040, BTC-043, BTC-046
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added a versioned `POINT_IN_TIME_FEATURE_MATRIX_V2` research contract with
    a frozen initial numeric feature order and deterministic SHA-256 definition
    fingerprint covering strategy/config, parameter-set, feature implementation,
    price-source, reference-price, and point-in-time policy versions.
  - Added typed feature observations with UTC observation and availability
    times, revision identity, and source provenance; as-of selection uses only
    values available by each decision timestamp.
  - Retained `float64` values, explicit missing-value masks, observation times,
    availability times, source IDs, and selected revision identities in immutable
    matrix datasets and deterministic serialized records.
  - Added deterministic inclusive decision-time ranges, date filtering,
    JSON-compatible persistence records, and direct NumPy/BTC-046 batch-scoring
    handoff without database knowledge.
  - Kept all seven requested future outcomes in the separate versioned
    `FORWARD_TARGET_MATRIX_V2` contract. Fixed 1/2/4/8-week return horizons use
    exact elapsed calendar time; MFE/MAE and barrier labels retain explicit
    source-defined semantics until their generation policies are frozen.
  - Added 24 focused cases covering future-data invariance, late revisions,
    ordering, date ranges, missing values, immutable consumer copies, target
    separation, invalid inputs, and deterministic serialization; the complete
    Python 3.12 suite passes with 761 tests.

#### BTC-049 Quant parity, numerical-safety, and batch-validation suite
- **Description:**
  Validate the new numerical core before downstream strategy work relies on it.
- **Status:** DONE
- **Release Gate:** CLOSED
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Pure-Python reference vs NumPy rolling parity tests pass
  - Existing Trend/Flow/Positioning/Structure score fixtures can be reproduced
  - Single-date vs batch-history calculations match
  - Future-data append tests prove no look-ahead changes historical outputs
  - NaN and infinity behavior is tested
  - Numerical tolerance policy is centralized
  - Basic performance benchmarks exist, but correctness takes priority over speed
  - Quant migration cannot be considered complete while parity tests fail
- **Dependencies:** BTC-043, BTC-044, BTC-045, BTC-046, BTC-047, BTC-048
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Centralized Python/Decimal parity tolerances through the shared
    `PARITY_TOLERANCE` numeric policy with `1e-12` absolute and relative bounds.
  - Added a cross-module release gate reproducing rolling Python oracles and
    existing Trend, Flow, Positioning, and Structure score fixtures.
  - Verified single-date versus batch-history equivalence and future-data
    append invariance across rolling kernels, BTC-046 scoring, BTC-047 risk,
    and BTC-048 feature matrices.
  - Corrected portfolio matrix reductions to return one aggregate per decision
    row, made risk improvement compare aggregate portfolio risk before
    clipping, and added stable summation for nearly hedged exposure.
  - Added controlled output-infinity rejection across rolling, transforms,
    distances, scoring, risk, and portfolio arithmetic; NaN remains explicit
    only under the documented missing/warm-up/undefined policies.
  - Added the seeded `QUANT_BENCHMARK_V1` CLI for rolling mean, rolling z-score,
    eight-component scoring, and four-tranche batch risk. Benchmarks persist
    checksums and throughput diagnostics but impose no speed threshold.
  - Added 15 focused cases; the initial Python 3.12 suite passed with 776
    tests, subject to the parity and numerical-safety release gate remediated
    below.
  - Reopened and remediated the E2 correctness gate with the centralized
    `DECISION_COMPARISON_V1` hard-threshold policy, using the existing `1e-12`
    absolute/relative tolerance without rounding persisted values.
  - Added stable extreme-finite arithmetic and deterministic rejection of
    unrepresentable simulation, rolling, transform, and distance outputs; no
    unexpected NaN/infinity is allowed to escape relevant public quant APIs.
  - Versioned target semantics and material feature-calculation provenance,
    enforced exact fixed-return horizons, and preserved selected PIT revision
    identity in feature and target serialization.
  - Added dedicated decision-boundary and research-integrity regressions. The
    complete E2 suite passes with 212 tests and the full Python 3.12.14 suite
    passes with 788 tests while treating `RuntimeWarning` as an error; compileall
    also passes.


## EPIC F — Trend Engine

#### BTC-050 Implement 4-week momentum
- **Description:**
  \[
  M_4=P_t/P_{t-28}-1
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `MOMENTUM_4W` helpers implementing `P_t / P_t-28 - 1` for price series and canonical daily close bars.
  - Kept outputs deterministic by sorting daily bars by timestamp before reading closes.
  - Added focused tests for exact 28-day math, no-lookahead behavior, zero prior-price handling, and daily-bar validation.

#### BTC-051 Implement 12-week momentum
- **Description:**
  \[
  M_{12}=P_t/P_{t-84}-1
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `MOMENTUM_12W` helpers implementing `P_t / P_t-84 - 1` for price series and canonical daily close bars.
  - Shared the generic price-momentum calculation with the 4-week momentum helper while preserving the existing public API.
  - Added focused tests for exact 84-day math, no-lookahead behavior, and timestamp-ordered daily-bar inputs.

#### BTC-052 Implement 20-week MA distance
- **Description:**
  Complete the ticket scope for implement 20-week ma distance.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `MA_DISTANCE_20W` helpers implementing `(P_t - MA_20W) / MA_20W` for price series and canonical weekly close bars.
  - Used the past-only rolling mean framework for the trailing 20-week moving average.
  - Added focused tests for exact formula output, deterministic timestamp ordering, zero-MA handling, and no-lookahead behavior.

#### BTC-053 Implement weekly structure classifier
- **Description:**
  Classify:

  ```text
  HH + HL
  HL only
  Mixed
  LH only
  LH + LL
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added weekly structure classification for `HH_HL`, `HL_ONLY`, `MIXED`, `LH_ONLY`, and `LH_LL`.
  - Mapped labels to rulebook raw scores from +1.0 to -1.0 and exposed stable `WEEKLY_STRUCTURE_*` reason codes for later persistence.
  - Added canonical weekly-bar wrapper that sorts by timestamp before comparing each completed week to the prior week.
  - Added focused tests for every classification, deterministic ordering, invalid inputs, and no-lookahead behavior.

#### BTC-054 Implement 52-week-high distance
- **Description:**
  Complete the ticket scope for implement 52-week-high distance.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `HIGH_DISTANCE_52W` helpers implementing `(P_t - H_52W) / H_52W` for price/high series and canonical weekly bars.
  - Used the trailing 52-week high through the current completed weekly bar for point-in-time-safe calculations.
  - Added focused tests for exact formula output, deterministic timestamp ordering, zero-high handling, invalid inputs, and no-lookahead behavior.

#### BTC-055 Implement Trend Score
- **Description:**
  Initial formula:

  \[
  TrendRaw =
  0.30Z_{M4}
  +0.30Z_{M12}
  +0.20Z_{20W}
  +0.15S_{structure}
  +0.05Z_{52H}
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Output 0–100
  - Inputs persisted
  - Score explainable
  - Historical recomputation deterministic
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `calculate_trend_score` implementing the rulebook weighted composite and `100 * Phi(TrendRaw)` conversion.
  - Added typed `TrendScoreInput` and `TrendScoreResult` payloads that expose component inputs, weights, contributions, interpretation, and stable reason code.
  - Added deterministic serialization through `TrendScoreResult.as_record()` for historical recomputation and persistence.
  - Added focused tests for formula output, score bounds, explainability, weight validation, score-band interpretation, and recomputation from persisted inputs.
  - **V2 migration note:** keep `calculate_trend_score` and its persisted result contract stable; move weighted math/CDF calculation behind BTC-044/BTC-046 only after parity passes.

## EPIC G — Flow Engine

#### BTC-060 Implement 5-day ETF flow feature
- **Description:**
  Complete the ticket scope for implement 5-day etf flow feature.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `ETF_FLOW_5D` and `ETF_NORM_5D` feature helpers using latest ETF flow revisions available at the signal timestamp.
  - Summed complete five-publication-day windows across the configured fund universe and normalized by latest available fund AUM.
  - Emitted stable reason codes for missing flow inputs or missing AUM instead of silently substituting zeroes.
  - Added deterministic serialization through `EtfFlowFeatureResult.as_record()` for persistence and historical recomputation.

#### BTC-061 Implement 20-day ETF flow feature
- **Description:**
  Complete the ticket scope for implement 20-day etf flow feature.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `ETF_FLOW_20D` and `ETF_NORM_20D` helpers using the shared point-in-time ETF flow window engine.
  - Summed complete twenty-publication-day windows across the configured fund universe and normalized by latest available fund AUM.
  - Reused stable ETF flow reason codes for missing flow inputs or missing AUM.
  - Covered deterministic serialization for persistence and historical recomputation.

#### BTC-062 Implement ETF flow acceleration
- **Description:**
  \[
  FlowAccel=
  ETFNorm_5-\frac{ETFNorm_{20}}{4}
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `FLOW_ACCEL` calculation as `ETF_NORM_5D - ETF_NORM_20D / 4`.
  - Persisted source normalized feature IDs and values through `EtfFlowAccelerationResult.as_record()`.
  - Propagated upstream ETF flow reason codes and emitted `ETF_FLOW_ACCEL_INPUT_MISSING` when acceleration cannot be calculated.
  - Added fail-fast validation for mismatched observation dates or incorrect input windows.

#### BTC-063 Implement spot vs perp participation
- **Description:**
  Complete the ticket scope for implement spot vs perp participation.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `SPOT_DOMINANCE` as `z(SpotVolumeGrowth) - z(PerpVolumeGrowth)`.
  - Defined volume growth as current trailing notional-volume window versus the previous equal-length window.
  - Added typed `VolumeParticipationObservation` inputs plus an adapter from spot OHLCV and perp volume rows.
  - Emitted stable reason codes for missing spot volume, missing perp volume, or insufficient history instead of zero-filling.
  - Added deterministic serialization through `SpotPerpParticipationResult.as_record()` for persistence and recomputation.

#### BTC-064 Implement spot vs perp CVD spread
- **Description:**
  Complete the ticket scope for implement spot vs perp cvd spread.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `CVD_SPREAD` as `z(SPOT_CVD) - z(PERP_CVD)`.
  - Added typed `CvdObservation` inputs with point-in-time `available_at` filtering.
  - Aggregated spot and perp CVD observations on common timestamps and z-scored using prior history only.
  - Emitted stable reason codes for missing spot CVD, missing perp CVD, or insufficient history instead of zero-filling.
  - Added deterministic serialization through `SpotPerpCvdSpreadResult.as_record()` for persistence and recomputation.

#### BTC-065 Implement Flow Score
- **Description:**
  Initial formula:

  \[
  FlowRaw =
  0.30z(ETFNorm_5)
  +0.25z(ETFNorm_{20})
  +0.20z(FlowAccel)
  +0.15z(CVDSpread)
  +0.10z(SpotDominance)
  \]

  Until P1 spot/perp inputs are implemented, use the Phase 1 ETF-core fallback:

  \[
  FlowRaw_{core} =
  0.40z(ETFNorm_5)
  +0.35z(ETFNorm_{20})
  +0.25z(FlowAccel)
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Missing P1 inputs are not silently filled with zero
  - Output records `FLOW_MODEL = ETF_CORE` or `FLOW_MODEL = ETF_SPOT_PERP_FULL`
  - Formula weights are loaded from versioned strategy config
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `FLOW_SCORE` using the full model when ETF, acceleration, CVD spread, and spot dominance z-score inputs are available.
  - Added the `ETF_CORE` fallback using ETF-only weights when P1 spot/perp inputs are missing, without zero-filling missing P1 components.
  - Persisted selected flow model, inputs, weights, contributions, score, interpretation, reason codes, and config metadata through `FlowScoreResult.as_record()`.
  - Added `full_flow` weights to the versioned strategy config and validated exact full/core flow weight keys at startup.
  - **V2 migration note:** retain full/core model selection and missing-input semantics in the domain layer; vectorized weighted math migrates behind BTC-043/BTC-046.

## EPIC H — Positioning Engine

#### BTC-070 Implement funding health
- **Description:**
  Input:

  - 7d funding average
  - 180d rolling z-score
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `FUNDING_HEALTH` from the current 7-day average funding rate and 180-day rolling z-score.
  - Implemented the rulebook Gaussian health curve centered on mildly positive funding z-score.
  - Filtered funding rows by point-in-time `available_at` and `observation_time`.
  - Persisted average/z-score feature IDs, windows, health-curve parameters, counts, score, and reason codes through `FundingHealthResult.as_record()`.
  - Emitted stable reason codes for missing funding input, insufficient history, and zero-variance history.

#### BTC-071 Implement OI growth health
- **Description:**
  Use rolling normalization rather than fixed permanent thresholds.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `OI_GROWTH_HEALTH` from `OI_GROWTH_7D = OI_t / OI_t-7 - 1`.
  - Aggregated open interest by timestamp for a selected unit and avoided mixing incompatible provider units.
  - Rolling-normalized OI growth with a 180-day prior-history z-score instead of fixed permanent percentage thresholds.
  - Applied a configurable Gaussian health curve to reward modest expansion while penalizing extreme crowded growth.
  - Persisted unit, current/prior OI, growth, z-score, health-curve parameters, counts, and reason codes through `OpenInterestGrowthHealthResult.as_record()`.

#### BTC-072 Implement OI intensity
- **Description:**
  \[
  OIIntensity=AggregateOI/BTCMarketCap
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `OI_INTENSITY = AggregateOI / BTCMarketCap` as a point-in-time positioning feature.
  - Introduced explicit `MarketCapObservation` inputs so recomputation does not depend on hidden live data.
  - Aggregated OI by timestamp for the selected unit and converted the ratio into a 180-day rolling historical percentile.
  - Mapped high OI-intensity percentile readings to lower leverage health scores.
  - Persisted aggregate OI, market cap, intensity, percentile, health score, counts, and stable reason codes through `OpenInterestIntensityResult.as_record()`.

#### BTC-073 Implement futures-basis health
- **Description:**
  Complete the ticket scope for implement futures-basis health.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `FUTURES_BASIS_HEALTH` using point-in-time futures-basis rows.
  - Averaged raw and annualized basis per timestamp across available contracts/exchanges.
  - Rolling-normalized annualized basis with a 180-day prior-history z-score.
  - Applied a configurable Gaussian health curve that prefers moderately positive basis and penalizes unusually weak or crowded readings.
  - Persisted basis averages, z-score, health-curve parameters, counts, and reason codes through `FuturesBasisHealthResult.as_record()`.

#### BTC-074 Implement Positioning Score
- **Description:**
  \[
  PositioningScore=
  0.35FundingHealth
  +0.30OIHealth
  +0.20BasisHealth
  +0.15LeverageHealth
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `POSITIONING_SCORE` as the rulebook weighted composite of funding, OI, basis, and leverage health components.
  - Added versioned `[scoring_weights.positioning]` config with exact component-key validation at startup.
  - Persisted inputs, weights, per-component contributions, config metadata, interpretation, and reason codes through `PositioningScoreResult.as_record()`.
  - Missing component inputs are not zero-filled; incomplete scores emit `POSITIONING_SCORE_INPUT_MISSING`.
  - In Phase 1, `OIHealth` maps to OI growth health and `LeverageHealth` maps to OI intensity health.
  - **V2 migration note:** preserve Positioning Score inputs, contributions, and reason-code behavior while Gaussian/scoring math is centralized through BTC-044/BTC-046.

#### BTC-075 Implement CROWDING flag
- **Description:**
  Effect:

  ```text
  NO ADD
  REDUCE ENTRY QUALITY
  OPTIONAL TIGHTER PROFIT PROTECTION
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `CROWDING` as a deterministic positioning flag triggered by excessive
    funding z-score, futures-basis z-score, or OI-intensity percentile.
  - Added versioned `[positioning_flags.crowding]` config for funding threshold,
    basis threshold, OI-intensity percentile threshold, and entry-quality penalty.
  - Persisted inputs, thresholds, effects, config metadata, completion state, and
    reason codes through `CrowdingFlagResult.as_record()`.
  - Missing flag inputs are not silently treated as normal; incomplete
    evaluations emit `CROWDING_INPUT_MISSING`.
  - Flagged evaluations emit `NO_ADD`, `REDUCE_ENTRY_QUALITY`, and
    `OPTIONAL_TIGHTER_PROFIT_PROTECTION` effects.

## EPIC I — Volatility Engine

#### BTC-080 Implement RV7 / RV20 / RV60
- **Description:**
  Complete the ticket scope for implement rv7 / rv20 / rv60.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added annualized close-to-close realized volatility helpers for RV7, RV20,
    and RV60 from point-in-time canonical daily bars.
  - Used trailing daily return windows through the current completed observation
    and annualized by the configured periods count.
  - Persisted feature ID, observation time, window, annualization periods,
    realized volatility, source counts, completion state, and reason codes
    through `RealizedVolatilityResult.as_record()`.
  - Emitted stable reason codes for missing input, insufficient history, and
    non-positive closes instead of silently zero-filling invalid outputs.
  - **V2 migration note:** realized-volatility numerical kernels migrate to BTC-043 after parity with existing persisted fixtures.

#### BTC-081 Implement compression ratio
- **Description:**
  \[
  RV_7/RV_{60}
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `VOL_COMPRESSION_RATIO = RV_7 / RV_60`.
  - Consumes explicit RV7/RV60 values or persisted realized-volatility results.
  - Persists numerator and denominator feature IDs, inputs, ratio, completion
    state, and stable reason codes through
    `VolatilityCompressionRatioResult.as_record()`.
  - Missing RV inputs and zero RV60 denominator are reported explicitly instead
    of silently zero-filling.
  - **V2 migration note:** compression calculation may use the quant core internally, but persisted feature semantics remain unchanged.

#### BTC-082 Implement volatility percentile
- **Description:**
  Complete the ticket scope for implement volatility percentile.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `VOL_PERCENTILE_2Y` from the rulebook formula
    `Percentile(RV20, 2yr)`.
  - Uses the latest persisted RV20 result available at signal time and ranks it
    against prior RV20 history only, excluding the current observation and future
    results.
  - Defaults to a 730-day percentile window with configurable minimum history.
  - Persists source feature ID, window parameters, realized volatility,
    percentile, counts, completion state, and reason codes through
    `VolatilityPercentileResult.as_record()`.
  - Missing RV20 input and insufficient history are reported explicitly instead
    of silently zero-filling.
  - **V2 migration note:** percentile calculation migrates to BTC-043 while preserving prior-history-only ranking semantics.

#### BTC-083 Implement orderliness score
- **Description:**
  Penalize:

  - extreme ranges
  - disorderly downside
  - liquidation cascades
  - volatility spikes
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `ORDERLINESS_SCORE`, starting from 100 and subtracting configured
    component penalties.
  - Penalizes extreme range percentile, disorderly downside return, liquidation
    percentile, and volatility percentile triggers.
  - Exports default equal weights plus default thresholds for each component.
  - Persists inputs, weights, thresholds, penalties, interpretation, config
    metadata, completion state, and reason codes through
    `OrderlinessScoreResult.as_record()`.
  - Missing component inputs are reported explicitly instead of silently
    zero-filling.
  - **V2 migration note:** numerical penalty aggregation may migrate to BTC-046; trigger interpretation remains in the volatility domain module.

#### BTC-084 Implement Volatility Score
- **Description:**
  Complete the ticket scope for implement volatility score.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-043, BTC-044, BTC-046
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `VOLATILITY_SCORE` as the rulebook v1.2 composite
    `0.5 CompressionScore + 0.5 OrderlinessScore`, using the shared BTC-046
    `decimal_weighted_score` boundary so advisory, paper, and backtest layers
    share one formula.
  - Added `COMPRESSION_SCORE`, a clamped linear ramp over RV7/RV60: full score
    at or below `0.70`, zero at or above `1.30`. The bounds are symmetric about
    the rulebook's `RV7 / RV60 < 1` boundary, so a neutral ratio scores 50.
  - Classifies the volatility regime as COMPRESSED / NORMAL / ELEVATED /
    STRESSED from the 2-year RV20 percentile. The regime is reported for
    setup-specific interpretation and deliberately does not enter the weighted
    composite, so a missing percentile never blocks the score.
  - Persists inputs, weights, thresholds, per-component contributions,
    compression score, regime, interpretation, config metadata, completion
    state, and reason codes through `VolatilityScoreResult.as_record()`.
  - Missing component inputs produce `VOLATILITY_SCORE_INPUT_MISSING` and a
    `None` score rather than a silent zero-fill.
  - `calculate_volatility_score_from_results()` composes the score directly
    from persisted BTC-081/BTC-082/BTC-083 feature results.
  - Threshold and band comparisons use `DECISION_COMPARISON_V1` helpers, and
    the score ramp stays in exact `Decimal`, matching the existing
    entry-location convention rather than round-tripping through float64.

#### BTC-085 Implement STRESS flag
- **Description:**
  Effect:

  ```text
  NO ADD
  REDUCE MAX EXPOSURE
  OPTIONALLY BLOCK NEW TRADES
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added hard `STRESS` flag evaluation with `NO_ADD`,
    `REDUCE_MAX_EXPOSURE`, and `OPTIONALLY_BLOCK_NEW_TRADES` effects.
  - Triggers on extreme volatility percentile, liquidation cascade percentile,
    disorderly downside return, abnormal funding z-score, abnormal basis z-score,
    or systemic market shock.
  - Exports default stress thresholds, max-exposure multiplier, and optional
    new-trade block setting.
  - Added `[volatility_flags.stress]` to the versioned strategy config with
    startup validation for percentile thresholds, downside threshold, funding
    and basis z-score thresholds, max-exposure multiplier, and new-trade block
    setting.
  - Persists inputs, thresholds, max-exposure multiplier, block-new-trades
    setting, effects, config metadata, completion state, and reason codes
    through `StressFlagResult.as_record()`.
  - Missing trigger inputs are reported explicitly instead of silently treating
    them as normal market conditions.

## EPIC J — Price-Level / Structure Engine

#### BTC-090 Detect weekly swing highs/lows
- **Description:**
  Complete the ticket scope for detect weekly swing highs/lows.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Point-in-time detection
  - No use of future bars before level confirmation
  - Detection timestamp persisted separately from level timestamp
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `detect_weekly_swing_levels` for confirmed canonical `1w` swing highs
    and lows.
  - Uses configurable left/right weekly confirmation windows with defaults from
    the phase-1 `swing_window_weeks` convention.
  - Filters source bars to observations closed and ingested by `as_of`, and does
    not emit a level before the right-side confirmation bar is available.
  - Persists `level_timestamp` separately from `detected_at` through
    `WeeklySwingLevel.as_record()`.
  - Records swing type, price, exchange, symbol, timeframe, provider, window
    parameters, and source count for deterministic replay.

#### BTC-091 Detect monthly swing highs/lows
- **Description:**
  Complete the ticket scope for detect monthly swing highs/lows.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `detect_monthly_swing_levels` for confirmed canonical `1mo` swing
    highs and lows.
  - Uses configurable left/right monthly confirmation windows with defaults from
    the phase-1 `swing_window_months` convention.
  - Filters source bars to observations closed and ingested by `as_of`, and does
    not emit a level before the right-side confirmation month is available.
  - Persists level timestamp separately from detected timestamp through
    `MonthlySwingLevel.as_record()`.
  - Records swing type, price, exchange, symbol, timeframe, provider, window
    parameters, and source count for deterministic replay.

#### BTC-092 Detect breakout/reclaim levels
- **Description:**
  Complete the ticket scope for detect breakout/reclaim levels.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `detect_breakout_reclaim_levels` for structural breakout/reclaim
    levels from confirmed weekly/monthly swing levels.
  - Breakouts require a canonical confirmation bar close above a prior swing
    high; reclaims require a bar trading through a prior swing low and closing
    back above it.
  - Uses only source levels and confirmation bars available by `as_of`, and
    waits for confirmation bars to close and be ingested.
  - Persists confirmation timestamp, detection timestamp, source swing
    provenance, close buffer, confirming close/low, series identity, and stable
    reason codes through `BreakoutReclaimLevel.as_record()`.
  - Added `breakout_close_buffer_fraction` and
    `reclaim_close_buffer_fraction` to versioned `price_levels` config with
    startup validation.

#### BTC-093 Implement anchored VWAP support
- **Description:**
  Anchor types:

  - major swing low
  - major swing high
  - breakout
  - capitulation event
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor.levels.anchored_vwap` with explicit anchors for
    `major_swing_low`, `major_swing_high`, `breakout`, and
    `capitulation_event`.
  - Swing anchors preserve original level timestamp separately from detection
    time; breakout anchors use the confirmation timestamp; capitulation anchors
    use explicit event metadata.
  - `calculate_anchored_vwap` includes only OHLCV bars matching the anchor
    series that are closed and ingested by `as_of`, and it does not emit a
    complete result before the anchor is detectable.
  - Results persist anchor provenance, configured price source, source
    timeframe, bar count, volume sum, price-volume sum, completion state, and
    reason codes.
  - Added `anchored_vwap_price_source` to versioned `price_levels` config with
    startup validation for `hlc3` and `close`.

#### BTC-094 Implement volume-profile levels
- **Description:**
  Candidates:

  - POC
  - HVN
  - VAH
  - VAL
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor.levels.volume_profile` for deterministic POC, HVN,
    VAH, and VAL records from point-in-time OHLCV bars.
  - Bars are filtered to those closed and ingested by `as_of`, then validated
    as a single market series and timeframe before profile levels are emitted.
  - Price-bin size, price source, value-area coverage, HVN volume threshold,
    and minimum bar count are loaded from versioned `price_levels` config and
    persisted in result and level records.
  - Results persist profile window, bin boundaries, level prices, bin volume,
    total volume, value-area volume, completion state, and reason codes.
  - Missing input, insufficient history, and zero-volume profiles are reported
    explicitly instead of silently producing fallback levels.

#### BTC-095 Implement level clustering
- **Description:**
  Combine nearby levels into support/resistance zones.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Cluster boundaries persisted
  - Member levels linked
  - Confluence score available
  - No double-counting of nearby lines
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor.levels.clustering` with `cluster_price_levels`,
    `LevelClusterMember`, `LevelCluster`, and `LevelClusterResult`.
  - Clustering accepts persisted level records or objects with `as_record()`,
    expands `VOLUME_PROFILE_LEVELS` result records into member levels, and
    treats completed `ANCHORED_VWAP` results as level members.
  - Levels are filtered by `as_of`; future sources, incomplete sources, and
    exact duplicate member IDs are counted and reported through reason codes.
  - Nearby prices are grouped using versioned `cluster_distance_fraction` and
    classified as support/resistance relative to the reference price.
  - Cluster records persist deterministic boundaries, weighted center price,
    stable cluster ID, linked member records, source/timeframe counts,
    `minimum_level_strength`, confluence score, completion state, and reason
    codes.
  - **V2 migration note:** BTC-045 adds ATR-normalized distance as the preferred research/production option; current fractional distance remains available for parity and comparison.

#### BTC-096 Implement level-strength score
- **Description:**
  Inputs:

  - timeframe
  - touch count
  - reaction magnitude
  - volume
  - confluence
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.levels.strength` with `LevelStrengthInput`,
    `LevelStrengthResult`, `calculate_level_strength`, and
    `calculate_level_strength_from_cluster`.
  - Score combines timeframe, touch count, reaction magnitude, volume
    percentile, and confluence using versioned
    `price_levels.level_strength_weights`.
  - Timeframe score table, full-touch count, and full-reaction fraction are
    loaded from versioned `price_levels` config and persisted with each result.
  - Cluster scoring reads member timeframes and confluence from cluster records
    and defaults touch count to cluster member count when no explicit touch
    metric is supplied.
  - Missing reaction/volume/confluence/timeframe inputs are reported explicitly
    instead of silently producing fallback scores; capped touch/reaction
    components emit reason codes.

#### BTC-097 Implement Structure Score
- **Description:**
  Initial formula:

  \[
  StructureScore=
  0.45LevelStrength
  +0.25EntryLocation
  +0.20RRQuality
  +0.10Confluence
  \]

  Phase 1 scope:

  - Weekly/monthly swing levels
  - Breakout/reclaim levels
  - Level clusters
  - Entry distance to support/resistance cluster
  - R/R quality based on nearest credible structural target

  AVWAP and volume-profile evidence are optional P1 enhancements and must not be
  required for the Phase 1 score.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.features.structure` with `StructureScoreInput`,
    `StructureSelection`, `StructureScoreResult`, `calculate_structure_score`,
    and `calculate_structure_score_from_clusters`.
  - Direct scoring applies
    `0.45 LevelStrength + 0.25 EntryLocation + 0.20 RRQuality + 0.10 Confluence`
    using versioned `scoring_weights.structure_score`.
  - Cluster scoring selects the nearest support cluster below entry and nearest
    resistance cluster above entry as the structural target, without requiring
    AVWAP or volume-profile evidence for the Phase 1 score.
  - Entry location uses versioned `price_levels` support-distance thresholds;
    R/R quality uses configured `rr_minimum`, `rr_preferred_min`, and
    `rr_preferred_max`.
  - Results persist component inputs, weights, contributions, selected
    support/target clusters, entry/stop prices, reward/risk, normalization
    parameters, config metadata, interpretation, completion state, and reason
    codes.
  - Missing support, target, level strength, or invalid risk are reported
    explicitly instead of silently filling component scores.
  - **V2 migration note:** preserve cluster selection, structural target selection, and persistence API; BTC-045/BTC-046 may replace only internal distance/scoring mathematics.
  - **v1.2 strategy note:** the completed v1.1 weighted formula remains a historical
    reference fixture. BTC-098 introduces the de-nested v1.2 Structure Score and
    must use a new strategy/config version rather than silently changing v1.1 history.

#### BTC-098 Implement Structure Score v1.2 de-nesting
- **Description:**
  Replace the v1.1 outer Structure composite:

  \[
  0.45LevelStrength + 0.25EntryLocation + 0.20RRQuality + 0.10Confluence
  \]

  with the v1.2 de-nested definition:

  \[
  StructureScore_{v1.2} =
  0.642857LevelStrength +
  0.357143EntryLocation
  \]

  `RRQuality` is removed from Structure arithmetic because R/R remains an
  independent hard asymmetry filter.

  Outer `Confluence` is removed because confluence is already represented inside
  `LevelStrength`.

- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - v1.1 Structure Score remains reproducible from historical persisted inputs
  - v1.2 uses only `LevelStrength` and `EntryLocation` as weighted outer components
  - v1.2 weights sum to 1 within configured numerical tolerance
  - R/R can still be calculated/persisted diagnostically but contributes zero weight to Structure
  - Confluence can still be persisted diagnostically but has no second outer contribution
  - Existing support/target cluster selection behavior remains available
  - New score/config version is persisted; historical v1.1 records are not overwritten
  - Focused tests cover exact re-normalized weights, missing inputs, score bounds, and deterministic recomputation
- **Dependencies:** BTC-045, BTC-046, BTC-097
- **Priority:** P0
- **Complexity:** M
- **Risk:** High.
- **Implementation Notes:**
  - Added an explicit `version` argument selecting `STRUCTURE_SCORE_V1_1` or
    `STRUCTURE_SCORE_V1_2`, with per-version component IDs and weights. v1.2 is
    now the default; v1.1 stays fully reachable and is pinned by its original
    tests, so historical records remain reproducible from the same persisted
    inputs.
  - v1.2 weights are `0.642857 LevelStrength + 0.357143 EntryLocation`, the
    v1.1 0.45/0.25 pair renormalized over their 0.70 subtotal. They sum to
    exactly `1.000000`, within the named
    `STRUCTURE_SCORE_WEIGHT_SUM_TOLERANCE` of 1e-6.
  - `rr_quality` and `confluence` are still accepted, calculated from clusters,
    and persisted, but under v1.2 they move out of `weights`/`contributions`
    into a separate `diagnostics` map and carry zero weight.
  - Because a zero-weight component cannot invalidate the composite, a missing
    R/R no longer makes a v1.2 Structure Score incomplete. An undefined R/R now
    yields a complete Structure Score that still carries
    `STRUCTURE_SCORE_INVALID_RISK` for the independent hard asymmetry filter.
    This is the substantive behavioural change of the de-nesting.
  - `score_version` is persisted in `as_record()`; v1.1 and v1.2 records differ
    by version and neither overwrites the other.
  - Support/target cluster selection is unchanged and asserted identical across
    both versions.
  - The BTC-049 validation gate now checks float64/Decimal score parity for
    both v1.1 and v1.2 rather than v1.1 alone.

## EPIC K — Regime Engine

#### BTC-100 Implement base Regime Score
- **Description:**
  Initial formula:

  \[
  RegimeScore=
  0.35Trend+
  0.20Flow+
  0.15Macro+
  0.10OnChain+
  0.10Volatility+
  0.10Liquidity
  \]

  Until macro, on-chain, and liquidity models are implemented, use:

  \[
  RegimeScore_{core} =
  0.45Trend+
  0.25Flow+
  0.15Volatility+
  0.15Positioning
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Output records `REGIME_MODEL = CORE_MARKET_ONLY` or `REGIME_MODEL = FULL_MACRO_ONCHAIN_LIQUIDITY`
  - Missing P1 inputs are not silently filled with zero
  - Formula weights are loaded from versioned strategy config
- **Dependencies:** BTC-046 after migration parity; existing inputs remain authoritative
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.features.regime` with `RegimeScoreInput`,
    `RegimeScoreResult`, and `calculate_regime_score`.
  - Uses `REGIME_MODEL = FULL_MACRO_ONCHAIN_LIQUIDITY` when macro, on-chain,
    and liquidity inputs are present, applying versioned
    `scoring_weights.full_regime`.
  - Falls back to `REGIME_MODEL = CORE_MARKET_ONLY` while P1 inputs are missing,
    using versioned `scoring_weights.core_regime`.
  - Missing P1 inputs emit `REGIME_SCORE_P1_INPUT_MISSING` instead of being
    zero-filled; missing core inputs prevent completion and emit
    `REGIME_SCORE_CORE_INPUT_MISSING`.
  - Results persist model selection, component inputs, selected weights,
    contributions, config metadata, interpretation, reason code, completion
    state, and reason codes.

#### BTC-101 Add regime smoothing
- **Description:**
  \[
  R_t=0.7R_{t-1}+0.3R_{new}
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `RegimeSmoothingInput`, `RegimeSmoothingResult`, and
    `calculate_regime_smoothing` in `btc_predictor.features.regime`.
  - Persists `REGIME_SMOOTHED_SCORE` from
    `previous_weight * previous_smoothed_score + new_weight * new_regime_score`,
    with weights loaded from versioned `regime_smoothing` config.
  - First-run bootstrap uses the current raw regime score and records
    `REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING`.
  - Missing current regime input prevents completion and records
    `REGIME_SMOOTHING_NEW_SCORE_MISSING`.
  - Results persist inputs, weights, contributions, config metadata,
    interpretation, reason code, completion state, and reason codes.

#### BTC-102 Implement regime classification
- **Description:**
  ```text
  80–100 Strong Bull
  65–80  Bull
  55–65  Mild Bull
  45–55  Neutral
  35–45  Mild Bear
  20–35  Bear
  0–20   Strong Bear
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added `RegimeClassificationResult` and `calculate_regime_classification`
    in `btc_predictor.features.regime`.
  - Persists `REGIME_CLASSIFICATION` using the versioned `regime_thresholds`
    configuration.
  - Uses lower-bound inclusive buckets: `80` is `STRONG_BULL`, `65` is `BULL`,
    `55` is `MILD_BULL`, `45` is `NEUTRAL`, `35` is `MILD_BEAR`, `20` is
    `BEAR`, and scores below `20` are `STRONG_BEAR`.
  - Missing score input prevents completion and records
    `REGIME_CLASSIFICATION_SCORE_MISSING`.
  - Results persist score, selected regime, thresholds, config metadata,
    reason code, completion state, and reason codes.

## EPIC L — Setup Detector

#### BTC-110 Implement Bull Trend Continuation setup
- **Description:**
  Hard filters:

  ```text
  Regime >= 65
  Trend >= 70
  Flow >= 55
  Positioning >= 60
  Structure >= 70
  No STRESS
  No severe CROWDING
  R/R >= 2
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.features.setup` with `BullTrendContinuationInput`,
    `BullTrendContinuationResult`, and `detect_bull_trend_continuation`.
  - Persists `SETUP_BULL_TREND_CONTINUATION` using the versioned
    `setup_requirements.bull_trend_continuation` hard filters.
  - Accepts passing boundary values for Regime `65`, Trend `70`, Flow `55`,
    Positioning `60`, Structure `70`, and R/R `2`.
  - Missing inputs prevent completion with
    `BULL_TREND_CONTINUATION_INPUT_MISSING`.
  - Failed filters persist specific reason codes for low component scores,
    active STRESS, severe CROWDING, or insufficient R/R.
  - Results persist inputs, requirements, config metadata, setup label,
    detected state, reason code, completion state, and reason codes.

#### BTC-111 Implement Bullish Reset setup
- **Description:**
  Detect:

  - intact broader bull regime
  - meaningful correction
  - funding reset
  - OI deleveraging
  - strong support cluster
  - improving flow
  - improving structure

  Initial deterministic thresholds:

  ```text
  RegimeScore >= 55
  TrendScore >= 55
  CorrectionFromLocalHigh between 8% and 25%
  FundingHealth improving over 7 trading days
  OIHealth improving or stable over 7 trading days
  FlowAccel improving over 5 trading days
  StructureScore >= 70
  Entry trigger confirmed
  Entry Conviction >= 80
  Initial R/R >= 2
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `BullishResetInput`, `BullishResetResult`, and
    `detect_bullish_reset` in `btc_predictor.features.setup`.
  - Persists `SETUP_BULLISH_RESET` using the versioned
    `setup_requirements.bullish_reset` filters.
  - Evaluates intact bull regime, trend support, correction band, funding
    health improvement, OI health stability/improvement, FlowAccel improvement,
    strong Structure Score, entry trigger confirmation, Entry Conviction, and
    initial R/R.
  - Histories are ordered oldest-to-newest; lookback checks compare the latest
    value with the value N observations back. FundingHealth and FlowAccel must
    be strictly higher; OIHealth may be equal or higher.
  - Missing scalar inputs prevent completion with `BULLISH_RESET_INPUT_MISSING`;
    short or unavailable history prevents completion with the relevant
    `*_HISTORY_INSUFFICIENT` reason.
  - Failed filters persist specific reason codes for low scores, shallow/deep
    correction, deteriorating health, missing entry confirmation, weak Entry
    Conviction, or insufficient R/R.
  - Results persist inputs, requirements, comparison deltas, config metadata,
    setup label, detected state, reason code, completion state, and reason
    codes.

#### BTC-112 Implement Capitulation Reversal setup
- **Description:**
  Require confirmation after capitulation.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `CapitulationReversalInput`, `CapitulationReversalResult`, and
    `detect_capitulation_reversal` in `btc_predictor.features.setup`.
  - Persists `SETUP_CAPITULATION_REVERSAL` and consumes an upstream
    `capitulation_flagged` input rather than implementing BTC-114 early.
  - Added versioned `setup_requirements.capitulation_reversal` config requiring
    a capitulation flag, confirmation trigger, confirmation after capitulation,
    confirmation within 14 days, Structure Score >= 60, Entry Conviction >= 80,
    and initial R/R >= 2.
  - Inputs include UTC capitulation and confirmation timestamps; results persist
    confirmation lag in days.
  - Missing inputs prevent completion with
    `CAPITULATION_REVERSAL_INPUT_MISSING`.
  - Failed filters persist specific reason codes for inactive capitulation,
    missing confirmation, confirmation before capitulation, stale confirmation,
    weak Structure, weak Entry Conviction, or insufficient R/R.
  - Results persist inputs, requirements, confirmation lag, config metadata,
    setup label, detected state, reason code, completion state, and reason
    codes.

#### BTC-113 Implement Bearish Distribution setup
- **Description:**
  Use stricter short requirements.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `BEARISH_DISTRIBUTION` / `SETUP_BEARISH_DISTRIBUTION` with
    `BearishDistributionInput`, `BearishDistributionResult`, and
    `detect_bearish_distribution` in `btc_predictor.features.setup`.
  - Added versioned `setup_requirements.bearish_distribution` config for
    stricter short filters: Regime <= 45, Trend <= 45, Flow <= 45,
    Positioning <= 45, Structure <= 50, Entry Conviction >= 85, initial R/R >=
    2.5, active distribution flag, confirmed short trigger, and no STRESS.
  - Missing inputs prevent completion with
    `BEARISH_DISTRIBUTION_INPUT_MISSING`.
  - Failed filters persist specific reason codes for scores above bearish
    ceilings, weak Entry Conviction, insufficient R/R, inactive distribution,
    missing short trigger, or active STRESS.
  - Results persist inputs, requirements, config metadata, setup label,
    detected state, reason code, completion state, and reason codes.

#### BTC-114 Implement CAPITULATION flag
- **Description:**
  Complete the ticket scope for implement capitulation flag.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `CAPITULATION` / `calculate_capitulation_flag` in
    `btc_predictor.features.volatility`.
  - Added versioned `[volatility_flags.capitulation]` config with startup
    validation for range percentile, downside return, liquidation percentile,
    volatility percentile, and funding z-score thresholds.
  - The flag triggers on an explicit systemic shock, or on a severe downside
    return confirmed by at least one panic component: extreme range,
    liquidation cascade, volatility spike, or negative funding flush.
  - Missing inputs are reported with `CAPITULATION_INPUT_MISSING` instead of
    being silently treated as normal market conditions.
  - A severe downside move without confirmation records
    `CAPITULATION_CONFIRMATION_MISSING`.
  - Results persist inputs, thresholds, config metadata, flag state, effects,
    completion state, and reason codes.

#### BTC-115 Implement EUPHORIA flag
- **Description:**
  Complete the ticket scope for implement euphoria flag.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Historical/completed; no remaining execution dependency.
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `EUPHORIA` / `calculate_euphoria_flag` in
    `btc_predictor.features.volatility`.
  - Added versioned `[volatility_flags.euphoria]` config with startup
    validation for range percentile, upside return, funding z-score, basis
    z-score, OI intensity percentile, and volatility percentile thresholds.
  - The flag triggers on an explicit systemic euphoria input, or on a large
    upside return confirmed by at least one overheating component: extreme
    range, overheated funding, overheated basis, extreme OI intensity, or
    volatility spike.
  - Missing inputs are reported with `EUPHORIA_INPUT_MISSING` instead of being
    silently treated as normal market conditions.
  - A large upside move without confirmation records
    `EUPHORIA_CONFIRMATION_MISSING`.
  - Results persist inputs, thresholds, config metadata, flag state, effects,
    completion state, and reason codes.

## EPIC M — Entry Trigger Engine

#### BTC-120 Implement reclaim trigger
- **Description:**
  Complete the ticket scope for implement reclaim trigger.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-092
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `evaluate_reclaim_trigger` in `btc_predictor.signals.reclaim` as the
    point-in-time confirmation step after a BTC-092 reclaim level is detected.
  - The first configured number of closed follow-up bars must hold the reclaimed
    level and close above it; a failed first window is not rescued by later bars.
  - Confirmation-bar count, hold buffer, and close buffer are loaded from the
    versioned `[entry_triggers.reclaim]` strategy configuration and validated at
    startup.
  - Results persist the complete BTC-092 source record, confirmation-bar prices
    and timestamps, calculated thresholds, strategy metadata, completion state,
    detection time, and stable reason codes.
  - Bars are filtered by series identity, bar-close time, ingestion time, and
    `as_of`; focused tests cover pending data, strict boundaries, failed holds,
    deterministic ordering, future-data appends, and the BTC-092 handoff.

#### BTC-121 Implement breakout + retest trigger
- **Description:**
  Complete the ticket scope for implement breakout + retest trigger.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-092, BTC-045
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `evaluate_breakout_retest_trigger` in
    `btc_predictor.signals.breakout_retest` as the entry-confirmation step after
    a BTC-092 breakout level is detected.
  - The state machine searches a bounded post-breakout window for a pullback into
    an ATR-normalized retest zone, requires former resistance to hold as support,
    and then requires a later close above the retest high plus configured buffer.
  - ATR distance uses the BTC-045 quantitative primitive and freezes an ATR value
    available by breakout detection so later volatility cannot rewrite the setup.
  - Retest/continuation windows, retest distance, tolerated support breach, and
    continuation buffer are startup-validated under
    `[entry_triggers.breakout_retest]`.
  - Results persist the BTC-092 source, ATR provenance, thresholds, all evaluated
    bars, retest and confirmation timestamps, config metadata, completion state,
    and stable pending/failure/success reason codes.
  - Focused tests cover missing ATR, unavailable bars, bounded expiry, failed
    support, strict continuation boundaries, future-data appends, deterministic
    ordering, and end-to-end BTC-092 integration.

#### BTC-122 Implement higher-low confirmation trigger
- **Description:**
  Complete the ticket scope for implement higher-low confirmation trigger.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-090
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `evaluate_higher_low_trigger` in
    `btc_predictor.signals.higher_low`, anchored to a confirmed BTC-090 weekly
    swing low.
  - The weekly source low is linked to the last matching canonical daily low in
    its UTC source week. The daily sequence then requires a confirmed bounce
    pivot, a confirmed pullback low strictly above the source threshold, and a
    later strict close above the pivot threshold.
  - Bounce and pullback extrema use independent past-only left/right windows;
    pattern and pivot-break searches are bounded so pending and expired states
    are explicit.
  - Historical daily structure can predate weekly swing confirmation, but the
    actionable trigger `detected_at` can never precede BTC-090 `detected_at`.
  - Window lengths, search limits, higher-low buffer, and pivot-break buffer are
    startup-validated under `[entry_triggers.higher_low]`.
  - Results persist the BTC-090 source, matching daily anchor, evaluated bars,
    pivot and higher-low confirmation times, thresholds, config metadata,
    completion state, and stable reason codes.
  - Focused tests cover delayed source knowledge, missing anchors, bounded stage
    expiry, strict thresholds, invalidation, unavailable data, deterministic
    future appends, and end-to-end BTC-090 integration.

#### BTC-123 Implement no-chase filter
- **Description:**
  If price moves materially outside intended entry zone:

  ```text
  NO TRADE
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-045, BTC-095
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `apply_no_chase_filter` in `btc_predictor.signals.no_chase` as a hard
    entry veto over BTC-095 `LevelCluster` records.
  - Long entries measure only price above a support zone's upper boundary;
    short entries mirror the rule below a resistance zone's lower boundary.
    Prices inside or on the non-chasing side of a zone have zero chase distance.
  - The default mode uses BTC-045 ATR-normalized distance with a `0.50 ATR`
    threshold. A versioned fractional compatibility mode uses distance divided
    by current entry price with a default `2%` threshold.
  - Exact-threshold distances pass. Distances strictly above the active limit
    persist `NO_CHASE_VIOLATION` and the `NO_TRADE` effect.
  - Chased prices missing required ATR provenance fail closed with
    `NO_CHASE_ATR_MISSING`, while prices still inside the entry zone do not
    require ATR.
  - Results persist the complete cluster, current-price and ATR availability,
    directional boundary, raw and normalized distances, both configured limits,
    config metadata, completion/block state, effects, and stable reason codes.
  - Focused tests cover long/short symmetry, exact boundaries, missing ATR,
    fractional compatibility, point-in-time availability, determinism, and
    direct BTC-095 cluster integration.

## EPIC N — Scoring Engine

#### BTC-129 Audit factor overlap and lock v1.2 de-nested scoring contracts
- **Description:**
  Establish an explicit dependency graph for Phase 1 scores before Entry
  Conviction and lifecycle scoring are implemented.

  v1.2 required contracts:

  ```text
  Regime
      context / setup gate
      NOT an Entry Conviction component
      NOT a Hold Score component

  Entry Conviction
      Trend
      Flow
      Positioning
      Volatility
      Structure

  Structure Score
      LevelStrength
      EntryLocation
      R/R is separate
      Confluence is not repeated outside LevelStrength

  Hold Score
      Trend
      Flow
      Positioning
      Structure
      MomentumPersistence
      Regime is separate context / invalidation logic

  Add Score
      NewStructure
      Flow
      Positioning
      Momentum
      RiskImprovement
      Hold Score is not nested
  ```

  Produce an analytical effective-weight report comparing the retired nested
  v1.1 architecture with v1.2.

- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Score dependency graph is documented and testable
  - Mechanical nested overlap from Regime -> Entry/Hold is absent
  - Mechanical nested overlap from Hold -> Add is absent
  - R/R is not a Structure Score contribution
  - Confluence is not counted twice in Structure
  - v1.1 analytical effective Entry weights are reported for benchmark comparison
  - v1.2 direct weights and their sums are reported exactly
  - Config validation rejects prohibited nested component definitions where practical
  - Natural empirical correlation is explicitly distinguished from mechanical double-counting
  - Entry/Hold/Add thresholds are marked provisional pending BTC-185
  - Strategy/config version is bumped for the intentional behavior change
- **Dependencies:** BTC-046, BTC-098, BTC-100
- **Priority:** P0
- **Complexity:** M
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/features/scoring_contracts.py`: a declarative,
    testable score dependency graph with the v1.2 weights, node roles
    (COMPOSITE / FACTOR / CONTEXT_GATE / INDEPENDENT_FILTER / DIAGNOSTIC), and
    an explicit prohibited-nesting table.
  - `audit_factor_overlap()` expands a composite into every weighted route to a
    leaf factor and reports any leaf reachable by more than one path. All three
    v1.2 composites audit clean; all three v1.1 composites do not.
  - The audit is explicitly **structural only**. `MECHANICAL_VS_EMPIRICAL_NOTE`
    records that natural empirical correlation between distinct components is
    expected and is not treated as double-counting; a test asserts two
    separately declared correlated factors still audit clean.
  - Analytical effective-weight report committed to
    `research_artifacts/btc129_scoring_contracts/`. Headline v1.1 leakage for
    Entry Conviction: Trend declared 0.20 but effective **0.29** (0.20 direct +
    0.20 x 0.45 through Regime); Flow 0.20 -> 0.25; Positioning 0.15 -> 0.18;
    Volatility 0.10 -> 0.13. Hold: Trend 0.20 -> 0.3125. Add: Trend leaks in at
    0.0625 purely through the nested Hold Score.
  - **Config was still v1.1 and is now migrated.** `default.toml` had
    `entry_conviction.regime = 0.20`, `hold_score.regime = 0.25`,
    `add_score.hold_score = 0.20`, and the retired Structure `rr_quality` /
    `confluence`. All are replaced with the v1.2 contracts.
  - Config validation rejects the prohibited nested components by name with a
    rationale, so a v1.1 config fails fast rather than silently double-counting.
    A test asserts the config guard and the analytical contract table cannot
    drift apart.
  - Entry/Hold/Add/Structure component key sets are pinned to their named v1.2
    scoring contracts. Changing membership requires a new scoring-contract
    version and config version; prohibited retired nesting receives a specific
    architectural validation error before generic component-set validation.
  - Strategy/config version bumped for the intentional behaviour change:
    `strategy_config_v1` -> `strategy_config_v2`, `swing_v1.0` -> `swing_v1.2`.
  - Weights and Entry/Hold/Add thresholds are marked
    `PROVISIONAL_PENDING_BTC_185`.
  - **EPIC S2 integration review:** `expand_factor_paths()` multiplied the
    declared graph weights in the caller's ambient decimal context, so the
    analytical effective-weight decomposition BTC-189 persists verbatim and
    BTC-193 replays could differ between the producing and the restoring
    process. The path products, the per-leaf totals, and the declared totals
    are now resolved in an explicit 60-digit context. Every reported weight
    is already exact at any precision at or above 20, so no value changed.

#### BTC-130 Implement Entry Conviction
- **Description:**
  v1.2 de-nested formula:

  \[
  EntryConviction =
  0.25Trend
  +0.25Flow
  +0.1875Positioning
  +0.125Volatility
  +0.1875Structure
  \]

  Regime remains a setup/context gate and is not an Entry Conviction component.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Exact v1.2 weights are loaded from versioned strategy config
  - Regime is absent from Entry Conviction weighted inputs
  - Component contributions sum to the final score within numerical tolerance
  - Batch and single-row scoring agree
  - Missing inputs are surfaced rather than zero-filled
  - Output is deterministic, explainable, and reproducible
  - Persisted record identifies v1.2 scoring/config version
- **Dependencies:** BTC-046, BTC-084, BTC-098, BTC-129
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.features.entry` with typed single-observation and
    float64 batch APIs over the exact five-component v1.2 contract.
  - Both APIs require a validated `StrategyConfig`; weights and persisted
    config identity therefore come from the same versioned parameter set.
  - Single results persist `ENTRY_CONVICTION_V1_2`, parameter status, direct
    inputs, weights, per-component contributions, missing components, reason
    codes, and full config metadata. Regime has no weighted input route.
  - Batch scoring delegates to BTC-046, retains NaN masks without zero-fill,
    and is parity-tested against repeated single-observation calculations.
  - Entry action bands remain owned by BTC-131 and are not inferred here.

#### BTC-131 Implement entry action thresholds
- **Description:**
  ```text
  <70     IGNORE
  70–79   WATCH
  80–84   VALID
  85–89   STRONG
  90+     EXCEPTIONAL
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added a configuration-driven `ENTRY_ACTION_CLASSIFICATION_V1` classifier
    over the persisted BTC-130 Entry Conviction score.
  - Exact threshold boundaries use the centralized quantitative decision
    tolerance policy and are loaded from `strategy.entry_thresholds`.
  - Results persist the source score/version, classification version, complete
    threshold contract, configuration identity, action reason code, and any
    incomplete-state reason codes.
  - Missing scores are surfaced as incomplete with
    `ENTRY_ACTION_SCORE_MISSING`; they are never interpreted as zero.
  - Short-entry requirements and hard vetoes remain separate policy layers;
    BTC-132 is unchanged.

#### BTC-132 Implement hard-veto engine
- **Description:**
  Veto examples:

  - data quality fail
  - no valid structural stop
  - poor R/R
  - stress
  - severe crowding
  - no-chase violation
  - unsupported setup
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-045 where distance/no-chase metrics are used
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added the versioned `HARD_VETO_V1` policy under
    `btc_predictor.signals.hard_veto` for new-trade authorization.
  - Evaluates data quality, structural-stop validity, independent R/R,
    configured stress blocking, severe crowding, no-chase state, and setup
    support in a deterministic order.
  - Required inputs fail closed: unavailable state produces `NO_TRADE`, an
    explicit `HARD_VETO_INPUT_MISSING` reason, and persisted missing-input IDs.
  - Stress blocks new trades only when the versioned
    `volatility_flags.stress.block_new_trades` policy is enabled. Ordinary
    crowding remains a penalty; the severe-crowding state is the veto input.
  - Results persist the policy version, resolved inputs, source reason codes,
    supported setups, stress policy, config identity, effects, completion
    state, and every active veto reason.
  - Entry Conviction is intentionally absent from the veto contract, so a
    high score cannot override a hard veto. BTC-133 remains unchanged.

#### BTC-133 Implement reason-code engine
- **Description:**
  Example reason codes:

  ```text
  TREND_12W_POSITIVE
  ETF_FLOW_ACCEL_POSITIVE
  FUNDING_RESET
  OI_DELEVERAGED
  WEEKLY_SUPPORT_CLUSTER
  RECLAIM_CONFIRMED
  RISK_REWARD_VALID
  CROWDING_WARNING
  MACRO_WEAK
  ```

  Every signal must explain itself.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-131, BTC-132
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `REASON_CODE_ENGINE_V1` to aggregate BTC-130 Entry Conviction,
    BTC-131 entry action, BTC-132 hard-veto output, and domain-owned signal
    evidence into one recommendation explanation.
  - Validates that all three required source results use the supplied strategy
    configuration and that the classified entry score matches the score being
    explained.
  - Reasons are validated against the existing database field limits,
    deduplicated by source and code, and ranked deterministically by severity,
    source, and stable code order. Contradictory duplicates fail fast.
  - Added canonical definitions for the nine rulebook examples while keeping
    numerical interpretation in the originating feature modules.
  - Persists engine/source versions, source completion state, configuration
    identity, entry action, veto state, ranked details, and flat reason codes.
  - Produces rows directly compatible with
    `signals.recommendation_reason_codes` and preserves upstream hard-veto
    evidence with its source component.

## EPIC O — Risk Engine

#### BTC-140 Implement structural invalidation selection
- **Description:**
  Select best invalidation level based on active setup and nearby structure.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-045, BTC-047, BTC-097
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/risk/invalidation.py` with
    `select_structural_invalidation()`, policy version
    `STRUCTURAL_INVALIDATION_V1`.
  - Scope is the invalidation **level only**. The volatility buffer (BTC-141)
    and the resulting stop (BTC-142) are not computed here; rulebook 16.1
    composes them as `Stop = StructuralInvalidation -/+ VolatilityBuffer`.
  - Selection is setup-specific via `SETUP_INVALIDATION_POLICY`. Bull trend
    continuation, bullish reset and bearish distribution take the nearest
    qualifying zone; capitulation reversal takes the farthest still-qualifying
    zone, matching the rulebook's wide Stage 1 thesis stop, because a washout
    buy expects nearby structure to be probed.
  - Stops are zone-based rather than line-based (rulebook 16.2), so the
    invalidation price is the far edge of the selected zone: `lower_bound` for
    a long, `upper_bound` for a short, never the centre.
  - Eligibility filters: correct side of entry, within a maximum distance
    fraction, and meeting minimum cluster confluence and member count.
    Proximity alone cannot win, so a weak near zone defers to a stronger
    farther one.
  - Point-in-time safe: a cluster whose `detected_at` is after `as_of` is
    rejected with `STRUCTURAL_INVALIDATION_NOT_YET_DETECTED`. Detection exactly
    at `as_of` is usable.
  - Deterministic: candidates are ordered by distance then `cluster_id`, so
    selection is independent of input ordering and ties resolve stably.
  - Every considered zone is persisted in `candidates` with an explicit
    eligible/rejection verdict, so any selection is reconstructable from the
    record.
  - An optional ATR is accepted and reported as ATR-normalized distance for
    diagnostics only; it never influences selection, keeping BTC-141 free to
    own buffer sizing.
  - Distance and confluence thresholds are marked
    `PROVISIONAL_RESEARCH_CALIBRATABLE` pending BTC-185.
  - EPIC O integration review: the record now persists `as_of`, so a stored
    selection can be re-checked against the availability rule it was made
    under; `_cluster_records` now unwraps a BTC-097 `LevelClusterResult`
    object, which previously failed with a misleading `zone_type` error while
    its `as_record()` mapping worked; and non-finite inputs are refused as
    named domain errors instead of raising `decimal.InvalidOperation`.

#### BTC-141 Implement volatility buffer
- **Description:**
  Initial:

  \[
  Buffer=\max(0.3ATR_{20},LevelNoiseEstimate)
  \]

  Test:

  ```text
  0.25 ATR
  0.50 ATR
  0.75 ATR
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-043, BTC-045, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/buffer.py` with
    `calculate_volatility_buffer()`, policy version `VOLATILITY_BUFFER_V1`,
    implementing `max(0.3 * ATR_20, LevelNoiseEstimate)`.
  - Scope is the buffer distance only; applying it to an invalidation level to
    reach a stop is BTC-142.
  - **Specification gap resolved:** `LevelNoiseEstimate` is named once in the
    rulebook and never defined. The approved Phase-1 interpretation is
    `LEVEL_NOISE_ESTIMATE_V1` =
    `0.5 * (zone_upper_bound - zone_lower_bound)`, status
    `PROVISIONAL_RESEARCH_CALIBRATABLE` so BTC-185 may challenge it while
    BTC-142 has one deterministic reading.
  - **Canonical strategy path:** `volatility_buffer_for_invalidation()` takes a
    BTC-140 selection and derives the noise term from the selected zone, so
    advisory, paper trading and backtesting cannot invent competing
    LevelNoiseEstimate definitions. The derivation exists in one place.
  - **Missing-noise semantics are differentiated.** A bounded zone that reaches
    the buffer without a derived noise term is an integration defect and yields
    an incomplete buffer with `VOLATILITY_BUFFER_LEVEL_NOISE_NOT_DERIVED`,
    never a silent ATR-only degradation. ATR-only is used only when structure
    genuinely has no usable zone width, recorded as
    `level_noise_source = UNAVAILABLE`.
  - **ATR identity is explicit.** `atr_window` is persisted alongside
    `atr_multiplier`, defaulting to 20 per rulebook 16.1, so an unlabeled ATR
    value can never later be assumed to be ATR20. The 14-day window used by the
    price-source research modules is deliberately left unharmonized; it is
    recorded as a different identity and does not alter strategy semantics.
  - `volatility_buffer_grid()` evaluates the rulebook's declared 0.25 / 0.50 /
    0.75 ATR robustness grid. It reports the sweep and deliberately does not
    select a winner; calibration belongs to BTC-185. Parameters are marked
    `PROVISIONAL_RESEARCH_CALIBRATABLE`.
  - A missing ATR yields an incomplete buffer rather than zero, so a stop can
    never be placed on a silently absent volatility term. A missing level noise
    estimate is permitted and the maximum degenerates to the ATR term.
  - `binding_term` records which of the two terms governed, and both terms stay
    persisted, so a buffer is reconstructable rather than just its winner.
  - `atr_from_daily_bars()` returns `None` during warm-up rather than a
    partial-window value.
  - EPIC O integration review: `atr_from_daily_bars()` now takes canonical 1d
    `OhlcvBar`s and delegates to the BTC-041 bar boundary
    (`btc_predictor.features.rolling.average_true_range`) instead of the raw
    BTC-043 float primitive. Only a bar carries the timestamp that decides
    whether the preceding element is the preceding session, so the previous
    sequence-based bridge read a provider outage as an ordinary session and
    labelled the result `atr_window=20` when the window covered more sessions
    than that. A window spanning an absent session is now `None`, which makes
    the buffer, and therefore the stop, incomplete. A non-daily series is
    refused rather than relabelled.
  - EPIC O integration review: `volatility_buffer_for_invalidation()` no longer
    turns a *refused* BTC-140 selection into a complete ATR-only buffer. A
    BTC-140 result either selected a bounded zone or refused, so a refusal was
    being reported as `level_noise_source = UNAVAILABLE`, the code reserved for
    structure that genuinely has no width. It now yields an incomplete buffer
    with `VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE`, preserving the upstream
    cause -- including a look-ahead rejection -- for consumers such as BTC-156
    that never see BTC-140.
  - The module's `0.30` / `20` defaults are pinned by test against the
    versioned `stop_buffers` config. They are module defaults, not a run's
    parameters: a run executing under a config that overrides them must pass
    them through. Reading `stop_buffers` directly, as BTC-144 reads
    `risk.schedule`, remains open; `stop_buffers.minimum_level_noise_multiplier`
    is currently consumed nowhere.

#### BTC-142 Implement initial stop
- **Description:**
  For longs:

  \[
  Stop=Invalidation-Buffer
  \]

  For shorts:

  \[
  Stop=Invalidation+Buffer
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-140, BTC-141, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/stop.py` with `calculate_initial_stop()`, policy
    version `INITIAL_STOP_V1`, implementing
    `long: Invalidation - Buffer` and `short: Invalidation + Buffer`.
  - `initial_stop_for_setup()` is the canonical path composing a BTC-140
    selection with a BTC-141 buffer. Direction, invalidation level and entry
    price are all taken from the BTC-140 result, so the trade side cannot be
    restated inconsistently downstream. It accepts result objects or their
    persisted records.
  - Upstream incompleteness propagates: an incomplete invalidation or buffer
    yields no stop, reported as `INITIAL_STOP_INVALIDATION_INCOMPLETE` and/or
    `INITIAL_STOP_BUFFER_INCOMPLETE`, and both are reported together when both
    fail.
  - Two guards beyond the bare formula: a stop driven to or below zero by a wide
    buffer is rejected (`INITIAL_STOP_NON_POSITIVE`), and when an entry price is
    supplied a long stop must sit below entry and a short stop above it
    (`INITIAL_STOP_WRONG_SIDE_OF_ENTRY`).
  - Owns the stop's own geometry: `stop_distance` and
    `stop_distance_fraction` are derived once here because BTC-145 consumes the
    latter as `StopDistance%`. Reward/risk (BTC-143), the risk budget (BTC-144)
    and sizing (BTC-145) remain out of scope, as does trailing behaviour.
  - The record carries both inputs alongside the output, so a stop is
    re-derivable from its own persisted row.

#### BTC-143 Implement R/R filter
- **Description:**
  Minimum:

  \[
  R/R \ge 2
  \]

  For Phase 1, measure potential reward to the nearest credible upside structural
  reference, selected in this order:

  1. Nearest major weekly/monthly resistance cluster
  2. Prior local swing high
  3. Prior range high
  4. Conservative measured move from the active setup
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - If no credible structural reward reference exists, the R/R filter fails
  - Selected reward reference is persisted with the recommendation
  - R/R calculation is reproducible from stored levels and entry/stop values
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/reward.py`, policy version
    `REWARD_RISK_FILTER_V1`, with `select_reward_reference()` and
    `evaluate_reward_risk()`.
  - Reference selection follows the rulebook order strictly: a nearer
    lower-tier reference never overrides a higher tier. Within a tier the
    nearest credible reference wins. Priority 1 requires a *major* cluster, so
    a daily cluster is skipped in favour of a prior swing high.
  - Reward is measured to the near edge of a resistance zone, the first price
    at which the level starts to matter, mirroring BTC-140's far-edge rule for
    invalidation.
  - **No credible reference fails the filter.** Absence of structure is never a
    pass and never neutral: `REWARD_RISK_NO_REWARD_REFERENCE`, `passes=False`.
    Inverted geometry (a reference behind entry, or a stop on the wrong side)
    fails as `REWARD_RISK_INVALID_RISK` rather than producing a negative ratio.
  - `reward_risk_for_stop()` is the canonical path, taking entry, stop and
    direction from the BTC-142 result so trade geometry cannot be restated.
  - The record persists the selected reference (type, priority, price, source,
    timeframe) plus every rejected alternative, and R/R is reproducible from the
    stored entry, stop and reference price alone.
  - Short setups are supported: reward is measured downward to support.
  - The ratio is computed in exact `Decimal` for the hard threshold comparison,
    with a test pinning it against the BTC-047 `reward_risk_ratio` float64
    kernel so the two cannot drift.
  - The `2.5`-`3.0` preferred band is reported as a reason code without
    changing the pass/fail verdict. Thresholds are provisional pending BTC-185.
  - EPIC O integration review closed a look-ahead defect. `as_of` was optional
    and defaulted to no availability filtering at all, so the canonical path
    passed the hard gate on a resistance cluster detected after the decision
    time -- while BTC-140, selecting from the same cluster family, required
    `as_of`. `as_of` is now required on `select_reward_reference()` and
    `reward_risk_for_stop()`, a reference carrying no `detected_at` is not
    credible (rulebook 3A.2 is not satisfied by an optimistic assumption), and
    references refused for availability stay in `considered_references` under
    `REWARD_RISK_REFERENCE_NOT_YET_AVAILABLE`. The record now persists `as_of`.
  - EPIC O integration review: the hard minimum had two owners. This module's
    `DEFAULT_MINIMUM_REWARD_RISK = 2` disagreed with the versioned
    `setup_requirements.bearish_distribution.minimum_rr = 2.5` that BTC-113
    enforces, so a short at R/R 2.1 passed here and failed there.
    `minimum_reward_risk_from_config()` resolves the per-setup minimum from the
    versioned config, and `reward_risk_for_stop(setup=...)` uses it. With no
    setup named the rulebook 15 baseline of 2 still applies.
  - **Interpretation recorded:** rulebook 15's `RiskToInvalidation` admits two
    readings. `REWARD_RISK_FILTER_V1` measures risk to the BTC-142 **stop**,
    not to the bare BTC-140 invalidation level, because rulebook 16.2 makes the
    stop the level representing thesis invalidation and rulebook 17 measures
    initial risk at the stop. It is also the more conservative reading.
    Changing it loosens a hard gate and requires a new policy version.

#### BTC-144 Implement conviction-based risk budget
- **Description:**
  Initial schedule:

  ```text
  80–84  0.35% NAV
  85–89  0.50% NAV
  90+    0.60% NAV
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/budget.py` with `calculate_risk_budget()`, policy
    version `RISK_BUDGET_V1`.
  - **The schedule is not hardcoded.** `risk.schedule` already existed in the
    versioned strategy config carrying exactly the rulebook values
    (0.0035 / 0.005 / 0.006), so the module reads it via
    `risk_schedule_from_config()` rather than restating the table. A test pins
    the config bands to the rulebook table.
  - Bands are half-open `[min, max)`, so a conviction of exactly 85 belongs to
    the 85-89 band and adjacent bands can never both match.
  - **Below 80 there is no budget.** Rulebook 14 makes anything under 80 WATCH
    or IGNORE, so sub-threshold conviction returns
    `RISK_BUDGET_BELOW_MINIMUM_CONVICTION` with a `None` fraction rather than a
    silently reduced allocation.
  - The configured `risk.max_risk_at_stop_fraction_nav` acts as a hard ceiling;
    a schedule band above it is capped with
    `RISK_BUDGET_CAPPED_AT_MAXIMUM`. The default schedule sits below the cap,
    asserted by test.
  - An optional NAV expresses the budget in currency, which BTC-145 divides by
    the stop distance. Position sizing itself stays out of scope.
  - The record persists the selected band and the whole schedule alongside the
    result, so an assignment is reconstructable rather than merely asserted.
  - Values remain `PROVISIONAL_PENDING_BTC_185`.

#### BTC-145 Implement initial position sizing
- **Description:**
  \[
  PositionNotional=
  \frac{NAV\times RiskBudget}{StopDistance\%}
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-144, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/sizing.py` with
    `calculate_initial_position_size()`, policy version
    `INITIAL_POSITION_SIZE_V1`.
  - The arithmetic is BTC-047's `max_allowed_notional`, which already
    implements `NAV * fraction / distance` and already refuses a zero stop
    distance. This module is the Decimal-facing domain boundary over it, with a
    parity test pinning the two together.
  - **A zero stop distance is rejected, not divided by**
    (`INITIAL_POSITION_SIZE_ZERO_STOP_DISTANCE`). That case is an undefined
    position, not an unbounded one.
  - `initial_position_size_for_trade()` is the canonical path: NAV and the risk
    fraction come from the BTC-144 budget, the stop distance and entry price
    from the BTC-142 stop, so no consumer restates trade geometry.
  - A sub-threshold conviction produces no position at all, because BTC-144
    produces no budget below 80. That propagates as
    `INITIAL_POSITION_SIZE_NO_RISK_BUDGET`.
  - Leverage is always reported as `notional_fraction_nav`, since a tight stop
    can imply multi-x NAV exposure. An optional
    `maximum_notional_fraction_nav` ceiling is supported but **off by default**:
    no calibrated leverage limit exists yet, so none is invented.
  - The record stores every input to the formula, so a size is re-derivable
    from its own row, and an optional entry price also yields the position in
    units.
  - The chain invariant is asserted directly: notional multiplied by the stop
    distance equals the risk budget, whatever the stop distance.
  - EPIC O integration review corrected the module docstring: BTC-047's
    `max_allowed_notional` is *not* called. The sizing decision is taken in
    exact `Decimal` so a rounding artefact cannot move a position, and the two
    implementations are held together by a parity test rather than by
    delegation. Non-finite inputs are now refused as named domain errors.

#### BTC-146 Implement maximum risk-at-stop
- **Description:**
  Phase 1 target:

  \[
  RiskAtStop \le 0.75\%-1.00\% NAV
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/exposure.py` with `calculate_risk_at_stop()`,
    policy version `RISK_AT_STOP_V1`.
  - **Scope resolved from rulebook 19: this is an aggregate portfolio
    constraint, not a per-trade one.** Risk is summed across tranches sharing a
    single stop. A per-trade-only reading would have duplicated the ceiling
    BTC-144 already applies to the conviction budget.
  - **The convention is a versioned, persisted choice.** Rulebook 19 gives two
    forms and requires the choice be "explicit and consistent across advisory,
    paper trading, and backtesting". `FLOORED_AT_ZERO` (default, matching the
    BTC-047 kernels) lets an already-profitable tranche contribute zero
    downside; `ABSOLUTE_DISTANCE` keeps the unsigned distance. They differ
    materially and are not interchangeable, so the convention is recorded on
    every result.
  - The floored convention is what makes the rulebook's stated objective true:
    "Notional exposure can increase while total downside risk stays bounded."
    A test demonstrates exposure doubling while aggregate risk falls, and a
    companion test shows a large add still raises risk, so adding is not
    treated as automatically safe.
  - Both rulebook input forms are accepted and proven equivalent: quantity
    (`Q_i * |Entry_i - Stop|`) and notional
    (`N_i * |(Entry_i - Stop) / Entry_i|`).
  - Three-way verdict against the 0.75%-1.00% NAV band: within target, above
    target but under the ceiling (warn), or exceeding the configured
    `max_risk_at_stop_fraction_nav` (breach). The ceiling comes from the
    versioned strategy config, not a literal, and the boundary is inclusive.
  - `headroom_amount` reports remaining risk capacity for add decisions and is
    floored at zero on a breach.
  - Per-tranche contributions are persisted, so an aggregate is auditable
    rather than opaque. Parity with the BTC-047 `risk_at_stop` kernel is
    pinned by test. Thresholds are `PROVISIONAL_PENDING_BTC_185`.
  - Independent BTC-146 review hardened replay integrity: configuration
    identity and provisional parameter status are now automatic, tranche IDs
    are required and canonically ordered, duplicate IDs fail fast, raw signed
    loss distance is persisted, and records self-validate aggregate,
    contribution, shared-stop, band, and headroom invariants.
  - Risk-at-stop remains distinct from gross exposure. A bounded stop loss does
    not assert that leverage is safe; a separate exposure cap remains required.
  - EPIC O integration review: the soft target no longer makes a legitimate
    config unusable. `DEFAULT_RISK_AT_STOP_TARGET_FRACTION` (0.75% NAV) was
    validated against the configured ceiling unconditionally, so a versioned
    config setting `max_risk_at_stop_fraction_nav` below it -- a *more*
    conservative choice, which BTC-144 accepts as its budget cap -- made every
    `calculate_risk_at_stop()` call raise. The default target is now tightened
    to the configured ceiling; an explicitly supplied target above the ceiling
    is still refused.

## EPIC P — Position Lifecycle / Pyramiding

#### BTC-150 Implement paper position state machine
- **Description:**
  States:

  ```text
  WATCH
  PENDING_ENTRY
  OPEN_INITIAL
  OPEN_ADDED
  DEFENSIVE
  CLOSED
  MISSED
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047 and completed paper-portfolio persistence schema
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/state_machine.py` with
    `start_position_lifecycle()`, `apply_position_event()` and
    `replay_position_lifecycle()`, policy version
    `PAPER_POSITION_STATE_MACHINE_V1`.
  - **The seven states are finer-grained than `positions.status`**, which only
    distinguishes `open` / `closed` / `missed`. `persisted_status_for_state()`
    makes that mapping explicit instead of leaving each caller to invent one;
    `WATCH` and `PENDING_ENTRY` map to no row at all, because no position
    exists before a fill.
  - **`PENDING_ENTRY` is read as the order-lifecycle state, not a score state**
    (an entry order exists and has not filled), which is what makes `MISSED`
    its terminal under rulebook 25. Whether the miss was a no-chase violation
    or a decayed setup is a reason code, not another state.
  - **`OPEN_INITIAL` versus `OPEN_ADDED` is derived from tranche count**, never
    remembered, so the state cannot drift from the ledger. `RECOVER` out of
    `DEFENSIVE` therefore returns to whichever open state the ledger implies.
  - **`DEFENSIVE` refuses `ADD`.** That is its operative content: rulebook 20
    maps Hold Score 50-60 to "Defensive; tighten / consider trim", and rulebook
    24 gives STRESS / CROWDING / EUPHORIA the shared effect `NO ADDING`. Every
    risk-reducing action stays available, and the state is recoverable because
    Hold Score is recomputed each cycle.
  - Illegal transitions are **recorded as refused transitions with a reason
    code, not raised**. A refused add is exactly the audit trail paper trading
    needs. Malformed input still raises, matching the risk and feature layers.
  - `PERSISTED_EVENT_ACTIONS` maps every event to a value the
    `position_events.action` CHECK constraint accepts, asserted by test against
    `PAPER_ACTIONS`. `DEFEND` and `RECOVER` have no dedicated action and
    persist as `HOLD`; the state resolution lives in the transition record, so
    replaying transitions preserves `DEFENSIVE` where replaying actions alone
    would lose it.
  - Rulebook 32 rule 3, "never widen a stop after entry", is enforced here
    because it is a ledger invariant rather than a stop policy: BTC-156 decides
    where a stop goes, this module refuses to record one that moved the wrong
    way, in both directions.
  - A trim is applied **pro-rata across open tranches**, so a partial exit
    leaves the weighted average entry unchanged rather than silently re-basing
    it. Average entry is pinned to the BTC-047 `weighted_average_entry` kernel
    by test, and a closed position retains the average it closed at.
  - A trim must stay strictly partial and an exit must be full, which is what
    guarantees the invariant that an open state always holds a positive
    quantity. Entry additionally requires a structural stop, per the rulebook
    26 gate.
  - Event times must be non-decreasing; a refused event never becomes the
    point-in-time watermark, so it cannot block a legitimate later event.
  - Independent BTC-150 review made the persistence boundary executable rather
    than documentary: transition records now retain requested and applied
    quantity separately, round-trip from serialized records, and self-validate
    state, tranche, quantity, average-entry, timing, action, and reason-code
    invariants before persistence or further mutation.
  - `position_events.action` remains intentionally coarse. A versioned
    `PAPER_POSITION_TRANSITION_V1` JSON payload in the existing `notes` column
    preserves `DEFEND`, `RECOVER`, refused attempts, stop state, and reason
    identity, so database rows can reconstruct `DEFENSIVE`; action-only replay
    is explicitly rejected. Refusals use action `HOLD` with `accepted = false`
    in the authoritative payload, accurately recording no ledger mutation.
  - State-only `HOLD`, `DEFEND`, and `RECOVER` events cannot silently move a
    stop. A missed lifecycle remains quantity-free and uses its terminal time
    for both schema-required timestamps on the `status = missed` row.
  - Applying one command twice applies it twice. Event-ID idempotency and
    concurrent-writer serialization remain persistence-layer responsibilities;
    the immutable reducer does not claim duplicate-delivery protection.
  - Scope held to the ledger and its invariants. Hold Score (BTC-152), Add
    Score (BTC-153), add requirements (BTC-154), tranche sizing (BTC-155),
    trailing stops (BTC-156), trim rules (BTC-157) and exit rules (BTC-158)
    supply the decisions this machine validates and records. BTC-151 now
    attaches the no-average-down invariant directly to this lifecycle boundary;
    the remaining policy tickets stay external to the ledger reducer.
  - **EPIC P integration review:** a pro-rata trim now rescales the tranche
    ledger onto one common quantum instead of rounding each tranche
    independently. The scaled quantities are not representable in general, so
    the rounded ledger stopped summing to the position and the module's own
    "quantity must equal the tranche ledger" invariant *raised* on an ordinary
    permitted trim of a multi-tranche position -- aborting a BTC-180 run rather
    than refusing. The requested quantity remains the applied quantity, and the
    average entry moves by around 1e-26 relative at worst, fourteen orders of
    magnitude below `DECISION_COMPARISON_V1`. The same review stopped a
    refusal recorded *before* the fill from writing a `position_events` row:
    accepted pre-position transitions never wrote one, so persisting the
    refused ones skipped the arming that moved the state and made the row set
    unreplayable. Pre-fill refusals stay in the authoritative snapshot; post-fill
    refusals still persist.

#### BTC-151 Implement no-average-down rule
- **Description:**
  Hard invariant:

  ```text
  ADD prohibited if position is losing
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-150
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Added the explicit `NO_AVERAGE_DOWN_V1` policy and a side-aware losing
    position test against the current weighted average entry: a long is losing
    below average entry and a short is losing above it.
  - Every proposed `ADD` is checked at its proposed fill price inside the
    BTC-150 lifecycle guard. A refusal is atomic: tranches, quantity, weighted
    average entry, stop, and lifecycle state remain unchanged.
  - Refusals persist as schema-compatible `HOLD` events with
    `accepted = false`, the proposed price and quantity, and reason code
    `POSITION_STATE_ADD_REFUSED_AVERAGE_DOWN`; snapshot and database-event
    replay reproduce the refusal exactly.
  - Equality is breakeven and is not losing, so BTC-151 permits it. The stricter
    requirement that a position must already be profitable belongs to BTC-154.
  - Strategy startup rejects `add_thresholds.no_average_down = false`; the hard
    invariant cannot be disabled by configuration. Strategy config identity
    remains attached to lifecycle records through `config_metadata`.
  - Focused tests cover long and short positions, exact boundary behavior,
    invalid numeric inputs, profitable adds, weighted multi-tranche entry after
    trimming, atomic refusal, deterministic output, and persistence replay.

#### BTC-152 Implement Hold Score
- **Description:**
  Implement the v1.2 de-nested Hold Score:

  \[
  HoldScore =
  0.2666667Trend+
  0.2666667Flow+
  0.20Positioning+
  0.1333333Structure+
  0.1333333MomentumPersistence
  \]

  Regime remains separately available for lifecycle context and
  `REGIME_INVALIDATION`; it is not weighted again inside Hold Score.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-046, BTC-129
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor.features.hold` with typed scalar and float64 batch APIs
    over the exact five-component `HOLD_SCORE_V1_2` contract.
  - Both APIs require a validated `StrategyConfig`; the exact provisional v1.2
    weights and `config_version`, `strategy_version`, and `parameter_set_id`
    are carried into every result.
  - Regime has no field or weighted input route. It remains an independent
    lifecycle context and `REGIME_INVALIDATION` input as required by v1.2.
  - Momentum Persistence is accepted as an explicit normalized 0-100 component
    score. The Hold Score aggregator does not invent domain semantics for that
    factor, and missing evidence makes the result incomplete rather than being
    silently zero-filled.
  - Persisted scalar records contain `HOLD_SCORE_V1_2`, parameter status,
    direct inputs, exact weights, per-component contributions, missing
    components, config identity, completion state, and deterministic
    `HOLD_SCORE_COMPLETE` / `HOLD_SCORE_INPUT_MISSING` reason codes.
  - Batch scoring delegates to BTC-046, preserves NaN masks, and is parity-
    tested against scalar calculations. Tests also cover exact arithmetic,
    contribution and contract drift, invalid numeric values, future-row append
    invariance, and deterministic recomputation.
  - Hold action bands and lifecycle transitions are not inferred here; this
    ticket supplies the explainable score consumed by those later policies.

#### BTC-153 Implement Add Score
- **Description:**
  Implement the v1.2 de-nested Add Score:

  \[
  AddScore=
  0.3125NewStructure+
  0.25Flow+
  0.1875Positioning+
  0.125Momentum+
  0.125RiskImprovement
  \]

  `HoldScore` is not nested inside Add Score. Hold quality and supportive Regime
  remain separate add requirements / lifecycle context.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-046, BTC-047, BTC-129
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.features.add` with typed scalar and float64 batch APIs
    over the exact five-component `ADD_SCORE_V1_2` contract, mirroring BTC-152.
  - `HoldScore` has no field, no weight key, and no input route, so the v1.2
    de-nesting is structural rather than documented. Regime is likewise absent.
    A test asserts the component set differs from Hold's rather than merely
    omitting one key: Add replaces Structure with NewStructure and drops Trend,
    so it is an independent judgement, not a re-weighting.
  - **`RiskImprovement` is the one component whose natural unit is not a 0-100
    score.** BTC-047 reports it in absolute currency. Following the BTC-152
    precedent for Momentum Persistence, the aggregator takes an explicit
    normalized component and invents no domain semantics for it.
  - `risk_improvement_component_score()` is offered separately as a versioned
    bridge (`RISK_IMPROVEMENT_PROPORTIONAL_V1`): the share of current risk that
    the proposed stop removes, scaled to 0-100. It has no free parameter, so it
    is a mechanical unit conversion rather than a calibration. A NAV-relative
    alternative is equally defensible, which is why the choice is versioned and
    why the aggregator never applies one implicitly.
  - The bridge calls the BTC-047 kernel with `floor_at_zero=False` rather than
    restating the formula, and reports `signed_improvement` alongside the
    floored score. A worsened stop and an unchanged one both score 0; only the
    signed value separates them, which is what rulebook 18's "stop can improve"
    requirement needs from BTC-154.
  - Zero current risk yields no component rather than a perfect one: there is
    nothing to remove, so the proportion is undefined and the Add Score becomes
    incomplete instead of silently maximal.
  - Persisted records carry `ADD_SCORE_V1_2`, parameter status, direct inputs,
    exact weights, per-component contributions, missing components, config
    identity, completion state, and deterministic `ADD_SCORE_COMPLETE` /
    `ADD_SCORE_INPUT_MISSING` reason codes. Config rejects a weight set that is
    missing a component, carries an extra one such as `hold_score`, or fails to
    sum to 1.
  - The `AddScore >= 85` threshold is deliberately not implemented here. Add
    requirements, hold quality, and supportive regime are BTC-154, consistent
    with BTC-152 leaving hold action bands to its consumers.

#### BTC-154 Implement add requirements
- **Description:**
  Require:

  - position profitable
  - new structural confirmation
  - stop can improve
  - supportive regime
  - supportive flow
  - healthy positioning
  - Add Score >= 85
  - risk-at-stop within max
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-153
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/signals/add_requirements.py` with
    `evaluate_add_requirements()`, policy version `ADD_REQUIREMENTS_V1`,
    mirroring the BTC-132 fail-closed veto engine.
  - All eight requirements are conjunctive and each has its own input and its
    own reason code, so a blocked add explains every reason it was blocked
    rather than only the first. Effects are `NO_ADD`, matching rulebook 24.
  - **Fail-closed:** an unresolved input blocks rather than being assumed
    favourable, and is reported in `missing_inputs`. A lifecycle that is not
    open resolves profitability to `None`, not `False`.
  - **Two requirements are deliberately not booleans.** Add Score is compared
    against `add_thresholds.add_min` under `DECISION_COMPARISON_V1`, so the 85
    boundary is inclusive and tolerance-stable. "Stop can improve" takes the
    *signed* currency improvement from BTC-153's bridge over the BTC-047
    kernel: a floored improvement cannot distinguish an unchanged stop from a
    worsened one, and both must block. Improvement must be strict.
  - **Profitability is strict, unlike BTC-151.** `position_is_profitable_at_price`
    was added beside `position_is_losing_at_price` in the BTC-150 ledger rather
    than restating the sign convention in a second module; breakeven is neither
    losing nor profitable, so it is not the negation of its sibling. BTC-151
    permits a breakeven add, BTC-154 refuses it.
  - `add_requirements_from_results()` is the canonical path, composing a
    BTC-150 lifecycle, a BTC-153 `AddScoreResult` and `RiskImprovementComponent`,
    and a BTC-146 `RiskAtStopResult` computed on the *projected* post-add book.
    Upstream reason codes are retained as evidence on the persisted record.
  - The two optional config gates (`existing_position_must_be_profitable`,
    `stop_must_improve`) are honoured and persisted on every result, so the
    gate set a run actually used is auditable. `no_average_down` remains
    non-disableable in BTC-151.
  - The BTC-150 transition table is not duplicated: a state that forbids ADD is
    refused by the state machine. Tranche sizing is BTC-155 and the subsequent
    stop move is BTC-156.
  - Focused tests cover each requirement independently, multi-failure
    reporting, every input failing closed, the configured threshold boundary,
    strict stop improvement, disabled gates, weighted-average-entry
    profitability across two tranches, incomplete upstream results, evidence
    retention, persistence drift, and determinism.
  - **EPIC P integration review:** `add_requirements_from_results` now
    identifies each upstream result rather than duck-typing it, and refuses a
    mixed parameter set, the way BTC-157 and BTC-158 already did. A
    `HoldScoreResult` also exposes `score` and `complete`, so the canonical
    path had been authorizing pyramid adds from Hold Score -- undoing by
    composition exactly the v1.2 de-nesting BTC-153 exists to make structural,
    and persisting `HOLD_SCORE_COMPLETE` as the evidence for it. Results
    carrying a foreign `strategy_version` / `parameter_set_id` were likewise
    accepted and then recorded under the local config.
  - **Open composition limit:** rulebook 24 gives STRESS / CROWDING / EUPHORIA
    the shared effect `NO ADDING`, and BTC-150 makes `DEFENSIVE` the state that
    enforces it, but no module in EPIC P emits `DEFEND` and this gate has no
    hard-flag requirement. BTC-157 consumes the same flags for TRIM. The
    composed chain therefore permits an add while CROWDING is active. Pinned by
    `test_no_epic_module_maps_a_hard_flag_onto_the_add_gate` rather than closed
    in review: choosing the mapping is a strategy decision.

#### BTC-155 Implement tranche sizing
- **Description:**
  Initial research schedule:

  ```text
  Initial  40%
  Add #1   35%
  Add #2   25%
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/risk/tranches.py` with `calculate_tranche_size()` and
    `next_tranche_for_position()`, policy version `TRANCHE_SIZING_V1`.
  - **The percentages are shares of the final position, so they must sum to 1.**
    Rulebook 18's column is "Relative Final Position": BTC-145 sizes the whole
    position once from the risk budget and this schedule only decides how that
    single size is delivered. A schedule summing to anything else would
    silently re-size the position, so configuration rejects it at startup.
  - **The schedule must never increase.** Rulebook 18's anti-martingale
    principle is "add to winners, never to losers"; adding in growing size is
    the martingale shape the strategy exists to avoid. A growing schedule is
    rejected at startup with an explicit message rather than merely discouraged
    in prose. Equal tranches are permitted, since non-increasing is the rule.
  - **The schedule length is the add cap.** BTC-154 decides whether an add is
    permitted; this decides whether one is allocated. A fourth tranche gets
    `TRANCHE_SIZING_SCHEDULE_EXHAUSTED` and no allocation rather than an
    extrapolated one, which would size risk nothing authorized.
  - Both views are reported: `fraction_of_final` sizes the order, and
    `cumulative_fraction` plus `remaining_fraction` let the ledger be checked.
    The three stages reconstruct exactly one whole position by test.
  - `next_tranche_for_position()` is the canonical path: the stage number comes
    from the BTC-150 tranche count and the whole-position size from the BTC-145
    result, so neither the off-by-one nor the position size can be restated by
    a caller. Tranche notional is pinned to the BTC-047 `position_notional`
    kernel.
  - The schedule lives in `risk.tranche_schedule` in versioned configuration
    rather than as a module constant, and carries
    `PROVISIONAL_RESEARCH_CALIBRATABLE`, because rulebook 18 states plainly
    that these percentages are research parameters.
  - Focused tests cover each stage's exact allocation, whole-position
    reconstruction, the anti-martingale ordering, schedule exhaustion, ledger
    composition at zero, one, and two adds, incomplete upstream sizing,
    schedule validation at both the module and config layers, malformed input,
    persistence, and determinism.
  - **EPIC P integration review:** `next_tranche_for_position` no longer falls
    back to BTC-145's original entry price for a *later* tranche. The schedule
    is a share of the final **notional**, so pairing that share with a stale
    price returned a quantity worth more than the share it reported: an add at
    +30% delivered 130% of its authorized notional while `allocation.notional`
    still said 100%. A later tranche without its own fill price now yields
    `TRANCHE_SIZING_NO_ADD_PRICE` and no allocation, which BTC-163 already
    fails closed on. The first tranche still uses the price BTC-145 sized it
    at. BTC-180 always passed the execution bar's open, so no run was affected.

#### BTC-156 Implement trailing stop progression
- **Description:**
  For long:

  \[
  CandidateStop=
  NewHigherLow-Buffer
  \]

  \[
  Stop_t=
  \max(Stop_{t-1},CandidateStop)
  \]

  Hard invariant:

  ```text
  STOP MAY NEVER MOVE LOWER FOR A LONG
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-141, BTC-142, BTC-150
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/risk/trailing.py` with `calculate_trailing_stop()` and
    `trail_stop_for_position()`, policy version `TRAILING_STOP_V1`.
  - **The hard invariant follows from the ratchet rather than sitting beside
    it.** `max(Stop_t-1, Candidate)` for a long and `min(...)` for a short
    already make a loosened stop unreachable; a candidate below the standing
    stop is discarded as `TRAILING_STOP_HELD`, never recorded. The invariant is
    re-checked at the persistence boundary so a hand-built or mutated record
    cannot record a loosened stop either.
  - Comparison uses `DECISION_COMPARISON_V1`, so a candidate inside tolerance
    is not an advance and float noise cannot ratchet the stop.
  - **No structure is a hold, not a failure.** Rulebook 22 advances only when
    new confirmed structure forms and states that no daily mechanical trailing
    is required, so an absent structure price yields
    `TRAILING_STOP_NO_NEW_STRUCTURE` with the standing stop intact and the
    result still complete.
  - **The three stages are derived from the advance count, never asserted.**
    Stage 1 is the wide BTC-142 structural stop before anything advanced,
    stage 2 the first advance under a new higher low, stage 3 every advance
    after. `as_record()` rejects a stage that disagrees with its count, the way
    BTC-150 derives `OPEN_ADDED` from its tranche count.
  - `trail_stop_for_position()` is the canonical path: direction, the standing
    stop, and the advance count all come from the BTC-150 ledger, and the
    buffer accepts a BTC-141 result directly. `stop_advance_count()` counts
    accepted post-entry transitions only when the stop genuinely tightens, so
    the entry's own thesis stop, same-stop events, and refused moves count for
    nothing. An add that raises the stop counts once, per rulebook 26.
  - Two guards beyond the formula: a non-positive candidate is refused, and an
    optional `current_price` refuses a candidate price has already passed,
    which would be an immediate exit dressed up as a stop move.
  - Scope: this decides where the stop goes. BTC-150 still owns whether the
    move is recordable and refuses one that widens; tests confirm an advanced
    stop is accepted by the lifecycle and a held one is a no-op it also accepts.
  - Focused tests cover the long and short formulas, the ratchet in both
    directions, a monotonic sequence that never retreats, tolerance behaviour,
    quiet bars, incomplete buffers, both guards, stage derivation and drift,
    ledger composition, persistence, and determinism.
  - **Independent xHigh review:** the declared dependencies were corrected to
    the actual strategy path: BTC-141 owns the buffer, BTC-142 establishes the
    initial stop, and BTC-150 owns standing state and transition persistence.
    The review also made confirmed structure identity and availability time
    mandatory on the canonical path, prevents a used structure from
    retriggering after buffer changes, counts only genuine stop improvements,
    and reconstructs persisted results from their formula and provenance.
  - **EPIC P integration review:** `trail_stop_for_position` now refuses an
    `as_of` earlier than the BTC-150 watermark. The standing stop and the
    advance count are read off the ledger as it stands, so a result stamped
    before the ledger's own last accepted event claimed to have been evaluated
    on state that did not exist yet. BTC-158 already refused the same
    composition.

#### BTC-157 Implement trim rules
- **Description:**
  Based on:

  - Hold Score
  - EUPHORIA
  - CROWDING
  - Flow deterioration
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Trim signals include reason codes
  - Trim signals are distinct from full exits
  - Paper trader can simulate partial reductions once BTC-164 is complete
- **Dependencies:** BTC-047, BTC-150, BTC-152
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.signals.trim` with policy version `TRIM_RULES_V1` and
    a self-validating `TrimSignalResult` persistence contract.
  - A TRIM requires an open BTC-150 lifecycle and is triggered independently
    by the configured Hold Score trim band, active EUPHORIA, active CROWDING,
    or deteriorating Flow Score. Every active trigger receives its own stable
    reason code and simultaneous reasons are retained in deterministic order.
  - The configured Hold Score boundaries are exact: `trim_min` is inclusive
    and `defensive_min` is exclusive. A score below `exit_below` suppresses
    TRIM with `TRIM_SUPPRESSED_EXIT_BAND` and leaves full-exit ownership to
    BTC-158. At the default thresholds, 40 is TRIM and values below 40 defer to
    exit rules.
  - Phase 1 flow deterioration is the current persisted Flow Score falling
    below the prior decision's Flow Score under `DECISION_COMPARISON_V1`. No
    unconfigured lookback or decline threshold is invented; the definition is
    marked `PROVISIONAL_PENDING_BTC_185` for later robustness research.
  - Missing evidence is never silently treated as healthy. It is persisted in
    `missing_inputs` with `TRIM_INPUT_MISSING`; a known risk-reduction trigger
    can still emit a transparent incomplete signal rather than being erased by
    an unrelated missing input.
  - `trim_rules_from_results()` composes authoritative BTC-150, BTC-152,
    Flow Score, EUPHORIA, and CROWDING results, rejects mixed config identities,
    and retains every upstream reason code as source evidence.
  - The signal is explicitly partial: it emits action `TRIM` and effect
    `PARTIAL_REDUCTION`, never `EXIT`, and deliberately carries no execution
    quantity. BTC-164 owns simulated trim sizing/fills, while BTC-150 already
    refuses a TRIM quantity that would remove the full position.
  - Focused tests cover exact score boundaries, all four triggers, simultaneous
    reason ordering, no-position and exit precedence, missing inputs, numeric
    tolerance, persistence drift, real upstream-result composition, config
    provenance, and deterministic replay.

#### BTC-158 Implement exit rules
- **Description:**
  Exit reasons:

  ```text
  STRUCTURAL_STOP
  HOLD_SCORE_COLLAPSE
  REGIME_INVALIDATION
  DATA_RISK
  MANUAL_RESEARCH_OVERRIDE
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-142, BTC-150, BTC-152, BTC-156
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.signals.exit_rules` with policy version
    `EXIT_RULES_V1`, typed direct and canonical composition APIs, and exact
    record reconstruction. It emits `EXIT` / `FULL_EXIT`; it does not mutate a
    lifecycle or simulate a fill.
  - All five declared exit reasons are independent and persist in stable order:
    `STRUCTURAL_STOP`, `HOLD_SCORE_COLLAPSE`, `REGIME_INVALIDATION`,
    `DATA_RISK`, and `MANUAL_RESEARCH_OVERRIDE`. Simultaneous reasons are
    retained rather than collapsed to one headline cause.
  - Structural-stop touch uses BTC-150's authoritative direction and current
    standing stop, whether established by BTC-142 or advanced by BTC-156. Long
    exits trigger at price `<= stop`; short exits mirror at price `>= stop`,
    using `DECISION_COMPARISON_V1` at equality/tolerance boundaries.
  - Hold Score collapse is the rulebook's exact configured condition:
    `HoldScore < hold_thresholds.exit_below`. Equality remains in the trim band;
    at the default configuration, 40 does not exit and a genuine value below
    40 does.
  - The rulebook does not define numerical regime-invalidation or data-risk
    thresholds. Both are explicit audited booleans from their owning policies;
    no threshold is invented here. In particular, ordinary
    `DATA_QUALITY_FAIL` is not silently interpreted as forced liquidation.
  - Manual research override requires a persisted non-empty explanation.
    Missing unrelated evidence is surfaced without suppressing a known stop,
    data-risk, regime, Hold Score, or manual safety exit.
  - Canonical composition validates BTC-150 and BTC-152 types, config identity,
    decision time against the lifecycle watermark, and authoritative source
    evidence. Evaluation is pure and leaves execution to the paper trader.
  - Focused tests cover all trigger combinations, long/short stop geometry,
    shared tolerance, exact Hold Score boundaries, no-position precedence,
    incomplete inputs, manual audit requirements, malformed numerics,
    persistence tampering, canonical provenance, determinism, and database
    lifecycle replay.

## EPIC Q — Paper Trading Engine

#### BTC-160 Create paper trading account
- **Description:**
  Configurable:

  - starting NAV
  - fees
  - slippage
  - funding
  - available cash
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-150
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/account.py` with `open_paper_account()` and
    `ExecutionCosts`, policy versions `PAPER_ACCOUNT_V1` and
    `EXECUTION_COST_V1`.
  - **All five configurables already existed under `[backtest]`** as
    `initial_cash`, `fee_bps`, `slippage_bps` and `funding_cost_bps_per_day`,
    so they are read rather than duplicated into a paper-only block. Rulebook
    32 rule 15 requires advisory, paper trading and backtesting to share the
    same assumptions; a parallel `[paper]` fee set would let them silently
    diverge, which is the failure that rule exists to prevent. A test asserts
    the account's costs equal the configured backtest assumptions.
  - **NAV and cash are kept distinct.** BTC-144, BTC-145 and BTC-146 all size
    against NAV, and NAV is cash plus unrealized position value. Sizing against
    cash would shrink every position as soon as a trade moved into profit, so
    `nav(unrealized_pnl=...)` is explicit and a test drives a real BTC-144
    budget through it.
  - Available cash is the balance less an optional reserve, floored at zero,
    and the reserve constrains deployable cash without ever entering the risk
    denominator. A reserve larger than the account is a configuration error
    rather than a silently clamped account that would refuse every trade.
  - Costs are in basis points, stated once as `BASIS_POINT`: 10 bps is 0.10%,
    verified against an independent `notional * 0.001`. Slippage is always
    adverse -- a buy fills higher, a sell fills lower -- with no configuration
    that makes a paper fill better than the reference price.
    `round_trip_cost()` exists because a 2R target is not 2R after costs.
  - The shipped funding rate is zero and configured as zero rather than absent,
    so a later calibration is a config change with a version behind it.
  - The account is immutable: charging a fee returns a new account, so a
    rejected or replayed step cannot leave a half-applied balance. Cash is
    floored at zero with `PAPER_ACCOUNT_CASH_EXHAUSTED`, matching the
    `paper_accounts_current_cash_non_negative` CHECK.
  - `as_db_record()` maps onto the `portfolio.paper_accounts` columns and its
    status CHECK, tested against the live table definition, so no caller
    invents a mapping the constraint would reject.
  - **EPIC Q integration review.** `charge_funding()` now requires a
    `direction` and signs the carry the way BTC-165's
    `funding_event_from_rate` does: a long pays it and a short receives it.
    `ExecutionCosts.funding()` is documented as the unsigned magnitude, so the
    account is the only place a side is applied and the two funding paths in
    the epic cannot disagree about the same position. Cash exhaustion is also
    sticky now, exposed as `cash_exhausted`: flooring at zero keeps the row
    insertable under the CHECK but discards the deficit, and that fact must
    outlive the step that caused it rather than being cleared by the next fee.

#### BTC-161 Implement simulated entry execution
- **Description:**
  ### Requirements

  - Respect entry zone
  - Realistic next-bar execution
  - No perfect fill assumptions
  - Mark missed entries
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/entry_execution.py` with
    `simulate_next_bar_entry()` and `restore_simulated_entry_execution()`,
    policy version `SIMULATED_ENTRY_EXECUTION_V1`.
  - **Respect entry zone:** a bar whose range never reaches the zone is a miss.
    The boundary is inclusive -- a high exactly equal to the zone lower bound
    is a touch, a cent below it is not -- and both sides of that line are
    pinned by test.
  - **Realistic next-bar execution:** `next_eligible_bar_timestamp()` resolves
    the first canonical full-bar boundary at or after the decision, across 1h,
    1d, 1w and 1mo. A decision inside a forming bar waits for the next one, and
    the execution bar must be exactly that bar.
  - **No perfect fill assumptions:** when the bar opens outside the zone the
    reference is the nearest boundary the bar could have crossed, not the open
    and not the best price in the range; when it opens inside, the open is the
    reference. The BTC-160 cost policy then moves that reference adversely and
    charges the fee, with the slippage cost recorded separately from the fee.
  - **Mark missed entries:** a miss is terminal and carries `ENTRY_DO_NOT_CHASE`
    alongside `ENTRY_ZONE_NOT_TOUCHED`, per rulebook 25. A later bar cannot be
    supplied to fill an intent that already missed, which is enforced rather
    than left to caller discipline.
  - `as_order_record()` maps onto the `portfolio.paper_orders` columns and its
    action and status CHECKs, with a miss carrying no fill time, no fill price,
    and zero filled quantity. `restore_simulated_entry_execution()` re-simulates
    from the persisted evidence and rejects any record that does not reproduce
    exactly, so a tampered row cannot be replayed.
  - Execution-bar validation rejects impossible OHLC geometry. That check
    caught four test fixtures which had overridden open/high/low while keeping
    a default close outside the new range; the fixtures were corrected rather
    than the check relaxed.
  - **EPIC Q integration review.** The notional is now the exact Decimal
    product, pinned to the BTC-047 kernel by parity check exactly as BTC-162
    does it, instead of being rounded through float64. The float detour made
    this the one execution in the epic whose notional -- and therefore whose
    fee -- disagreed with the product BTC-165 books for the same fill; the
    golden scenarios' recorded fees, net P&L, R and ending NAV moved in their
    last digits as a result. Zone touch and reference selection also use
    `DECISION_COMPARISON_V1`, so an entry zone and a BTC-162 stop answer the
    identical "did price reach this level" question under one policy.

#### BTC-162 Implement simulated stop execution
- **Description:**
  Handle:

  - stop touch
  - gaps
  - slippage
  - partial position state
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-146, BTC-150, BTC-156, BTC-160, BTC-161
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/stop_execution.py` with
    `simulate_stop_execution()`, `stop_execution_for_position()` and
    `restore_simulated_stop_execution()`, policy version
    `SIMULATED_STOP_EXECUTION_V1`.
  - **Stop touch:** a long fills when the bar trades at or below the stop, a
    short at or above it; the boundary is inclusive and both sides are pinned
    by test. Unlike a BTC-161 entry, an untouched stop is **not** terminal --
    it stays `submitted` and still works on the next bar, so "resting" and
    "missed" are deliberately different states.
  - **Gaps are the reason this ticket exists.** The gap test is on the bar's
    *open*, not its low: a bar that opened beyond the stop never offered the
    stop price at all, so the fill reference is the open. A test pins that two
    bars trading equally far below the stop resolve differently depending only
    on where they opened.
  - **Risk and P&L are separate.** `planned_downside_risk` uses BTC-146's
    tranche-level `FLOORED_AT_ZERO` convention. `planned_gross_pnl`,
    `gross_pnl` and `net_pnl` are signed; `realized_loss` is the non-negative
    loss part of net P&L. `execution_shortfall` reports gap, slippage and fee
    deterioration from the stop-price plan without subtracting costs twice.
    Mixed protected/at-risk tranches are persisted so weighted-average P&L is
    never mistaken for tranche-level downside risk.
  - **Slippage** is adverse on the exit side -- a long exit sells and fills
    below the reference, a short exit buys and fills above -- reusing the
    BTC-160 cost policy, with fee and slippage cost reported separately.
  - **Partial position state** means a trimmed position: the stop covers the
    remaining quantity, never the size originally entered. Partial *fills* of
    the stop order itself are not modelled, because intrabar liquidity is
    unknowable from OHLCV; the stop is all-or-nothing on what remains and the
    module says so rather than inventing a fill ladder.
  - `stop_execution_for_position()` is the canonical path: direction, standing
    stop, weighted average entry, remaining tranches, quantity, configuration
    identity and the stop's installation time all come from the BTC-150
    ledger. A caller cannot restate stale stop timing or metadata.
  - The independent xHigh review corrected three execution-path defects:
    profitable BTC-156 trailing stops are valid and executable; `open == stop`
    is a normal stop-price touch rather than a gap; and touch/gap boundaries
    use `DECISION_COMPARISON_V1`. A stop placed during a bar first becomes
    eligible on the next full bar, preventing retroactive use of that bar's
    earlier high/low. Focused tests cover Stage-3 profit protection, long/short
    symmetry, mixed tranches, trim state, zero-cost and gapped fills, replay,
    tamper rejection, lifecycle closure and exact accounting reconciliation.

#### BTC-163 Implement simulated adds
- **Description:**
  Complete the ticket scope for implement simulated adds.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-154
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/add_execution.py` with
    `simulate_add_execution()`, policy version `SIMULATED_ADD_EXECUTION_V1`.
    The ticket description was a placeholder, so scope was derived from the
    BTC-154 dependency: an add is the composition
    `requirements -> allocation -> fill -> ledger event`.
  - **An add is not an entry with a different label.** An entry is triggered by
    price reaching a zone; an add is triggered by conditions BTC-154 has
    already judged. No add zone is invented, because the rulebook defines none.
    The proposal fills at the next full bar's open, moved adversely by the
    BTC-160 cost policy, which is the honest fill for a decision made after the
    previous bar closed.
  - **A refused add produces no fill and keeps the gate's own explanation**,
    rather than flattening every refusal into one opaque code. An exhausted
    BTC-155 schedule likewise produces no fill: BTC-154 decides whether an add
    is permitted, BTC-155 whether one is allocated, and both must say yes. The
    requirement gate is evaluated first, since an add that was never permitted
    was never a sizing question.
  - **The re-check at execution is the substantive part.** BTC-154 judges
    profitability at the *decision*; the fill happens on the next bar. If price
    moved against the position in between, filling anyway would average down --
    rulebook 32 rule 2, which may never be violated. The gate's own standard is
    re-applied at execution, and the position is dropped rather than filled.
  - **The re-check uses the bar's open, not the slipped fill.** My first
    implementation passed the fill price, which meant adverse slippage on a buy
    made the position read as *more* profitable and could rescue an add that
    the market had already sunk. Slippage is a cost, not a mark. A regression
    test pins the case where the slipped price sits above the average entry but
    the market open sits below it.
  - When BTC-154's stricter profitability gate is disabled by configuration,
    BTC-151's never-average-down invariant still applies at execution, so a
    losing fill is refused while a breakeven one is allowed.
  - `as_order_record()` maps onto `portfolio.paper_orders` with action `ADD`
    and status `cancelled` for a refusal -- nothing about the market prevented
    it, so it is not a miss -- while still recording the quantity that would
    have been bought. Both upstream decision records travel with the fill.

#### BTC-164 Implement simulated trims
- **Description:**
  Complete the ticket scope for implement simulated trims.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-157, BTC-160
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/trim_execution.py` with
    `simulate_trim_execution()`, policy version `SIMULATED_TRIM_EXECUTION_V1`.
    The description was a placeholder, so scope came from BTC-157: that ticket
    decides *whether* to reduce, this one decides what it costs and what it
    locks in.
  - Shares the BTC-163 shape -- conditions trigger it, so it fills at the next
    full bar's open moved adversely -- but reduces, so a long trim **sells**
    and a short trim **buys**, the opposite side to an add in the same
    direction.
  - **A trim realizes part of the position, and the figure is signed.** That is
    the point of trimming, so `realized_pnl` is computed net of the fee and
    reported with `TRIM_EXECUTION_REALIZED_PROFIT` or `..._REALIZED_LOSS`. A
    defensive trim in the 40-50 Hold band locks in a loss, and reporting that
    as profit taken would misstate the trade. A test settles the figure
    straight onto a BTC-160 account, so no second convention is invented.
  - **A trim must stay strictly partial.** A full reduction is refused with
    `TRIM_EXECUTION_NOT_PARTIAL` rather than quietly becoming an exit, which is
    BTC-158's decision with its own rules and which the BTC-150 ledger already
    rejects as a trim.
  - **The trim size has no rulebook definition.** Rulebook 20 and 23 give
    Hold-Score bands that say "trim" without saying how much, so
    `DEFAULT_TRIM_FRACTION` is an explicit placeholder carrying
    `PROVISIONAL_RESEARCH_CALIBRATABLE`, overridable per call and persisted on
    every record. It is not calibrated and does not pretend to be.
  - The BTC-157 signal is checked before the size, since a trim that was never
    signalled was never a sizing question, and a refusal keeps the signal's own
    reason codes. `as_order_record()` maps onto `portfolio.paper_orders` with
    action `TRIM` and status `cancelled` for a refusal.

#### BTC-165 Implement paper trade accounting
- **Description:**
  Calculate:

  - gross P&L
  - net P&L
  - fees
  - funding
  - R multiple
  - MFE
  - MAE
  - holding days
  - max size
  - number of adds
  - exit reason
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-016, BTC-040, BTC-047, BTC-142, BTC-150, BTC-160, BTC-161, BTC-162, BTC-163, BTC-164
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/portfolio/accounting.py` with
    `calculate_trade_accounting()`, policy version
    `PAPER_TRADE_ACCOUNTING_V1`. All eleven figures come from one walk over the
    trade's fills, so no two of them can disagree.
  - **1R is the risk planned at entry**, `initial_quantity * |entry - initial
    stop|`, fixed once and versioned as `INITIAL_PLANNED_RISK_V1`. Measuring
    against the trailed stop would inflate R as the stop ratchets, letting a
    trade report a large R having never risked that much; adds raise P&L
    without retroactively changing the denominator. A stop at the entry leaves
    R undefined rather than infinite.
  - **MFE and MAE are signed peaks of total trade P&L**, including P&L already
    realized by trims and excluding fees, so they are comparable with gross
    P&L. Reporting them as unsigned distances would hide a trade that gapped
    favourably and never came back, whose adverse excursion is a profit -- a
    case a test pins directly. Excursions track the position actually held at
    each bar, so a pyramided trade's peak reflects the size it held then.
  - **Exactness was designed in, not left to rounding.** The final close takes
    the exact remaining cost basis instead of a second rounded division, so a
    fully closed trade satisfies `gross P&L == exit notional - entry notional`
    exactly. Excursions carry the cost basis rather than the average, so
    `quantity * price - basis` never divides. Max notional is the basis itself.
  - A trade that is profitable on price but loses after fees and funding raises
    `TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT`, which is a distinct
    outcome rather than a plain loss.
  - A position that is not fully closed still accounts for its realized part
    and reports `TRADE_ACCOUNTING_POSITION_STILL_OPEN`;
    `as_completed_trade_record()` refuses it and otherwise maps onto the
    `portfolio.completed_trades` columns including `realized_r`.
  - **Independent xHigh review:** closed the release-gate findings in a
    separate review commit. Funding is now represented by signed, timestamped
    `FundingEvent` records and reconciled to the quantity held at each event;
    positive cost is paid and negative cost is received. Aggregate nonzero
    funding is refused because it has no point-in-time evidence.
  - MFE/MAE now use
    `SIGNED_GROSS_PNL_FULL_BARS_AND_FILL_ENDPOINTS_V1`: any OHLC bar containing
    ENTER, ADD, TRIM, or EXIT is excluded because intrabar order is unknowable,
    while exact non-entry fill endpoints retain realized trim and gap-stop
    outcomes. This prevents pre-entry and post-exit extremes from leaking into
    excursions.
  - Open trades require an explicit `as_of`, have no exit reason or final R,
    and retain realized-to-date accounting only. Closed trades require source
    identities for both the initial stop and exit reason. The canonical
    lifecycle adapter reconciles every fill to BTC-150 transitions and derives
    those inputs from their source records.
  - Serialized accounting now carries all fill, funding, bar, policy, config,
    and source evidence plus a deterministic evidence digest. Restoration
    replays the record field-for-field and rejects inconsistent or altered
    metrics. Migration `0021_trade_accounting` adds every BTC-165 output,
    convention, and the complete replay record to `portfolio.completed_trades`.
    `max_size` is explicitly `MAX_OPEN_ENTRY_COST_BASIS_V1`, reported as both
    base-asset quantity and entry-cost notional rather than market exposure.
  - **EPIC Q integration review.** The position walk is now exact rational
    arithmetic. A pro-rata basis removal is `cost_basis * closed / open`, which
    repeats for any open quantity that does not terminate in Decimal's 28-digit
    context -- and BTC-155 produces those routinely, because it divides a
    notional by a price. The rounded removal left the amount taken out of the
    basis and the amount added to realized P&L disagreeing by about 1e-23, so
    an ordinary add-then-trim trade failed the exact cash-flow identity and was
    refused outright. Cost basis, realized P&L, entry and exit notional and the
    excursion walk are carried as `Fraction` and converted once at the
    boundary; a terminating value converts exactly and only a still-open
    trade's repeating pro-rata figure is rounded. Reported values are
    unchanged apart from trailing zeros. BTC-223 and BTC-224 had both pinned
    this gap as a known limit; both are now positive regressions.

#### BTC-166 Persist complete paper trade lifecycle
- **Description:**
  Every event linked to:

  ```text
  recommendation_id
  strategy_version
  parameter_set_id
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-160..165 and completed paper-portfolio persistence schema
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - **The schema could not satisfy this ticket.** `recommendation_id` already
    existed, but `strategy_version` and `parameter_set_id` had no column
    anywhere: BTC-150 kept them inside a JSON note, and `paper_orders` has no
    note column at all, so an order row carried no strategy identity
    whatsoever. Migration `0020_lifecycle_provenance` adds both as NOT NULL,
    blank-checked, indexed columns on `paper_orders`, `position_events` and
    `completed_trades`. Provenance has to be queryable, or two parameter sets
    are indistinguishable in the record and no paper-versus-backtest
    comparison means anything.
  - `completed_trades` reached its recommendation only through `positions`, so
    the migration adds a `recommendation_id` column and foreign key there too,
    making the triple uniform. That gap was found by the module's own row
    verifier rather than by inspection.
  - `recommendation_id` is deliberately left nullable. Its foreign keys are
    `ON DELETE SET NULL`, so a NOT NULL column would make deleting a
    recommendation fail rather than sever the link. The requirement is enforced
    in the writer, which is the layer that knows an event is model-driven, and
    a `None` recommendation is refused there.
  - Added `btc_predictor/portfolio/lifecycle_persistence.py` with
    `build_paper_trade_lifecycle_rows()`, policy version
    `PAPER_LIFECYCLE_PERSISTENCE_V1`. BTC-160 through BTC-165 each shape their
    own row; what none can know alone is whether the *set* of rows for one
    trade is complete and consistently attributed.
  - **Stamping is verified, not trusted.** `verify_lifecycle_rows()` re-checks
    every row for the full triple, for the same account and position, and for
    column names the target table actually has, so a builder that drifts from
    the schema fails there rather than at the first INSERT. `as_record()`
    re-verifies before persisting.
  - Provenance overrides an execution's own `recommendation_id`, so a lifecycle
    written under one recommendation cannot contain rows attributed to another.
  - A partial lifecycle still persists what it has and reports which part is
    absent (`NO_ORDERS`, `NO_EVENTS`, `TRADE_NOT_CLOSED`) rather than failing.
  - One BTC-161 test asserted its order record covered *exactly* every
    `paper_orders` column. That became false by design and was corrected to
    state the actual contract: execution knows the fill, not the run, and must
    not invent a strategy version.
  - **EPIC Q integration review.** Only the BTC-165 accounting had its strategy
    identity checked against the provenance; every BTC-161..164 execution and
    the BTC-150 ledger were stamped on trust. A trade run under one parameter
    set could therefore be persisted as another and `verify_lifecycle_rows()`
    would still pass, which would make the queryable provenance the ticket
    exists to create fiction. Every contributor's own `config_metadata` is now
    verified against the stamp before its rows are built.

## EPIC R — Advisory Output

#### BTC-170 Create recommendation renderer
- **Description:**
  Example output:

  ```text
  BTC SWING SIGNAL

  Regime: BULL
  Setup: BULLISH RESET
  Entry Conviction: 88

  ACTION:
  ENTER INITIAL TRANCHE

  Entry Zone:
  98,500–101,000

  Invalidation:
  91,300

  Stop:
  89,800

  Risk:
  0.50% NAV

  Suggested Exposure:
  5.1% NAV

  R/R:
  3.2R

  Trend:       82
  Flow:        87
  Positioning: 84
  Volatility:  71
  Structure:   94

  WHY:
  ✓ Bull regime intact
  ✓ ETF flow acceleration positive
  ✓ OI flushed
  ✓ Funding normalized
  ✓ Weekly support cluster
  ✓ Higher-low confirmation

  RISKS:
  ! Macro backdrop weakening
  ! Volatility above median

  ADD CONDITION:
  New higher low
  + Add Score >= 85
  + Positioning >= 70
  + risk limit respected

  ACTION:
  ENTER / WATCH / HOLD / ADD / TRIM / EXIT / NO TRADE
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130..133, BTC-140..146, BTC-160..166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.reporting.recommendation` with a typed, versioned
    `RECOMMENDATION_RENDERER_V1` contract over the existing reconstructable
    `signals.recommendations`, `signals.predictor_runs`, and ranked
    `signals.recommendation_reason_codes` records. The renderer makes no signal,
    risk, lifecycle, or action decisions of its own.
  - The plain-text advisory has stable sections for run identity, regime/setup,
    final action, entry geometry, risk, suggested exposure, R/R, component
    scores, positive evidence, warnings, hard blockers, and configured add
    conditions. Every persisted action has one unambiguous display label;
    unavailable optional values are shown as `N/A` rather than invented.
  - Reason rows are linked to the recommendation and displayed by their
    persisted contiguous `reason_rank`. Their code, source, severity, and detail
    remain in the replay record; `info`, `warning`, and `veto` evidence is
    visibly separated. Single-line validation prevents reason text from
    injecting a false action into the advisory.
  - The linked predictor run must match the recommendation's `run_id` and UTC
    evaluation time, and its config identity must match the supplied validated
    strategy config. An `ENTER` or `ADD` advisory is rejected when any persisted
    veto remains, preventing contradictory output at the presentation boundary.
  - Suggested exposure as a fraction of NAV is derived only when the persisted
    `risk_amount`, `risk_fraction_nav`, and `suggested_notional` establish NAV;
    otherwise it is explicitly unavailable. The full-precision inputs are
    retained even though display values are rounded deterministically.
  - Add conditions reflect the actual BTC-154/config contract: structural
    confirmation, Add Score threshold, supportive regime/flow/positioning,
    profitable position, improving stop, no averaging down, and aggregate
    risk-at-stop ceiling. The example's `Positioning >= 70` is not emitted
    because no such configured numeric add threshold exists.
  - `RecommendationRendererResult.as_record()` persists the source
    recommendation, predictor-run identity, ranked reasons, add-policy values,
    config identity, renderer version, media type, and body. Restoration
    regenerates the output and rejects source, config, or body drift. Eighteen
    focused tests cover deterministic rendering, every action, optional data,
    exact replay, provenance, rank/link validation, veto safety, and text
    injection; the full project suite passes.

#### BTC-171 Create existing-position management report
- **Description:**
  Show:

  - current position
  - average entry
  - current stop
  - new candidate stop
  - unrealized P&L
  - Hold Score
  - Add Score
  - risk-at-stop
  - suggested action
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-150..158, BTC-160..166, BTC-170
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor.reporting.position_management` with versioned
    `POSITION_MANAGEMENT_REPORT_V1` plain-text output over the BTC-170 advisory,
    BTC-150 lifecycle, BTC-156 trailing stop, BTC-146 aggregate risk-at-stop,
    and one explicit point-in-time mark.
  - The report shows the open state, direction, tranche count, quantity, mark
    price, market notional and NAV exposure, average entry, active stop,
    candidate stop, unrealized P&L and return, Hold Score, Add Score,
    risk-at-stop and ceiling state, final portfolio action, advisory reasons,
    and each upstream source's reason codes.
  - Current and proposed stop semantics are explicit. `lifecycle.stop_price` is
    the active stop and BTC-146 risk must be measured there; BTC-156's candidate
    is shown separately as `MOVE STOP`, `KEEP CURRENT STOP`, or `UNAVAILABLE`.
    A stop move is not silently folded into the persisted portfolio action.
  - `HOLD`, `ADD`, `TRIM`, or `EXIT` comes directly from the validated BTC-170
    recommendation. The renderer does not create a second action-precedence
    engine. Non-position actions and closed/missed lifecycles are rejected.
  - Mark-to-market notional and side-aware unrealized P&L call the shared
    BTC-047 float64 kernels. The mark timestamp must equal the recommendation's
    UTC evaluation time, lifecycle events cannot lie in the future, and the
    trailing result must use the same mark.
  - Config identity, symbol, direction, active stop, and the complete tranche
    ledger are checked across all sources. Aggregate risk from another position
    or stop cannot be attached to the report. Added
    `risk_at_stop_from_record()` so BTC-146 records receive the same exact
    restoration check already available for lifecycle and trailing-stop data.
  - `PositionManagementReportResult.as_record()` retains the complete advisory,
    lifecycle, trailing-stop and risk records, mark provenance, exact derived
    metrics, config identity, source reason codes, format/version identity, and
    rendered body. Restoration regenerates metrics and text and rejects drift.
  - Thirteen focused tests cover long/short P&L, advanced and held stops, all
    management actions, exact replay, source linkage, config/time/stop/tranche
    mismatches, closed positions, risk tampering, and line injection. The full
    project suite passes.

#### BTC-172 Add machine-readable JSON output
- **Description:**
  Useful for dashboards, notifications, or future automation.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-170, BTC-171
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor.reporting.json_output` with canonical schema
    `ADVISORY_JSON_SCHEMA_V1` and media type `application/json` for both
    `recommendation` (BTC-170) and `position_management` (BTC-171) documents.
  - Each JSON envelope declares its document type, schema version, decimal
    encoding (`decimal_string`), timestamp encoding (`iso8601_utc`), and the
    complete validated source record. Exact decimal values remain strings, so
    dashboard consumers do not inherit binary-float rounding.
  - Encoding uses sorted keys, compact separators, ASCII escaping, and rejects
    NaN/infinity. It deliberately has no generated-at field, random identifier,
    locale-sensitive formatting, or other nondeterministic value.
  - Config identity, renderer/report versions, all ranked reason details,
    upstream reason codes, marks, risk records, and replay evidence remain in
    the payload. The persistence record also exposes source feature/version,
    config metadata, and source/output reason-code identities for indexing.
  - `advisory_source_from_json()` restores and revalidates standalone documents
    through the BTC-170/BTC-171 replay functions. Noncanonical JSON, unknown
    envelope fields/types, changed encoding conventions, altered nested source
    records, and body/record drift fail closed.
  - Ten focused tests cover both document types, deterministic bytes,
    standalone and persistence replay, nested provenance, schema/encoding/type
    validation, tampering, malformed/noncanonical JSON, and unsupported source
    objects. The full project suite passes.

## EPIC S — Backtesting

#### BTC-180 Build event-driven backtest engine
- **Description:**
  Must support:

  - point-in-time signals
  - entry zones
  - missed entries
  - structural stops
  - adds
  - trims
  - trailing stops
  - fees
  - slippage
  - funding
  - NAV
  - risk-at-stop

  The backtester must call the same shared quant functions used by the advisory and paper-trading paths; it must not maintain separate formulas for sizing, risk-at-stop, R/R, or portfolio accounting.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-142, BTC-144..146, BTC-150, BTC-154..157,
  BTC-160..165
- **Priority:** P0
- **Complexity:** XL
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/engine.py` with `run_backtest()`, policy
    version `EVENT_DRIVEN_BACKTEST_V1`. The engine owns the clock and the
    routing while economic calculations stay in their authoritative owner
    modules.
  - The independent xHigh review fixed point-in-time decision timestamps,
    decision-time sizing, stale/final intent handling, adverse-first stop
    collisions, and trailing-stop provenance/reuse protection.
  - Entry, ADD, TRIM, structural stop, and discretionary EXIT fills route
    through shared execution owners. Fill conversion and completed/open-trade
    accounting route through BTC-165; sizing and per-bar risk route through
    BTC-144..146 and BTC-155. Delegation is verified with call spies and
    direct-owner parity tests rather than import checks alone.
  - The fixed within-bar order is carry for the pre-execution position,
    resting stop, one previously queued intent, close-marked NAV/risk, then the
    next strategy decision. A pre-authorized entry bracket resolves a same-bar
    entry/stop collision through BTC-162 on the adverse path; a newly installed
    trailing stop remains eligible only on later full bars under BTC-156.
  - Funding uses `BAR_CLOSE_PRE_EXECUTION_CARRY_V1` and persisted BTC-165
    `FundingEvent` evidence. ADD/TRIM/EXIT/STOP bars retain valid carry, and
    positive rates debit longs while crediting shorts.
  - NAV uses `CASH_PLUS_MARKED_UNREALIZED_V1`. Entry, exit, ADD, TRIM, funding,
    realized P&L, and open/closed trade evidence reconcile at result creation;
    unsupported insolvency fails closed instead of returning floored NAV.
  - Results persist exact bars, input/run/evidence digests, strategy identity,
    effective costs, event/refusal evidence, account state, lifecycle state,
    trades, and equity/risk snapshots. `restore_backtest_result()` validates a
    deterministic round trip and rejects nested evidence tampering.
  - Phase 1 supports one BTC position, one pending intent, explicit missed-bar
    expiry, and `MARK_OPEN_POSITION_NO_FORCED_EXIT_V1` at dataset end.
  - The strategy interface is a callable taking a `BacktestContext` and
    returning a `BacktestIntent`, which keeps the engine testable without the
    full feature stack while leaving every policy decision outside it.
  - **EPIC S integration review.** An ADD's BTC-154 requirements and a TRIM's
    BTC-157 signal are now held to the run's `config_metadata`, as the entry
    stop and the trailing stop already were. Both are strategy-supplied policy
    evidence that authorises an economic mutation and is persisted as the run's
    own evidence, so a result fitted under one parameter set could previously
    book an add or a trim inside a run declaring another, silently: BTC-182,
    BTC-183, BTC-184 and BTC-185 all compare `config_metadata` at their own
    boundaries and would all have agreed, because the run itself claimed the
    candidate identity. BTC-185 varies exactly those thresholds through
    `parameter_set_id`.
  - **EPIC S integration review.** An unnamed intent's default `source_id` is
    minted from the decision bar rather than from `decision_at`. Bar
    availability is not unique per decision -- `derive_ohlcv_bars` and
    `build_canonical_market_bars` stamp one ingestion time on a whole backfill
    -- and `source_id` is the key BTC-165 carries on every fill and the key
    BTC-183 joins entry contexts on. The bar contract keeps decision bars
    strictly increasing, so the default is now unique by construction. On such
    a dataset no decision can execute at all, and the refusal now names the
    dataset property that caused it instead of the strategy's bookkeeping.

#### BTC-181 Add realistic cost model
- **Description:**
  Profiles:

  ```text
  optimistic
  base
  stress
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/costs.py` with policy version
    `REALISTIC_COST_MODEL_V1`, feature `BACKTEST_COST_PROFILE`, and the ordered
    ladder `("optimistic", "base", "stress")` exposed as `cost_profiles()` and
    `cost_profile(name)`.
  - The `base` rung is not a fourth set of numbers. It is
    `execution_costs_from_config()` itself, the BTC-160 assumption advisory and
    paper trading already price against, so a base backtest cannot silently
    disagree with the rest of the system. Only the rungs that deviate are
    declared, under `[backtest.cost_profiles.optimistic]` and
    `[backtest.cost_profiles.stress]`; redeclaring `base` in configuration is
    rejected, as are unknown rung names and negative rates.
  - Resolving any rung validates the whole ladder and fails closed when a more
    pessimistic rung prices `fee_bps`, `slippage_bps`, or
    `funding_cost_bps_per_day` below a cheaper one. Every rung keeps
    `EXECUTION_COST_V1`, which the BTC-162/BTC-163 execution owners require,
    and `round_trip_cost()` delegates to the BTC-160 owner rather than
    re-deriving the round trip.
  - The shared `[backtest]` cost assumption is deliberately unchanged. This
    ticket adds the ladder around it; moving the base assumption itself is a
    versioned strategy-config decision, so the configured rung values are
    marked `PROVISIONAL_RESEARCH_CALIBRATABLE`.
  - `run_backtest(..., cost_profile=...)` executes a run under one named rung.
    It is mutually exclusive with an explicit `costs` override, an account
    priced off the rung is rejected, and leaving it unset preserves the exact
    BTC-180 resolution order while recording no profile, because a run that
    did not select a rung must not claim it did.
  - The selected rung is part of run identity: it enters `run_id`, is persisted
    on `BacktestResult` with its costs, round-trip cost fraction, config
    identity, and reason codes, and is restored by `restore_backtest_result()`.
    Relabelling a persisted rung fails replay.
  - Reason codes are `COST_PROFILE_SELECTED`,
    `COST_PROFILE_SHARED_CONFIG_COSTS` for the base rung, and
    `COST_PROFILE_FUNDING_UNPRICED` where a rung prices no carry, plus
    `BACKTEST_COST_PROFILE_APPLIED` on the run itself. A run that prices no
    funding says so instead of implying carry is free.

#### BTC-182 Implement walk-forward validation
- **Description:**
  No single static train/test split.

  Use rolling or expanding windows.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-180
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - The independent xHigh review closed a release-blocking single-fold
    loophole: a schedule must produce at least two complete folds before it can
    be called a walk-forward validation. Exactly one fold is still the static
    train/test split this ticket replaces, so it now fails before the strategy
    factory runs instead of persisting `WALK_FORWARD_COMPLETE`.
  - Added `btc_predictor/backtest/walk_forward.py` with feature
    `WALK_FORWARD_VALIDATION`, policy version `WALK_FORWARD_VALIDATION_V1`,
    split policy `TRAIN_STRICTLY_BEFORE_TEST_V1`, capital policy
    `INDEPENDENT_FOLD_CAPITAL_V1`, and the schemes `("rolling", "expanding")`.
  - `walk_forward_windows()` cuts any ordered UTC schedule into complete folds,
    so BTC-048 decision timestamps fold exactly like bar timestamps for the
    BTC-186/BTC-189 research consumers. An expanding split keeps every earlier
    period; a rolling split slides a fixed in-sample window; `embargo_periods`
    drops periods between train and test so research fitted against forward
    targets cannot label its own test window.
  - The leakage barrier is structural rather than advisory.
    `run_walk_forward()` hands the strategy factory a `TrainingWindow` holding
    that fold's in-sample bars only, and hands BTC-180 that fold's
    out-of-sample bars only. Each fold persists the proof: its engine result's
    `bar_count`, `started_at`, and `ended_at` must equal its window. What the
    module cannot police is a factory that reaches for data it was not given.
  - `INDEPENDENT_FOLD_CAPITAL_V1`: every fold opens a pristine account at the
    same starting NAV. Compounding folds would make fold *k* a function of
    folds *1..k-1*, which lets one lucky early fold carry a rule that stopped
    working years ago.
  - Out-of-sample windows never overlap: `step_periods` below `test_periods` is
    rejected rather than aggregated, because pooling overlapping windows counts
    the same market twice. A wider step is allowed but declares
    `WALK_FORWARD_OUT_OF_SAMPLE_GAPS`, and leading, skipped, tested, and
    trailing periods must add up to the schedule, so a coverage claim cannot
    hide untested history. A schedule too short for two complete folds fails
    closed with the minimum it needs, and a short tail is reported untested
    instead of tested as a short fold.
  - The engine sees only a fold's out-of-sample bars, so a strategy needing
    warm-up history must seed it from the `TrainingWindow`. Warm-up data is
    in-sample data.
  - A factory returns a `FoldStrategy` with an explicit `strategy_id` and an
    optional calibration record; one identity declaring two different
    calibrations is rejected. The validation records
    `WALK_FORWARD_STRATEGY_CONSTANT` or `WALK_FORWARD_STRATEGY_RECALIBRATED`
    from those declarations rather than guessing from closures, because a
    constant-rule walk-forward is evidence about the rule and not about a
    fitting procedure that never ran.
  - `validation_id` covers the policy versions, the plan, the schedule digest,
    the dataset length, symbol, starting capital, effective costs, any BTC-181
    rung, and every fold's declared identity, calibration, and `run_id`.
    `restore_walk_forward_validation()` recomputes each fold summary from
    restored BTC-180 evidence, so edited headline numbers, moved windows,
    dropped folds, and rewritten coverage counts all fail replay.
  - Configuration adds `[backtest.walk_forward]` (`scheme`, `train_periods`,
    `test_periods`, `step_periods`, `embargo_periods`), defaulting to an
    expanding 730/182/182/0 daily split and marked
    `PROVISIONAL_RESEARCH_CALIBRATABLE`. Configuration parses types; the
    relational rules stay in the owner module, as with the BTC-181 ladder.
  - BTC-180's bar contract is now exposed as `validate_backtest_bars()` so
    windows are planned against exactly the dataset the engine would replay;
    the validation itself is unchanged.
  - Reason codes are `WALK_FORWARD_ROLLING_WINDOWS`,
    `WALK_FORWARD_EXPANDING_WINDOWS`, `WALK_FORWARD_EMBARGO_APPLIED`,
    `WALK_FORWARD_NO_EMBARGO`, `WALK_FORWARD_OUT_OF_SAMPLE_CONTIGUOUS`,
    `WALK_FORWARD_OUT_OF_SAMPLE_GAPS`,
    `WALK_FORWARD_INDEPENDENT_FOLD_CAPITAL`,
    `WALK_FORWARD_COST_PROFILE_APPLIED`, `WALK_FORWARD_STRATEGY_CONSTANT`,
    `WALK_FORWARD_STRATEGY_RECALIBRATED`, `WALK_FORWARD_FOLD_CALIBRATED`,
    `WALK_FORWARD_FOLD_UNCALIBRATED`, `WALK_FORWARD_FOLD_NO_TRADES`,
    `WALK_FORWARD_FOLD_POSITION_OPEN_AT_END`,
    `WALK_FORWARD_TRAILING_PERIODS_UNTESTED`, `WALK_FORWARD_NO_TRADES`, and
    `WALK_FORWARD_COMPLETE`. A validation in which no fold traded says so
    rather than reading as a passed check.
  - Aggregates stay to what BTC-180 evidence supports: fold count, tested and
    untested coverage, trade counts, profitable and losing folds, the summed
    independent fold P&L, the unweighted mean fold return quantized to twelve
    decimal places, and the best and worst folds. Drawdown, regime, and setup
    breakdowns remain with BTC-183/BTC-184/BTC-189.
  - Added 66 focused tests covering the split contract, expanding and rolling
    windows, embargoes, coverage accounting, the leakage barrier in both
    directions, independent capital, calibration declarations, cost-profile
    pass-through, determinism, persistence, tampering, and configuration; the
    complete Python 3.12 suite passes with 2409 tests.

#### BTC-183 Implement regime performance breakdown
- **Description:**
  Break down by:

  - bull
  - bear
  - neutral
  - high vol
  - low vol
  - pre-ETF
  - ETF era
  - setup type
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-182
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/regime_performance.py` with feature
    `REGIME_PERFORMANCE_BREAKDOWN`, policy version
    `REGIME_PERFORMANCE_BREAKDOWN_V1`, and a report built only from BTC-182
    out-of-sample folds. It does not pool training history or independently
    compound fold capital.
  - Every filled BTC-180 trade must have exactly one
    `RegimePerformanceContext`, keyed by fold number and the queued entry
    intent's `source_id`. The context timestamp must equal the persisted entry
    decision event, its feature evidence must have been available no later
    than that decision, its config identity must equal the validation, and
    missing, duplicate, or unused contexts fail closed.
  - Context construction accepts the authoritative
    `RegimeClassificationResult`, `VolatilityScoreResult`, and one complete,
    detected Phase-1 setup result. Their full records are persisted. The
    reporting layer groups their declared labels; it does not recompute the
    regime score, volatility percentile, or setup rules.
  - `RULEBOOK_DIRECTIONAL_REGIME_BUCKETS_V1` maps Strong Bull, Bull, and Mild
    Bull to `BULL`; Strong Bear, Bear, and Mild Bear to `BEAR`; and preserves
    `NEUTRAL`. `VOLATILITY_REGIME_BINARY_BUCKETS_V1` maps the existing
    `VOLATILITY_REGIME_V1` Compressed/Normal side to `LOW_VOL` and the
    Elevated/Stressed side to `HIGH_VOL`, using the owner's existing
    Normal/Elevated boundary rather than introducing a second percentile
    threshold.
  - `US_SPOT_BITCOIN_ETF_FIRST_TRADING_DAY_V1` fixes the report's historical
    era boundary at `2024-01-11T00:00:00Z`: entry decisions before it are
    `PRE_ETF`, and decisions on or after it are `ETF_ERA`. The timestamp and
    policy version are persisted in every report.
  - Setup buckets preserve the four Phase-1 setup identifiers: Bull Trend
    Continuation, Bullish Reset, Capitulation Reversal, and Bearish
    Distribution. Every declared bucket is emitted even when it has no trades,
    so repeated experiments retain a stable schema.
  - Each bucket records total, closed, and open trades; closed wins, losses,
    and flats; realized net P&L; marked unrealized P&L; total P&L; available R
    count/sum/mean; and closed-trade win rate. Missing rates remain `None`, not
    zero. Rates and means use deterministic twelve-decimal half-even rounding.
  - `FOLD_END_MARK_TO_MARKET_V1` assigns a fold's BTC-180 ending unrealized P&L
    to its one permitted open trade while retaining that trade's realized net
    P&L. Every independent axis must cover every trade exactly once and must
    reconcile to overall P&L and, within BTC-180's declared Decimal tolerance,
    to the arithmetic sum of independent fold NAV changes.
  - `report_id` binds the versioned grouping/marking policies, ETF boundary,
    BTC-182 validation identity/evidence, and canonicalized context identities.
    `evidence_digest` covers the complete validation, source feature records,
    attributions, metrics, configuration metadata, and reason codes;
    `restore_regime_performance_breakdown()` rebuilds all derived evidence and
    rejects tampering.
  - Reason codes are
    `REGIME_PERFORMANCE_ENTRY_DECISION_CONTEXT`,
    `REGIME_PERFORMANCE_MARKET_REGIME_GROUPS_APPLIED`,
    `REGIME_PERFORMANCE_VOLATILITY_GROUPS_APPLIED`,
    `REGIME_PERFORMANCE_ETF_ERA_GROUPS_APPLIED`,
    `REGIME_PERFORMANCE_SETUP_GROUPS_APPLIED`,
    `REGIME_PERFORMANCE_OPEN_TRADES_MARKED`,
    `REGIME_PERFORMANCE_NO_TRADES`, and
    `REGIME_PERFORMANCE_COMPLETE`.
  - Added 32 focused tests covering all seven Rulebook regimes, all four
    volatility regimes, all four setup types, the ETF boundary, point-in-time
    matching, open/closed/no-trade economics, complete attribution,
    deterministic ordering and replay, persistence, and tamper rejection. The
    complete Python 3.12 suite passes with 2441 tests.

#### BTC-184 Implement setup-level performance report
- **Description:**
  Compare:

  ```text
  Trend Continuation
  Bullish Reset
  Capitulation Reversal
  Bearish Distribution
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-182
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/setup_performance.py` with feature
    `SETUP_LEVEL_PERFORMANCE_REPORT`, report policy
    `SETUP_LEVEL_PERFORMANCE_REPORT_V1`, closed-outcome metric policy
    `CLOSED_NET_OUTCOME_METRICS_V1`, and implementation commit `08e6197`.
  - The report consumes only BTC-182 out-of-sample validation evidence and the
    exact filled-entry contexts already governed by BTC-183. It delegates
    attribution to `run_regime_performance_breakdown()` rather than detecting
    setups, rescoring history, or duplicating point-in-time matching rules.
  - Every report emits the four Phase-1 setup rows in canonical order: Bull
    Trend Continuation, Bullish Reset, Capitulation Reversal, and Bearish
    Distribution. Empty rows remain present so experiment schemas are stable.
  - Each row compares trade and closed-outcome counts, realized and fold-end
    marked P&L, fees, funding, total costs, closed net profit/loss, expectancy,
    win rate, average winner/loser, average closed holding days, and realized-R
    count/sum/mean. Economic values come from BTC-165 trade accounting and the
    BTC-183 setup bucket, not parallel formulas.
  - Open positions contribute realized economics and the BTC-183
    `FOLD_END_MARK_TO_MARKET_V1` ending mark to total P&L, but do not enter
    closed-trade expectancy, win rate, profit factor, average outcome, holding
    period, or R metrics.
  - Profit factor is versioned as closed net profit divided by absolute closed
    net loss. Its value remains `None` with explicit statuses for no closed
    trades, no closed losses (unbounded), and all-flat closed outcomes; missing
    metrics are never silently zero-filled.
  - `report_id` binds the metric, profit-factor, and open-mark policies plus the
    BTC-183 source report identity/evidence. The full source breakdown,
    configuration metadata, four comparison rows, and reason codes are covered
    by `evidence_digest`; `restore_setup_performance_report()` reconstructs all
    derived evidence and rejects top-level or nested tampering.
  - Added 14 focused tests covering all four setup types, open/closed/no-trade
    behavior, wins and losses, costs and R delegation, profit-factor statuses,
    exact source-path parity, deterministic ordering, persistence, and tamper
    rejection. Focused and dependency tests pass with 112 tests; the complete
    Python 3.12 suite passes with 2455 tests.

#### BTC-185 Implement threshold sweeps
- **Description:**
  Sweep:

  - Entry Conviction
  - Trend minimum
  - Flow minimum
  - Positioning minimum
  - Structure minimum
  - R/R
  - stop buffer
  - Hold threshold
  - Add threshold
  - risk budget

  Prefer robust plateaus over sharp optima.

  Because v1.2 changes score distributions, explicitly revalidate:

  ```text
  Entry Conviction action bands
  Structure minimum / hard-reject bands
  Hold Score action bands
  Add Score threshold
  ```

  Retain v1.1 nested scoring only as a benchmark strategy version; do not mix
  v1.1 and v1.2 scores inside one parameter set.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-049, BTC-180
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/threshold_sweeps.py` with policy version
    `ONE_DIMENSIONAL_THRESHOLD_SWEEP_V1`. Each report varies exactly one
    declared scalar threshold and evaluates every candidate through a complete
    BTC-182 out-of-sample walk-forward validation; multi-dimensional surfaces
    remain BTC-188 scope.
  - The supported vocabulary covers Entry Conviction, Trend, Flow,
    Positioning, Structure, R/R, ATR stop buffer, Hold, Add, and risk budget.
    Each specification persists the exact configuration paths being varied and
    the ticket-required score-band / hard-reject revalidation scope.
  - Every candidate receives a deterministic parameter-set ID and must persist
    that identity through its strategy configuration and nested backtest
    evidence. Candidate comparisons fail closed unless symbol, full schedule,
    split, capital, costs, tested coverage, and every out-of-sample input digest
    match.
  - Net outcome metrics reuse BTC-182/BTC-180 evidence: fold and trade counts,
    arithmetic total and net P&L across independent folds, mean/best/worst fold
    return, closed-trade expectancy, and mean available BTC-165 R-multiple.
    Unavailable closed-trade metrics remain `None`; they are not zero-filled.
  - `ADJACENT_GLOBAL_BEST_TOLERANCE_V1` reports contiguous candidate regions
    within an explicit absolute objective tolerance as robust plateaus. A lone
    best candidate is flagged as an isolated optimum; the research layer never
    promotes or mutates the production parameter set.
  - Enforced exact strategy/scoring-architecture pairs so v1.2 direct,
    de-nested scores and the v1.1 nested benchmark can only be evaluated in
    separate sweep specifications and parameter sets.
  - Reports persist versioned policies, objective/tolerance, baseline, candidate
    configuration, reason codes, full nested validations, deterministic IDs,
    and a SHA-256 evidence digest. Restoration reconstructs all derived metrics
    and plateau claims and rejects top-level or nested tampering.
  - Added 32 focused tests covering all ten dimensions, required revalidation
    scopes, plateau and isolated-optimum behavior, unavailable metrics,
    comparable input enforcement, architecture isolation, deterministic replay,
    persistence, invalid definitions, and tamper rejection. Focused and
    dependency regressions pass with 390 tests; the complete Python 3.12 suite
    passes with 2487 tests. Implementation commit:
    `f26dca55e0b559b2496513a2d52be2e23e246727`.
  - The independent review closed two findings. A candidate that never traded
    returns exactly zero rather than nothing, so a sweep in which some or all
    candidates never traded produced a contiguous zero-return region that read
    as `THRESHOLD_SWEEP_ROBUST_PLATEAU` on no evidence, and named a non-trading
    candidate as best. The report now also declares
    `THRESHOLD_SWEEP_NO_TRADES` or `THRESHOLD_SWEEP_CANDIDATES_WITHOUT_TRADES`,
    carrying BTC-182's `WALK_FORWARD_NO_TRADES` convention up to the sweep.
  - Comparability now also holds the fitting procedure constant. Candidates
    refit per fold and candidates running a constant rule previously passed
    `THRESHOLD_SWEEP_COMPARABLE_RUNS` together, which confounds the swept
    threshold with the fitting procedure that BTC-182 records as
    `WALK_FORWARD_STRATEGY_CONSTANT` or `WALK_FORWARD_STRATEGY_RECALIBRATED`.
  - Added 4 independent regressions for the flat no-trade sweep, the partly
    traded sweep, a fully traded sweep, and mixed fitting procedures. Focused
    tests pass with 36 tests; the complete Python 3.12 suite passes with 2491
    tests.


## EPIC S2 — Extended Quant Research

These tickets begin only after the deterministic strategy, risk engine, and backtest engine can produce trustworthy historical outcomes.

#### BTC-186 Feature interaction research
- **Description:**
  Test whether combinations of predictors contain more information than individual component scores.

  Candidate interactions:

  \[
  Trend \times Flow
  \]

  \[
  Flow \times Positioning
  \]

  \[
  Positioning \times Structure
  \]

  \[
  Trend \times Volatility
  \]

  \[
  FundingReset \times OIDeleveraging \times FlowImprovement
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Uses only point-in-time Feature Matrix data
  - Reports interaction definition, sample size, effect size, and stability
  - Tests interactions by regime/setup rather than only globally
  - Does not promote any interaction directly into production
  - Candidate production changes require BTC-193 promotion process
- **Dependencies:** BTC-048, BTC-180, BTC-182
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/research/feature_interactions.py` with policy version
    `FEATURE_INTERACTION_RESEARCH_V1`. The five ticket candidates are frozen as
    explicit feature bindings. The three-way reset/deleveraging/improvement
    hypothesis requires point-in-time columns with those declared semantics;
    the research layer does not silently reinterpret existing health or level
    features as improvement signals.
  - Each BTC-182 fold fits a standardized main-effects OLS baseline and a
    nested model adding the standardized product term. Training statistics and
    transformations come only from that fold's training rows; only labels
    available by the fold's first test timestamp may enter fitting. Incremental
    out-of-sample R-squared compares the two models on the held-out rows.
  - Every interaction reports its exact formula and feature names, complete-case
    sample size, tested sample size, fold effect coefficients, baseline and
    interaction MSE, incremental out-of-sample R-squared, weighted mean effect,
    cross-fold effect dispersion, sign consistency, and positive-increment
    fraction. Zero-variance, rank-deficient, and undersized folds remain
    explicit unavailable estimates; missing features or targets are never
    zero-filled.
  - Reports include a global result plus every observed point-in-time regime
    and setup segment. Context evidence must be available by its exact decision
    timestamp, and feature, target, context schedules and strategy/config/
    parameter-set provenance must agree before analysis begins.
  - Specifications and reports persist versioned policies, BTC-182 split
    evidence, feature/target definition fingerprints, deterministic input and
    context digests, reason codes, research-only status, and the required
    `BTC-193` promotion boundary. Restoration reconstructs derived evidence and
    rejects nested tampering.
  - Added 18 focused tests covering all five interactions, main-effect control,
    global/regime/setup conditioning, effect size and stability, missing-value
    handling, unavailable training labels, future-append invariance,
    point-in-time contexts, provenance and schedule mismatches, explicit
    three-way bindings, deterministic replay, tamper rejection, invalid
    definitions, and degenerate designs. Focused dependency regressions pass
    with 324 tests; the complete Python 3.12 suite passes with 2509 tests.
    Implementation commits: `fed9b8775c3a2c4abf99bb2ca979afa2115a801f`
    (module and exports, committed concurrently with the BTC-185 review fix)
    and `b684c221be77287bcbe7b9e803a39d4203b75e4b` (formula precision and focused
    verification), followed by `24bf8e07d824601634006fb01429e0303bc319d1`
    (derived-evidence reconstruction validation).
  - **EPIC S2 integration review.** Derived statistics were computed in the
    caller's ambient decimal context rather than an explicit one, unlike
    BTC-187 and BTC-188. Under a reduced precision the module silently
    produced a different report for identical inputs, and a previously valid
    record failed `restore_feature_interaction_report()` with an aggregate
    mismatch that reads as tampering. `_metric()` and `_weighted_mean()` now
    pin `INTERACTION_DECIMAL_PRECISION`; every value at the default context
    is unchanged. Pinned by a regression that replays the report and its
    record at four reduced precisions.

#### BTC-187 Monte Carlo portfolio risk analysis
- **Description:**
  Bootstrap or resample historical strategy trade outcomes to estimate distributions of portfolio risk.

  Estimate:

  ```text
  Max drawdown
  Longest losing streak
  Ending NAV
  Calmar
  Probability DD > 10%
  Probability DD > 15%
  Risk-of-ruin style tail metrics
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Supports configurable simulation count and deterministic random seeds
  - Operates on R-multiples and/or net trade returns
  - Compares multiple risk-per-trade schedules
  - Produces percentile distributions, not only averages
  - Results are reproducible for a fixed seed/config
  - Used to challenge risk budgets rather than automatically change them
- **Dependencies:** BTC-165, BTC-180, BTC-191
- **Priority:** P1
- **Complexity:** L
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/monte_carlo_risk.py` with policy version
    `MONTE_CARLO_PORTFOLIO_RISK_V1`. `monte_carlo_risk_spec()` freezes one
    research question and binds it to the digest of the observed universe;
    `run_monte_carlo_risk_analysis()` is the only way to produce evidence and
    `restore_monte_carlo_risk_report()` the only replay path, which rebuilds
    the whole seeded analysis and compares it to the record rather than
    trusting persisted numbers.
  - The resampled universe is the *observed* record, never a fitted
    distribution. `trade_outcome_samples_from_dataset()` reads BTC-191 rows and
    `trade_outcome_samples_from_backtest()` reads a BTC-180 run's trades, both
    under `CLOSED_TRADE_OUTCOME_SAMPLES_V1`. Numbers are not recomputed: the R
    multiple stays the BTC-165 `INITIAL_PLANNED_RISK_V1` value. BTC-180 allows
    a run to end holding a position, so that trade is carried as an excluded
    sample citing `TRADE_ACCOUNTING_POSITION_STILL_OPEN` rather than resampled
    as though it had finished or discarded along with the run's closed trades.
  - Two bases, never mixed inside one analysis. Under `r_multiple` a
    schedule's declared fraction is capital *risked at the stop*
    (`RISK_FRACTION_OF_NAV_AT_STOP_V1`), matching Rulebook 17 / BTC-144, so NAV
    moves by `f * R`. Under `net_return_fraction` -- net P&L over entry
    notional, `NET_PNL_OVER_ENTRY_NOTIONAL_V1`, using the `entry_notional`
    BTC-191 carries for exactly this -- the same fraction means capital
    *deployed* (`NOTIONAL_FRACTION_OF_NAV_V1`). The two answer different sizing
    questions and are recorded as different `analysis_id`s.
  - `FIXED_FRACTIONAL_COMPOUNDING_V1` walks each path trade by trade;
    `PATH_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1` measures the worst decline along the
    realized path (not across paths); `RUIN_STOPS_THE_PATH_V1` ends a path at
    the declared ruin NAV, so `trades_taken` is itself tail evidence.
    `PATH_TOTAL_RETURN_OVER_MAX_DRAWDOWN_V1` divides path total return by that
    drawdown and is deliberately unannualized -- a resampled trade sequence
    declares no calendar. A path that never drew down reports Calmar as
    `UNDEFINED_NO_DRAWDOWN` rather than infinite, and those paths are counted.
  - Distributions, not averages. Every metric reports
    `NEAREST_RANK_PERCENTILE_V1` percentiles over a configurable grid (default
    1/5/10/25/50/75/90/95/99) beside mean, minimum, and maximum, so a reported
    percentile is an observed path. Alongside them each schedule reports the
    ticket's exceedance probabilities (default drawdown worse than 10% and 15%,
    configurable), probability of loss, and probability of ruin.
  - `COMMON_RESAMPLED_PATHS_ACROSS_SCHEDULES_V1`: the index paths are drawn
    once and every compared schedule is walked over the identical paths, so a
    difference between two budgets is the budget and not sampling noise. That
    also makes the comparison monotone -- on a shared path a larger fraction
    can only deepen the drawdown -- which is asserted as an invariant.
  - Determinism is owned by `btc_predictor.quant.simulation`, which gained
    `uniform_index_samples()` (`PCG64_RAW_REJECTION_UNIFORM_INDEX_V1`) and
    `permutation_index_samples()` (`PCG64_RAW_FISHER_YATES_PERMUTATION_V1`).
    Both read the raw 64-bit `PCG64` words with modulo rejection instead of a
    `Generator` bounded-integer convenience method: the bit-generator stream is
    stable across NumPy versions while the algorithm layered on it is not
    guaranteed to be, and persisted seeded evidence must replay on a later
    NumPy. Every derived statistic is computed in an explicit 60-digit decimal
    context and quantized to `1E-12`, so replay does not depend on the caller's
    ambient decimal context. Schedules are canonically ordered by NAV fraction,
    so one research question keeps one `analysis_id` however it was declared.
  - Nothing is zero-filled. A trade whose basis outcome BTC-165 could not
    measure is excluded by name carrying the BTC-165 reason code that explains
    it, and a zero entry notional makes the net return
    `MONTE_CARLO_NET_RETURN_UNDEFINED_ZERO_ENTRY_NOTIONAL` rather than zero.
    The report accounts for every sample as included or excluded, and declares
    `MONTE_CARLO_SMALL_SAMPLE_UNIVERSE` below 30 usable trades because
    resampling cannot manufacture evidence the observed record lacks. IID
    bootstrap declares `MONTE_CARLO_SERIAL_DEPENDENCE_NOT_PRESERVED`;
    permutation declares `MONTE_CARLO_TRADE_MULTISET_PRESERVED`.
  - The layer challenges a risk budget and cannot change one.
    `config_risk_per_trade_schedules()` reads the candidates the versioned
    strategy config already declares -- the BTC-144 conviction bands and the
    configured maximum risk at stop -- so a comparison challenges the budgets
    the strategy actually uses; the module has no promotion or mutation path
    and records `RESEARCH_ONLY_NOT_PRODUCTION` with BTC-193 as the required
    promotion boundary.
  - **Independent review:** fixed a P2 boundary defect in the public raw-index
    sampler. Bounds above the signed `int64` output domain had been accepted,
    allowing returned indices to wrap negative or raise an implementation
    overflow instead of satisfying `[0, high)`. The helper now fails closed
    above `2**63`, and frozen uniform/permutation golden vectors protect the
    persisted replay stream across dependency upgrades. Focused review tests
    pass with 104 tests; dependency regressions pass with 185 tests; the full
    Python 3.12 suite passes with 2684 tests.
  - **EPIC S2 integration review.** The public `nearest_rank()` is the owner
    BTC-189 delegates to for `NEAREST_RANK_PERCENTILE_V1`, and BTC-189 calls
    it from outside this module's own pinned computations. It resolved the
    rank in the caller's ambient context, so one declared convention could
    yield two ranks for the same percentile and sample size. The rank is now
    resolved in `MONTE_CARLO_DECIMAL_PRECISION`; internal percentile
    reporting was already inside that context and is unchanged.

#### BTC-188 Multi-dimensional parameter sensitivity surfaces
- **Description:**
  Extend BTC-185 from one-dimensional threshold sweeps into parameter surfaces.

  Example surfaces:

  \[
  f(EntryThreshold,RiskBudget)
  \]

  \[
  f(AddThreshold,StopBuffer)
  \]

  \[
  f(StructureMinimum,RRMinimum)
  \]
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Reports robust plateaus rather than only best points
  - Supports at least two-dimensional parameter grids
  - Calculates trade count, expectancy, average R, max drawdown, Sharpe, and Calmar per cell
  - Flags isolated optima as potential overfit
  - Results link back to parameter-set IDs
- **Dependencies:** BTC-180, BTC-185
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added `btc_predictor/backtest/parameter_surfaces.py` with policy version
    `MULTI_DIMENSIONAL_PARAMETER_SURFACE_V1`. A specification declares two or
    more axes over the BTC-185 parameter vocabulary; every cell of the axis
    aligned grid is evaluated as a separate complete BTC-182 out-of-sample
    walk-forward validation. Axes are canonically ordered by parameter name so
    one research question keeps one `surface_id` however it was declared, and
    two axes may not vary the same parameter or the same configuration path.
  - The layer reuses BTC-185 as the owner of the shared contract rather than
    restating it: `threshold_sweep_metrics` for net outcome metrics,
    `comparable_run_signature` for run comparability,
    `threshold_parameter_value` and `threshold_parameter_paths` for the
    parameter domains, `threshold_config_metadata` for the persisted identity,
    and `validate_scoring_architecture` for v1.2 / v1.1-benchmark isolation.
    Those six helpers are new public entry points on the BTC-185 module; its
    existing behaviour is unchanged.
  - Per cell the report adds the drawdown and risk-adjusted statistics the
    ticket requires to BTC-185's trade count, expectancy, and average R.
    `WORST_FOLD_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1` reports the worst within-fold
    peak-to-trough NAV decline, because BTC-182 restarts capital per fold and
    stitching folds would invent a compounded equity path that was never run.
    `POOLED_WITHIN_FOLD_PERIOD_RETURN_ZERO_RF_SHARPE_V1` pools per-period NAV
    returns inside folds, never across a fold break, and divides the mean by
    the sample standard deviation. `MEAN_FOLD_RETURN_OVER_MAX_DRAWDOWN_V1`
    divides the BTC-182 mean fold return by that drawdown. Neither ratio is
    annualized: the walk-forward layer declares no periods-per-year factor,
    and the report states this with `SURFACE_RISK_METRICS_UNANNUALIZED`.
  - Every derived statistic is computed inside an explicit 60-digit decimal
    context and quantized to `1E-12`, so replay does not depend on the
    caller's ambient decimal context. Undefined statistics carry an explicit
    status (`UNDEFINED_ZERO_DISPERSION`, `UNDEFINED_NO_DRAWDOWN`,
    `UNDEFINED_NON_POSITIVE_NAV`, `UNAVAILABLE_INSUFFICIENT_PERIODS`,
    `UNAVAILABLE_NO_EQUITY_CURVE`, `UNAVAILABLE_DRAWDOWN`) and remain `None`;
    they are never zero-filled. A drawdown of exactly zero is a measurement,
    so Calmar is reported as undefined rather than infinite.
  - `CONNECTED_GRID_GLOBAL_BEST_TOLERANCE_V1` generalizes the BTC-185 adjacent
    region to N dimensions: cells within an absolute objective tolerance of
    the global best form a plateau when they are connected by single steps
    along one axis. Cells whose objective is unavailable are holes that break
    connectivity instead of bridging it. A plateau records exact membership by
    parameter-set ID plus a per-axis bounding box that is explicitly not a
    membership claim. A best cell in no plateau is reported as
    `SURFACE_ISOLATED_OPTIMUM_OVERFIT_RISK`; the research layer never promotes
    or mutates the production parameter set.
  - Carrying the BTC-185 review forward, a cell that never traded still
    returns exactly zero, so the report additionally declares
    `SURFACE_NO_TRADES` or `SURFACE_CELLS_WITHOUT_TRADES` and
    `SURFACE_UNAVAILABLE_CELL_OBJECTIVE`, so a flat or partly evidenced region
    cannot read as robustness.
  - Reports persist versioned policies, objective and tolerance, every axis
    definition and revalidation scope, deterministic parameter-set IDs, full
    nested BTC-182 validations, plateau membership, reason codes, and a
    SHA-256 evidence digest. Restoration reconstructs every derived metric and
    plateau claim from the nested validations and rejects top-level or nested
    tampering.
  - Added 48 focused tests covering the three ticket example surfaces, three
    dimensional grids, declaration-order invariance, all six required per-cell
    metrics against independently derived drawdown, Sharpe, and Calmar values,
    connected and non-adjacent regions, isolated optima, unavailable
    objectives breaking connectivity, no-trade and partly traded surfaces,
    undefined risk statistics, comparability and fitting-procedure
    enforcement, architecture isolation, deterministic replay, persistence,
    invalid definitions, and tamper rejection. Focused and dependency
    regressions pass with 318 tests; the complete Python 3.12 suite passes
    with 2557 tests.
  - **EPIC S2 integration review.** Per-cell metrics were already computed in
    an explicit context, but the plateau tolerance comparison
    `best_value - value <= plateau_tolerance` was not. Plateau membership is
    a research conclusion rather than a formatting detail, so it is now
    resolved in `SURFACE_DECIMAL_PRECISION` as well.

#### BTC-189 Statistical predictor diagnostics
- **Description:**
  Add a formal quant diagnostic layer for features and scores.

  Initial diagnostics:

  ```text
  Pearson IC
  Spearman IC
  bootstrap confidence intervals
  quintile / bucket returns
  conditional expectancy
  direct-component correlation matrix
  rank-correlation matrix
  analytical effective-weight decomposition
  component / factor ablation
  trade-decision overlap after ablation
  conviction monotonicity
  factor concentration / effective-rank diagnostic
  regime-conditioned stability
  setup-conditioned stability
  MFE / MAE relationships
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Uses point-in-time Feature Matrix rows
  - Separates contemporaneous features from future targets
  - Reports sample size and uncertainty
  - Can compare raw features with composite scores
  - Reports v1.1 nested vs v1.2 de-nested effective-weight decomposition
  - Ablation can remove one component at a time without retraining unrelated rules
  - Reports trade overlap, expectancy, average R, and drawdown change after each ablation
  - Can evaluate whether higher conviction is monotonically associated with better outcomes
  - Distinguishes empirical correlation from prohibited mechanical nesting
  - Research outputs cannot modify the live strategy without BTC-193
- **Dependencies:** BTC-048, BTC-182, BTC-190
- **Priority:** P1
- **Complexity:** L
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/predictor_diagnostics.py` with feature
    `PREDICTOR_DIAGNOSTICS` and policy version
    `STATISTICAL_PREDICTOR_DIAGNOSTICS_V1`, and
    `btc_predictor/research/component_ablation.py` with
    `SINGLE_COMPONENT_ABLATION_V1`. The two halves of the ticket ask different
    questions of different evidence: the first reads BTC-048 rows, the second
    re-runs BTC-182 validations, so they are separate versioned reports rather
    than one report with two unrelated failure modes.
  - Predictors are the BTC-048 point-in-time feature columns and outcomes are
    the separately versioned forward targets. `FORWARD_TARGETS_RETROSPECTIVE_ONLY_V1`
    is structural, not advisory: a feature matrix whose columns include a
    target name is rejected, nothing here is fitted, and no target value can
    reach a predictor value.
  - Every estimate reports its own sample size and uncertainty. Pearson and
    Spearman ICs come with a seeded percentile bootstrap
    (`SEEDED_IID_PERCENTILE_BOOTSTRAP_V1`) drawn from the BTC-049
    `uniform_index_samples` stream and cut with BTC-187's
    `NEAREST_RANK_PERCENTILE_V1`, which was exposed as `nearest_rank()` rather
    than restated. Each estimate's stream is derived from the spec and that
    estimate's own identity, so an interval replays on its own regardless of
    how many other segments were evaluated first.
  - Missing values are complete-case excluded per pair and never zero-filled.
    A sample below `minimum_sample_size` reports `INSUFFICIENT_SAMPLES` with no
    coefficient, no interval, and zero resample counts; a constant predictor or
    target reports which side was constant. Correlation matrices use one shared
    complete-case mask across all components, because a pairwise-deleted matrix
    can be non-positive-semidefinite and would make the eigenvalue diagnostic
    meaningless.
  - `EQUAL_COUNT_SORTED_POSITION_BUCKETS_V1` cuts buckets by sorted position,
    so counts differ by at most one. Tied predictor values can therefore
    straddle a boundary; the boundary values are persisted and the straddle is
    declared in `tied_bucket_boundaries` rather than hidden. Buckets carry
    conditional expectancy, and `BUCKET_MEAN_RANK_CORRELATION_MONOTONICITY_V1`
    turns them into the conviction-monotonicity answer: the rank correlation of
    bucket ordinal against bucket mean, plus the step counts, so "mostly
    increasing" is distinguishable from monotone.
  - A specification must declare both a raw feature and a composite score, and
    must name the conviction predictor as one of its composite scores. The
    comparison and monotonicity reason codes are therefore always true of the
    report that carries them rather than aspirational.
  - Empirical correlation and mechanical nesting are reported side by side and
    never merged. The Pearson and rank matrices measure co-movement and each
    carries BTC-129's `MECHANICAL_VS_EMPIRICAL_NOTE`; the structural question
    is answered by `effective_weight_report()` embedded verbatim, so the v1.1
    nested and v1.2 de-nested decompositions come from the scoring-contract
    owner rather than being recomputed here.
  - `CORRELATION_EIGENVALUE_ENTROPY_EFFECTIVE_RANK_V1` reports the component
    correlation matrix's eigenvalues, the largest eigenvalue share, and the
    effective rank as the exponential of the eigenvalue-share entropy, so `k`
    distinct components score `k` and one repeated direction scores `1`.
  - MFE/MAE are related on jointly complete rows
    (`PAIRED_FORWARD_EXCURSION_BUCKET_RELATIONSHIP_V1`), so a bucket's upside
    and downside are the same trades rather than two different samples.
  - Every statistic is emitted globally and for each observed regime and setup,
    and `SEGMENT_WEIGHTED_RANK_IC_STABILITY_V1` summarizes cross-segment rank-IC
    dispersion and sign consistency. Rank IC is the stability statistic because
    it is least sensitive to one extreme outcome inside a thin segment.
  - Ablation removes exactly one direct component of a declared BTC-129
    composite and renormalizes the survivors proportionally
    (`PROPORTIONAL_RENORMALIZATION_OF_REMAINING_COMPONENTS_V1`), so every
    surviving component keeps its relative importance and no unrelated rule is
    refitted. The declared scoring architecture selects the BTC-129 graph and
    contracts version, so a v1.1 benchmark study is audited against v1.1.
    Weights are read from the owner and re-checked against it; they are never
    restated here.
  - Like BTC-185 and BTC-188, ablation does not rescore or mutate config: a
    caller receives a versioned parameter-set identity per variant and returns
    that variant's complete BTC-182 validation. Variants that differ in
    anything but `parameter_set_id` are rejected, and
    `comparable_run_signature()` must agree across every run before anything is
    compared.
  - Outcome metrics stay owned by BTC-185's `threshold_sweep_metrics()` and the
    drawdown by BTC-188, whose `WORST_FOLD_PEAK_TO_TROUGH_NAV_DRAWDOWN_V1`
    measurement was exposed as `walk_forward_max_drawdown()` instead of being
    duplicated. Each ablation reports its trade-decision overlap keyed by
    `FOLD_ENTRY_TIMESTAMP_TRADE_OVERLAP_V1` — fold number and the bar the
    position opened on, because run-local event IDs are not comparable across
    runs — and its change in trade count, mean return, expectancy, average R,
    and drawdown. A change whose baseline or variant value is undefined is
    declared `BASELINE_UNDEFINED`, `VARIANT_UNDEFINED`, or `BOTH_UNDEFINED`
    rather than reported as zero, and a study in which nothing traded says so.
  - Both reports are `RESEARCH_ONLY_NOT_PRODUCTION` with BTC-193 as the
    promotion boundary and no strategy or configuration mutation path.
    Persistence is the deterministic `as_record()` contract; restoration
    rebuilds and rejects edited coefficients, dropped analyses, moved segments,
    relabelled production status, unknown reason codes, and a substituted
    effective-weight decomposition.
  - Added 50 focused tests (31 diagnostics, 19 ablation) covering IC signs and
    rank/linear separation, seeded interval replay, complete-case exclusion,
    insufficient and zero-variance samples, bucket partitioning and boundary
    ties, monotonicity in both directions, raw-versus-composite comparison,
    regime and setup stability, correlation matrices, factor concentration,
    excursion pairing, point-in-time revision selection, target separation,
    proportional renormalization, run comparability, overlap in the identical,
    partial, and empty cases, undefined metric changes, the v1.1 nesting
    benchmark, determinism, record round trips, and tamper rejection. The
    complete Python 3.12 suite passes with 2734 tests.
  - **EPIC S2 integration review.** A BTC-189 report is embedded in a BTC-193
    promotion packet and restored from it, so evidence that replays
    differently under another process's decimal context would be rejected as
    tampered. `predictor_diagnostics` now pins `DIAGNOSTIC_DECIMAL_PRECISION`
    around `_metric()`, `_weighted_mean()`, and the bootstrap tail
    percentile; `component_ablation` extends its existing pin to the
    surviving weight total, the overlap fraction, and the metric changes,
    which sat outside it. The embedded BTC-129 decomposition was corrected in
    its own module. No reported value changes at the default context.
  - **EPIC S2 integration review, not a defect.** `_buckets()` and
    `_excursion_buckets()` both cut `EQUAL_COUNT_SORTED_POSITION_BUCKETS_V1`
    edges, and `_weighted_mean` / `_population_std` / `_sign_consistency` /
    `_metric` restate BTC-186's private helpers. The formulas agree and are
    pinned by test; a shared owner would have to cross the two modules'
    distinct error types, so the duplication is recorded rather than merged.


## EPIC T — Research & Learning Loop

#### BTC-190 Store market state for every decision date
- **Description:**
  Not only traded dates.

  Persist:

  ```text
  scores
  setup
  decision
  future_1w_return
  future_2w_return
  future_4w_return
  future_8w_return
  future_MFE
  future_MAE
  ```

  This allows research into rejected opportunities.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-180
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/decision_state.py` with policy version
    `DECISION_STATE_STORE_V1`. One immutable row per decision date joins the
    recorded categorical state, the point-in-time scores, and the forward
    outcomes; `build_decision_state_store()` is the only constructor and
    `restore_decision_state_store()` the only replay path.
  - Coverage is enforced, not assumed. `EVERY_DECISION_DATE_REQUIRED_V1`
    requires the recorded decision states to cover the BTC-048 feature-matrix
    decision grid exactly: a gap, a duplicate, or a state outside the grid
    fails closed, so traded dates cannot quietly become the only rows. Rows
    are ordered by decision timestamp regardless of input order, and
    `rejected_rows()` returns the non-traded dates the ticket exists for.
  - Numbers are not recomputed here. Scores are read from the BTC-048
    `PointInTimeFeatureMatrix` columns named by the versioned definition
    (default: the six v1.2 composite scores) and the outcomes from the
    BTC-048 `ForwardTargetMatrix` (default: the six the ticket lists), so the
    fixed-horizon, MFE, and MAE semantics stay owned by BTC-048 and its
    target specifications rather than being restated. `hit_2R_before_1R`
    stays available to a wider definition but is outside the default columns.
  - Categorical vocabularies are owned elsewhere too: the decision is a
    `RECOMMENDATION_ACTIONS` value, the setup one of the four Rulebook setups
    plus the explicit `NO_SETUP` sentinel, the regime a
    `REGIME_CLASSIFICATION_LABELS` value plus `UNCLASSIFIED`, and reason codes
    are `RecommendationReasonCode` values. Unknown values fail closed.
  - Traded and rejected dates are distinguished by observed execution, not by
    inferring intent from an action label: `TRADED` requires a
    `trade_reference` and `NOT_TRADED` forbids one, so a missed `ENTER`
    remains a rejected opportunity.
  - Nothing is zero-filled. Every score cell carries `AVAILABLE`,
    `MISSING_VALUE` (observed, value absent), or `NOT_OBSERVED`, and every
    outcome cell `AVAILABLE`, `MISSING_VALUE`, `PENDING_HORIZON` (the fixed
    horizon had not elapsed by the extraction time), or `NOT_RECORDED`.
    Unrecorded cells carry no provenance, so no future metadata leaks into a
    row; `score_matrix()` and `outcome_matrix()` expose the same values to
    NumPy consumers as read-only arrays with NaN missing masks.
  - `OUTCOME_AVAILABLE_BY_EXTRACTION_TIME_V1` keeps the store replayable as of
    its extraction time: an outcome that only became available afterwards is
    rejected with instructions to rebuild the forward-target matrix with that
    cutoff, a target matrix's own `data_available_at` must equal the
    extraction time, the extraction time may not precede the last decision
    date, and outcome price-source policy must match the feature-matrix
    provenance.
  - Persistence is the deterministic `as_record()` contract used by BTC-048
    and the other research layers, not a new database table; physical
    materialization is deliberately out of this ticket's scope. Records carry
    the definition fingerprint, feature and target definitions and their
    fingerprints, the provenance config metadata, the input digest, a
    coverage census, reason codes, `RESEARCH_ONLY_NOT_PRODUCTION`, BTC-193 as
    the promotion boundary, and a SHA-256 evidence digest. Restoration
    recomputes the coverage census from the restored rows and rejects
    tampered values, counts, dropped dates, and unknown columns.
  - Added 32 focused tests covering complete coverage of traded and rejected
    dates, point-in-time score selection and late revisions, pending and
    unrecorded outcomes, recorded-but-valueless cells, coverage census
    counts, ordering, every fail-closed guard, deterministic replay, record
    round trips, and tamper rejection. The complete Python 3.12 suite passes
    with 2589 tests.
  - **EPIC T integration review.** No defect. The store composes correctly with
    BTC-191: a traded date and the paper row it produced carry identical
    decision, setup, and regime labels and the same `trade_reference`, and a
    score revised after the decision reaches neither layer. Two non-blocking
    items are left with their owners. The store is the only EPIC T evidence
    BTC-193 cannot accept, so its persisted `BTC_193_REQUIRED_V1` boundary is a
    statement rather than an enforced gate, unlike BTC-191's, which BTC-193
    reaches through the BTC-192 paper comparison. And because the store is the
    epic's only proof that a campaign's traded dates are all of them, nothing
    stops a BTC-192 paper arm from being an unrepresentative subset of the
    trades its declared scope covers; binding the two is a versioned BTC-192
    policy decision rather than a review fix. Composition is pinned by
    `btc_predictor/tests/test_research_epic_t_integration.py`. `future_MFE` and
    `future_MAE` declare no horizon, so an unrecorded excursion is
    `NOT_RECORDED` rather than `PENDING_HORIZON`; that follows the documented
    status semantics, which scope `PENDING_HORIZON` to fixed horizons.

#### BTC-191 Create paper-trade outcome dataset
- **Description:**
  Join entry-state features to final outcomes.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-165, BTC-166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/paper_trade_outcomes.py` with policy version
    `PAPER_TRADE_OUTCOME_DATASET_V1`. One immutable row per completed paper
    trade puts the BTC-048 entry state and the BTC-165 final outcome in the
    same row; `build_paper_trade_outcome_dataset()` is the only constructor and
    `restore_paper_trade_outcome_dataset()` the only replay path.
  - **Only closed trades are joined.** `CLOSED_TRADES_ONLY_BY_EXTRACTION_TIME_V1`
    refuses an open position rather than joining its running numbers, because
    accounting-to-date is not a final outcome, and refuses a trade that closed
    after the extraction time so the dataset stays replayable as of that time.
    A row that still carried `TRADE_ACCOUNTING_POSITION_STILL_OPEN` fails
    closed even if it were constructed directly.
  - Numbers are not recomputed here. Outcome cells are read from the BTC-165
    `PaperTradeAccounting` and keep its field names, so `r_multiple` stays
    `INITIAL_PLANNED_RISK_V1`, the excursions stay
    `SIGNED_GROSS_PNL_FULL_BARS_AND_FILL_ENDPOINTS_V1`, and `max size` stays
    `MAX_OPEN_ENTRY_COST_BASIS_V1`. The dataset records those conventions and
    the accounting policy version and refuses an accounting that disagrees with
    them. `initial_risk`, `entry_notional`, and `exit_notional` are carried so
    BTC-187 can normalize outcomes without inventing a return convention here.
  - Entry state is point-in-time by construction:
    `ENTRY_STATE_AS_OF_ENTRY_DECISION_TIMESTAMP_V1` reads the BTC-048
    feature-matrix row for the trade's entry decision timestamp, which must be
    a decision timestamp on that grid and must not follow the opening fill, and
    every cell's availability is re-checked against that timestamp. The
    categorical vocabularies stay owned by BTC-190 (`PAPER_TRADE_DECISIONS`,
    `PAPER_TRADE_SETUPS`, `PAPER_TRADE_REGIMES`), so a trade and the decision
    date that produced it carry identical labels for BTC-192.
  - Nothing is zero-filled. An entry feature is `AVAILABLE`, `MISSING_VALUE`
    (observed, value absent), or `NOT_OBSERVED`, and unrecorded cells carry no
    provenance. An outcome BTC-165 could not measure is `NOT_MEASURED` and must
    cite the BTC-165 reason code that explains it -- `TRADE_ACCOUNTING_R_UNDEFINED`
    or `TRADE_ACCOUNTING_NO_EXCURSION_BARS` -- and that code must be one the
    accounting actually raised. `entry_feature_matrix()` and `outcome_matrix()`
    expose read-only NumPy arrays with NaN missing masks; `outcome_series()`
    returns the exact `Decimal` values for consumers that must not round.
  - Provenance is reused, not restated: each row carries the BTC-166
    `LifecycleProvenance` triple, and `ONE_STRATEGY_PROVENANCE_PER_DATASET_V1`
    requires the entry, its accounting `config_metadata`, and the feature-matrix
    provenance to agree on `strategy_version` and `parameter_set_id`. Comparing
    strategy versions or parameter sets is BTC-192's job across datasets, not a
    silent mixture inside one. Entry symbol and direction are cross-checked
    against the executed trade.
  - Exit reasons are recorded and counted as BTC-165 identifiers without a new
    frozen vocabulary, because the exit reasons in use are wider than
    `EXIT_REASON_IDS`; the census reports exactly the reasons observed.
  - Persistence is the deterministic `as_record()` contract used by BTC-048 and
    BTC-190, not a new database table. Records carry the definition fingerprint,
    feature definition and fingerprint, provenance config metadata, accounting
    conventions, the input digest (which replays every accounting through
    `PaperTradeAccounting.as_record()`), a coverage census, reason codes,
    `RESEARCH_ONLY_NOT_PRODUCTION`, BTC-193 as the promotion boundary, and a
    SHA-256 evidence digest. Restoration recomputes the census and rejects
    tampered values, dropped rows, altered counts, relabelled provenance, and
    invented reason codes.
  - Added 26 focused tests covering the join, point-in-time entry state and late
    revisions, absent features and unmeasured outcomes, undefined R, open and
    late-closing trades, unmatched entries and accountings, duplicate trade
    references, instrument/side and provenance mismatches, deterministic
    ordering and digests, record round trips, tamper rejection, narrowed
    definitions, the coverage census, NumPy handoff, and the empty dataset.
    Focused dependency regressions pass with 222 tests; the complete Python
    3.12 suite passes with 2615 tests.
  - **EPIC T integration review.** No defect in this ticket; its narrowed
    definition surfaced one in BTC-192, which read `net_pnl` and `r_multiple`
    out of a row without requiring the dataset to declare them and reported the
    absence as an outcome BTC-165 could not measure. BTC-192 now fails closed
    the way BTC-187's Monte Carlo sampler and the model/human comparison
    already did. Long and short rows keep the BTC-165 signs of `net_pnl` and
    `r_multiple` into the comparison's win/loss classification. One
    non-blocking item is left with BTC-165's owner: `r_multiple` is the one
    accounting output resolved in the caller's ambient decimal context, so a
    dataset built under a narrowed precision carries a differently rounded R.
    Every other outcome is exact, no EPIC T restore path re-executes the
    accounting, and pinning that division is a repository-wide accounting
    convention change rather than a research-layer fix.

#### BTC-192 Create strategy comparison framework
- **Description:**
  Compare:

  - strategy_v1.0
  - candidate strategy versions
  - parameter sets
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-191
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/strategy_comparison.py` with feature
    `STRATEGY_COMPARISON` and policy version
    `STRATEGY_COMPARISON_FRAMEWORK_V1`. The explicit baseline and every
    candidate are keyed by their persisted `strategy_version` and
    `parameter_set_id`, so the framework can compare strategy versions,
    parameter sets within one version, or both without silently merging their
    evidence.
  - The two direct dependency evidence modes remain separate. BTC-180
    historical runs are accepted only when bar digest, symbol, evaluated
    period, starting capital, effective costs, and selected cost rung agree;
    their common scope identifier is derived from that evidence. BTC-191
    paper datasets require a caller-declared campaign/window identifier and
    must also agree on extraction time and all BTC-165 accounting conventions.
    Historical and paper evidence cannot be blended in one report.
  - Metrics use only final closed BTC-165 outcomes: trade/closed/open counts,
    measured and unmeasured coverage, net P&L, expectancy, win rate, gross
    profit/loss, profit factor, and mean R. BTC-180 open trades remain counted
    but are excluded from quality metrics; BTC-191 `net_pnl` and `r_multiple`
    cells are read directly rather than reconstructed from prices.
  - Missing evidence is never zero-filled. Empty samples and unmeasured
    outcomes retain explicit counts and `None`; profit factor distinguishes no
    measured trades, no losses, and all-flat samples. Every candidate-minus-
    baseline absolute delta is `AVAILABLE`, `BASELINE_UNAVAILABLE`,
    `CANDIDATE_UNAVAILABLE`, or `BOTH_UNAVAILABLE`.
  - Arithmetic uses a fixed 60-digit Decimal context and persisted 12-decimal
    rate convention. Input order cannot change output: the exact baseline is
    first and candidates sort by strategy and parameter identity. Duplicate
    identities, duplicate source IDs, an absent baseline, mixed evidence
    modes, and incomparable scopes fail closed.
  - Reports embed the complete BTC-180 or BTC-191 records together with source
    IDs/digests, metric policy, comparison scope, identities, derived metrics,
    deltas, configuration metadata, and reason codes. Restoration replays the
    authoritative source records and rebuilds the report, rejecting source,
    metric, delta, identity, scope, or policy tampering.
  - Results are `RESEARCH_ONLY_NOT_PRODUCTION`; BTC-193 is persisted as the
    required promotion boundary, and the framework has no configuration or
    live-strategy mutation path.
  - Added 12 focused tests covering strategy-version and parameter-set
    comparisons, authoritative backtest and paper outcomes, deterministic
    ordering, exact deltas, empty/missing metrics, paper scope declarations,
    like-for-like backtest guards, mixed-mode rejection, duplicate identities,
    record round trips, tamper rejection, and the promotion boundary. Focused
    backtest/research regressions pass with 356 tests; the complete Python 3.12
    suite passes with 2746 tests.
  - **EPIC T integration review.** Two defects, both fixed in `18f0358`. The
    profit factor took the magnitude of the gross loss with `abs`, which rounds
    in the caller's ambient decimal context, before handing it to the `_ratio`
    helper that pins an explicit 60-digit context, so one set of BTC-191
    outcomes produced two profit factors and two evidence digests and a valid
    record failed restoration with a tampering-shaped error; BTC-193 embeds and
    replays this report, so sound promotion evidence would have been rejected
    as tampered. `copy_abs` now takes the magnitude without rounding, and no
    value changes at the default context. Separately, the metric columns were
    read inside a `try/except KeyError` returning `None`, so a BTC-191 dataset
    that never declared `net_pnl` or `r_multiple` was summarized as a strategy
    whose every closed trade went unmeasured, raising
    `STRATEGY_COMPARISON_UNMEASURED_OUTCOMES` with no BTC-165 reason code to
    cite; `STRATEGY_COMPARISON_REQUIRED_PAPER_OUTCOMES` now requires the
    columns the metrics read. One non-blocking item is left with this ticket's
    owner: paper comparison scope stays caller-declared, so the epic's own
    BTC-190 coverage evidence does not constrain which trades an arm contains.
    Summed closed-trade net P&L reconciles exactly with the BTC-180 NAV change
    under fees, slippage, and funding.

#### BTC-193 Implement controlled strategy promotion process
- **Description:**
  Workflow:

  ```text
  Current Production Version
          ↓
  Paper Trade Data
          ↓
  Research
          ↓
  Candidate Version
          ↓
  Historical Backtest
          ↓
  Walk-Forward Test
          ↓
  Robustness Tests
          ↓
  Manual Approval
          ↓
  New Production Version
  ```

  ### Rule

  The live strategy may **not self-modify automatically**.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-182, BTC-185, BTC-189, BTC-192
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/research/strategy_promotion.py` with feature
    `CONTROLLED_STRATEGY_PROMOTION`, policy version
    `CONTROLLED_STRATEGY_PROMOTION_V1`, exact-identity evidence policy
    `EXACT_IDENTITY_REPLAYABLE_EVIDENCE_CHAIN_V1`, explicit manual approval
    policy `EXPLICIT_MANUAL_HUMAN_DECISION_V1`, and deployment policy
    `RECORD_ONLY_NO_CONFIG_MUTATION_V1`.
  - `prepare_strategy_promotion()` composes the existing authoritative owners
    instead of recalculating their metrics. A complete packet requires a
    BTC-192 paper-trade comparison, both BTC-189 predictor-diagnostic and
    component-ablation reports, a BTC-192 historical-backtest comparison, a
    standalone BTC-182 walk-forward validation, and at least one BTC-185
    threshold-robustness sweep.
  - Every stage is bound to the exact current-production and candidate
    `config_version`, `strategy_version`, and `parameter_set_id`. The paper and
    historical comparisons must use their correct evidence modes, current
    production must be their explicit baseline, the candidate must be present,
    and research/walk-forward/robustness provenance must match the candidate.
  - The roadmap and Rulebook specify no automatic statistical promotion
    threshold, so BTC-193 does not invent one or reinterpret dependency
    metrics. A complete packet always stops at `AWAITING_MANUAL_APPROVAL`.
    `record_manual_promotion_decision()` requires an explicit approve/reject
    decision, named approver, UTC decision time, and rationale tied to the
    packet's content-addressed ID.
  - Approval produces an immutable `PROMOTED` record whose resulting production
    identity is the candidate; rejection produces `REJECTED` and retains the
    current identity. Both outcomes persist configuration identities, the full
    replayable evidence chain, decision metadata, policy versions, and reason
    codes. Neither path writes, swaps, or reloads live configuration, and every
    final record states `config_mutation_performed = false`.
  - Packet, manual-decision, and final-record restoration reject missing,
    substituted, reordered, or edited evidence and derived-outcome tampering.
    Robustness inputs sort deterministically and duplicate report or parameter
    coverage fails closed.
  - Added 11 focused tests covering the complete workflow, deterministic
    evidence handling, missing evidence, version and mode mismatch, explicit
    manual approval and rejection, UTC/manual metadata, cross-packet decision
    reuse, record-only deployment behavior, deterministic round trips, and
    tamper rejection. Dependency-focused regressions pass with 175 tests; an
    isolated Python 3.12 HEAD-plus-BTC-193 suite passes with 2757 tests.
    Implementation commit:
    `bc5dda69bfe8c6ef4b0384e9fa9c147857c2f4fb`.
  - **EPIC T integration review.** No defect. The packet binds every stage to
    the exact candidate identity, the record-only deployment policy holds --
    no module in the epic reads, writes, or reloads live configuration -- and
    BTC-191 evidence survives byte-identically into the packet record. Two
    non-blocking observations are left with this ticket's owner. The packet
    reason codes are a fixed tuple, so they assert
    `STRATEGY_PROMOTION_EVIDENCE_CHAIN_COMPLETE` even when both comparisons
    contain zero trades; the causes are not lost, because the embedded BTC-192
    records still carry `STRATEGY_COMPARISON_NO_TRADES`, but nothing lifts them
    to the packet's own summary. And identity binding is not scope binding: the
    walk-forward, robustness, and historical evidence must belong to the
    candidate but need not cover comparable periods or bars.

## EPIC U — Manual Trade Tracking

#### BTC-200 Implement recommendation decision journal
- **Description:**
  Decisions:

  ```text
  APPROVED
  REJECTED
  MODIFIED
  MISSED
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170, BTC-172
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/journal/decision_journal.py` with
    `journal_recommendation_decision()`, policy version
    `RECOMMENDATION_DECISION_JOURNAL_V1`, and the new `btc_predictor.journal`
    package for EPIC U. A decision is a statement about an advisory, not about
    a trade.
  - **The BTC-017 manual trade journal could not hold this record.** Its
    `manual_decision` vocabulary (`FOLLOWED`, `OVERRIDDEN`, `SKIPPED`,
    `MANUAL_ONLY`) is checked in the database and does not contain the four
    required decisions, and every other column of that table describes a fill.
    `REJECTED` and `MISSED` advisories produce no fill at all. Migration
    `0022_decision_journal` adds `portfolio.recommendation_decisions`; BTC-017
    keeps its own table and vocabulary for BTC-202's actual executions.
  - Each row carries the BTC-166 provenance triple taken from
    `LifecycleProvenance`, the authoritative owner, plus `config_version`, so a
    decision is attributable to the exact strategy version and parameter set
    that produced the advisory rather than to whatever is configured when the
    row is read. A decision whose provenance or config identity disagrees with
    the advisory is refused.
  - The canonical BTC-172 recommendation document is stored verbatim with a
    SHA-256 digest over those exact bytes. A decision is only auditable against
    what the operator was shown, so restoration replays the stored document
    through `advisory_source_from_json()` and rejects tampered, re-encoded, or
    noncanonical bodies rather than trusting the entry to describe itself.
  - Decisions the advisory cannot support are refused. `MODIFIED` names which
    advised values were departed from, requires the advisory to have stated
    them, and stores them in canonical field order so identical modifications
    record identically. Neither `MODIFIED` nor `MISSED` is accepted against an
    advisory whose action carries no order, because there is nothing to modify
    or to miss. The advised action itself is not modifiable: taking a different
    action is a rejection of the advised one.
  - Chosen values are deliberately not recorded here; actual entry, size, stop
    and exit remain BTC-202's scope, and discretionary reason codes remain
    BTC-201's, so `note` is uninterpreted single-line text in V1.
  - `decided_at` must be UTC and may not precede the advisory's evaluation
    time, enforced both in the writer and as a database check; the FK to
    `signals.recommendations` is `ON DELETE RESTRICT` because a decision
    without its recommendation is unattributable, and one advisory carries at
    most one recorded disposition.
  - Fifty-two focused tests cover the four decisions, deterministic records and
    digests, both advisory input forms, provenance and config-identity
    matching, point-in-time ordering, `MODIFIED` and `MISSED` semantics, note
    validation, exact row/column mapping, and replay against tampering. The
    complete Python 3.12 suite passes with 2813 tests.
    Implementation commit:
    `b833f81fe8c6773f173618c3040ecd297a7dbb52`.

#### BTC-201 Add discretionary reason codes
- **Description:**
  Examples:

  ```text
  MACRO_CONCERN
  ENTRY_TOO_EXTENDED
  LOW_PERSONAL_CONFIDENCE
  ALREADY_EXPOSED
  UNAVAILABLE_TO_TRADE
  MODEL_DISAGREEMENT
  OTHER
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-200
- **Priority:** P1
- **Complexity:** XS
- **Risk:** Low.
- **Implementation Notes:**
  - Extended the BTC-200 recommendation decision journal with the versioned
    discretionary-reason policy `DISCRETIONARY_REASON_CODES_V1`. The V1 closed
    vocabulary is `MACRO_CONCERN`, `ENTRY_TOO_EXTENDED`,
    `LOW_PERSONAL_CONFIDENCE`, `ALREADY_EXPOSED`, `UNAVAILABLE_TO_TRADE`,
    `MODEL_DISAGREEMENT`, and `OTHER`.
  - `journal_recommendation_decision()` accepts zero or more discretionary
    reasons for every decision type. The ticket defines neither
    decision-specific requirements nor an `OTHER`-note requirement, so V1 does
    not invent either rule; `note` remains optional single-line text.
  - Reasons are validated against the declared vocabulary, duplicates and
    malformed sequences fail closed, and accepted sets are persisted in the
    declared policy order. Equivalent sets therefore produce identical records
    regardless of caller order.
  - Discretionary reasons remain distinct from the journal's model/system
    `reason_codes`. Records and database rows persist both the ordered
    `discretionary_reason_codes` and
    `discretionary_reason_policy_version`, and replay rejects unknown,
    reordered, duplicated, or policy-substituted values.
  - Migration `0023_discretionary_reasons` adds the two non-null columns to
    `portfolio.recommendation_decisions`. Existing BTC-200 rows are backfilled
    explicitly with the V1 policy and an empty reason list; migration-only
    server defaults are then removed so new writes must supply both fields.
  - Ten focused test functions covering twenty cases exercise the complete
    vocabulary, all four decision types, optional reasons, canonical ordering,
    validation, persistence, deterministic replay, and tamper rejection.
    Journal/schema/migration tests pass with 103 tests, and the complete Python
    3.12 suite passes with 2833 tests while treating `RuntimeWarning` as an
    error. Implementation commit:
    `3d709621518ad526186071158f522582e1c1f53c`.

#### BTC-202 Implement actual trade entry
- **Description:**
  Record real manual execution.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-200, BTC-201 and completed manual-trade journal schema
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/journal/actual_trade.py` with
    `record_actual_trade_entry()`, deterministic replay through
    `actual_trade_entry_from_record()`, and policy version
    `MANUAL_EXECUTION_JOURNAL_V1`. Actual entry time, price, positive size and
    size unit are required; stop and the paired exit time/price remain explicit
    nullable facts and are never zero-filled.
  - A recommendation-linked fill must consume a self-validating BTC-200
    `RecommendationDecisionEntry`. Only `APPROVED` and `MODIFIED` decisions on
    an `ENTER` advisory can produce an actual trade entry, mapping respectively
    to the BTC-017 `FOLLOWED` and `OVERRIDDEN` vocabulary. Symbol, direction and
    chronology must agree with the stored advisory and decision; `REJECTED`,
    `MISSED`, non-entry advisories and mismatched attribution fail closed.
  - `MANUAL_ONLY` remains supported for real trades that did not originate in
    an advisory. Such rows deliberately persist no recommendation, strategy,
    config or decision metadata rather than assigning an unrelated current
    configuration after the fact. The schema's `SKIPPED` value is not emitted
    by the actual-execution writer because it describes no fill.
  - Linked execution rows snapshot the BTC-166 strategy/config identity, the
    BTC-200 decision timestamp, policy and reason codes, and the BTC-201
    discretionary-reason policy and ordered codes. `MODIFIED` executions also
    require the existing human-readable `override_reason`; the API derives the
    execution classification instead of accepting a potentially inconsistent
    caller value.
  - Migration `0024_actual_trade_entry` extends the BTC-017 table with the
    attribution and version fields. Existing rows retain nullable attribution
    under the explicit `MANUAL_EXECUTION_JOURNAL_LEGACY` marker; PostgreSQL
    checks enforce complete V1 fills, coherent exit pairs, event ordering and
    linked-versus-manual-only attribution for all new V1 rows.
  - Twenty-eight focused tests cover linked, modified and manual-only entries;
    config/reason persistence; advisory identity and time checks; finite
    positive values; explicit missing values; exit pairing; exact row mapping;
    deterministic replay; migration SQL; and tamper rejection. The focused
    journal/schema/migration suite passes with 132 tests, and the complete
    Python 3.12 suite passes with 2862 tests while treating `RuntimeWarning` as
    an error. Implementation commit:
    `4ae6c9a9c041e5172f2a3a994fda43489f04d43c`.

#### BTC-203 Build Model vs Human comparison
- **Description:**
  Compare:

  | Metric | Model Paper | Human Actual | Model + Human |
  |---|---:|---:|---:|
  | Trades | | | |
  | Win rate | | | |
  | Avg R | | | |
  | Profit factor | | | |
  | Max DD | | | |
  | Sharpe | | | |
  | Return/trade | | | |
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-191, BTC-202
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/reporting/model_human_comparison.py` with policy
    version `MODEL_HUMAN_COMPARISON_V1`. The report consumes one self-validating
    BTC-191 paper-trade outcome dataset and zero or more self-validating BTC-202
    actual-trade records, embeds those complete sources, and supports
    deterministic replay through `restore_model_human_comparison()`.
  - The three columns have explicit V1 membership. `MODEL_PAPER` contains every
    completed paper outcome in the campaign, `HUMAN_ACTUAL` contains every
    supplied actual execution including open and `MANUAL_ONLY` trades, and
    `MODEL_PLUS_HUMAN` is the recommendation-linked subset of the actual arm.
    A manual-only trade is therefore never silently attributed to the model.
  - All required quality metrics use normalized closed-trade returns. Paper
    return is authoritative BTC-165 net P&L divided by entry notional. BTC-202
    records no live fee or funding fields, so actual return is explicitly the
    gross directional entry-to-exit price return; V1 persists that limitation
    as `ACTUAL_GROSS_DIRECTIONAL_PRICE_RETURN_NO_RECORDED_COSTS_V1` rather than
    estimating costs. Profit factor is gross positive normalized return over
    absolute gross negative normalized return.
  - Average R reads the BTC-165 R multiple for paper trades and uses the
    recorded actual entry, exit and adverse initial stop for human trades.
    Open trades, absent stops, non-adverse stops, and BTC-165 unmeasured cells
    retain explicit unavailable statuses and are never zero-filled.
  - Max drawdown is the peak-to-trough decline of the closed-return sequence
    under the declared full-notional compounding convention. Sharpe is the
    unannualized mean closed-trade return divided by its sample standard
    deviation at zero risk-free rate. Both preserve explicit no-sample,
    missing-return, zero-dispersion and non-positive-equity states. All derived
    arithmetic uses a fixed 60-digit Decimal context and 12-decimal output.
  - Comparisons are point-in-time at the BTC-191 extraction timestamp. Actual
    records journaled later are rejected; campaign evidence must use one
    symbol; linked actual trades must match a unique paper recommendation,
    symbol, direction, and config/strategy/parameter identity; and duplicate
    records or linked recommendation IDs fail closed. BTC-201 discretionary
    reason codes and their policy remain embedded in the actual sources and
    normalized outcomes.
  - Reports persist every metric and availability policy, canonical trade
    order, configuration metadata, reason codes, source records, comparison
    ID, and SHA-256 evidence digest. Restoration replays both upstream owners
    and rebuilds all three arms, rejecting policy, source, metric, membership,
    reason-code, ordering, or digest tampering.
  - Twenty-five focused tests cover the three arm definitions, all seven
    requested metrics, long/short R math, open and missing evidence, empty
    samples, cost-policy visibility, point-in-time and comparability guards,
    deterministic input ordering, record inputs, Decimal-context independence,
    round trips, and tamper rejection. Focused dependency/reporting regressions
    pass with 203 tests, and the complete Python 3.12 suite passes with 2887
    tests while treating `RuntimeWarning` as an error. Implementation commit:
    `e425afb2c819eea38fc341d9b92cfc2ee5b3c2ac`.

## EPIC V — Reporting & Monitoring

#### BTC-210 Create daily system status report
- **Description:**
  Show:

  - latest data timestamp
  - data-quality status
  - current regime
  - active setup
  - current recommendation
  - paper portfolio status
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170, BTC-172
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `btc_predictor/reporting/daily_status.py` with versioned
    `DAILY_SYSTEM_STATUS_REPORT_V1` plain-text output. The report is a
    presentation boundary: regime, setup, and action come directly from the
    validated BTC-170 advisory; the report does not create a second decision
    path.
  - Latest-data time is an explicit UTC point-in-time input and must not be
    later than the recommendation evaluation time. Its factual source ID is
    retained without implying that the source is canonical, because BTC-019's
    production reference remains unresolved and V1 fallback splicing is
    prohibited.
  - OHLCV and derivatives quality reports are normalized into a stable,
    component-sorted `PASS`/`FAIL` summary. Failed component reason codes are
    retained and must agree with the advisory's persisted
    `DATA_QUALITY_FAIL` evidence; a failed report cannot coexist with an
    `ENTER` or `ADD` action.
  - Paper status composes the BTC-160 account and zero or more BTC-150 current
    lifecycle snapshots into explicit `ACTIVE_FLAT`, `ACTIVE_MONITORING`,
    `ACTIVE_OPEN`, or `ARCHIVED` states. Existing-position actions require an
    open lifecycle, and account/lifecycle configuration, symbol, direction,
    and accepted or rejected transition times are checked against the current
    advisory.
  - The complete BTC-170 advisory, BTC-172 canonical recommendation JSON,
    account, lifecycle records, data-source provenance, component quality
    codes, strategy/config/parameter identity, output reason codes, and body
    are retained by `as_record()`. `daily_system_status_from_record()` restores
    every upstream owner and rejects source, summary, body, JSON, metadata, or
    ordering drift.
  - Input mappings and lifecycle sequences are canonically sorted, source
    identifiers are single-line validated, and missing optional portfolio
    values display as `N/A`; no runtime clock, random ID, locale-dependent
    formatting, or silent numerical zero-fill is introduced.
  - Thirteen focused tests cover all six requested report fields, clean and
    failed quality, monitoring and open portfolio states, canonical ordering,
    complete provenance/config/reason persistence, exact replay, tamper
    rejection, owner identity, point-in-time checks, lifecycle consistency,
    and injection guards. Focused dependency regressions pass with 298 tests,
    and the complete Python 3.12 suite passes with 2900 tests while treating
    `RuntimeWarning` as an error. Implementation commits:
    `3a878aa6d2f0b12c294cb9eed194905a2819d5aa` and
    `93a2082b67e78d109fab49cc22710a5a9660ecb6`.

#### BTC-211 Create weekly strategy report
- **Description:**
  Show:

  - regime changes
  - setup changes
  - price levels
  - current paper trades
  - risk
  - recent score movement
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170..172, BTC-210
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/reporting/weekly_strategy.py` with versioned
    `WEEKLY_STRATEGY_REPORT_V1` plain-text output. It is a presentation
    boundary over BTC-210 daily status snapshots and BTC-171 current-position
    reports; it does not reclassify regimes/setups, recalculate strategy
    scores, choose actions, or replace the shared risk owner.
  - The report uses a deterministic rolling seven-day window ending at the
    latest supplied daily status. Daily inputs are canonically time-sorted,
    timestamps and recommendation IDs must be unique, and all observations
    must retain one market, timeframe, config identity, and paper-account
    identity. The report states its first available observation and count so
    sparse history is visible rather than implied complete.
  - Every observed regime and setup transition is linked to the previous and
    current recommendation IDs. Recent movement covers Trend, Regime, Flow,
    Positioning, Volatility, Structure, Entry Conviction, Hold, and Add scores
    as first-to-current exact Decimal deltas. A one-observation window or an
    unavailable optional score retains an unavailable baseline/delta and
    renders `N/A`; it is never converted to zero or described as stable.
  - Current entry zone, invalidation, and initial stop come directly from the
    latest BTC-170 advisory. Active stop, candidate stop, mark, current paper
    trade economics, and risk-at-stop come directly from BTC-171 reports. Each
    latest open BTC-150 lifecycle must have exactly one matching current
    position report, whose advisory and mark time must match the latest
    BTC-210 snapshot.
  - Recommendation risk remains distinct from current-position risk. The
    current risk amount, NAV fraction, configured maximum, persisted
    convention, verdict, and owner reason codes are displayed without
    aggregating a second risk formula. Mark/source provenance is retained as
    factual evidence and does not promote any provider to a canonical price
    role while BTC-019 remains unresolved.
  - `WeeklyStrategyReportResult.as_record()` retains all BTC-210 records
    (including their BTC-172 canonical advisory JSON), all BTC-171 records,
    computed transition and score summaries, complete config/source/reason
    provenance, the versioned window, and the exact rendered body.
    `weekly_strategy_report_from_record()` restores every owner and rejects
    source, ordering, summary, metadata, body, or extra-field drift.
  - Report-level reason codes distinguish changed, stable, and insufficient
    regime/setup history; open versus absent paper trades; and available
    versus unavailable risk. Ten focused tests cover all six requested report
    areas, transition ordering, score movement and missing-data semantics,
    current-position coverage, point-in-time linkage, canonical ordering,
    exact replay, tamper rejection, account identity, and the seven-day bound.
    Focused dependency regressions pass with 356 tests, and the complete
    Python 3.12 suite passes with 2910 tests while treating `RuntimeWarning` as
    an error. Implementation commit:
    `c9929906f9114a5606ac43b63f9bad8192339d90`.

#### BTC-212 Create alerts
- **Description:**
  Potential alerts:

  ```text
  ACTIONABLE_SETUP
  ENTRY_ZONE_REACHED
  NEW_ADD_SIGNAL
  STOP_MOVE
  TRIM_SIGNAL
  EXIT_SIGNAL
  DATA_QUALITY_FAIL
  STRESS
  EUPHORIA
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-170..172, BTC-210
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added `btc_predictor/reporting/alerts.py` with versioned `ALERTS_V1`
    batches, canonical schema `ALERTS_JSON_V1`, and media type
    `application/json`. Alerts are a notification boundary over existing
    owners: the module never re-scores a setup, re-derives data quality, or
    chooses a trading action.
  - Every alert type is projected from one already validated owner.
    `ACTIONABLE_SETUP`, `NEW_ADD_SIGNAL`, `TRIM_SIGNAL`, and `EXIT_SIGNAL`
    come from the persisted BTC-170 action; `STOP_MOVE` comes from the BTC-156
    trailing-stop `advanced` transition carried by a BTC-171 report;
    `DATA_QUALITY_FAIL` comes from the BTC-210 component summary; `STRESS` and
    `EUPHORIA` come from the typed hard-flag feature results. Each alert
    retains its source feature ID and that source's own reason codes.
  - Emission order is the alert order documented by this ticket, and position
    reports are canonically ordered by their BTC-150 lifecycle record, so an
    identical evaluation always produces byte-identical output. The body is
    canonical JSON with sorted keys, compact separators, ASCII escaping, and
    no NaN/infinity, runtime clock, random identifier, or binary float.
  - `ENTRY_ZONE_REACHED` requires one explicit point-in-time price observation
    whose timestamp equals the batch `as_of`. Membership is an exact inclusive
    Decimal comparison against the advisory's own entry zone. When a zone
    exists but no observation is supplied, the batch records
    `ALERTS_ENTRY_ZONE_PRICE_MISSING` and `complete = False`; a missing price
    is never treated as "zone not reached". The observation's source ID is
    retained as factual provenance only and promotes no provider to a
    canonical price role while BTC-019 remains unresolved.
  - Config identity is checked across the BTC-210 status, every BTC-171
    report, and both hard flags. The batch `as_of` must equal the daily
    status timestamp, each current open lifecycle must be covered by exactly
    one BTC-171 report, and each report's advisory and mark time must match
    the daily status. Incomplete stress or euphoria inputs surface
    `ALERTS_STRESS_SOURCE_INCOMPLETE` / `ALERTS_EUPHORIA_SOURCE_INCOMPLETE`
    and clear `complete` instead of being silently zero-filled.
  - `AlertsResult.as_record()` retains the complete BTC-210 record (including
    its embedded BTC-172 advisory JSON), all BTC-171 records, the stress and
    euphoria records, the price observation, every alert with its details,
    config identity, output reason codes, and the exact body.
    `alerts_from_record()` restores every owner and rejects alert, body,
    reason-code, completeness, source, ordering, or extra-field drift; result
    reason codes must also belong to `ALERTS_REASON_CODES`.
  - Scope decision: an alert batch is a projection of one evaluation plus the
    transitions its owners already compute (`STOP_MOVE`). The ticket does not
    define cross-evaluation alert history, so `NEW_ADD_SIGNAL` is scoped to
    the current persisted `ADD` action and no second state history is
    invented here. Each alert carries `alert_type`, `as_of`, and
    `recommendation_id`, which is sufficient for a delivery layer to suppress
    repeats.
  - Fifteen focused tests cover all nine alert types, the quiet no-alert
    state, exact entry-zone bounds, missing-price and incomplete-flag
    surfacing, canonical ordering and input-order independence, complete
    provenance and config persistence, exact replay, alert/body/reason/source
    tampering, open-position coverage, config and point-in-time drift, forged
    owner identity, and injection-prone provenance. Focused dependency
    regressions pass with 61 tests, and the complete Python 3.12 suite passes
    with 2925 tests while treating `RuntimeWarning` as an error.


## V2 Quant-Refactor Completion Gate

The project must not proceed to trust paper/backtest performance until all of the following are true:

- [ ] BTC-019 production canonical reference is explicitly approved and versioned
- [x] BTC-042 quant package exists and numerical conventions are documented
- [x] BTC-043 rolling/statistics NumPy parity passes
- [x] BTC-044 nonlinear transformations reproduce existing score behavior
- [x] BTC-045 distance engine is validated and compatibility mode retained
- [x] BTC-046 vectorized scoring reproduces completed composite scores
- [x] BTC-047 risk/portfolio mathematics is the single shared implementation
- [x] BTC-048 point-in-time Feature Matrix is reproducible
- [x] BTC-049 parity, look-ahead, NaN/inf, and batch-vs-single tests pass
- [x] BTC-098 Structure Score v1.2 removes R/R and repeated Confluence from outer weighting
- [x] BTC-129 factor-overlap audit confirms de-nested Entry/Hold/Add contracts
- [ ] Existing completed feature APIs continue to reproduce historical fixtures
- [ ] No completed ticket is reclassified from DONE solely because its internals were migrated
- [ ] Any intentional strategy-behavior change receives a new strategy/config version


## EPIC W — Testing

#### BTC-220 Unit tests for feature calculations
- **Description:**
  Complete the ticket scope for feature/domain calculations and ensure migrated
  NumPy kernels remain covered through BTC-049 parity tests.

  Include focused unit tests for:

  - quant transforms
  - vectorized scoring
  - distance calculations
  - risk mathematics
  - portfolio mathematics
  - domain wrappers and reason-code behavior
  - de-nested Entry / Structure / Hold / Add score contracts
  - prohibited mechanical nesting / weight-sum validation
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-049 for quant parity coverage
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Scope was established by measuring branch coverage of the ticket's named
    owners rather than by re-listing already-covered behaviour. Existing
    BTC-042..049 parity, BTC-098, and BTC-129 suites already covered the
    happy-path mathematics, so this ticket closed the remaining gaps. Combined
    statement/branch coverage across the fourteen scoped modules moved from
    93% to 99%; no existing test was weakened or removed.
  - `quant/comparisons.py` had no focused test at all despite owning every
    tolerance-aware hard decision in `risk.budget`, `risk.sizing`,
    `risk.tranches`, `risk.exposure`, `risk.invalidation`, and
    `levels.clustering`. Added `test_quant_comparisons.py` pinning the frozen
    `DECISION_COMPARISON_V1` policy version, the default tolerance's identity
    with `PARITY_TOLERANCE`, the three-valued ordering, absolute and relative
    band collapse, band selection by the larger operand magnitude,
    antisymmetry, helper/compare agreement, inclusive-versus-strict disagreement
    inside the band, and binary-float artifact immunity (`0.1 + 0.2` compares
    equal to `0.3`). Booleans, non-finite values, non-numerics, and a
    non-`DecisionTolerance` tolerance are all rejected; a zero tolerance
    restores exact `Decimal` comparison.
  - `features/_scoring.py` — the single Decimal/float64 seam all nine v1.2
    domain score wrappers delegate through — also had no focused test. Added
    `test_feature_score_boundary.py` proving the boundary delegates to the
    authoritative `quant.scoring.weighted_score` owner rather than
    reimplementing it, that the persisted Decimal scale follows the exact
    `weight * value` template, that `component_ids` controls evaluation and
    output order, and that a missing component (including a NaN reaching the
    boundary) is surfaced as `None` with the component named in
    `missing_components` and never contributes zero. A zero component score is
    explicitly distinguished from a missing one. Every v1.2 contract in
    `scoring_contracts` is exercised through the default weight-sum policy,
    with unconstrained totals opt-in and negative weights rejected.
  - Added the untested accumulation and result-rejection contracts in
    `quant/arrays.py`: `stable_row_sum` is exact where naive accumulation
    cancels, returns a float for a vector and one aggregate per matrix row
    without flattening, supports empty input, requires explicit NaN
    propagation, and rejects rank > 2 and totals outside the finite float64
    range; `reject_infinite_result` admits documented NaN while
    `reject_non_finite_result` admits neither.
  - Pinned the scalar-parameter contracts shared by the transform, distance,
    and scoring kernels — booleans, array-shaped scalars, complex, string,
    non-finite, and unrepresentable-integer parameters all fail fast — plus
    ragged-input rejection, `percentile_to_health` domain bounds, the
    `mode`/`atr` pairing rules in `entry_distance_score` and
    `cluster_distance_matrix`, ATR shape alignment, the ordered
    full/zero score interval, the empty component axis, and the
    `expected_weight_total` / `weight_tolerance` policy scalars.
  - Risk and portfolio mathematics: added the scalar single-tranche
    `risk_at_stop` path (equal to its own tranche contribution and to the
    single-element vector), and rank > 2 and ragged-input rejection for both
    the risk and portfolio input coercers.
  - Domain wrappers: Entry Conviction, Entry Action, Hold, Add, and Structure
    records now reject identity, version, parameter-status, contribution-set,
    missingness, completeness, threshold-set, and config-metadata drift.
    Weight validation is pinned for exact component membership, the
    `0.000001` sum tolerance (accepted at the tolerance, rejected at ten times
    it), non-negativity, and non-numeric or non-finite weights. Entry action
    thresholds must be exactly the contract set, `watch_min >= ignore_below`,
    and strictly increasing.
  - Structure: added coverage of the previously untested piecewise component
    curves — entry location saturating at 100 at or inside the full-score
    distance and at 0 at or beyond the zero-score distance, monotone in
    between; and R/R quality across all four bands with the bands taken from
    the supplied parameters rather than hardcoded. Also covered the cluster
    input adapters (bare mapping, `as_record()` sources, rejection of anything
    else), the level-strength adapter treating an incomplete or scoreless
    result as missing rather than zero, and unit-interval weight and fraction
    validation.
  - Reason codes: added engine identity, source-version, source-completion,
    config-metadata, and derived-state validation; source and signal-reason
    type guards; bounded code and component lengths; and the observable setup
    behaviour (absent or unsupported setup vetoes and propagates; supported
    setup matching ignores case and surrounding whitespace).
  - Scoring contracts: an unknown composite is rejected by
    `expand_factor_paths`, `effective_weights`, and `audit_factor_overlap`
    rather than silently returning no paths.
  - Deliberately not covered: a small number of defence-in-depth guards that
    no public call can reach — the `RuntimeError` consistency assertions in
    `features/_scoring.py` and `features/structure.py`, the internal
    `_restore_output` shape/NaN assertions and the zero-scale interval guard
    in `quant/transforms.py`, and the reason severity and detail branches that
    `RecommendationReasonCode.__post_init__` already forecloses. Writing tests
    for these would require constructing states the public API cannot produce.
  - Added 233 focused cases. The full Python 3.12.14 suite passes with 3158
    tests, also passing with `RuntimeWarning` treated as an error; compileall
    passes.

#### BTC-221 Look-ahead bias test suite
- **Description:**
  Critical tests:

  - future bars unavailable
  - future ETF flows unavailable
  - future confirmed pivots unavailable
  - rolling normalization past-only
  - AVWAP anchors point-in-time valid
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-043, BTC-048, BTC-049
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - The required independent xHigh review passed after two review fixes; see
    the review record at the end of these notes.
  - Added the dedicated cross-cutting suite `test_look_ahead_bias.py` for the
    five critical areas. The owner suites already prove that each engine
    filters its own inputs, so this ticket pins the stronger replay property
    those filters exist for under Rulebook v1.2 section 3A.2: an as-of result
    computed from the full universe is identical to the same result computed
    from a universe physically truncated to what was available, and appending
    future observations never rewrites an earlier decision. Both halves are
    asserted, because truncation equivalence alone cannot see an engine that
    ignores its cutoff, and append invariance alone is satisfied vacuously by
    an engine that ignores its inputs.
  - Future bars: canonical market bars at a cutoff carry that cutoff as their
    availability, expose only sessions closed and ingested by it, never emit a
    partially observed bucket (a month is withheld until its final hour is
    ingested, and an hour published before it closes cannot complete a day or
    a week), grow strictly as a prefix across decisions, and are unchanged
    both by appended future hours and by truncating the hourly universe.
    Realized volatility repeats the same three-way comparison.
  - Future ETF flows: the 5-day, 20-day, and acceleration records at a
    decision equal those built from a universe truncated to
    `available_at <= as_of`; unpublished observation dates never move an
    earlier decision; a restated revision moves only decisions taken after it
    is published; a window taken before first publication is reported
    `ETF_FLOW_INPUT_MISSING` with `None` sums rather than zero; and the
    selected observation date never runs past the latest available row.
  - Future confirmed pivots: the expected weekly and monthly swings are pinned
    with their level timestamps, prices, and detection times; a pivot is
    unavailable until its confirmation window closes; a pivot whose confirming
    bar is backfilled late waits for that ingestion and records the ingestion
    time as `detected_at`; confirmed sets grow monotonically and are never
    restated; and every emitted level satisfies
    `level_timestamp < detected_at <= as_of`.
  - Rolling normalization: prior-window kernels exclude the current
    observation (a value far outside its own prior window reaches the
    percentile and normalization ceiling and a z-score above `sqrt(window)`),
    a degenerate prior window is missing rather than zero, no kernel —
    prior-window or inclusive — lets a later observation change an earlier
    output, and every streaming prefix reproduces the batch result exactly.
    The Decimal domain wrappers keep warm-up as `None`, and
    `volatility_percentile` ranks against strictly prior history and is
    unchanged by a future result.
  - AVWAP anchors: an anchor inherits its confirmed pivot's detection time and
    source provenance; an anchor backdated before its source is rejected; the
    VWAP is incomplete with `ANCHORED_VWAP_ANCHOR_NOT_DETECTED` and a `None`
    value before detection; accumulation covers exactly the bars closed and
    ingested by the decision, excluding a session published while still
    running; coverage grows monotonically; and appended future bars change
    nothing.
  - A cross-cutting replay evaluates all five owners at six decision
    timestamps spanning both weekly pivot confirmations and asserts that the
    full universe, the future-polluted universe, and the truncated universe
    produce identical records. A companion test asserts the same records for
    reversed input ordering.
  - Suite value was measured rather than assumed: twelve single-line
    look-ahead defects were injected into the owners and the suite re-run.
    Nine are caught. The three that are not are equivalent mutants on a
    contiguous canonical series — `levels/swing.py` gates emission both by
    filtering `_available_bars` and by its `detected_at > signal_time` check,
    and for a gap-free series with monotone ingestion the filter removes only
    a suffix, so each guard alone reproduces the other's admitted candidate
    set. The observable contract is still pinned: mutating `_swing_detected_at`
    to time a level from its close and ignore late ingestion is caught.
  - Two observations were recorded for the independent review rather than
    silently resolved. First,
    `features/volatility.py::_available_daily_bars` admits a daily bar whose
    session has not closed when its `ingested_at` is early, unlike the swing
    and AVWAP readers, which require the session to have closed;
    `build_canonical_market_bars` never emits a partial bucket, so no
    behaviour was changed. Second, `levels/swing.py` treats the available bars
    as contiguous, so a bar backfilled into the middle of a series shifts the
    confirmation window onto non-adjacent neighbours. The review resolved the
    first and part of the second; see the review record below.
  - Added 35 focused cases. The full Python 3.12.14 suite passes with 3193
    tests, also passing with `RuntimeWarning` treated as an error; compileall
    passes.
  - **Independent xHigh review (2026-09-02):** the suite covers all five
    critical areas, its 35 cases pass, and no test encodes an incorrect
    contract. Both halves of the replay property are genuinely asserted and
    the discriminating cases in the normalization tests do separate a
    prior-window kernel from a self-inclusive one. Two look-ahead defects were
    confirmed by direct probe and fixed, both in the ticket's own critical
    areas, both latent today because no production decision path calls the
    affected owners and canonical bars carry uniform ingestion times.
  - **Review finding 1 (P2, fixed).** `features/volatility.py::_available_daily_bars`
    gated on `timestamp <= signal_time`, the only bar-availability filter in
    the repository that does not require the session to have closed. A daily
    bar published while its session ran therefore contributed an unfinished
    close to the return window, and the truncation-equivalence property this
    ticket pins was false for that owner: at a decision inside a running
    session the full universe returned `observation_time` one day ahead of the
    truncated universe. The filter now requires
    `next_bar_timestamp(timestamp, timeframe) <= signal_time`, matching the
    swing, AVWAP, volume-profile, breakout, reclaim, retest, and higher-low
    readers and BTC-080's stated contract of a completed observation. Four
    `test_volatility_features.py` cases whose fixture publishes a daily bar
    five minutes after the session opens had their decision time moved one day
    forward; every assertion in them is unchanged.
  - **Review finding 2 (P2, fixed).** `levels/swing.py::_swing_detected_at`
    derived a level's availability from the confirming bar alone. When any
    other bar in the confirmation window was ingested later, the emitted level
    claimed a `detected_at` earlier than the time the level was derivable, and
    that time moved *backwards* across decisions: with the week-5 bar
    backfilled five weeks late, the week-3 swing low reported `detected_at` at
    week 8 for three consecutive decisions and then restated it to week 7,
    four weeks before the window existed. Because AVWAP anchors inherit
    `detected_at` from their source level, the anchor and its VWAP became
    usable equally early, violating Rulebook v1.2 section 3A.2 for any
    consumer that replays persisted levels by availability.
    `_swing_detected_at` now takes the latest close-or-ingestion time across
    the whole window. On a contiguous series ingested in order this is the
    confirming bar, so canonical detection times are unchanged and no other
    test moved.
  - **Review limitation (P3, not fixed).** The implementer's second
    observation is only partly resolved. `detect_weekly_swing_levels` and
    `detect_monthly_swing_levels` still build the confirmation window from
    whatever bars are available, so a gap admits a window of non-adjacent
    bars; a level can still be emitted from such a window and then restated
    *forward* once the gap fills. That direction is not look-ahead, and
    requiring window contiguity would change which levels exist on gappy data,
    which is a strategy-semantics change belonging to the swing detector's
    owner rather than to this test ticket.
  - **Review regressions.** Added
    `test_realized_volatility_excludes_a_daily_session_that_has_not_closed`
    and `test_a_pivot_is_not_backdated_when_a_window_bar_is_backfilled_late`
    to `test_look_ahead_bias.py`. Both were confirmed to fail against the
    pre-fix owners and pass after. The suite is now 37 cases; the full Python
    3.12.14 suite passes with 3414 tests, also passing with `RuntimeWarning`
    treated as an error, and compileall passes.

#### BTC-222 Risk invariant tests
- **Description:**
  Verify:

  ```text
  No averaging down
  Stops never widen
  Risk-at-stop never exceeds limit
  No add when STRESS
  No add when CROWDING rule blocks
  No trade during DATA_QUALITY_FAIL
  ```
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added the dedicated cross-cutting suite `test_risk_invariants.py`. Each of
    the six invariants already has an owner suite proving that its own engine
    refuses a violating input, so this ticket pins the property those refusals
    exist for and no single owner can see: no path reaches a violating state.
    Every invariant is asserted at all three consumers rulebook 19 names -
    advisory gates, the BTC-150 ledger with its simulated executions, and the
    BTC-180 replay - and in both halves, because a refusal that still mutated
    the ledger would satisfy "refused" alone and an engine that refused
    everything would satisfy "unchanged" alone.
  - No averaging down: the weighted average entry may only move in the
    position's favour across an arbitrary long or short sequence of adds,
    trims and stop moves; disabling BTC-154's optional profitability gate does
    not open a path around BTC-151, and `no_average_down: false` is rejected by
    configuration; an add the gate permitted at the decision is cancelled when
    its fill bar gaps under the average, and the ledger refuses the same fill
    independently; the execution re-check judges the market reference rather
    than the slipped fill, so a buy that fills higher never reads as healthier
    than the market it filled in.
  - Stops never widen: the standing stop is monotone across mixed accepted and
    refused move sequences in both directions; a refused widening survives
    `position_event_records` replay and snapshot restore as a refusal; BTC-156
    and BTC-150 refuse the same loosening independently; and with tranches
    untouched a ratcheting stop can only lower BTC-146 risk at stop.
  - Risk-at-stop within the limit: BTC-144, BTC-142, BTC-145 and BTC-146
    compose so that a sized entry spends exactly its risk budget, swept across
    conviction bands and stop distances; the budget and exposure owners read
    one configured ceiling; a projected post-add book above the ceiling is
    refused by the gate, by the execution (which retains the gate's own reason
    code) and leaves the ledger unchanged; every permitted add in a size sweep
    leaves a realized book equal to the approved projection and within the
    ceiling; and a breach is reported with zero headroom rather than silently
    clipped.
  - No add when STRESS: the flag declares rulebook 24's `NO_ADD` effect and the
    BTC-150 `DEFENSIVE` state is where the ledger carries it - an otherwise
    perfect add is refused from both `OPEN_INITIAL` and `OPEN_ADDED`, only
    `RECOVER` restores it, and because BTC-180 routes every accepted add
    through `apply_position_event`, the same refusal applies on the replay
    path. Blocking new trades stays optional and versioned: the flag and the
    hard veto read the same `volatility_flags.stress.block_new_trades` field,
    and the unconditional `NO_ADD` effect does not depend on it.
  - No add when CROWDING blocks: the flag declares `NO_ADD`; rulebook 18.1
    requirement 6 ("Positioning is not crowded") is the named gate input where
    it lands, and the crowding reason codes persist with the refusal rather
    than being summarised away; a crowding-blocked add never fills, costs
    nothing, and still records the allocation it declined; severe crowding
    blocks a new trade at the hard veto with no configuration switch to
    disable it.
  - No trade during DATA_QUALITY_FAIL: swept over every recommendation action,
    a failure never yields `ENTER` or `ADD` while existing-position actions are
    preserved at warning rather than veto severity; the gate and the hard veto
    agree; the failure and its component evidence persist as ordered veto rows;
    an ordinary failure is not a forced liquidation; and the `ADD` to `HOLD`
    downgrade is what protects the book, since the requested add would have
    changed it.
  - A ten-bar BTC-180 replay proposes exactly the decisions the invariants must
    refuse or allow - an underwater add, a crowded add, a loosening trail, a
    tightening trail and a legitimate add - and the recorded evidence is walked
    to re-derive the average-entry and stop monotonicity, the per-refusal
    reason codes, and a reported risk-at-stop at every open bar. The run is
    deterministic and its record restores unchanged.
  - Suite value was measured rather than assumed: seventeen single-line
    invariant defects were injected into the owners (stop-widen guard off,
    average-down guard off, `DEFENSIVE` permitting `ADD`, the add re-check
    reading the slipped fill, the execution ignoring a blocked gate, the gate
    ignoring the risk ceiling or crowding, the data-quality gate passing
    through, the hard veto ignoring data quality, severe crowding or the stress
    policy, the risk ceiling always satisfied, trailing accepting a loosening,
    either flag losing its `NO_ADD` effect, sizing doubling the budget, and a
    trim re-basing the average entry) and the suite re-run. All seventeen are
    caught.
  - One observation is recorded for the independent review rather than silently
    resolved. Rulebook 24 gives STRESS an unconditional NO ADDING effect, but
    no module binds a `StressFlagResult` to an add decision: BTC-154's eight
    inputs have no stress input, and the implemented carrier is the BTC-150
    `DEFENSIVE` state, which BTC-180 exposes no action to enter. A
    stress-driven no-add therefore reaches a backtest only through whatever the
    strategy resolves into the gate's own inputs. Nothing was changed, because
    inventing that binding would be new strategy semantics; CROWDING has no
    such gap, since rulebook 18.1 requirement 6 names its gate input directly.
  - Added 59 focused cases. The full Python 3.12.14 suite passes with 3252
    tests, also passing with `RuntimeWarning` treated as an error; compileall
    passes.
  - **Independent xHigh review (2026-09-03):** all six named invariants are
    covered, the 59 cases pass, and no test encodes an incorrect contract. The
    both-halves discipline is real rather than decorative: `economics()` pins
    exactly the state a refusal must leave untouched, and the discriminating
    cases do separate a refusing engine from an engine that refuses
    everything. Suite value was re-measured independently of the implementer's
    seventeen: twenty-five further single-line defects were injected across
    the state machine, add execution, add requirements, data-quality gate,
    hard veto, trailing stop, risk exposure and the backtest engine, including
    both long/short asymmetries. All but the four below were caught. One
    review finding was confirmed and fixed.
  - **Review finding (P2, fixed).** The third invariant was pinned at the gate
    and at the ledger but not at the BTC-180 replay.
    `test_a_full_replay_reports_risk_at_stop_at_every_open_bar` asserted only
    that each open bar's risk was present and non-negative, and that the final
    book was within the ceiling when re-measured at `ending_nav`, the most
    forgiving NAV in a profitable run. Four injected defects in the engine's
    equity reporting therefore passed the suite unchanged: computing the
    fraction against a wrong NAV, measuring under the other rulebook 19
    convention, dropping a tranche from the aggregate, and measuring against a
    stop the ledger never held. The convention and the dropped tranche were
    caught by no suite in the repository, and both make the replay silently
    under-report risk, which is the composition defect this ticket exists to
    catch. Rulebook 19 requires one explicit convention across advisory, paper
    trading and backtesting and rulebook 32 rule 15 requires the same shared
    formulas, so the assertion those rules ask for is a reconciliation against
    the owner, not a presence check.
    `test_the_replayed_risk_at_stop_is_the_shared_owner_on_its_own_book` now
    rebuilds the ledger the replay held at each open bar from its own
    persisted event rows and requires the reported risk to equal BTC-146
    measured on that book at that bar's NAV, and to be within the configured
    ceiling there. All four defects were confirmed to fail against it. A
    *global* convention change is deliberately still not caught here, because
    it moves both sides of the reconciliation together and is BTC-146's own
    contract, whose suite catches it with fifteen failures.
  - **Review correction to the notes (P3).** The implementer's STRESS
    observation is confirmed: `DEFEND` has no emitter outside the state
    machine, and BTC-154's eight inputs carry no stress input, so nothing
    binds a `StressFlagResult` to an add decision. The accompanying claim that
    "CROWDING has no such gap" is overstated and is corrected here. Nothing
    binds a `CrowdingFlagResult` to `positioning_healthy` either:
    `add_requirements_from_results` takes that state as a caller-supplied
    boolean and has no caller outside its own owner suite, as do
    `evaluate_add_requirements`, `evaluate_hard_veto` and
    `apply_data_quality_gate`. The real asymmetry is narrower than the note
    claimed -- rulebook 18.1 requirement 6 names where a crowding flag should
    land, while rulebook 24's STRESS effect names no landing site at all -- and
    both bindings remain unmade. Neither was invented here, for the reason the
    implementer gave.
  - **Review limitation (P3, not fixed).** Two invariants are asserted at the
    gate and the ledger but argued rather than run at the replay. A
    stress-driven refusal is argued from BTC-180 routing every accepted add
    through `apply_position_event`, and DATA_QUALITY_FAIL has no replay
    scenario at all. Neither is constructible today: the engine exposes no
    action that enters `DEFENSIVE` and takes no data-quality input, so running
    them would require new strategy semantics rather than a new test. The
    suite docstring's "asserted at all three consumers" should be read with
    that exception.
  - **Review regression.** Added
    `test_the_replayed_risk_at_stop_is_the_shared_owner_on_its_own_book`. The
    suite is now 60 cases; the full Python 3.12.14 suite passes with 3415
    tests, also passing with `RuntimeWarning` treated as an error, and
    compileall passes.

#### BTC-223 Paper execution tests
- **Description:**
  Test:

  - missed entry
  - gap through stop
  - multiple tranches
  - stop move
  - trim
  - exit
  - funding and fees
- **Status:** DONE
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-160..166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added the dedicated cross-cutting suite `test_paper_execution.py` for the
    seven named scenarios. Each already has an owner suite, and every one of
    those stubs the others - a BTC-161 test invents a lifecycle, a BTC-150 test
    invents a fill price, a BTC-165 test invents both - so this ticket pins
    what none of them can see: whether a scenario survives the whole chain.
    Each scenario is driven through the real BTC-160 account, BTC-161 to
    BTC-164 executions, the BTC-150 ledger, BTC-165 accounting and BTC-166
    persistence, and asserted in three parts: the scenario's execution
    semantics still hold in composition, every owner agrees about the same
    trade with no figure recomputed on a second convention, and the result is
    deterministic and replays from its own record.
  - Missed entry: with no fill there is no notional, so a miss costs the
    account nothing; the ledger reaches `MISSED` with no tranche, no quantity
    and no average entry; BTC-165 refuses to account a trade with no fills
    rather than inventing a zero-quantity one; and BTC-166 persists the missed
    order and event while reporting `TRADE_NOT_CLOSED`. Rulebook 32 rule 8 is
    checked at both owners - the execution refuses any bar that is not its one
    eligible bar, and the terminal ledger refuses a later entry.
  - Gap through stop: two bars trading equally far below the stop resolve
    differently on their opens alone, and the gap's extra loss is not absorbed
    anywhere - it reaches the trade's realized R, which is worse than the
    touched stop's, itself already worse than -1R once costs are paid. The R
    denominator BTC-165 uses is the same number BTC-162 planned at the stop. An
    untouched stop stays `submitted` and changes nothing, unlike a missed
    entry.
  - Multiple tranches: every quantity is BTC-155's allocation, never a
    hand-picked size; each add fills strictly above the running average, so
    rulebook 32 rule 2 holds at the fill and not only at the decision; the
    schedule caps the book and the fourth add is refused for free; a
    gate-blocked add records the allocation it declined while filling nothing;
    and the stop covers the aggregate quantity with a planned risk equal to the
    per-tranche sum that BTC-146 independently reports for the same ledger.
  - Stop move: the execution reads the stop the ledger now carries rather than
    the entry stop or a caller's restatement; a stop moved mid-bar cannot fill
    on the bar whose low is already history; a loosening is held and the
    tighter stop still governs; and a ratchet into profit leaves BTC-146's
    floored downside at zero while BTC-165's `INITIAL_PLANNED_RISK_V1` keeps 1R
    the risk actually taken at entry, so a travelling stop cannot inflate R.
  - Trim: on one tranche the trim's realized P&L is exactly the gross BTC-165
    attributes to that fill, so a re-based average would break the identity;
    across tranches the pro-rata reduction leaves the weighted average entry
    and the tranche prices unchanged; the following stop covers only what
    remains; a full-size reduction is refused by both owners rather than
    quietly becoming an exit; and a defensive trim settles the signed loss it
    locked in, not its magnitude.
  - Exit: the BTC-158 reason travels from the signal through the execution and
    the ledger transition into `completed_trades`, keeping the execution's own
    codes rather than being summarised away; an exit closes everything at both
    owners; and a closed trade persists orders, events and the completed trade
    under one provenance triple.
  - Funding and fees: the non-zero rate comes from the versioned `stress` cost
    profile rather than an invented number. Every leg pays the configured fee
    on its own slipped notional, slippage is adverse on all four legs in both
    directions, a long pays carry and a short receives it, funding is
    reconciled to the quantity the ledger held at each event, and a trade that
    is profitable on price but loses after costs raises
    `TRADE_ACCOUNTING_COSTS_REVERSED_A_GROSS_PROFIT`. The account walked the
    BTC-180 way - each leg's fee, each signed funding event, then gross P&L
    once - ends at exactly `starting NAV + net P&L`. The shipped base profile
    prices funding at a configured zero, and an aggregate figure with no
    point-in-time evidence is still refused.
  - A whole-trade test composes entry, a pyramided add, a trim, a ratcheted
    stop, carried funding and a signalled exit into one lifecycle and
    reconciles the ledger walk, the source identity of every transition, the
    accounting, the account and the persisted rows, then replays the ledger
    from its own event records and reproduces every record from the same
    inputs.
  - Suite value was measured rather than assumed: fifteen single-line
    composition defects were injected into the owners (a stop sized for the
    entry tranche rather than what the ledger holds, a trim re-basing the
    average entry, a trim reporting P&L before its fee, an add's notional
    missing from the entry basis, the gap test reading the low, a miss filling
    at the zone boundary, the account not accumulating a charged fee, funding
    signed the wrong way, unstamped lifecycle rows, an exit filling at the bar
    close, R measured against the closing stop, a refused add reporting a
    filled quantity, an add filling at the close, a trim filling at the high,
    and the ratchet accepting a loosening) and the suite re-run. All fifteen
    are caught, and the discretionary exit filling at the bar close is caught
    by no owner suite.
  - Two observations are recorded rather than silently resolved. First, the
    BTC-180 discretionary-exit boundary exposes no `as_order_record`, unlike
    BTC-161 through BTC-164 and BTC-162's stop, so a signalled exit contributes
    no `paper_orders` row to a BTC-166 lifecycle; the exit is still fully
    attributed through its BTC-150 event row and the completed trade, and
    adding an order mapping is BTC-166 and BTC-180 scope. Second, BTC-165
    removes a trim's cost basis as `cost_basis * quantity / open`, so when the
    open quantity does not terminate in Decimal's 28-digit context - which
    BTC-155 produces routinely, since it divides a notional by a price - the
    closed trade misses the exact cash-flow identity by about 1e-23 and is
    refused outright. Refusing is the right response to that situation, and a
    silently wrong gross P&L would be far worse, but the situation is reachable
    from an ordinary add-then-trim trade. Both are pinned by test and left to
    their owners.
  - Added 44 focused cases. The full Python 3.12.14 suite passes with 3296
    tests, also passing with `RuntimeWarning` treated as an error; compileall
    passes.

#### BTC-224 Golden historical scenarios
- **Description:**
  Create hand-reviewed BTC periods and expected strategy behavior.
- **Status:** DONE
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-220..223
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
- **Implementation Notes:**
  - Added the frozen fixture `tests/golden/btc_golden_scenarios_v1.json` and
    the suite `test_golden_scenarios.py`. Six real BTC periods are frozen with
    their review, the trade plan a reviewer drew on them, and the behaviour the
    system is expected to produce; each is replayed through the real BTC-180
    engine and the BTC-141..165 owners it routes to. Everything upstream of
    this ticket is tested on constructed bars, which can only demonstrate the
    behaviour their author already had in mind. A golden scenario is the
    opposite instrument: a period nobody designed, paired with a stated
    expectation.
  - Sessions are derived from the pinned BTC-019 Coinbase 1h artifact - the
    `sha256:300b283f...` its collection manifest records - by the BTC-020 owner
    `derive_ohlcv_bars`, and each session is decision-available at its own
    close boundary under `GOLDEN_BAR_AVAILABILITY_SESSION_CLOSE_V1`. Every
    window is gap-free and carries its own bar digest, so an edited session is
    a fixture failure rather than a new expectation; the committed bars were
    verified to reproduce exactly from that artifact.
  - Three things are separated deliberately. Market facts come from the frozen
    bars: which session a zone was touched in, where a stop sat, what ATR20
    was, what a fill cost. Judgement comes from the recorded review: the
    structural level a stop hangs on, the conviction, and the BTC-154/157/158
    states no price-only replay can know, written down with their reasoning
    rather than invented as mechanical proxies. Every figure comes from its
    owner - BTC-141 buffers, BTC-142 stops, BTC-144/145 sizing, BTC-155
    tranches, BTC-156 trails, BTC-160..165 execution and accounting.
  - The periods and what each is for. October 2023's reclaim: an entry at a
    zone the market opened above, two trails to reviewed higher lows, a second
    tranche the trail itself authorises, and a position marked rather than
    force closed when the window ends. The 17 August 2023 range break: a -7.22%
    session taking out a tight ATR-bound stop. The January 2024 ETF launch: a
    chased continuation zone terminally missed for nothing, then a reclaim
    stopped on its own entry session through the pre-authorised bracket, with
    no excursion evidence because one session holds no intrabar path.
    February-March 2024: a euphoria trim into the all-time high, +8.5R, and a
    stop that fired before the queued second trim, which went stale rather than
    executing against a position that no longer existed. 31 July 2024: a
    regime-invalidation exit at -0.37R where the standing stop would have paid
    -1.006R the next session and still been open for the 5 August unwind. And
    the 10 October 2025 selloff.
  - A finding real sessions produce and constructed bars hide: no stop in the
    fixture gaps. A continuously traded series opens each session within a tick
    of the previous close, so a stop inside a session's range is always offered
    at its own price and the loss beyond -1R is slippage and fees. The
    gapped-open path BTC-223 pins with constructed bars is not reachable on
    this data, which is asserted rather than assumed.
  - The 10 October 2025 scenario is deliberately source scoped. Its stop at
    107,623.70 sits between that session's pinned Coinbase low of 107,000 and
    Bitstamp's 109,683, so the same reviewed plan is stopped out on this series
    and on Bitfinex and is not stopped out on Bitstamp. That is the event
    `PRICE_SOURCE_POLICY_V1` uses to reject a single-venue reference. BTC-019
    remains in progress, so the fixture records `canonical_reference_status`
    as `UNRESOLVED` and the suite checks the recorded venue lows against the
    series it ships, rather than letting one venue read as the price of
    Bitcoin.
  - Expectations are pinned twice. The reviewed event stream, trades, reason
    codes, final state and NAV are compared to the fixture; and the same
    figures are re-derived from the bars on a second convention - fill
    references from the session geometry, fills, fees and slippage from the
    bps, the first tranche's planned risk from the conviction budget and stop
    distance, and the ending NAV from one walk over the fills - so a golden
    master cannot quietly bless a defect it recorded.
  - Also asserted per scenario: determinism and a restore round trip; the
    BTC-221 truncation property applied to the engine on real history; no
    averaging down, a monotone standing stop, and risk at stop inside the
    configured ceiling on every session; that the stop was resolved on exactly
    the sessions it protected, which accounts for the events the expectation
    does not list; and that the BTC-181 ladder reprices a period - net P&L
    strictly monotone across the three rungs, carry only on the stress rung and
    only where a position survived a session boundary - without changing a
    single reviewed decision.
  - The reviewed February 2024 plan also added a second tranche on 27 February.
    That trade cannot be accounted at all: BTC-155 allocates a tranche quantity
    of notional/price that does not terminate in Decimal's context, and
    BTC-165's pro-rata trim basis then misses its own cash-flow identity. This
    is the composition gap BTC-223 recorded and left to its owner. The add is
    therefore kept out of the replayed plan and pinned instead as the
    scenario's `known_composition_limit`, which shows the gap is reachable from
    an ordinary review of an ordinary period and not only from a constructed
    fixture. It will need updating when the accumulation is made exact.
  - Added 116 focused cases. The full Python 3.12.14 suite passes with 3412
    tests, also passing with `RuntimeWarning` treated as an error; compileall
    passes.
  - **Independent xHigh review (2026-09-03):** the fixture's provenance is
    genuine and the expectations do not encode a defect. The pinned artifact
    still hashes to the recorded `300b283f...`, and all 279 fixture sessions
    were re-derived from it through `derive_ohlcv_bars` outside the suite and
    matched digit for digit on every OHLCV field, so the committed bars are
    the artifact's own daily aggregation rather than a transcription. The
    recorded February 2024 composition limit reproduces exactly, raising
    `closed trade does not satisfy the exact cash-flow identity` from
    BTC-165's accounting, so it is a real reachable limit and not a
    placeholder. The double-pinning was measured rather than assumed: defects
    injected into the cost policy, the entry zone cap, the stop fill
    reference, the fee rate and the conviction budget were all caught by the
    re-derivation tests and not only by the recorded master. Two figures were
    pinned once; one review finding covers both, and is fixed.
  - **Review finding (P3, fixed).** `test_the_money_reconciles_from_the_fills_alone`
    took `funding` straight from `result.trades` and then used that same value
    on both sides of the NAV identity, so the identity held for any funding
    rate: tripling the rate the engine charges left all 116 cases passing.
    The base rung prices no carry, so the term was zero on every scenario in
    any case. Separately, the R multiple -- the reviewed headline of every
    scenario -- was pinned only by the recorded expectation; switching the
    convention from net to gross P&L failed nothing but
    `test_each_scenario_reproduces_its_reviewed_trades`, because every
    hand-derived R bound in the scenario tests is coarse enough to survive a
    few bps, so a regenerated fixture would have blessed it. The
    reconciliation now runs on all three BTC-181 rungs, derives the carry from
    the sessions themselves -- the quantity the ledger carried into each
    session, marked at that session's close, one day per canonical daily bar
    -- and derives R from the reconciled net over the risk the entry actually
    took. Both defects were confirmed to pass the suite before and to fail it
    after. Both are also caught by their owner suites, which is why this is
    P3 rather than higher: the gap was in this ticket's own stated
    double-pinning property, not in the repository's coverage of the owners.
  - **Review limitation (P3, not fixed).** The suite checks the source
    artifact's digest for shape only; it never hashes the artifact itself, so
    a re-sourced fixture would still pass. That check was done by hand in this
    review and is deliberately not automated here, because the artifact is a
    2.1 MB collection input rather than a test fixture and BTC-019 has
    approved no canonical reference for it to be pinned against.
  - **Review regression.** `test_the_money_reconciles_from_the_fills_alone` is
    now parametrized over `COST_PROFILES` and derives the carry and the R
    multiple independently. The suite is now 128 cases; the full Python
    3.12.14 suite passes with 3427 tests, also passing with `RuntimeWarning`
    treated as an error, and compileall passes.


---

**Document Version:** 2.6

**Architecture Change:** Dedicated NumPy/SciPy quant core + v1.2 de-nested scoring contracts with parity/version-controlled migration

**Source of Truth:** PostgreSQL

**Primary Execution Mode:** Human advisory + autonomous paper portfolio

**Price Data Policy:** Bitstamp retained for raw OHLCV but rejected as sole canonical reference; Coinbase and Bitfinex remain validation sources; optional Coin Metrics benchmark; BTC-019 remains in progress pending an approved reference policy

**Scoring Architecture Policy:** v1.2 removes mechanical nested factor double-counting; Regime is context/gate, R/R is independent, and Entry/Hold/Add are direct-component composites.




**Codex Default Model:** GPT-5.6 Sol — High

**Codex Correctness-Critical Model:** GPT-5.6 Sol — Extra High (xhigh)

**Codex Audit Policy:** Independent xHigh review on highest-risk Phase 1 tickets.

**Model Allocation Policy:** Quality-first; no Terra assignments in v2.5.
