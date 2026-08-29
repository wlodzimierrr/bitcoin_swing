import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.research.reference_composite import (
    BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID,
    MEDIAN_OHLC_DEFINITION,
    REFERENCE_DEGRADED,
    REFERENCE_OK,
    REFERENCE_UNAVAILABLE,
    VENUE_DISAGREEMENT,
    build_composite_observation,
    provider_candle_input,
)
from btc_predictor.research.reference_composite_v2 import (
    BUCKET_COMPLETE_DEGRADED,
    BUCKET_COMPLETE_VENUE_DISAGREEMENT,
    BUCKET_INCOMPLETE_UNUSABLE,
    FROZEN_V2_DEFINITION_SHA256,
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    V2_APPROVAL_GATES,
    V2_ATR_MATERIALITY_GRID,
    V2_METHOD_VERSION,
    V2_PRIMARY_ATR_MATERIALITY_THRESHOLD,
    V2_PROTOCOL_STATUS,
    V2_PROTOCOL_VERSION,
    UntouchedValidationSampleGuardError,
    aggregate_v2_reference_bucket,
    build_v2_reference_observation,
    frozen_v2_protocol_definition,
    guard_untouched_validation_sample,
    v2_definition_sha256,
    verify_frozen_dependency_artifacts,
    verify_frozen_v2_protocol_artifacts,
)


TIMESTAMP = datetime(2025, 1, 6, tzinfo=UTC)
DECISION_TIME = TIMESTAMP + timedelta(hours=1, minutes=5)
PROVIDER_METADATA = {
    BITSTAMP_PROVIDER_ID: ("bitstamp", "BTC/USD"),
    COINBASE_PROVIDER_ID: ("coinbase", "BTC-USD"),
    BITFINEX_PROVIDER_ID: ("bitfinex", "BTC/USD"),
}


def candle_input(
    provider: str,
    *,
    timestamp: datetime = TIMESTAMP,
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    available_minutes_after_open: int = 60,
):
    exchange, symbol = PROVIDER_METADATA[provider]
    return provider_candle_input(
        OhlcvBar(
            timestamp=timestamp,
            exchange=exchange,
            symbol=symbol,
            timeframe="1h",
            open=Decimal(open_price),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
            volume=Decimal("1"),
            provider=provider,
            ingested_at=timestamp + timedelta(hours=1),
        ),
        available_at=timestamp + timedelta(minutes=available_minutes_after_open),
    )


def build(inputs, *, timestamp: datetime = TIMESTAMP, trailing_atr: str | None = "100"):
    return build_v2_reference_observation(
        inputs,
        observation_time=timestamp,
        decision_time=timestamp + timedelta(hours=1, minutes=5),
        trailing_atr=Decimal(trailing_atr) if trailing_atr is not None else None,
    )


def ordinary_inputs(*, timestamp: datetime = TIMESTAMP):
    return (
        candle_input(
            BITSTAMP_PROVIDER_ID,
            timestamp=timestamp,
            open_price="100",
            high="110",
            low="90",
            close="105",
        ),
        candle_input(
            COINBASE_PROVIDER_ID,
            timestamp=timestamp,
            open_price="101",
            high="111",
            low="91",
            close="105.1",
        ),
        candle_input(
            BITFINEX_PROVIDER_ID,
            timestamp=timestamp,
            open_price="102",
            high="112",
            low="92",
            close="105.2",
        ),
    )


def test_v2_definition_serialization_and_hash_are_deterministic() -> None:
    first = frozen_v2_protocol_definition()
    second = frozen_v2_protocol_definition()

    assert first == second
    assert first["status"] == V2_PROTOCOL_STATUS
    assert first["reference_policy_version"] == V2_PROTOCOL_VERSION
    assert first["method"]["version"] == V2_METHOD_VERSION
    assert first["method"]["open"] == "median(available provider opens)"
    assert first["method"]["high"] == "median(available provider highs)"
    assert first["method"]["low"] == "median(available provider lows)"
    assert first["method"]["close"] == "median(available provider closes)"
    assert first["method"]["volume"] == "not_composited_provider_specific_only"
    assert first["providers"]["instruments"][BITFINEX_PROVIDER_ID] == {
        "exchange": "bitfinex",
        "normalized_symbol": "BTC/USD",
        "api_symbol": "tBTCUSD",
    }
    assert first["definition_sha256"] == v2_definition_sha256(first)
    assert first["definition_sha256"] == FROZEN_V2_DEFINITION_SHA256


def test_v2_protocol_freezes_atr_grid_and_primary_materiality() -> None:
    definition = frozen_v2_protocol_definition()

    assert definition["atr_materiality"]["grid"] == [
        str(value) for value in V2_ATR_MATERIALITY_GRID
    ]
    assert definition["atr_materiality"]["primary_threshold"] == str(
        V2_PRIMARY_ATR_MATERIALITY_THRESHOLD
    )
    assert all(
        set(("metric", "threshold", "direction", "rationale", "hard", "source_of_rationale"))
        <= set(item)
        for item in definition["approval_gates"]
    )
    assert len(V2_APPROVAL_GATES) == 39
    assert len({item.metric for item in V2_APPROVAL_GATES}) == 39
    assert sum(item.hard for item in V2_APPROVAL_GATES) == 34
    assert sum(not item.hard for item in V2_APPROVAL_GATES) == 5


def test_three_provider_ok_reference_publishes_exact_median_and_provenance() -> None:
    result = build(tuple(reversed(ordinary_inputs())))
    record = result.as_record()

    assert result.quality_state == REFERENCE_OK
    assert result.reference_price_available
    assert (result.open, result.high, result.low, result.close) == (
        Decimal("101"),
        Decimal("111"),
        Decimal("91"),
        Decimal("105.1"),
    )
    assert record["providers_available"] == [
        BITSTAMP_PROVIDER_ID,
        COINBASE_PROVIDER_ID,
        BITFINEX_PROVIDER_ID,
    ]
    assert set(record["provider_observation_ids"]) == set(PROVIDER_METADATA)
    assert set(record["provider_ohlc"]) == set(PROVIDER_METADATA)
    assert set(record["provider_available_at"]) == set(PROVIDER_METADATA)
    assert record["available_at"] == DECISION_TIME.isoformat()
    assert record["fallback_used"] is False


def test_three_provider_venue_disagreement_still_publishes_median() -> None:
    result = build(
        (
            candle_input(BITSTAMP_PROVIDER_ID, close="100"),
            candle_input(COINBASE_PROVIDER_ID, close="110"),
            candle_input(BITFINEX_PROVIDER_ID, high="130", close="120"),
        )
    )

    assert result.quality_state == VENUE_DISAGREEMENT
    assert result.reference_price_available
    assert result.close == Decimal("110")
    assert "V2_CLOSE_DISAGREEMENT_PUBLISHED" in result.reason_codes


def test_three_provider_partial_close_consensus_is_degraded() -> None:
    result = build(
        (
            candle_input(BITSTAMP_PROVIDER_ID, close="100"),
            candle_input(COINBASE_PROVIDER_ID, close="100.4"),
            candle_input(BITFINEX_PROVIDER_ID, close="103"),
        )
    )

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.reference_price_available
    assert result.close == Decimal("100.4")


def test_three_provider_range_disagreement_keeps_severity_and_publishes() -> None:
    result = build(
        (
            candle_input(BITSTAMP_PROVIDER_ID, high="160", low="40"),
            candle_input(COINBASE_PROVIDER_ID, high="110", low="90"),
            candle_input(BITFINEX_PROVIDER_ID, high="111", low="89"),
        )
    )

    assert result.quality_state == VENUE_DISAGREEMENT
    assert result.reference_price_available
    assert (result.high, result.low) == (Decimal("111"), Decimal("89"))
    assert "V2_THREE_PROVIDER_RANGE_DISAGREEMENT" in result.reason_codes


def test_two_provider_agreement_publishes_degraded_reference() -> None:
    result = build(ordinary_inputs()[:2])

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.reference_price_available
    assert result.input_count == 2


@pytest.mark.parametrize(
    "inputs,trailing_atr,reason",
    [
        (
            (
                candle_input(BITSTAMP_PROVIDER_ID, close="100"),
                candle_input(COINBASE_PROVIDER_ID, close="110"),
            ),
            "100",
            "V2_TWO_PROVIDER_CLOSE_DISAGREEMENT",
        ),
        (
            (
                candle_input(BITSTAMP_PROVIDER_ID, high="160", low="40"),
                candle_input(COINBASE_PROVIDER_ID, high="110", low="90"),
            ),
            "100",
            "V2_TWO_PROVIDER_RANGE_DISAGREEMENT",
        ),
        (
            (
                candle_input(BITSTAMP_PROVIDER_ID, high="125", low="75"),
                candle_input(COINBASE_PROVIDER_ID, high="105", low="95"),
            ),
            "100",
            "V2_TWO_PROVIDER_RANGE_DISAGREEMENT",
        ),
        (ordinary_inputs()[:2], None, "V2_TRAILING_ATR_UNAVAILABLE"),
    ],
)
def test_two_provider_failed_agreement_is_unavailable(inputs, trailing_atr, reason) -> None:
    result = build(inputs, trailing_atr=trailing_atr)

    assert result.quality_state == REFERENCE_UNAVAILABLE
    assert not result.reference_price_available
    assert result.open is result.high is result.low is result.close is None
    assert reason in result.reason_codes


@pytest.mark.parametrize("inputs", [(), (candle_input(BITSTAMP_PROVIDER_ID),)])
def test_one_or_zero_provider_is_unavailable(inputs) -> None:
    result = build(inputs)

    assert result.quality_state == REFERENCE_UNAVAILABLE
    assert not result.reference_price_available
    assert "V2_INPUT_COUNT_INSUFFICIENT" in result.reason_codes


def test_late_provider_is_excluded_without_variable_waiting() -> None:
    late = candle_input(BITFINEX_PROVIDER_ID, available_minutes_after_open=66)

    result = build((*ordinary_inputs()[:2], late))
    record = result.as_record()

    assert result.quality_state == REFERENCE_DEGRADED
    assert result.providers_available == (BITSTAMP_PROVIDER_ID, COINBASE_PROVIDER_ID)
    assert BITFINEX_PROVIDER_ID not in record["provider_observation_ids"]
    assert "V2_PROVIDER_LATE" in result.reason_codes


def test_decision_time_and_no_splicing_are_enforced() -> None:
    with pytest.raises(ValueError, match="bar close plus five minutes"):
        build_v2_reference_observation(
            ordinary_inputs(),
            observation_time=TIMESTAMP,
            decision_time=DECISION_TIME + timedelta(minutes=1),
            trailing_atr=Decimal("100"),
        )

    result = build(ordinary_inputs())
    with pytest.raises(ValueError, match="fallback splicing"):
        replace(result, fallback_used=True).as_record()


def test_invalid_provider_candle_cannot_enter_v2_provenance() -> None:
    invalid = candle_input(
        BITSTAMP_PROVIDER_ID,
        open_price="100",
        high="99",
        low="90",
        close="105",
    )

    with pytest.raises(ValueError, match="candle invariants"):
        build((invalid, *ordinary_inputs()[1:]))


def test_provider_symbol_must_match_frozen_instrument() -> None:
    invalid = candle_input(BITSTAMP_PROVIDER_ID)
    invalid = replace(invalid, bar=replace(invalid.bar, symbol="BTC-USD"))

    with pytest.raises(ValueError, match="frozen V2 instrument"):
        build((invalid, *ordinary_inputs()[1:]))


def hourly_observations(start: datetime, count: int = 24):
    return tuple(
        build(
            ordinary_inputs(timestamp=start + timedelta(hours=offset)),
            timestamp=start + timedelta(hours=offset),
        )
        for offset in range(count)
    )


def test_complete_daily_bucket_persists_degraded_quality_metadata() -> None:
    observations = list(hourly_observations(TIMESTAMP))
    timestamp = observations[5].observation_time
    observations[5] = build(
        ordinary_inputs(timestamp=timestamp)[:2],
        timestamp=timestamp,
    )

    bucket = aggregate_v2_reference_bucket(
        observations,
        bucket_start=TIMESTAMP,
        timeframe="1d",
    )

    assert bucket.bucket_complete and bucket.bucket_usable
    assert bucket.bucket_status == BUCKET_COMPLETE_DEGRADED
    assert bucket.expected_bar_count == bucket.observed_bar_count == 24
    assert bucket.degraded_bar_count == 1
    assert bucket.missing_bar_count == 0
    assert bucket.open is not None and bucket.close is not None


def test_complete_daily_bucket_keeps_venue_disagreement_warning_and_ohlc() -> None:
    observations = list(hourly_observations(TIMESTAMP))
    timestamp = observations[8].observation_time
    observations[8] = build(
        (
            candle_input(BITSTAMP_PROVIDER_ID, timestamp=timestamp, close="100"),
            candle_input(COINBASE_PROVIDER_ID, timestamp=timestamp, close="110"),
            candle_input(BITFINEX_PROVIDER_ID, timestamp=timestamp, high="130", close="120"),
        ),
        timestamp=timestamp,
    )

    bucket = aggregate_v2_reference_bucket(
        observations,
        bucket_start=TIMESTAMP,
        timeframe="1d",
    )

    assert bucket.bucket_status == BUCKET_COMPLETE_VENUE_DISAGREEMENT
    assert bucket.bucket_usable
    assert bucket.venue_disagreement_bar_count == 1
    assert bucket.open is not None


def test_incomplete_bucket_is_persisted_but_never_publishes_partial_ohlc() -> None:
    observations = hourly_observations(TIMESTAMP, count=23)

    bucket = aggregate_v2_reference_bucket(
        observations,
        bucket_start=TIMESTAMP,
        timeframe="1d",
    )
    record = bucket.as_record()

    assert bucket.bucket_status == BUCKET_INCOMPLETE_UNUSABLE
    assert not bucket.bucket_complete
    assert not bucket.bucket_usable
    assert bucket.quality_state == REFERENCE_UNAVAILABLE
    assert bucket.expected_bar_count == 24
    assert bucket.observed_bar_count == 23
    assert bucket.missing_bar_count == 1
    assert record["composite_ohlc"] is None
    assert record["missing_observation_times"] == [
        (TIMESTAMP + timedelta(hours=23)).isoformat()
    ]


def test_weekly_bucket_has_stable_168_hour_contract() -> None:
    weekly = hourly_observations(TIMESTAMP, count=168)

    bucket = aggregate_v2_reference_bucket(
        weekly,
        bucket_start=TIMESTAMP,
        timeframe="1w",
    )

    assert bucket.expected_bar_count == 168
    assert bucket.observed_bar_count == 168
    assert bucket.bucket_complete and bucket.bucket_usable


def test_higher_timeframe_bucket_rejects_off_grid_observation() -> None:
    timestamp = TIMESTAMP + timedelta(minutes=30)
    observation = build(ordinary_inputs(timestamp=timestamp), timestamp=timestamp)

    with pytest.raises(ValueError, match="hourly bucket boundary"):
        aggregate_v2_reference_bucket(
            (observation,),
            bucket_start=TIMESTAMP,
            timeframe="1d",
        )


def test_untouched_period_guard_blocks_overlap_without_reading_data() -> None:
    for start, end in (
        (UNTOUCHED_OOS_START, UNTOUCHED_OOS_END),
        (UNTOUCHED_OOS_START - timedelta(hours=1), UNTOUCHED_OOS_START),
        (UNTOUCHED_OOS_END, UNTOUCHED_OOS_END + timedelta(hours=1)),
    ):
        with pytest.raises(UntouchedValidationSampleGuardError):
            guard_untouched_validation_sample(
                start=start,
                end=end,
                purpose="exploratory-test",
            )

    guard_untouched_validation_sample(
        start=UNTOUCHED_OOS_END + timedelta(hours=1),
        end=UNTOUCHED_OOS_END + timedelta(hours=2),
        purpose="synthetic-test",
    )


def test_v1_disagreement_behavior_remains_immutable() -> None:
    result = build_composite_observation(
        (
            candle_input(BITSTAMP_PROVIDER_ID, close="100"),
            candle_input(COINBASE_PROVIDER_ID, close="110"),
            candle_input(BITFINEX_PROVIDER_ID, high="130", close="120"),
        ),
        observation_time=TIMESTAMP,
        decision_time=DECISION_TIME,
        method=MEDIAN_OHLC_DEFINITION,
        trailing_atr=Decimal("100"),
    )

    assert result.quality_state == VENUE_DISAGREEMENT
    assert not result.usable
    assert result.open is result.high is result.low is result.close is None


def test_frozen_dependency_artifacts_are_unchanged() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    verify_frozen_dependency_artifacts(repository_root)


def test_committed_v2_protocol_artifacts_match_frozen_definition() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    artifact_dir = (
        repository_root
        / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2"
    )

    verify_frozen_v2_protocol_artifacts(artifact_dir)
    committed = json.loads((artifact_dir / "protocol_definition.json").read_text())
    assert committed == frozen_v2_protocol_definition()
