"""Volume-profile levels from point-in-time OHLCV bars."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime


VOLUME_PROFILE_RESULT_FEATURE_ID = "VOLUME_PROFILE_LEVELS"
VOLUME_PROFILE_LEVEL_FEATURE_ID = "VOLUME_PROFILE_LEVEL"
VOLUME_PROFILE_POC = "poc"
VOLUME_PROFILE_HVN = "hvn"
VOLUME_PROFILE_VAH = "vah"
VOLUME_PROFILE_VAL = "val"
VOLUME_PROFILE_LEVEL_TYPES = (
    VOLUME_PROFILE_POC,
    VOLUME_PROFILE_HVN,
    VOLUME_PROFILE_VAH,
    VOLUME_PROFILE_VAL,
)
VOLUME_PROFILE_PRICE_SOURCE_HLC3 = "hlc3"
VOLUME_PROFILE_PRICE_SOURCE_CLOSE = "close"
VOLUME_PROFILE_PRICE_SOURCES = (
    VOLUME_PROFILE_PRICE_SOURCE_HLC3,
    VOLUME_PROFILE_PRICE_SOURCE_CLOSE,
)
VOLUME_PROFILE_REASON_CODES = (
    "VOLUME_PROFILE_INPUT_MISSING",
    "VOLUME_PROFILE_INSUFFICIENT_BARS",
    "VOLUME_PROFILE_ZERO_VOLUME",
    "VOLUME_PROFILE_POC",
    "VOLUME_PROFILE_HVN",
    "VOLUME_PROFILE_VALUE_AREA",
    "VOLUME_PROFILE_COMPLETE",
)
DEFAULT_VOLUME_PROFILE_PRICE_SOURCE = VOLUME_PROFILE_PRICE_SOURCE_HLC3
DEFAULT_VOLUME_PROFILE_BIN_SIZE_FRACTION = Decimal("0.01")
DEFAULT_VOLUME_PROFILE_VALUE_AREA_FRACTION = Decimal("0.70")
DEFAULT_VOLUME_PROFILE_HVN_VOLUME_FRACTION = Decimal("0.70")
DEFAULT_VOLUME_PROFILE_MIN_BARS = 20


@dataclass(frozen=True)
class VolumeProfileBin:
    index: int
    lower: Decimal
    upper: Decimal
    midpoint: Decimal
    volume: Decimal
    bar_count: int

    def as_record(self) -> dict[str, Any]:
        if self.upper <= self.lower:
            raise ValueError("bin upper must be greater than lower")
        if self.midpoint <= 0:
            raise ValueError("bin midpoint must be > 0")
        if self.volume < 0:
            raise ValueError("bin volume must be >= 0")
        if self.bar_count < 0:
            raise ValueError("bin bar_count must be >= 0")
        return {
            "index": self.index,
            "lower": str(self.lower),
            "upper": str(self.upper),
            "midpoint": str(self.midpoint),
            "volume": str(self.volume),
            "bar_count": self.bar_count,
        }


@dataclass(frozen=True)
class VolumeProfileLevel:
    feature_id: str
    level_type: str
    price: Decimal
    detected_at: datetime
    profile_start: datetime
    profile_end: datetime
    exchange: str
    symbol: str
    timeframe: str
    provider: str
    price_source: str
    bin_size: Decimal
    bin_size_fraction: Decimal
    bin_lower: Decimal
    bin_upper: Decimal
    bin_volume: Decimal
    total_volume: Decimal
    value_area_volume: Decimal
    value_area_fraction: Decimal
    hvn_volume_fraction: Decimal
    source_bar_count: int
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        profile_start = require_utc_datetime(self.profile_start, "profile_start")
        profile_end = require_utc_datetime(self.profile_end, "profile_end")
        if self.feature_id != VOLUME_PROFILE_LEVEL_FEATURE_ID:
            raise ValueError("feature_id must be VOLUME_PROFILE_LEVEL")
        if self.level_type not in VOLUME_PROFILE_LEVEL_TYPES:
            raise ValueError(f"level_type must be one of {VOLUME_PROFILE_LEVEL_TYPES}")
        if profile_end < profile_start:
            raise ValueError("profile_end must be >= profile_start")
        if detected_at < profile_end:
            raise ValueError("detected_at must be >= profile_end")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        _validate_price_source(self.price_source)
        _positive_decimal(self.bin_size, "bin_size")
        _positive_fraction(self.bin_size_fraction, "bin_size_fraction")
        _positive_fraction(self.value_area_fraction, "value_area_fraction")
        _positive_fraction(self.hvn_volume_fraction, "hvn_volume_fraction")
        if self.bin_upper <= self.bin_lower:
            raise ValueError("bin_upper must be greater than bin_lower")
        if self.bin_volume < 0:
            raise ValueError("bin_volume must be >= 0")
        if self.total_volume <= 0:
            raise ValueError("total_volume must be > 0")
        if self.value_area_volume <= 0:
            raise ValueError("value_area_volume must be > 0")
        if self.source_bar_count < 1:
            raise ValueError("source_bar_count must be >= 1")
        return {
            "feature_id": self.feature_id,
            "level_type": self.level_type,
            "price": str(self.price),
            "detected_at": detected_at.isoformat(),
            "profile_start": profile_start.isoformat(),
            "profile_end": profile_end.isoformat(),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "provider": self.provider,
            "price_source": self.price_source,
            "bin_size": str(self.bin_size),
            "bin_size_fraction": str(self.bin_size_fraction),
            "bin_lower": str(self.bin_lower),
            "bin_upper": str(self.bin_upper),
            "bin_volume": str(self.bin_volume),
            "total_volume": str(self.total_volume),
            "value_area_volume": str(self.value_area_volume),
            "value_area_fraction": str(self.value_area_fraction),
            "hvn_volume_fraction": str(self.hvn_volume_fraction),
            "source_bar_count": self.source_bar_count,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class VolumeProfileResult:
    feature_id: str
    as_of: datetime
    levels: tuple[VolumeProfileLevel, ...]
    price_source: str
    bin_size_fraction: Decimal
    value_area_fraction: Decimal
    hvn_volume_fraction: Decimal
    min_bar_count: int
    source_bar_count: int
    total_volume: Decimal
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        as_of = require_utc_datetime(self.as_of, "as_of")
        if self.feature_id != VOLUME_PROFILE_RESULT_FEATURE_ID:
            raise ValueError("feature_id must be VOLUME_PROFILE_LEVELS")
        _validate_price_source(self.price_source)
        _positive_fraction(self.bin_size_fraction, "bin_size_fraction")
        _positive_fraction(self.value_area_fraction, "value_area_fraction")
        _positive_fraction(self.hvn_volume_fraction, "hvn_volume_fraction")
        if self.min_bar_count < 1:
            raise ValueError("min_bar_count must be >= 1")
        if self.source_bar_count < 0:
            raise ValueError("source_bar_count must be >= 0")
        if self.total_volume < 0:
            raise ValueError("total_volume must be >= 0")
        if self.complete and not self.levels:
            raise ValueError("complete volume profile requires levels")
        return {
            "feature_id": self.feature_id,
            "as_of": as_of.isoformat(),
            "levels": [level.as_record() for level in self.levels],
            "price_source": self.price_source,
            "bin_size_fraction": str(self.bin_size_fraction),
            "value_area_fraction": str(self.value_area_fraction),
            "hvn_volume_fraction": str(self.hvn_volume_fraction),
            "min_bar_count": self.min_bar_count,
            "source_bar_count": self.source_bar_count,
            "total_volume": str(self.total_volume),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_volume_profile_levels(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    price_source: str = DEFAULT_VOLUME_PROFILE_PRICE_SOURCE,
    bin_size_fraction: Any = DEFAULT_VOLUME_PROFILE_BIN_SIZE_FRACTION,
    value_area_fraction: Any = DEFAULT_VOLUME_PROFILE_VALUE_AREA_FRACTION,
    hvn_volume_fraction: Any = DEFAULT_VOLUME_PROFILE_HVN_VOLUME_FRACTION,
    min_bar_count: int = DEFAULT_VOLUME_PROFILE_MIN_BARS,
) -> VolumeProfileResult:
    """Calculate POC, HVN, VAH, and VAL from bars available at signal time."""

    signal_time = require_utc_datetime(as_of, "as_of")
    price_source = _validate_price_source(price_source)
    bin_fraction = _positive_decimal_fraction(bin_size_fraction, "bin_size_fraction")
    value_fraction = _positive_decimal_fraction(
        value_area_fraction,
        "value_area_fraction",
    )
    hvn_fraction = _positive_decimal_fraction(hvn_volume_fraction, "hvn_volume_fraction")
    if min_bar_count < 1:
        raise ValueError("min_bar_count must be >= 1")

    available_bars = _available_bars(bars, signal_time=signal_time)
    if not available_bars:
        return _incomplete_result(
            as_of=signal_time,
            price_source=price_source,
            bin_size_fraction=bin_fraction,
            value_area_fraction=value_fraction,
            hvn_volume_fraction=hvn_fraction,
            min_bar_count=min_bar_count,
            reason_codes=("VOLUME_PROFILE_INPUT_MISSING",),
        )

    total_volume = sum((bar.volume for bar in available_bars), Decimal("0"))
    if len(available_bars) < min_bar_count:
        return _incomplete_result(
            as_of=signal_time,
            price_source=price_source,
            bin_size_fraction=bin_fraction,
            value_area_fraction=value_fraction,
            hvn_volume_fraction=hvn_fraction,
            min_bar_count=min_bar_count,
            source_bar_count=len(available_bars),
            total_volume=total_volume,
            reason_codes=("VOLUME_PROFILE_INSUFFICIENT_BARS",),
        )
    if total_volume == 0:
        return _incomplete_result(
            as_of=signal_time,
            price_source=price_source,
            bin_size_fraction=bin_fraction,
            value_area_fraction=value_fraction,
            hvn_volume_fraction=hvn_fraction,
            min_bar_count=min_bar_count,
            source_bar_count=len(available_bars),
            reason_codes=("VOLUME_PROFILE_ZERO_VOLUME",),
        )

    timeframe = _single_timeframe(available_bars)
    exchange, symbol, provider = _single_series_identity(available_bars)
    reference_price = available_bars[-1].close
    bin_size = reference_price * bin_fraction
    _positive_decimal(bin_size, "bin_size")
    profile_bins = _build_profile_bins(
        available_bars,
        price_source=price_source,
        bin_size=bin_size,
    )
    poc_bin = _poc_bin(profile_bins, reference_price=reference_price)
    value_area_bins = _value_area_bins(
        profile_bins,
        poc_bin=poc_bin,
        total_volume=total_volume,
        value_area_fraction=value_fraction,
    )
    value_area_volume = sum((profile_bin.volume for profile_bin in value_area_bins), Decimal("0"))
    profile_start = available_bars[0].timestamp
    profile_end = available_bars[-1].timestamp

    levels = [
        _level_from_bin(
            poc_bin,
            level_type=VOLUME_PROFILE_POC,
            price=poc_bin.midpoint,
            detected_at=signal_time,
            profile_start=profile_start,
            profile_end=profile_end,
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            provider=provider,
            price_source=price_source,
            bin_size=bin_size,
            bin_size_fraction=bin_fraction,
            total_volume=total_volume,
            value_area_volume=value_area_volume,
            value_area_fraction=value_fraction,
            hvn_volume_fraction=hvn_fraction,
            source_bar_count=len(available_bars),
            reason_codes=("VOLUME_PROFILE_POC",),
        )
    ]
    levels.extend(
        _level_from_bin(
            profile_bin,
            level_type=VOLUME_PROFILE_HVN,
            price=profile_bin.midpoint,
            detected_at=signal_time,
            profile_start=profile_start,
            profile_end=profile_end,
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            provider=provider,
            price_source=price_source,
            bin_size=bin_size,
            bin_size_fraction=bin_fraction,
            total_volume=total_volume,
            value_area_volume=value_area_volume,
            value_area_fraction=value_fraction,
            hvn_volume_fraction=hvn_fraction,
            source_bar_count=len(available_bars),
            reason_codes=("VOLUME_PROFILE_HVN",),
        )
        for profile_bin in _hvn_bins(
            profile_bins,
            poc_bin=poc_bin,
            hvn_volume_fraction=hvn_fraction,
        )
    )

    value_area_low = min(value_area_bins, key=lambda profile_bin: profile_bin.index)
    value_area_high = max(value_area_bins, key=lambda profile_bin: profile_bin.index)
    levels.extend(
        (
            _level_from_bin(
                value_area_high,
                level_type=VOLUME_PROFILE_VAH,
                price=value_area_high.upper,
                detected_at=signal_time,
                profile_start=profile_start,
                profile_end=profile_end,
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                provider=provider,
                price_source=price_source,
                bin_size=bin_size,
                bin_size_fraction=bin_fraction,
                total_volume=total_volume,
                value_area_volume=value_area_volume,
                value_area_fraction=value_fraction,
                hvn_volume_fraction=hvn_fraction,
                source_bar_count=len(available_bars),
                reason_codes=("VOLUME_PROFILE_VALUE_AREA",),
            ),
            _level_from_bin(
                value_area_low,
                level_type=VOLUME_PROFILE_VAL,
                price=value_area_low.lower,
                detected_at=signal_time,
                profile_start=profile_start,
                profile_end=profile_end,
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                provider=provider,
                price_source=price_source,
                bin_size=bin_size,
                bin_size_fraction=bin_fraction,
                total_volume=total_volume,
                value_area_volume=value_area_volume,
                value_area_fraction=value_fraction,
                hvn_volume_fraction=hvn_fraction,
                source_bar_count=len(available_bars),
                reason_codes=("VOLUME_PROFILE_VALUE_AREA",),
            ),
        )
    )

    return VolumeProfileResult(
        feature_id=VOLUME_PROFILE_RESULT_FEATURE_ID,
        as_of=signal_time,
        levels=tuple(
            sorted(
                levels,
                key=lambda level: (
                    VOLUME_PROFILE_LEVEL_TYPES.index(level.level_type),
                    level.price,
                ),
            )
        ),
        price_source=price_source,
        bin_size_fraction=bin_fraction,
        value_area_fraction=value_fraction,
        hvn_volume_fraction=hvn_fraction,
        min_bar_count=min_bar_count,
        source_bar_count=len(available_bars),
        total_volume=total_volume,
        complete=True,
        reason_codes=("VOLUME_PROFILE_COMPLETE",),
    )


def _available_bars(
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        _validate_ohlcv_bar(bar)
        if next_bar_timestamp(bar.timestamp, bar.timeframe) > signal_time:
            continue
        if require_utc_datetime(bar.ingested_at, "ingested_at") > signal_time:
            continue
        available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_ohlcv_bar(bar: OhlcvBar) -> None:
    record = bar.as_record()
    if record["open"] <= 0:
        raise ValueError("bar open must be > 0")
    if record["high"] <= 0:
        raise ValueError("bar high must be > 0")
    if record["low"] <= 0:
        raise ValueError("bar low must be > 0")
    if record["close"] <= 0:
        raise ValueError("bar close must be > 0")
    if record["volume"] < 0:
        raise ValueError("bar volume must be >= 0")
    next_bar_timestamp(record["timestamp"], record["timeframe"])


def _build_profile_bins(
    bars: Sequence[OhlcvBar],
    *,
    price_source: str,
    bin_size: Decimal,
) -> tuple[VolumeProfileBin, ...]:
    observed: dict[int, tuple[Decimal, int]] = {}
    for bar in bars:
        price = _bar_price(bar, price_source)
        index = int((price / bin_size).to_integral_value(rounding=ROUND_FLOOR))
        volume, bar_count = observed.get(index, (Decimal("0"), 0))
        observed[index] = (volume + bar.volume, bar_count + 1)

    min_index = min(observed)
    max_index = max(observed)
    profile_bins = []
    for index in range(min_index, max_index + 1):
        volume, bar_count = observed.get(index, (Decimal("0"), 0))
        lower = Decimal(index) * bin_size
        upper = Decimal(index + 1) * bin_size
        profile_bins.append(
            VolumeProfileBin(
                index=index,
                lower=lower,
                upper=upper,
                midpoint=(lower + upper) / Decimal("2"),
                volume=volume,
                bar_count=bar_count,
            )
        )
    return tuple(profile_bins)


def _poc_bin(
    profile_bins: Sequence[VolumeProfileBin],
    *,
    reference_price: Decimal,
) -> VolumeProfileBin:
    return min(
        profile_bins,
        key=lambda profile_bin: (
            -profile_bin.volume,
            abs(profile_bin.midpoint - reference_price),
            profile_bin.index,
        ),
    )


def _hvn_bins(
    profile_bins: Sequence[VolumeProfileBin],
    *,
    poc_bin: VolumeProfileBin,
    hvn_volume_fraction: Decimal,
) -> tuple[VolumeProfileBin, ...]:
    threshold = poc_bin.volume * hvn_volume_fraction
    return tuple(
        sorted(
            (
                profile_bin
                for profile_bin in profile_bins
                if profile_bin.index != poc_bin.index
                and profile_bin.volume > 0
                and profile_bin.volume >= threshold
            ),
            key=lambda profile_bin: (-profile_bin.volume, profile_bin.index),
        )
    )


def _value_area_bins(
    profile_bins: Sequence[VolumeProfileBin],
    *,
    poc_bin: VolumeProfileBin,
    total_volume: Decimal,
    value_area_fraction: Decimal,
) -> tuple[VolumeProfileBin, ...]:
    by_index = {profile_bin.index: profile_bin for profile_bin in profile_bins}
    min_index = min(by_index)
    max_index = max(by_index)
    included = {poc_bin.index}
    cumulative_volume = poc_bin.volume
    target_volume = total_volume * value_area_fraction
    left_index = poc_bin.index - 1
    right_index = poc_bin.index + 1

    while cumulative_volume < target_volume and (
        left_index >= min_index or right_index <= max_index
    ):
        if left_index < min_index:
            selected_index = right_index
            right_index += 1
        elif right_index > max_index:
            selected_index = left_index
            left_index -= 1
        elif by_index[right_index].volume > by_index[left_index].volume:
            selected_index = right_index
            right_index += 1
        else:
            selected_index = left_index
            left_index -= 1
        included.add(selected_index)
        cumulative_volume += by_index[selected_index].volume

    return tuple(by_index[index] for index in sorted(included))


def _level_from_bin(
    profile_bin: VolumeProfileBin,
    *,
    level_type: str,
    price: Decimal,
    detected_at: datetime,
    profile_start: datetime,
    profile_end: datetime,
    exchange: str,
    symbol: str,
    timeframe: str,
    provider: str,
    price_source: str,
    bin_size: Decimal,
    bin_size_fraction: Decimal,
    total_volume: Decimal,
    value_area_volume: Decimal,
    value_area_fraction: Decimal,
    hvn_volume_fraction: Decimal,
    source_bar_count: int,
    reason_codes: tuple[str, ...],
) -> VolumeProfileLevel:
    return VolumeProfileLevel(
        feature_id=VOLUME_PROFILE_LEVEL_FEATURE_ID,
        level_type=level_type,
        price=price,
        detected_at=detected_at,
        profile_start=profile_start,
        profile_end=profile_end,
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        provider=provider,
        price_source=price_source,
        bin_size=bin_size,
        bin_size_fraction=bin_size_fraction,
        bin_lower=profile_bin.lower,
        bin_upper=profile_bin.upper,
        bin_volume=profile_bin.volume,
        total_volume=total_volume,
        value_area_volume=value_area_volume,
        value_area_fraction=value_area_fraction,
        hvn_volume_fraction=hvn_volume_fraction,
        source_bar_count=source_bar_count,
        reason_codes=reason_codes,
    )


def _incomplete_result(
    *,
    as_of: datetime,
    price_source: str,
    bin_size_fraction: Decimal,
    value_area_fraction: Decimal,
    hvn_volume_fraction: Decimal,
    min_bar_count: int,
    reason_codes: tuple[str, ...],
    source_bar_count: int = 0,
    total_volume: Decimal = Decimal("0"),
) -> VolumeProfileResult:
    return VolumeProfileResult(
        feature_id=VOLUME_PROFILE_RESULT_FEATURE_ID,
        as_of=as_of,
        levels=(),
        price_source=price_source,
        bin_size_fraction=bin_size_fraction,
        value_area_fraction=value_area_fraction,
        hvn_volume_fraction=hvn_volume_fraction,
        min_bar_count=min_bar_count,
        source_bar_count=source_bar_count,
        total_volume=total_volume,
        complete=False,
        reason_codes=reason_codes,
    )


def _bar_price(bar: OhlcvBar, price_source: str) -> Decimal:
    if price_source == VOLUME_PROFILE_PRICE_SOURCE_HLC3:
        return (bar.high + bar.low + bar.close) / Decimal("3")
    if price_source == VOLUME_PROFILE_PRICE_SOURCE_CLOSE:
        return bar.close
    raise ValueError(f"price_source must be one of {VOLUME_PROFILE_PRICE_SOURCES}")


def _single_timeframe(bars: Sequence[OhlcvBar]) -> str:
    timeframes = {bar.timeframe for bar in bars}
    if len(timeframes) != 1:
        raise ValueError("volume profile requires bars from a single timeframe")
    return next(iter(timeframes))


def _single_series_identity(bars: Sequence[OhlcvBar]) -> tuple[str, str, str]:
    identities = {(bar.exchange, bar.symbol, bar.provider) for bar in bars}
    if len(identities) != 1:
        raise ValueError("volume profile requires bars from a single market series")
    return next(iter(identities))


def _validate_price_source(price_source: str) -> str:
    if price_source not in VOLUME_PROFILE_PRICE_SOURCES:
        raise ValueError(f"price_source must be one of {VOLUME_PROFILE_PRICE_SOURCES}")
    return price_source


def _positive_decimal_fraction(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    return _positive_fraction(decimal_value, name)


def _positive_fraction(value: Decimal, name: str) -> Decimal:
    if value <= 0 or value > 1:
        raise ValueError(f"{name} must be > 0 and <= 1")
    return value


def _positive_decimal(value: Decimal, name: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"{name} must be > 0")
    return value
