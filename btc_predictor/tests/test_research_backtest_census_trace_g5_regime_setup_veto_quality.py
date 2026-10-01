"""Deterministic synthetic fixtures for RBT-002 R1 runtime cross-check (group 5).

Roots driven: core regime score / smoothing / classification (Rulebook 10),
setup detectors A-D (Rulebook 11), hard veto (Rulebook 14) and the BTC-031
data-quality owners plus the DATA_QUALITY_FAIL gate (Rulebook 24).

Every thunk builds its own inputs from ``btc_predictor`` owner types and the
stdlib only (``Decimal``, ``datetime`` with ``UTC``), with fixed dates inside
2021-01-01..2024-12-31, and returns the root's result. No randomness, no wall
clock, no network, no database. The only file read is the versioned champion
strategy config, through ``load_strategy_config()``.

The first thunk of every root reaches the owner's main path (complete /
accepted / detected / clean). Later thunks exercise the refusal, incomplete or
missing-input branches.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.data.derivatives import (
    FundingRate,
    FuturesBasis,
    Liquidation,
    OpenInterest,
    PerpVolume,
)
from btc_predictor.data.ohlcv import OhlcvBar
from btc_predictor.data.quality import (
    DerivativesQualityConfig,
    DerivativesQualityIssue,
    DerivativesQualityReport,
    OhlcvQualityConfig,
    OhlcvQualityIssue,
    OhlcvQualityReport,
    validate_derivatives_quality,
    validate_ohlcv_quality,
)
from btc_predictor.features.regime import (
    RegimeScoreInput,
    RegimeSmoothingInput,
    calculate_regime_classification,
    calculate_regime_score,
    calculate_regime_smoothing,
)
from btc_predictor.features.setup import (
    BULL_TREND_CONTINUATION_SETUP,
    BearishDistributionInput,
    BullishResetInput,
    BullTrendContinuationInput,
    CapitulationReversalInput,
    detect_bearish_distribution,
    detect_bull_trend_continuation,
    detect_bullish_reset,
    detect_capitulation_reversal,
)
from btc_predictor.signals.data_quality import (
    DataQualityFailure,
    apply_data_quality_gate,
    failures_from_quality_reports,
)
from btc_predictor.signals.hard_veto import HardVetoInput, evaluate_hard_veto


D = Decimal


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# --- core regime (Rulebook 10) --------------------------------------------------------


def regime_score_core_market_only_complete():
    """Champion path: P1 macro/onchain/liquidity absent -> CORE_MARKET_ONLY, complete."""

    config = load_strategy_config()
    return calculate_regime_score(
        RegimeScoreInput(
            trend_score=D("74"),
            flow_score=D("62"),
            volatility_score=D("58"),
            positioning_score=D("66"),
        ),
        core_weights=config.scoring_weights.core_regime,
        full_weights=config.scoring_weights.full_regime,
        config_metadata=config.run_metadata(),
    )


def regime_score_core_input_missing():
    """A core component is missing: score is None, complete is False."""

    config = load_strategy_config()
    return calculate_regime_score(
        RegimeScoreInput(
            trend_score=D("74"),
            flow_score=None,
            volatility_score=D("58"),
            positioning_score=D("66"),
        ),
        core_weights=config.scoring_weights.core_regime,
        full_weights=config.scoring_weights.full_regime,
        config_metadata=config.run_metadata(),
    )


def regime_score_full_model_complete():
    """All seven components present -> FULL_MACRO_ONCHAIN_LIQUIDITY branch."""

    config = load_strategy_config()
    return calculate_regime_score(
        RegimeScoreInput(
            trend_score=D("80"),
            flow_score=D("70"),
            volatility_score=D("60"),
            positioning_score=D("65"),
            macro_score=D("50"),
            onchain_score=D("55"),
            liquidity_score=D("45"),
        ),
        core_weights=config.scoring_weights.core_regime,
        full_weights=config.scoring_weights.full_regime,
        config_metadata=config.run_metadata(),
    )


def regime_smoothing_complete():
    config = load_strategy_config()
    return calculate_regime_smoothing(
        RegimeSmoothingInput(previous_smoothed_score=D("60"), new_regime_score=D("67.4")),
        previous_weight=config.regime_smoothing.previous_weight,
        new_weight=config.regime_smoothing.new_weight,
        config_metadata=config.run_metadata(),
    )


def regime_smoothing_new_score_missing():
    """Refusal: no new regime score -> incomplete, REGIME_SMOOTHING_NEW_SCORE_MISSING."""

    config = load_strategy_config()
    return calculate_regime_smoothing(
        RegimeSmoothingInput(previous_smoothed_score=D("60"), new_regime_score=None),
        previous_weight=config.regime_smoothing.previous_weight,
        new_weight=config.regime_smoothing.new_weight,
        config_metadata=config.run_metadata(),
    )


def regime_smoothing_bootstrap_without_previous():
    """Bootstrap branch: no previous smoothed score -> score = new score."""

    config = load_strategy_config()
    return calculate_regime_smoothing(
        RegimeSmoothingInput(previous_smoothed_score=None, new_regime_score=D("72.25")),
        previous_weight=config.regime_smoothing.previous_weight,
        new_weight=config.regime_smoothing.new_weight,
        config_metadata=config.run_metadata(),
    )


def regime_classification_complete():
    config = load_strategy_config()
    return calculate_regime_classification(
        D("62.38"),
        thresholds=config.regime_thresholds,
        config_metadata=config.run_metadata(),
    )


def regime_classification_score_missing():
    config = load_strategy_config()
    return calculate_regime_classification(
        None,
        thresholds=config.regime_thresholds,
        config_metadata=config.run_metadata(),
    )


# --- setups (Rulebook 11) -------------------------------------------------------------


def bull_trend_continuation_detected():
    config = load_strategy_config()
    return detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=D("72.25"),
            trend_score=D("74"),
            flow_score=D("62"),
            positioning_score=D("70"),
            structure_score=D("80"),
            stress_flagged=False,
            severe_crowding_flagged=False,
            risk_reward=D("2.4"),
        ),
        requirements=config.setup_requirements.bull_trend_continuation,
        config_metadata=config.run_metadata(),
    )


def bull_trend_continuation_input_missing():
    config = load_strategy_config()
    return detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=D("72.25"),
            trend_score=D("74"),
            flow_score=None,
            positioning_score=D("70"),
            structure_score=D("80"),
            stress_flagged=None,
            severe_crowding_flagged=False,
            risk_reward=None,
        ),
        requirements=config.setup_requirements.bull_trend_continuation,
        config_metadata=config.run_metadata(),
    )


def bull_trend_continuation_rejected():
    """Complete inputs failing every hard filter."""

    config = load_strategy_config()
    return detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=D("60"),
            trend_score=D("65"),
            flow_score=D("50"),
            positioning_score=D("55"),
            structure_score=D("65"),
            stress_flagged=True,
            severe_crowding_flagged=True,
            risk_reward=D("1.5"),
        ),
        requirements=config.setup_requirements.bull_trend_continuation,
        config_metadata=config.run_metadata(),
    )


def _rising(start: str, step: str, count: int) -> tuple[Decimal, ...]:
    return tuple(D(start) + D(step) * index for index in range(count))


def bullish_reset_detected():
    config = load_strategy_config()
    return detect_bullish_reset(
        BullishResetInput(
            regime_score=D("65"),
            trend_score=D("62"),
            correction_from_local_high_fraction=D("0.12"),
            funding_health_history=_rising("40", "1.5", 8),
            oi_health_history=(D("60"), D("59"), D("58"), D("57"), D("56"), D("55"), D("54"), D("60")),
            flow_accel_history=_rising("-3", "1.2", 6),
            structure_score=D("74"),
            entry_trigger_confirmed=True,
            entry_conviction_score=D("82"),
            risk_reward=D("2.3"),
        ),
        requirements=config.setup_requirements.bullish_reset,
        config_metadata=config.run_metadata(),
    )


def bullish_reset_history_insufficient():
    """Missing / too-short histories -> incomplete (INPUT_MISSING, *_HISTORY_INSUFFICIENT)."""

    config = load_strategy_config()
    return detect_bullish_reset(
        BullishResetInput(
            regime_score=D("65"),
            trend_score=D("62"),
            correction_from_local_high_fraction=D("0.12"),
            funding_health_history=(D("40"), D("41"), D("42")),
            oi_health_history=None,
            flow_accel_history=(D("-3"), None, D("-1"), D("0"), D("1"), None),
            structure_score=D("74"),
            entry_trigger_confirmed=None,
            entry_conviction_score=D("82"),
            risk_reward=D("2.3"),
        ),
        requirements=config.setup_requirements.bullish_reset,
        config_metadata=config.run_metadata(),
    )


def bullish_reset_rejected():
    """Complete inputs failing the filters (correction too deep, deteriorating histories)."""

    config = load_strategy_config()
    return detect_bullish_reset(
        BullishResetInput(
            regime_score=D("50"),
            trend_score=D("50"),
            correction_from_local_high_fraction=D("0.31"),
            funding_health_history=tuple(D("45") for _ in range(8)),
            oi_health_history=(D("60"), D("59"), D("58"), D("57"), D("56"), D("55"), D("54"), D("50")),
            flow_accel_history=(D("3"), D("2"), D("1"), D("0"), D("-1"), D("-2")),
            structure_score=D("60"),
            entry_trigger_confirmed=False,
            entry_conviction_score=D("70"),
            risk_reward=D("1.2"),
        ),
        requirements=config.setup_requirements.bullish_reset,
        config_metadata=config.run_metadata(),
    )


def capitulation_reversal_detected():
    config = load_strategy_config()
    return detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=True,
            capitulation_detected_at=_utc(2022, 6, 18),
            confirmation_triggered=True,
            confirmation_at=_utc(2022, 6, 22),
            structure_score=D("72"),
            entry_conviction_score=D("84"),
            risk_reward=D("2.5"),
        ),
        requirements=config.setup_requirements.capitulation_reversal,
        config_metadata=config.run_metadata(),
    )


def capitulation_reversal_input_missing_confirmation_first():
    """Incomplete (structure missing) and confirmation precedes the capitulation event."""

    config = load_strategy_config()
    return detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=True,
            capitulation_detected_at=_utc(2022, 6, 18),
            confirmation_triggered=True,
            confirmation_at=_utc(2022, 6, 15),
            structure_score=None,
            entry_conviction_score=D("84"),
            risk_reward=D("2.5"),
        ),
        requirements=config.setup_requirements.capitulation_reversal,
        config_metadata=config.run_metadata(),
    )


def capitulation_reversal_rejected():
    """Complete inputs: no capitulation, no confirmation, stale lag, weak scores."""

    config = load_strategy_config()
    return detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=False,
            capitulation_detected_at=_utc(2022, 6, 18),
            confirmation_triggered=False,
            confirmation_at=_utc(2022, 7, 10),
            structure_score=D("50"),
            entry_conviction_score=D("70"),
            risk_reward=D("1.5"),
        ),
        requirements=config.setup_requirements.capitulation_reversal,
        config_metadata=config.run_metadata(),
    )


def bearish_distribution_detected():
    """Detector main path (inert for trading while backtest.allow_short_trades = false)."""

    config = load_strategy_config()
    return detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=D("35"),
            trend_score=D("30"),
            flow_score=D("25"),
            positioning_score=D("35"),
            structure_score=D("45"),
            entry_conviction_score=D("90"),
            risk_reward=D("3"),
            distribution_flagged=True,
            short_trigger_confirmed=True,
            stress_flagged=False,
        ),
        requirements=config.setup_requirements.bearish_distribution,
        config_metadata=config.run_metadata(),
    )


def bearish_distribution_input_missing():
    config = load_strategy_config()
    return detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=D("35"),
            trend_score=None,
            flow_score=D("25"),
            positioning_score=D("35"),
            structure_score=D("45"),
            entry_conviction_score=D("90"),
            risk_reward=D("3"),
            distribution_flagged=None,
            short_trigger_confirmed=True,
            stress_flagged=False,
        ),
        requirements=config.setup_requirements.bearish_distribution,
        config_metadata=config.run_metadata(),
    )


def bearish_distribution_rejected():
    config = load_strategy_config()
    return detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=D("55"),
            trend_score=D("50"),
            flow_score=D("50"),
            positioning_score=D("50"),
            structure_score=D("60"),
            entry_conviction_score=D("80"),
            risk_reward=D("2"),
            distribution_flagged=False,
            short_trigger_confirmed=False,
            stress_flagged=True,
        ),
        requirements=config.setup_requirements.bearish_distribution,
        config_metadata=config.run_metadata(),
    )


# --- hard veto (Rulebook 14) ----------------------------------------------------------


def hard_veto_clear():
    config = load_strategy_config()
    return evaluate_hard_veto(
        HardVetoInput(
            data_quality_fail=False,
            valid_structural_stop=True,
            reward_risk_passes=True,
            stress_flagged=False,
            severe_crowding_flagged=False,
            no_chase_blocked=False,
            setup=BULL_TREND_CONTINUATION_SETUP,
            source_reason_codes={
                "setup": ("SETUP_BULL_TREND_CONTINUATION_VALID",),
                "reward_risk_passes": ("REWARD_RISK_PASS",),
            },
        ),
        strategy_config=config,
    )


def hard_veto_inputs_missing():
    """Fail-closed: every resolved state unavailable."""

    config = load_strategy_config()
    return evaluate_hard_veto(
        HardVetoInput(
            data_quality_fail=None,
            valid_structural_stop=None,
            reward_risk_passes=None,
            stress_flagged=None,
            severe_crowding_flagged=None,
            no_chase_blocked=None,
            setup=None,
        ),
        strategy_config=config,
    )


def hard_veto_all_vetoes():
    """Complete inputs triggering every veto (STRESS is non-blocking in the champion config)."""

    config = load_strategy_config()
    return evaluate_hard_veto(
        HardVetoInput(
            data_quality_fail=True,
            valid_structural_stop=False,
            reward_risk_passes=False,
            stress_flagged=True,
            severe_crowding_flagged=True,
            no_chase_blocked=True,
            setup="RANGE_FADE",
            source_reason_codes={"data_quality_fail": ("DATA_QUALITY_FAIL",)},
        ),
        strategy_config=config,
    )


# --- data quality (Rulebook 24 DATA_QUALITY_FAIL) -------------------------------------


def _daily_bar(timestamp: datetime, open_: Decimal, close: Decimal, volume: Decimal, *,
               high: Decimal | None = None, low: Decimal | None = None,
               timeframe: str = "1d") -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=open_,
        high=high if high is not None else max(open_, close) + D("200"),
        low=low if low is not None else min(open_, close) - D("200"),
        close=close,
        volume=volume,
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1, minutes=5),
    )


def _clean_daily_bars(first: datetime, count: int) -> list[OhlcvBar]:
    bars = []
    previous_close = D("22000")
    for index in range(count):
        close = D("22000") + D("150") * index + (D("80") if index % 3 == 0 else D("-40"))
        bars.append(
            _daily_bar(first + timedelta(days=index), previous_close, close, D("1000") + D("10") * index)
        )
        previous_close = close
    return bars


def ohlcv_quality_clean_daily():
    first = _utc(2023, 3, 1)
    bars = _clean_daily_bars(first, 20)
    return validate_ohlcv_quality(
        bars,
        start=first,
        end=first + timedelta(days=19),
        timeframe="1d",
        as_of=first + timedelta(days=20),
        config=OhlcvQualityConfig(),
    )


def ohlcv_quality_defective_daily():
    """Duplicate, impossible, missing, stale and extreme bars plus a filtered 1h bar."""

    first = _utc(2023, 3, 1)
    bars = _clean_daily_bars(first, 10)
    del bars[4]  # MISSING_PERIOD on 2023-03-05
    bars.append(bars[0])  # DUPLICATE_BAR
    bars[6] = _daily_bar(bars[6].timestamp, D("23000"), D("23100"), D("1000"),
                         high=D("22000"), low=D("23500"))  # IMPOSSIBLE_OHLC
    bars[8] = _daily_bar(bars[8].timestamp, D("23300"), D("42000"), D("9000"))  # EXTREME
    bars.append(_daily_bar(_utc(2023, 3, 2, 5), D("22100"), D("22150"), D("5"), timeframe="1h"))
    return validate_ohlcv_quality(
        bars,
        start=first,
        end=first + timedelta(days=9),
        timeframe="1d",
        as_of=first + timedelta(days=16),  # STALE_DATA
        config=OhlcvQualityConfig(
            max_staleness=timedelta(days=2),
            max_close_change_fraction=D("0.30"),
            max_bar_range_fraction=D("0.20"),
            max_volume=D("5000"),
        ),
    )


def ohlcv_quality_monthly_gap():
    """Calendar timeframe (1mo, _add_month) with a missing month, default staleness."""

    bars = [
        _daily_bar(_utc(2022, 1, 1), D("47000"), D("38500"), D("90000"), timeframe="1mo"),
        _daily_bar(_utc(2022, 2, 1), D("38500"), D("43200"), D("85000"), timeframe="1mo"),
        _daily_bar(_utc(2022, 4, 1), D("45500"), D("37700"), D("80000"), timeframe="1mo"),
    ]
    return validate_ohlcv_quality(
        bars,
        start=_utc(2022, 1, 1),
        end=_utc(2022, 4, 1),
        timeframe="1mo",
        as_of=_utc(2022, 5, 15),
    )


def _funding(observation: datetime, exchange: str = "binance") -> FundingRate:
    return FundingRate(
        observation_time=observation,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=D("0.0001"),
        funding_interval_hours=D("8"),
        provider=exchange,
        source="provider-api",
        available_at=observation + timedelta(minutes=1),
        ingested_at=observation + timedelta(minutes=2),
    )


def _open_interest(observation: datetime, amount: str = "85000", unit: str = "contracts",
                   exchange: str = "binance") -> OpenInterest:
    return OpenInterest(
        observation_time=observation,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        open_interest=D(amount),
        open_interest_unit=unit,
        provider=exchange,
        source="provider-api",
        available_at=observation + timedelta(minutes=1),
        ingested_at=observation + timedelta(minutes=2),
    )


def _perp_volume(observation: datetime, exchange: str = "binance") -> PerpVolume:
    return PerpVolume(
        observation_time=observation,
        exchange=exchange,
        symbol="BTCUSDT",
        timeframe="1h",
        volume=D("1200"),
        volume_unit="BTC",
        notional_usd=D("26000000"),
        provider=exchange,
        source="provider-api",
        available_at=observation + timedelta(minutes=1),
        ingested_at=observation + timedelta(minutes=2),
    )


def _basis(observation: datetime) -> FuturesBasis:
    return FuturesBasis(
        observation_time=observation,
        exchange="binance",
        symbol="BTCUSD",
        instrument="BTCUSD-230331",
        expiry=_utc(2023, 3, 31, 8),
        basis_rate=D("0.004"),
        annualized_basis_rate=D("0.07"),
        provider="binance",
        source="provider-api",
        available_at=observation + timedelta(minutes=1),
        ingested_at=observation + timedelta(minutes=2),
    )


def _liquidation(observation: datetime) -> Liquidation:
    return Liquidation(
        observation_time=observation,
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="1h",
        side="long",
        quantity=D("35"),
        quantity_unit="BTC",
        notional_usd=D("760000"),
        provider="binance",
        source="provider-api",
        available_at=observation + timedelta(minutes=1),
        ingested_at=observation + timedelta(minutes=2),
    )


def _clean_derivatives_rows() -> list:
    hours = [_utc(2023, 3, 10, hour) for hour in range(8, 12)]
    return [
        _funding(_utc(2023, 3, 9, 16)),
        _funding(_utc(2023, 3, 10, 0)),
        _funding(_utc(2023, 3, 10, 8)),
        *(_open_interest(hour) for hour in hours),
        *(_perp_volume(hour) for hour in hours),
        *(_basis(hour) for hour in hours),
        *(_liquidation(hour) for hour in hours),
    ]


_CLEAN_DERIVATIVES_AS_OF = _utc(2023, 3, 10, 12)


def derivatives_quality_clean():
    return validate_derivatives_quality(
        _clean_derivatives_rows(),
        as_of=_CLEAN_DERIVATIVES_AS_OF,
        config=DerivativesQualityConfig(expected_exchanges=("binance",)),
    )


def derivatives_quality_defective():
    """Stale/absent funding, negative OI, provider gap, unit change, missing snapshots."""

    as_of = _utc(2023, 3, 10, 12)
    rows = [
        _funding(_utc(2023, 3, 9, 0)),
        _funding(_utc(2023, 3, 9, 16)),  # 16h gap > 8h + 1h -> PROVIDER_DISCONTINUITY
        _open_interest(_utc(2023, 3, 10, 4)),
        _open_interest(_utc(2023, 3, 10, 9), amount="-5"),  # gap 5h, NEGATIVE_OPEN_INTEREST
        _open_interest(_utc(2023, 3, 10, 10), amount="1900", unit="BTC"),  # UNIT_CHANGE
        _perp_volume(_utc(2023, 3, 10, 6)),  # stale perp-volume snapshot
    ]
    return validate_derivatives_quality(
        rows,
        as_of=as_of,
        config=DerivativesQualityConfig(expected_exchanges=("binance", "okx")),
    )


# --- data-quality failures and gate ---------------------------------------------------


def quality_failures_from_clean_reports():
    """Composer path: reports produced by the BTC-031 owners over clean data -> no failures."""

    first = _utc(2023, 3, 1)
    reports = {
        "btc_ohlcv_1d": validate_ohlcv_quality(
            _clean_daily_bars(first, 20),
            start=first,
            end=first + timedelta(days=19),
            timeframe="1d",
            as_of=first + timedelta(days=20),
            config=OhlcvQualityConfig(),
        ),
        "btc_derivatives": validate_derivatives_quality(
            _clean_derivatives_rows(),
            as_of=_CLEAN_DERIVATIVES_AS_OF,
            config=DerivativesQualityConfig(expected_exchanges=("binance",)),
        ),
    }
    return failures_from_quality_reports(reports)


def quality_failures_from_failed_reports():
    reports = {
        "btc_ohlcv_1d": OhlcvQualityReport(
            issues=(
                OhlcvQualityIssue(
                    reason_code="MISSING_PERIOD",
                    severity="error",
                    message="Expected OHLCV period is missing.",
                    timestamp=_utc(2023, 3, 5),
                ),
                OhlcvQualityIssue(
                    reason_code="STALE_DATA",
                    severity="error",
                    message="Latest OHLCV bar is older than the allowed staleness threshold.",
                    timestamp=_utc(2023, 3, 10),
                ),
                OhlcvQualityIssue(
                    reason_code="MISSING_PERIOD",
                    severity="error",
                    message="Expected OHLCV period is missing.",
                    timestamp=_utc(2023, 3, 6),
                ),
            ),
        ),
        "btc_derivatives": DerivativesQualityReport(
            issues=(
                DerivativesQualityIssue(
                    reason_code="STALE_FUNDING",
                    severity="error",
                    message="No funding observation is available for the expected exchange.",
                    details={"exchange": "okx"},
                ),
            ),
        ),
        "btc_ohlcv_1w": OhlcvQualityReport(issues=()),
    }
    return failures_from_quality_reports(reports)


def data_quality_gate_enter_clean():
    return apply_data_quality_gate("ENTER", ())


def data_quality_gate_enter_blocked():
    failures = (
        DataQualityFailure(source_component="btc_ohlcv_1d", reason_codes=("MISSING_PERIOD", "STALE_DATA")),
        DataQualityFailure(source_component="btc_derivatives", reason_codes=("STALE_FUNDING",)),
    )
    return apply_data_quality_gate("ENTER", failures)


def data_quality_gate_add_blocked_with_position():
    failures = (DataQualityFailure(source_component="btc_derivatives", reason_codes=("UNIT_CHANGE",)),)
    return apply_data_quality_gate(
        "ADD",
        failures,
        existing_position_state={"state": "OPEN", "entry_time": "2023-03-01T00:00:00+00:00"},
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.features.regime.calculate_regime_score": (
        regime_score_core_market_only_complete,
        regime_score_core_input_missing,
        regime_score_full_model_complete,
    ),
    "btc_predictor.features.regime.calculate_regime_smoothing": (
        regime_smoothing_complete,
        regime_smoothing_new_score_missing,
        regime_smoothing_bootstrap_without_previous,
    ),
    "btc_predictor.features.regime.calculate_regime_classification": (
        regime_classification_complete,
        regime_classification_score_missing,
    ),
    "btc_predictor.features.setup.detect_bull_trend_continuation": (
        bull_trend_continuation_detected,
        bull_trend_continuation_input_missing,
        bull_trend_continuation_rejected,
    ),
    "btc_predictor.features.setup.detect_bullish_reset": (
        bullish_reset_detected,
        bullish_reset_history_insufficient,
        bullish_reset_rejected,
    ),
    "btc_predictor.features.setup.detect_capitulation_reversal": (
        capitulation_reversal_detected,
        capitulation_reversal_input_missing_confirmation_first,
        capitulation_reversal_rejected,
    ),
    "btc_predictor.features.setup.detect_bearish_distribution": (
        bearish_distribution_detected,
        bearish_distribution_input_missing,
        bearish_distribution_rejected,
    ),
    "btc_predictor.signals.hard_veto.evaluate_hard_veto": (
        hard_veto_clear,
        hard_veto_inputs_missing,
        hard_veto_all_vetoes,
    ),
    "btc_predictor.data.quality.validate_ohlcv_quality": (
        ohlcv_quality_clean_daily,
        ohlcv_quality_defective_daily,
        ohlcv_quality_monthly_gap,
    ),
    "btc_predictor.data.quality.validate_derivatives_quality": (
        derivatives_quality_clean,
        derivatives_quality_defective,
    ),
    "btc_predictor.signals.data_quality.failures_from_quality_reports": (
        quality_failures_from_clean_reports,
        quality_failures_from_failed_reports,
    ),
    "btc_predictor.signals.data_quality.apply_data_quality_gate": (
        data_quality_gate_enter_clean,
        data_quality_gate_enter_blocked,
        data_quality_gate_add_blocked_with_position,
    ),
}


# --- RBT-002 R1 runtime cross-check -------------------------------------------------------

import functools as _functools  # noqa: E402

import pytest as _pytest  # noqa: E402

from btc_predictor.research_backtest import input_census as _input_census  # noqa: E402


@_functools.cache
def _census() -> _input_census.DecisionPathCensus:
    return _input_census.discover_decision_path()


@_pytest.mark.parametrize(
    "root, index",
    [(root, index) for root, thunks in sorted(FIXTURES.items()) for index in range(len(thunks))],
)
def test_the_static_census_contains_everything_this_root_traces(root: str, index: int) -> None:
    """Run the root on its synthetic fixture under sys.setprofile: every
    btc_predictor function entered and dataclass constructed must be in the
    static census, and the root itself must have run."""

    result, traced = _input_census.trace_owner_calls(FIXTURES[root][index])
    assert root in traced.functions
    assert _input_census.uncovered_traced(_census(), traced) == {"functions": [], "dataclasses": []}
    if index == 0 and hasattr(result, "complete"):
        assert result.complete is True
