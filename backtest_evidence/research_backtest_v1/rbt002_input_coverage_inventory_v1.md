# RBT-002 historical input coverage inventory

`INVENTORY_HISTORICAL_INPUT_COVERAGE_V1` under `RESEARCH_BACKTEST_POLICY_V5`. Evidence class `RESEARCH_BACKTEST_NON_CERTIFYING`, canonical reference `UNRESOLVED`.
Inventory SHA-256 `108ab25b2240a76befc0f685cc684175e5207561d978bad099869fb0cc5efe3a` over the canonical bytes of `rbt002_input_coverage_inventory_v1.json`.

Nothing here is a trading outcome. Holdout and pre-2020 rows were only counted.

## Input surface (policy V5 section 5A)

Discovered, not listed: `DECISION_PATH_STATIC_CENSUS_V2` walks the owner code from 74 hand-written roots and reaches 882 callables and 159 types (156 dataclasses, 1 protocol). 82 owner-module definitions are left out, each with a recorded reason.

Inside those callables it discovers 230 nested, local and private callables (188 GENERATOR_EXPRESSION, 40 LAMBDA, 2 NESTED_FUNCTION), each classified from its call sites inside the owner: 230 OWNER_INTERNAL.

| nested classification basis | callables |
| --- | ---: |
| EVERY_CALL_SITE_IS_A_DIRECT_CALL_PASSING_LITERALS_OR_ENCLOSING_SCOPE_NAMES | 2 |
| GENERATOR_EXPRESSION_ITERATOR_BOUND_IN_THE_ENCLOSING_SCOPE | 188 |
| KEY_FUNCTION_OF_BUILTIN_SORTED_MIN_OR_MAX_OVER_ENCLOSING_SCOPE_VALUES | 40 |

3520 inputs: the fields of 157 reached types, the parameters of 74 roots, the parameters of 662 internal callables and the parameters of 230 nested callables.

| census category | inputs |
| --- | ---: |
| COMPOSER_INPUT_TYPE | 259 |
| CONFIG_LOADER_PARAMETER | 79 |
| ENGINE_STATE | 34 |
| INTERNAL_PARAMETER | 1407 |
| NESTED_OWNER_INTERNAL_PARAMETER | 232 |
| OWNER_CONFIG | 15 |
| OWNER_DEFAULT_CONSTANT | 23 |
| OWNER_OUTPUT | 948 |
| ROOT_PARAMETER | 367 |
| STRATEGY_CONFIG | 156 |

| family | raw leaf inputs | inputs drawing on the family (direct or upstream) |
| --- | ---: | ---: |
| BTC_MARKET_CAP | 5 | 889 |
| CVD | 0 | 35 |
| DISCRETIONARY_ASSERTION | 0 | 119 |
| ENGINE_STATE | 0 | 137 |
| ETF_FLOW_AND_AUM | 11 | 876 |
| FUNDING_RATE | 12 | 952 |
| FUTURES_BASIS | 12 | 900 |
| LIQUIDATIONS | 13 | 941 |
| MACRO_ONCHAIN_LIQUIDITY | 0 | 3 |
| OPEN_INTEREST | 13 | 985 |
| PERP_VOLUME | 13 | 95 |
| REFERENCE_PRICE_1H | 25 | 2429 |
| SHARED_RAW_VOLUME_1H | 14 | 1205 |
| STRATEGY_CONFIG | 0 | 483 |
| US_EQUITY_MARKET_CLOSURES | 2 | 816 |

| kind | inputs |
| --- | ---: |
| ABSENT_RULEBOOK_FALLBACK | 11 |
| DERIVED_BY_OWNER | 1149 |
| DISCRETIONARY | 7 |
| ENGINE_STATE | 108 |
| OWNERLESS_CERTIFIED_DEFINITION | 3 |
| OWNERLESS_RULEBOOK_FALLBACK | 2 |
| OWNERLESS_UNDEFINED | 43 |
| OWNER_INTERNAL_DATAFLOW | 1639 |
| RAW_HISTORICAL | 104 |
| STRATEGY_CONFIG | 454 |

Owner-less inputs:

- `ADD_MOMENTUM_SCORE` (OWNERLESS_UNDEFINED; Entry Conviction: none)
- `CAPITULATION_EVENT` (OWNERLESS_UNDEFINED; Entry Conviction: structure)
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

Owner keyword defaults that no reached caller overrides (fixed constants of the decision path):

- `btc_predictor.features.rolling.average_true_range.min_periods` = `None`
- `btc_predictor.features.rolling.rolling_mean.min_periods` = `None`
- `btc_predictor.features.trend.fifty_two_week_high_distance.window` = `52`
- `btc_predictor.features.trend.twenty_week_ma_distance.window` = `20`
- `btc_predictor.quant.comparisons.decision_compare.tolerance` = `btc_predictor.quant.comparisons.DecisionTolerance(absolute=Decimal('1E-12'), relative=Decimal('1E-12'))`
- `btc_predictor.quant.distances.atr_normalized_distance.nan_policy` = `'raise'`
- `btc_predictor.quant.distances.pairwise_price_distance.nan_policy` = `'raise'`
- `btc_predictor.quant.risk.risk_improvement.nan_policy` = `'raise'`
- `btc_predictor.quant.rolling.realized_volatility.min_periods` = `None`
- `btc_predictor.quant.rolling.realized_volatility.nan_policy` = `'raise'`
- `btc_predictor.quant.rolling.realized_volatility.sample` = `False`
- `btc_predictor.quant.rolling.true_range.nan_policy` = `'raise'`
- `btc_predictor.quant.scoring.weighted_score.weight_tolerance` = `1e-06`
- `btc_predictor.quant.transforms.gaussian_health.maximum` = `100.0`
- `btc_predictor.quant.transforms.gaussian_health.nan_policy` = `'raise'`
- `btc_predictor.quant.transforms.normal_cdf_score.maximum` = `100.0`
- `btc_predictor.quant.transforms.normal_cdf_score.mean` = `0.0`
- `btc_predictor.quant.transforms.normal_cdf_score.minimum` = `0.0`
- `btc_predictor.quant.transforms.normal_cdf_score.nan_policy` = `'raise'`
- `btc_predictor.quant.transforms.normal_cdf_score.standard_deviation` = `1.0`
- `btc_predictor.quant.transforms.percentile_to_health.higher_is_healthier` = `False`
- `btc_predictor.quant.transforms.percentile_to_health.nan_policy` = `'raise'`
- `btc_predictor.risk.reward.select_reward_reference.major_timeframes` = `('1w', '1mo')`

Nested-callable defaults (owner-internal; whether a call site inside the owner passes the argument):

- `btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held.candidate` = `None` (A_REACHED_CALLER_PASSES_THIS_ARGUMENT)
- `btc_predictor.risk.trailing.calculate_trailing_stop.<locals>.held.complete` = `True` (A_REACHED_CALLER_PASSES_THIS_ARGUMENT)

## Census limits (policy V5 section 5A.5)

The census claims completeness only for static discovery plus the runtime trace over the paths the fixture runs and the owner tests actually exercise; it is not a universal proof (policy V5 section 5A.5). Static discovery walks every reached callable's bytecode, annotations, defaults, members and nested code, and classifies every nested, local and private callable it defines. The tracer has no exemption: every executed frame, nested or not, must match a statically discovered callable by code identity and parameter names.

- **ENCLOSING_LOCAL_CALLBACKS.** A callable an owner receives as a value (a parameter or local variable holding a callback) is invisible to static discovery, which resolves names only in module globals, closure cells and function-local imports. Every function, lambda, generator expression and class defined inside a reached body is discovered and classified; a received callback is caught only if a traced run executes it.
- **UNNAMED_PROTOCOL_IMPLEMENTATIONS.** A method on a concrete class that no reached code names, such as a caller-supplied implementation of a Protocol, is not discovered. The one reached Protocol, btc_predictor.levels.breakout.SourceLevel, is field-only, and its supported implementations (the weekly and monthly swing levels) are reached.
- **DYNAMIC_GETATTR_DISPATCH.** A getattr with a computed name is not resolved. Every reached owner getattr reads a field, property or as_record of a reached class or a field of an enumerated configuration dataclass (R1 audit, confirmed by the re-review pattern audit).
- **UNEXECUTED_BRANCHES.** Code that never runs gives no runtime evidence. The measured line and branch coverage of the reached owner bodies is recorded below; an unexecuted arc is covered by static discovery alone.

Measured with coverage.py 7.16.0 (branch measurement) on CPython 3.12.14 on 2026-10-02. Reached-body figures count the statements and branch arcs inside the source bodies of the reached named callables, which contain every nested callable; whole-module figures also count unreached definitions and module initialisation of the 50 reached source modules.

| run | reached-body lines | reached-body branches | whole reached modules: lines | whole reached modules: branches | nested callables executed |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixture runs | 4,993/7,565 (66.00%) | 2,235/3,728 (59.95%) | 4,993/11,539 (43.27%) | 2,235/4,140 (53.99%) | 224/230 |
| owner tests | 5,855/7,565 (77.40%) | 2,934/3,728 (78.70%) | 6,480/11,539 (56.16%) | 3,149/4,140 (76.06%) | 224/230 |

1,493 reached-body branch arcs never run under the fixtures and 794 never run under the owner tests. Their complete source-line to target-line lists are in backtest_evidence/research_backtest_v1/rbt002_rereview_evidence_v1.json under coverage.runs.{fixtures,owners}.files.*.unexecuted_branches; the R2 re-measurement reproduced those lists exactly.

Under both runs a root-scoped tracer checked every executed frame against the static census by code identity and parameter names, with no exemption: 0 uncovered functions and 0 uncovered dataclasses.
Nested callables neither run executes (classified from source alone): `btc_predictor.data.quality.DerivativesQualityConfig.__post_init__.<locals>.<genexpr>#1`, `btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#1`, `btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#2`, `btc_predictor.features.entry.EntryConvictionResult.as_record.<locals>.<genexpr>#3`, `btc_predictor.risk.trailing._validate_result.<locals>.<genexpr>#1`.

Backstop: the runtime completeness guard of policy V5 section 5A.6, binding on RBT-004, RBT-005 and RBT-006. Every owner function a composer calls directly must be a census root, and any incomplete owner result or missing-input reason code in a composed replay must map to a cause in the reviewed inventory or CHAMPION_COMPLETION_SPEC_V1; an unaccounted one fails the test (RBT-004/RBT-005) or blocks the freeze (RBT-006).

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
- **BLK-AVWAP-EVENT-ANCHOR** (NEEDS_OWNER_DECISION): The anchored-VWAP market-event anchor has no owner.
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
