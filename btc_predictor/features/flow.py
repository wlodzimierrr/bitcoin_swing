"""Flow feature helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data import EtfFlow, require_utc_datetime


FIVE_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_5D"
FIVE_DAY_ETF_NORM_FEATURE_ID = "ETF_NORM_5D"
FIVE_DAY_ETF_FLOW_WINDOW_DAYS = 5
TWENTY_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_20D"
TWENTY_DAY_ETF_NORM_FEATURE_ID = "ETF_NORM_20D"
TWENTY_DAY_ETF_FLOW_WINDOW_DAYS = 20
ETF_FLOW_FEATURE_REASON_CODES = (
    "ETF_FLOW_INPUT_MISSING",
    "ETF_FLOW_AUM_MISSING",
)


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
