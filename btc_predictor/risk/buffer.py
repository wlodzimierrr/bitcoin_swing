"""Volatility buffer for structural stops (BTC-141).

Rulebook 16.1 places the stop a volatility buffer beyond the structural
invalidation level:

    Stop = StructuralInvalidation -/+ VolatilityBuffer

with the initial research formula

    Buffer = max(0.3 * ATR_20, LevelNoiseEstimate)

This module produces the buffer distance only. Selecting the invalidation level
is BTC-140 and applying the buffer to reach a stop is BTC-142.

Specification note
------------------
``LevelNoiseEstimate`` is named once in the rulebook and never defined. The
approved Phase-1 interpretation is ``LEVEL_NOISE_ESTIMATE_V1``:

    LevelNoiseEstimate = 0.5 * (zone_upper_bound - zone_lower_bound)

i.e. how far price may wander around the level and still be inside the same
structure. It is a provisional reading of an underspecified term rather than a
rulebook formula, carries a version so BTC-185 can challenge it, and is applied
in exactly one place: :func:`volatility_buffer_for_invalidation`, the canonical
strategy path from a BTC-140 selection to a buffer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.quant.comparisons import decision_greater_equal, decision_less_equal
from btc_predictor.quant.rolling import average_true_range


VOLATILITY_BUFFER_FEATURE_ID = "VOLATILITY_BUFFER"
VOLATILITY_BUFFER_POLICY_VERSION = "VOLATILITY_BUFFER_V1"

# Rulebook 16.1 initial research formula.
DEFAULT_BUFFER_ATR_MULTIPLIER = Decimal("0.30")
DEFAULT_BUFFER_ATR_WINDOW_DAYS = 20
# The rulebook's declared robustness grid. Exposed so BTC-185 can sweep it;
# deliberately NOT calibrated here. The exact value must be backtested.
BUFFER_ATR_MULTIPLIER_GRID = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("0.75"),
)
BUFFER_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

ATR_BOUND = "ATR"
LEVEL_NOISE_BOUND = "LEVEL_NOISE"
BUFFER_BINDING_TERMS = (ATR_BOUND, LEVEL_NOISE_BOUND)

# The approved Phase-1 interpretation of the rulebook's undefined
# LevelNoiseEstimate term. BTC-142 needs exactly one deterministic reading;
# BTC-185 may challenge the definition, which is why it carries a version.
LEVEL_NOISE_ESTIMATE_VERSION = "LEVEL_NOISE_ESTIMATE_V1"
LEVEL_NOISE_ESTIMATE_FORMULA = "0.5 * (zone_upper_bound - zone_lower_bound)"
LEVEL_NOISE_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

# How the level-noise term reached the buffer. Distinguishing these keeps an
# integration defect from looking like a legitimate ATR-only fallback.
LEVEL_NOISE_DERIVED_FROM_ZONE = "DERIVED_FROM_ZONE"
LEVEL_NOISE_EXPLICITLY_SUPPLIED = "EXPLICITLY_SUPPLIED"
LEVEL_NOISE_UNAVAILABLE = "UNAVAILABLE"
LEVEL_NOISE_SOURCES = (
    LEVEL_NOISE_DERIVED_FROM_ZONE,
    LEVEL_NOISE_EXPLICITLY_SUPPLIED,
    LEVEL_NOISE_UNAVAILABLE,
)

VOLATILITY_BUFFER_REASON_CODES = (
    "VOLATILITY_BUFFER_COMPLETE",
    "VOLATILITY_BUFFER_INPUT_MISSING",
    "VOLATILITY_BUFFER_ATR_BOUND",
    "VOLATILITY_BUFFER_LEVEL_NOISE_BOUND",
    "VOLATILITY_BUFFER_LEVEL_NOISE_UNAVAILABLE",
    "VOLATILITY_BUFFER_LEVEL_NOISE_DERIVED",
    "VOLATILITY_BUFFER_LEVEL_NOISE_NOT_DERIVED",
)


@dataclass(frozen=True)
class VolatilityBufferResult:
    feature_id: str
    policy_version: str
    buffer: Decimal | None
    atr: Decimal | None
    atr_window: int
    atr_multiplier: Decimal
    atr_component: Decimal | None
    level_noise_estimate: Decimal | None
    level_noise_version: str
    level_noise_source: str
    zone_lower_bound: Decimal | None
    zone_upper_bound: Decimal | None
    binding_term: str | None
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.buffer is None:
            raise ValueError("complete volatility buffer requires a buffer")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "buffer": str(self.buffer) if self.buffer is not None else None,
            "atr": str(self.atr) if self.atr is not None else None,
            "atr_window": self.atr_window,
            "atr_multiplier": str(self.atr_multiplier),
            "atr_component": (
                str(self.atr_component) if self.atr_component is not None else None
            ),
            "level_noise_estimate": (
                str(self.level_noise_estimate)
                if self.level_noise_estimate is not None
                else None
            ),
            "level_noise_version": self.level_noise_version,
            "level_noise_source": self.level_noise_source,
            "zone_lower_bound": (
                str(self.zone_lower_bound)
                if self.zone_lower_bound is not None
                else None
            ),
            "zone_upper_bound": (
                str(self.zone_upper_bound)
                if self.zone_upper_bound is not None
                else None
            ),
            "binding_term": self.binding_term,
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_volatility_buffer(
    *,
    atr: Any | None,
    level_noise_estimate: Any | None = None,
    atr_multiplier: Any = DEFAULT_BUFFER_ATR_MULTIPLIER,
    atr_window: int = DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    level_noise_source: str = LEVEL_NOISE_EXPLICITLY_SUPPLIED,
    zone_lower_bound: Any | None = None,
    zone_upper_bound: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> VolatilityBufferResult:
    """Return ``max(atr_multiplier * ATR, LevelNoiseEstimate)``.

    ``atr_window`` labels which ATR identity the supplied value carries. It is
    provenance only -- this function never computes an ATR -- but recording it
    stops an unlabeled value from later being assumed to be ATR20.

    A missing ATR makes the buffer incomplete rather than zero: a stop must
    never be placed using a silently absent volatility term. A missing level
    noise estimate degenerates the maximum to the ATR term, and
    ``level_noise_source`` records whether that absence was genuine.

    Prefer :func:`volatility_buffer_for_invalidation` on the strategy path so
    the level-noise definition is applied in exactly one place.
    """

    multiplier = _non_negative_decimal(atr_multiplier, "atr_multiplier")
    window = int(atr_window)
    if window < 1:
        raise ValueError("atr_window must be >= 1")
    if level_noise_source not in LEVEL_NOISE_SOURCES:
        raise ValueError(f"level_noise_source must be one of {LEVEL_NOISE_SOURCES}")
    metadata = dict(config_metadata or {})
    noise = (
        _non_negative_decimal(level_noise_estimate, "level_noise_estimate")
        if level_noise_estimate is not None
        else None
    )
    lower = (
        _positive_decimal(zone_lower_bound, "zone_lower_bound")
        if zone_lower_bound is not None
        else None
    )
    upper = (
        _positive_decimal(zone_upper_bound, "zone_upper_bound")
        if zone_upper_bound is not None
        else None
    )
    # A bounded zone that reached here without a derived noise term is an
    # integration defect, not a legitimate ATR-only fallback.
    zone_without_noise = noise is None and lower is not None and upper is not None
    source = LEVEL_NOISE_UNAVAILABLE if noise is None else level_noise_source

    if atr is None or zone_without_noise:
        return VolatilityBufferResult(
            feature_id=VOLATILITY_BUFFER_FEATURE_ID,
            policy_version=VOLATILITY_BUFFER_POLICY_VERSION,
            buffer=None,
            atr=None if atr is None else _positive_decimal(atr, "atr"),
            atr_window=window,
            atr_multiplier=multiplier,
            atr_component=None,
            level_noise_estimate=noise,
            level_noise_version=LEVEL_NOISE_ESTIMATE_VERSION,
            level_noise_source=source,
            zone_lower_bound=lower,
            zone_upper_bound=upper,
            binding_term=None,
            config_metadata=metadata,
            complete=False,
            reason_codes=(
                ("VOLATILITY_BUFFER_LEVEL_NOISE_NOT_DERIVED",)
                if zone_without_noise
                else ("VOLATILITY_BUFFER_INPUT_MISSING",)
            ),
        )

    atr_value = _positive_decimal(atr, "atr")
    atr_component = multiplier * atr_value

    reason_codes = []
    if noise is None:
        reason_codes.append("VOLATILITY_BUFFER_LEVEL_NOISE_UNAVAILABLE")
        buffer = atr_component
        binding = ATR_BOUND
    else:
        if source == LEVEL_NOISE_DERIVED_FROM_ZONE:
            reason_codes.append("VOLATILITY_BUFFER_LEVEL_NOISE_DERIVED")
        if decision_greater_equal(atr_component, noise):
            buffer = atr_component
            binding = ATR_BOUND
        else:
            buffer = noise
            binding = LEVEL_NOISE_BOUND
    reason_codes.append(
        "VOLATILITY_BUFFER_ATR_BOUND"
        if binding == ATR_BOUND
        else "VOLATILITY_BUFFER_LEVEL_NOISE_BOUND"
    )
    reason_codes.append("VOLATILITY_BUFFER_COMPLETE")

    return VolatilityBufferResult(
        feature_id=VOLATILITY_BUFFER_FEATURE_ID,
        policy_version=VOLATILITY_BUFFER_POLICY_VERSION,
        buffer=buffer,
        atr=atr_value,
        atr_window=window,
        atr_multiplier=multiplier,
        atr_component=atr_component,
        level_noise_estimate=noise,
        level_noise_version=LEVEL_NOISE_ESTIMATE_VERSION,
        level_noise_source=source,
        zone_lower_bound=lower,
        zone_upper_bound=upper,
        binding_term=binding,
        config_metadata=metadata,
        complete=True,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


def volatility_buffer_for_invalidation(
    invalidation: Any,
    *,
    atr: Any | None,
    atr_multiplier: Any = DEFAULT_BUFFER_ATR_MULTIPLIER,
    atr_window: int = DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    config_metadata: Mapping[str, str] | None = None,
) -> VolatilityBufferResult:
    """Canonical Phase-1 path from a BTC-140 selection to a buffer.

    Advisory, paper trading and backtesting must all enter here so the
    LevelNoiseEstimate definition is applied in exactly one place:

        BTC-140 selected zone -> LEVEL_NOISE_ESTIMATE_V1 -> BTC-141 buffer

    When the selection carries a bounded zone the noise term is always derived
    from it. ATR-only is used only when the selection genuinely has no usable
    zone width, and that state is recorded explicitly.
    """

    record = _invalidation_record(invalidation)
    lower = record.get("selected_zone_lower_bound")
    upper = record.get("selected_zone_upper_bound")

    if lower is None or upper is None:
        # Genuinely no usable structure: an explicitly diagnosed ATR-only
        # fallback, not a silent degradation.
        return calculate_volatility_buffer(
            atr=atr,
            level_noise_estimate=None,
            atr_multiplier=atr_multiplier,
            atr_window=atr_window,
            level_noise_source=LEVEL_NOISE_UNAVAILABLE,
            config_metadata=config_metadata,
        )

    noise = level_noise_from_zone(lower_bound=lower, upper_bound=upper)
    return calculate_volatility_buffer(
        atr=atr,
        level_noise_estimate=noise,
        atr_multiplier=atr_multiplier,
        atr_window=atr_window,
        level_noise_source=LEVEL_NOISE_DERIVED_FROM_ZONE,
        zone_lower_bound=lower,
        zone_upper_bound=upper,
        config_metadata=config_metadata,
    )


def _invalidation_record(invalidation: Any) -> Mapping[str, Any]:
    if isinstance(invalidation, Mapping):
        return invalidation
    as_record = getattr(invalidation, "as_record", None)
    if callable(as_record):
        return as_record()
    raise TypeError("invalidation must be a mapping or expose as_record()")


def volatility_buffer_grid(
    *,
    atr: Any | None,
    level_noise_estimate: Any | None = None,
    multipliers: Sequence[Any] = BUFFER_ATR_MULTIPLIER_GRID,
    atr_window: int = DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    config_metadata: Mapping[str, str] | None = None,
) -> dict[str, VolatilityBufferResult]:
    """Evaluate the buffer across the declared ATR-multiplier research grid.

    BTC-185 sweeps this; it does not select a winner here.
    """

    return {
        str(_non_negative_decimal(multiplier, "atr_multiplier")): (
            calculate_volatility_buffer(
                atr=atr,
                level_noise_estimate=level_noise_estimate,
                atr_multiplier=multiplier,
                atr_window=atr_window,
                config_metadata=config_metadata,
            )
        )
        for multiplier in multipliers
    }


def level_noise_from_zone(
    *,
    lower_bound: Any,
    upper_bound: Any,
) -> Decimal:
    """Provisional LevelNoiseEstimate: half the structural zone width.

    The rulebook names ``LevelNoiseEstimate`` without defining it. A structural
    zone's width is how far price may wander and still sit on the same level,
    so half that width is the distance from the zone edge to its centre. This
    is an explicit Phase-1 interpretation, not a rulebook formula.
    """

    lower = _positive_decimal(lower_bound, "lower_bound")
    upper = _positive_decimal(upper_bound, "upper_bound")
    if decision_less_equal(upper, lower) and upper != lower:
        raise ValueError("upper_bound must be >= lower_bound")
    return (upper - lower) / Decimal("2")


def atr_from_daily_bars(
    highs: Sequence[Any],
    lows: Sequence[Any],
    closes: Sequence[Any],
    *,
    window: int = DEFAULT_BUFFER_ATR_WINDOW_DAYS,
) -> Decimal | None:
    """Latest ATR over ``window`` completed daily bars, or None while warming up.

    Delegates the rolling arithmetic to the BTC-043 float64 primitive and
    returns a Decimal at this boundary.
    """

    if window < 1:
        raise ValueError("window must be >= 1")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("high, low and close series must be the same length")
    if len(closes) <= window:
        return None
    values = average_true_range(
        [float(value) for value in highs],
        [float(value) for value in lows],
        [float(value) for value in closes],
        window=window,
        nan_policy="propagate",
    )
    latest = values[-1]
    if latest != latest:  # NaN while the window is incomplete
        return None
    return Decimal(str(float(latest)))


def _decimal(value: Any, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result
