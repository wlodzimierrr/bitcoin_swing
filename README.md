# Bitcoin Swing Predictor

Low-frequency Bitcoin swing trading decision-support system.

The initial implementation is organized around the project rulebook and ticket
backlog:

- `bitcoin_swing_predictor_rulebook_v1.md`
- `bitcoin_swing_predictor_project_tickets_v1.md`
- `bitcoin_swing_predictor_project_tickets_structured_v1.md`

## Development

Create a virtual environment and install the package in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Run database migrations against a database URL:

```bash
alembic \
  -x database_url=postgresql+psycopg://user:password@localhost/dbname \
  -x runtime_role=btc_predictor_runtime \
  -x research_role=btc_predictor_research \
  upgrade head
```

The application also exposes migration helpers for tests and scripts:

```python
from btc_predictor.db import upgrade_database, verify_research_connection

upgrade_database("postgresql+psycopg://user:password@localhost/dbname")
verify_research_connection("postgresql+psycopg://user:password@localhost/dbname")
```

Predictor output is persisted through `signals.predictor_runs`,
`signals.recommendations`, and `signals.recommendation_reason_codes`. Together
these tables carry the strategy/config/code identity, point-in-time data cutoff,
scores, levels, risk payload, action, and ordered reason codes needed to
reconstruct a historical recommendation.

Paper trading state is persisted through `portfolio.paper_accounts`,
`portfolio.positions`, `portfolio.tranches`, `portfolio.paper_orders`,
`portfolio.stops`, `portfolio.position_events`, and
`portfolio.completed_trades`.

BTC OHLCV collection is provider-injected through
`OhlcvCollectionRequest` and `collect_btc_ohlcv`. The collector fetches raw
`1h` bars, writes them with conflict-do-nothing semantics so existing raw
records are not silently changed, and derives complete daily, weekly, and
monthly bars from the same point-in-time source data.

Canonical market bars can be generated with `build_canonical_market_bars`.
They use `1h` BTC source bars that were closed and ingested by the
`data_available_at` cutoff. The canonical session is UTC: daily bars start at
00:00 UTC, weekly bars start Monday 00:00 UTC, and monthly bars start on the
first calendar day at 00:00 UTC.

BTC derivatives collection is provider-injected through
`DerivativesCollectionRequest` and `collect_btc_derivatives`. Funding, open
interest, futures basis, liquidations, and perpetual volume are normalized into
raw point-in-time records, persisted idempotently, and can be aggregated through
`aggregate_btc_derivatives_available_at` without using observations unavailable
at the signal timestamp.

ETF flow collection is provider-injected through `EtfFlowCollectionRequest` and
`collect_etf_flows`. Daily fund flows and optional AUM values are normalized to
USD, persisted as immutable raw revisions, and checked against expected
publication dates so missing flow days are explicit.

Macro data collection is provider-injected through `MacroDataCollectionRequest`
and `collect_macro_data`. The initial candidate set covers VIX, DXY or an
equivalent dollar proxy, a Nasdaq proxy, US 2Y yield, and a real-yield proxy.
Observations are persisted as immutable `raw.generic_series` revisions with
deterministic series IDs, UTC availability timestamps, and explicit missing
observation dates.

On-chain data collection is provider-injected through
`OnchainDataCollectionRequest` and `collect_onchain_data`. The initial candidate
set covers SOPR, MVRV, realized P/L, short-term holder realized price, and
exchange flows. Observations use deterministic `raw.generic_series` IDs,
preserve provider revisions, and report missing calendar-day observations.

Ingestion jobs can be audited through `IngestionAuditRecord` and
`build_ingestion_audit_insert_ignore`. Audit rows live in
`system.ingestion_audit_log` and capture job timing, fetched/inserted counts,
failures, gaps, provider response metadata, config version, and collector-level
reason codes when applicable.

OHLCV quality checks are available through `OhlcvQualityConfig` and
`validate_ohlcv_quality`. They detect duplicate bars, impossible OHLC values,
missing periods, stale data, and extreme malformed values with stable reason
codes that can be persisted to the ingestion audit log.

Derivatives quality checks are available through `DerivativesQualityConfig` and
`validate_derivatives_quality`. They detect stale funding, negative open
interest, provider discontinuities, missing exchange snapshots, and provider
unit changes with stable reason codes for audit persistence.

Predictor decisions can apply the `DATA_QUALITY_FAIL` gate through
`apply_data_quality_gate`. Critical data-quality failures veto new `ENTER`
recommendations to `NO_TRADE` and veto `ADD` recommendations to `HOLD`, while
preserving existing-position state and ordered failure reason codes for
`signals.recommendation_reason_codes`.

Feature generation includes a past-only rolling statistics framework in
`btc_predictor.features`. It provides rolling means, rolling volatility,
z-scores, percentiles, ATR, and historical normalization. Mean, volatility, and
ATR use trailing windows through the current completed observation; z-scores,
percentiles, and historical normalization compare the current observation only
against prior history.

The trend feature helpers include `four_week_momentum`, which implements
`MOMENTUM_4W` as `P_t / P_t-28 - 1` for canonical daily closes.
They also include `twelve_week_momentum`, which implements `MOMENTUM_12W` as
`P_t / P_t-84 - 1`.
The `twenty_week_ma_distance` helper implements `MA_DISTANCE_20W` as
`(P_t - MA_20W) / MA_20W` for canonical weekly closes.
The `fifty_two_week_high_distance` helper implements `HIGH_DISTANCE_52W` as
`(P_t - H_52W) / H_52W` using the trailing 52-week high through the current
completed weekly bar.
Weekly market structure classification compares each weekly high/low against
the prior week and emits the rulebook labels `HH_HL`, `HL_ONLY`, `MIXED`,
`LH_ONLY`, and `LH_LL` with stable raw scores and reason codes.
`calculate_trend_score` combines normalized trend components with the rulebook
weights and converts the raw composite to a 0-100 score using the standard
normal CDF. Its result includes inputs, weights, contributions, interpretation,
and a stable reason code for deterministic recomputation.

Flow feature helpers include `five_day_etf_flow` and `twenty_day_etf_flow`,
which implement `ETF_FLOW_5D`, `ETF_NORM_5D`, `ETF_FLOW_20D`, and
`ETF_NORM_20D` from the latest ETF flow revisions available at signal time.
They use publication-day windows, report normalized values when latest fund AUM
is available, and emit reason codes instead of silently filling missing inputs
or denominators. `etf_flow_acceleration` implements `FLOW_ACCEL` as
`ETF_NORM_5D - ETF_NORM_20D / 4` and records the normalized inputs used in the
calculation. `spot_perp_participation` implements `SPOT_DOMINANCE` as
`z(SpotVolumeGrowth) - z(PerpVolumeGrowth)` using available spot and perpetual
volume observations, with a row adapter for spot OHLCV and perp volume records.
`spot_perp_cvd_spread` implements `CVD_SPREAD` as
`z(SPOT_CVD) - z(PERP_CVD)` over point-in-time CVD observations.

Runtime environment can be selected with `BTC_PREDICTOR_ENV`. The default is
`dev`.

Strategy parameters are loaded from the versioned TOML file at
`btc_predictor/config/strategy/default.toml`. Startup code can load runtime and
strategy config together, validating both before returning:

```python
from btc_predictor.config import load_application_config

config = load_application_config()
run_metadata = config.strategy.run_metadata()
```
