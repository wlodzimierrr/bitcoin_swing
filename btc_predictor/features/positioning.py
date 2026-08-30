"""Positioning feature helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import (
    FundingRate,
    FuturesBasis,
    OpenInterest,
    require_utc_datetime,
)
from btc_predictor.features._scoring import decimal_weighted_score
from btc_predictor.quant.transforms import gaussian_health, percentile_to_health


FUNDING_HEALTH_FEATURE_ID = "FUNDING_HEALTH"
FUNDING_7D_AVG_FEATURE_ID = "FUNDING_7D_AVG"
FUNDING_ZSCORE_FEATURE_ID = "FUNDING_ZSCORE_180D"
FUTURES_BASIS_HEALTH_FEATURE_ID = "FUTURES_BASIS_HEALTH"
FUTURES_BASIS_AVG_FEATURE_ID = "FUTURES_BASIS_AVG"
FUTURES_BASIS_ZSCORE_FEATURE_ID = "FUTURES_BASIS_ZSCORE_180D"
OI_GROWTH_HEALTH_FEATURE_ID = "OI_GROWTH_HEALTH"
OI_GROWTH_FEATURE_ID = "OI_GROWTH_7D"
OI_GROWTH_ZSCORE_FEATURE_ID = "OI_GROWTH_ZSCORE_180D"
OI_INTENSITY_FEATURE_ID = "OI_INTENSITY"
OI_INTENSITY_PERCENTILE_FEATURE_ID = "OI_INTENSITY_PERCENTILE_180D"
POSITIONING_SCORE_FEATURE_ID = "POSITIONING_SCORE"
CROWDING_FLAG_FEATURE_ID = "CROWDING"
CROWDING_FLAG_EFFECTS = (
    "NO_ADD",
    "REDUCE_ENTRY_QUALITY",
    "OPTIONAL_TIGHTER_PROFIT_PROTECTION",
)
POSITIONING_SCORE_COMPONENT_IDS = (
    "funding_health",
    "oi_health",
    "basis_health",
    "leverage_health",
)
DEFAULT_POSITIONING_SCORE_WEIGHTS = {
    "funding_health": Decimal("0.35"),
    "oi_health": Decimal("0.30"),
    "basis_health": Decimal("0.20"),
    "leverage_health": Decimal("0.15"),
}
FUNDING_HEALTH_REASON_CODES = (
    "FUNDING_RATE_INPUT_MISSING",
    "FUNDING_HEALTH_INSUFFICIENT_HISTORY",
    "FUNDING_HEALTH_ZERO_VARIANCE",
)
FUTURES_BASIS_HEALTH_REASON_CODES = (
    "FUTURES_BASIS_INPUT_MISSING",
    "FUTURES_BASIS_INSUFFICIENT_HISTORY",
    "FUTURES_BASIS_ZERO_VARIANCE",
)
OI_GROWTH_HEALTH_REASON_CODES = (
    "OI_GROWTH_INPUT_MISSING",
    "OI_GROWTH_PRIOR_INPUT_MISSING",
    "OI_GROWTH_INSUFFICIENT_HISTORY",
    "OI_GROWTH_ZERO_VARIANCE",
)
OI_INTENSITY_REASON_CODES = (
    "OI_INTENSITY_OI_INPUT_MISSING",
    "OI_INTENSITY_MARKET_CAP_INPUT_MISSING",
    "OI_INTENSITY_INSUFFICIENT_HISTORY",
)
POSITIONING_SCORE_REASON_CODES = (
    "POSITIONING_SCORE_INPUT_MISSING",
)
CROWDING_FLAG_REASON_CODES = (
    "CROWDING_FUNDING_EXCESS",
    "CROWDING_BASIS_EXCESS",
    "CROWDING_LEVERAGE_EXCESS",
    "CROWDING_INPUT_MISSING",
)
DEFAULT_FUNDING_AVERAGE_WINDOW_DAYS = 7
DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS = 180
DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS = 30
DEFAULT_FUNDING_HEALTH_PREFERRED_ZSCORE = Decimal("0.25")
DEFAULT_FUNDING_HEALTH_ZSCORE_WIDTH = Decimal("1.25")
DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS = 180
DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS = 30
DEFAULT_FUTURES_BASIS_HEALTH_PREFERRED_ZSCORE = Decimal("0.25")
DEFAULT_FUTURES_BASIS_HEALTH_ZSCORE_WIDTH = Decimal("1.25")
DEFAULT_OI_GROWTH_WINDOW_DAYS = 7
DEFAULT_OI_GROWTH_ZSCORE_WINDOW_DAYS = 180
DEFAULT_OI_GROWTH_MIN_ZSCORE_OBSERVATIONS = 30
DEFAULT_OI_GROWTH_HEALTH_PREFERRED_ZSCORE = Decimal("0.25")
DEFAULT_OI_GROWTH_HEALTH_ZSCORE_WIDTH = Decimal("1.25")
DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS = 180
DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS = 30
DEFAULT_CROWDING_FUNDING_ZSCORE_MIN = Decimal("2")
DEFAULT_CROWDING_BASIS_ZSCORE_MIN = Decimal("2")
DEFAULT_CROWDING_OI_INTENSITY_PERCENTILE_MIN = Decimal("90")
DEFAULT_CROWDING_ENTRY_QUALITY_PENALTY = Decimal("10")


@dataclass(frozen=True)
class MarketCapObservation:
    observation_time: datetime
    market_cap_usd: Decimal
    provider: str
    available_at: datetime

    def as_record(self) -> dict[str, Any]:
        observation_time = require_utc_datetime(
            self.observation_time,
            "observation_time",
        )
        available_at = require_utc_datetime(self.available_at, "available_at")
        if self.market_cap_usd <= 0:
            raise ValueError("market_cap_usd must be > 0")
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        return {
            "observation_time": observation_time,
            "market_cap_usd": self.market_cap_usd,
            "provider": self.provider,
            "available_at": available_at,
        }


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
class FuturesBasisHealthResult:
    feature_id: str
    observation_time: datetime
    average_feature_id: str
    zscore_feature_id: str
    zscore_window_days: int
    min_zscore_observations: int
    preferred_basis_zscore: Decimal
    basis_zscore_width: Decimal
    basis_rate_avg: Decimal | None
    annualized_basis_rate_avg: Decimal | None
    annualized_basis_zscore: Decimal | None
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
            "average_feature_id": self.average_feature_id,
            "zscore_feature_id": self.zscore_feature_id,
            "zscore_window_days": self.zscore_window_days,
            "min_zscore_observations": self.min_zscore_observations,
            "preferred_basis_zscore": str(self.preferred_basis_zscore),
            "basis_zscore_width": str(self.basis_zscore_width),
            "basis_rate_avg": (
                str(self.basis_rate_avg) if self.basis_rate_avg is not None else None
            ),
            "annualized_basis_rate_avg": (
                str(self.annualized_basis_rate_avg)
                if self.annualized_basis_rate_avg is not None
                else None
            ),
            "annualized_basis_zscore": (
                str(self.annualized_basis_zscore)
                if self.annualized_basis_zscore is not None
                else None
            ),
            "health_score": str(self.health_score) if self.health_score is not None else None,
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


@dataclass(frozen=True)
class OpenInterestIntensityResult:
    feature_id: str
    observation_time: datetime
    percentile_feature_id: str
    open_interest_unit: str
    percentile_window_days: int
    min_percentile_observations: int
    aggregate_open_interest: Decimal | None
    market_cap_usd: Decimal | None
    oi_intensity: Decimal | None
    oi_intensity_percentile: Decimal | None
    health_score: Decimal | None
    history_observation_count: int
    open_interest_record_count: int
    market_cap_record_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ).isoformat(),
            "percentile_feature_id": self.percentile_feature_id,
            "open_interest_unit": self.open_interest_unit,
            "percentile_window_days": self.percentile_window_days,
            "min_percentile_observations": self.min_percentile_observations,
            "aggregate_open_interest": (
                str(self.aggregate_open_interest)
                if self.aggregate_open_interest is not None
                else None
            ),
            "market_cap_usd": (
                str(self.market_cap_usd) if self.market_cap_usd is not None else None
            ),
            "oi_intensity": (
                str(self.oi_intensity) if self.oi_intensity is not None else None
            ),
            "oi_intensity_percentile": (
                str(self.oi_intensity_percentile)
                if self.oi_intensity_percentile is not None
                else None
            ),
            "health_score": str(self.health_score) if self.health_score is not None else None,
            "history_observation_count": self.history_observation_count,
            "open_interest_record_count": self.open_interest_record_count,
            "market_cap_record_count": self.market_cap_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class PositioningScoreInput:
    funding_health: Decimal | None
    oi_health: Decimal | None
    basis_health: Decimal | None
    leverage_health: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "funding_health": (
                str(self.funding_health) if self.funding_health is not None else None
            ),
            "oi_health": str(self.oi_health) if self.oi_health is not None else None,
            "basis_health": (
                str(self.basis_health) if self.basis_health is not None else None
            ),
            "leverage_health": (
                str(self.leverage_health) if self.leverage_health is not None else None
            ),
        }


@dataclass(frozen=True)
class PositioningScoreResult:
    feature_id: str
    score: Decimal | None
    interpretation: str | None
    inputs: PositioningScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.interpretation is None:
            return None
        return f"{self.feature_id}_{self.interpretation}"

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "contributions": {
                key: str(value) if value is not None else None
                for key, value in self.contributions.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class CrowdingFlagInput:
    funding_zscore: Decimal | None
    basis_zscore: Decimal | None
    oi_intensity_percentile: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "funding_zscore": (
                str(self.funding_zscore) if self.funding_zscore is not None else None
            ),
            "basis_zscore": (
                str(self.basis_zscore) if self.basis_zscore is not None else None
            ),
            "oi_intensity_percentile": (
                str(self.oi_intensity_percentile)
                if self.oi_intensity_percentile is not None
                else None
            ),
        }


@dataclass(frozen=True)
class CrowdingFlagResult:
    feature_id: str
    flagged: bool
    effects: tuple[str, ...]
    entry_quality_penalty: Decimal
    funding_zscore_min: Decimal
    basis_zscore_min: Decimal
    oi_intensity_percentile_min: Decimal
    inputs: CrowdingFlagInput
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "flagged": self.flagged,
            "effects": list(self.effects),
            "entry_quality_penalty": str(self.entry_quality_penalty),
            "funding_zscore_min": str(self.funding_zscore_min),
            "basis_zscore_min": str(self.basis_zscore_min),
            "oi_intensity_percentile_min": str(self.oi_intensity_percentile_min),
            "inputs": self.inputs.as_record(),
            "config_metadata": dict(self.config_metadata),
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


def futures_basis_health(
    futures_basis_rows: Sequence[FuturesBasis],
    *,
    as_of: datetime,
    zscore_window_days: int = DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS,
    min_zscore_observations: int = DEFAULT_FUTURES_BASIS_MIN_ZSCORE_OBSERVATIONS,
    preferred_basis_zscore: Decimal = DEFAULT_FUTURES_BASIS_HEALTH_PREFERRED_ZSCORE,
    basis_zscore_width: Decimal = DEFAULT_FUTURES_BASIS_HEALTH_ZSCORE_WIDTH,
) -> FuturesBasisHealthResult:
    """Calculate futures-basis health from annualized basis rolling z-score."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_futures_basis_health_parameters(
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        basis_zscore_width=basis_zscore_width,
    )
    available_rows = tuple(
        row
        for row in futures_basis_rows
        if row.as_record()["available_at"] <= signal_time
        and row.as_record()["observation_time"] <= signal_time
    )
    observation_time = (
        max(row.observation_time for row in available_rows)
        if available_rows
        else signal_time
    )
    averages_by_time = _futures_basis_averages_by_time(available_rows)
    current_average = averages_by_time.get(observation_time)
    basis_rate_avg = current_average[0] if current_average is not None else None
    annualized_basis_rate_avg = current_average[1] if current_average is not None else None

    reason_codes = []
    if not available_rows or annualized_basis_rate_avg is None:
        reason_codes.append("FUTURES_BASIS_INPUT_MISSING")

    history = _futures_basis_history(
        averages_by_time,
        observation_time=observation_time,
        zscore_window_days=zscore_window_days,
    )
    annualized_basis_zscore = None
    if annualized_basis_rate_avg is not None:
        if len(history) < min_zscore_observations:
            reason_codes.append("FUTURES_BASIS_INSUFFICIENT_HISTORY")
        else:
            annualized_basis_zscore = _zscore(annualized_basis_rate_avg, history)
            if annualized_basis_zscore is None:
                reason_codes.append("FUTURES_BASIS_ZERO_VARIANCE")

    health_score = (
        _gaussian_health_score(
            annualized_basis_zscore,
            preferred_zscore=preferred_basis_zscore,
            zscore_width=basis_zscore_width,
        )
        if annualized_basis_zscore is not None
        else None
    )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return FuturesBasisHealthResult(
        feature_id=FUTURES_BASIS_HEALTH_FEATURE_ID,
        observation_time=observation_time,
        average_feature_id=FUTURES_BASIS_AVG_FEATURE_ID,
        zscore_feature_id=FUTURES_BASIS_ZSCORE_FEATURE_ID,
        zscore_window_days=zscore_window_days,
        min_zscore_observations=min_zscore_observations,
        preferred_basis_zscore=preferred_basis_zscore,
        basis_zscore_width=basis_zscore_width,
        basis_rate_avg=basis_rate_avg,
        annualized_basis_rate_avg=annualized_basis_rate_avg,
        annualized_basis_zscore=annualized_basis_zscore,
        health_score=health_score,
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


def open_interest_intensity(
    open_interest_rows: Sequence[OpenInterest],
    market_caps: Sequence[MarketCapObservation],
    *,
    as_of: datetime,
    open_interest_unit: str,
    percentile_window_days: int = DEFAULT_OI_INTENSITY_PERCENTILE_WINDOW_DAYS,
    min_percentile_observations: int = DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS,
) -> OpenInterestIntensityResult:
    """Calculate OI intensity and its rolling historical percentile."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_oi_intensity_parameters(
        open_interest_unit=open_interest_unit,
        percentile_window_days=percentile_window_days,
        min_percentile_observations=min_percentile_observations,
    )
    available_oi_rows = tuple(
        row
        for row in open_interest_rows
        if row.open_interest_unit == open_interest_unit
        and row.as_record()["available_at"] <= signal_time
        and row.as_record()["observation_time"] <= signal_time
    )
    available_market_caps = tuple(
        row
        for row in market_caps
        if row.as_record()["available_at"] <= signal_time
        and row.as_record()["observation_time"] <= signal_time
    )
    aggregate_by_time = _aggregate_open_interest_by_time(available_oi_rows)
    market_cap_by_time = _market_cap_by_time(available_market_caps)
    intensity_by_time = _open_interest_intensity_by_time(
        aggregate_by_time,
        market_cap_by_time,
    )
    observation_time = _latest_intensity_observation_time(
        intensity_by_time,
        aggregate_by_time,
        market_cap_by_time,
        signal_time=signal_time,
    )
    aggregate_open_interest = aggregate_by_time.get(observation_time)
    market_cap_usd = market_cap_by_time.get(observation_time)
    oi_intensity = intensity_by_time.get(observation_time)
    history = _oi_intensity_history(
        intensity_by_time,
        observation_time=observation_time,
        percentile_window_days=percentile_window_days,
    )

    reason_codes = []
    if aggregate_open_interest is None:
        reason_codes.append("OI_INTENSITY_OI_INPUT_MISSING")
    if market_cap_usd is None:
        reason_codes.append("OI_INTENSITY_MARKET_CAP_INPUT_MISSING")

    oi_intensity_percentile = None
    if oi_intensity is not None:
        if len(history) < min_percentile_observations:
            reason_codes.append("OI_INTENSITY_INSUFFICIENT_HISTORY")
        else:
            oi_intensity_percentile = _percentile_rank(oi_intensity, history)

    health_score = None
    if oi_intensity_percentile is not None:
        health_score = Decimal(
            str(percentile_to_health(float(oi_intensity_percentile)))
        )
    reason_codes = _dedupe_reason_codes(reason_codes)
    return OpenInterestIntensityResult(
        feature_id=OI_INTENSITY_FEATURE_ID,
        observation_time=observation_time,
        percentile_feature_id=OI_INTENSITY_PERCENTILE_FEATURE_ID,
        open_interest_unit=open_interest_unit,
        percentile_window_days=percentile_window_days,
        min_percentile_observations=min_percentile_observations,
        aggregate_open_interest=aggregate_open_interest,
        market_cap_usd=market_cap_usd,
        oi_intensity=oi_intensity,
        oi_intensity_percentile=oi_intensity_percentile,
        health_score=health_score,
        history_observation_count=len(history),
        open_interest_record_count=len(available_oi_rows),
        market_cap_record_count=len(available_market_caps),
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def calculate_positioning_score(
    inputs: PositioningScoreInput,
    *,
    weights: dict[str, Any] | None = None,
    config_metadata: dict[str, str] | None = None,
) -> PositioningScoreResult:
    """Calculate the rulebook positioning score from health components."""

    selected_weights = _positioning_score_weights(weights)
    input_values = _positioning_score_input_values(inputs)
    missing_components = [
        component_id
        for component_id in POSITIONING_SCORE_COMPONENT_IDS
        if input_values[component_id] is None
    ]
    reason_codes = []
    if missing_components:
        reason_codes.append("POSITIONING_SCORE_INPUT_MISSING")

    weighted = decimal_weighted_score(
        input_values,
        selected_weights,
        component_ids=POSITIONING_SCORE_COMPONENT_IDS,
    )
    contributions = weighted.contributions
    score = weighted.score
    return PositioningScoreResult(
        feature_id=POSITIONING_SCORE_FEATURE_ID,
        score=score,
        interpretation=_positioning_score_interpretation(score),
        inputs=inputs,
        weights=selected_weights,
        contributions=contributions,
        config_metadata=dict(config_metadata or {}),
        complete=score is not None,
        reason_codes=tuple(reason_codes),
    )


def calculate_crowding_flag(
    inputs: CrowdingFlagInput,
    *,
    funding_zscore_min: Any = DEFAULT_CROWDING_FUNDING_ZSCORE_MIN,
    basis_zscore_min: Any = DEFAULT_CROWDING_BASIS_ZSCORE_MIN,
    oi_intensity_percentile_min: Any = DEFAULT_CROWDING_OI_INTENSITY_PERCENTILE_MIN,
    entry_quality_penalty: Any = DEFAULT_CROWDING_ENTRY_QUALITY_PENALTY,
    config_metadata: dict[str, str] | None = None,
) -> CrowdingFlagResult:
    """Flag excessive leverage, funding, or futures-basis crowding."""

    funding_threshold = _non_negative_decimal(
        funding_zscore_min,
        "funding_zscore_min",
    )
    basis_threshold = _non_negative_decimal(basis_zscore_min, "basis_zscore_min")
    oi_threshold = _score_decimal(
        oi_intensity_percentile_min,
        "oi_intensity_percentile_min",
    )
    penalty = _score_decimal(entry_quality_penalty, "entry_quality_penalty")

    input_values = _crowding_input_values(inputs)
    reason_codes = []
    if any(value is None for value in input_values.values()):
        reason_codes.append("CROWDING_INPUT_MISSING")
    if (
        input_values["funding_zscore"] is not None
        and input_values["funding_zscore"] >= funding_threshold
    ):
        reason_codes.append("CROWDING_FUNDING_EXCESS")
    if (
        input_values["basis_zscore"] is not None
        and input_values["basis_zscore"] >= basis_threshold
    ):
        reason_codes.append("CROWDING_BASIS_EXCESS")
    if (
        input_values["oi_intensity_percentile"] is not None
        and input_values["oi_intensity_percentile"] >= oi_threshold
    ):
        reason_codes.append("CROWDING_LEVERAGE_EXCESS")

    reason_codes = _dedupe_reason_codes(reason_codes)
    flagged = any(reason_code.endswith("_EXCESS") for reason_code in reason_codes)
    return CrowdingFlagResult(
        feature_id=CROWDING_FLAG_FEATURE_ID,
        flagged=flagged,
        effects=CROWDING_FLAG_EFFECTS if flagged else (),
        entry_quality_penalty=penalty if flagged else Decimal("0"),
        funding_zscore_min=funding_threshold,
        basis_zscore_min=basis_threshold,
        oi_intensity_percentile_min=oi_threshold,
        inputs=inputs,
        config_metadata=dict(config_metadata or {}),
        complete="CROWDING_INPUT_MISSING" not in reason_codes,
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


def _validate_futures_basis_health_parameters(
    *,
    zscore_window_days: int,
    min_zscore_observations: int,
    basis_zscore_width: Decimal,
) -> None:
    if zscore_window_days < 1:
        raise ValueError("zscore_window_days must be >= 1")
    if min_zscore_observations < 1:
        raise ValueError("min_zscore_observations must be >= 1")
    if basis_zscore_width <= 0:
        raise ValueError("basis_zscore_width must be > 0")


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


def _validate_oi_intensity_parameters(
    *,
    open_interest_unit: str,
    percentile_window_days: int,
    min_percentile_observations: int,
) -> None:
    if not open_interest_unit.strip():
        raise ValueError("open_interest_unit must be non-empty")
    if percentile_window_days < 1:
        raise ValueError("percentile_window_days must be >= 1")
    if min_percentile_observations < 1:
        raise ValueError("min_percentile_observations must be >= 1")


def _positioning_score_weights(weights: dict[str, Any] | None) -> dict[str, Decimal]:
    if weights is None:
        return dict(DEFAULT_POSITIONING_SCORE_WEIGHTS)

    missing = set(POSITIONING_SCORE_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(POSITIONING_SCORE_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "positioning weights must exactly match "
            f"{POSITIONING_SCORE_COMPONENT_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    decimal_weights = {
        component_id: _decimal(weights[component_id])
        for component_id in POSITIONING_SCORE_COMPONENT_IDS
    }
    if any(weight < 0 for weight in decimal_weights.values()):
        raise ValueError("positioning weights must be non-negative")
    if sum(decimal_weights.values(), Decimal("0")) != Decimal("1"):
        raise ValueError("positioning weights must sum to 1")
    return decimal_weights


def _positioning_score_input_values(
    inputs: PositioningScoreInput,
) -> dict[str, Decimal | None]:
    values = {
        "funding_health": inputs.funding_health,
        "oi_health": inputs.oi_health,
        "basis_health": inputs.basis_health,
        "leverage_health": inputs.leverage_health,
    }
    return {
        component_id: (
            _score_decimal(value, component_id) if value is not None else None
        )
        for component_id, value in values.items()
    }


def _crowding_input_values(inputs: CrowdingFlagInput) -> dict[str, Decimal | None]:
    return {
        "funding_zscore": (
            _decimal(inputs.funding_zscore)
            if inputs.funding_zscore is not None
            else None
        ),
        "basis_zscore": (
            _decimal(inputs.basis_zscore) if inputs.basis_zscore is not None else None
        ),
        "oi_intensity_percentile": (
            _score_decimal(
                inputs.oi_intensity_percentile,
                "oi_intensity_percentile",
            )
            if inputs.oi_intensity_percentile is not None
            else None
        ),
    }


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


def _futures_basis_averages_by_time(
    futures_basis_rows: Sequence[FuturesBasis],
) -> dict[datetime, tuple[Decimal, Decimal]]:
    values_by_time: dict[datetime, list[tuple[Decimal, Decimal]]] = {}
    for row in futures_basis_rows:
        record = row.as_record()
        observation_time = record["observation_time"]
        values_by_time.setdefault(observation_time, []).append(
            (record["basis_rate"], record["annualized_basis_rate"])
        )
    return {
        observation_time: (
            _average(tuple(value[0] for value in values)),
            _average(tuple(value[1] for value in values)),
        )
        for observation_time, values in values_by_time.items()
    }


def _futures_basis_history(
    averages_by_time: dict[datetime, tuple[Decimal, Decimal]],
    *,
    observation_time: datetime,
    zscore_window_days: int,
) -> tuple[Decimal, ...]:
    window_start = observation_time - timedelta(days=zscore_window_days)
    return tuple(
        annualized_average
        for historical_time, (_, annualized_average) in sorted(averages_by_time.items())
        if window_start <= historical_time < observation_time
    )


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


def _market_cap_by_time(
    market_caps: Sequence[MarketCapObservation],
) -> dict[datetime, Decimal]:
    values_by_time: dict[datetime, list[Decimal]] = {}
    for row in market_caps:
        record = row.as_record()
        observation_time = record["observation_time"]
        values_by_time.setdefault(observation_time, []).append(record["market_cap_usd"])
    return {
        observation_time: _average(tuple(values))
        for observation_time, values in values_by_time.items()
    }


def _open_interest_intensity_by_time(
    aggregate_by_time: dict[datetime, Decimal],
    market_cap_by_time: dict[datetime, Decimal],
) -> dict[datetime, Decimal]:
    return {
        observation_time: aggregate_by_time[observation_time]
        / market_cap_by_time[observation_time]
        for observation_time in sorted(set(aggregate_by_time) & set(market_cap_by_time))
    }


def _latest_intensity_observation_time(
    intensity_by_time: dict[datetime, Decimal],
    aggregate_by_time: dict[datetime, Decimal],
    market_cap_by_time: dict[datetime, Decimal],
    *,
    signal_time: datetime,
) -> datetime:
    if intensity_by_time:
        return max(intensity_by_time)
    if aggregate_by_time:
        return max(aggregate_by_time)
    if market_cap_by_time:
        return max(market_cap_by_time)
    return signal_time


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


def _oi_intensity_history(
    intensity_by_time: dict[datetime, Decimal],
    *,
    observation_time: datetime,
    percentile_window_days: int,
) -> tuple[Decimal, ...]:
    window_start = observation_time - timedelta(days=percentile_window_days)
    return tuple(
        intensity
        for historical_time, intensity in sorted(intensity_by_time.items())
        if window_start <= historical_time < observation_time
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


def _percentile_rank(value: Decimal, history: Sequence[Decimal]) -> Decimal:
    if not history:
        raise ValueError("history must contain at least one observation")
    less_count = sum(1 for item in history if item < value)
    equal_count = sum(1 for item in history if item == value)
    rank = Decimal(less_count) + (Decimal("0.5") * Decimal(equal_count))
    return (rank / Decimal(len(history))) * Decimal("100")


def _positioning_score_interpretation(score: Decimal | None) -> str | None:
    if score is None:
        return None
    if score >= Decimal("70"):
        return "ADD_SUPPORTIVE"
    if score >= Decimal("60"):
        return "TRADE_SUPPORTIVE"
    if score >= Decimal("40"):
        return "WEAK_POSITIONING"
    return "STRESSED_POSITIONING"


def _score_decimal(value: Any, name: str) -> Decimal:
    decimal_value = _decimal(value)
    if decimal_value < 0 or decimal_value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return decimal_value


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    decimal_value = _decimal(value)
    if decimal_value < 0:
        raise ValueError(f"{name} must be >= 0")
    return decimal_value


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


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
    return Decimal(
        str(
            gaussian_health(
                float(zscore),
                preferred=float(preferred_zscore),
                width=float(zscore_width),
            )
        )
    )


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
