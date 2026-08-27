"""Positioning feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from math import exp
from typing import Any

from btc_predictor.data import FundingRate, OpenInterest, require_utc_datetime


FUNDING_HEALTH_FEATURE_ID = "FUNDING_HEALTH"
FUNDING_7D_AVG_FEATURE_ID = "FUNDING_7D_AVG"
FUNDING_ZSCORE_FEATURE_ID = "FUNDING_ZSCORE_180D"
OI_GROWTH_HEALTH_FEATURE_ID = "OI_GROWTH_HEALTH"
OI_GROWTH_FEATURE_ID = "OI_GROWTH_7D"
OI_GROWTH_ZSCORE_FEATURE_ID = "OI_GROWTH_ZSCORE_180D"
FUNDING_HEALTH_REASON_CODES = (
    "FUNDING_RATE_INPUT_MISSING",
    "FUNDING_HEALTH_INSUFFICIENT_HISTORY",
    "FUNDING_HEALTH_ZERO_VARIANCE",
)
OI_GROWTH_HEALTH_REASON_CODES = (
    "OI_GROWTH_INPUT_MISSING",
    "OI_GROWTH_PRIOR_INPUT_MISSING",
    "OI_GROWTH_INSUFFICIENT_HISTORY",
    "OI_GROWTH_ZERO_VARIANCE",
)
DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS = 7
DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS = 180
DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS = 30
DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE = Decimal("0.25")
DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH = Decimal("1.25")
DEFAULT_OI_GROWTH_WINDOW_DAYS = 7
DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS = 180
DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS = 30
DEFAULT_OI_GROWTH_HEALTH_PREFERRED_ZSCORE = Decimal("0.25")
DEFAULT_OI_GROWTH_HEALTH_ZSCORE_WIDTH = Decimal("1.25")


@dataclass(frozen=True)
class FundingHealthResult:
    feature_id: str
    observation_time: datetime
    average_feature_id: str
    zscore_feature_id: str
    average_window_days: int
    zscore_window_days: int
    min_zscore_observations: int
    preferred_zscore: Decimal
    zscore_width: Decimal
    funding_7d_avg: Decimal | None
    funding_zscore: Decimal | None
    health_score: Decimal | None
    average_window_record_count: int
    history_observation_count: int
    source_record_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "average_feature_id": self.average_feature_id,
            "zscore_feature_id": self.zscore_feature_id,
            "average_window_days": self.average_window_days,
            "zscore_window_days": self.zscore_window_days,
            "min_zscore_observations": self.min_zscore_observations,
            "preferred_zscore": str(self.preferred_zscore),
            "zscore_width": str(self.zscore_width),
            "funding_7d_avg": (
                str(self.funding_7d_avg)
                if self.funding_7d_avg is not None
                else None
            ),
            "funding_zscore": (
                str(self.funding_zscore)
                if self.funding_zscore is not None
                else None
            ),
            "health_score": str(self.health_score) if self.health_score is not None else None,
            "average_window_record_count": self.average_window_record_count,
            "history_observation_count": self.history_observation_count,
            "source_record_count": self.source_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class OpenInterestGrowthHealthResult:
    feature_id: str
    observation_time: datetime
    growth_feature_id: str
    zscore_feature_id: str
    open_interest_unit: str
    growth_window_days: int
    zscore_window_days: int
    min_zscore_observations: int
    preferred_growth_zscore: Decimal
    growth_zscore_width: Decimal
    aggregate_open_interest: Decimal | None
    prior_open_interest: Decimal | None
    oi_growth: Decimal | None
    oi_growth_zscore: Decimal | None
    health_score: Decimal | None
    history_observation_count: int
    source_record_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "growth_feature_id": self.growth_feature_id,
            "zscore_feature_id": self.zscore_feature_id,
            "open_interest_unit": self.open_interest_unit,
            "growth_window_days": self.growth_window_days,
            "zscore_window_days": self.zscore_window_days,
            "min_zscore_observations": self.min_zscore_observations,
            "preferred_growth_zscore": str(self.preferred_growth_zscore),
            "growth_zscore_width": str(self.growth_zscore_width),
            "aggregate_open_interest": (
                str(self.aggregate_open_interest)
                if self.aggregate_open_interest is not None
                else None
            ),
            "prior_open_interest": (
                str(self.prior_open_interest)
                if self.prior_open_interest is not None
                else None
            ),
            "oi_growth": str(self.oi_growth) if self.oi_growth is not None else None,
            "oi_growth_zscore": (
                str(self.oi_growth_zscore)
                if self.oi_growth_zscore is not None
                else None
            ),
            "health_score": str(self.health_score) if self.health_score is not None else None,
            "history_observation_count": self.history_observation_count,
            "source_record_count": self.source_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def funding_health(
    funding_rates: Sequence[FundingRate],
    *,
    as_of: datetime,
    average_window_days: int = DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS,
    zscore_window_days: int = DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS,
    min_zscore_observations: int = DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS,
    preferred_zscore: Decimal = DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE,
    zscore_width: Decimal = DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH,
) -> FundingHealthResult:
    """Calculate funding health from 7-day average and 180-day rolling z-score."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_funding_health_parameters(
        average_window_days=average_window_days,
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        zscore_width=zscore_width,
    )
    available_rows = tuple(
        row
        for row in funding_rates
        if row.as_record()["available_at"] <= signal_time
        and row.as_record()["observation_time"] <= signal_time
    )
    observation_time = (
        max(row.observation_time for row in available_rows)
        if available_rows
        else signal_time
    )
    funding_averages = _funding_averages_by_time(
        available_rows,
        average_window_days=average_window_days,
    )
    funding_7d_avg = funding_averages.get(observation_time)
    average_window_record_count = _funding_window_record_count(
        available_rows,
        observation_time=observation_time,
        average_window_days=average_window_days,
    )

    reason_codes = []
    if not available_rows or funding_7d_avg is None:
        reason_codes.append("FUNDING_RATE_INPUT_MISSING")

    funding_zscore = None
    history = _funding_average_history(
        funding_averages,
        observation_time=observation_time,
        zscore_window_days=zscore_window_days,
    )
    if funding_7d_avg is not None:
        if len(history) < min_zscore_observations:
            reason_codes.append("FUNDING_HEALTH_INSUFFICIENT_HISTORY")
        else:
            funding_zscore = _zscore(funding_7d_avg, history)
            if funding_zscore is None:
                reason_codes.append("FUNDING_HEALTH_ZERO_VARIANCE")

    health_score = (
        _funding_health_score(
            funding_zscore,
            preferred_zscore=preferred_zscore,
            zscore_width=zscore_width,
        )
        if funding_zscore is not None
        else None
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return FundingHealthResult(
        feature_id=FUNDING_HEALTH_FEATURE_ID,
        observation_time=observation_time,
        average_feature_id=FUNDING_7D_AVG_FEATURE_ID,
        zscore_feature_id=FUNDING_ZSCORE_FEATURE_ID,
        average_window_days=average_window_days,
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        preferred_zscore=preferred_zscore,
        zscore_width=zscore_width,
        funding_7d_avg=funding_7d_avg,
        funding_zscore=funding_zscore,
        health_score=health_score,
        average_window_record_count=average_window_record_count,
        history_observation_count=len(history),
        source_record_count=len(available_rows),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def open_interest_growth_health(
    open_interest_rows: Sequence[OpenInterest],
    *,
    as_of: datetime,
    open_interest_unit: str,
    growth_window_days: int = DEFAULT_OI_GROWTH_WINDOW_DAYS,
    zscore_window_days: int = DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS,
    min_zscore_observations: int = DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS,
    preferred_growth_zscore: Decimal = DEFAULT_OI_GROWTH_HEALTH_PREFERRED_ZSCORE,
    growth_zscore_width: Decimal = DEFAULT_OI_GROWTH_HEALTH_ZSCORE_WIDTH,
) -> OpenInterestGrowthHealthResult:
    """Calculate OI growth health from rolling-normalized open-interest growth."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_oi_growth_health_parameters(
        open_interest_unit=open_interest_unit,
        growth_window_days=growth_window_days,
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        growth_zscore_width=growth_zscore_width,
    )
    available_rows = tuple(
        row
        for row in open_interest_rows
        if row.open_interest_unit == open_interest_unit
        and row.as_record()["available_at"] <= signal_time
        and row.as_record()["observation_time"] <= signal_time
    )
    observation_time = (
        max(row.observation_time for row in available_rows)
        if available_rows
        else signal_time
    )
    aggregate_by_time = _aggregate_open_interest_by_time(available_rows)
    aggregate_open_interest = aggregate_by_time.get(observation_time)
    prior_open_interest = _prior_open_interest(
        aggregate_by_time,
        observation_time=observation_time,
        growth_window_days=growth_window_days,
    )
    growth_by_time = _open_interest_growth_by_time(
        aggregate_by_time,
        growth_window_days=growth_window_days,
    )
    oi_growth = growth_by_time.get(observation_time)
    history = _oi_growth_history(
        growth_by_time,
        observation_time=observation_time,
        zscore_window_days=zscore_window_days,
    )

    reason_codes = []
    if not available_rows or aggregate_open_interest is None:
        reason_codes.append("OI_GROWTH_INPUT_MISSING")
    if aggregate_open_interest is not None and oi_growth is None:
        reason_codes.append("OI_GROWTH_PRIOR_INPUT_MISSING")

    oi_growth_zscore = None
    if oi_growth is not None:
        if len(history) < min_zscore_observations:
            reason_codes.append("OI_GROWTH_INSUFFICIENT_HISTORY")
        else:
            oi_growth_zscore = _zscore(oi_growth, history)
            if oi_growth_zscore is None:
                reason_codes.append("OI_GROWTH_ZERO_VARIANCE")

    health_score = (
        _gaussian_health_score(
            oi_growth_zscore,
            preferred_zscore=preferred_growth_zscore,
            zscore_width=growth_zscore_width,
        )
        if oi_growth_zscore is not None
        else None
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return OpenInterestGrowthHealthResult(
        feature_id=OI_GROWTH_HEALTH_FEATURE_ID,
        observation_time=observation_time,
        growth_feature_id=OI_GROWTH_FEATURE_ID,
        zscore_feature_id=OI_GROWTH_ZSCORE_FEATURE_ID,
        open_interest_unit=open_interest_unit,
        growth_window_days=growth_window_days,
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        preferred_growth_zscore=preferred_growth_zscore,
        growth_zscore_width=growth_zscore_width,
        aggregate_open_interest=aggregate_open_interest,
        prior_open_interest=prior_open_interest,
        oi_growth=oi_growth,
        oi_growth_zscore=oi_growth_zscore,
        health_score=health_score,
        history_observation_count=len(history),
        source_record_count=len(available_rows),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def _validate_funding_health_parameters(
    *,
    average_window_days: int,
    zscore_window_days: int,
    min_zscore_observations: int,
    zscore_width: Decimal,
) -> None:
    if average_window_days < 1:
        raise ValueError("average_window_days must be >= 1")
    if zscore_window_days < 1:
        raise ValueError("zscore_window_days must be >= 1")
    if min_zscore_observations < 1:
        raise ValueError("min_zscore_observations must be >= 1")
    if zscore_width <= 0:
        raise ValueError("zscore_width must be > 0")


def _validate_oi_growth_health_parameters(
    *,
    open_interest_unit: str,
    growth_window_days: int,
    zscore_window_days: int,
    min_zscore_observations: int,
    growth_zscore_width: Decimal,
) -> None:
    if not open_interest_unit.strip():
        raise ValueError("open_interest_unit must be non-empty")
    if growth_window_days < 1:
        raise ValueError("growth_window_days must be >= 1")
    if zscore_window_days < 1:
        raise ValueError("zscore_window_days must be >= 1")
    if min_zscore_observations < 1:
        raise ValueError("min_zscore_observations must be >= 1")
    if growth_zscore_width <= 0:
        raise ValueError("growth_zscore_width must be > 0")


def _funding_averages_by_time(
    funding_rates: Sequence[FundingRate],
    *,
    average_window_days: int,
) -> dict[datetime, Decimal]:
    observation_times = tuple(sorted({row.observation_time for row in funding_rates}))
    return {
        observation_time: _average(
            tuple(
                row.funding_rate
                for row in funding_rates
                if _in_trailing_day_window(
                    row.observation_time,
                    observation_time=observation_time,
                    window_days=average_window_days,
                )
            )
        )
        for observation_time in observation_times
    }


def _funding_window_record_count(
    funding_rates: Sequence[FundingRate],
    *,
    observation_time: datetime,
    average_window_days: int,
) -> int:
    return sum(
        1
        for row in funding_rates
        if _in_trailing_day_window(
            row.observation_time,
            observation_time=observation_time,
            window_days=average_window_days,
        )
    )


def _funding_average_history(
    funding_averages: dict[datetime, Decimal],
    *,
    observation_time: datetime,
    zscore_window_days: int,
) -> tuple[Decimal, ...]:
    window_start = observation_time - timedelta(days=zscore_window_days)
    return tuple(
        average
        for historical_time, average in sorted(funding_averages.items())
        if window_start <= historical_time < observation_time
    )


def _in_trailing_day_window(
    candidate_time: datetime,
    *,
    observation_time: datetime,
    window_days: int,
) -> bool:
    window_start = observation_time - timedelta(days=window_days)
    return window_start < candidate_time <= observation_time


def _aggregate_open_interest_by_time(
    open_interest_rows: Sequence[OpenInterest],
) -> dict[datetime, Decimal]:
    aggregate_by_time: dict[datetime, Decimal] = {}
    for row in open_interest_rows:
        record = row.as_record()
        observation_time = record["observation_time"]
        aggregate_by_time[observation_time] = (
            aggregate_by_time.get(observation_time, Decimal("0"))
            + record["open_interest"]
        )
    return aggregate_by_time


def _prior_open_interest(
    aggregate_by_time: dict[datetime, Decimal],
    *,
    observation_time: datetime,
    growth_window_days: int,
) -> Decimal | None:
    cutoff = observation_time - timedelta(days=growth_window_days)
    prior_times = tuple(time for time in aggregate_by_time if time <= cutoff)
    if not prior_times:
        return None
    return aggregate_by_time[max(prior_times)]


def _open_interest_growth_by_time(
    aggregate_by_time: dict[datetime, Decimal],
    *,
    growth_window_days: int,
) -> dict[datetime, Decimal | None]:
    growth_by_time = {}
    for observation_time, aggregate_open_interest in sorted(aggregate_by_time.items()):
        prior = _prior_open_interest(
            aggregate_by_time,
            observation_time=observation_time,
            growth_window_days=growth_window_days,
        )
        growth_by_time[observation_time] = (
            (aggregate_open_interest / prior) - Decimal("1")
            if prior is not None and prior != 0
            else None
        )
    return growth_by_time


def _oi_growth_history(
    growth_by_time: dict[datetime, Decimal | None],
    *,
    observation_time: datetime,
    zscore_window_days: int,
) -> tuple[Decimal, ...]:
    window_start = observation_time - timedelta(days=zscore_window_days)
    return tuple(
        growth
        for historical_time, growth in sorted(growth_by_time.items())
        if growth is not None and window_start <= historical_time < observation_time
    )


def _zscore(value: Decimal, history: Sequence[Decimal]) -> Decimal | None:
    mean = _average(history)
    variance = sum(((item - mean) ** 2 for item in history), Decimal("0")) / Decimal(
        len(history)
    )
    volatility = variance.sqrt()
    if volatility == 0:
        return None
    return (value - mean) / volatility


def _funding_health_score(
    funding_zscore: Decimal,
    *,
    preferred_zscore: Decimal,
    zscore_width: Decimal,
) -> Decimal:
    return _gaussian_health_score(
        funding_zscore,
        preferred_zscore=preferred_zscore,
        zscore_width=zscore_width,
    )


def _gaussian_health_score(
    zscore: Decimal,
    *,
    preferred_zscore: Decimal,
    zscore_width: Decimal,
) -> Decimal:
    scaled_distance = (zscore - preferred_zscore) / zscore_width
    return Decimal(str(100 * exp(-0.5 * (float(scaled_distance) ** 2))))


def _average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("values must contain at least one observation")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _dedupe_reason_codes(reason_codes: Sequence[str]) -> tuple[str, ...]:
    deduped = []
    for reason_code in reason_codes:
        if reason_code not in deduped:
            deduped.append(reason_code)
    return tuple(deduped)
