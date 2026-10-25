"""RBT-004 ``COMPOSE_CHAMPION_ENTRY_DECISION_V1``: the flat-state half of the champion.

The EPIC Y research champion ``swing_v1.2+completion_v1`` is the repository
strategy configuration plus ``CHAMPION_COMPLETION_SPEC_V1`` (policy V7
section 6). At each daily decision instant this composer turns point-in-time
inputs into exactly one of: an ``ARM_ENTRY`` intent, a recorded ``NO_TRADE``,
or ``STRUCTURALLY_UNEVALUABLE``. It adds no formula. Every number comes from an
owner call or from the spec's ``declared_arithmetic``, and every owner it calls
directly is a census root or a classified input source
(:mod:`btc_predictor.research_backtest.composer_boundary`).

**Decision instant.** A daily decision instant is a UTC midnight, the close of
the day's 23:00 hourly bar (the RBT-001 control convention). The backtest
adapter (:meth:`EntryComposer.__call__`) acts only on those callbacks. A
midnight the engine never offers, because its hourly bar is missing, is logged
as ``STRUCTURALLY_UNEVALUABLE`` with the 1h-gap cause and the position state
the engine last reported. A skipped midnight whose decision bar the composer
can see is a composer defect: the engine's bars differ from the replay inputs,
and the decision is never silently dropped.

**Composition order** (ticket steps 1-6, in the order the owners' inputs force;
Rulebook sections 2, 3 and 26):

0. Point-in-time slice. Only replay inputs whose modelled availability is at or
   before ``t`` are read. ``replay_market_bars_at`` derives the 1d/1w/1mo bars.
   ``P_t`` is the close of the hourly bar that closes at ``t``.
1. Components:
   - Trend: momentum, MA-distance, 52-week-high and weekly-structure owners,
     then ``UNIFORM_ZSCORE_V1``, then ``calculate_trend_score``.
   - Flow: ``ETF_CORE``, CVD absent. ETF windows run on the per-window fund
     universe and the loaded ``US_EQUITY_MARKET_CLOSURE_TABLE_V1``.
   - Positioning: the three owners behind the policy V7 section 6A.9
     zero-variance guards, plus OI intensity.
   - Volatility: RV, percentile, compression, then orderliness from
     ``RANGE_PERCENTILE``, ``DOWNSIDE_RETURN`` and the last completed UTC
     day's ``LIQUIDATION_PERCENTILE`` (never an older day's).
   - Structure: swing and breakout/reclaim levels, clusters, the spec's
     level-strength inputs, then the structure owner.
2. Core regime, smoothing and classification; the Rulebook section 24 flags.
3. Geometry per long archetype (invalidation, volatility buffer, initial stop,
   BTC-143 R/R). It must precede Structure, because the structure owner
   requires a stop, and the setup detectors, because they need the R/R. Then
   the entry triggers and setup detection.
4. Entry Conviction and its action band.
5. No-chase, the hard veto (with ``DATA_QUALITY_FAIL`` and the V4 STRESS
   mapping) and the data-quality gate.
6. The ``ARM_ENTRY`` intent with the BTC-140..142 initial stop.

**Owner rulings applied (2026-10-03, recorded in the RBT-004 notes):**
- the entry zone is the point ``[P_t, P_t]``;
- Setup C reads CAPITULATION through the V4 mapping, with a 14-day
  (``max_confirmation_lag_days``) episode memory; an instant with no ledger
  row or no known flag state is unknown, never "not flagged";
- data quality covers the last completed UTC day;
- when no archetype yields a complete stop, a data cause makes the instant
  ``STRUCTURALLY_UNEVALUABLE`` and a geometry cause makes it ``NO_TRADE``;
- when Setup C conflicts with A or B, it is ``NO_TRADE``;
- entry triggers must fire fresh at the decision instant;
- Setup B histories use native cadence.

Nothing is zero-filled. A missing input propagates as its owner defines it.
Every incomplete owner result and every missing-input reason code is mapped to
an accounted cause (:data:`CAUSE_ACCOUNTING`) in the reviewed inventory or the
spec. An unaccounted one is recorded on its ledger row, and the RBT-004 tests
fail on it (policy V7 section 5A.6).
"""

from __future__ import annotations

import bisect
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.backtest.engine import ARM_ENTRY_ACTION, BacktestContext, BacktestIntent
from btc_predictor.config.strategy import STRUCTURE_SCORE_CONTRACT_VERSION, StrategyConfig
from btc_predictor.data import FuturesBasis, OhlcvBar
from btc_predictor.data.ohlcv import next_bar_timestamp
from btc_predictor.data.quality import validate_derivatives_quality, validate_ohlcv_quality
from btc_predictor.features.entry import (
    EntryConvictionInput,
    calculate_entry_conviction,
    classify_entry_action,
)
from btc_predictor.features.flow import (
    FlowScoreInput,
    calculate_flow_score,
    etf_flow_acceleration,
    five_day_etf_flow,
    spot_perp_cvd_spread,
    twenty_day_etf_flow,
)
from btc_predictor.features.momentum import (
    four_week_momentum_from_daily_bars,
    price_momentum_from_daily_bars,
    twelve_week_momentum_from_daily_bars,
)
from btc_predictor.features.positioning import (
    CrowdingFlagInput,
    MarketCapObservation,
    PositioningScoreInput,
    _aggregate_open_interest_by_time,
    _funding_average_history,
    _funding_averages_by_time,
    _futures_basis_averages_by_time,
    _futures_basis_history,
    _oi_growth_history,
    _open_interest_growth_by_time,
    calculate_crowding_flag,
    calculate_positioning_score,
    funding_health,
    futures_basis_health,
    open_interest_growth_health,
    open_interest_intensity,
)
from btc_predictor.features.regime import (
    RegimeScoreInput,
    RegimeSmoothingInput,
    calculate_regime_classification,
    calculate_regime_score,
    calculate_regime_smoothing,
)
from btc_predictor.features.rolling import rolling_percentile, rolling_zscore, true_ranges
from btc_predictor.features.setup import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    BearishDistributionInput,
    BullishResetInput,
    BullTrendContinuationInput,
    CapitulationReversalInput,
    detect_bearish_distribution,
    detect_bull_trend_continuation,
    detect_bullish_reset,
    detect_capitulation_reversal,
)
from btc_predictor.features.structure import calculate_structure_score_from_clusters
from btc_predictor.features.trend import (
    TrendScoreInput,
    calculate_trend_score,
    classify_weekly_structure_from_weekly_bars,
    fifty_two_week_high_distance_from_weekly_bars,
    twenty_week_ma_distance_from_weekly_bars,
)
from btc_predictor.features.volatility import (
    DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS,
    CapitulationFlagInput,
    EuphoriaFlagInput,
    OrderlinessScoreInput,
    StressFlagInput,
    VolatilityScoreInput,
    calculate_capitulation_flag,
    calculate_euphoria_flag,
    calculate_orderliness_score,
    calculate_stress_flag,
    calculate_volatility_score,
    realized_volatility_from_daily_bars,
    volatility_compression_ratio_from_results,
    volatility_percentile,
)
from btc_predictor.levels.breakout import RECLAIM_LEVEL_TYPE, detect_breakout_reclaim_levels
from btc_predictor.levels.clustering import cluster_price_levels
from btc_predictor.levels.strength import calculate_level_strength_from_cluster
from btc_predictor.levels.swing import (
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LOW,
    detect_monthly_swing_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.research.us_equity_market_closures import (
    COVERAGE_END as CLOSURE_TABLE_COVERAGE_END,
    COVERAGE_START as CLOSURE_TABLE_COVERAGE_START,
    TABLE_VERSION as CLOSURE_TABLE_VERSION,
    load_closures,
)
from btc_predictor.research_backtest.completion_spec import (
    RETURN_HORIZON_DAILY_BARS,
    RESEARCH_STRATEGY_ID,
    SPEC_VERSION,
    UNIFORM_PERCENTILE_MIN_OBSERVATIONS,
    UNIFORM_PERCENTILE_WINDOW_DAYS,
    UNIFORM_ZSCORE_MIN_OBSERVATIONS,
    UNIFORM_ZSCORE_WINDOW_OBSERVATIONS,
    CHAMPION_BASE_IDENTITY,
)
from btc_predictor.research_backtest.replay_inputs import (
    DATA_WINDOW,
    VenueReplayDataset,
    canonical_json_bytes,
    replay_market_bars_at,
    sha256_hex,
)
from btc_predictor.risk.buffer import atr_from_daily_bars, volatility_buffer_for_invalidation
from btc_predictor.risk.invalidation import select_structural_invalidation
from btc_predictor.risk.reward import reward_risk_for_stop
from btc_predictor.risk.stop import initial_stop_for_setup
from btc_predictor.signals.data_quality import apply_data_quality_gate, failures_from_quality_reports
from btc_predictor.signals.hard_veto import HardVetoInput, evaluate_hard_veto
from btc_predictor.signals.higher_low import evaluate_higher_low_trigger
from btc_predictor.signals.no_chase import apply_no_chase_filter
from btc_predictor.signals.reclaim import evaluate_reclaim_trigger

ENTRY_COMPOSER_VERSION = "COMPOSE_CHAMPION_ENTRY_DECISION_V1"
ENTRY_COMPOSER_TICKET = "RBT-004"
LEDGER_VERSION = "CHAMPION_ENTRY_DECISION_LEDGER_V1"
# The CHAMPION_COMPLETION_SPEC_V1 definition this composer implements, as rebound
# by RBT-004 Part A (tests compare it with the persisted digest).
COMPLETION_SPEC_SHA256 = "787ddfa26391a1956ed8ee92209308b95797536e0906844d9811f9e8ca2620f0"

OUTCOME_ARM_ENTRY = "ARM_ENTRY"
OUTCOME_NO_TRADE = "NO_TRADE"
OUTCOME_STRUCTURALLY_UNEVALUABLE = "STRUCTURALLY_UNEVALUABLE"
OUTCOMES = (OUTCOME_ARM_ENTRY, OUTCOME_NO_TRADE, OUTCOME_STRUCTURALLY_UNEVALUABLE)

# NO_TRADE reasons the composer records next to the owners' reason codes.
REASON_POSITION_ALREADY_OPEN = "POSITION_ALREADY_OPEN"
REASON_NO_VALID_STRUCTURAL_STOP = "NO_VALID_STRUCTURAL_STOP"
REASON_NO_SETUP_DETECTED = "NO_SETUP_DETECTED"
REASON_SETUP_GEOMETRY_CONFLICT = "SETUP_GEOMETRY_CONFLICT"
REASON_ENTRY_CONVICTION_BELOW_TRADE_BAND = "ENTRY_CONVICTION_BELOW_TRADE_BAND"
REASON_HARD_VETO = "HARD_VETO"
REASON_DATA_QUALITY_GATE = "DATA_QUALITY_GATE"
# STRUCTURALLY_UNEVALUABLE when the decision instant has no hourly price bar.
CAUSE_DECISION_PRICE_BAR_MISSING = "DECISION_INSTANT_PRICE_BAR_MISSING"
CAUSE_LIQUIDATION_PERCENTILE_MISSING = "LIQUIDATION_PERCENTILE_INPUT_MISSING"
CAUSE_WEEKLY_STRUCTURE_MISSING = "WEEKLY_STRUCTURE_INSUFFICIENT_HISTORY"

# Inventory classification of OpenInterestGrowth/Intensity open_interest_unit:
# "the pinned OI unit (RBT-002 pins USD)".
OPEN_INTEREST_UNIT = "USD"
# Rulebook 11 order of the long archetypes; A and B share the NEAREST-zone
# invalidation policy, C uses the FARTHEST zone (risk/invalidation.py).
LONG_ARCHETYPES = (BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP, CAPITULATION_REVERSAL_SETUP)
_SHARED_GEOMETRY_ARCHETYPES = frozenset({BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP})
# The five Entry Conviction components, in EntryConvictionInput order.
COMPONENT_NAMES = ("trend", "flow", "positioning", "volatility", "structure")
# classify_entry_action labels at or above entry_thresholds.valid_trade_min
# (Rulebook 13: an actual trade requires C_entry >= 80).
TRADE_BAND_ACTIONS = ("VALID", "STRONG", "EXCEPTIONAL")
# Stop failures caused by missing data (owner ruling: STRUCTURALLY_UNEVALUABLE);
# every other incomplete stop is market geometry (NO_TRADE).
_STOP_DATA_CAUSES = frozenset(
    {"STRUCTURAL_INVALIDATION_INPUT_MISSING", "VOLATILITY_BUFFER_INPUT_MISSING", "INITIAL_STOP_INPUT_MISSING"}
)
_DAY = timedelta(days=1)
_HOUR = timedelta(hours=1)

# BTC-048 feature-matrix columns the ledger carries (research/feature_matrix.py
# INITIAL_FEATURE_NAMES; parity is tested there).
FEATURE_NAMES = (
    "TREND_SCORE", "FLOW_SCORE", "POSITIONING_SCORE", "VOLATILITY_SCORE", "STRUCTURE_SCORE", "REGIME_SCORE",
    "REGIME_SMOOTHED_SCORE", "ORDERLINESS_SCORE", "MOMENTUM_4W", "MOMENTUM_12W", "MA_DISTANCE_20W", "HIGH_DISTANCE_52W",
    "ETF_NORM_5D", "ETF_NORM_20D", "FLOW_ACCEL", "CVD_SPREAD", "SPOT_DOMINANCE", "FUNDING_7D_AVG",
    "FUNDING_ZSCORE_180D", "FUNDING_HEALTH", "OI_GROWTH_7D", "OI_GROWTH_ZSCORE_180D", "OI_GROWTH_HEALTH",
    "OI_INTENSITY", "OI_INTENSITY_PERCENTILE_180D", "FUTURES_BASIS_AVG", "FUTURES_BASIS_ZSCORE_180D",
    "FUTURES_BASIS_HEALTH", "RV_7", "RV_20", "RV_60", "VOL_COMPRESSION_RATIO", "VOL_PERCENTILE_2Y",
)


class EntryComposerError(ValueError):
    """The composer was given inputs it cannot compose, or found a composer defect."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# --- accounted causes (policy V7 section 5A.6) ----------------------------------------

AUTHORITY_SPEC_ENTRY = "CHAMPION_COMPLETION_SPEC_V1_ENTRY"
AUTHORITY_SPEC_GUARD = "CHAMPION_COMPLETION_SPEC_V1_GUARD"
AUTHORITY_INVENTORY_ROW = "INVENTORY_ROW"
AUTHORITY_INVENTORY_MINIMUM_HISTORY = "INVENTORY_MINIMUM_HISTORY"


@dataclass(frozen=True)
class AccountedCause:
    """Where a reason code is accounted for.

    - ``SPEC_ENTRY``: ``reference`` is an input id, and ``cause`` must be one of
      that entry's accounted causes.
    - ``SPEC_GUARD``: ``reference`` is a positioning guard id.
    - ``INVENTORY_ROW``: ``reference`` is a row key, and ``cause`` must appear in
      that row's missing behaviour.
    - ``INVENTORY_MINIMUM_HISTORY``: ``reference`` is a minimum-history input id.
    """

    authority: str
    reference: str
    cause: str

    def as_record(self) -> dict[str, str]:
        return {"authority": self.authority, "reference": self.reference, "cause": self.cause}


def _spec(input_id: str, cause: str) -> AccountedCause:
    return AccountedCause(AUTHORITY_SPEC_ENTRY, input_id, cause)


def _row(reference: str, cause: str) -> AccountedCause:
    return AccountedCause(AUTHORITY_INVENTORY_ROW, reference, cause)


def _history(input_id: str) -> AccountedCause:
    return AccountedCause(AUTHORITY_INVENTORY_MINIMUM_HISTORY, input_id, "minimum history")


_F = "btc_predictor.features."
_SETUP_NONE = "the setup's *_INPUT_MISSING reason"

# Reason code -> accounted cause. A (feature_id, code) key applies to one owner
# result only. Codes absent here are unaccounted and fail the RBT-004 guard.
CAUSE_ACCOUNTING: Mapping[Any, AccountedCause] = {
    # composer-level CHAMPION_COMPLETION_SPEC_V1 causes
    **{
        f"{input_id}_{suffix}": _spec(input_id, f"{input_id}_{suffix}")
        for input_id in (
            "TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H",
            "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL",
        )
        for suffix in ("INPUT_MISSING", "INSUFFICIENT_HISTORY", "ZERO_VARIANCE")
    },
    "RANGE_PERCENTILE_INPUT_MISSING": _spec("RANGE_PERCENTILE", "RANGE_PERCENTILE_INPUT_MISSING"),
    "RANGE_PERCENTILE_INSUFFICIENT_HISTORY": _spec("RANGE_PERCENTILE", "RANGE_PERCENTILE_INSUFFICIENT_HISTORY"),
    "DOWNSIDE_RETURN_INPUT_MISSING": _spec("DOWNSIDE_RETURN", "DOWNSIDE_RETURN_INPUT_MISSING"),
    "UPSIDE_RETURN_INPUT_MISSING": _spec("UPSIDE_RETURN", "UPSIDE_RETURN_INPUT_MISSING"),
    **{
        f"LEVEL_REACTION_MAGNITUDE_{suffix}": _spec("LEVEL_REACTION_MAGNITUDE", f"LEVEL_REACTION_MAGNITUDE_{suffix}")
        for suffix in ("INPUT_MISSING", "NO_SWING_MEMBER")
    },
    **{
        f"LEVEL_VOLUME_PERCENTILE_{suffix}": _spec("LEVEL_VOLUME_PERCENTILE", f"LEVEL_VOLUME_PERCENTILE_{suffix}")
        for suffix in ("INPUT_MISSING", "NO_SWING_MEMBER", "WARM_UP", "INSUFFICIENT_HISTORY")
    },
    "SEVERE_CROWDING_STATE_INPUT_MISSING": _spec("SEVERE_CROWDING_STATE", "SEVERE_CROWDING_STATE_INPUT_MISSING"),
    "CORRECTION_FROM_LOCAL_HIGH_INPUT_MISSING": _spec("CORRECTION_FROM_LOCAL_HIGH", "CORRECTION_FROM_LOCAL_HIGH_INPUT_MISSING"),
    "BEARISH_DISTRIBUTION_INPUT_MISSING": _spec("DISTRIBUTION_STATE", "INERT_SHORT_SIDE"),
    "REWARD_RISK_NO_REWARD_REFERENCE": _spec("MEASURED_MOVE_REFERENCE", "REWARD_RISK_NO_REWARD_REFERENCE"),
    # the policy V7 section 6A.9 guards (and the owners' own zero-variance refusals)
    "FUNDING_HEALTH_ZERO_VARIANCE": AccountedCause(AUTHORITY_SPEC_GUARD, "FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1", "FUNDING_HEALTH_ZERO_VARIANCE"),
    "FUTURES_BASIS_ZERO_VARIANCE": AccountedCause(AUTHORITY_SPEC_GUARD, "FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1", "FUTURES_BASIS_ZERO_VARIANCE"),
    "OI_GROWTH_ZERO_VARIANCE": AccountedCause(AUTHORITY_SPEC_GUARD, "OI_GROWTH_ZERO_VARIANCE_GUARD_V1", "OI_GROWTH_ZERO_VARIANCE"),
    # composer-level inventory causes
    CAUSE_DECISION_PRICE_BAR_MISSING: _row("btc_predictor.data.quality.validate_ohlcv_quality.bars", "a missing hour is a gap, never filled"),
    CAUSE_LIQUIDATION_PERCENTILE_MISSING: _row(_F + "volatility.OrderlinessScoreInput.liquidation_percentile", "ORDERLINESS_INPUT_MISSING"),
    CAUSE_WEEKLY_STRUCTURE_MISSING: _history("WEEKLY_STRUCTURE"),
    # flow
    "ETF_FLOW_INPUT_MISSING": _row(_F + "flow.five_day_etf_flow.flows", "ETF_FLOW_INPUT_MISSING"),
    "ETF_FLOW_AUM_MISSING": _row(_F + "flow.five_day_etf_flow.flows", "ETF_FLOW_AUM_MISSING"),
    "ETF_FLOW_ACCEL_INPUT_MISSING": _row(_F + "flow.etf_flow_acceleration.five_day_flow", "ETF_FLOW_ACCEL_INPUT_MISSING"),
    "FLOW_SCORE_CORE_INPUT_MISSING": _row(_F + "flow.calculate_flow_score.inputs", "FLOW_SCORE_CORE_INPUT_MISSING"),
    "FLOW_SCORE_P1_INPUT_MISSING": _row(_F + "flow.FlowScoreInput.cvd_spread_zscore", "FLOW_SCORE_P1_INPUT_MISSING"),
    "SPOT_CVD_INPUT_MISSING": _row(_F + "flow.CvdObservation.cvd_usd", "SPOT_CVD_INPUT_MISSING"),
    "PERP_CVD_INPUT_MISSING": _row(_F + "flow.CvdObservation.cvd_usd", "PERP_CVD_INPUT_MISSING"),
    "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY": _row(_F + "flow.spot_perp_cvd_spread.observations", "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY"),
    # positioning
    "FUNDING_RATE_INPUT_MISSING": _row(_F + "positioning.funding_health.funding_rates", "FUNDING_RATE_INPUT_MISSING"),
    "FUNDING_HEALTH_INSUFFICIENT_HISTORY": _history("FUNDING_HEALTH"),
    "FUTURES_BASIS_INPUT_MISSING": _row(_F + "positioning.futures_basis_health.futures_basis_rows", "FUTURES_BASIS_INPUT_MISSING"),
    "FUTURES_BASIS_INSUFFICIENT_HISTORY": _history("FUTURES_BASIS_HEALTH"),
    "OI_GROWTH_INPUT_MISSING": _row(_F + "positioning.open_interest_growth_health.open_interest_rows", "OI_GROWTH_INPUT_MISSING"),
    "OI_GROWTH_PRIOR_INPUT_MISSING": _history("OI_GROWTH_HEALTH"),
    "OI_GROWTH_INSUFFICIENT_HISTORY": _history("OI_GROWTH_HEALTH"),
    "OI_INTENSITY_OI_INPUT_MISSING": _row(_F + "positioning.open_interest_intensity.open_interest_rows", "OI_INTENSITY_OI_INPUT_MISSING"),
    "OI_INTENSITY_MARKET_CAP_INPUT_MISSING": _row(_F + "positioning.open_interest_intensity.market_caps", "OI_INTENSITY_MARKET_CAP_INPUT_MISSING"),
    "OI_INTENSITY_INSUFFICIENT_HISTORY": _history("OI_INTENSITY_PERCENTILE"),
    "POSITIONING_SCORE_INPUT_MISSING": _row(_F + "positioning.calculate_positioning_score.inputs", "POSITIONING_SCORE_INPUT_MISSING"),
    "CROWDING_INPUT_MISSING": _row(_F + "positioning.calculate_crowding_flag.inputs", "CROWDING_INPUT_MISSING"),
    # volatility and the hard flags
    ("RV_7", "REALIZED_VOLATILITY_INPUT_MISSING"): _history("RV_7"),
    ("RV_7", "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY"): _history("RV_7"),
    ("RV_20", "REALIZED_VOLATILITY_INPUT_MISSING"): _history("RV_20"),
    ("RV_20", "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY"): _history("RV_20"),
    ("RV_60", "REALIZED_VOLATILITY_INPUT_MISSING"): _history("RV_60"),
    ("RV_60", "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY"): _history("RV_60"),
    "VOL_PERCENTILE_INPUT_MISSING": _row(_F + "volatility.volatility_percentile.results", "VOL_PERCENTILE_INPUT_MISSING"),
    "VOL_PERCENTILE_INSUFFICIENT_HISTORY": _history("VOL_PERCENTILE_2Y"),
    "VOL_COMPRESSION_INPUT_MISSING": _row(_F + "volatility.volatility_compression_ratio_from_results.results", "VOL_COMPRESSION_INPUT_MISSING"),
    "ORDERLINESS_INPUT_MISSING": _row(_F + "volatility.calculate_orderliness_score.inputs", "ORDERLINESS_INPUT_MISSING"),
    "VOLATILITY_SCORE_INPUT_MISSING": _row(_F + "volatility.calculate_volatility_score.inputs", "VOLATILITY_SCORE_INPUT_MISSING"),
    "VOLATILITY_REGIME_UNKNOWN": _row(_F + "volatility.VolatilityScoreInput.volatility_percentile", "VOLATILITY_REGIME_UNKNOWN"),
    "STRESS_INPUT_MISSING": _row(_F + "volatility.StressFlagInput.systemic_shock", "STRESS_INPUT_MISSING"),
    "CAPITULATION_INPUT_MISSING": _row(_F + "volatility.calculate_capitulation_flag.inputs", "CAPITULATION_INPUT_MISSING"),
    "EUPHORIA_INPUT_MISSING": _row(_F + "volatility.calculate_euphoria_flag.inputs", "EUPHORIA_INPUT_MISSING"),
    # structure, levels and geometry
    "LEVEL_CLUSTER_INPUT_MISSING": _row("btc_predictor.levels.clustering.cluster_price_levels.levels", "LEVEL_CLUSTER_INPUT_MISSING"),
    "LEVEL_STRENGTH_INPUT_MISSING": _row(
        "btc_predictor.levels.strength.calculate_level_strength_from_cluster.reaction_magnitude_fraction", "LEVEL_STRENGTH_INPUT_MISSING"
    ),
    "STRUCTURE_SCORE_INPUT_MISSING": _row(
        _F + "structure.calculate_structure_score_from_clusters.level_strength_result", "STRUCTURE_SCORE_INPUT_MISSING"
    ),
    **{
        code: _row("btc_predictor.risk.invalidation.select_structural_invalidation.clusters", "no eligible cluster -> no structural invalidation")
        for code in (
            "STRUCTURAL_INVALIDATION_INPUT_MISSING", "STRUCTURAL_INVALIDATION_NO_CANDIDATE",
            "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED", "STRUCTURAL_INVALIDATION_WRONG_SIDE",
            "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE", "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE",
        )
    },
    "VOLATILITY_BUFFER_INPUT_MISSING": _row("btc_predictor.risk.buffer.volatility_buffer_for_invalidation.atr", "required"),
    "VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE": _row("btc_predictor.risk.buffer.volatility_buffer_for_invalidation.invalidation", "required"),
    **{
        code: _row("btc_predictor.risk.stop.initial_stop_for_setup.invalidation", "no valid structural stop")
        for code in (
            "INITIAL_STOP_INPUT_MISSING", "INITIAL_STOP_INVALIDATION_INCOMPLETE", "INITIAL_STOP_BUFFER_INCOMPLETE",
            "INITIAL_STOP_NON_POSITIVE", "INITIAL_STOP_WRONG_SIDE_OF_ENTRY",
        )
    },
    "REWARD_RISK_INPUT_MISSING": _row("btc_predictor.risk.reward.reward_risk_for_stop.stop", "None -> no R/R"),
    "NO_CHASE_ATR_MISSING": _row("btc_predictor.signals.no_chase.apply_no_chase_filter.atr", "None -> ATR mode unavailable"),
    # regime, Entry Conviction and the veto
    "REGIME_SCORE_CORE_INPUT_MISSING": _row(_F + "regime.calculate_regime_score.inputs", "REGIME_SCORE_CORE_INPUT_MISSING"),
    "REGIME_SCORE_P1_INPUT_MISSING": _row(_F + "regime.RegimeScoreInput.macro_score", "REGIME_SCORE_P1_INPUT_MISSING"),
    "REGIME_SMOOTHING_NEW_SCORE_MISSING": _row(_F + "regime.calculate_regime_smoothing.inputs", "REGIME_SMOOTHING_NEW_SCORE_MISSING"),
    "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING": _row(
        _F + "regime.RegimeSmoothingInput.previous_smoothed_score", "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING"
    ),
    "REGIME_CLASSIFICATION_SCORE_MISSING": _row(_F + "regime.calculate_regime_classification.score", "REGIME_CLASSIFICATION_SCORE_MISSING"),
    "ENTRY_CONVICTION_INPUT_MISSING": _row(_F + "entry.calculate_entry_conviction.inputs", "ENTRY_CONVICTION_INPUT_MISSING"),
    "ENTRY_ACTION_SCORE_MISSING": _row(_F + "entry.classify_entry_action.score", "ENTRY_ACTION_SCORE_MISSING"),
    "HARD_VETO_INPUT_MISSING": _row("btc_predictor.signals.hard_veto.evaluate_hard_veto.inputs", "HARD_VETO_INPUT_MISSING"),
    # setups and triggers: a None setup input is the inventory's documented fail-closed path
    **{
        code: _row(_F + f"setup.{owner_input}", _SETUP_NONE)
        for code, owner_input in (
            ("BULL_TREND_CONTINUATION_INPUT_MISSING", "BullTrendContinuationInput.trend_score"),
            ("BULLISH_RESET_INPUT_MISSING", "BullishResetInput.trend_score"),
            ("BULLISH_RESET_FUNDING_HEALTH_HISTORY_INSUFFICIENT", "BullishResetInput.funding_health_history"),
            ("BULLISH_RESET_OI_HEALTH_HISTORY_INSUFFICIENT", "BullishResetInput.oi_health_history"),
            ("BULLISH_RESET_FLOW_ACCEL_HISTORY_INSUFFICIENT", "BullishResetInput.flow_accel_history"),
            ("CAPITULATION_REVERSAL_INPUT_MISSING", "CapitulationReversalInput.capitulation_flagged"),
            ("RECLAIM_TRIGGER_CONFIRMATION_PENDING", "BullishResetInput.entry_trigger_confirmed"),
            ("HIGHER_LOW_SOURCE_BAR_MISSING", "CapitulationReversalInput.confirmation_triggered"),
            ("HIGHER_LOW_PIVOT_PENDING", "CapitulationReversalInput.confirmation_triggered"),
            ("HIGHER_LOW_PULLBACK_PENDING", "CapitulationReversalInput.confirmation_triggered"),
            ("HIGHER_LOW_BREAK_PENDING", "CapitulationReversalInput.confirmation_triggered"),
        )
    },
}

# On a complete owner result only these codes signal a missing input; on an
# incomplete result every code is checked and at least one must be accounted.
_MISSING_MARKERS = ("INPUT_MISSING", "INSUFFICIENT_HISTORY", "HISTORY_INSUFFICIENT", "ZERO_VARIANCE", "PREVIOUS_SCORE_MISSING", "_UNKNOWN")


def accounted_cause(code: str, feature_id: str | None = None) -> AccountedCause | None:
    if feature_id is not None and (feature_id, code) in CAUSE_ACCOUNTING:
        return CAUSE_ACCOUNTING[(feature_id, code)]
    return CAUSE_ACCOUNTING.get(code)


# --- composer inputs ------------------------------------------------------------------


@dataclass(frozen=True)
class LiquidationPercentileObservation:
    """One UTC day's ``LIQUIDATION_PERCENTILE``.

    The value is reused by reference from EPIC X
    ``PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1`` under
    ``HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`` (policy V7 section 4A). It
    is an excluded owner-less certified definition: the composer consumes it
    and never computes it. ``None`` is a day the adapter refused
    (``LIQUIDATION_FEED_UNAVAILABLE``). It is never filled with zero.
    """

    observation_date: date
    liquidation_percentile: Decimal | None
    available_at: datetime
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.observation_date) is not date:
            raise EntryComposerError("INPUT_REFUSED", "observation_date must be a date")
        available = _utc(self.available_at, "available_at")
        day_end = datetime(self.observation_date.year, self.observation_date.month, self.observation_date.day, tzinfo=UTC) + _DAY
        if available < day_end:
            raise EntryComposerError("INPUT_REFUSED", "a liquidation day is never available before it ends")
        value = self.liquidation_percentile
        if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or not Decimal("0") <= value <= Decimal("100")):
            raise EntryComposerError("INPUT_REFUSED", "liquidation_percentile must be a Decimal on 0-100 or None")


@dataclass(frozen=True)
class EtfFundLaunch:
    """A US spot bitcoin ETF's first US trading date, with its source evidence.

    Policy V7 section 5 (adopted verbatim) passes, per window, the funds whose
    first trading date is on or before the window's first included publication
    date.
    """

    fund: str
    first_trading_date: date
    source: str

    def __post_init__(self) -> None:
        if not self.fund or type(self.first_trading_date) is not date or not self.source.strip():
            raise EntryComposerError("INPUT_REFUSED", "an ETF fund launch needs a fund, a date and source evidence")


@dataclass(frozen=True)
class EntryComposerInputs:
    """Every replay input the entry composer reads, each with modelled availability.

    ``dataset`` carries the venue's 1h price stream and the shared snapshot:
    Bitstamp 1h volume, ETF flows, funding, open interest and perp volume. The
    following families have no reviewed replay builder yet (RBT-001A); they
    arrive as owner records whose availability fields carry the policy V7
    section 4 modelled availability:
    - futures basis (``SNAPSHOT``);
    - market cap (``DAILY_PUBLISHED``);
    - the liquidation percentile.
    """

    dataset: VenueReplayDataset
    futures_basis: tuple[FuturesBasis, ...] = ()
    market_caps: tuple[MarketCapObservation, ...] = ()
    liquidation_percentiles: tuple[LiquidationPercentileObservation, ...] = ()
    etf_fund_launches: tuple[EtfFundLaunch, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, VenueReplayDataset):
            raise EntryComposerError("INPUT_REFUSED", "dataset must be a reviewed VenueReplayDataset")
        funds = [launch.fund for launch in self.etf_fund_launches]
        if len(funds) != len(set(funds)):
            raise EntryComposerError("INPUT_REFUSED", "an ETF fund launch is listed twice")
        days = [item.observation_date for item in self.liquidation_percentiles]
        if len(days) != len(set(days)):
            raise EntryComposerError("INPUT_REFUSED", "a liquidation day is listed twice")


# --- ledger ---------------------------------------------------------------------------


# The owner-input fields each policy V7 section 6A.9 guard withholds on refusal
# (the frozen contracts' clause 6), recorded per refusal so every downstream
# None is attributed to the guard's cause (clause 7).
GUARD_WITHHELD_INPUTS: Mapping[str, tuple[str, ...]] = {
    "FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1": (
        "PositioningScoreInput.funding_health", "CrowdingFlagInput.funding_zscore", "StressFlagInput.funding_zscore",
        "CapitulationFlagInput.funding_zscore", "EuphoriaFlagInput.funding_zscore",
    ),
    "FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1": (
        "PositioningScoreInput.basis_health", "CrowdingFlagInput.basis_zscore", "StressFlagInput.basis_zscore",
        "EuphoriaFlagInput.basis_zscore",
    ),
    # no composed owner consumes oi_growth_zscore
    "OI_GROWTH_ZERO_VARIANCE_GUARD_V1": ("PositioningScoreInput.oi_health",),
}


@dataclass(frozen=True)
class GuardRefusal:
    guard_id: str
    owner: str
    reason_code: str
    history_observation_count: int
    observation_time: datetime

    @property
    def withheld_inputs(self) -> tuple[str, ...]:
        return GUARD_WITHHELD_INPUTS[self.guard_id]

    def as_record(self) -> dict[str, Any]:
        return {
            "guard_id": self.guard_id,
            "owner": self.owner,
            "reason_code": self.reason_code,
            "history_observation_count": self.history_observation_count,
            "observation_time": self.observation_time.isoformat(),
            "withheld_inputs": list(self.withheld_inputs),
        }


@dataclass(frozen=True)
class UnevaluableComponent:
    component: str
    causes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "causes": [
                {"code": code, **(_accounting_record(code))} for code in self.causes
            ],
        }


@dataclass(frozen=True)
class EntryDecisionRow:
    """One decision-ledger row: the outcome at one daily decision instant."""

    decision_at: datetime
    venue: str
    outcome: str
    reasons: tuple[str, ...]
    position_open: bool
    setup: str | None
    detected_setups: tuple[str, ...]
    entry_conviction: Decimal | None
    entry_action: str | None
    regime: Mapping[str, Any]
    components: Mapping[str, Any]
    flags: Mapping[str, Any]
    unevaluable: tuple[UnevaluableComponent, ...]
    guard_refusals: tuple[GuardRefusal, ...]
    owner_reason_codes: Mapping[str, Any]
    unaccounted: tuple[str, ...]
    features: Mapping[str, Decimal | None]
    data_quality: Mapping[str, Any]
    intent: Mapping[str, Any] | None
    capitulation_flag_state: bool | None = None

    def as_record(self) -> dict[str, Any]:
        return _jsonable(
            {
                "decision_at": self.decision_at,
                "venue": self.venue,
                "outcome": self.outcome,
                "reasons": list(self.reasons),
                "position_open": self.position_open,
                "setup": self.setup,
                "detected_setups": list(self.detected_setups),
                "entry_conviction": self.entry_conviction,
                "entry_action": self.entry_action,
                "regime": self.regime,
                "components": self.components,
                "flags": self.flags,
                "unevaluable": [item.as_record() for item in self.unevaluable],
                "guard_refusals": [item.as_record() for item in self.guard_refusals],
                "owner_reason_codes": self.owner_reason_codes,
                "unaccounted": list(self.unaccounted),
                "features": self.features,
                "data_quality": self.data_quality,
                "intent": self.intent,
                "capitulation_flag_state": self.capitulation_flag_state,
            }
        )


@dataclass(frozen=True)
class EntryDecision:
    """The decision at one instant: its ledger row and, for ARM_ENTRY, the intent."""

    row: EntryDecisionRow
    intent: BacktestIntent | None


# --- composer -------------------------------------------------------------------------


def is_daily_decision_instant(instant: datetime) -> bool:
    moment = _utc(instant, "instant")
    return moment.hour == 0 and moment.minute == 0 and moment.second == 0 and moment.microsecond == 0


class EntryComposer:
    """The flat-state champion composer (RBT-004).

    :meth:`decide` is engine-agnostic: decision instant in, decision record
    out. That lets the advisory and paper paths drive the same composer later
    (Rulebook invariant 15); adopting it there is out of scope. Calling the
    instance is the BTC-180 ``run_backtest`` strategy adapter.
    """

    def __init__(self, inputs: EntryComposerInputs, *, strategy_config: StrategyConfig) -> None:
        if not isinstance(inputs, EntryComposerInputs):
            raise EntryComposerError("INPUT_REFUSED", "inputs must be EntryComposerInputs")
        if not isinstance(strategy_config, StrategyConfig):
            raise EntryComposerError("INPUT_REFUSED", "strategy_config must be a StrategyConfig")
        metadata = strategy_config.run_metadata()
        if dict(metadata) != dict(CHAMPION_BASE_IDENTITY):
            raise EntryComposerError("CHAMPION_IDENTITY", f"the champion is {dict(CHAMPION_BASE_IDENTITY)}, not {dict(metadata)}")
        self._inputs = inputs
        self._config = strategy_config
        self._metadata = dict(metadata)
        self._venue = inputs.dataset.venue.venue_id
        self._window = inputs.dataset.window
        self._hourly = tuple(sorted(inputs.dataset.price_bars, key=lambda bar: bar.timestamp))
        self._hourly_available = [bar.ingested_at for bar in self._hourly]
        # _visible_hourly bisects this list, so availability must follow bar order.
        if any(later < earlier for earlier, later in zip(self._hourly_available, self._hourly_available[1:])):
            raise EntryComposerError("INPUT_REFUSED", "hourly bar availability must be nondecreasing in bar order")
        shared = inputs.dataset.shared_snapshot
        self._volume_by_hour = {bar.timestamp: (bar.volume, bar.ingested_at) for bar in shared.volume_bars}
        self._launches = {launch.fund: launch.first_trading_date for launch in inputs.etf_fund_launches}
        self._liquidations = {item.observation_date: item for item in inputs.liquidation_percentiles}
        # US_EQUITY_MARKET_CLOSURE_TABLE_V1, loaded and hash-verified once, then
        # passed whole to every ETF flow window. The flow owner reads only the
        # dates on or before each window's end, so later closures never matter.
        self._market_holidays = load_closures(CLOSURE_TABLE_COVERAGE_START, CLOSURE_TABLE_COVERAGE_END)
        self._ledger: list[EntryDecisionRow] = []
        self._last_decision_at: datetime | None = None
        self._last_position_open = False
        # Exact memos. Every replay input is immutable, and an owner result at a
        # past instant reads only what was visible then, so it never changes.
        self._volume_percentile_memo: dict[tuple[Any, ...], tuple[Decimal | None, str | None]] = {}
        self._health_memo: dict[tuple[str, datetime], Decimal | None] = {}
        self._rv20_memo: dict[datetime, Any] = {}

    # -- public ---------------------------------------------------------------------

    @property
    def ledger(self) -> tuple[EntryDecisionRow, ...]:
        return tuple(self._ledger)

    @property
    def closure_table_version(self) -> str:
        return CLOSURE_TABLE_VERSION

    def ledger_records(self) -> list[dict[str, Any]]:
        return [row.as_record() for row in self._ledger]

    def ledger_bytes(self) -> bytes:
        header = {
            "ledger_version": LEDGER_VERSION,
            "composer_version": ENTRY_COMPOSER_VERSION,
            "research_strategy_id": RESEARCH_STRATEGY_ID,
            "completion_spec": {"version": SPEC_VERSION, "sha256": COMPLETION_SPEC_SHA256},
            "champion_base_identity": dict(CHAMPION_BASE_IDENTITY),
            "venue": self._venue,
            "closure_table": CLOSURE_TABLE_VERSION,
            "rows": self.ledger_records(),
        }
        return canonical_json_bytes(header)

    def ledger_sha256(self) -> str:
        return sha256_hex(self.ledger_bytes())

    def unaccounted_causes(self) -> tuple[tuple[str, str], ...]:
        return tuple((row.decision_at.isoformat(), code) for row in self._ledger for code in row.unaccounted)

    def __call__(self, context: BacktestContext) -> BacktestIntent | None:
        """The BTC-180 strategy callback: decide at daily decision instants only."""

        as_of = context.as_of
        # The position at a missed midnight is the one the previous callback saw:
        # the engine processes no bar between that callback and this one's bar.
        position_before = self._last_position_open
        self._last_position_open = context.position_open
        if not is_daily_decision_instant(as_of):
            return None
        if self._last_decision_at is not None:
            missed = self._last_decision_at + _DAY
            while missed < as_of:
                decision = self.decide(missed, position_open=position_before)
                if decision.row.reasons != (CAUSE_DECISION_PRICE_BAR_MISSING,):
                    # The engine skipped a midnight whose decision bar the composer
                    # sees: its bars differ from the replay inputs. Never drop it.
                    raise EntryComposerError("COMPOSER_DEFECT", f"the engine offered no callback at {missed.isoformat()}, which has a decision bar")
                self._append(decision)
                missed += _DAY
        decision = self.decide(as_of, position_open=context.position_open)
        if decision.intent is not None and context.bar.close != decision.intent.entry_zone_upper:
            raise EntryComposerError("COMPOSER_DEFECT", "the decision price differs from the engine's decision bar close")
        self._append(decision)
        return decision.intent

    def decide(self, as_of: datetime, *, position_open: bool = False) -> EntryDecision:
        """Compose the entry decision at one daily decision instant (no ledger write)."""

        instant = _utc(as_of, "as_of")
        if not is_daily_decision_instant(instant):
            raise EntryComposerError("NOT_A_DECISION_INSTANT", f"{instant.isoformat()} is not a UTC midnight")
        if self._ledger and instant <= self._ledger[-1].decision_at:
            raise EntryComposerError("DECISION_ORDER", "decision instants must strictly increase")
        return _DecisionRun(self, instant, position_open=position_open).run()

    def record(self, decision: EntryDecision) -> None:
        """Append a :meth:`decide` result to the ledger (the engine adapter does this)."""

        self._append(decision)

    # -- internals ------------------------------------------------------------------

    def _append(self, decision: EntryDecision) -> None:
        if self._ledger and decision.row.decision_at <= self._ledger[-1].decision_at:
            raise EntryComposerError("DECISION_ORDER", "ledger rows must strictly increase")
        self._ledger.append(decision.row)
        self._last_decision_at = decision.row.decision_at

    def _visible_hourly(self, instant: datetime) -> tuple[OhlcvBar, ...]:
        end = bisect.bisect_right(self._hourly_available, instant)
        return self._hourly[:end]

    def _previous_row(self) -> EntryDecisionRow | None:
        return self._ledger[-1] if self._ledger else None


class _DecisionRun:
    """One decision instant's composition; it records every owner result."""

    def __init__(self, composer: EntryComposer, instant: datetime, *, position_open: bool) -> None:
        self.c = composer
        self.t = instant
        self.position_open = position_open
        self.config = composer._config
        self.metadata = composer._metadata
        self.results: dict[str, Any] = {}
        # Auxiliary owner results (history windows, calendar pages, recomputed
        # histories): not ledgered, but held to the same policy V7 section 5A.6
        # accounting as every recorded result.
        self.auxiliary: list[tuple[str, Any]] = []
        self.composer_causes: dict[str, list[str]] = {}
        self.guard_refusals: list[GuardRefusal] = []
        self.features: dict[str, Decimal | None] = {name: None for name in FEATURE_NAMES}
        self.detected: tuple[str, ...] = ()
        self.gate_record: dict[str, Any] | None = None
        self.capitulation_now: bool | None = None
        self.calendar: list[date] = []

    # -- recording ----------------------------------------------------------------

    def _keep(self, label: str, result: Any) -> Any:
        self.results[label] = result
        return result

    def _check(self, label: str, result: Any) -> Any:
        self.auxiliary.append((label, result))
        return result

    def _cause(self, component: str, code: str) -> None:
        self.composer_causes.setdefault(component, [])
        if code not in self.composer_causes[component]:
            self.composer_causes[component].append(code)

    # -- run ------------------------------------------------------------------------

    def run(self) -> EntryDecision:
        hourly = self.c._visible_hourly(self.t)
        if not hourly or hourly[-1].ingested_at != self.t:
            return self._price_bar_missing()
        self.price = hourly[-1].close
        canonical = replay_market_bars_at(hourly, decision_at=self.t, window=self.c._window)
        self.daily = tuple(bar for bar in canonical if bar.timeframe == "1d")
        self.weekly = tuple(bar for bar in canonical if bar.timeframe == "1w")
        self.monthly = tuple(bar for bar in canonical if bar.timeframe == "1mo")
        self.hourly = hourly

        self.data_quality = self._data_quality()
        trend = self._trend()
        flow = self._flow()
        positioning = self._positioning()
        volatility = self._volatility()
        regime = self._regime(trend, flow, volatility, positioning)
        flags = self._flags()
        geometry = self._geometry()
        structure = self._structure(geometry)
        conviction = self._keep(
            "entry_conviction",
            calculate_entry_conviction(
                EntryConvictionInput(
                    trend_score=trend,
                    flow_score=flow,
                    positioning_score=positioning,
                    volatility_score=volatility,
                    structure_score=structure,
                ),
                strategy_config=self.config,
            ),
        )
        action = self._keep("entry_action", classify_entry_action(conviction.score, strategy_config=self.config))
        self.features.update(
            {
                "TREND_SCORE": trend,
                "FLOW_SCORE": flow,
                "POSITIONING_SCORE": positioning,
                "VOLATILITY_SCORE": volatility,
                "STRUCTURE_SCORE": structure,
            }
        )
        components = dict(zip(COMPONENT_NAMES, (trend, flow, positioning, volatility, structure)))

        if self.position_open:
            return self._finish(OUTCOME_NO_TRADE, (REASON_POSITION_ALREADY_OPEN,), components, regime, flags, conviction, action)
        if not conviction.complete:
            missing = [name for name, value in components.items() if value is None]
            if missing == ["structure"] and geometry["no_stop_cause"] == "GEOMETRY":
                return self._finish(OUTCOME_NO_TRADE, (REASON_NO_VALID_STRUCTURAL_STOP,), components, regime, flags, conviction, action)
            return self._finish(OUTCOME_STRUCTURALLY_UNEVALUABLE, tuple(f"{name.upper()}_INCOMPLETE" for name in missing), components, regime, flags, conviction, action)

        setups = self._setups(regime, flags, geometry, structure, conviction)
        detected = tuple(name for name in LONG_ARCHETYPES if setups[name].detected)
        self.detected = detected
        if not detected:
            return self._finish(OUTCOME_NO_TRADE, (REASON_NO_SETUP_DETECTED,), components, regime, flags, conviction, action)
        if CAPITULATION_REVERSAL_SETUP in detected and set(detected) & _SHARED_GEOMETRY_ARCHETYPES:
            return self._finish(OUTCOME_NO_TRADE, (REASON_SETUP_GEOMETRY_CONFLICT,), components, regime, flags, conviction, action)
        setup = detected[0]
        return self._gate(setup, setups[setup], geometry, flags, components, regime, conviction, action)

    # -- step 0: missing decision bar -----------------------------------------------------

    def _price_bar_missing(self) -> EntryDecision:
        self.data_quality = {"evaluated": False}
        self._cause("decision_instant", CAUSE_DECISION_PRICE_BAR_MISSING)
        row = EntryDecisionRow(
            decision_at=self.t,
            venue=self.c._venue,
            outcome=OUTCOME_STRUCTURALLY_UNEVALUABLE,
            reasons=(CAUSE_DECISION_PRICE_BAR_MISSING,),
            position_open=self.position_open,
            setup=None,
            detected_setups=(),
            entry_conviction=None,
            entry_action=None,
            # the same keys as every evaluated row, all unevaluated
            regime={"model": None, "score": None, "smoothed_score": None, "previous_smoothed_score": None, "classification": None, "complete": False},
            components={name: None for name in COMPONENT_NAMES},
            flags={},
            unevaluable=(UnevaluableComponent("decision_instant", (CAUSE_DECISION_PRICE_BAR_MISSING,)),),
            guard_refusals=(),
            owner_reason_codes={},
            unaccounted=self._unaccounted(),
            features=dict(self.features),
            data_quality=self.data_quality,
            intent=None,
            capitulation_flag_state=None,
        )
        return EntryDecision(row, None)

    # -- data quality (Rulebook 24 DATA_QUALITY_FAIL; owner ruling: the last completed UTC day)

    def _data_quality(self) -> dict[str, Any]:
        start = self.t - _DAY
        day_bars = tuple(bar for bar in self.hourly if start <= bar.timestamp < self.t)
        ohlcv = validate_ohlcv_quality(day_bars, start=start, end=self.t - _HOUR, timeframe="1h", as_of=self.t)
        shared = self.c._inputs.dataset.shared_snapshot
        derivatives_rows = tuple(
            row
            for family in (shared.funding_rates, shared.open_interest, shared.perp_volumes)
            for row in family
            if row.available_at <= self.t and start < row.observation_time <= self.t
        )
        derivatives = validate_derivatives_quality(derivatives_rows, as_of=self.t)
        self.quality_failures = failures_from_quality_reports({"ohlcv_1h": ohlcv, "derivatives": derivatives})
        return {
            "evaluated": True,
            "window_start": start,
            "window_end": self.t,
            "data_quality_fail": bool(self.quality_failures),
            "failures": [
                {"source_component": failure.source_component, "reason_codes": list(failure.reason_codes)}
                for failure in self.quality_failures
            ],
        }

    # -- step 1: trend ----------------------------------------------------------------

    def _trend(self) -> Decimal | None:
        m4 = four_week_momentum_from_daily_bars(self.daily)
        m12 = twelve_week_momentum_from_daily_bars(self.daily)
        d20 = twenty_week_ma_distance_from_weekly_bars(self.weekly)
        h52 = fifty_two_week_high_distance_from_weekly_bars(self.weekly)
        structure = classify_weekly_structure_from_weekly_bars(self.weekly)
        self.high_distance = h52[-1] if h52 else None
        self.momentum_4w_series = m4
        self.momentum_12w_series = m12
        self.features.update(
            {
                "MOMENTUM_4W": m4[-1] if m4 else None,
                "MOMENTUM_12W": m12[-1] if m12 else None,
                "MA_DISTANCE_20W": d20[-1] if d20 else None,
                "HIGH_DISTANCE_52W": self.high_distance,
            }
        )
        values = {}
        for input_id, series in (("TREND_Z_M4", m4), ("TREND_Z_M12", m12), ("TREND_Z_20W", d20), ("TREND_Z_52H", h52)):
            values[input_id], cause = _uniform_zscore(series, input_id=input_id)
            if cause is not None:
                self._cause("trend", cause)
        self.trend_z = values
        structure_score = structure[-1].raw_score if structure and structure[-1] is not None else None
        if structure_score is None:
            self._cause("trend", CAUSE_WEEKLY_STRUCTURE_MISSING)
        if any(value is None for value in values.values()) or structure_score is None:
            # TrendScoreInput has no None path: the owner is not called and the
            # trend component stays None (spec MISSING_TREND; never zero-filled).
            return None
        result = (
            calculate_trend_score(
                TrendScoreInput(
                    z_m4=values["TREND_Z_M4"],
                    z_m12=values["TREND_Z_M12"],
                    z_20w=values["TREND_Z_20W"],
                    structure_score=structure_score,
                    z_52h=values["TREND_Z_52H"],
                )
            )
        )
        return result.score

    # -- step 1: flow (ETF_CORE) ----------------------------------------------------------

    def _flow(self) -> Decimal | None:
        shared = self.c._inputs.dataset.shared_snapshot
        visible = tuple(flow for flow in shared.etf_flows if flow.available_at <= self.t)
        unknown = sorted({flow.fund for flow in visible} - set(self.c._launches))
        if unknown:
            raise EntryComposerError("INPUT_REFUSED", f"ETF funds without a recorded first trading date: {unknown}")
        self.flow_accel_native: list[Decimal | None] = []
        cvd = self._keep("cvd_spread", spot_perp_cvd_spread((), as_of=self.t))
        self.features["CVD_SPREAD"] = cvd.cvd_spread
        z_values: dict[str, Decimal | None] = {}
        if not visible:
            for input_id in ("FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"):
                z_values[input_id] = None
                self._cause("flow", f"{input_id}_INPUT_MISSING")
        else:
            z_values = self._flow_zscores(visible)
        self.flow_z = z_values
        result = self._keep(
            "flow_score",
            calculate_flow_score(
                FlowScoreInput(
                    etf_norm_5_zscore=z_values["FLOW_Z_ETF_NORM_5D"],
                    etf_norm_20_zscore=z_values["FLOW_Z_ETF_NORM_20D"],
                    flow_accel_zscore=z_values["FLOW_Z_FLOW_ACCEL"],
                    cvd_spread_zscore=None,
                    spot_dominance_zscore=None,
                ),
                core_weights=dict(self.config.scoring_weights.core_flow),
                full_weights=dict(self.config.scoring_weights.full_flow),
                config_metadata=self.metadata,
            ),
        )
        self.flow_result = result
        return result.score if result.complete else None

    def _flow_zscores(self, visible: tuple[Any, ...]) -> dict[str, Decimal | None]:
        holidays = self.c._market_holidays
        # D: the owner's own latest visible observation date (end_date=None). Only
        # D is read from this call; its window value is never consumed, so it is
        # audited with the auxiliary results rather than ledgered as a flow input.
        anchor = self._check("etf_anchor", five_day_etf_flow(visible, as_of=self.t, market_holidays=holidays))
        latest = anchor.observation_date
        earliest_observation = min(flow.observation_date for flow in visible)
        self.calendar = []
        values = {"5": [], "20": [], "accel": []}
        current: dict[str, Decimal | None] = {}
        native_accel: list[Decimal | None] = []
        index = -1
        while True:
            index += 1
            self._extend_calendar(visible, latest, index + 20)
            day = self.calendar[index]
            if day < earliest_observation and index > 0:
                break
            five = self._etf_window(visible, index, 5)
            twenty = self._etf_window(visible, index, 20)
            n5 = five.normalized_flow if five is not None and five.complete else None
            n20 = twenty.normalized_flow if twenty is not None and twenty.complete else None
            accel_value = None
            if five is not None and twenty is not None:
                accel = self._check("etf_flow_acceleration_history", etf_flow_acceleration(five, twenty))
                if index == 0:
                    self._keep("etf_flow_acceleration", accel)
                accel_value = accel.acceleration if accel.complete else None
            if index == 0:
                current = {"5": n5, "20": n20, "accel": accel_value}
                if five is not None:
                    self._keep("etf_flow_5d", five)
                if twenty is not None:
                    self._keep("etf_flow_20d", twenty)
            else:
                for key, value in (("5", n5), ("20", n20), ("accel", accel_value)):
                    if value is not None:
                        values[key].append(value)
            if len(native_accel) <= int(self.config.setup_requirements.bullish_reset["flow_accel_improving_days"]):
                native_accel.append(accel_value)
            if index > 0 and all(len(values[key]) >= UNIFORM_ZSCORE_WINDOW_OBSERVATIONS for key in values):
                break
        # flow_accel_history in chronological order: prior publication days, then D.
        self.flow_accel_native = list(reversed(native_accel))
        self.features.update({"ETF_NORM_5D": current.get("5"), "ETF_NORM_20D": current.get("20"), "FLOW_ACCEL": current.get("accel")})
        z_values = {}
        for input_id, key in (("FLOW_Z_ETF_NORM_5D", "5"), ("FLOW_Z_ETF_NORM_20D", "20"), ("FLOW_Z_FLOW_ACCEL", "accel")):
            series = (*reversed(values[key]), current.get(key))
            z_values[input_id], cause = _uniform_zscore(series, input_id=input_id)
            if cause is not None:
                self._cause("flow", cause)
        return z_values

    def _extend_calendar(self, visible: tuple[Any, ...], latest: date, size: int) -> None:
        """US publication days on or before D, newest first, read from the owner's own windows.

        The calendar is never restated: each page is the ``included_observation_dates``
        of a 20-day window the flow owner computes with the loaded closure table.
        """

        while len(self.calendar) < size:
            end = latest if not self.calendar else self.calendar[-1] - _DAY
            page = self._check("etf_calendar_page", twenty_day_etf_flow(visible, as_of=self.t, market_holidays=self.c._market_holidays, end_date=end))
            self.calendar.extend(day for day in reversed(page.included_observation_dates) if not self.calendar or day < self.calendar[-1])

    def _etf_window(self, visible: tuple[Any, ...], index: int, window: int) -> Any:
        dates = self.calendar[index : index + window]
        first = dates[-1]
        funds = tuple(sorted(fund for fund, launch in self.c._launches.items() if launch <= first))
        if not funds:
            return None  # every window before the first fund launch: pre-launch, never invented
        if window == 5:
            result = five_day_etf_flow(visible, as_of=self.t, funds=funds, market_holidays=self.c._market_holidays, end_date=self.calendar[index])
        else:
            result = twenty_day_etf_flow(visible, as_of=self.t, funds=funds, market_holidays=self.c._market_holidays, end_date=self.calendar[index])
        self._check(f"etf_window_{window}d", result)
        if tuple(reversed(dates)) != tuple(result.included_observation_dates):
            raise EntryComposerError("COMPOSER_DEFECT", "the owner's window disagrees with its own publication calendar")
        return result

    # -- step 1: positioning (policy V7 section 6A.9 guards) -------------------------------

    def _visible_rows(self, rows: Sequence[Any]) -> tuple[Any, ...]:
        return tuple(row for row in rows if row.available_at <= self.t)

    def _owner_visible(self, rows: Sequence[Any], unit: str | None = None) -> tuple[Any, ...]:
        # The owners' own inline two-field predicate (positioning.py), applied identically.
        return tuple(
            row
            for row in rows
            if (unit is None or row.open_interest_unit == unit)
            and row.as_record()["available_at"] <= self.t
            and row.as_record()["observation_time"] <= self.t
        )

    def _positioning(self) -> Decimal | None:
        shared = self.c._inputs.dataset.shared_snapshot
        funding_rows = self._visible_rows(shared.funding_rates)
        basis_rows = self._visible_rows(self.c._inputs.futures_basis)
        oi_rows = self._visible_rows(shared.open_interest)
        caps = tuple(cap for cap in self.c._inputs.market_caps if cap.available_at <= self.t)

        funding = self._keep("funding_health", funding_health(funding_rows, as_of=self.t))
        basis = self._keep("futures_basis_health", futures_basis_health(basis_rows, as_of=self.t))
        growth = self._keep(
            "open_interest_growth_health",
            open_interest_growth_health(oi_rows, as_of=self.t, open_interest_unit=OPEN_INTEREST_UNIT),
        )
        intensity = self._keep(
            "open_interest_intensity",
            open_interest_intensity(oi_rows, caps, as_of=self.t, open_interest_unit=OPEN_INTEREST_UNIT),
        )
        funding_refused = self._guard_funding(funding_rows, funding)
        basis_refused = self._guard_basis(basis_rows, basis)
        growth_refused = self._guard_growth(oi_rows, growth)
        self.funding_z = None if funding_refused else funding.funding_zscore
        self.basis_z = None if basis_refused else basis.annualized_basis_zscore
        self.oi_growth_z = None if growth_refused else growth.oi_growth_zscore
        self.oi_intensity_percentile = intensity.oi_intensity_percentile
        funding_score = None if funding_refused else funding.health_score
        basis_score = None if basis_refused else basis.health_score
        growth_score = None if growth_refused else growth.health_score
        self.c._health_memo[("funding", self.t)] = funding_score
        self.c._health_memo[("growth", self.t)] = growth_score
        self.features.update(
            {
                "FUNDING_7D_AVG": funding.funding_7d_avg,
                "FUNDING_ZSCORE_180D": self.funding_z,
                "FUNDING_HEALTH": funding_score,
                "OI_GROWTH_7D": growth.oi_growth,
                "OI_GROWTH_ZSCORE_180D": self.oi_growth_z,
                "OI_GROWTH_HEALTH": growth_score,
                "OI_INTENSITY": intensity.oi_intensity,
                "OI_INTENSITY_PERCENTILE_180D": intensity.oi_intensity_percentile,
                "FUTURES_BASIS_AVG": basis.annualized_basis_rate_avg,
                "FUTURES_BASIS_ZSCORE_180D": self.basis_z,
                "FUTURES_BASIS_HEALTH": basis_score,
            }
        )
        result = self._keep(
            "positioning_score",
            calculate_positioning_score(
                PositioningScoreInput(
                    funding_health=funding_score,
                    oi_health=growth_score,
                    basis_health=basis_score,
                    leverage_health=intensity.health_score,
                ),
                weights=dict(self.config.scoring_weights.positioning),
                config_metadata=self.metadata,
            ),
        )
        return result.score if result.complete else None

    def _refuse(self, guard_id: str, owner: str, code: str, result: Any) -> bool:
        self.guard_refusals.append(GuardRefusal(guard_id, owner, code, result.history_observation_count, result.observation_time))
        self._cause("positioning", code)
        return True

    def _check_history(self, history: tuple[Decimal, ...], latest: datetime | None, result: Any) -> None:
        if len(history) != result.history_observation_count or latest != result.observation_time:
            raise EntryComposerError("COMPOSER_DEFECT", f"{result.feature_id}: the guard's history disagrees with the owner result")

    def _guard_funding(self, rows: tuple[Any, ...], result: Any) -> bool:
        if result.funding_zscore is None:
            return False
        rows_t = self._owner_visible(rows)
        averages = _funding_averages_by_time(rows_t, average_window_days=result.average_window_days)
        history = _funding_average_history(averages, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)
        self._check_history(history, max(averages) if averages else None, result)
        if all(value == history[0] for value in history):
            return self._refuse("FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1", "funding_health", "FUNDING_HEALTH_ZERO_VARIANCE", result)
        return False

    def _guard_basis(self, rows: tuple[Any, ...], result: Any) -> bool:
        if result.annualized_basis_zscore is None:
            return False
        rows_t = self._owner_visible(rows)
        averages = _futures_basis_averages_by_time(rows_t)
        history = _futures_basis_history(averages, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)
        self._check_history(history, max(averages) if averages else None, result)
        if all(value == history[0] for value in history):
            return self._refuse("FUTURES_BASIS_ZERO_VARIANCE_GUARD_V1", "futures_basis_health", "FUTURES_BASIS_ZERO_VARIANCE", result)
        return False

    def _guard_growth(self, rows: tuple[Any, ...], result: Any) -> bool:
        if result.oi_growth_zscore is None:
            return False
        rows_t = self._owner_visible(rows, unit=result.open_interest_unit)
        aggregate = _aggregate_open_interest_by_time(rows_t)
        growth = _open_interest_growth_by_time(aggregate, growth_window_days=result.growth_window_days)
        history = _oi_growth_history(growth, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)
        self._check_history(history, max(aggregate) if aggregate else None, result)
        if all(value == history[0] for value in history):
            return self._refuse("OI_GROWTH_ZERO_VARIANCE_GUARD_V1", "open_interest_growth_health", "OI_GROWTH_ZERO_VARIANCE", result)
        return False

    # -- step 1: volatility -------------------------------------------------------------

    def _volatility(self) -> Decimal | None:
        daily = self.daily
        rv = {}
        for window, name in ((7, "RV_7"), (20, "RV_20"), (60, "RV_60")):
            rv[name] = self._keep(name.lower(), realized_volatility_from_daily_bars(daily, as_of=self.t, window_days=window))
            self.features[name] = rv[name].realized_volatility
        # A superset of the owner's own prior window (it selects the history itself);
        # older RV_20 results would be ignored by the owner, so they are not computed.
        history_start = daily[-1].timestamp - timedelta(days=DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS + 1) if daily else self.t
        rv20_history = tuple(self._rv20_at(bar) for bar in daily[:-1] if bar.timestamp >= history_start)
        percentile = self._keep("volatility_percentile", volatility_percentile((*rv20_history, rv["RV_20"]), as_of=self.t))
        compression = self._keep("volatility_compression", volatility_compression_ratio_from_results((rv["RV_7"], rv["RV_60"])))
        self.volatility_percentile_value = percentile.volatility_percentile
        self.features["VOL_PERCENTILE_2Y"] = percentile.volatility_percentile
        self.features["VOL_COMPRESSION_RATIO"] = compression.compression_ratio

        self.range_percentile, cause = self._range_percentile()
        if cause is not None:
            self._cause("volatility", cause)
        returns = price_momentum_from_daily_bars(daily, lookback_periods=RETURN_HORIZON_DAILY_BARS)
        self.seven_day_return = returns[-1] if returns else None
        if self.seven_day_return is None:
            self._cause("volatility", "DOWNSIDE_RETURN_INPUT_MISSING")
        self.liquidation_percentile = self._liquidation_percentile()
        orderliness = self._keep(
            "orderliness",
            calculate_orderliness_score(
                OrderlinessScoreInput(
                    range_percentile=self.range_percentile,
                    downside_return=self.seven_day_return,
                    liquidation_percentile=self.liquidation_percentile,
                    volatility_percentile=percentile.volatility_percentile,
                ),
                config_metadata=self.metadata,
            ),
        )
        self.features["ORDERLINESS_SCORE"] = orderliness.score
        result = self._keep(
            "volatility_score",
            calculate_volatility_score(
                VolatilityScoreInput(
                    compression_ratio=compression.compression_ratio,
                    orderliness_score=orderliness.score,
                    volatility_percentile=percentile.volatility_percentile,
                ),
                config_metadata=self.metadata,
            ),
        )
        return result.score if result.complete else None

    def _rv20_at(self, bar: OhlcvBar) -> Any:
        """RV_20 as of a past daily bar's close (memoised: it reads only bars visible then)."""

        if bar.timestamp not in self.c._rv20_memo:
            self.c._rv20_memo[bar.timestamp] = realized_volatility_from_daily_bars(self.daily, as_of=bar.ingested_at, window_days=20)
        return self._check("rv_20_history", self.c._rv20_memo[bar.timestamp])

    def _range_percentile(self) -> tuple[Decimal | None, str | None]:
        """RANGE_PERCENTILE: UNIFORM_PERCENTILE_V1 of TR(d) / close(d - 1 day)."""

        daily = self.daily
        if not daily:
            return None, "RANGE_PERCENTILE_INPUT_MISSING"
        ranges = true_ranges(daily)
        observations: list[tuple[datetime, Decimal | None]] = []
        for index, bar in enumerate(daily):
            # TR is None after an absent session; the first bar has no prior close.
            value = ranges[index] / daily[index - 1].close if index > 0 and ranges[index] is not None else None
            observations.append((bar.timestamp, value))
        return _uniform_percentile(observations, input_id="RANGE_PERCENTILE")

    def _liquidation_percentile(self) -> Decimal | None:
        """LIQUIDATION_PERCENTILE of the last completed UTC day ``[t - 1 day, t)``.

        A daily total is an ``INTERVAL`` value modelled available at its day's end
        (policy V7 section 4), so the day ending at ``t`` is the one visible at
        ``t``. An older day is never substituted for a missing one.
        """

        item = self.c._liquidations.get((self.t - _DAY).date())
        if item is None or item.available_at > self.t or item.liquidation_percentile is None:
            self._cause("volatility", CAUSE_LIQUIDATION_PERCENTILE_MISSING)
            return None
        return item.liquidation_percentile

    # -- step 2: regime -----------------------------------------------------------------

    def _regime(self, trend: Decimal | None, flow: Decimal | None, volatility: Decimal | None, positioning: Decimal | None) -> dict[str, Any]:
        score = self._keep(
            "regime_score",
            calculate_regime_score(
                RegimeScoreInput(trend_score=trend, flow_score=flow, volatility_score=volatility, positioning_score=positioning),
                core_weights=dict(self.config.scoring_weights.core_regime),
                full_weights=dict(self.config.scoring_weights.full_regime),
                config_metadata=self.metadata,
            ),
        )
        previous_row = self.c._previous_row()
        previous = previous_row.regime.get("smoothed_score") if previous_row is not None else None
        smoothed = self._keep(
            "regime_smoothing",
            calculate_regime_smoothing(
                RegimeSmoothingInput(previous_smoothed_score=previous, new_regime_score=score.score),
                previous_weight=self.config.regime_smoothing.previous_weight,
                new_weight=self.config.regime_smoothing.new_weight,
                config_metadata=self.metadata,
            ),
        )
        classification = self._keep(
            "regime_classification",
            calculate_regime_classification(smoothed.score, thresholds=self.config.regime_thresholds, config_metadata=self.metadata),
        )
        self.features["REGIME_SCORE"] = score.score
        self.features["REGIME_SMOOTHED_SCORE"] = smoothed.score
        self.regime_smoothed = smoothed.score
        return {
            "model": score.regime_model,
            "score": score.score,
            "smoothed_score": smoothed.score,
            "previous_smoothed_score": previous,
            "classification": classification.regime,
            "complete": classification.complete,
        }

    # -- step 2: Rulebook 24 flags ------------------------------------------------------

    def _flags(self) -> dict[str, Any]:
        stress_config = self.config.volatility_flags.stress
        stress_inputs = (
            self.volatility_percentile_value,
            self.liquidation_percentile,
            self.seven_day_return,
            self.funding_z,
            self.basis_z,
        )
        stress = self._keep(
            "stress",
            calculate_stress_flag(
                StressFlagInput(
                    volatility_percentile=self.volatility_percentile_value,
                    liquidation_percentile=self.liquidation_percentile,
                    downside_return=self.seven_day_return,
                    funding_zscore=self.funding_z,
                    basis_zscore=self.basis_z,
                    systemic_shock=None,
                ),
                volatility_percentile_min=stress_config.volatility_percentile_min,
                liquidation_percentile_min=stress_config.liquidation_percentile_min,
                downside_return_min=stress_config.downside_return_min,
                funding_abs_zscore_min=stress_config.funding_abs_zscore_min,
                basis_abs_zscore_min=stress_config.basis_abs_zscore_min,
                max_exposure_multiplier=stress_config.max_exposure_multiplier,
                block_new_trades=stress_config.block_new_trades,
                config_metadata=self.metadata,
            ),
        )
        # Policy V7 section 7 (V4 verbatim): pass flagged, recording
        # STRESS_INPUT_MISSING, when the only missing input is DISCRETIONARY.
        # Spec limitation STRESS_NON_DISCRETIONARY_MISSING: any other missing
        # input gives None, so the hard veto fails closed.
        stress_flagged = stress.flagged if all(value is not None for value in stress_inputs) else None

        crowding_config = self.config.positioning_flags.crowding
        crowding = self._keep(
            "crowding",
            calculate_crowding_flag(
                CrowdingFlagInput(
                    funding_zscore=self.funding_z,
                    basis_zscore=self.basis_z,
                    oi_intensity_percentile=self.oi_intensity_percentile,
                ),
                funding_zscore_min=crowding_config.funding_zscore_min,
                basis_zscore_min=crowding_config.basis_zscore_min,
                oi_intensity_percentile_min=crowding_config.oi_intensity_percentile_min,
                entry_quality_penalty=crowding_config.entry_quality_penalty,
                config_metadata=self.metadata,
            ),
        )
        # SEVERE_CROWDING_STATE = CROWDING.flagged if CROWDING.complete else None.
        severe_crowding = crowding.flagged if crowding.complete else None
        if severe_crowding is None:
            self._cause("flags", "SEVERE_CROWDING_STATE_INPUT_MISSING")

        capitulation_config = self.config.volatility_flags.capitulation
        capitulation_inputs = (
            self.range_percentile,
            self.seven_day_return,
            self.liquidation_percentile,
            self.volatility_percentile_value,
            self.funding_z,
        )
        capitulation = self._keep(
            "capitulation",
            calculate_capitulation_flag(
                CapitulationFlagInput(
                    range_percentile=self.range_percentile,
                    downside_return=self.seven_day_return,
                    liquidation_percentile=self.liquidation_percentile,
                    volatility_percentile=self.volatility_percentile_value,
                    funding_zscore=self.funding_z,
                    systemic_shock=None,
                ),
                range_percentile_min=capitulation_config.range_percentile_min,
                downside_return_min=capitulation_config.downside_return_min,
                liquidation_percentile_min=capitulation_config.liquidation_percentile_min,
                volatility_percentile_min=capitulation_config.volatility_percentile_min,
                funding_zscore_max=capitulation_config.funding_zscore_max,
                config_metadata=self.metadata,
            ),
        )
        # Owner ruling (Setup C): the V4 mapping, as for STRESS.
        self.capitulation_now = capitulation.flagged if all(value is not None for value in capitulation_inputs) else None

        euphoria_config = self.config.volatility_flags.euphoria
        euphoria = self._keep(
            "euphoria",
            calculate_euphoria_flag(
                EuphoriaFlagInput(
                    range_percentile=self.range_percentile,
                    upside_return=self.seven_day_return,
                    funding_zscore=self.funding_z,
                    basis_zscore=self.basis_z,
                    oi_intensity_percentile=self.oi_intensity_percentile,
                    volatility_percentile=self.volatility_percentile_value,
                    systemic_euphoria=None,
                ),
                range_percentile_min=euphoria_config.range_percentile_min,
                upside_return_min=euphoria_config.upside_return_min,
                funding_zscore_min=euphoria_config.funding_zscore_min,
                basis_zscore_min=euphoria_config.basis_zscore_min,
                oi_intensity_percentile_min=euphoria_config.oi_intensity_percentile_min,
                volatility_percentile_min=euphoria_config.volatility_percentile_min,
                config_metadata=self.metadata,
            ),
        )
        if self.seven_day_return is None:
            self._cause("flags", "UPSIDE_RETURN_INPUT_MISSING")
        self.stress_flagged = stress_flagged
        self.severe_crowding = severe_crowding
        self.stress_result = stress
        self.crowding_result = crowding
        return {
            "stress": {"flagged": stress.flagged, "mapped": stress_flagged, "complete": stress.complete, "reason_codes": stress.reason_codes},
            "crowding": {"flagged": crowding.flagged, "severe_crowding_state": severe_crowding, "complete": crowding.complete, "reason_codes": crowding.reason_codes},
            "capitulation": {"flagged": capitulation.flagged, "mapped": self.capitulation_now, "complete": capitulation.complete, "reason_codes": capitulation.reason_codes},
            "euphoria": {"flagged": euphoria.flagged, "complete": euphoria.complete, "reason_codes": euphoria.reason_codes},
        }

    # -- step 3/6: levels, clusters and geometry per long archetype ------------------------

    def _geometry(self) -> dict[str, Any]:
        levels_config = self.config.price_levels
        weekly_levels = (
            detect_weekly_swing_levels(
                self.weekly, as_of=self.t, left_bars=levels_config.swing_window_weeks, right_bars=levels_config.swing_window_weeks
            )
        )
        monthly_levels = (
            detect_monthly_swing_levels(
                self.monthly, as_of=self.t, left_bars=levels_config.swing_window_months, right_bars=levels_config.swing_window_months
            )
        )
        breakout_levels = (
            detect_breakout_reclaim_levels(
                (*weekly_levels, *monthly_levels),
                self.daily,
                as_of=self.t,
                breakout_close_buffer_fraction=levels_config.breakout_close_buffer_fraction,
                reclaim_close_buffer_fraction=levels_config.reclaim_close_buffer_fraction,
            )
        )
        clusters = self._keep(
            "clusters",
            cluster_price_levels(
                (*weekly_levels, *monthly_levels, *breakout_levels),
                as_of=self.t,
                reference_price=self.price,
                cluster_distance_fraction=levels_config.cluster_distance_fraction,
                minimum_level_strength=levels_config.minimum_level_strength,
            ),
        )
        atr = atr_from_daily_bars(self.daily, window=self.config.stop_buffers.atr_period)
        self.weekly_levels = weekly_levels
        self.breakout_levels = breakout_levels
        self.clusters = clusters
        self.atr = atr
        swing_highs = tuple(level for level in weekly_levels if level.level_type == WEEKLY_SWING_HIGH)
        per_setup: dict[str, dict[str, Any]] = {}
        for setup in LONG_ARCHETYPES:
            invalidation = self._keep(
                f"invalidation:{setup}",
                select_structural_invalidation(
                    clusters, setup=setup, entry_price=self.price, as_of=self.t, atr=atr, config_metadata=self.metadata
                ),
            )
            buffer = self._keep(
                f"buffer:{setup}",
                volatility_buffer_for_invalidation(
                    invalidation,
                    atr=atr,
                    atr_multiplier=self.config.stop_buffers.atr_multiplier,
                    atr_window=self.config.stop_buffers.atr_period,
                    config_metadata=self.metadata,
                ),
            )
            stop = self._keep(f"stop:{setup}", initial_stop_for_setup(invalidation, buffer, config_metadata=self.metadata))
            reward = self._keep(
                f"reward_risk:{setup}",
                reward_risk_for_stop(
                    stop,
                    resistance_clusters=clusters.clusters,
                    swing_highs=swing_highs,
                    range_highs=breakout_levels,
                    measured_move=None,
                    as_of=self.t,
                    setup=setup,
                    config=self.config,
                    config_metadata=self.metadata,
                ),
            )
            per_setup[setup] = {"invalidation": invalidation, "buffer": buffer, "stop": stop, "reward_risk": reward}
        complete = [setup for setup in LONG_ARCHETYPES if per_setup[setup]["stop"].complete]
        no_stop_cause = None
        if not complete:
            codes = {code for item in per_setup.values() for key in ("invalidation", "buffer", "stop") for code in item[key].reason_codes}
            no_stop_cause = "DATA" if codes & _STOP_DATA_CAUSES else "GEOMETRY"
        return {"per_setup": per_setup, "complete_stop_setups": tuple(complete), "no_stop_cause": no_stop_cause}

    # -- step 1 (structure) after the stop ---------------------------------------------------

    def _structure(self, geometry: dict[str, Any]) -> Decimal | None:
        complete = geometry["complete_stop_setups"]
        if not complete:
            # The structure owner needs a stop. Record why no archetype has one: the
            # data causes (owner ruling: STRUCTURALLY_UNEVALUABLE) or, failing those,
            # the geometry causes (owner ruling: NO_TRADE, no valid structural stop).
            data = geometry["no_stop_cause"] == "DATA"
            for item in geometry["per_setup"].values():
                for key in ("invalidation", "buffer", "stop"):
                    for code in item[key].reason_codes:
                        if not item[key].complete and (code in _STOP_DATA_CAUSES) == data:
                            self._cause("structure", code)
            return None
        structure_kwargs = {
            "version": STRUCTURE_SCORE_CONTRACT_VERSION,
            "weights": dict(self.config.scoring_weights.structure_score),
            "entry_location_full_score_distance_fraction": self.config.price_levels.entry_location_full_score_distance_fraction,
            "entry_location_zero_score_distance_fraction": self.config.price_levels.entry_location_zero_score_distance_fraction,
            "rr_minimum": self.config.price_levels.rr_minimum,
            "rr_preferred_min": self.config.price_levels.rr_preferred_min,
            "rr_preferred_max": self.config.price_levels.rr_preferred_max,
            "config_metadata": self.metadata,
        }
        first_stop = geometry["per_setup"][complete[0]]["stop"].stop_price
        # Pass 1: the structure owner's own support selection (it needs no level strength).
        probe = self._keep(
            "structure_selection",
            calculate_structure_score_from_clusters(self.clusters, entry_price=self.price, stop_price=first_stop, **structure_kwargs),
        )
        support_id = probe.selection.support_cluster_id
        support = next((cluster for cluster in self.clusters.clusters if cluster.cluster_id == support_id), None)
        strength = None
        if support is not None:
            reaction, reaction_cause = self._level_reaction(support)
            volume, volume_cause = self._level_volume(support)
            for cause in (reaction_cause, volume_cause):
                if cause is not None:
                    self._cause("structure", cause)
            levels_config = self.config.price_levels
            strength = self._keep(
                "level_strength",
                calculate_level_strength_from_cluster(
                    support,
                    reaction_magnitude_fraction=reaction,
                    volume_percentile=volume,
                    weights=dict(levels_config.level_strength_weights),
                    timeframe_scores=dict(levels_config.level_strength_timeframe_scores),
                    touch_count_full=levels_config.level_strength_touch_count_full,
                    reaction_full_fraction=levels_config.level_strength_reaction_full_fraction,
                    config_metadata=self.metadata,
                ),
            )
        scores = set()
        self.structure_results = {}
        for setup in complete:
            result = self._keep(
                f"structure:{setup}",
                calculate_structure_score_from_clusters(
                    self.clusters,
                    entry_price=self.price,
                    stop_price=geometry["per_setup"][setup]["stop"].stop_price,
                    level_strength_result=strength,
                    **structure_kwargs,
                ),
            )
            self.structure_results[setup] = result
            scores.add(result.score if result.complete else None)
        if len(scores) != 1:
            raise EntryComposerError("COMPOSER_DEFECT", "STRUCTURE_SCORE_V1_2 differs between archetype stops")
        return scores.pop()

    def _swing_members(self, cluster: Any) -> list[Any]:
        return [m for m in cluster.members if m.feature_id in (WEEKLY_SWING_LEVEL_FEATURE_ID, MONTHLY_SWING_LEVEL_FEATURE_ID)]

    def _level_reaction(self, cluster: Any) -> tuple[Decimal | None, str | None]:
        """LEVEL_REACTION_MAGNITUDE: the minimum net reaction over the cluster's swing members."""

        members = self._swing_members(cluster)
        if not members:
            return None, "LEVEL_REACTION_MAGNITUDE_NO_SWING_MEMBER"
        values = []
        for member in members:
            bars = self.weekly if member.source_timeframe == "1w" else self.monthly if member.source_timeframe == "1mo" else ()
            timestamps = [bar.timestamp for bar in bars]
            if member.source_timestamp not in timestamps:
                return None, "LEVEL_REACTION_MAGNITUDE_INPUT_MISSING"
            index = timestamps.index(member.source_timestamp) + int(member.source_record["right_bars"])
            if index >= len(bars):
                return None, "LEVEL_REACTION_MAGNITUDE_INPUT_MISSING"
            close = bars[index].close
            price = member.price
            values.append((close - price) / price if member.level_type == WEEKLY_SWING_LOW else (price - close) / price)
        return min(values), None

    def _level_volume(self, cluster: Any) -> tuple[Decimal | None, str | None]:
        """LEVEL_VOLUME_PERCENTILE: the minimum pivot-bar Bitstamp volume percentile over swing members."""

        members = self._swing_members(cluster)
        if not members:
            return None, "LEVEL_VOLUME_PERCENTILE_NO_SWING_MEMBER"
        values = []
        for member in members:
            key = (member.feature_id, member.source_timestamp, member.source_timeframe)
            if key not in self.c._volume_percentile_memo:
                self.c._volume_percentile_memo[key] = self._member_volume_percentile(member)
            value, cause = self.c._volume_percentile_memo[key]
            if value is None:
                return None, cause
            values.append(value)
        return min(values), None

    def _member_volume_percentile(self, member: Any) -> tuple[Decimal | None, str | None]:
        start = member.source_timestamp
        end = next_bar_timestamp(start, member.source_timeframe)
        span = end - start
        hours = int(span / _HOUR)
        window_start = end - timedelta(days=UNIFORM_PERCENTILE_WINDOW_DAYS)
        observations: list[tuple[datetime, Decimal | None]] = []
        possible = 0
        day = window_start
        while day < end:
            if day - span >= DATA_WINDOW.start:
                possible += 1
            observations.append((day, self._volume_sum(day, hours)))
            day += _DAY
        observations.append((end, self._volume_sum(end, hours)))
        value, cause = _uniform_percentile(observations, input_id="LEVEL_VOLUME_PERCENTILE")
        if cause == "LEVEL_VOLUME_PERCENTILE_INSUFFICIENT_HISTORY" and possible < UNIFORM_PERCENTILE_MIN_OBSERVATIONS:
            cause = "LEVEL_VOLUME_PERCENTILE_WARM_UP"
        return value, cause

    def _volume_sum(self, boundary: datetime, hours: int) -> Decimal | None:
        """Q_L(d): Bitstamp 1h volume summed over [d - L, d), only when every hour is present and visible."""

        total = Decimal("0")
        for offset in range(hours, 0, -1):
            item = self.c._volume_by_hour.get(boundary - offset * _HOUR)
            if item is None or item[1] > self.t:
                return None
            total += item[0]
        return total

    # -- step 3: triggers and setups --------------------------------------------------------

    def _reclaim_trigger(self) -> bool | None:
        """Setup B entry_trigger_confirmed (owner ruling: fresh at this instant)."""

        reclaims = [level for level in self.breakout_levels if level.level_type == RECLAIM_LEVEL_TYPE and level.detected_at <= self.t]
        if not reclaims:
            return False
        level = max(reclaims, key=lambda item: (item.detected_at, item.confirmation_timestamp, item.level_timestamp, item.price))
        reclaim_config = self.config.entry_triggers.reclaim
        result = self._keep(
            "reclaim_trigger",
            evaluate_reclaim_trigger(
                level,
                (*self.daily, *self.weekly, *self.monthly),
                as_of=self.t,
                confirmation_bars=reclaim_config.confirmation_bars,
                hold_buffer_fraction=reclaim_config.hold_buffer_fraction,
                close_buffer_fraction=reclaim_config.close_buffer_fraction,
                config_metadata=self.metadata,
            ),
        )
        if not result.complete:
            return None
        return bool(result.triggered and result.detected_at == self.t)

    def _higher_low_trigger(self) -> tuple[bool | None, datetime | None]:
        """Setup C confirmation (owner ruling; spec NEW_STRUCTURAL_CONFIRMATION precedent)."""

        lows = [level for level in self.weekly_levels if level.level_type == WEEKLY_SWING_LOW and level.detected_at <= self.t]
        if not lows:
            return False, None
        source = max(lows, key=lambda item: (item.detected_at, item.level_timestamp))
        higher_low_config = self.config.entry_triggers.higher_low
        result = self._keep(
            "higher_low_trigger",
            evaluate_higher_low_trigger(
                source,
                self.daily,
                as_of=self.t,
                pivot_left_bars=higher_low_config.pivot_left_bars,
                pivot_right_bars=higher_low_config.pivot_right_bars,
                higher_low_left_bars=higher_low_config.higher_low_left_bars,
                higher_low_right_bars=higher_low_config.higher_low_right_bars,
                max_pattern_bars=higher_low_config.max_pattern_bars,
                max_breakout_bars=higher_low_config.max_breakout_bars,
                higher_low_buffer_fraction=higher_low_config.higher_low_buffer_fraction,
                pivot_break_buffer_fraction=higher_low_config.pivot_break_buffer_fraction,
                config_metadata=self.metadata,
            ),
        )
        if "HIGHER_LOW_SOURCE_BAR_MISSING" in result.reason_codes:
            return None, None
        if result.triggered and result.detected_at == self.t:
            return True, result.detected_at
        return False, None

    def _capitulation_episode(self) -> tuple[bool | None, datetime | None]:
        """Owner ruling: CAPITULATION flagged at any decision instant in the last 14 days.

        The lag is ``setup_requirements.capitulation_reversal.max_confirmation_lag_days``.
        ``capitulation_detected_at`` is the first instant of that episode: the run of
        consecutive flagged daily rows ending at the latest flag. With no flag in the
        window, an unknown instant there gives None (otherwise False). A run preceded
        by an unknown instant has no determined start, so ``capitulation_detected_at``
        is None and the detector reports its input missing.
        """

        lag_days = int(self.config.setup_requirements.capitulation_reversal["max_confirmation_lag_days"])
        states = {row.decision_at: row.capitulation_flag_state for row in self.c._ledger}
        states[self.t] = self.capitulation_now
        # A daily instant with no ledger row, or whose flag state is None, is
        # unknown: never read as "not flagged" (no invented False).
        window = [self.t - days_back * _DAY for days_back in range(lag_days, -1, -1)]
        flagged = [instant for instant in window if states.get(instant) is True]
        if not flagged:
            return (None if any(states.get(instant) is None for instant in window) else False), None
        start = flagged[-1]
        while states.get(start - _DAY) is True:
            start -= _DAY
        if states.get(start - _DAY) is None:
            # The episode may have begun on the unknown instant or earlier, so its
            # first instant is not determined: Setup C fails closed (trades less).
            return True, None
        return True, start

    def _health_history(self, owner: str, lookback: int) -> tuple[Decimal | None, ...]:
        """Funding/OI health at the prior daily decision instants (owner ruling: native cadence)."""

        values = []
        shared = self.c._inputs.dataset.shared_snapshot
        for days_back in range(lookback, -1, -1):
            instant = self.t - days_back * _DAY
            if (owner, instant) in self.c._health_memo:
                values.append(self.c._health_memo[(owner, instant)])
                continue
            if owner == "funding":
                rows = tuple(row for row in shared.funding_rates if row.available_at <= instant)
                result = self._check("funding_health_history", funding_health(rows, as_of=instant))
                refused = self._history_guard_refused(rows, result, instant, "funding")
                values.append(None if refused else result.health_score)
            else:
                rows = tuple(row for row in shared.open_interest if row.available_at <= instant)
                result = self._check("open_interest_growth_health_history", open_interest_growth_health(rows, as_of=instant, open_interest_unit=OPEN_INTEREST_UNIT))
                refused = self._history_guard_refused(rows, result, instant, "growth")
                values.append(None if refused else result.health_score)
            self.c._health_memo[(owner, instant)] = values[-1]
        return tuple(values)

    def _history_guard_refused(self, rows: tuple[Any, ...], result: Any, instant: datetime, kind: str) -> bool:
        # The same policy V7 section 6A.9 guard, evaluated at that earlier instant.
        if kind == "funding":
            if result.funding_zscore is None:
                return False
            rows_t = tuple(row for row in rows if row.as_record()["available_at"] <= instant and row.as_record()["observation_time"] <= instant)
            averages = _funding_averages_by_time(rows_t, average_window_days=result.average_window_days)
            history = _funding_average_history(averages, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)
            self._check_history(history, max(averages) if averages else None, result)
        else:
            if result.oi_growth_zscore is None:
                return False
            rows_t = tuple(
                row
                for row in rows
                if row.open_interest_unit == result.open_interest_unit
                and row.as_record()["available_at"] <= instant
                and row.as_record()["observation_time"] <= instant
            )
            aggregate = _aggregate_open_interest_by_time(rows_t)
            growth = _open_interest_growth_by_time(aggregate, growth_window_days=result.growth_window_days)
            history = _oi_growth_history(growth, observation_time=result.observation_time, zscore_window_days=result.zscore_window_days)
            self._check_history(history, max(aggregate) if aggregate else None, result)
        return all(value == history[0] for value in history)

    def _setups(self, regime: dict[str, Any], flags: dict[str, Any], geometry: dict[str, Any], structure: Decimal | None, conviction: Any) -> dict[str, Any]:
        requirements = self.config.setup_requirements
        per_setup = geometry["per_setup"]
        trend = self.features["TREND_SCORE"]
        flow = self.features["FLOW_SCORE"]
        positioning = self.features["POSITIONING_SCORE"]
        smoothed = self.regime_smoothed

        setup_a = self._keep(
            f"setup:{BULL_TREND_CONTINUATION_SETUP}",
            detect_bull_trend_continuation(
                BullTrendContinuationInput(
                    regime_score=smoothed,
                    trend_score=trend,
                    flow_score=flow,
                    positioning_score=positioning,
                    structure_score=structure,
                    stress_flagged=self.stress_flagged,
                    severe_crowding_flagged=self.severe_crowding,
                    risk_reward=per_setup[BULL_TREND_CONTINUATION_SETUP]["reward_risk"].reward_risk,
                ),
                requirements=requirements.bull_trend_continuation,
                config_metadata=self.metadata,
            ),
        )
        correction = -self.high_distance if self.high_distance is not None else None
        if correction is None:
            self._cause("setups", "CORRECTION_FROM_LOCAL_HIGH_INPUT_MISSING")
        reset = requirements.bullish_reset
        setup_b = self._keep(
            f"setup:{BULLISH_RESET_SETUP}",
            detect_bullish_reset(
                BullishResetInput(
                    regime_score=smoothed,
                    trend_score=trend,
                    correction_from_local_high_fraction=correction,
                    funding_health_history=self._health_history("funding", int(reset["funding_health_improving_days"])),
                    oi_health_history=self._health_history("growth", int(reset["oi_health_stable_days"])),
                    flow_accel_history=tuple(self.flow_accel_native),
                    structure_score=structure,
                    entry_trigger_confirmed=self._reclaim_trigger(),
                    entry_conviction_score=conviction.score,
                    risk_reward=per_setup[BULLISH_RESET_SETUP]["reward_risk"].reward_risk,
                ),
                requirements=reset,
                config_metadata=self.metadata,
            ),
        )
        capitulation_flagged, capitulation_at = self._capitulation_episode()
        confirmed, confirmed_at = self._higher_low_trigger()
        setup_c = self._keep(
            f"setup:{CAPITULATION_REVERSAL_SETUP}",
            detect_capitulation_reversal(
                CapitulationReversalInput(
                    capitulation_flagged=capitulation_flagged,
                    capitulation_detected_at=capitulation_at,
                    confirmation_triggered=confirmed,
                    confirmation_at=confirmed_at,
                    structure_score=structure,
                    entry_conviction_score=conviction.score,
                    risk_reward=per_setup[CAPITULATION_REVERSAL_SETUP]["reward_risk"].reward_risk,
                ),
                requirements=requirements.capitulation_reversal,
                config_metadata=self.metadata,
            ),
        )
        # Setup D: called for archetype coverage with its inert short-side inputs
        # (spec DISTRIBUTION_STATE / SHORT_TRIGGER); short geometry is not composed.
        self._keep(
            f"setup:{BEARISH_DISTRIBUTION_SETUP}",
            detect_bearish_distribution(
                BearishDistributionInput(
                    regime_score=smoothed,
                    trend_score=trend,
                    flow_score=flow,
                    positioning_score=positioning,
                    structure_score=structure,
                    entry_conviction_score=conviction.score,
                    risk_reward=None,
                    distribution_flagged=None,
                    short_trigger_confirmed=None,
                    stress_flagged=self.stress_flagged,
                ),
                requirements=requirements.bearish_distribution,
                config_metadata=self.metadata,
            ),
        )
        return {BULL_TREND_CONTINUATION_SETUP: setup_a, BULLISH_RESET_SETUP: setup_b, CAPITULATION_REVERSAL_SETUP: setup_c}

    # -- step 4/5: gates and the intent ----------------------------------------------------

    def _gate(self, setup: str, detection: Any, geometry: dict[str, Any], flags: dict[str, Any], components: dict[str, Any], regime: dict[str, Any], conviction: Any, action: Any) -> EntryDecision:
        item = geometry["per_setup"][setup]
        stop = item["stop"]
        reward = item["reward_risk"]
        invalidation = item["invalidation"]
        zone = next(cluster for cluster in self.clusters.clusters if cluster.cluster_id == invalidation.selected_cluster_id)
        no_chase_config = self.config.entry_triggers.no_chase
        atr_mode = no_chase_config.distance_mode == "atr"
        no_chase = self._keep(
            "no_chase",
            apply_no_chase_filter(
                zone,
                current_price=self.price,
                current_price_available_at=self.t,
                as_of=self.t,
                direction="long",
                distance_mode=no_chase_config.distance_mode,
                max_distance_atr=no_chase_config.max_distance_atr,
                max_distance_fraction=no_chase_config.max_distance_fraction,
                atr=self.atr if atr_mode else None,
                atr_available_at=self.t if atr_mode and self.atr is not None else None,
                config_metadata=self.metadata,
            ),
        )
        veto = self._keep(
            "hard_veto",
            evaluate_hard_veto(
                HardVetoInput(
                    data_quality_fail=bool(self.quality_failures),
                    valid_structural_stop=True if stop.complete else None,
                    reward_risk_passes=reward.passes if reward.complete else None,
                    stress_flagged=self.stress_flagged,
                    severe_crowding_flagged=self.severe_crowding,
                    no_chase_blocked=no_chase.blocked if no_chase.complete else None,
                    setup=setup,
                    source_reason_codes={
                        "data_quality_fail": tuple(code for failure in self.quality_failures for code in failure.reason_codes),
                        "valid_structural_stop": tuple(stop.reason_codes),
                        "reward_risk_passes": tuple(reward.reason_codes),
                        "stress_flagged": tuple(self.stress_result.reason_codes),
                        "severe_crowding_flagged": tuple(self.crowding_result.reason_codes),
                        "no_chase_blocked": tuple(no_chase.reason_codes),
                        "setup": tuple(detection.reason_codes),
                    },
                ),
                strategy_config=self.config,
            ),
        )
        gate = apply_data_quality_gate("ENTER", self.quality_failures)
        reasons = []
        if action.action not in TRADE_BAND_ACTIONS:
            reasons.append(REASON_ENTRY_CONVICTION_BELOW_TRADE_BAND)
        if veto.blocked:
            reasons.append(REASON_HARD_VETO)
        if gate.action != "ENTER":
            reasons.append(REASON_DATA_QUALITY_GATE)
        self.gate_record = {"action": gate.action, "data_quality_fail": gate.data_quality_fail}
        if reasons:
            return self._finish(OUTCOME_NO_TRADE, tuple(reasons), components, regime, flags, conviction, action, setup=setup)
        if stop.direction != "long" or stop.entry_price != self.price or dict(stop.config_metadata) != self.metadata:
            raise EntryComposerError("COMPOSER_DEFECT", "the initial stop does not match the decision price and champion identity")
        intent = BacktestIntent(
            action=ARM_ENTRY_ACTION,
            direction="long",
            entry_zone_lower=self.price,
            entry_zone_upper=self.price,
            initial_stop=stop,
            entry_conviction=conviction.score,
            source_id=f"rbt004:{self.c._venue}:entry:{self.t.isoformat()}",
        )
        return self._finish(OUTCOME_ARM_ENTRY, (setup,), components, regime, flags, conviction, action, setup=setup, intent=intent)

    # -- the ledger row ----------------------------------------------------------------------

    def _component_causes(self, components: dict[str, Any]) -> tuple[UnevaluableComponent, ...]:
        incomplete = []
        owner_codes = {
            "trend": (),
            "flow": ("flow_score", "etf_flow_5d", "etf_flow_20d", "etf_flow_acceleration"),
            "positioning": ("funding_health", "open_interest_growth_health", "futures_basis_health", "open_interest_intensity", "positioning_score"),
            "volatility": ("rv_7", "rv_20", "rv_60", "volatility_percentile", "volatility_compression", "orderliness", "volatility_score"),
            "structure": ("clusters", "level_strength", "structure_selection"),
        }
        for name, value in components.items():
            if value is not None:
                continue
            causes = list(self.composer_causes.get(name, ()))
            for label in owner_codes[name]:
                result = self.results.get(label)
                if result is not None and not result.complete:
                    causes.extend(code for code in result.reason_codes if accounted_cause(code, result.feature_id) is not None)
            if not causes and name == "structure":
                for label, result in self.results.items():
                    if label.startswith("structure:") and not result.complete:
                        causes.extend(result.reason_codes)
            incomplete.append(UnevaluableComponent(name, _unique(causes)))
        return tuple(incomplete)

    def _unaccounted(self) -> tuple[str, ...]:
        missing = []
        for label, result in (*self.results.items(), *self.auxiliary):
            codes = tuple(result.reason_codes)
            feature_id = result.feature_id
            if not result.complete:
                accounted = [code for code in codes if accounted_cause(code, feature_id) is not None]
                if not accounted:
                    missing.append(f"{label}:{'|'.join(codes) or 'INCOMPLETE_WITHOUT_REASON'}")
            for code in codes:
                if any(marker in code for marker in _MISSING_MARKERS) and accounted_cause(code, feature_id) is None:
                    missing.append(f"{label}:{code}")
        for component, codes in self.composer_causes.items():
            for code in codes:
                if accounted_cause(code) is None:
                    missing.append(f"{component}:{code}")
        return _unique(missing)

    def _finish(
        self,
        outcome: str,
        reasons: tuple[str, ...],
        components: dict[str, Any],
        regime: dict[str, Any],
        flags: dict[str, Any],
        conviction: Any,
        action: Any,
        *,
        setup: str | None = None,
        intent: BacktestIntent | None = None,
    ) -> EntryDecision:
        unevaluable = self._component_causes(components) if outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE else ()
        owner_codes = {
            label: {"feature_id": result.feature_id, "complete": result.complete, "reason_codes": list(result.reason_codes)}
            for label, result in sorted(self.results.items())
        }
        intent_record = None
        if intent is not None:
            stop = intent.initial_stop
            intent_record = {
                "action": intent.action,
                "direction": intent.direction,
                "entry_zone_lower": intent.entry_zone_lower,
                "entry_zone_upper": intent.entry_zone_upper,
                "entry_conviction": intent.entry_conviction,
                "source_id": intent.source_id,
                "initial_stop": stop.as_record() if stop is not None else None,
            }
        row = EntryDecisionRow(
            decision_at=self.t,
            venue=self.c._venue,
            outcome=outcome,
            reasons=reasons,
            position_open=self.position_open,
            setup=setup,
            detected_setups=self.detected,
            entry_conviction=conviction.score,
            entry_action=action.action,
            regime=regime,
            components=components,
            flags=flags,
            unevaluable=unevaluable,
            guard_refusals=tuple(self.guard_refusals),
            owner_reason_codes=owner_codes,
            unaccounted=self._unaccounted(),
            features=dict(self.features),
            data_quality={**self.data_quality, "gate": self.gate_record},
            intent=intent_record,
            capitulation_flag_state=self.capitulation_now,
        )
        return EntryDecision(row, intent)


# --- spec uniform rules (CHAMPION_COMPLETION_SPEC_V1 uniform_rules application contracts) --


def _uniform_zscore(series: Sequence[Decimal | None], *, input_id: str) -> tuple[Decimal | None, str | None]:
    """UNIFORM_ZSCORE_V1, in the application contract's order.

    1. Select H: the last 20 defined native observations strictly before the
       current one, skipping None and never filling.
    2. Return None if x is None or len(H) < 20.
    3. Refuse an exactly constant H on the original values, before any float
       conversion, whether or not x equals it.
    4. Otherwise call ``rolling_zscore((*H, x), window=len(H), min_periods=20,
       sample=False)`` and use its last result.
    """

    if not series or series[-1] is None:
        return None, f"{input_id}_INPUT_MISSING"
    current = series[-1]
    history = tuple(value for value in series[:-1] if value is not None)[-UNIFORM_ZSCORE_WINDOW_OBSERVATIONS:]
    if len(history) < UNIFORM_ZSCORE_MIN_OBSERVATIONS:
        return None, f"{input_id}_INSUFFICIENT_HISTORY"
    if all(value == history[0] for value in history):
        return None, f"{input_id}_ZERO_VARIANCE"
    value = rolling_zscore((*history, current), window=len(history), min_periods=UNIFORM_ZSCORE_MIN_OBSERVATIONS, sample=False)[-1]
    if value is None:
        return None, f"{input_id}_ZERO_VARIANCE"
    return value, None


def _uniform_percentile(observations: Sequence[tuple[datetime, Decimal | None]], *, input_id: str) -> tuple[Decimal | None, str | None]:
    """UNIFORM_PERCENTILE_V1: select history by time in [D - 730 days, D), then call the helper."""

    when, current = observations[-1]
    if current is None:
        return None, f"{input_id}_INPUT_MISSING"
    start = when - timedelta(days=UNIFORM_PERCENTILE_WINDOW_DAYS)
    history = tuple(value for moment, value in observations[:-1] if start <= moment < when and value is not None)
    if len(history) < UNIFORM_PERCENTILE_MIN_OBSERVATIONS:
        return None, f"{input_id}_INSUFFICIENT_HISTORY"
    value = rolling_percentile((*history, current), window=len(history), min_periods=UNIFORM_PERCENTILE_MIN_OBSERVATIONS)[-1]
    return value, (None if value is not None else f"{input_id}_INPUT_MISSING")


# --- serialisation -------------------------------------------------------------------------


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return tuple(seen)


def _accounting_record(code: str) -> dict[str, Any]:
    cause = accounted_cause(code)
    return {"accounted": cause.as_record() if cause is not None else None}


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EntryComposerError("INPUT_REFUSED", f"{name} must be a timezone-aware datetime")
    return value.astimezone(UTC)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return repr(value)
    raise EntryComposerError("NOT_SERIALISABLE", f"{type(value).__name__} has no ledger form")


def ledger_json(composer: EntryComposer) -> str:
    """A readable rendering of the canonical ledger bytes."""

    return json.dumps(json.loads(composer.ledger_bytes()), indent=1, sort_keys=True)
