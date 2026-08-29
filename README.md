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

BTC price-source research is versioned as `PRICE_SOURCE_POLICY_V1` in
`btc_predictor.research`. Empirical BTC-019 research rejected Bitstamp
`BTC/USD` (`btcusd`) as the sole canonical reference, while retaining it as a
primary raw OHLCV source. Coinbase
`BTC-USD` and Bitfinex `BTC/USD` (`tBTCUSD`) are required independent validation
venues. Coin Metrics `btc-usd` is an optional institutional benchmark and
yfinance `BTC-USD` remains a noncanonical sanity check. The reference-price
role is explicitly separate from any execution venue, and historical fallback
splicing is prohibited in V1.

`compare_price_sources` produces a point-in-time report from synchronized `1h`
histories. It measures provider coverage, gaps, duplicates, close/high/low and
wick divergence, daily-return and ATR divergence, structural swing and
breakout/reclaim differences, stop-touch sensitivity, and MFE/MAE sensitivity.
Results are grouped into price, indicator, decision, and portfolio tiers. The
report cannot become decision-ready until Bitstamp, Coinbase, and Bitfinex have
at least two years of common bars, an explicit canonical-source decision is
recorded, and every top divergence event has a structured manual review.
Provider endpoints, access and entitlement diagnostics, pagination limits,
constraints, and candle semantics are persisted with the policy record.
The decision and its three-year evidence are persisted under
`research_artifacts/btc019/PRICE_SOURCE_POLICY_V1/`; no provider is currently
approved as strategy-canonical.

Follow-up `BTC_REFERENCE_COMPOSITE_V1` research compares Bitstamp, Coinbase,
and Bitfinex against median-OHLC, confirmed-extremes, and clipped-center
composites. Candidate definitions were frozen before an untouched 2020-2022
validation. Median OHLC handled the known isolated-wick and consensus-stop
cases, but the result is `RESEARCH_INCONCLUSIVE` because external degraded-bar
frequency and swing disagreement missed their predeclared gates. Composite
records remain research-only in `derived.btc_reference_composite`; neither
`PRICE_SOURCE_POLICY_V1` nor the production canonical reference was changed.

BTC-019B diagnoses the two failed V1 gates without changing the composite or
its frozen thresholds. Reproduce the immutable diagnostic artifacts with
Python 3.12+:

```bash
python -m btc_predictor.research.btc019b_diagnostics \
  --raw-dir data/btc_reference_composite_v1/external_2019-12-01_2022-12-31 \
  --v1-artifact-dir research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V1 \
  --output-dir /tmp/btc019b-reproduction
```

The committed result is under `research_artifacts/btc019b/` and remains
`MIXED`: the 286 degraded-but-usable hours had no measured
structural or trade/risk effect, while three unusable disagreement hours caused
two complete weekly buckets to be omitted, four exact swing-set differences,
and two breakout/reclaim state differences. V1 remains
`RESEARCH_INCONCLUSIVE`, BTC-019 remains in progress, and the production
canonical reference remains unresolved.

BTC-019C freezes the research-only `BTC_REFERENCE_COMPOSITE_V2` protocol at
definition SHA-256
`bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a`.
The immutable definition and governance report are under
`research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2/`.
No V2 external validation was performed and the sealed 2015-2019 candidate
sample was not opened. BTC-019 remains in progress; normal Phase-1 development
may resume before a later validator opens that sample against the frozen hash.

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

Lower-level numerical work is isolated in `btc_predictor.quant`, a typed
NumPy/SciPy core with no database, configuration, signal-action, or domain-model
dependencies. Its `FLOAT64_V1` policy standardizes internal arrays on owned
`float64` values, exact shape matching, explicit NaN handling, unconditional
infinity rejection, `1e-12` comparison tolerances, and explicitly seeded PCG64
simulation. Existing Decimal-facing feature APIs remain unchanged; migration to
the array core can proceed ticket by ticket. The complete conventions are in
`btc_predictor/quant/POLICY.md`.

BTC-043 provides NumPy kernels for rolling mean and volatility, prior-window
z-scores and percentile ranks, historical normalization, close-to-close
returns, true range, ATR, and annualized realized volatility. Outputs are
parity-tested against the BTC-041 Decimal implementation at `1e-12` absolute
and relative tolerance. Batch results match prefix-by-prefix calculations,
warm-up and missing values remain explicit, and the existing
`btc_predictor.features` APIs retain their Decimal/`None` surface while
delegating numerical work to the vectorized core.

Volatility feature helpers include
`rv_7_20_60_from_daily_bars`, which calculates annualized close-to-close
realized volatility for 7-, 20-, and 60-day windows from point-in-time canonical
daily bars. `volatility_compression_ratio` implements
`VOL_COMPRESSION_RATIO = RV_7 / RV_60` from persisted realized-volatility
outputs and emits stable reason codes for missing inputs or a zero RV60
denominator. `volatility_percentile` implements `VOL_PERCENTILE_2Y` as the
current RV20 percentile rank against prior RV20 history in the trailing 730-day
window. `calculate_orderliness_score` starts from 100 and subtracts configured
penalties for extreme ranges, disorderly downside returns, liquidation cascades,
and volatility spikes, while persisting thresholds, weights, penalties, and
reason codes. `calculate_stress_flag` emits the hard `STRESS` override from
extreme volatility, liquidation cascades, disorderly downside, abnormal
funding/basis, or systemic shock inputs, with persisted exposure-reduction
settings and optional new-trade blocking loaded from the versioned strategy
config. `calculate_capitulation_flag` emits `CAPITULATION` for confirmed
downside washouts: either an explicit systemic shock, or a severe downside
return plus confirmation from extreme range, liquidation cascade, volatility
spike, or negative funding flush. `calculate_euphoria_flag` emits `EUPHORIA`
for confirmed upside excess: either an explicit systemic euphoria input, or a
large upside return plus confirmation from extreme range, overheated funding,
overheated basis, extreme OI intensity, or volatility spike.

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

Price-level helpers include `detect_weekly_swing_levels`, which confirms
weekly swing highs and lows only after the configured right-side weekly bars
have closed and been ingested. Each `WeeklySwingLevel` persists the original
level timestamp separately from the later detection timestamp.
`detect_monthly_swing_levels` applies the same point-in-time confirmation model
to canonical monthly bars, using calendar-month close times and persisting each
`MonthlySwingLevel` for deterministic replay. `detect_breakout_reclaim_levels`
detects breakout levels from confirmed swing highs and reclaim levels from
confirmed swing lows, using only source levels and confirmation bars available
at signal time. Breakout/reclaim close buffers are loaded from versioned
`price_levels` config. `calculate_anchored_vwap` builds anchored VWAP records
from major swing lows/highs, breakout levels, and capitulation events, using
the configured HLC3/close price source and only bars closed and ingested by the
signal time. `calculate_volume_profile_levels` builds POC, HVN, VAH, and VAL
records from deterministic price bins, with bin size, value-area coverage, HVN
thresholds, minimum bars, and price source controlled by versioned
`price_levels` config. `cluster_price_levels` combines nearby level records
into support/resistance zones using the configured cluster-distance fraction,
persists member links, and assigns a confluence score from distinct source
families, timeframes, and repeated touches without counting exact duplicates.
`calculate_level_strength` scores clustered levels from timeframe, touch count,
reaction magnitude, volume percentile, and confluence inputs, using versioned
weights and normalization thresholds from `price_levels`.
`calculate_structure_score` combines level strength, entry location, R/R
quality, and confluence into the Phase 1 structure score. Its cluster helper
uses the nearest support zone below entry and nearest resistance target above
entry, without requiring AVWAP or volume-profile evidence.

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
`z(SPOT_CVD) - z(PERP_CVD)` over point-in-time CVD observations. Flow Score
combines z-normalized flow components using versioned strategy-config weights
and records either `FLOW_MODEL = ETF_CORE` or
`FLOW_MODEL = ETF_SPOT_PERP_FULL`; missing P1 inputs trigger the ETF-core
fallback without zero-filling.

Regime Score combines Trend, Flow, Macro, On-chain, Volatility, and Liquidity
inputs when the full model is available. Until those P1 models exist,
`calculate_regime_score` records `REGIME_MODEL = CORE_MARKET_ONLY` and uses the
configured Trend/Flow/Volatility/Positioning fallback without zero-filling
missing core inputs. `calculate_regime_smoothing` then persists
`REGIME_SMOOTHED_SCORE` as
`0.70 * previous_smoothed_score + 0.30 * new_regime_score` using versioned
`regime_smoothing` config. First-run bootstrap uses the raw regime score and
records the missing previous value explicitly. `calculate_regime_classification`
persists `REGIME_CLASSIFICATION` from the configured regime thresholds, covering
Strong Bull through Strong Bear without relying on hard-coded runtime buckets.

Setup detector helpers include `detect_bull_trend_continuation`, which persists
`SETUP_BULL_TREND_CONTINUATION` from the configured hard filters for Regime,
Trend, Flow, Positioning, Structure, STRESS, severe CROWDING, and R/R. Missing
inputs block completion, while failed filters are kept as deterministic reason
codes. `detect_bullish_reset` persists `SETUP_BULLISH_RESET` for pullbacks in
an intact bull regime, requiring a configured correction band, improving funding
health, stable or improving OI health, improving flow acceleration, strong
structure, a confirmed entry trigger, sufficient entry conviction, and R/R.
`detect_capitulation_reversal` persists `SETUP_CAPITULATION_REVERSAL` by
requiring an upstream capitulation flag plus a later confirmation trigger within
the configured freshness window, with Structure, Entry Conviction, and R/R
checks kept explicit. `detect_bearish_distribution` persists
`SETUP_BEARISH_DISTRIBUTION` as the stricter short-side setup, requiring bearish
Regime, Trend, Flow, Positioning, and Structure ceilings, a distribution flag, a
confirmed short trigger, no STRESS, stronger Entry Conviction, and higher R/R.

Positioning feature helpers include `funding_health`, which implements
`FUNDING_HEALTH` from the current 7-day average funding rate and its 180-day
rolling z-score. The result records the health-curve parameters and emits stable
reason codes for missing funding input, insufficient history, or zero-variance
history. `open_interest_growth_health` implements `OI_GROWTH_HEALTH` from
`OI_GROWTH_7D = OI_t / OI_t-7 - 1`, using rolling normalization rather than
fixed permanent thresholds and keeping the selected OI unit explicit.
`open_interest_intensity` implements `OI_INTENSITY = AggregateOI / BTCMarketCap`
and converts the point-in-time ratio into a 180-day historical percentile, with
high percentile readings mapped to lower health scores. `futures_basis_health`
implements `FUTURES_BASIS_HEALTH` from average annualized futures basis and its
180-day rolling z-score, preferring moderately positive basis while penalizing
unusually weak or crowded readings. `calculate_positioning_score` implements the
rulebook composite from funding, OI, basis, and leverage health components,
using versioned strategy-config weights and persisting contributions plus config
metadata. `calculate_crowding_flag` emits the `CROWDING` flag from excessive
funding, basis, or leverage readings, with configured thresholds and persisted
effects for blocking adds, reducing entry quality, and optional profit
protection tightening.

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
