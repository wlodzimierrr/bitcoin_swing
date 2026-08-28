# Bitcoin Swing Predictor — Project Roadmap & Tickets

## 1. Project Goal

Build a **low-frequency Bitcoin swing trading decision-support system** that:

- Finds only high-conviction BTC swing opportunities
- Prefers **NO TRADE** over weak or marginal setups
- Targets roughly **1–4 meaningful entries per month**, potentially fewer
- Uses weekly/monthly regime analysis and multi-week holding periods
- Produces a complete trade recommendation for manual execution
- Runs an independent paper-trading portfolio automatically
- Tracks every recommendation, simulated trade, manual trade, and lifecycle decision
- Uses PostgreSQL as the system of record
- Improves through controlled research and versioned strategy updates rather than self-modifying after every trade

The system is **not** intended to execute live trades automatically in Phase 1.

---

# 2. Core Product Principles

1. **Default = NO TRADE**
2. **Human execution, machine guidance**
3. **Paper trader follows the model without discretion**
4. **Never average down**
5. **Structure determines the stop**
6. **Volatility determines the stop buffer**
7. **Risk budget determines position size**
8. **Add only after favorable confirmation**
9. **Notional exposure may rise while risk-at-stop stays bounded**
10. **No fixed take-profit required**
11. **Every decision must be explainable**
12. **Every signal must be reproducible**
13. **All research must be point-in-time correct**
14. **Strategy versions are immutable once promoted**
15. **No automatic production learning from individual trades**

---

# 3. Target Architecture

```text
                    MARKET DATA
                        │
                        ▼
                 DATA INGESTION
                        │
                        ▼
                   PostgreSQL
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      RAW DATA      DERIVED DATA    TRADE STATE
          │             │
          ▼             ▼
      Feature       Price-Level
      Engine          Engine
          │             │
          └──────┬──────┘
                 ▼
            Regime Engine
                 │
                 ▼
            Setup Detector
                 │
                 ▼
           Scoring Engine
                 │
                 ▼
             Risk Engine
                 │
          ┌──────┴──────┐
          ▼             ▼
   Trade Adviser    Paper Trader
          │             │
          ▼             ▼
    Recommendation   Shadow Portfolio
          │             │
          ▼             ▼
     Human Decision   Simulated Trades
          │             │
          └──────┬──────┘
                 ▼
             PostgreSQL
                 │
                 ▼
          Research / Review
                 │
                 ▼
        Candidate Strategy Version
                 │
                 ▼
       Walk-Forward Validation
                 │
                 ▼
           Manual Promotion
```

---

# 4. Phase Structure

## Phase 1 — Research-Grade Core

Goal:

> Build a deterministic, point-in-time correct BTC swing predictor with price-structure stops, risk sizing, paper trading, and reproducible backtesting.

Deliverables:

- PostgreSQL schema
- Market-data ingestion
- Feature engine
- Price-level engine
- Regime engine
- Setup detector
- Scoring system
- Risk engine
- Position lifecycle rules
- Backtester
- Paper trader
- Recommendation output
- Audit trail
- Initial research report

---

## Phase 2 — Live Signal Observation

Goal:

> Run the model on live data with no real capital committed.

Deliverables:

- Scheduled live scoring
- Live recommendation feed
- Paper portfolio
- Alerts
- Signal journal
- Drift monitoring
- Data-quality monitoring

---

## Phase 3 — Manual Trading Support

Goal:

> Use the model as a live adviser while trades are executed manually.

Deliverables:

- Manual trade entry
- Actual-vs-recommended execution tracking
- Portfolio state tracking
- Manual override journal
- Model vs human performance comparison

---

## Phase 4 — Optional Semi-Automation

Only if justified later.

Potential scope:

- Draft orders
- Order validation
- Human approval before submission
- Exchange adapter

---

# 5. Technology Stack

## Core

- Python 3.12+
- PostgreSQL
- SQLAlchemy
- psycopg
- Alembic
- pandas or Polars
- NumPy
- SciPy
- scikit-learn
- statsmodels

## Research / Visualization

- matplotlib
- Plotly optional
- Jupyter optional for research only

## Testing

- pytest
- hypothesis where useful

## Configuration

- YAML or TOML
- No strategy thresholds hard-coded in business logic

---

# 6. PostgreSQL Schema

Recommended schemas:

```text
raw
derived
signals
portfolio
research
system
```

---

## raw

Immutable provider observations.

Suggested tables:

```text
raw.btc_ohlcv
raw.funding_rates
raw.open_interest
raw.futures_basis
raw.liquidations
raw.etf_flows
raw.macro_series
raw.onchain_metrics
raw.provider_ingestion_log
```

---

## derived

Point-in-time computed data.

Suggested tables:

```text
derived.market_daily
derived.market_weekly
derived.trend_features
derived.flow_features
derived.positioning_features
derived.volatility_features
derived.price_levels
derived.level_clusters
derived.structure_features
derived.regime_features
```

---

## signals

Every predictor output.

Suggested tables:

```text
signals.regime_scores
signals.setup_candidates
signals.predictor_scores
signals.recommendations
signals.reason_codes
```

---

## portfolio

Paper and manual portfolio state.

Suggested tables:

```text
portfolio.paper_accounts
portfolio.paper_positions
portfolio.paper_tranches
portfolio.paper_orders
portfolio.paper_trades

portfolio.manual_accounts
portfolio.manual_positions
portfolio.manual_trades

portfolio.stops
portfolio.position_events
```

---

## research

Research lineage and backtesting.

Suggested tables:

```text
research.strategy_versions
research.parameter_sets
research.backtest_runs
research.backtest_trades
research.backtest_equity
research.trade_features
research.trade_outcomes
research.threshold_sweeps
research.model_comparisons
```

---

## system

Operational data.

Suggested tables:

```text
system.jobs
system.job_runs
system.data_quality_events
system.alerts
system.config_versions
```

---

# 7. Point-in-Time Data Contract

Every external dataset should support point-in-time correctness.

Where relevant, store both:

```text
observation_time
available_at
```

The predictor may only use observations where:

\[
available\_at \le signal\_time
\]

This rule applies to:

- ETF flows
- macro data
- on-chain metrics
- revised datasets
- provider snapshots

No feature may use information that was unavailable at the prediction timestamp.

---

# 8. Strategy Versioning

Every recommendation and backtest must store:

```text
strategy_version
feature_version
parameter_set_id
code_commit
data_snapshot_id or run timestamp
```

Example:

```text
strategy_version = swing_v1.0
feature_version  = features_v1.0
parameter_set_id = 12
```

Production strategy versions must not mutate silently.

---

# 9. Ticket Conventions

Priority:

```text
P0 = required for Phase 1
P1 = important but not blocking first end-to-end run
P2 = later enhancement
```

Estimate:

```text
1 = very small
2 = small
3 = medium
5 = substantial
8 = large / potentially split
```

---

# EPIC A — Project Foundation

## BTC-001 — Create Python project structure

**Priority:** P0  
**Estimate:** 2

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

### Acceptance Criteria

- Installable Python package
- Central configuration loader
- Structured logging
- Test runner works
- No secrets committed
- Environment-specific configuration supported

---

## BTC-002 — Define strategy configuration schema

**Priority:** P0  
**Estimate:** 2

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

### Acceptance Criteria

- Strategy parameters are externalized
- Config validated at startup
- Invalid configs fail fast
- Config version is persisted with every run

---

## BTC-003 — Add database migration framework

**Priority:** P0  
**Estimate:** 2

Use Alembic.

### Acceptance Criteria

- Fresh database can be built from migrations
- Upgrade and downgrade tested
- Schema state can be reproduced exactly

---

# EPIC B — PostgreSQL Data Model

## BTC-010 — Create core PostgreSQL schemas

**Priority:** P0  
**Estimate:** 1

Create:

```text
raw
derived
signals
portfolio
research
system
```

### Acceptance Criteria

- Schemas created through migration
- Application DB user has correct permissions
- Research and runtime connections verified

---

## BTC-011 — Create raw OHLCV schema

**Priority:** P0  
**Estimate:** 2

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

### Acceptance Criteria

- Unique primary key
- UTC timestamps
- Duplicate ingestion is idempotent
- Missing bars can be detected

---

## BTC-012 — Create derivatives raw schemas

**Priority:** P0  
**Estimate:** 3

Tables for:

- Funding
- Open interest
- Futures basis
- Liquidations
- Perp volume

### Acceptance Criteria

- Exchange/source preserved
- Units documented
- Timestamp semantics documented
- Point-in-time availability supported

---

## BTC-013 — Create ETF flow raw schema

**Priority:** P0  
**Estimate:** 2

Store:

- fund
- observation date
- flow
- AUM if available
- source
- available_at

### Acceptance Criteria

- Historical revisions can be represented
- Signal jobs query only data available at signal time

---

## BTC-014 — Create macro and on-chain generic series schema

**Priority:** P1  
**Estimate:** 3

Support generic time series:

```text
series_id
observation_time
value
available_at
provider
revision
```

### Acceptance Criteria

- Can store VIX, yields, DXY proxies, liquidity measures, and on-chain metrics
- Revisions do not overwrite historical availability state

---

## BTC-015 — Create predictor and recommendation schemas

**Priority:** P0  
**Estimate:** 3

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

### Acceptance Criteria

Every recommendation is reconstructable later.

---

## BTC-016 — Create paper portfolio schemas

**Priority:** P0  
**Estimate:** 3

Create entities for:

- Paper account
- Position
- Tranche
- Order
- Stop
- Position event
- Completed trade

### Acceptance Criteria

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

---

## BTC-017 — Create manual trade journal schema

**Priority:** P1  
**Estimate:** 2

Store:

- linked recommendation
- actual entry
- actual size
- actual stop
- manual decision
- override reason
- actual exit
- notes

### Acceptance Criteria

Can compare recommendation vs actual execution.

---

# EPIC C — Data Ingestion

## BTC-020 — Implement BTC OHLCV collector

**Priority:** P0  
**Estimate:** 3

Collect at minimum:

- 1h data
- derive daily
- derive weekly
- derive monthly

### Acceptance Criteria

- Idempotent ingestion
- UTC normalization
- Retry support
- Missing interval detection
- Daily, weekly, and monthly bars derive from point-in-time source data
- Raw records never silently changed

---

## BTC-021 — Implement derivatives collector

**Priority:** P0  
**Estimate:** 5

Collect:

- funding
- OI
- futures basis
- liquidations
- perp volume

### Acceptance Criteria

- Provider-specific raw data normalized
- Aggregate BTC view can be generated
- No future timestamps leak into derived data

---

## BTC-022 — Implement ETF flow collector

**Priority:** P0  
**Estimate:** 3

### Acceptance Criteria

- Daily flow loaded
- AUM normalization supported where available
- available_at correctly captured
- Missing publication days handled explicitly

---

## BTC-023 — Implement macro data collector

**Priority:** P1  
**Estimate:** 3

Initial candidate data:

- VIX
- DXY or equivalent
- Nasdaq proxy
- US 2Y yield
- real yield proxy

---

## BTC-024 — Implement on-chain collector

**Priority:** P1  
**Estimate:** 3

Initial candidates:

- SOPR
- MVRV
- realized P/L
- short-term holder realized price
- exchange flows

---

## BTC-025 — Build ingestion audit log

**Priority:** P0  
**Estimate:** 2

Track:

- job start/end
- records fetched
- records inserted
- failures
- gaps
- provider response metadata

---

# EPIC D — Data Quality

## BTC-030 — Implement OHLCV quality checks

**Priority:** P0  
**Estimate:** 2

Detect:

- duplicate bars
- impossible OHLC
- missing periods
- stale data
- extreme malformed values

---

## BTC-031 — Implement derivatives quality checks

**Priority:** P0  
**Estimate:** 2

Detect:

- stale funding
- impossible negative OI
- sudden provider discontinuities
- missing exchange snapshots
- unit changes

---

## BTC-032 — Implement DATA_QUALITY_FAIL flag

**Priority:** P0  
**Estimate:** 2

### Rule

If critical inputs fail quality checks:

```text
NO NEW TRADE
NO ADD
```

### Acceptance Criteria

- Predictor can still report existing position state
- Failure reasons are persisted

---

# EPIC E — Derived Market Data

## BTC-040 — Build daily, weekly, and monthly market bars

**Priority:** P0  
**Estimate:** 3

Generate canonical BTC daily, weekly, and monthly bars.

### Acceptance Criteria

- Consistent session definition
- Weekly boundaries documented
- Monthly boundaries documented
- Reproducible aggregation
- Point-in-time correct

---

## BTC-041 — Build rolling statistics framework

**Priority:** P0  
**Estimate:** 3

Reusable functions for:

- rolling means
- rolling volatility
- z-scores
- percentiles
- ATR
- historical normalization

### Acceptance Criteria

All rolling calculations use only past information.

---

# EPIC F — Trend Engine

## BTC-050 — Implement 4-week momentum

**Priority:** P0  
**Estimate:** 1

\[
M_4=P_t/P_{t-28}-1
\]

---

## BTC-051 — Implement 12-week momentum

**Priority:** P0  
**Estimate:** 1

\[
M_{12}=P_t/P_{t-84}-1
\]

---

## BTC-052 — Implement 20-week MA distance

**Priority:** P0  
**Estimate:** 1

---

## BTC-053 — Implement weekly structure classifier

**Priority:** P0  
**Estimate:** 3

Classify:

```text
HH + HL
HL only
Mixed
LH only
LH + LL
```

---

## BTC-054 — Implement 52-week-high distance

**Priority:** P0  
**Estimate:** 1

---

## BTC-055 — Implement Trend Score

**Priority:** P0  
**Estimate:** 2

Initial formula:

\[
TrendRaw =
0.30Z_{M4}
+0.30Z_{M12}
+0.20Z_{20W}
+0.15S_{structure}
+0.05Z_{52H}
\]

### Acceptance Criteria

- Output 0–100
- Inputs persisted
- Score explainable
- Historical recomputation deterministic

---

# EPIC G — Flow Engine

## BTC-060 — Implement 5-day ETF flow feature

**Priority:** P0  
**Estimate:** 1

---

## BTC-061 — Implement 20-day ETF flow feature

**Priority:** P0  
**Estimate:** 1

---

## BTC-062 — Implement ETF flow acceleration

**Priority:** P0  
**Estimate:** 1

\[
FlowAccel=
ETFNorm_5-\frac{ETFNorm_{20}}{4}
\]

---

## BTC-063 — Implement spot vs perp participation

**Priority:** P1  
**Estimate:** 3

---

## BTC-064 — Implement spot vs perp CVD spread

**Priority:** P1  
**Estimate:** 3

---

## BTC-065 — Implement Flow Score

**Priority:** P0  
**Estimate:** 2

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

### Acceptance Criteria

- Missing P1 inputs are not silently filled with zero
- Output records `FLOW_MODEL = ETF_CORE` or `FLOW_MODEL = ETF_SPOT_PERP_FULL`
- Formula weights are loaded from versioned strategy config

---

# EPIC H — Positioning Engine

## BTC-070 — Implement funding health

**Priority:** P0  
**Estimate:** 2

Input:

- 7d funding average
- 180d rolling z-score

---

## BTC-071 — Implement OI growth health

**Priority:** P0  
**Estimate:** 2

Use rolling normalization rather than fixed permanent thresholds.

---

## BTC-072 — Implement OI intensity

**Status:** DONE
**Priority:** P0
**Estimate:** 2

\[
OIIntensity=AggregateOI/BTCMarketCap
\]

Implemented as a point-in-time feature with explicit market-cap observations,
selected OI unit filtering, 180-day rolling percentile normalization, inverse
health scoring for crowded leverage, and stable reason codes for missing inputs
or insufficient history.

---

## BTC-073 — Implement futures-basis health

**Status:** DONE
**Priority:** P0  
**Estimate:** 2

Implemented as `FUTURES_BASIS_HEALTH` using point-in-time futures-basis rows,
per-timestamp averages across available contracts/exchanges, 180-day rolling
normalization of annualized basis, configurable health-curve parameters, and
stable reason codes for missing input, insufficient history, or zero-variance
history.

---

## BTC-074 — Implement Positioning Score

**Status:** DONE
**Priority:** P0  
**Estimate:** 3

\[
PositioningScore=
0.35FundingHealth
+0.30OIHealth
+0.20BasisHealth
+0.15LeverageHealth
\]

Implemented as `POSITIONING_SCORE` using versioned strategy-config weights,
explicit 0-100 health inputs, per-component contributions, no missing-input
zero filling, stable reason codes, and persisted config metadata. In Phase 1,
`OIHealth` maps to OI growth health and `LeverageHealth` maps to OI intensity
health.

---

## BTC-075 — Implement CROWDING flag

**Status:** DONE
**Priority:** P0  
**Estimate:** 2

Effect:

```text
NO ADD
REDUCE ENTRY QUALITY
OPTIONAL TIGHTER PROFIT PROTECTION
```

Implemented as `CROWDING`, triggered by excessive funding z-score,
futures-basis z-score, or OI-intensity percentile. Thresholds and entry-quality
penalty are loaded from versioned strategy config. The result persists inputs,
thresholds, effects, config metadata, completion state, and reason codes.

---

# EPIC I — Volatility Engine

## BTC-080 — Implement RV7 / RV20 / RV60

**Status:** DONE
**Priority:** P0  
**Estimate:** 1

Implemented as annualized close-to-close realized volatility from
point-in-time canonical daily bars, with default RV7, RV20, and RV60 helpers.
Each result persists feature ID, observation time, window, annualization
periods, realized volatility, source counts, completion state, and stable
reason codes.

---

## BTC-081 — Implement compression ratio

**Status:** DONE
**Priority:** P0  
**Estimate:** 1

\[
RV_7/RV_{60}
\]

Implemented as `VOL_COMPRESSION_RATIO = RV_7 / RV_60`, consuming explicit RV7
and RV60 values or persisted RV feature results. The result persists numerator
and denominator feature IDs, input values, completion state, and stable reason
codes for missing inputs or zero RV60 denominator.

---

## BTC-082 — Implement volatility percentile

**Status:** DONE
**Priority:** P0  
**Estimate:** 1

Implemented as `VOL_PERCENTILE_2Y`, using the rulebook input
`Percentile(RV20, 2yr)`. The helper consumes persisted RV feature results,
selects the latest RV20 available at signal time, ranks it only against prior
RV20 history in the trailing 730-day window, and persists source feature ID,
window parameters, counts, percentile, completion state, and stable reason
codes.

---

## BTC-083 — Implement orderliness score

**Status:** DONE
**Priority:** P0  
**Estimate:** 2

Penalize:

- extreme ranges
- disorderly downside
- liquidation cascades
- volatility spikes

Implemented as `ORDERLINESS_SCORE`, starting at 100 and subtracting configured
component penalties for extreme range percentile, disorderly downside return,
liquidation percentile, and volatility percentile triggers. Results persist
inputs, weights, thresholds, penalties, interpretation, completion state,
config metadata, and stable reason codes.

---

## BTC-084 — Implement Volatility Score

**Priority:** P0  
**Estimate:** 2

---

## BTC-085 — Implement STRESS flag

**Status:** DONE
**Priority:** P0  
**Estimate:** 2

Effect:

```text
NO ADD
REDUCE MAX EXPOSURE
OPTIONALLY BLOCK NEW TRADES
```

Implemented as the hard `STRESS` flag, triggered by extreme volatility
percentile, liquidation percentile, disorderly downside return, abnormal
funding z-score, abnormal basis z-score, or systemic market shock. Results
persist inputs, thresholds, max-exposure multiplier, optional new-trade block
setting, effects, completion state, config metadata, and stable reason codes.
Default thresholds and exposure settings are defined under
`[volatility_flags.stress]` in the versioned strategy config and validated at
startup.

---

# EPIC J — Price-Level / Structure Engine

## BTC-090 — Detect weekly swing highs/lows

**Status:** DONE
**Priority:** P0  
**Estimate:** 5

### Acceptance Criteria

- Point-in-time detection
- No use of future bars before level confirmation
- Detection timestamp persisted separately from level timestamp

Implemented `detect_weekly_swing_levels` for confirmed canonical `1w` swing
highs/lows. Detection uses configurable left/right weekly confirmation windows,
filters to bars closed and ingested by `as_of`, and emits no level until the
right-side confirmation bar is available. `WeeklySwingLevel.as_record()`
persists `level_timestamp` separately from `detected_at`, along with price,
series identity, swing type, window parameters, and source count.

---

## BTC-091 — Detect monthly swing highs/lows

**Status:** DONE
**Priority:** P0  
**Estimate:** 3

Implemented `detect_monthly_swing_levels` for confirmed canonical `1mo` swing
highs/lows. Detection uses configurable left/right monthly confirmation windows,
filters to bars closed and ingested by `as_of`, and emits no level until the
right-side confirmation month is available. `MonthlySwingLevel.as_record()`
persists level timestamp separately from detected timestamp, along with price,
series identity, swing type, window parameters, and source count.

---

## BTC-092 — Detect breakout/reclaim levels

**Status:** DONE
**Priority:** P0  
**Estimate:** 5

Implemented `detect_breakout_reclaim_levels` for structural breakout and
reclaim levels from confirmed weekly/monthly swing levels. Breakouts require a
canonical confirmation bar close above a prior swing high; reclaims require a
bar trading through a prior swing low and closing back above it. Detection only
uses source levels and confirmation bars available by `as_of`, records
confirmation timestamp separately from detection timestamp, persists source
level provenance, and uses versioned `price_levels` close-buffer parameters.

---

## BTC-093 — Implement anchored VWAP support

**Status:** DONE
**Priority:** P1  
**Estimate:** 5

Anchor types:

- major swing low
- major swing high
- breakout
- capitulation event

Implemented anchored VWAP support in `btc_predictor.levels.anchored_vwap`.
Confirmed weekly/monthly swing lows and highs become `major_swing_low` and
`major_swing_high` anchors, confirmed breakout levels become `breakout`
anchors, and explicit capitulation events can become `capitulation_event`
anchors. VWAP uses bars from the anchor timestamp onward but only emits after
the anchor's detection time, and only from OHLCV bars closed and ingested by
`as_of`.

Results persist anchor provenance, configured price source, source timeframe,
bar count, volume sum, price-volume sum, completion state, and reason codes.
Added `anchored_vwap_price_source` to versioned `price_levels` config with
startup validation for `hlc3` and `close`.

---

## BTC-094 — Implement volume-profile levels

**Priority:** P1  
**Estimate:** 5

Candidates:

- POC
- HVN
- VAH
- VAL

---

## BTC-095 — Implement level clustering

**Priority:** P0  
**Estimate:** 5

Combine nearby levels into support/resistance zones.

### Acceptance Criteria

- Cluster boundaries persisted
- Member levels linked
- Confluence score available
- No double-counting of nearby lines

---

## BTC-096 — Implement level-strength score

**Priority:** P0  
**Estimate:** 3

Inputs:

- timeframe
- touch count
- reaction magnitude
- volume
- confluence

---

## BTC-097 — Implement Structure Score

**Priority:** P0  
**Estimate:** 3

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

---

# EPIC K — Regime Engine

## BTC-100 — Implement base Regime Score

**Priority:** P0  
**Estimate:** 3

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

### Acceptance Criteria

- Output records `REGIME_MODEL = CORE_MARKET_ONLY` or `REGIME_MODEL = FULL_MACRO_ONCHAIN_LIQUIDITY`
- Missing P1 inputs are not silently filled with zero
- Formula weights are loaded from versioned strategy config

---

## BTC-101 — Add regime smoothing

**Priority:** P0  
**Estimate:** 1

\[
R_t=0.7R_{t-1}+0.3R_{new}
\]

---

## BTC-102 — Implement regime classification

**Priority:** P0  
**Estimate:** 1

```text
80–100 Strong Bull
65–80  Bull
55–65  Mild Bull
45–55  Neutral
35–45  Mild Bear
20–35  Bear
0–20   Strong Bear
```

---

# EPIC L — Setup Detector

## BTC-110 — Implement Bull Trend Continuation setup

**Priority:** P0  
**Estimate:** 3

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

---

## BTC-111 — Implement Bullish Reset setup

**Priority:** P0  
**Estimate:** 5

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

---

## BTC-112 — Implement Capitulation Reversal setup

**Priority:** P1  
**Estimate:** 5

Require confirmation after capitulation.

---

## BTC-113 — Implement Bearish Distribution setup

**Priority:** P1  
**Estimate:** 5

Use stricter short requirements.

---

## BTC-114 — Implement CAPITULATION flag

**Priority:** P1  
**Estimate:** 2

---

## BTC-115 — Implement EUPHORIA flag

**Priority:** P1  
**Estimate:** 2

---

# EPIC M — Entry Trigger Engine

## BTC-120 — Implement reclaim trigger

**Priority:** P0  
**Estimate:** 3

---

## BTC-121 — Implement breakout + retest trigger

**Priority:** P0  
**Estimate:** 3

---

## BTC-122 — Implement higher-low confirmation trigger

**Priority:** P0  
**Estimate:** 3

---

## BTC-123 — Implement no-chase filter

**Priority:** P0  
**Estimate:** 2

If price moves materially outside intended entry zone:

```text
NO TRADE
```

---

# EPIC N — Scoring Engine

## BTC-130 — Implement Entry Conviction

**Priority:** P0  
**Estimate:** 2

\[
EntryConviction =
0.20Trend
+0.20Regime
+0.20Flow
+0.15Positioning
+0.10Volatility
+0.15Structure
\]

---

## BTC-131 — Implement entry action thresholds

**Priority:** P0  
**Estimate:** 1

```text
<70     IGNORE
70–79   WATCH
80–84   VALID
85–89   STRONG
90+     EXCEPTIONAL
```

---

## BTC-132 — Implement hard-veto engine

**Priority:** P0  
**Estimate:** 3

Veto examples:

- data quality fail
- no valid structural stop
- poor R/R
- stress
- severe crowding
- no-chase violation
- unsupported setup

---

## BTC-133 — Implement reason-code engine

**Priority:** P0  
**Estimate:** 3

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

---

# EPIC O — Risk Engine

## BTC-140 — Implement structural invalidation selection

**Priority:** P0  
**Estimate:** 5

Select best invalidation level based on active setup and nearby structure.

---

## BTC-141 — Implement volatility buffer

**Priority:** P0  
**Estimate:** 2

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

---

## BTC-142 — Implement initial stop

**Priority:** P0  
**Estimate:** 2

For longs:

\[
Stop=Invalidation-Buffer
\]

For shorts:

\[
Stop=Invalidation+Buffer
\]

---

## BTC-143 — Implement R/R filter

**Priority:** P0  
**Estimate:** 2

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

### Acceptance Criteria

- If no credible structural reward reference exists, the R/R filter fails
- Selected reward reference is persisted with the recommendation
- R/R calculation is reproducible from stored levels and entry/stop values

---

## BTC-144 — Implement conviction-based risk budget

**Priority:** P0  
**Estimate:** 2

Initial schedule:

```text
80–84  0.35% NAV
85–89  0.50% NAV
90+    0.60% NAV
```

---

## BTC-145 — Implement initial position sizing

**Priority:** P0  
**Estimate:** 2

\[
PositionNotional=
\frac{NAV\times RiskBudget}{StopDistance\%}
\]

---

## BTC-146 — Implement maximum risk-at-stop

**Priority:** P0  
**Estimate:** 2

Phase 1 target:

\[
RiskAtStop \le 0.75\%-1.00\% NAV
\]

---

# EPIC P — Position Lifecycle / Pyramiding

## BTC-150 — Implement paper position state machine

**Priority:** P0  
**Estimate:** 5

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

---

## BTC-151 — Implement no-average-down rule

**Priority:** P0  
**Estimate:** 1

Hard invariant:

```text
ADD prohibited if position is losing
```

---

## BTC-152 — Implement Hold Score

**Priority:** P0  
**Estimate:** 2

\[
HoldScore =
0.25Regime+
0.20Trend+
0.20Flow+
0.15Positioning+
0.10Structure+
0.10MomentumPersistence
\]

---

## BTC-153 — Implement Add Score

**Priority:** P0  
**Estimate:** 3

\[
AddScore=
0.20HoldScore+
0.25NewStructure+
0.20Flow+
0.15Positioning+
0.10Momentum+
0.10RiskImprovement
\]

---

## BTC-154 — Implement add requirements

**Priority:** P0  
**Estimate:** 3

Require:

- position profitable
- new structural confirmation
- stop can improve
- supportive regime
- supportive flow
- healthy positioning
- Add Score >= 85
- risk-at-stop within max

---

## BTC-155 — Implement tranche sizing

**Priority:** P0  
**Estimate:** 2

Initial research schedule:

```text
Initial  40%
Add #1   35%
Add #2   25%
```

---

## BTC-156 — Implement trailing stop progression

**Priority:** P0  
**Estimate:** 5

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

---

## BTC-157 — Implement trim rules

**Priority:** P0  
**Estimate:** 3

Based on:

- Hold Score
- EUPHORIA
- CROWDING
- Flow deterioration

### Acceptance Criteria

- Trim signals include reason codes
- Trim signals are distinct from full exits
- Paper trader can simulate partial reductions once BTC-164 is complete

---

## BTC-158 — Implement exit rules

**Priority:** P0  
**Estimate:** 3

Exit reasons:

```text
STRUCTURAL_STOP
HOLD_SCORE_COLLAPSE
REGIME_INVALIDATION
DATA_RISK
MANUAL_RESEARCH_OVERRIDE
```

---

# EPIC Q — Paper Trading Engine

## BTC-160 — Create paper trading account

**Priority:** P0  
**Estimate:** 2

Configurable:

- starting NAV
- fees
- slippage
- funding
- available cash

---

## BTC-161 — Implement simulated entry execution

**Priority:** P0  
**Estimate:** 3

### Requirements

- Respect entry zone
- Realistic next-bar execution
- No perfect fill assumptions
- Mark missed entries

---

## BTC-162 — Implement simulated stop execution

**Priority:** P0  
**Estimate:** 3

Handle:

- stop touch
- gaps
- slippage
- partial position state

---

## BTC-163 — Implement simulated adds

**Priority:** P0  
**Estimate:** 3

---

## BTC-164 — Implement simulated trims

**Priority:** P0  
**Estimate:** 2

---

## BTC-165 — Implement paper trade accounting

**Priority:** P0  
**Estimate:** 3

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

---

## BTC-166 — Persist complete paper trade lifecycle

**Priority:** P0  
**Estimate:** 3

Every event linked to:

```text
recommendation_id
strategy_version
parameter_set_id
```

---

# EPIC R — Advisory Output

## BTC-170 — Create recommendation renderer

**Priority:** P0  
**Estimate:** 3

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

---

## BTC-171 — Create existing-position management report

**Priority:** P0  
**Estimate:** 3

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

---

## BTC-172 — Add machine-readable JSON output

**Priority:** P1  
**Estimate:** 2

Useful for dashboards, notifications, or future automation.

---

# EPIC S — Backtesting

## BTC-180 — Build event-driven backtest engine

**Priority:** P0  
**Estimate:** 8

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

---

## BTC-181 — Add realistic cost model

**Priority:** P0  
**Estimate:** 2

Profiles:

```text
optimistic
base
stress
```

---

## BTC-182 — Implement walk-forward validation

**Priority:** P0  
**Estimate:** 5

No single static train/test split.

Use rolling or expanding windows.

---

## BTC-183 — Implement regime performance breakdown

**Priority:** P0  
**Estimate:** 3

Break down by:

- bull
- bear
- neutral
- high vol
- low vol
- pre-ETF
- ETF era
- setup type

---

## BTC-184 — Implement setup-level performance report

**Priority:** P0  
**Estimate:** 3

Compare:

```text
Trend Continuation
Bullish Reset
Capitulation Reversal
Bearish Distribution
```

---

## BTC-185 — Implement threshold sweeps

**Priority:** P0  
**Estimate:** 5

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

---

# EPIC T — Research & Learning Loop

## BTC-190 — Store market state for every decision date

**Priority:** P0  
**Estimate:** 3

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

---

## BTC-191 — Create paper-trade outcome dataset

**Priority:** P0  
**Estimate:** 3

Join entry-state features to final outcomes.

---

## BTC-192 — Create strategy comparison framework

**Priority:** P1  
**Estimate:** 3

Compare:

- strategy_v1.0
- candidate strategy versions
- parameter sets

---

## BTC-193 — Implement controlled strategy promotion process

**Priority:** P0  
**Estimate:** 3

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

---

# EPIC U — Manual Trade Tracking

## BTC-200 — Implement recommendation decision journal

**Priority:** P1  
**Estimate:** 2

Decisions:

```text
APPROVED
REJECTED
MODIFIED
MISSED
```

---

## BTC-201 — Add discretionary reason codes

**Priority:** P1  
**Estimate:** 1

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

---

## BTC-202 — Implement actual trade entry

**Priority:** P1  
**Estimate:** 2

Record real manual execution.

---

## BTC-203 — Build Model vs Human comparison

**Priority:** P1  
**Estimate:** 3

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

---

# EPIC V — Reporting & Monitoring

## BTC-210 — Create daily system status report

**Priority:** P1  
**Estimate:** 2

Show:

- latest data timestamp
- data-quality status
- current regime
- active setup
- current recommendation
- paper portfolio status

---

## BTC-211 — Create weekly strategy report

**Priority:** P1  
**Estimate:** 3

Show:

- regime changes
- setup changes
- price levels
- current paper trades
- risk
- recent score movement

---

## BTC-212 — Create alerts

**Priority:** P1  
**Estimate:** 3

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

---

# EPIC W — Testing

## BTC-220 — Unit tests for feature calculations

**Priority:** P0  
**Estimate:** 3

---

## BTC-221 — Look-ahead bias test suite

**Priority:** P0  
**Estimate:** 5

Critical tests:

- future bars unavailable
- future ETF flows unavailable
- future confirmed pivots unavailable
- rolling normalization past-only
- AVWAP anchors point-in-time valid

---

## BTC-222 — Risk invariant tests

**Priority:** P0  
**Estimate:** 3

Verify:

```text
No averaging down
Stops never widen
Risk-at-stop never exceeds limit
No add when STRESS
No add when CROWDING rule blocks
No trade during DATA_QUALITY_FAIL
```

---

## BTC-223 — Paper execution tests

**Priority:** P0  
**Estimate:** 3

Test:

- missed entry
- gap through stop
- multiple tranches
- stop move
- trim
- exit
- funding and fees

---

## BTC-224 — Golden historical scenarios

**Priority:** P1  
**Estimate:** 5

Create hand-reviewed BTC periods and expected strategy behavior.

---

# 10. Suggested Phase 1 Execution Order

```text
BTC-001 → BTC-002 → BTC-003
                  ↓
BTC-010 → BTC-011 → BTC-012 → BTC-013 → BTC-015 → BTC-016
                  ↓
BTC-020 → BTC-021 → BTC-022 → BTC-025
                  ↓
BTC-030 → BTC-031 → BTC-032
                  ↓
BTC-040 → BTC-041
                  ↓
BTC-050..055  Trend
BTC-060..065  Flow
BTC-070..075  Positioning
BTC-080..085  Volatility
                  ↓
BTC-090 → BTC-091 → BTC-095 → BTC-096 → BTC-097
                  ↓
BTC-100 → BTC-101 → BTC-102
                  ↓
BTC-110 → BTC-111
                  ↓
BTC-120 → BTC-121 → BTC-122 → BTC-123
                  ↓
BTC-130 → BTC-131 → BTC-132 → BTC-133
                  ↓
BTC-140 → BTC-141 → BTC-142 → BTC-143 → BTC-144 → BTC-145 → BTC-146
                  ↓
BTC-150 → BTC-151 → BTC-152 → BTC-153 → BTC-154 → BTC-155 → BTC-156 → BTC-157 → BTC-158
                  ↓
BTC-160 → BTC-161 → BTC-162 → BTC-163 → BTC-164 → BTC-165 → BTC-166
                  ↓
BTC-170 → BTC-171
                  ↓
BTC-180 → BTC-181 → BTC-182 → BTC-183 → BTC-184 → BTC-185
                  ↓
BTC-190 → BTC-191 → BTC-193
                  ↓
BTC-220 → BTC-221 → BTC-222 → BTC-223
```

---

# 11. Phase 1 Minimal Viable Scope

To avoid overbuilding, the first full end-to-end version can omit:

- complex macro model
- complex on-chain model
- volume profile
- anchored VWAP
- short setup
- capitulation setup
- live broker integration
- automated execution
- ML models

The first version should support:

```text
BTC daily + weekly + monthly OHLCV
Funding
Open Interest
Futures Basis
ETF Flows

Trend Score
Flow Score
Positioning Score
Volatility Score

Weekly / Monthly Price Levels
Level Clusters
Structure Score

Regime Score

Bull Trend Continuation
Bullish Reset

Entry Conviction
Structural Stop
Risk Sizing
Hold Score
Add Score
Trailing Stop

Paper Trading
Backtesting
Recommendation Report
```

This is enough to test the core thesis.

---

# 12. Phase 1 Definition of Done

Phase 1 is complete when:

- [ ] PostgreSQL schema is migration-controlled
- [ ] Raw BTC market data is stored reproducibly
- [ ] Derivatives data is stored point-in-time correctly
- [ ] ETF flows are stored with availability timestamps
- [ ] Daily, weekly, and monthly canonical bars are generated
- [ ] Trend Score works
- [ ] Flow Score works
- [ ] Positioning Score works
- [ ] Volatility Score works
- [ ] Weekly/monthly price levels are detected without look-ahead
- [ ] Level clusters are created
- [ ] Structure Score works
- [ ] Regime Score works
- [ ] Bull Trend Continuation setup works
- [ ] Bullish Reset setup works
- [ ] Reclaim trigger works
- [ ] Breakout/retest trigger works
- [ ] Higher-low trigger works
- [ ] Entry Conviction works
- [ ] Hard veto engine works
- [ ] Structural stop works
- [ ] Volatility buffer works
- [ ] Risk sizing works
- [ ] No-average-down invariant is enforced
- [ ] Hold Score works
- [ ] Add Score works
- [ ] Pyramiding rules work
- [ ] Trailing structural stop works
- [ ] Trim rules and simulated trims work
- [ ] Paper trader runs autonomously
- [ ] Paper trade results persist to PostgreSQL
- [ ] Recommendation report is generated
- [ ] Event-driven backtest works
- [ ] Fees/slippage/funding are modeled
- [ ] Walk-forward validation works
- [ ] Threshold robustness tests are completed
- [ ] Look-ahead test suite passes
- [ ] Risk invariant test suite passes
- [ ] Every signal is explainable
- [ ] Every signal is reproducible from stored state

---

# 13. Phase 1 Success Criteria

The system should not be promoted to live manual use simply because the backtest is profitable.

Minimum research expectations:

- Positive expectancy after realistic costs
- Positive average R per trade
- Acceptable max drawdown
- Performance not dependent on one BTC regime
- Reasonable behavior across parameter neighborhoods
- Low turnover
- Trade frequency aligned with selective strategy
- Adds improve or at least do not materially damage expectancy
- Structural stops outperform naive arbitrary percentage stops
- No evidence of look-ahead leakage
- Paper trading behaves consistently with historical simulation

---

# 14. Research Questions Phase 1 Must Answer

1. Does a low-frequency regime/setup approach outperform simple BTC momentum?
2. Does the Bullish Reset setup outperform Trend Continuation?
3. Does ETF flow materially improve selectivity?
4. Does derivatives positioning improve timing?
5. Are structural stops better than ATR-only stops?
6. What price-level types provide the strongest invalidation levels?
7. Does entering near support clusters improve R expectancy?
8. Do adds improve total R or merely increase drawdown?
9. What Add Score threshold is robust?
10. Does conviction correlate monotonically with trade quality?
11. Are 80+ conviction trades materially better than 70–79 watch signals?
12. Does waiting for a reclaim or higher low improve results?
13. How much performance is lost through no-chase rules?
14. Which regimes should block new entries entirely?
15. What is the optimal practical maximum risk-at-stop?
16. Does manual discretion improve model outcomes once Phase 3 begins?

---

# 15. Non-Goals for Phase 1

Do not build:

- HFT infrastructure
- Low-latency execution
- Automated live trading
- Reinforcement learning
- Neural networks
- Self-modifying strategies
- Tick-level prediction
- Multi-asset portfolio optimization
- Complex derivatives execution
- Exchange API trading keys
- Automated leverage optimization

The first goal is to answer:

> **Can a transparent, low-frequency, high-conviction BTC swing framework generate robust risk-adjusted returns while trading rarely and managing winners intelligently?**

If the answer is yes, later phases can add sophistication without changing the core architecture.

---

# 16. Recommended First Sprint

## Sprint Goal

Create the data and database foundation required for point-in-time research.

### Sprint Tickets

```text
BTC-001  Python project structure
BTC-002  Strategy config schema
BTC-003  Alembic migrations
BTC-010  PostgreSQL schemas
BTC-011  OHLCV tables
BTC-012  Derivatives tables
BTC-013  ETF flow table
BTC-015  Predictor/recommendation tables
BTC-016  Paper portfolio tables
BTC-020  BTC OHLCV collector
BTC-025  Ingestion audit log
BTC-030  OHLCV data quality
BTC-040  Daily/weekly/monthly canonical bars
BTC-041  Rolling statistics framework
```

### Sprint Exit Criteria

At the end of Sprint 1:

```text
Market data
    ↓
Python ingestion
    ↓
PostgreSQL raw schema
    ↓
Quality checks
    ↓
Canonical daily/weekly/monthly BTC dataset
```

must run reproducibly from scratch.

---

# 17. Recommended Second Sprint

## Sprint Goal

Produce the first complete market-state score.

### Sprint Tickets

```text
BTC-021  Derivatives collector
BTC-022  ETF flow collector
BTC-031  Derivatives data quality

BTC-050..055  Trend Engine
BTC-060..062  Core Flow Features
BTC-065       Core Flow Score
BTC-070..074  Positioning Engine
BTC-080..085  Volatility Engine
BTC-100..102  Regime Engine
```

### Sprint Exit Criteria

For every evaluation date the system can produce:

```text
Trend Score
Flow Score
Positioning Score
Volatility Score
Regime Score
Regime Classification
```

with a complete audit trail.

---

# 18. Recommended Third Sprint

## Sprint Goal

Turn market state into actionable trade candidates.

### Sprint Tickets

```text
BTC-090
BTC-091
BTC-095
BTC-096
BTC-097

BTC-110
BTC-111

BTC-120
BTC-121
BTC-122
BTC-123

BTC-130
BTC-131
BTC-132
BTC-133
```

### Sprint Exit Criteria

The system can produce:

```text
NO TRADE
WATCH
VALID TRADE
```

with:

- setup
- conviction
- entry zone
- structural level
- reason codes

---

# 19. Recommended Fourth Sprint

## Sprint Goal

Add capital protection and full position lifecycle management.

### Sprint Tickets

```text
BTC-140..146
BTC-150..158
```

### Sprint Exit Criteria

The engine can:

```text
ENTER SMALL
HOLD
RAISE STOP
ADD
EXIT
```

while respecting all risk invariants.

---

# 20. Recommended Fifth Sprint

## Sprint Goal

Validate the complete system historically and in paper mode.

### Sprint Tickets

```text
BTC-160..166
BTC-170..171
BTC-180..185
BTC-190
BTC-191
BTC-193
BTC-220..223
```

### Sprint Exit Criteria

The complete lifecycle is:

```text
Historical / live data
        ↓
Predictor
        ↓
Recommendation
        ↓
Paper execution
        ↓
Trade lifecycle
        ↓
Outcome
        ↓
Research database
        ↓
Performance report
```

with no manual intervention required for the paper portfolio.

---

# 21. Final Product Behavior

Most evaluation periods:

```text
NO TRADE
```

Some periods:

```text
WATCH
Bullish Reset forming
```

Rarely:

```text
ACTIONABLE

ENTER INITIAL TRANCHE
Conviction: 88
Risk: 0.50% NAV
Entry Zone: ...
Stop: ...
R/R: ...
```

During successful trades:

```text
HOLD

or

ADD
New structure confirmed
Stop improved
Risk-at-stop remains controlled
```

During deterioration:

```text
NO ADD
TIGHTEN RISK
TRIM
```

On invalidation:

```text
EXIT
```

The paper portfolio executes all valid strategy actions automatically.

The human receives the same information but remains fully responsible for any real-world trade execution.

---

**Document Version:** 1.0  
**Project:** Bitcoin Swing Predictor  
**Primary Mode:** Human-guided trading + autonomous paper portfolio  
**Database:** PostgreSQL  
**Implementation Language:** Python  
**Execution Horizon:** Multi-week BTC swing trading
