from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import OhlcvBar
from btc_predictor.db.derived import build_reference_composite_insert_ignore
from btc_predictor.research.reference_composite import (
    BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    CLIPPED_CENTER_DEFINITION,
    COINBASE_PROVIDER_ID,
    CONFIRMED_EXTREMES_DEFINITION,
    MEDIAN_OHLC_DEFINITION,
    REFERENCE_DEGRADED,
    REFERENCE_OK,
    REFERENCE_UNAVAILABLE,
    THREE_PROVIDER_CONSENSUS,
    TWO_PROVIDER_CONSENSUS,
    VENUE_DISAGREEMENT,
    CompositeMethodDefinition,
    build_composite_observation,
    provider_candle_input,
)


TIMESTAMP = datetime(2025, 10, 10, 21, tzinfo=UTC)
DECISION_TIME = TIMESTAMP + timedelta(hours=1, minutes=5)
PROVIDER_METADATA = {
    BITSTAMP_PROVIDER_ID: ("bitstamp", "BTC/USD"),
    COINBASE_PROVIDER_ID: ("coinbase", "BTC-USD"),
    BITFINEX_PROVIDER_ID: ("bitfinex", "BTC/USD"),
}


def candle_input(
    provider: str,
    *,
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    available_minutes_after_open: int = 60,
):
    exchange, symbol = PROVIDER_METADATA[provider]
    bar = OhlcvBar(
        timestamp=TIMESTAMP,
        exchange=exchange,
        symbol=symbol,
        timeframe="1h",
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        provider=provider,
        ingested_at=DECISION_TIME,
    )
    return provider_candle_input(
        bar,
        available_at=TIMESTAMP + timedelta(minutes=available_minutes_after_open),
    )


def build(inputs, method=MEDIAN_OHLC_DEFINITION, trailing_atr="100"):
    return build_composite_observation(
        inputs,
        observation_time=TIMESTAMP,
        decision_time=DECISION_TIME,
        method=method,
        trailing_atr=Decimal(trailing_atr) if trailing_atr is not None else None,
    )


def ordinary_inputs():
    return (
        candle_input(
            BITSTAMP_PROVIDER_ID,
            open_price="100",
            high="110",
            low="90",
            close="105",
        ),
        candle_input(
            COINBASE_PROVIDER_ID,
            open_price="101",
            high="111",
            low="91",
            close="105.1",
        ),
        candle_input(
            BITFINEX_PROVIDER_ID,
            open_price="102",
            high="112",
            low="92",
            close="105.2",
        ),
    )


def test_three_venue_median_composite_is_exact_and_deterministic() -> None:
    first = build(ordinary_inputs())
    second = build(tuple(reversed(ordinary_inputs())))

    assert first.quality_state == REFERENCE_OK
    assert first.confirmation_state == THREE_PROVIDER_CONSENSUS
    assert (first.open, first.high, first.low, first.close) == (
        Decimal("101"),
        Decimal("111"),
        Decimal("91"),
        Decimal("105.1"),
    )
    assert first.as_record() == second.as_record()


def test_two_venue_mode_is_explicitly_degraded() -> None:
    result = build(ordinary_inputs()[:2], method=CONFIRMED_EXTREMES_DEFINITION)

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.confirmation_state == TWO_PROVIDER_CONSENSUS
    assert result.input_count == 2
    assert result.input_providers_available == (BITSTAMP_PROVIDER_ID, COINBASE_PROVIDER_ID)


@pytest.mark.parametrize("inputs", [(), (candle_input(BITSTAMP_PROVIDER_ID),)])
def test_zero_or_one_venue_is_unavailable(inputs) -> None:
    result = build(inputs)

    assert result.quality_state == REFERENCE_UNAVAILABLE
    assert not result.usable
    assert result.open is None
    assert "COMPOSITE_INPUT_COUNT_INSUFFICIENT" in result.reason_codes


def test_confirmed_extremes_reject_isolated_high_and_low_outliers() -> None:
    inputs = (
        candle_input(BITSTAMP_PROVIDER_ID, high="150", low="50"),
        candle_input(COINBASE_PROVIDER_ID, high="111", low="89"),
        candle_input(BITFINEX_PROVIDER_ID, high="112", low="90"),
    )

    result = build(inputs, method=CONFIRMED_EXTREMES_DEFINITION)

    assert result.high == Decimal("112")
    assert result.low == Decimal("89")


def test_confirmed_extremes_keep_two_venue_consensus_against_one_outlier() -> None:
    inputs = (
        candle_input(BITSTAMP_PROVIDER_ID, high="120", low="80"),
        candle_input(COINBASE_PROVIDER_ID, high="150", low="60"),
        candle_input(BITFINEX_PROVIDER_ID, high="151", low="61"),
    )

    result = build(inputs, method=CONFIRMED_EXTREMES_DEFINITION)

    assert result.high == Decimal("151")
    assert result.low == Decimal("60")


def test_clipped_center_limits_isolated_extreme_influence() -> None:
    inputs = (
        candle_input(BITSTAMP_PROVIDER_ID, high="200", low="20"),
        candle_input(COINBASE_PROVIDER_ID, high="110", low="90"),
        candle_input(BITFINEX_PROVIDER_ID, high="111", low="91"),
    )

    result = build(inputs, method=CLIPPED_CENTER_DEFINITION)

    assert result.high == Decimal("115.6666666666666666666666667")
    assert result.low == Decimal("85.33333333333333333333333333")
    assert result.high < Decimal("200")
    assert result.low > Decimal("20")


def test_close_disagreement_with_no_consensus_publishes_no_candle() -> None:
    inputs = (
        candle_input(BITSTAMP_PROVIDER_ID, close="100"),
        candle_input(COINBASE_PROVIDER_ID, close="101"),
        candle_input(BITFINEX_PROVIDER_ID, high="125", close="120"),
    )

    result = build(inputs)

    assert result.quality_state == VENUE_DISAGREEMENT
    assert result.open is result.high is result.low is result.close is None
    assert "COMPOSITE_CLOSE_DISAGREEMENT" in result.reason_codes


def test_three_venue_close_outlier_degrades_when_two_venues_still_agree() -> None:
    inputs = (
        candle_input(BITSTAMP_PROVIDER_ID, close="100"),
        candle_input(COINBASE_PROVIDER_ID, close="100.4"),
        candle_input(BITFINEX_PROVIDER_ID, high="105", close="102"),
    )

    result = build(inputs)

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.confirmation_state == TWO_PROVIDER_CONSENSUS
    assert result.close == Decimal("100.4")
    assert "COMPOSITE_CLOSE_PARTIAL_CONSENSUS" in result.reason_codes


def test_late_provider_is_excluded_at_the_fixed_decision_cutoff() -> None:
    late = candle_input(BITFINEX_PROVIDER_ID, available_minutes_after_open=66)

    result = build((*ordinary_inputs()[:2], late))

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.confirmation_state == TWO_PROVIDER_CONSENSUS
    assert result.bitfinex_observation_id is None
    assert result.available_at == DECISION_TIME
    assert "COMPOSITE_PROVIDER_LATE" in result.reason_codes


def test_point_in_time_rules_reject_early_inputs_and_variable_waiting() -> None:
    with pytest.raises(ValueError, match="before bar close"):
        candle_input(BITSTAMP_PROVIDER_ID, available_minutes_after_open=59)

    with pytest.raises(ValueError, match="policy decision delay"):
        build_composite_observation(
            ordinary_inputs(),
            observation_time=TIMESTAMP,
            decision_time=TIMESTAMP + timedelta(hours=2),
            method=MEDIAN_OHLC_DEFINITION,
            trailing_atr=Decimal("100"),
        )


def test_composite_preserves_raw_provenance_and_prohibits_splicing() -> None:
    result = build(ordinary_inputs())
    record = result.as_record()
    database_record = result.as_database_record()

    assert len(record["bitstamp_observation_id"]) == 64
    assert len(record["coinbase_observation_id"]) == 64
    assert len(record["bitfinex_observation_id"]) == 64
    assert record["reference_policy_version"] == "BTC_REFERENCE_COMPOSITE_V1"
    assert record["fallback_used"] is False
    assert database_record["observation_time"] == TIMESTAMP
    assert database_record["available_at"] == DECISION_TIME
    assert database_record["open"] == Decimal("101")
    with pytest.raises(ValueError, match="splicing is prohibited"):
        replace(result, fallback_used=True).as_record()


def test_composite_candle_invariants_hold_for_every_candidate() -> None:
    for method in (
        MEDIAN_OHLC_DEFINITION,
        CONFIRMED_EXTREMES_DEFINITION,
        CLIPPED_CENTER_DEFINITION,
    ):
        bar = build(ordinary_inputs(), method=method).as_ohlcv_bar()
        assert bar.high >= max(bar.open, bar.close)
        assert bar.low <= min(bar.open, bar.close)
        assert bar.high >= bar.low


def test_method_and_version_semantics_are_frozen() -> None:
    invalid = CompositeMethodDefinition(
        method="median_ohlc",
        method_version="CONFIRMED_EXTREMES_V1",
        confirmation_tolerance_atr=None,
        formula="invalid semantic mutation",
    )

    with pytest.raises(ValueError, match="frozen V1 pairing"):
        invalid.as_record()


def test_immutable_database_insert_uses_the_composite_primary_key() -> None:
    statement = build_reference_composite_insert_ignore(
        (build(ordinary_inputs()).as_database_record(),),
    )
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO derived.btc_reference_composite" in sql
    assert "ON CONFLICT (reference_policy_version, observation_time, composite_method_version) DO NOTHING" in sql


def test_october_2025_consensus_stop_regression() -> None:
    inputs = (
        candle_input(
            BITSTAMP_PROVIDER_ID,
            open_price="113000",
            high="114000",
            low="109683",
            close="111000",
        ),
        candle_input(
            COINBASE_PROVIDER_ID,
            open_price="113050",
            high="114050",
            low="107000",
            close="110950",
        ),
        candle_input(
            BITFINEX_PROVIDER_ID,
            open_price="112950",
            high="113950",
            low="103310",
            close="111050",
        ),
    )
    stop = Decimal("107270")

    results = {
        method.method_version: build(inputs, method=method, trailing_atr="3023")
        for method in (
            MEDIAN_OHLC_DEFINITION,
            CONFIRMED_EXTREMES_DEFINITION,
            CLIPPED_CENTER_DEFINITION,
        )
    }

    assert Decimal("109683") > stop
    assert Decimal("107000") <= stop
    assert Decimal("103310") <= stop
    assert all(result.low <= stop for result in results.values())
