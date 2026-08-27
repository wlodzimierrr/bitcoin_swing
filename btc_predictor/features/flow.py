"""Flow feature helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import EtfFlow, OhlcvBar, PerpVolume, require_utc_datetime


FIVE_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_5D"
FIVE_DAY_ETF_NORM_FEATURE_ID = "ETF_NORM_5D"
FIVE_DAY_ETF_FLOW_WINDOW_DAYS = 5
TWENTY_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_20D"
TWENTY_DAY_ETF_NORM_FEATURE_ID = "ETF_NORM_20D"
TWENTY_DAY_ETF_FLOW_WINDOW_DAYS = 20
ETF_FLOW_ACCELERATION_FEATURE_ID = "FLOW_ACCEL"
SPOT_PERP_PARTICIPATION_FEATURE_ID = "SPOT_DOMINANCE"
SPOT_VOLUME_GROWTH_FEATURE_ID = "SPOT_VOLUME_GROWTH"
PERP_VOLUME_GROWTH_FEATURE_ID = "PERP_VOLUME_GROWTH"
SPOT_PERP_CVD_SPREAD_FEATURE_ID = "CVD_SPREAD"
SPOT_CVD_FEATURE_ID = "SPOT_CVD"
PERP_CVD_FEATURE_ID = "PERP_CVD"
ETF_FLOW_FEATURE_REASON_CODES = (
    "ETF_FLOW_INPUT_MISSING",
    "ETF_FLOW_AUM_MISSING",
)
ETF_FLOW_ACCELERATION_REASON_CODES = (
    "ETF_FLOW_ACCEL_INPUT_MISSING",
)
SPOT_PERP_PARTICIPATION_REASON_CODES = (
    "SPOT_VOLUME_INPUT_MISSING",
    "PERP_VOLUME_INPUT_MISSING",
    "SPOT_PERP_PARTICIPATION_INSUFFICIENT_HISTORY",
)
SPOT_PERP_CVD_SPREAD_REASON_CODES = (
    "SPOT_CVD_INPUT_MISSING",
    "PERP_CVD_INPUT_MISSING",
    "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY",
)


@dataclass(frozen=True)
class VolumeParticipationObservation:
    observation_time: datetime
    market_type: str
    notional_usd: Decimal
    provider: str
    available_at: datetime

    def as_record(self) -> dict[str, Any]:
        if self.market_type not in {"spot", "perp"}:
            raise ValueError("market_type must be spot or perp")
        if self.notional_usd < 0:
            raise ValueError("notional_usd must be >= 0")
        return {
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ),
            "market_type": self.market_type,
            "notional_usd": self.notional_usd,
            "provider": self.provider,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
        }


@dataclass(frozen=True)
class CvdObservation:
    observation_time: datetime
    market_type: str
    cvd_usd: Decimal
    provider: str
    available_at: datetime

    def as_record(self) -> dict[str, Any]:
        if self.market_type not in {"spot", "perp"}:
            raise ValueError("market_type must be spot or perp")
        return {
            "observation_time": require_utc_datetime(
                self.observation_time,
                "observation_time",
            ),
            "market_type": self.market_type,
            "cvd_usd": self.cvd_usd,
            "provider": self.provider,
            "available_at": require_utc_datetime(self.available_at, "available_at"),
        }


@dataclass(frozen=True)
class EtfFlowFeatureResult:
    feature_id: str
    normalized_feature_id: str
    window_days: int
    observation_date: date
    included_observation_dates: tuple[date, ...]
    funds: tuple[str, ...]
    flow_sum_usd: Decimal | None
    total_aum_usd: Decimal | None
    normalized_flow: Decimal | None
    source_record_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "normalized_feature_id": self.normalized_feature_id,
            "window_days": self.window_days,
            "observation_date": self.observation_date.isoformat(),
            "included_observation_dates": [
                observation_date.isoformat()
                for observation_date in self.included_observation_dates
            ],
            "funds": list(self.funds),
            "flow_sum_usd": str(self.flow_sum_usd) if self.flow_sum_usd is not None else None,
            "total_aum_usd": str(self.total_aum_usd) if self.total_aum_usd is not None else None,
            "normalized_flow": (
                str(self.normalized_flow) if self.normalized_flow is not None else None
            ),
            "source_record_count": self.source_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class EtfFlowAccelerationResult:
    feature_id: str
    observation_date: date
    five_day_normalized_feature_id: str
    twenty_day_normalized_feature_id: str
    five_day_normalized_flow: Decimal | None
    twenty_day_normalized_flow: Decimal | None
    acceleration: Decimal | None
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "observation_date": self.observation_date.isoformat(),
            "five_day_normalized_feature_id": self.five_day_normalized_feature_id,
            "twenty_day_normalized_feature_id": self.twenty_day_normalized_feature_id,
            "five_day_normalized_flow": (
                str(self.five_day_normalized_flow)
                if self.five_day_normalized_flow is not None
                else None
            ),
            "twenty_day_normalized_flow": (
                str(self.twenty_day_normalized_flow)
                if self.twenty_day_normalized_flow is not None
                else None
            ),
            "acceleration": str(self.acceleration) if self.acceleration is not None else None,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class SpotPerpParticipationResult:
    feature_id: str
    observation_time: datetime
    spot_volume_growth_feature_id: str
    perp_volume_growth_feature_id: str
    growth_window_periods: int
    zscore_window_periods: int
    min_zscore_periods: int
    spot_volume_growth: Decimal | None
    perp_volume_growth: Decimal | None
    spot_volume_growth_zscore: Decimal | None
    perp_volume_growth_zscore: Decimal | None
    spot_dominance: Decimal | None
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
            "spot_volume_growth_feature_id": self.spot_volume_growth_feature_id,
            "perp_volume_growth_feature_id": self.perp_volume_growth_feature_id,
            "growth_window_periods": self.growth_window_periods,
            "zscore_window_periods": self.zscore_window_periods,
            "min_zscore_periods": self.min_zscore_periods,
            "spot_volume_growth": (
                str(self.spot_volume_growth)
                if self.spot_volume_growth is not None
                else None
            ),
            "perp_volume_growth": (
                str(self.perp_volume_growth)
                if self.perp_volume_growth is not None
                else None
            ),
            "spot_volume_growth_zscore": (
                str(self.spot_volume_growth_zscore)
                if self.spot_volume_growth_zscore is not None
                else None
            ),
            "perp_volume_growth_zscore": (
                str(self.perp_volume_growth_zscore)
                if self.perp_volume_growth_zscore is not None
                else None
            ),
            "spot_dominance": (
                str(self.spot_dominance)
                if self.spot_dominance is not None
                else None
            ),
            "source_record_count": self.source_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class SpotPerpCvdSpreadResult:
    feature_id: str
    observation_time: datetime
    spot_cvd_feature_id: str
    perp_cvd_feature_id: str
    zscore_window_periods: int
    min_zscore_periods: int
    spot_cvd: Decimal | None
    perp_cvd: Decimal | None
    spot_cvd_zscore: Decimal | None
    perp_cvd_zscore: Decimal | None
    cvd_spread: Decimal | None
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
            "spot_cvd_feature_id": self.spot_cvd_feature_id,
            "perp_cvd_feature_id": self.perp_cvd_feature_id,
            "zscore_window_periods": self.zscore_window_periods,
            "min_zscore_periods": self.min_zscore_periods,
            "spot_cvd": str(self.spot_cvd) if self.spot_cvd is not None else None,
            "perp_cvd": str(self.perp_cvd) if self.perp_cvd is not None else None,
            "spot_cvd_zscore": (
                str(self.spot_cvd_zscore)
                if self.spot_cvd_zscore is not None
                else None
            ),
            "perp_cvd_zscore": (
                str(self.perp_cvd_zscore)
                if self.perp_cvd_zscore is not None
                else None
            ),
            "cvd_spread": str(self.cvd_spread) if self.cvd_spread is not None else None,
            "source_record_count": self.source_record_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def five_day_etf_flow(
    flows: Sequence[EtfFlow],
    *,
    as_of: datetime,
    funds: Sequence[str] = (),
    market_holidays: Iterable[date] = (),
    end_date: date | None = None,
) -> EtfFlowFeatureResult:
    """Calculate ETF_5 and ETFNorm_5 from point-in-time available flow rows."""

    return etf_flow_window(
        flows,
        as_of=as_of,
        window_days=FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
        funds=funds,
        market_holidays=market_holidays,
        end_date=end_date,
        feature_id=FIVE_DAY_ETF_FLOW_FEATURE_ID,
        normalized_feature_id=FIVE_DAY_ETF_NORM_FEATURE_ID,
    )


def twenty_day_etf_flow(
    flows: Sequence[EtfFlow],
    *,
    as_of: datetime,
    funds: Sequence[str] = (),
    market_holidays: Iterable[date] = (),
    end_date: date | None = None,
) -> EtfFlowFeatureResult:
    """Calculate ETF_20 and ETFNorm_20 from point-in-time available flow rows."""

    return etf_flow_window(
        flows,
        as_of=as_of,
        window_days=TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
        funds=funds,
        market_holidays=market_holidays,
        end_date=end_date,
        feature_id=TWENTY_DAY_ETF_FLOW_FEATURE_ID,
        normalized_feature_id=TWENTY_DAY_ETF_NORM_FEATURE_ID,
    )


def etf_flow_acceleration(
    five_day_flow: EtfFlowFeatureResult,
    twenty_day_flow: EtfFlowFeatureResult,
) -> EtfFlowAccelerationResult:
    """Calculate FlowAccel = ETFNorm_5 - ETFNorm_20 / 4."""

    if five_day_flow.observation_date != twenty_day_flow.observation_date:
        raise ValueError("flow acceleration inputs must share observation_date")
    if five_day_flow.window_days != FIVE_DAY_ETF_FLOW_WINDOW_DAYS:
        raise ValueError("five_day_flow must use a 5-day window")
    if twenty_day_flow.window_days != TWENTY_DAY_ETF_FLOW_WINDOW_DAYS:
        raise ValueError("twenty_day_flow must use a 20-day window")

    reason_codes = _dedupe_reason_codes(
        (
            *five_day_flow.reason_codes,
            *twenty_day_flow.reason_codes,
        )
    )
    if (
        five_day_flow.normalized_flow is None
        or twenty_day_flow.normalized_flow is None
    ):
        reason_codes = _dedupe_reason_codes(
            (*reason_codes, "ETF_FLOW_ACCEL_INPUT_MISSING")
        )

    acceleration = (
        five_day_flow.normalized_flow - (twenty_day_flow.normalized_flow / Decimal("4"))
        if five_day_flow.normalized_flow is not None
        and twenty_day_flow.normalized_flow is not None
        else None
    )
    return EtfFlowAccelerationResult(
        feature_id=ETF_FLOW_ACCELERATION_FEATURE_ID,
        observation_date=five_day_flow.observation_date,
        five_day_normalized_feature_id=five_day_flow.normalized_feature_id,
        twenty_day_normalized_feature_id=twenty_day_flow.normalized_feature_id,
        five_day_normalized_flow=five_day_flow.normalized_flow,
        twenty_day_normalized_flow=twenty_day_flow.normalized_flow,
        acceleration=acceleration,
        complete=not reason_codes,
        reason_codes=reason_codes,
    )


def spot_perp_participation_from_rows(
    spot_bars: Sequence[OhlcvBar],
    perp_volumes: Sequence[PerpVolume],
    *,
    as_of: datetime,
    growth_window_periods: int = 5,
    zscore_window_periods: int = 20,
    min_zscore_periods: int | None = None,
) -> SpotPerpParticipationResult:
    """Calculate spot-vs-perp participation from spot OHLCV and perp volume rows."""

    observations = []
    for bar in spot_bars:
        observations.append(
            VolumeParticipationObservation(
                observation_time=bar.timestamp,
                market_type="spot",
                notional_usd=bar.close * bar.volume,
                provider=bar.provider,
                available_at=bar.ingested_at,
            )
        )
    for volume in perp_volumes:
        if volume.notional_usd is None:
            continue
        observations.append(
            VolumeParticipationObservation(
                observation_time=volume.observation_time,
                market_type="perp",
                notional_usd=volume.notional_usd,
                provider=volume.provider,
                available_at=volume.available_at,
            )
        )

    return spot_perp_participation(
        observations,
        as_of=as_of,
        growth_window_periods=growth_window_periods,
        zscore_window_periods=zscore_window_periods,
        min_zscore_periods=min_zscore_periods,
    )


def spot_perp_participation(
    observations: Sequence[VolumeParticipationObservation],
    *,
    as_of: datetime,
    growth_window_periods: int = 5,
    zscore_window_periods: int = 20,
    min_zscore_periods: int | None = None,
) -> SpotPerpParticipationResult:
    """Calculate SpotDominance = z(spot volume growth) - z(perp volume growth)."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_participation_windows(
        growth_window_periods,
        zscore_window_periods,
        min_zscore_periods,
    )
    required_zscore_periods = (
        zscore_window_periods if min_zscore_periods is None else min_zscore_periods
    )
    available_observations = tuple(
        observation
        for observation in observations
        if observation.as_record()["available_at"] <= signal_time
        and observation.as_record()["observation_time"] <= signal_time
    )
    by_market_time = _aggregate_participation_observations(available_observations)
    spot_by_time = by_market_time["spot"]
    perp_by_time = by_market_time["perp"]
    common_times = tuple(sorted(set(spot_by_time) & set(perp_by_time)))
    observation_time = common_times[-1] if common_times else signal_time

    reason_codes = []
    if not spot_by_time:
        reason_codes.append("SPOT_VOLUME_INPUT_MISSING")
    if not perp_by_time:
        reason_codes.append("PERP_VOLUME_INPUT_MISSING")

    spot_growth = None
    perp_growth = None
    spot_growth_zscore = None
    perp_growth_zscore = None
    spot_dominance = None
    if common_times:
        spot_values = tuple(spot_by_time[time] for time in common_times)
        perp_values = tuple(perp_by_time[time] for time in common_times)
        spot_growth_series = _trailing_volume_growth(
            spot_values,
            window=growth_window_periods,
        )
        perp_growth_series = _trailing_volume_growth(
            perp_values,
            window=growth_window_periods,
        )
        spot_growth = spot_growth_series[-1]
        perp_growth = perp_growth_series[-1]
        spot_growth_zscore = _latest_zscore(
            spot_growth_series,
            window=zscore_window_periods,
            min_periods=required_zscore_periods,
        )
        perp_growth_zscore = _latest_zscore(
            perp_growth_series,
            window=zscore_window_periods,
            min_periods=required_zscore_periods,
        )
        if spot_growth_zscore is not None and perp_growth_zscore is not None:
            spot_dominance = spot_growth_zscore - perp_growth_zscore

    if spot_dominance is None:
        reason_codes.append("SPOT_PERP_PARTICIPATION_INSUFFICIENT_HISTORY")

    reason_codes = list(_dedupe_reason_codes(reason_codes))
    return SpotPerpParticipationResult(
        feature_id=SPOT_PERP_PARTICIPATION_FEATURE_ID,
        observation_time=observation_time,
        spot_volume_growth_feature_id=SPOT_VOLUME_GROWTH_FEATURE_ID,
        perp_volume_growth_feature_id=PERP_VOLUME_GROWTH_FEATURE_ID,
        growth_window_periods=growth_window_periods,
        zscore_window_periods=zscore_window_periods,
        min_zscore_periods=required_zscore_periods,
        spot_volume_growth=spot_growth,
        perp_volume_growth=perp_growth,
        spot_volume_growth_zscore=spot_growth_zscore,
        perp_volume_growth_zscore=perp_growth_zscore,
        spot_dominance=spot_dominance,
        source_record_count=len(available_observations),
        complete=not reason_codes,
        reason_codes=tuple(reason_codes),
    )


def spot_perp_cvd_spread(
    observations: Sequence[CvdObservation],
    *,
    as_of: datetime,
    zscore_window_periods: int = 20,
    min_zscore_periods: int | None = None,
) -> SpotPerpCvdSpreadResult:
    """Calculate CVDSpread = z(SpotCVD) - z(PerpCVD)."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_zscore_window(zscore_window_periods, min_zscore_periods)
    required_zscore_periods = (
        zscore_window_periods if min_zscore_periods is None else min_zscore_periods
    )
    available_observations = tuple(
        observation
        for observation in observations
        if observation.as_record()["available_at"] <= signal_time
        and observation.as_record()["observation_time"] <= signal_time
    )
    by_market_time = _aggregate_cvd_observations(available_observations)
    spot_by_time = by_market_time["spot"]
    perp_by_time = by_market_time["perp"]
    common_times = tuple(sorted(set(spot_by_time) & set(perp_by_time)))
    observation_time = common_times[-1] if common_times else signal_time

    reason_codes = []
    if not spot_by_time:
        reason_codes.append("SPOT_CVD_INPUT_MISSING")
    if not perp_by_time:
        reason_codes.append("PERP_CVD_INPUT_MISSING")

    spot_cvd = None
    perp_cvd = None
    spot_cvd_zscore = None
    perp_cvd_zscore = None
    cvd_spread = None
    if common_times:
        spot_values = tuple(spot_by_time[time] for time in common_times)
        perp_values = tuple(perp_by_time[time] for time in common_times)
        spot_cvd = spot_values[-1]
        perp_cvd = perp_values[-1]
        spot_cvd_zscore = _latest_zscore(
            spot_values,
            window=zscore_window_periods,
            min_periods=required_zscore_periods,
        )
        perp_cvd_zscore = _latest_zscore(
            perp_values,
            window=zscore_window_periods,
            min_periods=required_zscore_periods,
        )
        if spot_cvd_zscore is not None and perp_cvd_zscore is not None:
            cvd_spread = spot_cvd_zscore - perp_cvd_zscore

    if cvd_spread is None:
        reason_codes.append("SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY")

    reason_codes = list(_dedupe_reason_codes(reason_codes))
    return SpotPerpCvdSpreadResult(
        feature_id=SPOT_PERP_CVD_SPREAD_FEATURE_ID,
        observation_time=observation_time,
        spot_cvd_feature_id=SPOT_CVD_FEATURE_ID,
        perp_cvd_feature_id=PERP_CVD_FEATURE_ID,
        zscore_window_periods=zscore_window_periods,
        min_zscore_periods=required_zscore_periods,
        spot_cvd=spot_cvd,
        perp_cvd=perp_cvd,
        spot_cvd_zscore=spot_cvd_zscore,
        perp_cvd_zscore=perp_cvd_zscore,
        cvd_spread=cvd_spread,
        source_record_count=len(available_observations),
        complete=not reason_codes,
        reason_codes=tuple(reason_codes),
    )


def etf_flow_window(
    flows: Sequence[EtfFlow],
    *,
    as_of: datetime,
    window_days: int,
    funds: Sequence[str] = (),
    market_holidays: Iterable[date] = (),
    end_date: date | None = None,
    feature_id: str,
    normalized_feature_id: str,
) -> EtfFlowFeatureResult:
    """Calculate an ETF flow window from latest point-in-time revisions."""

    cutoff = require_utc_datetime(as_of, "as_of")
    if window_days < 1:
        raise ValueError("window_days must be >= 1")

    available_flows = _latest_available_flows_by_fund_date(
        flows,
        as_of=cutoff,
        funds=funds,
        end_date=end_date,
    )
    observation_date = end_date or _latest_observation_date(available_flows, cutoff.date())
    included_dates = _trailing_publication_dates(
        observation_date,
        window_days=window_days,
        market_holidays=market_holidays,
    )
    fund_universe = _fund_universe(available_flows, funds)
    window_rows = tuple(
        available_flows[(fund, observation_date)]
        for fund in fund_universe
        for observation_date in included_dates
        if (fund, observation_date) in available_flows
    )
    missing_inputs = [
        (fund, observation_date)
        for fund in fund_universe
        for observation_date in included_dates
        if (fund, observation_date) not in available_flows
    ]
    reason_codes = []
    if missing_inputs or not fund_universe:
        reason_codes.append("ETF_FLOW_INPUT_MISSING")

    flow_sum_usd = (
        sum((flow.flow_usd for flow in window_rows), Decimal("0"))
        if not missing_inputs and fund_universe
        else None
    )
    latest_aum_by_fund = _latest_aum_by_fund(
        available_flows.values(),
        funds=fund_universe,
        observation_date=observation_date,
    )
    missing_aum = fund_universe and set(latest_aum_by_fund) != set(fund_universe)
    total_aum_usd = (
        sum(latest_aum_by_fund.values(), Decimal("0"))
        if latest_aum_by_fund and not missing_aum
        else None
    )
    if total_aum_usd == 0:
        total_aum_usd = None
    if total_aum_usd is None:
        reason_codes.append("ETF_FLOW_AUM_MISSING")

    normalized_flow = (
        flow_sum_usd / total_aum_usd
        if flow_sum_usd is not None and total_aum_usd is not None
        else None
    )
    return EtfFlowFeatureResult(
        feature_id=feature_id,
        normalized_feature_id=normalized_feature_id,
        window_days=window_days,
        observation_date=observation_date,
        included_observation_dates=included_dates,
        funds=fund_universe,
        flow_sum_usd=flow_sum_usd,
        total_aum_usd=total_aum_usd,
        normalized_flow=normalized_flow,
        source_record_count=len(window_rows),
        complete=not reason_codes,
        reason_codes=tuple(reason_codes),
    )


def _latest_available_flows_by_fund_date(
    flows: Sequence[EtfFlow],
    *,
    as_of: datetime,
    funds: Sequence[str],
    end_date: date | None,
) -> dict[tuple[str, date], EtfFlow]:
    requested_funds = set(funds)
    latest: dict[tuple[str, date], EtfFlow] = {}
    for flow in flows:
        available_at = require_utc_datetime(flow.available_at, "available_at")
        if available_at > as_of:
            continue
        if end_date is not None and flow.observation_date > end_date:
            continue
        if requested_funds and flow.fund not in requested_funds:
            continue

        key = (flow.fund, flow.observation_date)
        current = latest.get(key)
        if current is None or _flow_revision_sort_key(flow) > _flow_revision_sort_key(current):
            latest[key] = flow
    return latest


def _flow_revision_sort_key(flow: EtfFlow) -> tuple[datetime, str, str]:
    return (
        require_utc_datetime(flow.available_at, "available_at"),
        flow.revision,
        flow.provider,
    )


def _latest_observation_date(
    flows_by_fund_date: dict[tuple[str, date], EtfFlow],
    fallback: date,
) -> date:
    if not flows_by_fund_date:
        return fallback
    return max(observation_date for _, observation_date in flows_by_fund_date)


def _trailing_publication_dates(
    observation_date: date,
    *,
    window_days: int,
    market_holidays: Iterable[date],
) -> tuple[date, ...]:
    holidays = set(market_holidays)
    dates = []
    current = observation_date
    while len(dates) < window_days:
        if current.weekday() < 5 and current not in holidays:
            dates.append(current)
        current -= timedelta(days=1)
    return tuple(reversed(dates))


def _fund_universe(
    flows_by_fund_date: dict[tuple[str, date], EtfFlow],
    funds: Sequence[str],
) -> tuple[str, ...]:
    if funds:
        return tuple(sorted(funds))
    return tuple(sorted({fund for fund, _ in flows_by_fund_date}))


def _latest_aum_by_fund(
    flows: Iterable[EtfFlow],
    *,
    funds: Sequence[str],
    observation_date: date,
) -> dict[str, Decimal]:
    latest: dict[str, EtfFlow] = {}
    requested_funds = set(funds)
    for flow in flows:
        if flow.fund not in requested_funds:
            continue
        if flow.observation_date > observation_date or flow.aum_usd is None:
            continue
        current = latest.get(flow.fund)
        if current is None or (flow.observation_date, *_flow_revision_sort_key(flow)) > (
            current.observation_date,
            *_flow_revision_sort_key(current),
        ):
            latest[flow.fund] = flow
    return {fund: flow.aum_usd for fund, flow in latest.items() if flow.aum_usd is not None}


def _validate_participation_windows(
    growth_window_periods: int,
    zscore_window_periods: int,
    min_zscore_periods: int | None,
) -> None:
    if growth_window_periods < 1:
        raise ValueError("growth_window_periods must be >= 1")
    if zscore_window_periods < 1:
        raise ValueError("zscore_window_periods must be >= 1")
    _validate_zscore_window(zscore_window_periods, min_zscore_periods)


def _validate_zscore_window(
    zscore_window_periods: int,
    min_zscore_periods: int | None,
) -> None:
    if zscore_window_periods < 1:
        raise ValueError("zscore_window_periods must be >= 1")
    if min_zscore_periods is not None:
        if min_zscore_periods < 1:
            raise ValueError("min_zscore_periods must be >= 1")
        if min_zscore_periods > zscore_window_periods:
            raise ValueError("min_zscore_periods must be <= zscore_window_periods")


def _aggregate_participation_observations(
    observations: Sequence[VolumeParticipationObservation],
) -> dict[str, dict[datetime, Decimal]]:
    aggregated: dict[str, dict[datetime, Decimal]] = {"spot": {}, "perp": {}}
    for observation in observations:
        record = observation.as_record()
        market_type = record["market_type"]
        observation_time = record["observation_time"]
        notional_usd = record["notional_usd"]
        aggregated[market_type][observation_time] = (
            aggregated[market_type].get(observation_time, Decimal("0"))
            + notional_usd
        )
    return aggregated


def _aggregate_cvd_observations(
    observations: Sequence[CvdObservation],
) -> dict[str, dict[datetime, Decimal]]:
    aggregated: dict[str, dict[datetime, Decimal]] = {"spot": {}, "perp": {}}
    for observation in observations:
        record = observation.as_record()
        market_type = record["market_type"]
        observation_time = record["observation_time"]
        cvd_usd = record["cvd_usd"]
        aggregated[market_type][observation_time] = (
            aggregated[market_type].get(observation_time, Decimal("0"))
            + cvd_usd
        )
    return aggregated


def _trailing_volume_growth(
    values: Sequence[Decimal],
    *,
    window: int,
) -> tuple[Decimal | None, ...]:
    growth_values = []
    for index in range(len(values)):
        if index < (window * 2) - 1:
            growth_values.append(None)
            continue
        current_window = values[index - window + 1 : index + 1]
        prior_window = values[index - (window * 2) + 1 : index - window + 1]
        prior_sum = sum(prior_window, Decimal("0"))
        if prior_sum == 0:
            growth_values.append(None)
            continue
        current_sum = sum(current_window, Decimal("0"))
        growth_values.append((current_sum / prior_sum) - Decimal("1"))
    return tuple(growth_values)


def _latest_zscore(
    values: Sequence[Decimal | None],
    *,
    window: int,
    min_periods: int,
) -> Decimal | None:
    if not values or values[-1] is None:
        return None
    history = tuple(value for value in values[:-1] if value is not None)[-window:]
    if len(history) < min_periods:
        return None
    mean = sum(history, Decimal("0")) / Decimal(len(history))
    variance = sum(((value - mean) ** 2 for value in history), Decimal("0")) / Decimal(
        len(history)
    )
    volatility = variance.sqrt()
    if volatility == 0:
        return None
    return (values[-1] - mean) / volatility


def _dedupe_reason_codes(reason_codes: Iterable[str]) -> tuple[str, ...]:
    deduped = []
    for reason_code in reason_codes:
        if reason_code not in deduped:
            deduped.append(reason_code)
    return tuple(deduped)
