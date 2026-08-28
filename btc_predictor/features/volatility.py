"""Volatility feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, require_utc_datetime


RV_7_FEATURE_ID = "RV_7"
RV_20_FEATURE_ID = "RV_20"
RV_60_FEATURE_ID = "RV_60"
VOLATILITY_COMPRESSION_RATIO_FEATURE_ID = "VOL_COMPRESSION_RATIO"
REALIZED_VOLATILITY_WINDOWS = (7, 20, 60)
REALIZED_VOLATILITY_FEATURE_IDS = {
    7: RV_7_FEATURE_ID,
    20: RV_20_FEATURE_ID,
    60: RV_60_FEATURE_ID,
}
VOLATILITY_COMPRESSION_RATIO_REASON_CODES = (
    "VOL_COMPRESSION_INPUT_MISSING",
    "VOL_COMPRESSION_ZERO_DENOMINATOR",
)
REALIZED_VOLATILITY_REASON_CODES = (
    "REALIZED_VOLATILITY_INPUT_MISSING",
    "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",
    "REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",
)
DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS = 365


@dataclass(frozen=True)
class RealizedVolatilityResult:
    feature_id: str
    observation_time: datetime
    window_days: int
    annualization_periods: int
    realized_volatility: Decimal | None
    return_count: int
    source_bar_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "window_days": self.window_days,
            "annualization_periods": self.annualization_periods,
            "realized_volatility": (
                str(self.realized_volatility)
                if self.realized_volatility is not None
                else None
            ),
            "return_count": self.return_count,
            "source_bar_count": self.source_bar_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class VolatilityCompressionRatioInput:
    rv_7: Decimal | None
    rv_60: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "rv_7": str(self.rv_7) if self.rv_7 is not None else None,
            "rv_60": str(self.rv_60) if self.rv_60 is not None else None,
        }


@dataclass(frozen=True)
class VolatilityCompressionRatioResult:
    feature_id: str
    numerator_feature_id: str
    denominator_feature_id: str
    compression_ratio: Decimal | None
    inputs: VolatilityCompressionRatioInput
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "numerator_feature_id": self.numerator_feature_id,
            "denominator_feature_id": self.denominator_feature_id,
            "compression_ratio": (
                str(self.compression_ratio)
                if self.compression_ratio is not None
                else None
            ),
            "inputs": self.inputs.as_record(),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def realized_volatility_from_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    window_days: int,
    annualization_periods: int = DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
) -> RealizedVolatilityResult:
    """Calculate annualized realized volatility from daily close-to-close returns."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_realized_volatility_parameters(
        window_days=window_days,
        annualization_periods=annualization_periods,
    )
    _validate_daily_bars(bars)
    available_bars = _available_daily_bars(bars, signal_time=signal_time)
    observation_time = available_bars[-1].timestamp if available_bars else signal_time
    reason_codes = []
    if not available_bars:
        reason_codes.append("REALIZED_VOLATILITY_INPUT_MISSING")

    selected_bars = available_bars[-(window_days + 1) :]
    if available_bars and len(selected_bars) < window_days + 1:
        reason_codes.append("REALIZED_VOLATILITY_INSUFFICIENT_HISTORY")

    realized_volatility = None
    returns: tuple[Decimal, ...] = ()
    if len(selected_bars) == window_days + 1:
        closes = tuple(bar.close for bar in selected_bars)
        if any(close <= 0 for close in closes):
            reason_codes.append("REALIZED_VOLATILITY_NON_POSITIVE_CLOSE")
        else:
            returns = _close_to_close_returns(closes)
            realized_volatility = _annualized_volatility(
                returns,
                annualization_periods=annualization_periods,
            )

    reason_codes = _dedupe_reason_codes(reason_codes)
    return RealizedVolatilityResult(
        feature_id=_realized_volatility_feature_id(window_days),
        observation_time=observation_time,
        window_days=window_days,
        annualization_periods=annualization_periods,
        realized_volatility=realized_volatility,
        return_count=len(returns),
        source_bar_count=len(available_bars),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def volatility_compression_ratio(
    inputs: VolatilityCompressionRatioInput,
) -> VolatilityCompressionRatioResult:
    """Calculate volatility compression as RV7 / RV60."""

    input_values = _compression_input_values(inputs)
    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("VOL_COMPRESSION_INPUT_MISSING")
    if input_values["rv_60"] == 0:
        reason_codes.append("VOL_COMPRESSION_ZERO_DENOMINATOR")

    compression_ratio = (
        input_values["rv_7"] / input_values["rv_60"]
        if not reason_codes
        else None
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return VolatilityCompressionRatioResult(
        feature_id=VOLATILITY_COMPRESSION_RATIO_FEATURE_ID,
        numerator_feature_id=RV_7_FEATURE_ID,
        denominator_feature_id=RV_60_FEATURE_ID,
        compression_ratio=compression_ratio,
        inputs=inputs,
        complete=compression_ratio is not None,
        reason_codes=reason_codes,
    )


def volatility_compression_ratio_from_results(
    results: Sequence[RealizedVolatilityResult],
) -> VolatilityCompressionRatioResult:
    """Calculate compression from persisted RV feature results."""

    results_by_feature_id = {result.feature_id: result for result in results}
    return volatility_compression_ratio(
        VolatilityCompressionRatioInput(
            rv_7=(
                results_by_feature_id[RV_7_FEATURE_ID].realized_volatility
                if RV_7_FEATURE_ID in results_by_feature_id
                else None
            ),
            rv_60=(
                results_by_feature_id[RV_60_FEATURE_ID].realized_volatility
                if RV_60_FEATURE_ID in results_by_feature_id
                else None
            ),
        )
    )


def rv_7_20_60_from_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    annualization_periods: int = DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
) -> tuple[RealizedVolatilityResult, RealizedVolatilityResult, RealizedVolatilityResult]:
    """Calculate RV7, RV20, and RV60 from point-in-time daily bars."""

    return tuple(
        realized_volatility_from_daily_bars(
            bars,
            as_of=as_of,
            window_days=window_days,
            annualization_periods=annualization_periods,
        )
        for window_days in REALIZED_VOLATILITY_WINDOWS
    )


def _validate_realized_volatility_parameters(
    *,
    window_days: int,
    annualization_periods: int,
) -> None:
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    if annualization_periods < 1:
        raise ValueError("annualization_periods must be >= 1")


def _validate_daily_bars(bars: Sequence[OhlcvBar]) -> None:
    for bar in bars:
        if bar.timeframe != "1d":
            raise ValueError("realized volatility requires canonical 1d bars")


def _compression_input_values(
    inputs: VolatilityCompressionRatioInput,
) -> dict[str, Decimal | None]:
    return {
        "rv_7": _non_negative_decimal(inputs.rv_7, "rv_7")
        if inputs.rv_7 is not None
        else None,
        "rv_60": _non_negative_decimal(inputs.rv_60, "rv_60")
        if inputs.rv_60 is not None
        else None,
    }


def _available_daily_bars(
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
) -> tuple[OhlcvBar, ...]:
    available_bars = []
    for bar in bars:
        record = bar.as_record()
        if record["ingested_at"] <= signal_time and record["timestamp"] <= signal_time:
            available_bars.append(bar)
    return tuple(sorted(available_bars, key=lambda bar: bar.timestamp))


def _close_to_close_returns(closes: Sequence[Decimal]) -> tuple[Decimal, ...]:
    return tuple(
        (current_close / previous_close) - Decimal("1")
        for previous_close, current_close in zip(closes, closes[1:])
    )


def _annualized_volatility(
    returns: Sequence[Decimal],
    *,
    annualization_periods: int,
) -> Decimal:
    mean = sum(returns, Decimal("0")) / Decimal(len(returns))
    variance = sum(((value - mean) ** 2 for value in returns), Decimal("0")) / Decimal(
        len(returns)
    )
    return variance.sqrt() * Decimal(annualization_periods).sqrt()


def _realized_volatility_feature_id(window_days: int) -> str:
    return REALIZED_VOLATILITY_FEATURE_IDS.get(window_days, f"RV_{window_days}")


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        raise ValueError(f"{name} must be >= 0")
    return decimal_value


def _dedupe_reason_codes(reason_codes: Sequence[str]) -> tuple[str, ...]:
    deduped = []
    for reason_code in reason_codes:
        if reason_code not in deduped:
            deduped.append(reason_code)
    return tuple(deduped)
