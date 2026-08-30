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
`bitcoin_swing_predictor_project_tickets_v1.md` is retained only as historical
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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-045 where distance/no-chase metrics are used
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-131, BTC-132
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
  - **Specification gap recorded:** `LevelNoiseEstimate` is named once in the
    rulebook and never defined. It is therefore an explicit caller-supplied
    input. `level_noise_from_zone()` offers a documented Phase-1 reading (half
    the structural zone width, i.e. the distance from zone edge to centre) but
    is labelled a provisional interpretation rather than a rulebook formula.
  - ATR window defaults to 20 per rulebook 16.1. Note this differs from the
    14-day ATR used by the price-source research modules; the buffer window is
    explicit and configurable.
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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-140, BTC-141, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - If no credible structural reward reference exists, the R/R filter fails
  - Selected reward reference is persisted with the recommendation
  - R/R calculation is reproducible from stored levels and entry/stop values
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-144 Implement conviction-based risk budget
- **Description:**
  Initial schedule:

  ```text
  80–84  0.35% NAV
  85–89  0.50% NAV
  90+    0.60% NAV
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-145 Implement initial position sizing
- **Description:**
  \[
  PositionNotional=
  \frac{NAV\times RiskBudget}{StopDistance\%}
  \]
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-144, BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-146 Implement maximum risk-at-stop
- **Description:**
  Phase 1 target:

  \[
  RiskAtStop \le 0.75\%-1.00\% NAV
  \]
- **Status:** TODO
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
- **Status:** TODO
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

#### BTC-151 Implement no-average-down rule
- **Description:**
  Hard invariant:

  ```text
  ADD prohibited if position is losing
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-150
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-046, BTC-129
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-046, BTC-047, BTC-129
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-153
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-155 Implement tranche sizing
- **Description:**
  Initial research schedule:

  ```text
  Initial  40%
  Add #1   35%
  Add #2   25%
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-043, BTC-045, BTC-047
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

#### BTC-157 Implement trim rules
- **Description:**
  Based on:

  - Hold Score
  - EUPHORIA
  - CROWDING
  - Flow deterioration
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Trim signals include reason codes
  - Trim signals are distinct from full exits
  - Paper trader can simulate partial reductions once BTC-164 is complete
- **Dependencies:** BTC-047, BTC-150, BTC-152
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-142, BTC-150, BTC-152, BTC-156
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

## EPIC Q — Paper Trading Engine

#### BTC-160 Create paper trading account
- **Description:**
  Configurable:

  - starting NAV
  - fees
  - slippage
  - funding
  - available cash
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-150
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-161 Implement simulated entry execution
- **Description:**
  ### Requirements

  - Respect entry zone
  - Realistic next-bar execution
  - No perfect fill assumptions
  - Mark missed entries
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-162 Implement simulated stop execution
- **Description:**
  Handle:

  - stop touch
  - gaps
  - slippage
  - partial position state
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

#### BTC-163 Implement simulated adds
- **Description:**
  Complete the ticket scope for implement simulated adds.
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-154
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-164 Implement simulated trims
- **Description:**
  Complete the ticket scope for implement simulated trims.
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-157, BTC-160
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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

#### BTC-166 Persist complete paper trade lifecycle
- **Description:**
  Every event linked to:

  ```text
  recommendation_id
  strategy_version
  parameter_set_id
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-160..165 and completed paper-portfolio persistence schema
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-130..133, BTC-140..146, BTC-160..166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-150..158, BTC-160..166, BTC-170
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-172 Add machine-readable JSON output
- **Description:**
  Useful for dashboards, notifications, or future automation.
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-170, BTC-171
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Review Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-047, BTC-048, BTC-049, BTC-150..158
- **Priority:** P0
- **Complexity:** XL
- **Risk:** High.

#### BTC-181 Add realistic cost model
- **Description:**
  Profiles:

  ```text
  optimistic
  base
  stress
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-182 Implement walk-forward validation
- **Description:**
  No single static train/test split.

  Use rolling or expanding windows.
- **Status:** TODO
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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-182
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-184 Implement setup-level performance report
- **Description:**
  Compare:

  ```text
  Trend Continuation
  Bullish Reset
  Capitulation Reversal
  Bearish Distribution
  ```
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-182
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — Extra High (xhigh)
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-049, BTC-180
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.


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
- **Status:** TODO
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
- **Status:** TODO
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
- **Status:** TODO
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
- **Status:** TODO
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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-180
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-191 Create paper-trade outcome dataset
- **Description:**
  Join entry-state features to final outcomes.
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-048, BTC-165, BTC-166
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-192 Create strategy comparison framework
- **Description:**
  Compare:

  - strategy_v1.0
  - candidate strategy versions
  - parameter sets
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-180, BTC-191
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-182, BTC-185, BTC-189, BTC-192
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170, BTC-172
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-200
- **Priority:** P1
- **Complexity:** XS
- **Risk:** Low.

#### BTC-202 Implement actual trade entry
- **Description:**
  Record real manual execution.
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-200, BTC-201 and completed manual-trade journal schema
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-191, BTC-202
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170, BTC-172
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

#### BTC-211 Create weekly strategy report
- **Description:**
  Show:

  - regime changes
  - setup changes
  - price levels
  - current paper trades
  - risk
  - recent score movement
- **Status:** TODO
- **Model:** GPT-5.6 Sol — High
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** BTC-166, BTC-170..172, BTC-210
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.

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
- [ ] BTC-098 Structure Score v1.2 removes R/R and repeated Confluence from outer weighting
- [ ] BTC-129 factor-overlap audit confirms de-nested Entry/Hold/Add contracts
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
