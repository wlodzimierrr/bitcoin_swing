# Bitcoin Swing Predictor — Structured Tickets v1

This file reformats the implementation tickets from `bitcoin_swing_predictor_project_tickets_v1.md` into a compact execution-ticket style.

Status values:

```text
TODO / IN_PROGRESS / BLOCKED / DONE
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
- **Acceptance Criteria:**
  - Installable Python package
  - Central configuration loader
  - Structured logging
  - Test runner works
  - No secrets committed
  - Environment-specific configuration supported
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Strategy parameters are externalized
  - Config validated at startup
  - Invalid configs fail fast
  - Config version is persisted with every run
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-003 Add database migration framework
- **Description:**
  Use Alembic.
- **Status:** DONE
- **Acceptance Criteria:**
  - Fresh database can be built from migrations
  - Upgrade and downgrade tested
  - Schema state can be reproduced exactly
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Schemas created through migration
  - Application DB user has correct permissions
  - Research and runtime connections verified
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Unique primary key
  - UTC timestamps
  - Duplicate ingestion is idempotent
  - Missing bars can be detected
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-012 Create derivatives raw schemas
- **Description:**
  Tables for:

  - Funding
  - Open interest
  - Futures basis
  - Liquidations
  - Perp volume
- **Status:** DONE
- **Acceptance Criteria:**
  - Exchange/source preserved
  - Units documented
  - Timestamp semantics documented
  - Point-in-time availability supported
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Historical revisions can be represented
  - Signal jobs query only data available at signal time
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Can store VIX, yields, DXY proxies, liquidity measures, and on-chain metrics
  - Revisions do not overwrite historical availability state
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  Every recommendation is reconstructable later.
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  Can compare recommendation vs actual execution.
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `portfolio.manual_trade_journal` in Alembic revision `0017_create_manual_trade_journal_schema`.
  - Linked journal entries to `signals.recommendations` for suggested-versus-actual execution comparison.
  - Captured actual entry, size, stop, exit, manual decision, override reason, and notes.

## EPIC C — Data Ingestion

#### BTC-020 Implement BTC OHLCV collector
- **Description:**
  Collect at minimum:

  - 1h data
  - derive daily
  - derive weekly
  - derive monthly
- **Status:** DONE
- **Acceptance Criteria:**
  - Idempotent ingestion
  - UTC normalization
  - Retry support
  - Missing interval detection
  - Daily, weekly, and monthly bars derive from point-in-time source data
  - Raw records never silently changed
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added provider-injected BTC OHLCV collection with retry support.
  - Collected canonical raw `1h` bars with UTC validation and conflict-do-nothing inserts.
  - Derived complete daily, weekly, and monthly bars from available `1h` source bars.
  - Reported missing source intervals and skipped incomplete derived periods.

#### BTC-021 Implement derivatives collector
- **Description:**
  Collect:

  - funding
  - OI
  - futures basis
  - liquidations
  - perp volume
- **Status:** DONE
- **Acceptance Criteria:**
  - Provider-specific raw data normalized
  - Aggregate BTC view can be generated
  - No future timestamps leak into derived data
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Daily flow loaded
  - AUM normalization supported where available
  - available_at correctly captured
  - Missing publication days handled explicitly
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added deterministic OHLCV quality reporting with stable reason codes for duplicate bars, impossible OHLC, missing periods, stale data, and extreme malformed values.
  - Added typed quality configuration for staleness, close-change, bar-range, and volume thresholds with fast validation of invalid thresholds.
  - Kept extreme-value checks scoped per exchange/symbol/timeframe/provider series so multi-provider inputs are reproducible.
  - Verified ordered reason codes can be persisted through the existing ingestion audit log.

#### BTC-031 Implement derivatives quality checks
- **Description:**
  Detect:

  - stale funding
  - impossible negative OI
  - sudden provider discontinuities
  - missing exchange snapshots
  - unit changes
- **Status:** DONE
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Predictor can still report existing position state
  - Failure reasons are persisted
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Consistent session definition
  - Weekly boundaries documented
  - Monthly boundaries documented
  - Reproducible aggregation
  - Point-in-time correct
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added a canonical BTC market-bar session definition using UTC daily, Monday-start weekly, and first-calendar-day monthly boundaries.
  - Added `build_canonical_market_bars` to generate daily, weekly, and monthly bars only from closed `1h` source bars ingested by the point-in-time `data_available_at` cutoff.
  - Reused the existing complete-bucket OHLCV aggregation logic for reproducible open/high/low/close/volume calculations.
  - Documented daily, weekly, and monthly session boundaries in the README and pinned them with focused tests.

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
- **Acceptance Criteria:**
  All rolling calculations use only past information.
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.
- **Implementation Notes:**
  - Added pure-Python rolling statistics helpers for rolling means, volatility, z-scores, percentiles, ATR, and historical normalization.
  - Kept rolling means, volatility, and ATR on trailing windows through the current completed observation.
  - Kept z-scores, percentiles, and historical normalization on prior-history windows that exclude the current value from the baseline.
  - Added lookahead-safety tests proving earlier outputs do not change when future values or bars are appended.

## EPIC F — Trend Engine

#### BTC-050 Implement 4-week momentum
- **Description:**
  \[
  M_4=P_t/P_{t-28}-1
  \]
- **Status:** DONE
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Output 0–100
  - Inputs persisted
  - Score explainable
  - Historical recomputation deterministic
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `calculate_trend_score` implementing the rulebook weighted composite and `100 * Phi(TrendRaw)` conversion.
  - Added typed `TrendScoreInput` and `TrendScoreResult` payloads that expose component inputs, weights, contributions, interpretation, and stable reason code.
  - Added deterministic serialization through `TrendScoreResult.as_record()` for historical recomputation and persistence.
  - Added focused tests for formula output, score bounds, explainability, weight validation, score-band interpretation, and recomputation from persisted inputs.

## EPIC G — Flow Engine

#### BTC-060 Implement 5-day ETF flow feature
- **Description:**
  Complete the ticket scope for implement 5-day etf flow feature.
- **Status:** DONE
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Missing P1 inputs are not silently filled with zero
  - Output records `FLOW_MODEL = ETF_CORE` or `FLOW_MODEL = ETF_SPOT_PERP_FULL`
  - Formula weights are loaded from versioned strategy config
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.
- **Implementation Notes:**
  - Added `FLOW_SCORE` using the full model when ETF, acceleration, CVD spread, and spot dominance z-score inputs are available.
  - Added the `ETF_CORE` fallback using ETF-only weights when P1 spot/perp inputs are missing, without zero-filling missing P1 components.
  - Persisted selected flow model, inputs, weights, contributions, score, interpretation, reason codes, and config metadata through `FlowScoreResult.as_record()`.
  - Added `full_flow` weights to the versioned strategy config and validated exact full/core flow weight keys at startup.

## EPIC H — Positioning Engine

#### BTC-070 Implement funding health
- **Description:**
  Input:

  - 7d funding average
  - 180d rolling z-score
- **Status:** DONE
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-073 Implement futures-basis health
- **Description:**
  Complete the ticket scope for implement futures-basis health.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-074 Implement Positioning Score
- **Description:**
  \[
  PositioningScore=
  0.35FundingHealth
  +0.30OIHealth
  +0.20BasisHealth
  +0.15LeverageHealth
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-075 Implement CROWDING flag
- **Description:**
  Effect:

  ```text
  NO ADD
  REDUCE ENTRY QUALITY
  OPTIONAL TIGHTER PROFIT PROTECTION
  ```
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

## EPIC I — Volatility Engine

#### BTC-080 Implement RV7 / RV20 / RV60
- **Description:**
  Complete the ticket scope for implement rv7 / rv20 / rv60.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

#### BTC-081 Implement compression ratio
- **Description:**
  \[
  RV_7/RV_{60}
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

#### BTC-082 Implement volatility percentile
- **Description:**
  Complete the ticket scope for implement volatility percentile.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

#### BTC-083 Implement orderliness score
- **Description:**
  Penalize:

  - extreme ranges
  - disorderly downside
  - liquidation cascades
  - volatility spikes
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-084 Implement Volatility Score
- **Description:**
  Complete the ticket scope for implement volatility score.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-085 Implement STRESS flag
- **Description:**
  Effect:

  ```text
  NO ADD
  REDUCE MAX EXPOSURE
  OPTIONALLY BLOCK NEW TRADES
  ```
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

## EPIC J — Price-Level / Structure Engine

#### BTC-090 Detect weekly swing highs/lows
- **Description:**
  Complete the ticket scope for detect weekly swing highs/lows.
- **Status:** TODO
- **Acceptance Criteria:**
  - Point-in-time detection
  - No use of future bars before level confirmation
  - Detection timestamp persisted separately from level timestamp
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

#### BTC-091 Detect monthly swing highs/lows
- **Description:**
  Complete the ticket scope for detect monthly swing highs/lows.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-092 Detect breakout/reclaim levels
- **Description:**
  Complete the ticket scope for detect breakout/reclaim levels.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

#### BTC-093 Implement anchored VWAP support
- **Description:**
  Anchor types:

  - major swing low
  - major swing high
  - breakout
  - capitulation event
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.

#### BTC-094 Implement volume-profile levels
- **Description:**
  Candidates:

  - POC
  - HVN
  - VAH
  - VAL
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.

#### BTC-095 Implement level clustering
- **Description:**
  Combine nearby levels into support/resistance zones.
- **Status:** TODO
- **Acceptance Criteria:**
  - Cluster boundaries persisted
  - Member levels linked
  - Confluence score available
  - No double-counting of nearby lines
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

#### BTC-096 Implement level-strength score
- **Description:**
  Inputs:

  - timeframe
  - touch count
  - reaction magnitude
  - volume
  - confluence
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Output records `REGIME_MODEL = CORE_MARKET_ONLY` or `REGIME_MODEL = FULL_MACRO_ONCHAIN_LIQUIDITY`
  - Missing P1 inputs are not silently filled with zero
  - Formula weights are loaded from versioned strategy config
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-101 Add regime smoothing
- **Description:**
  \[
  R_t=0.7R_{t-1}+0.3R_{new}
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

#### BTC-112 Implement Capitulation Reversal setup
- **Description:**
  Require confirmation after capitulation.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.

#### BTC-113 Implement Bearish Distribution setup
- **Description:**
  Use stricter short requirements.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.

#### BTC-114 Implement CAPITULATION flag
- **Description:**
  Complete the ticket scope for implement capitulation flag.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

#### BTC-115 Implement EUPHORIA flag
- **Description:**
  Complete the ticket scope for implement euphoria flag.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** S
- **Risk:** Low.

## EPIC M — Entry Trigger Engine

#### BTC-120 Implement reclaim trigger
- **Description:**
  Complete the ticket scope for implement reclaim trigger.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-121 Implement breakout + retest trigger
- **Description:**
  Complete the ticket scope for implement breakout + retest trigger.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-122 Implement higher-low confirmation trigger
- **Description:**
  Complete the ticket scope for implement higher-low confirmation trigger.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-123 Implement no-chase filter
- **Description:**
  If price moves materially outside intended entry zone:

  ```text
  NO TRADE
  ```
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

## EPIC N — Scoring Engine

#### BTC-130 Implement Entry Conviction
- **Description:**
  \[
  EntryConviction =
  0.20Trend
  +0.20Regime
  +0.20Flow
  +0.15Positioning
  +0.10Volatility
  +0.15Structure
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

## EPIC O — Risk Engine

#### BTC-140 Implement structural invalidation selection
- **Description:**
  Select best invalidation level based on active setup and nearby structure.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - If no credible structural reward reference exists, the R/R filter fails
  - Selected reward reference is persisted with the recommendation
  - R/R calculation is reproducible from stored levels and entry/stop values
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** XS
- **Risk:** Low.

#### BTC-152 Implement Hold Score
- **Description:**
  \[
  HoldScore =
  0.25Regime+
  0.20Trend+
  0.20Flow+
  0.15Positioning+
  0.10Structure+
  0.10MomentumPersistence
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-153 Implement Add Score
- **Description:**
  \[
  AddScore=
  0.20HoldScore+
  0.25NewStructure+
  0.20Flow+
  0.15Positioning+
  0.10Momentum+
  0.10RiskImprovement
  \]
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Trim signals include reason codes
  - Trim signals are distinct from full exits
  - Paper trader can simulate partial reductions once BTC-164 is complete
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-163 Implement simulated adds
- **Description:**
  Complete the ticket scope for implement simulated adds.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-164 Implement simulated trims
- **Description:**
  Complete the ticket scope for implement simulated trims.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-172 Add machine-readable JSON output
- **Description:**
  Useful for dashboards, notifications, or future automation.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** S
- **Risk:** Low.

#### BTC-182 Implement walk-forward validation
- **Description:**
  No single static train/test split.

  Use rolling or expanding windows.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** L
- **Risk:** High.

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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-191 Create paper-trade outcome dataset
- **Description:**
  Join entry-state features to final outcomes.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** XS
- **Risk:** Low.

#### BTC-202 Implement actual trade entry
- **Description:**
  Record real manual execution.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** M
- **Risk:** Medium.

## EPIC W — Testing

#### BTC-220 Unit tests for feature calculations
- **Description:**
  Complete the ticket scope for unit tests for feature calculations.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
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
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P0
- **Complexity:** M
- **Risk:** Medium.

#### BTC-224 Golden historical scenarios
- **Description:**
  Create hand-reviewed BTC periods and expected strategy behavior.
- **Status:** TODO
- **Acceptance Criteria:**
  - Implementation is covered by focused tests where practical
  - Output is deterministic and reproducible
  - Relevant configuration and reason codes are persisted where applicable
- **Dependencies:** Follow roadmap execution order in `bitcoin_swing_predictor_project_tickets_v1.md`
- **Priority:** P1
- **Complexity:** L
- **Risk:** High.
