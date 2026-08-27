from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import EtfFlow
from btc_predictor.features import (
    ETF_FLOW_FEATURE_REASON_CODES,
    FIVE_DAY_ETF_FLOW_FEATURE_ID,
    FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
    FIVE_DAY_ETF_NORM_FEATURE_ID,
    TWENTY_DAY_ETF_FLOW_FEATURE_ID,
    TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
    TWENTY_DAY_ETF_NORM_FEATURE_ID,
    etf_flow_window,
    five_day_etf_flow,
    twenty_day_etf_flow,
)


def etf_flow(
    fund: str,
    observation_date: date,
    flow_usd: str,
    *,
    aum_usd: str | None = "10000",
    revision: str = "initial",
    available_at: datetime | None = None,
) -> EtfFlow:
    return EtfFlow(
        fund=fund,
        observation_date=observation_date,
        flow_usd=Decimal(flow_usd),
        aum_usd=Decimal(aum_usd) if aum_usd is not None else None,
        provider="farside",
        source="farside-dashboard",
        revision=revision,
        available_at=available_at or datetime.combine(
            observation_date + timedelta(days=1),
            datetime.min.time(),
            tzinfo=UTC,
        ),
        ingested_at=datetime(2026, 8, 31, tzinfo=UTC),
    )


def five_weekday_flows() -> tuple[EtfFlow, ...]:
    dates = tuple(date(2026, 8, 24) + timedelta(days=offset) for offset in range(5))
    return flow_rows_for_publication_dates(dates)


def flow_rows_for_publication_dates(dates: tuple[date, ...]) -> tuple[EtfFlow, ...]:
    flows = []
    for observation_date in dates:
        flows.append(etf_flow("IBIT", observation_date, "100", aum_usd="10000"))
        flows.append(etf_flow("FBTC", observation_date, "-20", aum_usd="5000"))
    return tuple(flows)


def publication_dates_ending(
    end_date: date,
    *,
    count: int,
    market_holidays: set[date] | None = None,
) -> tuple[date, ...]:
    holidays = market_holidays or set()
    publication_dates = []
    current = end_date
    while len(publication_dates) < count:
        if current.weekday() < 5 and current not in holidays:
            publication_dates.append(current)
        current -= timedelta(days=1)
    return tuple(reversed(publication_dates))


def test_five_day_etf_flow_metadata_is_stable() -> None:
    assert FIVE_DAY_ETF_FLOW_FEATURE_ID == "ETF_FLOW_5D"
    assert FIVE_DAY_ETF_NORM_FEATURE_ID == "ETF_NORM_5D"
    assert FIVE_DAY_ETF_FLOW_WINDOW_DAYS == 5
    assert ETF_FLOW_FEATURE_REASON_CODES == (
        "ETF_FLOW_INPUT_MISSING",
        "ETF_FLOW_AUM_MISSING",
    )


def test_twenty_day_etf_flow_metadata_is_stable() -> None:
    assert TWENTY_DAY_ETF_FLOW_FEATURE_ID == "ETF_FLOW_20D"
    assert TWENTY_DAY_ETF_NORM_FEATURE_ID == "ETF_NORM_20D"
    assert TWENTY_DAY_ETF_FLOW_WINDOW_DAYS == 20


def test_five_day_etf_flow_sums_latest_five_publication_days_and_normalizes_by_aum() -> None:
    result = five_day_etf_flow(
        five_weekday_flows(),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    assert result.complete is True
    assert result.observation_date == date(2026, 8, 28)
    assert result.included_observation_dates == (
        date(2026, 8, 24),
        date(2026, 8, 25),
        date(2026, 8, 26),
        date(2026, 8, 27),
        date(2026, 8, 28),
    )
    assert result.flow_sum_usd == Decimal("400")
    assert result.total_aum_usd == Decimal("15000")
    assert result.normalized_flow == Decimal("0.02666666666666666666666666667")
    assert result.source_record_count == 10
    assert result.reason_codes == ()


def test_twenty_day_etf_flow_sums_latest_twenty_publication_days_and_normalizes() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)

    result = twenty_day_etf_flow(
        flow_rows_for_publication_dates(dates),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    assert result.complete is True
    assert result.feature_id == "ETF_FLOW_20D"
    assert result.normalized_feature_id == "ETF_NORM_20D"
    assert result.window_days == 20
    assert result.observation_date == date(2026, 8, 28)
    assert result.included_observation_dates == dates
    assert result.flow_sum_usd == Decimal("1600")
    assert result.total_aum_usd == Decimal("15000")
    assert result.normalized_flow == Decimal("0.1066666666666666666666666667")
    assert result.source_record_count == 40
    assert result.reason_codes == ()


def test_twenty_day_etf_flow_reports_missing_inputs_without_zero_fill() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)
    flows = flow_rows_for_publication_dates(dates)[:-1]

    result = twenty_day_etf_flow(
        flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
        end_date=date(2026, 8, 28),
    )

    assert result.complete is False
    assert result.flow_sum_usd is None
    assert result.normalized_flow is None
    assert result.source_record_count == 39
    assert result.reason_codes == ("ETF_FLOW_INPUT_MISSING",)


def test_five_day_etf_flow_uses_latest_revision_available_at_signal_time() -> None:
    flows = (
        etf_flow("IBIT", date(2026, 8, 24), "100", available_at=datetime(2026, 8, 25, tzinfo=UTC)),
        etf_flow(
            "IBIT",
            date(2026, 8, 24),
            "999",
            revision="v2",
            available_at=datetime(2026, 8, 30, tzinfo=UTC),
        ),
    )

    early = etf_flow_window(
        flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        window_days=1,
        funds=("IBIT",),
        end_date=date(2026, 8, 24),
        feature_id="ETF_FLOW_1D",
        normalized_feature_id="ETF_NORM_1D",
    )
    late = etf_flow_window(
        flows,
        as_of=datetime(2026, 8, 30, tzinfo=UTC),
        window_days=1,
        funds=("IBIT",),
        end_date=date(2026, 8, 24),
        feature_id="ETF_FLOW_1D",
        normalized_feature_id="ETF_NORM_1D",
    )

    assert early.flow_sum_usd == Decimal("100")
    assert late.flow_sum_usd == Decimal("999")


def test_five_day_etf_flow_reports_missing_inputs_without_substituting_zeroes() -> None:
    flows = five_weekday_flows()[:-1]

    result = five_day_etf_flow(
        flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
        end_date=date(2026, 8, 28),
    )

    assert result.complete is False
    assert result.flow_sum_usd is None
    assert result.normalized_flow is None
    assert result.source_record_count == 9
    assert result.reason_codes == ("ETF_FLOW_INPUT_MISSING",)


def test_five_day_etf_flow_reports_missing_aum_without_silent_normalization() -> None:
    flows = tuple(
        etf_flow_record
        if etf_flow_record.fund == "IBIT"
        else EtfFlow(**{**etf_flow_record.as_record(), "aum_usd": None})
        for etf_flow_record in five_weekday_flows()
    )

    result = five_day_etf_flow(
        flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    assert result.flow_sum_usd == Decimal("400")
    assert result.total_aum_usd is None
    assert result.normalized_flow is None
    assert result.complete is False
    assert result.reason_codes == ("ETF_FLOW_AUM_MISSING",)


def test_five_day_etf_flow_can_skip_market_holidays() -> None:
    result = etf_flow_window(
        (
            etf_flow("IBIT", date(2026, 8, 21), "10"),
            etf_flow("IBIT", date(2026, 8, 24), "20"),
            etf_flow("IBIT", date(2026, 8, 26), "30"),
        ),
        as_of=datetime(2026, 8, 27, tzinfo=UTC),
        window_days=3,
        funds=("IBIT",),
        market_holidays={date(2026, 8, 25)},
        end_date=date(2026, 8, 26),
        feature_id="ETF_FLOW_3D",
        normalized_feature_id="ETF_NORM_3D",
    )

    assert result.included_observation_dates == (
        date(2026, 8, 21),
        date(2026, 8, 24),
        date(2026, 8, 26),
    )
    assert result.flow_sum_usd == Decimal("60")


def test_five_day_etf_flow_is_deterministic_for_unsorted_inputs() -> None:
    flows = five_weekday_flows()

    first = five_day_etf_flow(
        flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    ).as_record()
    second = five_day_etf_flow(
        tuple(reversed(flows)),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    ).as_record()

    assert first == second


def test_five_day_etf_flow_exposes_persistable_payload() -> None:
    result = five_day_etf_flow(
        five_weekday_flows(),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    assert result.as_record() == {
        "feature_id": "ETF_FLOW_5D",
        "normalized_feature_id": "ETF_NORM_5D",
        "window_days": 5,
        "observation_date": "2026-08-28",
        "included_observation_dates": [
            "2026-08-24",
            "2026-08-25",
            "2026-08-26",
            "2026-08-27",
            "2026-08-28",
        ],
        "funds": ["FBTC", "IBIT"],
        "flow_sum_usd": "400",
        "total_aum_usd": "15000",
        "normalized_flow": "0.02666666666666666666666666667",
        "source_record_count": 10,
        "complete": True,
        "reason_codes": [],
    }


def test_twenty_day_etf_flow_exposes_persistable_payload() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)

    result = twenty_day_etf_flow(
        flow_rows_for_publication_dates(dates),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    assert result.as_record() == {
        "feature_id": "ETF_FLOW_20D",
        "normalized_feature_id": "ETF_NORM_20D",
        "window_days": 20,
        "observation_date": "2026-08-28",
        "included_observation_dates": [
            observation_date.isoformat() for observation_date in dates
        ],
        "funds": ["FBTC", "IBIT"],
        "flow_sum_usd": "1600",
        "total_aum_usd": "15000",
        "normalized_flow": "0.1066666666666666666666666667",
        "source_record_count": 40,
        "complete": True,
        "reason_codes": [],
    }


def test_five_day_etf_flow_requires_utc_as_of() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        five_day_etf_flow((), as_of=datetime(2026, 8, 29))


def test_five_day_etf_flow_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="window_days"):
        etf_flow_window(
            (),
            as_of=datetime(2026, 8, 29, tzinfo=UTC),
            window_days=0,
            feature_id="ETF_FLOW_0D",
            normalized_feature_id="ETF_NORM_0D",
        )
