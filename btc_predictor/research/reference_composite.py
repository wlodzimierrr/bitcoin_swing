"""Point-in-time cross-venue BTC reference-composite research methods."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from btc_predictor.data import OhlcvBar, require_utc_datetime


REFERENCE_COMPOSITE_POLICY_VERSION = "BTC_REFERENCE_COMPOSITE_V1"
REFERENCE_COMPOSITE_STATUS = "RESEARCH"
REFERENCE_COMPOSITE_PROVIDER_ID = "btc_reference_composite"
REFERENCE_COMPOSITE_EXCHANGE = "cross_venue_reference"
REFERENCE_COMPOSITE_SYMBOL = "BTC/USD"

BITSTAMP_PROVIDER_ID = "bitstamp"
COINBASE_PROVIDER_ID = "coinbase"
BITFINEX_PROVIDER_ID = "bitfinex"
REQUIRED_COMPOSITE_PROVIDER_IDS = (
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    BITFINEX_PROVIDER_ID,
)

MEDIAN_OHLC_METHOD = "median_ohlc"
MEDIAN_OHLC_VERSION = "MEDIAN_OHLC_V1"
CONFIRMED_EXTREMES_METHOD = "confirmed_extremes"
CONFIRMED_EXTREMES_VERSION = "CONFIRMED_EXTREMES_V1"
CLIPPED_CENTER_METHOD = "clipped_center"
CLIPPED_CENTER_VERSION = "CLIPPED_CENTER_V1"
COMPOSITE_METHODS = (
    MEDIAN_OHLC_METHOD,
    CONFIRMED_EXTREMES_METHOD,
    CLIPPED_CENTER_METHOD,
)
METHOD_VERSION_BY_METHOD = {
    MEDIAN_OHLC_METHOD: MEDIAN_OHLC_VERSION,
    CONFIRMED_EXTREMES_METHOD: CONFIRMED_EXTREMES_VERSION,
    CLIPPED_CENTER_METHOD: CLIPPED_CENTER_VERSION,
}

REFERENCE_OK = "REFERENCE_OK"
REFERENCE_DEGRADED = "REFERENCE_DEGRADED"
REFERENCE_UNAVAILABLE = "REFERENCE_UNAVAILABLE"
VENUE_DISAGREEMENT = "VENUE_DISAGREEMENT"
REFERENCE_QUALITY_STATES = (
    REFERENCE_OK,
    REFERENCE_DEGRADED,
    REFERENCE_UNAVAILABLE,
    VENUE_DISAGREEMENT,
)

SINGLE_PROVIDER_OBSERVATION = "SINGLE_PROVIDER_OBSERVATION"
TWO_PROVIDER_CONSENSUS = "TWO_PROVIDER_CONSENSUS"
THREE_PROVIDER_CONSENSUS = "THREE_PROVIDER_CONSENSUS"
UNRESOLVED_PROVIDER_DISAGREEMENT = "UNRESOLVED_PROVIDER_DISAGREEMENT"
REFERENCE_CONFIRMATION_STATES = (
    SINGLE_PROVIDER_OBSERVATION,
    TWO_PROVIDER_CONSENSUS,
    THREE_PROVIDER_CONSENSUS,
    UNRESOLVED_PROVIDER_DISAGREEMENT,
)

DEFAULT_CONFIRMATION_TOLERANCE_ATR = Decimal("0.15")
CONFIRMATION_TOLERANCE_ATR_GRID = (
    Decimal("0.05"),
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
    Decimal("0.30"),
)
DEFAULT_CLOSE_DISAGREEMENT_BPS = Decimal("50")
DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR = Decimal("0.30")
DEFAULT_ATR_WINDOW_DAYS = 14
DEFAULT_DECISION_DELAY = timedelta(minutes=5)

COMPOSITE_REASON_CODES = (
    "COMPOSITE_INPUT_COUNT_INSUFFICIENT",
    "COMPOSITE_TRAILING_ATR_UNAVAILABLE",
    "COMPOSITE_CLOSE_DISAGREEMENT",
    "COMPOSITE_CLOSE_PARTIAL_CONSENSUS",
    "COMPOSITE_TWO_PROVIDER_RANGE_DISAGREEMENT",
    "COMPOSITE_CANDLE_INVARIANT_FAILED",
    "COMPOSITE_PROVIDER_LATE",
)


@dataclass(frozen=True)
class CompositeMethodDefinition:
    method: str
    method_version: str
    confirmation_tolerance_atr: Decimal | None
    formula: str

    def as_record(self) -> dict[str, str | None]:
        if self.method not in COMPOSITE_METHODS:
            raise ValueError(f"method must be one of {COMPOSITE_METHODS}")
        if self.method_version != METHOD_VERSION_BY_METHOD[self.method]:
            raise ValueError("method and method_version must use the frozen V1 pairing")
        if not self.method_version.strip() or not self.formula.strip():
            raise ValueError("method version and formula must be non-empty")
        if (
            self.confirmation_tolerance_atr is not None
            and self.confirmation_tolerance_atr <= 0
        ):
            raise ValueError("confirmation tolerance must be positive")
        return {
            "method": self.method,
            "method_version": self.method_version,
            "confirmation_tolerance_atr": (
                str(self.confirmation_tolerance_atr)
                if self.confirmation_tolerance_atr is not None
                else None
            ),
            "formula": self.formula,
        }


MEDIAN_OHLC_DEFINITION = CompositeMethodDefinition(
    method=MEDIAN_OHLC_METHOD,
    method_version=MEDIAN_OHLC_VERSION,
    confirmation_tolerance_atr=None,
    formula="Independent cross-provider median of open, high, low, and close.",
)
CONFIRMED_EXTREMES_DEFINITION = CompositeMethodDefinition(
    method=CONFIRMED_EXTREMES_METHOD,
    method_version=CONFIRMED_EXTREMES_VERSION,
    confirmation_tolerance_atr=DEFAULT_CONFIRMATION_TOLERANCE_ATR,
    formula=(
        "Median open/close; retain the most extreme high or low only when the "
        "two most extreme venues are within tolerance, otherwise use the median."
    ),
)
CLIPPED_CENTER_DEFINITION = CompositeMethodDefinition(
    method=CLIPPED_CENTER_METHOD,
    method_version=CLIPPED_CENTER_VERSION,
    confirmation_tolerance_atr=DEFAULT_CONFIRMATION_TOLERANCE_ATR,
    formula=(
        "For each OHLC field, start at the cross-provider median and add the "
        "mean residual after clipping each residual to +/- tolerance * prior ATR."
    ),
)
DEFAULT_COMPOSITE_METHOD_DEFINITIONS = (
    MEDIAN_OHLC_DEFINITION,
    CONFIRMED_EXTREMES_DEFINITION,
    CLIPPED_CENTER_DEFINITION,
)


@dataclass(frozen=True)
class ReferenceCompositePolicy:
    version: str = REFERENCE_COMPOSITE_POLICY_VERSION
    status: str = REFERENCE_COMPOSITE_STATUS
    required_provider_ids: tuple[str, ...] = REQUIRED_COMPOSITE_PROVIDER_IDS
    minimum_provider_count: int = 2
    decision_delay: timedelta = DEFAULT_DECISION_DELAY
    close_disagreement_bps: Decimal = DEFAULT_CLOSE_DISAGREEMENT_BPS
    two_provider_range_disagreement_atr: Decimal = (
        DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR
    )
    atr_window_days: int = DEFAULT_ATR_WINDOW_DAYS

    def as_record(self) -> dict[str, Any]:
        if self.version != REFERENCE_COMPOSITE_POLICY_VERSION:
            raise ValueError(f"version must be {REFERENCE_COMPOSITE_POLICY_VERSION}")
        if self.status != REFERENCE_COMPOSITE_STATUS:
            raise ValueError("composite policy must remain RESEARCH until approved")
        if self.required_provider_ids != REQUIRED_COMPOSITE_PROVIDER_IDS:
            raise ValueError("V1 composite provider set is immutable")
        if self.minimum_provider_count != 2:
            raise ValueError("V1 composite requires two independent providers")
        if self.decision_delay < timedelta(0):
            raise ValueError("decision delay must be non-negative")
        if self.close_disagreement_bps <= 0:
            raise ValueError("close disagreement threshold must be positive")
        if self.two_provider_range_disagreement_atr <= 0:
            raise ValueError("range disagreement threshold must be positive")
        if self.atr_window_days < 1:
            raise ValueError("ATR window must be positive")
        return {
            "version": self.version,
            "status": self.status,
            "required_provider_ids": list(self.required_provider_ids),
            "minimum_provider_count": self.minimum_provider_count,
            "decision_delay_seconds": int(self.decision_delay.total_seconds()),
            "close_disagreement_bps": str(self.close_disagreement_bps),
            "two_provider_range_disagreement_atr": str(
                self.two_provider_range_disagreement_atr,
            ),
            "atr_window_days": self.atr_window_days,
            "missing_provider_logic": {
                "3": REFERENCE_OK,
                "2": "REFERENCE_DEGRADED if agreement checks pass",
                "1": REFERENCE_UNAVAILABLE,
                "0": REFERENCE_UNAVAILABLE,
            },
            "point_in_time_logic": (
                "Include only inputs available by observation close plus the fixed "
                "decision delay; composite available_at is that fixed decision time."
            ),
            "fallback_splicing_allowed": False,
        }


DEFAULT_REFERENCE_COMPOSITE_POLICY = ReferenceCompositePolicy()


@dataclass(frozen=True)
class ProviderCandleInput:
    observation_id: str
    bar: OhlcvBar
    available_at: datetime

    def as_record(self) -> dict[str, Any]:
        available_at = require_utc_datetime(self.available_at, "available_at")
        record = self.bar.as_record()
        if self.bar.provider not in REQUIRED_COMPOSITE_PROVIDER_IDS:
            raise ValueError("provider is not part of the V1 composite")
        if self.bar.timeframe != "1h":
            raise ValueError("reference composite requires 1h input candles")
        if available_at < self.bar.timestamp + timedelta(hours=1):
            raise ValueError("provider candle cannot be available before bar close")
        if not self.observation_id.strip():
            raise ValueError("observation_id must be non-empty")
        return {
            "observation_id": self.observation_id,
            "provider": self.bar.provider,
            "observation_time": record["timestamp"].isoformat(),
            "available_at": available_at.isoformat(),
        }


@dataclass(frozen=True)
class CompositeDiagnostics:
    close_dispersion_bps: Decimal | None
    high_dispersion_atr: Decimal | None
    low_dispersion_atr: Decimal | None
    range_dispersion_atr: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "close_dispersion_bps": _optional_decimal(self.close_dispersion_bps),
            "high_dispersion_atr": _optional_decimal(self.high_dispersion_atr),
            "low_dispersion_atr": _optional_decimal(self.low_dispersion_atr),
            "range_dispersion_atr": _optional_decimal(self.range_dispersion_atr),
        }


@dataclass(frozen=True)
class CompositeReferenceObservation:
    reference_policy_version: str
    observation_time: datetime
    available_at: datetime
    input_providers_expected: tuple[str, ...]
    input_providers_available: tuple[str, ...]
    bitstamp_observation_id: str | None
    coinbase_observation_id: str | None
    bitfinex_observation_id: str | None
    input_count: int
    composite_method: str
    composite_method_version: str
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    quality_state: str
    confirmation_state: str
    fallback_used: bool
    diagnostics: CompositeDiagnostics
    reason_codes: tuple[str, ...]

    @property
    def usable(self) -> bool:
        return self.quality_state in (REFERENCE_OK, REFERENCE_DEGRADED)

    def as_record(self) -> dict[str, Any]:
        observation_time = require_utc_datetime(
            self.observation_time,
            "observation_time",
        )
        available_at = require_utc_datetime(self.available_at, "available_at")
        if self.reference_policy_version != REFERENCE_COMPOSITE_POLICY_VERSION:
            raise ValueError("reference policy version mismatch")
        if self.input_providers_expected != REQUIRED_COMPOSITE_PROVIDER_IDS:
            raise ValueError("input_providers_expected must use the frozen V1 set")
        if self.input_count != len(self.input_providers_available):
            raise ValueError("input_count must match available provider count")
        if self.quality_state not in REFERENCE_QUALITY_STATES:
            raise ValueError("unknown reference quality state")
        if self.confirmation_state not in REFERENCE_CONFIRMATION_STATES:
            raise ValueError("unknown reference confirmation state")
        if self.fallback_used:
            raise ValueError("historical fallback splicing is prohibited")
        values = (self.open, self.high, self.low, self.close)
        if self.usable:
            if any(value is None for value in values):
                raise ValueError("usable composite must contain OHLC values")
            _validate_candle(
                self.open,
                self.high,
                self.low,
                self.close,
            )
        elif any(value is not None for value in values):
            raise ValueError("unusable composite must not publish OHLC values")
        return {
            "reference_policy_version": self.reference_policy_version,
            "observation_time": observation_time.isoformat(),
            "available_at": available_at.isoformat(),
            "input_providers_expected": list(self.input_providers_expected),
            "input_providers_available": list(self.input_providers_available),
            "bitstamp_observation_id": self.bitstamp_observation_id,
            "coinbase_observation_id": self.coinbase_observation_id,
            "bitfinex_observation_id": self.bitfinex_observation_id,
            "input_count": self.input_count,
            "composite_method": self.composite_method,
            "composite_method_version": self.composite_method_version,
            "open": _optional_decimal(self.open),
            "high": _optional_decimal(self.high),
            "low": _optional_decimal(self.low),
            "close": _optional_decimal(self.close),
            "quality_state": self.quality_state,
            "confirmation_state": self.confirmation_state,
            "fallback_used": self.fallback_used,
            "diagnostics": self.diagnostics.as_record(),
            "reason_codes": list(self.reason_codes),
        }

    def as_ohlcv_bar(self) -> OhlcvBar:
        if not self.usable:
            raise ValueError("unusable composite cannot be exposed as an OHLCV bar")
        return OhlcvBar(
            timestamp=self.observation_time,
            exchange=REFERENCE_COMPOSITE_EXCHANGE,
            symbol=REFERENCE_COMPOSITE_SYMBOL,
            timeframe="1h",
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=Decimal("0"),
            provider=self.composite_method_version.lower(),
            ingested_at=self.available_at,
        )

    def as_database_record(self) -> dict[str, Any]:
        """Return a typed row for immutable derived-table persistence."""

        self.as_record()
        return {
            "reference_policy_version": self.reference_policy_version,
            "observation_time": self.observation_time,
            "available_at": self.available_at,
            "input_providers_expected": list(self.input_providers_expected),
            "input_providers_available": list(self.input_providers_available),
            "bitstamp_observation_id": self.bitstamp_observation_id,
            "coinbase_observation_id": self.coinbase_observation_id,
            "bitfinex_observation_id": self.bitfinex_observation_id,
            "input_count": self.input_count,
            "composite_method": self.composite_method,
            "composite_method_version": self.composite_method_version,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "quality_state": self.quality_state,
            "confirmation_state": self.confirmation_state,
            "fallback_used": self.fallback_used,
            "diagnostics": self.diagnostics.as_record(),
            "reason_codes": list(self.reason_codes),
        }


def provider_candle_input(
    bar: OhlcvBar,
    *,
    available_at: datetime | None = None,
) -> ProviderCandleInput:
    """Wrap an immutable raw candle with explicit point-in-time availability."""

    value = ProviderCandleInput(
        observation_id=raw_observation_id(bar),
        bar=bar,
        available_at=available_at or bar.timestamp + timedelta(hours=1),
    )
    value.as_record()
    return value


def raw_observation_id(bar: OhlcvBar) -> str:
    record = bar.as_record()
    identity = "|".join(
        (
            record["timestamp"].isoformat(),
            record["exchange"],
            record["symbol"],
            record["timeframe"],
            record["provider"],
        ),
    )
    return hashlib.sha256(identity.encode("ascii")).hexdigest()


def build_composite_observation(
    inputs: Sequence[ProviderCandleInput],
    *,
    observation_time: datetime,
    decision_time: datetime,
    method: CompositeMethodDefinition,
    trailing_atr: Decimal | None,
    policy: ReferenceCompositePolicy = DEFAULT_REFERENCE_COMPOSITE_POLICY,
) -> CompositeReferenceObservation:
    """Build one deterministic composite using only inputs available at cutoff."""

    policy.as_record()
    method.as_record()
    timestamp = require_utc_datetime(observation_time, "observation_time")
    cutoff = require_utc_datetime(decision_time, "decision_time")
    expected_cutoff = timestamp + timedelta(hours=1) + policy.decision_delay
    if cutoff != expected_cutoff:
        raise ValueError(
            "decision_time must equal bar close plus the policy decision delay",
        )
    supplied: dict[str, ProviderCandleInput] = {}
    late_provider_ids = []
    for item in inputs:
        item.as_record()
        if item.bar.timestamp != timestamp:
            raise ValueError("all inputs must match observation_time")
        if item.bar.provider in supplied:
            raise ValueError("provider inputs must be unique")
        if item.available_at <= cutoff:
            supplied[item.bar.provider] = item
        else:
            late_provider_ids.append(item.bar.provider)

    ordered_provider_ids = tuple(
        provider_id
        for provider_id in policy.required_provider_ids
        if provider_id in supplied
    )
    available = [supplied[provider_id] for provider_id in ordered_provider_ids]
    bars = [item.bar for item in available]
    diagnostics = _diagnostics(bars, trailing_atr=trailing_atr)
    reason_codes = [
        "COMPOSITE_PROVIDER_LATE" for _ in late_provider_ids
    ]
    quality_state, confirmation_state = _quality_state(
        bars,
        diagnostics=diagnostics,
        trailing_atr=trailing_atr,
        method=method,
        policy=policy,
        reason_codes=reason_codes,
    )
    ohlc: tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]
    if quality_state in (REFERENCE_OK, REFERENCE_DEGRADED):
        try:
            ohlc = _compose_ohlc(
                bars,
                method=method,
                trailing_atr=trailing_atr,
            )
            _validate_candle(*ohlc)
        except ValueError:
            quality_state = VENUE_DISAGREEMENT
            confirmation_state = UNRESOLVED_PROVIDER_DISAGREEMENT
            reason_codes.append("COMPOSITE_CANDLE_INVARIANT_FAILED")
            ohlc = (None, None, None, None)
    else:
        ohlc = (None, None, None, None)
    observation_ids = {
        provider_id: item.observation_id for provider_id, item in supplied.items()
    }
    result = CompositeReferenceObservation(
        reference_policy_version=policy.version,
        observation_time=timestamp,
        available_at=cutoff,
        input_providers_expected=policy.required_provider_ids,
        input_providers_available=ordered_provider_ids,
        bitstamp_observation_id=observation_ids.get(BITSTAMP_PROVIDER_ID),
        coinbase_observation_id=observation_ids.get(COINBASE_PROVIDER_ID),
        bitfinex_observation_id=observation_ids.get(BITFINEX_PROVIDER_ID),
        input_count=len(available),
        composite_method=method.method,
        composite_method_version=method.method_version,
        open=ohlc[0],
        high=ohlc[1],
        low=ohlc[2],
        close=ohlc[3],
        quality_state=quality_state,
        confirmation_state=confirmation_state,
        fallback_used=False,
        diagnostics=diagnostics,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )
    result.as_record()
    return result


def method_definition(
    method_version: str,
    *,
    tolerance_atr: Decimal | str = DEFAULT_CONFIRMATION_TOLERANCE_ATR,
) -> CompositeMethodDefinition:
    tolerance = Decimal(str(tolerance_atr))
    if method_version == MEDIAN_OHLC_VERSION:
        return MEDIAN_OHLC_DEFINITION
    if method_version == CONFIRMED_EXTREMES_VERSION:
        return CompositeMethodDefinition(
            method=CONFIRMED_EXTREMES_METHOD,
            method_version=CONFIRMED_EXTREMES_VERSION,
            confirmation_tolerance_atr=tolerance,
            formula=CONFIRMED_EXTREMES_DEFINITION.formula,
        )
    if method_version == CLIPPED_CENTER_VERSION:
        return CompositeMethodDefinition(
            method=CLIPPED_CENTER_METHOD,
            method_version=CLIPPED_CENTER_VERSION,
            confirmation_tolerance_atr=tolerance,
            formula=CLIPPED_CENTER_DEFINITION.formula,
        )
    raise ValueError("unknown composite method version")


def _quality_state(
    bars: Sequence[OhlcvBar],
    *,
    diagnostics: CompositeDiagnostics,
    trailing_atr: Decimal | None,
    method: CompositeMethodDefinition,
    policy: ReferenceCompositePolicy,
    reason_codes: list[str],
) -> tuple[str, str]:
    count = len(bars)
    if count < policy.minimum_provider_count:
        reason_codes.append("COMPOSITE_INPUT_COUNT_INSUFFICIENT")
        return (
            REFERENCE_UNAVAILABLE,
            SINGLE_PROVIDER_OBSERVATION
            if count == 1
            else UNRESOLVED_PROVIDER_DISAGREEMENT,
        )
    partial_close_consensus = False
    if (
        diagnostics.close_dispersion_bps is not None
        and diagnostics.close_dispersion_bps > policy.close_disagreement_bps
    ):
        if count == 3 and _has_two_provider_close_consensus(
            bars,
            threshold_bps=policy.close_disagreement_bps,
        ):
            partial_close_consensus = True
            reason_codes.append("COMPOSITE_CLOSE_PARTIAL_CONSENSUS")
        else:
            reason_codes.append("COMPOSITE_CLOSE_DISAGREEMENT")
            return VENUE_DISAGREEMENT, UNRESOLVED_PROVIDER_DISAGREEMENT
    if method.confirmation_tolerance_atr is not None and trailing_atr is None:
        reason_codes.append("COMPOSITE_TRAILING_ATR_UNAVAILABLE")
        return REFERENCE_UNAVAILABLE, UNRESOLVED_PROVIDER_DISAGREEMENT
    if count == 2:
        if trailing_atr is None:
            reason_codes.append("COMPOSITE_TRAILING_ATR_UNAVAILABLE")
            return REFERENCE_UNAVAILABLE, UNRESOLVED_PROVIDER_DISAGREEMENT
        if any(
            value is not None
            and value > policy.two_provider_range_disagreement_atr
            for value in (
                diagnostics.high_dispersion_atr,
                diagnostics.low_dispersion_atr,
            )
        ):
            reason_codes.append("COMPOSITE_TWO_PROVIDER_RANGE_DISAGREEMENT")
            return VENUE_DISAGREEMENT, UNRESOLVED_PROVIDER_DISAGREEMENT
        return REFERENCE_DEGRADED, TWO_PROVIDER_CONSENSUS
    if partial_close_consensus:
        return REFERENCE_DEGRADED, TWO_PROVIDER_CONSENSUS
    return REFERENCE_OK, THREE_PROVIDER_CONSENSUS


def _has_two_provider_close_consensus(
    bars: Sequence[OhlcvBar],
    *,
    threshold_bps: Decimal,
) -> bool:
    closes = sorted(bar.close for bar in bars)
    return any(
        (right - left) / _median((left, right)) * Decimal("10000")
        <= threshold_bps
        for left, right in zip(closes, closes[1:])
    )


def _compose_ohlc(
    bars: Sequence[OhlcvBar],
    *,
    method: CompositeMethodDefinition,
    trailing_atr: Decimal | None,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    opens = [bar.open for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    closes = [bar.close for bar in bars]
    if method.method == MEDIAN_OHLC_METHOD:
        return tuple(_median(values) for values in (opens, highs, lows, closes))
    if trailing_atr is None or trailing_atr <= 0:
        raise ValueError("tolerance-based composite requires positive prior ATR")
    tolerance = method.confirmation_tolerance_atr
    if tolerance is None:
        raise ValueError("tolerance-based method is missing tolerance")
    threshold = tolerance * trailing_atr
    if method.method == CONFIRMED_EXTREMES_METHOD:
        return (
            _median(opens),
            _confirmed_high(highs, threshold=threshold),
            _confirmed_low(lows, threshold=threshold),
            _median(closes),
        )
    if method.method == CLIPPED_CENTER_METHOD:
        return tuple(
            _clipped_center(values, threshold=threshold)
            for values in (opens, highs, lows, closes)
        )
    raise ValueError("unsupported composite method")


def _diagnostics(
    bars: Sequence[OhlcvBar],
    *,
    trailing_atr: Decimal | None,
) -> CompositeDiagnostics:
    if len(bars) < 2:
        return CompositeDiagnostics(None, None, None, None)
    closes = [bar.close for bar in bars]
    high_difference = max(bar.high for bar in bars) - min(bar.high for bar in bars)
    low_difference = max(bar.low for bar in bars) - min(bar.low for bar in bars)
    ranges = [bar.high - bar.low for bar in bars]
    atr = trailing_atr if trailing_atr is not None and trailing_atr > 0 else None
    return CompositeDiagnostics(
        close_dispersion_bps=(max(closes) - min(closes)) / _median(closes) * 10000,
        high_dispersion_atr=high_difference / atr if atr is not None else None,
        low_dispersion_atr=low_difference / atr if atr is not None else None,
        range_dispersion_atr=(max(ranges) - min(ranges)) / atr if atr is not None else None,
    )


def _confirmed_high(values: Sequence[Decimal], *, threshold: Decimal) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 2:
        return ordered[-1]
    return ordered[-1] if ordered[-1] - ordered[-2] <= threshold else ordered[-2]


def _confirmed_low(values: Sequence[Decimal], *, threshold: Decimal) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 2:
        return ordered[0]
    return ordered[0] if ordered[1] - ordered[0] <= threshold else ordered[1]


def _clipped_center(values: Sequence[Decimal], *, threshold: Decimal) -> Decimal:
    center = _median(values)
    residuals = [
        min(threshold, max(-threshold, value - center)) for value in values
    ]
    return center + sum(residuals, Decimal("0")) / Decimal(len(residuals))


def _median(values: Sequence[Decimal]) -> Decimal:
    return Decimal(str(median(values)))


def _validate_candle(
    open_price: Decimal | None,
    high: Decimal | None,
    low: Decimal | None,
    close: Decimal | None,
) -> None:
    if any(value is None for value in (open_price, high, low, close)):
        raise ValueError("composite OHLC values must be present")
    if any(value <= 0 for value in (open_price, high, low, close)):
        raise ValueError("composite OHLC values must be positive")
    if high < max(open_price, close) or low > min(open_price, close) or high < low:
        raise ValueError("composite candle has impossible OHLC ordering")


def _optional_decimal(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
