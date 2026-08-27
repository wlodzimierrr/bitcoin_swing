from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import EtfFlow, OhlcvBar, PerpVolume
from btc_predictor.features import (
    CvdObservation,
    ETF_FLOW_ACCELERATION_FEATURE_ID,
    ETF_FLOW_ACCELERATION_REASON_CODES,
    ETF_FLOW_FEATURE_REASON_CODES,
    FIVE_DAY_ETF_FLOW_FEATURE_ID,
    FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
    FIVE_DAY_ETF_NORM_FEATURE_ID,
    PERP_VOLUME_GROWTH_FEATURE_ID,
    PERP_CVD_FEATURE_ID,
    SPOT_PERP_PARTICIPATION_FEATURE_ID,
    SPOT_PERP_PARTICIPATION_REASON_CODES,
    SPOT_PERP_CVD_SPREAD_FEATURE_ID,
    SPOT_PERP_CVD_SPREAD_REASON_CODES,
    SPOT_CVD_FEATURE_ID,
    SPOT_VOLUME_GROWTH_FEATURE_ID,
    TWENTY_DAY_ETF_FLOW_FEATURE_ID,
    TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
    TWENTY_DAY_ETF_NORM_FEATURE_ID,
    VolumeParticipationObservation,
    EtfFlowFeatureResult,
    etf_flow_acceleration,
    etf_flow_window,
    five_day_etf_flow,
    spot_perp_cvd_spread,
    spot_perp_participation,
    spot_perp_participation_from_rows,
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


def participation_observation(
    observation_time: datetime,
    *,
    market_type: str,
    notional_usd: str,
    available_at: datetime | None = None,
) -> VolumeParticipationObservation:
    return VolumeParticipationObservation(
        observation_time=observation_time,
        market_type=market_type,
        notional_usd=Decimal(notional_usd),
        provider="fixture",
        available_at=available_at or observation_time + timedelta(minutes=1),
    )


def cvd_observation(
    observation_time: datetime,
    *,
    market_type: str,
    cvd_usd: str,
    available_at: datetime | None = None,
) -> CvdObservation:
    return CvdObservation(
        observation_time=observation_time,
        market_type=market_type,
        cvd_usd=Decimal(cvd_usd),
        provider="fixture",
        available_at=available_at or observation_time + timedelta(minutes=1),
    )


def spot_bar(timestamp: datetime, *, close: str, volume: str) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=Decimal(close),
        high=Decimal(close),
        low=Decimal(close),
        close=Decimal(close),
        volume=Decimal(volume),
        provider="coinbase",
        ingested_at=timestamp + timedelta(minutes=1),
    )


def perp_volume(timestamp: datetime, *, notional_usd: str | None) -> PerpVolume:
    return PerpVolume(
        observation_time=timestamp,
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="1h",
        volume=Decimal("1"),
        volume_unit="contracts",
        notional_usd=Decimal(notional_usd) if notional_usd is not None else None,
        provider="binance",
        source="binance-api",
        available_at=timestamp + timedelta(minutes=1),
        ingested_at=timestamp + timedelta(minutes=2),
    )


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


def test_etf_flow_acceleration_metadata_is_stable() -> None:
    assert ETF_FLOW_ACCELERATION_FEATURE_ID == "FLOW_ACCEL"
    assert ETF_FLOW_ACCELERATION_REASON_CODES == ("ETF_FLOW_ACCEL_INPUT_MISSING",)


def test_spot_perp_participation_metadata_is_stable() -> None:
    assert SPOT_PERP_PARTICIPATION_FEATURE_ID == "SPOT_DOMINANCE"
    assert SPOT_VOLUME_GROWTH_FEATURE_ID == "SPOT_VOLUME_GROWTH"
    assert PERP_VOLUME_GROWTH_FEATURE_ID == "PERP_VOLUME_GROWTH"
    assert SPOT_PERP_PARTICIPATION_REASON_CODES == (
        "SPOT_VOLUME_INPUT_MISSING",
        "PERP_VOLUME_INPUT_MISSING",
        "SPOT_PERP_PARTICIPATION_INSUFFICIENT_HISTORY",
    )


def test_spot_perp_cvd_spread_metadata_is_stable() -> None:
    assert SPOT_PERP_CVD_SPREAD_FEATURE_ID == "CVD_SPREAD"
    assert SPOT_CVD_FEATURE_ID == "SPOT_CVD"
    assert PERP_CVD_FEATURE_ID == "PERP_CVD"
    assert SPOT_PERP_CVD_SPREAD_REASON_CODES == (
        "SPOT_CVD_INPUT_MISSING",
        "PERP_CVD_INPUT_MISSING",
        "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY",
    )


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


def test_etf_flow_acceleration_compares_five_day_flow_to_twenty_day_average() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)
    flows = []
    for observation_date in dates[:15]:
        flows.append(etf_flow("IBIT", observation_date, "20", aum_usd="10000"))
        flows.append(etf_flow("FBTC", observation_date, "0", aum_usd="5000"))
    for observation_date in dates[15:]:
        flows.append(etf_flow("IBIT", observation_date, "100", aum_usd="10000"))
        flows.append(etf_flow("FBTC", observation_date, "-20", aum_usd="5000"))

    five_day = five_day_etf_flow(
        tuple(flows),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )
    twenty_day = twenty_day_etf_flow(
        tuple(reversed(flows)),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    result = etf_flow_acceleration(five_day, twenty_day)

    assert result.complete is True
    assert result.feature_id == "FLOW_ACCEL"
    assert result.observation_date == date(2026, 8, 28)
    assert result.five_day_normalized_feature_id == "ETF_NORM_5D"
    assert result.twenty_day_normalized_feature_id == "ETF_NORM_20D"
    assert result.five_day_normalized_flow == Decimal("0.02666666666666666666666666667")
    assert result.twenty_day_normalized_flow == Decimal("0.04666666666666666666666666667")
    assert result.acceleration == Decimal("0.01500000000000000000000000000")
    assert result.reason_codes == ()


def test_etf_flow_acceleration_exposes_persistable_payload() -> None:
    five_day = EtfFlowFeatureResult(
        feature_id="ETF_FLOW_5D",
        normalized_feature_id="ETF_NORM_5D",
        window_days=5,
        observation_date=date(2026, 8, 28),
        included_observation_dates=(),
        funds=("IBIT",),
        flow_sum_usd=Decimal("200"),
        total_aum_usd=Decimal("10000"),
        normalized_flow=Decimal("0.02"),
        source_record_count=5,
        complete=True,
    )
    twenty_day = EtfFlowFeatureResult(
        feature_id="ETF_FLOW_20D",
        normalized_feature_id="ETF_NORM_20D",
        window_days=20,
        observation_date=date(2026, 8, 28),
        included_observation_dates=(),
        funds=("IBIT",),
        flow_sum_usd=Decimal("400"),
        total_aum_usd=Decimal("10000"),
        normalized_flow=Decimal("0.04"),
        source_record_count=20,
        complete=True,
    )

    result = etf_flow_acceleration(five_day, twenty_day)

    assert result.as_record() == {
        "feature_id": "FLOW_ACCEL",
        "observation_date": "2026-08-28",
        "five_day_normalized_feature_id": "ETF_NORM_5D",
        "twenty_day_normalized_feature_id": "ETF_NORM_20D",
        "five_day_normalized_flow": "0.02",
        "twenty_day_normalized_flow": "0.04",
        "acceleration": "0.01",
        "complete": True,
        "reason_codes": [],
    }


def test_etf_flow_acceleration_reports_missing_normalized_inputs() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)
    five_day_flows = tuple(
        flow
        if flow.fund == "IBIT"
        else EtfFlow(**{**flow.as_record(), "aum_usd": None})
        for flow in flow_rows_for_publication_dates(dates[15:])
    )
    five_day = five_day_etf_flow(
        five_day_flows,
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )
    twenty_day = twenty_day_etf_flow(
        flow_rows_for_publication_dates(dates),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    result = etf_flow_acceleration(five_day, twenty_day)

    assert result.complete is False
    assert result.acceleration is None
    assert result.reason_codes == (
        "ETF_FLOW_AUM_MISSING",
        "ETF_FLOW_ACCEL_INPUT_MISSING",
    )


def test_spot_perp_participation_calculates_spot_dominance_from_volume_growth_zscores() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(5))
    spot_values = ("100", "110", "132", "171.6", "240.24")
    perp_values = ("100", "120", "132", "132", "138.6")
    observations = tuple(
        participation_observation(time, market_type=market_type, notional_usd=value)
        for time, spot_value, perp_value in zip(times, spot_values, perp_values, strict=True)
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )

    result = spot_perp_participation(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    assert result.complete is True
    assert result.feature_id == "SPOT_DOMINANCE"
    assert result.observation_time == times[-1]
    assert result.spot_volume_growth == Decimal("0.4")
    assert result.perp_volume_growth == Decimal("0.05")
    assert result.spot_volume_growth_zscore is not None
    assert result.perp_volume_growth_zscore is not None
    assert result.spot_dominance is not None
    assert result.spot_volume_growth_zscore.quantize(Decimal("0.000001")) == Decimal("2.449490")
    assert result.perp_volume_growth_zscore.quantize(Decimal("0.000001")) == Decimal("-0.612372")
    assert result.spot_dominance.quantize(Decimal("0.000001")) == Decimal("3.061862")
    assert result.source_record_count == 10
    assert result.reason_codes == ()


def test_spot_perp_participation_filters_unavailable_future_inputs() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(5))
    observations = tuple(
        participation_observation(time, market_type=market_type, notional_usd=value)
        for time, spot_value, perp_value in zip(
            times,
            ("100", "110", "132", "171.6", "240.24"),
            ("100", "120", "132", "132", "138.6"),
            strict=True,
        )
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )
    unavailable_future = participation_observation(
        times[-1],
        market_type="spot",
        notional_usd="999999",
        available_at=times[-1] + timedelta(days=1),
    )

    baseline = spot_perp_participation(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    ).as_record()
    with_future = spot_perp_participation(
        (*observations, unavailable_future),
        as_of=times[-1] + timedelta(minutes=2),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    ).as_record()

    assert with_future == baseline


def test_spot_perp_participation_reports_missing_inputs_without_zero_fill() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    observations = tuple(
        participation_observation(
            start + timedelta(hours=offset),
            market_type="spot",
            notional_usd="100",
        )
        for offset in range(5)
    )

    result = spot_perp_participation(
        observations,
        as_of=start + timedelta(hours=5),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    assert result.complete is False
    assert result.spot_dominance is None
    assert result.reason_codes == (
        "PERP_VOLUME_INPUT_MISSING",
        "SPOT_PERP_PARTICIPATION_INSUFFICIENT_HISTORY",
    )


def test_spot_perp_participation_exposes_persistable_payload() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(5))
    observations = tuple(
        participation_observation(time, market_type=market_type, notional_usd=value)
        for time, spot_value, perp_value in zip(
            times,
            ("100", "110", "132", "171.6", "240.24"),
            ("100", "120", "132", "132", "138.6"),
            strict=True,
        )
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )

    result = spot_perp_participation(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    record = result.as_record()
    assert record["feature_id"] == "SPOT_DOMINANCE"
    assert record["observation_time"] == "2026-08-24T04:00:00+00:00"
    assert record["spot_volume_growth_feature_id"] == "SPOT_VOLUME_GROWTH"
    assert record["perp_volume_growth_feature_id"] == "PERP_VOLUME_GROWTH"
    assert record["spot_volume_growth"] == "0.4"
    assert record["perp_volume_growth"] == "0.05"
    assert record["source_record_count"] == 10
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_spot_perp_participation_from_rows_uses_spot_close_volume_and_perp_notional() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(5))

    result = spot_perp_participation_from_rows(
        tuple(
            spot_bar(time, close="10", volume=volume)
            for time, volume in zip(
                times,
                ("10", "11", "13.2", "17.16", "24.024"),
                strict=True,
            )
        ),
        tuple(
            perp_volume(time, notional_usd=notional)
            for time, notional in zip(
                times,
                ("100", "120", "132", "132", "138.6"),
                strict=True,
            )
        ),
        as_of=times[-1] + timedelta(minutes=2),
        growth_window_periods=1,
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    assert result.complete is True
    assert result.spot_volume_growth == Decimal("0.4")
    assert result.perp_volume_growth == Decimal("0.05")
    assert result.source_record_count == 10


def test_spot_perp_participation_rejects_invalid_observations_and_windows() -> None:
    with pytest.raises(ValueError, match="market_type"):
        participation_observation(
            datetime(2026, 8, 24, tzinfo=UTC),
            market_type="futures",
            notional_usd="100",
        ).as_record()

    with pytest.raises(ValueError, match="growth_window_periods"):
        spot_perp_participation(
            (),
            as_of=datetime(2026, 8, 24, tzinfo=UTC),
            growth_window_periods=0,
        )


def test_spot_perp_cvd_spread_calculates_spread_from_cvd_zscores() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(4))
    spot_values = ("100", "110", "120", "160")
    perp_values = ("100", "120", "140", "145")
    observations = tuple(
        cvd_observation(time, market_type=market_type, cvd_usd=value)
        for time, spot_value, perp_value in zip(times, spot_values, perp_values, strict=True)
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )

    result = spot_perp_cvd_spread(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    assert result.complete is True
    assert result.feature_id == "CVD_SPREAD"
    assert result.observation_time == times[-1]
    assert result.spot_cvd == Decimal("160")
    assert result.perp_cvd == Decimal("145")
    assert result.spot_cvd_zscore is not None
    assert result.perp_cvd_zscore is not None
    assert result.cvd_spread is not None
    assert result.spot_cvd_zscore.quantize(Decimal("0.000001")) == Decimal("6.123724")
    assert result.perp_cvd_zscore.quantize(Decimal("0.000001")) == Decimal("1.530931")
    assert result.cvd_spread.quantize(Decimal("0.000001")) == Decimal("4.592793")
    assert result.source_record_count == 8
    assert result.reason_codes == ()


def test_spot_perp_cvd_spread_filters_unavailable_future_inputs() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(4))
    observations = tuple(
        cvd_observation(time, market_type=market_type, cvd_usd=value)
        for time, spot_value, perp_value in zip(
            times,
            ("100", "110", "120", "160"),
            ("100", "120", "140", "145"),
            strict=True,
        )
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )
    unavailable_future = cvd_observation(
        times[-1],
        market_type="spot",
        cvd_usd="999999",
        available_at=times[-1] + timedelta(days=1),
    )

    baseline = spot_perp_cvd_spread(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        zscore_window_periods=3,
        min_zscore_periods=3,
    ).as_record()
    with_future = spot_perp_cvd_spread(
        (*observations, unavailable_future),
        as_of=times[-1] + timedelta(minutes=2),
        zscore_window_periods=3,
        min_zscore_periods=3,
    ).as_record()

    assert with_future == baseline


def test_spot_perp_cvd_spread_reports_missing_inputs_without_zero_fill() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    observations = tuple(
        cvd_observation(
            start + timedelta(hours=offset),
            market_type="spot",
            cvd_usd="100",
        )
        for offset in range(4)
    )

    result = spot_perp_cvd_spread(
        observations,
        as_of=start + timedelta(hours=4),
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    assert result.complete is False
    assert result.cvd_spread is None
    assert result.reason_codes == (
        "PERP_CVD_INPUT_MISSING",
        "SPOT_PERP_CVD_SPREAD_INSUFFICIENT_HISTORY",
    )


def test_spot_perp_cvd_spread_exposes_persistable_payload() -> None:
    start = datetime(2026, 8, 24, tzinfo=UTC)
    times = tuple(start + timedelta(hours=offset) for offset in range(4))
    observations = tuple(
        cvd_observation(time, market_type=market_type, cvd_usd=value)
        for time, spot_value, perp_value in zip(
            times,
            ("100", "110", "120", "160"),
            ("100", "120", "140", "145"),
            strict=True,
        )
        for market_type, value in (("spot", spot_value), ("perp", perp_value))
    )

    result = spot_perp_cvd_spread(
        observations,
        as_of=times[-1] + timedelta(minutes=2),
        zscore_window_periods=3,
        min_zscore_periods=3,
    )

    record = result.as_record()
    assert record["feature_id"] == "CVD_SPREAD"
    assert record["observation_time"] == "2026-08-24T03:00:00+00:00"
    assert record["spot_cvd_feature_id"] == "SPOT_CVD"
    assert record["perp_cvd_feature_id"] == "PERP_CVD"
    assert record["zscore_window_periods"] == 3
    assert record["min_zscore_periods"] == 3
    assert record["spot_cvd"] == "160"
    assert record["perp_cvd"] == "145"
    assert record["source_record_count"] == 8
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_spot_perp_cvd_spread_rejects_invalid_observations_and_windows() -> None:
    with pytest.raises(ValueError, match="market_type"):
        cvd_observation(
            datetime(2026, 8, 24, tzinfo=UTC),
            market_type="futures",
            cvd_usd="100",
        ).as_record()

    with pytest.raises(ValueError, match="zscore_window_periods"):
        spot_perp_cvd_spread(
            (),
            as_of=datetime(2026, 8, 24, tzinfo=UTC),
            zscore_window_periods=0,
        )


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


def test_etf_flow_acceleration_rejects_mismatched_observation_dates() -> None:
    five_day = five_day_etf_flow(
        five_weekday_flows(),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )
    twenty_dates = publication_dates_ending(date(2026, 8, 27), count=20)
    twenty_day = twenty_day_etf_flow(
        flow_rows_for_publication_dates(twenty_dates),
        as_of=datetime(2026, 8, 28, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    with pytest.raises(ValueError, match="observation_date"):
        etf_flow_acceleration(five_day, twenty_day)


def test_etf_flow_acceleration_rejects_wrong_windows() -> None:
    dates = publication_dates_ending(date(2026, 8, 28), count=20)
    five_day = etf_flow_window(
        flow_rows_for_publication_dates(dates[1:]),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        window_days=19,
        funds=("IBIT", "FBTC"),
        end_date=date(2026, 8, 28),
        feature_id="ETF_FLOW_19D",
        normalized_feature_id="ETF_NORM_19D",
    )
    twenty_day = twenty_day_etf_flow(
        flow_rows_for_publication_dates(dates),
        as_of=datetime(2026, 8, 29, tzinfo=UTC),
        funds=("IBIT", "FBTC"),
    )

    with pytest.raises(ValueError, match="5-day window"):
        etf_flow_acceleration(five_day, twenty_day)
