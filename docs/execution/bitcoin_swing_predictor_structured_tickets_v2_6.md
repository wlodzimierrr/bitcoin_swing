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
  - **V2 migration note:** this pure-Python implementation remains the reference/parity oracle while BTC-043 introduces the NumPy production kernel.
  - The public behavior and point-in-time semantics of BTC-041 must not change during vectorization.


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
  - `atr_from_daily_bars()` bridges to the BTC-043 `average_true_range`
    primitive and returns `None` during warm-up rather than a partial-window
    value.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-170..172, BTC-210
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.


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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-049 for quant parity coverage
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-221 Look-ahead bias test suite
- **Description:**
  Critical tests:

  - future bars unavailable
  - future ETF flows unavailable
  - future confirmed pivots unavailable
  - rolling normalization past-only
  - AVWAP anchors point-in-time valid
- **Status:** TODO
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
- **Status:** TODO
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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-160..166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-224 Golden historical scenarios
- **Description:**
  Create hand-reviewed BTC periods and expected strategy behavior.
- **Status:** TODO
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
