# RBT-002 historical input coverage inventory

`INVENTORY_HISTORICAL_INPUT_COVERAGE_V1` under `RESEARCH_BACKTEST_POLICY_V3`. Evidence class `RESEARCH_BACKTEST_NON_CERTIFYING`, canonical reference `UNRESOLVED`.
Inventory SHA-256 `b4b51fc4e46fee18c4d228f985e2efaeb6db6d577916e2390ac35398aed6a106` over the canonical bytes of `rbt002_input_coverage_inventory_v1.json`.

Nothing here is a trading outcome. Holdout and pre-2020 rows were only counted.

## Input surface (policy V3 section 5A)

592 inputs: 36 owner input types and 68 owner call sites.

| family | raw leaf inputs | inputs drawing on the family (direct or upstream) |
| --- | ---: | ---: |
| BTC_MARKET_CAP | 5 | 58 |
| CVD | 0 | 7 |
| DISCRETIONARY_ASSERTION | 0 | 7 |
| ENGINE_STATE | 0 | 62 |
| ETF_FLOW_AND_AUM | 11 | 64 |
| FUNDING_RATE | 12 | 70 |
| FUTURES_BASIS | 12 | 66 |
| LIQUIDATIONS | 13 | 64 |
| MACRO_ONCHAIN_LIQUIDITY | 0 | 3 |
| OPEN_INTEREST | 13 | 69 |
| PERP_VOLUME | 13 | 20 |
| REFERENCE_PRICE_1H | 25 | 198 |
| SHARED_RAW_VOLUME_1H | 14 | 57 |
| STRATEGY_CONFIG | 0 | 179 |
| US_EQUITY_MARKET_CLOSURES | 2 | 50 |

| kind | inputs |
| --- | ---: |
| ABSENT_RULEBOOK_FALLBACK | 11 |
| DERIVED_BY_OWNER | 189 |
| DISCRETIONARY | 7 |
| ENGINE_STATE | 62 |
| OWNERLESS_CERTIFIED_DEFINITION | 3 |
| OWNERLESS_RULEBOOK_FALLBACK | 2 |
| OWNERLESS_UNDEFINED | 35 |
| RAW_HISTORICAL | 104 |
| STRATEGY_CONFIG | 179 |

Owner-less inputs:

- `ADD_MOMENTUM_SCORE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `CORRECTION_FROM_LOCAL_HIGH` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `DATA_RISK_EXIT_PREDICATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `DISTRIBUTION_STATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `DOWNSIDE_RETURN` (OWNERLESS_UNDEFINED; Entry Conviction: volatility)
- `FLOW_SUPPORTIVE_PREDICATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `FLOW_Z_ETF_NORM_20D` (OWNERLESS_UNDEFINED; Entry Conviction: flow)
- `FLOW_Z_ETF_NORM_5D` (OWNERLESS_UNDEFINED; Entry Conviction: flow)
- `FLOW_Z_FLOW_ACCEL` (OWNERLESS_UNDEFINED; Entry Conviction: flow)
- `LEVEL_REACTION_MAGNITUDE` (OWNERLESS_UNDEFINED; Entry Conviction: structure)
- `LEVEL_VOLUME_PERCENTILE` (OWNERLESS_RULEBOOK_FALLBACK; Entry Conviction: structure)
- `LIQUIDATION_PERCENTILE` (OWNERLESS_CERTIFIED_DEFINITION; Entry Conviction: volatility)
- `MEASURED_MOVE_REFERENCE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `MOMENTUM_PERSISTENCE_SCORE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `NEW_STRUCTURAL_CONFIRMATION` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `NEW_STRUCTURE_SCORE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `RANGE_PERCENTILE` (OWNERLESS_UNDEFINED; Entry Conviction: volatility)
- `REGIME_INVALIDATION_PREDICATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `REGIME_SUPPORTIVE_PREDICATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `SEVERE_CROWDING_STATE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `SHORT_TRIGGER` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `TREND_Z_20W` (OWNERLESS_UNDEFINED; Entry Conviction: trend)
- `TREND_Z_52H` (OWNERLESS_UNDEFINED; Entry Conviction: trend)
- `TREND_Z_M12` (OWNERLESS_UNDEFINED; Entry Conviction: trend)
- `TREND_Z_M4` (OWNERLESS_UNDEFINED; Entry Conviction: trend)
- `UPSIDE_RETURN` (OWNERLESS_UNDEFINED; Entry Conviction: none)

## Database coverage

| family | venue | status | data-window rows | missing |
| --- | --- | --- | ---: | ---: |
| REFERENCE_PRICE_1H | BITSTAMP | COMPLETE | 52608 | 0 |
| SHARED_RAW_VOLUME_1H | BITSTAMP | COMPLETE | 52608 | 0 |
| REFERENCE_PRICE_1H | COINBASE | GAPS_PRESERVED | 52597 | 11 |
| REFERENCE_PRICE_1H | BITFINEX | GAPS_PRESERVED | 52592 | 16 |
| ETF_FLOW_AND_AUM | SHARED | EMPTY | 0 | - |
| FUNDING_RATE | SHARED | EMPTY | 0 | - |
| OPEN_INTEREST | SHARED | EMPTY | 0 | - |
| FUTURES_BASIS | SHARED | EMPTY | 0 | - |
| LIQUIDATIONS | SHARED | EMPTY | 0 | - |
| PERP_VOLUME | SHARED | EMPTY | 0 | - |
| BTC_MARKET_CAP | SHARED | EMPTY | 0 | - |
| US_EQUITY_MARKET_CLOSURES | SHARED | PRESENT | None | - |

Exposure: 2232 pre-2020 raw rows and 0 holdout raw rows. pre-2020 rows exist in the research database; they were counted only. RBT-001 refuses any record before 2020-01-01 and RBT-003 loaders must bound every query to the data window.

## Earliest evaluable date (input completeness only)

| venue | Entry Conviction + core regime | lower bound if owner-less inputs were defined without extra history | blocking inputs |
| --- | --- | --- | --- |
| BITSTAMP | UNDEFINED_OWNERLESS  | 2024-02-10T00:00:00+00:00 | DOWNSIDE_RETURN, FLOW_Z_ETF_NORM_20D, FLOW_Z_ETF_NORM_5D, FLOW_Z_FLOW_ACCEL, LEVEL_REACTION_MAGNITUDE, LEVEL_VOLUME_PERCENTILE, RANGE_PERCENTILE, TREND_Z_20W, TREND_Z_52H, TREND_Z_M12, TREND_Z_M4 |
| COINBASE | UNDEFINED_OWNERLESS  | 2024-02-10T00:00:00+00:00 | DOWNSIDE_RETURN, FLOW_Z_ETF_NORM_20D, FLOW_Z_ETF_NORM_5D, FLOW_Z_FLOW_ACCEL, LEVEL_REACTION_MAGNITUDE, LEVEL_VOLUME_PERCENTILE, RANGE_PERCENTILE, TREND_Z_20W, TREND_Z_52H, TREND_Z_M12, TREND_Z_M4 |
| BITFINEX | UNDEFINED_OWNERLESS  | 2024-02-10T00:00:00+00:00 | DOWNSIDE_RETURN, FLOW_Z_ETF_NORM_20D, FLOW_Z_ETF_NORM_5D, FLOW_Z_FLOW_ACCEL, LEVEL_REACTION_MAGNITUDE, LEVEL_VOLUME_PERCENTILE, RANGE_PERCENTILE, TREND_Z_20W, TREND_Z_52H, TREND_Z_M12, TREND_Z_M4 |

| venue | component | status | available at | lower bound |
| --- | --- | --- | --- | --- |
| BITSTAMP | trend | UNDEFINED_OWNERLESS | - | 2021-01-04T00:00:00+00:00 |
| BITSTAMP | flow | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |
| BITSTAMP | positioning | EVALUABLE | 2020-10-02T00:00:00+00:00 | - |
| BITSTAMP | volatility | UNDEFINED_OWNERLESS | - | 2022-05-29T00:00:00+00:00 |
| BITSTAMP | structure | UNDEFINED_OWNERLESS | - | 2020-02-24T00:00:00+00:00 |
| BITSTAMP | core regime | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |
| COINBASE | trend | UNDEFINED_OWNERLESS | - | 2021-01-25T00:00:00+00:00 |
| COINBASE | flow | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |
| COINBASE | positioning | EVALUABLE | 2020-10-02T00:00:00+00:00 | - |
| COINBASE | volatility | UNDEFINED_OWNERLESS | - | 2022-05-29T00:00:00+00:00 |
| COINBASE | structure | UNDEFINED_OWNERLESS | - | 2020-03-02T00:00:00+00:00 |
| COINBASE | core regime | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |
| BITFINEX | trend | UNDEFINED_OWNERLESS | - | 2021-01-18T00:00:00+00:00 |
| BITFINEX | flow | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |
| BITFINEX | positioning | EVALUABLE | 2020-10-02T00:00:00+00:00 | - |
| BITFINEX | volatility | UNDEFINED_OWNERLESS | - | 2022-05-29T00:00:00+00:00 |
| BITFINEX | structure | UNDEFINED_OWNERLESS | - | 2020-03-02T00:00:00+00:00 |
| BITFINEX | core regime | UNDEFINED_OWNERLESS | - | 2024-02-10T00:00:00+00:00 |

## Source ranking

| family | rank | role | candidate | depth | cost (USD) | adequate |
| --- | ---: | --- | --- | --- | ---: | --- |
| BTC_MARKET_CAP | 1 | CANDIDATE | `coinmetrics_community_capmrktcurusd` | 2010-07-18 (MEASURED) | 0 | True |
| BTC_MARKET_CAP | 2 | CANDIDATE | `coingecko_market_cap_history` | UNVERIFIED (UNVERIFIED) | UNVERIFIED | False |
| ETF_FLOW_AND_AUM | 1 | CANDIDATE | `coinglass_etf_flows_and_history` | 2024-01-11 (DOCUMENTED) | 29 | True |
| ETF_FLOW_AND_AUM | 2 | CANDIDATE | `issuer_websites` | UNVERIFIED (UNVERIFIED) | 0 | False |
| ETF_FLOW_AND_AUM | 3 | CANDIDATE | `farside_btc_etf_flows` | UNVERIFIED (UNVERIFIED) | 0 | False |
| FUNDING_RATE | 1 | CANDIDATE | `binance_usdm_btcusdt_funding_archive` | 2020-01-01T00:00:00Z (MEASURED) | 0 | True |
| FUNDING_RATE | 2 | CANDIDATE | `tardis_kraken_derivative_ticker` | 2019-03-30 (MEASURED) | 4200 | True |
| FUNDING_RATE | 3 | CANDIDATE | `kraken_v4_historical_funding_rates` | 2025-10-01T08:00:00Z (MEASURED) | 0 | False |
| FUTURES_BASIS | 1 | CANDIDATE | `binance_coinm_quarterly_basis` | 2020-08-01T00:00:00Z (MEASURED) | 0 | True |
| FUTURES_BASIS | 2 | CANDIDATE | `tardis_kraken_futures_fixed_maturity` | UNVERIFIED (UNVERIFIED) | UNVERIFIED | False |
| LIQUIDATIONS | 1 | CORROBORATION_ONLY | `kraken_futures_analytics_liquidation_volume` | 2020-02-26 (MEASURED) | 0 | False |
| LIQUIDATIONS | 1 | CANDIDATE | `kraken_futures_rest_executions` | 2021-05-27T11:55:25.097Z (MEASURED) | 0 | True |
| LIQUIDATIONS | 2 | CANDIDATE | `tardis_kraken_futures_liquidations` | 2019-03-30 (MEASURED) | 4200 | True |
| LIQUIDATIONS | 3 | CANDIDATE | `coinalyze_liquidation_history_daily` | UNVERIFIED (UNVERIFIED) | 0 | False |
| LIQUIDATIONS | 4 | CANDIDATE | `coinglass_pair_liquidation_history_daily` | all-time at 1d (plan table) (DOCUMENTED) | 29 | False |
| OPEN_INTEREST | 1 | CANDIDATE | `binance_usdm_btcusdt_metrics_archive` | 2020-09-01T00:00:00Z (MEASURED) | 0 | True |
| OPEN_INTEREST | 3 | CANDIDATE | `kraken_futures_analytics_open_interest` | 2023-03-07 (MEASURED) | 0 | False |
| PERP_VOLUME | 1 | CANDIDATE | `binance_usdm_btcusdt_klines_1h` | 2020-01-01T00:00:00Z (MEASURED) | 0 | True |

## Blockers

- **BLK-TREND-ZSCORE-NORMALISATION** (NEEDS_OWNER_DECISION): Trend z-score normalisation is undefined. Entry Conviction structurally incomplete on every date.
- **BLK-FLOW-ZSCORE-NORMALISATION** (NEEDS_OWNER_DECISION): Flow z-score normalisation is undefined. Entry Conviction structurally incomplete on every date.
- **BLK-VOLATILITY-RANGE-AND-RETURN** (NEEDS_OWNER_DECISION): Range percentile and downside/upside return are undefined. Entry Conviction structurally incomplete on every date.
- **BLK-LEVEL-STRENGTH-INPUTS** (NEEDS_OWNER_DECISION): Level reaction is undefined; the volume fallback lacks an executable path. Entry Conviction structurally incomplete on every date.
- **BLK-SEVERE-CROWDING-STATE** (NEEDS_OWNER_DECISION): 'Severe crowding' has no owner definition. Every new trade vetoed on every date.
- **BLK-LIFECYCLE-PREDICATES** (NEEDS_OWNER_DECISION): Hold, add and exit inputs have no owner.
- **BLK-SETUP-INPUTS** (NEEDS_OWNER_DECISION): Setup inputs without an owner.
- **BLK-LIQUIDATION-HISTORICAL-CENSUS** (NEEDS_POLICY_V4_DECISION): The certified hourly census cannot be applied unchanged to history.
- **BLK-FUTURES-BASIS-CONTRACT** (NEEDS_POLICY_V4_DECISION): The futures-basis contract is not defined anywhere.
- **BLK-STRESS-HARD-VETO-MAPPING** (NEEDS_POLICY_V4_DECISION): How an incomplete STRESS result reaches the hard veto. Every new trade vetoed on every date.
- **BLK-ETF-FUND-UNIVERSE** (NEEDS_POLICY_V4_DECISION): The ETF fund universe across fund launches.

## RBT-003 acquisition plan

| family | source | span start | status | cost (USD) |
| --- | --- | --- | --- | ---: |
| ETF_FLOW_AND_AUM | `coinglass_etf_flows_and_history` | 2024-01-11 | READY_FOR_RBT_003_AFTER_RBT_001A | 29 |
| FUNDING_RATE | `binance_usdm_btcusdt_funding_archive` | 2020-01-01T00:00:00+00:00 | READY_FOR_RBT_003_AFTER_RBT_001A | 0 |
| OPEN_INTEREST | `binance_usdm_btcusdt_metrics_archive` | 2020-09-01T00:00:00+00:00 | READY_FOR_RBT_003_AFTER_RBT_001A | 0 |
| PERP_VOLUME | `binance_usdm_btcusdt_klines_1h` | 2020-01-01T00:00:00+00:00 | READY_FOR_RBT_003_AFTER_RBT_001A | 0 |
| FUTURES_BASIS | `binance_coinm_quarterly_basis` | 2020-08-01T00:00:00+00:00 | BLOCKED_PENDING_POLICY_V4_DECISION | 0 |
| LIQUIDATIONS | `kraken_futures_rest_executions` | 2021-05-27T11:55:25.097000+00:00 | BLOCKED_PENDING_POLICY_V4_DECISION | 0 |
| BTC_MARKET_CAP | `coinmetrics_community_capmrktcurusd` | 2020-01-01 | READY_FOR_RBT_003_AFTER_RBT_001A | 0 |

Total acquisition cost: USD 29 (one CoinGlass Hobbyist month (USD 29) for ETF flows and per-fund AUM; every other selected source is free). Nothing was purchased.

## Verdict

EPIC Y stops for owner decisions: True (BLK-TREND-ZSCORE-NORMALISATION, BLK-FLOW-ZSCORE-NORMALISATION, BLK-VOLATILITY-RANGE-AND-RETURN, BLK-LEVEL-STRENGTH-INPUTS).
