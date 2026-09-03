"""BTC-141: volatility buffer for structural stops."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar

from btc_predictor.risk import (
    ATR_BOUND,
    BUFFER_ATR_MULTIPLIER_GRID,
    BUFFER_BINDING_TERMS,
    BUFFER_PARAMETER_STATUS,
    DEFAULT_BUFFER_ATR_MULTIPLIER,
    DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    LEVEL_NOISE_BOUND,
    VOLATILITY_BUFFER_FEATURE_ID,
    VOLATILITY_BUFFER_POLICY_VERSION,
    VOLATILITY_BUFFER_REASON_CODES,
    VolatilityBufferResult,
    atr_from_daily_bars,
    calculate_volatility_buffer,
    level_noise_from_zone,
    volatility_buffer_grid,
)


def test_metadata_is_stable() -> None:
    assert VOLATILITY_BUFFER_FEATURE_ID == "VOLATILITY_BUFFER"
    assert VOLATILITY_BUFFER_POLICY_VERSION == "VOLATILITY_BUFFER_V1"
    assert DEFAULT_BUFFER_ATR_MULTIPLIER == Decimal("0.30")
    assert DEFAULT_BUFFER_ATR_WINDOW_DAYS == 20
    assert BUFFER_ATR_MULTIPLIER_GRID == (
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("0.75"),
    )
    assert BUFFER_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert BUFFER_BINDING_TERMS == (ATR_BOUND, LEVEL_NOISE_BOUND)


# --- max(0.3 * ATR, LevelNoiseEstimate) ---------------------------------


def test_default_buffer_is_three_tenths_of_atr() -> None:
    result = calculate_volatility_buffer(atr="1000")

    assert result.buffer == Decimal("300.00")
    assert result.atr_component == Decimal("300.00")
    assert result.complete is True
    assert result.binding_term == ATR_BOUND


def test_level_noise_wins_when_it_exceeds_the_atr_term() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="500")

    assert result.buffer == Decimal("500")
    assert result.binding_term == LEVEL_NOISE_BOUND
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_BOUND" in result.reason_codes


def test_atr_term_wins_when_it_exceeds_level_noise() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="200")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND
    assert "VOLATILITY_BUFFER_ATR_BOUND" in result.reason_codes


def test_a_tie_resolves_to_the_atr_term_deterministically() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="300")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND


def test_buffer_is_the_maximum_of_both_terms_across_a_sweep() -> None:
    for noise in range(0, 1000, 50):
        result = calculate_volatility_buffer(atr="1000", level_noise_estimate=noise)
        assert result.buffer == max(Decimal("300.00"), Decimal(noise))


# --- declared research grid ---------------------------------------------


def test_declared_atr_multiplier_grid_is_evaluated() -> None:
    grid = volatility_buffer_grid(atr="1000")

    assert set(grid) == {"0.25", "0.50", "0.75"}
    assert grid["0.25"].buffer == Decimal("250.00")
    assert grid["0.50"].buffer == Decimal("500.00")
    assert grid["0.75"].buffer == Decimal("750.00")
    for result in grid.values():
        assert result.complete is True


def test_grid_respects_level_noise_and_reports_the_binding_term() -> None:
    grid = volatility_buffer_grid(atr="1000", level_noise_estimate="400")

    # 0.25 * 1000 = 250 < 400, so noise binds at the tightest multiplier only.
    assert grid["0.25"].buffer == Decimal("400")
    assert grid["0.25"].binding_term == LEVEL_NOISE_BOUND
    assert grid["0.50"].buffer == Decimal("500.00")
    assert grid["0.50"].binding_term == ATR_BOUND
    assert grid["0.75"].binding_term == ATR_BOUND


def test_grid_does_not_select_a_winner() -> None:
    """BTC-141 reports the sweep; BTC-185 calibrates it."""

    grid = volatility_buffer_grid(atr="1000")
    buffers = [result.buffer for result in grid.values()]

    assert len(set(buffers)) == len(buffers)
    assert BUFFER_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"


# --- missing data --------------------------------------------------------


def test_missing_atr_makes_the_buffer_incomplete_not_zero() -> None:
    result = calculate_volatility_buffer(atr=None, level_noise_estimate="500")

    # A stop must never be placed on a silently absent volatility term.
    assert result.complete is False
    assert result.buffer is None
    assert result.binding_term is None
    assert result.reason_codes == ("VOLATILITY_BUFFER_INPUT_MISSING",)


def test_missing_level_noise_degenerates_to_the_atr_term() -> None:
    result = calculate_volatility_buffer(atr="1000")

    assert result.complete is True
    assert result.buffer == Decimal("300.00")
    assert result.level_noise_estimate is None
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_UNAVAILABLE" in result.reason_codes


def test_zero_level_noise_is_permitted_and_never_binds() -> None:
    result = calculate_volatility_buffer(atr="1000", level_noise_estimate="0")

    assert result.buffer == Decimal("300.00")
    assert result.binding_term == ATR_BOUND


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"atr": "0"}, "atr must be positive"),
        ({"atr": "-5"}, "atr must be positive"),
        ({"atr": "1000", "level_noise_estimate": "-1"}, "must be non-negative"),
        ({"atr": "1000", "atr_multiplier": "-0.1"}, "must be non-negative"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        calculate_volatility_buffer(**kwargs)


def test_a_zero_multiplier_is_allowed_and_lets_level_noise_govern() -> None:
    result = calculate_volatility_buffer(
        atr="1000",
        level_noise_estimate="120",
        atr_multiplier="0",
    )

    assert result.buffer == Decimal("120")
    assert result.binding_term == LEVEL_NOISE_BOUND


# --- LevelNoiseEstimate interpretation -----------------------------------


def test_level_noise_from_zone_is_half_the_zone_width() -> None:
    assert level_noise_from_zone(lower_bound="95", upper_bound="97") == Decimal("1")
    assert level_noise_from_zone(lower_bound="100", upper_bound="100") == Decimal("0")


def test_level_noise_from_zone_composes_with_the_buffer() -> None:
    noise = level_noise_from_zone(lower_bound="9000", upper_bound="9600")
    result = calculate_volatility_buffer(atr="500", level_noise_estimate=noise)

    # Half of a 600-wide zone is 300, which exceeds 0.3 * 500 = 150.
    assert noise == Decimal("300")
    assert result.buffer == Decimal("300")
    assert result.binding_term == LEVEL_NOISE_BOUND


# --- ATR bridge to the BTC-041 bar boundary -----------------------------

ATR_ORIGIN = datetime(2026, 1, 1, tzinfo=UTC)


def daily_bar(day: int, *, timeframe: str = "1d") -> OhlcvBar:
    timestamp = ATR_ORIGIN + timedelta(days=day)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1"),
        provider="ccdata",
        ingested_at=timestamp + timedelta(days=1),
    )


def test_atr_from_daily_bars_uses_the_shared_rolling_primitive() -> None:
    atr = atr_from_daily_bars([daily_bar(day) for day in range(25)], window=20)

    # Constant 2-wide bars give a true range of 2 throughout.
    assert atr == Decimal("2.0")


def test_atr_from_daily_bars_returns_none_while_warming_up() -> None:
    # Warm-up must be None, never a partial-window number.
    assert atr_from_daily_bars([daily_bar(day) for day in range(5)], window=20) is None


def test_atr_from_daily_bars_validates_its_inputs() -> None:
    with pytest.raises(ValueError, match="window must be >= 1"):
        atr_from_daily_bars([daily_bar(0)], window=0)
    with pytest.raises(ValueError, match="canonical 1d bars"):
        atr_from_daily_bars(
            [daily_bar(day, timeframe="1w") for day in range(25)],
            window=20,
        )


def test_a_window_spanning_an_absent_session_has_no_atr() -> None:
    # PRICE_SOURCE_POLICY_V1 keeps a provider outage as an explicit gap, and a
    # true range measured across it is not a session's range. The buffer must
    # be incomplete rather than inflated, so no stop is placed at all.
    days = [day for day in range(25) if day != 20]

    assert atr_from_daily_bars([daily_bar(day) for day in days], window=20) is None


# --- determinism and persistence ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    first = calculate_volatility_buffer(atr="1234.5", level_noise_estimate="410")
    second = calculate_volatility_buffer(atr="1234.5", level_noise_estimate="410")

    assert first.as_record() == second.as_record()


def test_record_is_persistable_with_both_terms() -> None:
    result = calculate_volatility_buffer(
        atr="1000",
        level_noise_estimate="500",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, VolatilityBufferResult)
    assert record["feature_id"] == "VOLATILITY_BUFFER"
    assert record["policy_version"] == "VOLATILITY_BUFFER_V1"
    assert record["buffer"] == "500"
    assert record["atr"] == "1000"
    assert record["atr_multiplier"] == "0.30"
    # Both terms stay reconstructable, not just the winner.
    assert record["atr_component"] == "300.00"
    assert record["level_noise_estimate"] == "500"
    assert record["binding_term"] == "LEVEL_NOISE"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    assert record["complete"] is True


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        calculate_volatility_buffer(atr="1000"),
        calculate_volatility_buffer(atr="1000", level_noise_estimate="500"),
        calculate_volatility_buffer(atr=None),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in VOLATILITY_BUFFER_REASON_CODES


# --- BTC-141 integration hardening --------------------------------------

from datetime import UTC, datetime  # noqa: E402

from btc_predictor.risk import (  # noqa: E402
    BULL_TREND_CONTINUATION_SETUP,
    LEVEL_NOISE_DERIVED_FROM_ZONE,
    LEVEL_NOISE_ESTIMATE_FORMULA,
    LEVEL_NOISE_ESTIMATE_VERSION,
    LEVEL_NOISE_EXPLICITLY_SUPPLIED,
    LEVEL_NOISE_PARAMETER_STATUS,
    LEVEL_NOISE_SOURCES,
    LEVEL_NOISE_UNAVAILABLE,
    select_structural_invalidation,
    volatility_buffer_for_invalidation,
)

HARDENING_AS_OF = datetime(2026, 6, 1, tzinfo=UTC)


def support_zone(lower: str, upper: str) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": "zone",
        "zone_type": "support",
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": "75",
        "member_count": 3,
        "detected_at": datetime(2026, 1, 1, tzinfo=UTC),
    }


def invalidation_for(zones, entry_price: str = "10000"):
    return select_structural_invalidation(
        zones,
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=entry_price,
        as_of=HARDENING_AS_OF,
    )


def test_level_noise_estimate_v1_has_explicit_version_identity() -> None:
    assert LEVEL_NOISE_ESTIMATE_VERSION == "LEVEL_NOISE_ESTIMATE_V1"
    assert LEVEL_NOISE_ESTIMATE_FORMULA == (
        "0.5 * (zone_upper_bound - zone_lower_bound)"
    )
    assert LEVEL_NOISE_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert LEVEL_NOISE_SOURCES == (
        LEVEL_NOISE_DERIVED_FROM_ZONE,
        LEVEL_NOISE_EXPLICITLY_SUPPLIED,
        LEVEL_NOISE_UNAVAILABLE,
    )


@pytest.mark.parametrize(
    ("lower", "upper", "expected"),
    [
        ("9000", "9600", Decimal("300")),
        ("9000", "9200", Decimal("100")),
        ("9000", "10000", Decimal("500")),
        ("100", "100", Decimal("0")),
    ],
)
def test_zone_width_deterministically_drives_level_noise(
    lower: str,
    upper: str,
    expected: Decimal,
) -> None:
    assert level_noise_from_zone(lower_bound=lower, upper_bound=upper) == expected


def test_canonical_path_derives_noise_from_the_selected_zone() -> None:
    invalidation = invalidation_for([support_zone("9000", "9600")])

    result = volatility_buffer_for_invalidation(invalidation, atr="500")

    # Half of a 600-wide zone is 300, which beats 0.3 * 500 = 150.
    assert result.level_noise_estimate == Decimal("300")
    assert result.level_noise_source == LEVEL_NOISE_DERIVED_FROM_ZONE
    assert result.level_noise_version == LEVEL_NOISE_ESTIMATE_VERSION
    assert result.zone_lower_bound == Decimal("9000")
    assert result.zone_upper_bound == Decimal("9600")
    assert result.buffer == Decimal("300")
    assert result.binding_term == LEVEL_NOISE_BOUND
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_DERIVED" in result.reason_codes


def test_canonical_path_tracks_a_changing_zone_width() -> None:
    narrow = volatility_buffer_for_invalidation(
        invalidation_for([support_zone("9000", "9100")]), atr="500"
    )
    wide = volatility_buffer_for_invalidation(
        invalidation_for([support_zone("9000", "9800")]), atr="500"
    )

    assert narrow.level_noise_estimate == Decimal("50")
    assert wide.level_noise_estimate == Decimal("400")
    # A narrow zone lets the ATR term govern; a wide one does not.
    assert narrow.binding_term == ATR_BOUND
    assert wide.binding_term == LEVEL_NOISE_BOUND


def test_a_bounded_zone_cannot_silently_forget_its_noise_calculation() -> None:
    result = calculate_volatility_buffer(
        atr="500",
        level_noise_estimate=None,
        zone_lower_bound="9000",
        zone_upper_bound="9600",
    )

    # Integration defect: a usable zone reached the buffer without deriving
    # noise. This must not degrade quietly to an ATR-only buffer.
    assert result.complete is False
    assert result.buffer is None
    assert result.reason_codes == ("VOLATILITY_BUFFER_LEVEL_NOISE_NOT_DERIVED",)
    assert result.level_noise_source == LEVEL_NOISE_UNAVAILABLE


def test_genuine_unavailability_uses_a_diagnosed_atr_only_fallback() -> None:
    # Genuine unavailability is a caller that brings no zone at all -- the
    # trailing path, for instance, whose structure is a swing rather than a
    # cluster. A *refused* BTC-140 selection is a different state; see below.
    result = volatility_buffer_for_invalidation({}, atr="500")

    assert result.complete is True
    assert result.buffer == Decimal("150.00")
    assert result.level_noise_estimate is None
    assert result.level_noise_source == LEVEL_NOISE_UNAVAILABLE
    assert "VOLATILITY_BUFFER_LEVEL_NOISE_UNAVAILABLE" in result.reason_codes
    assert result.binding_term == ATR_BOUND


def test_a_refused_invalidation_is_not_a_legitimate_atr_only_fallback() -> None:
    # A BTC-140 result either selected a bounded zone or refused; there is no
    # complete selection without one. Reading a refusal as "structure has no
    # usable width" would relabel the upstream cause and hand a complete buffer
    # to consumers that never see BTC-140.
    refused = invalidation_for([])
    assert refused.complete is False

    result = volatility_buffer_for_invalidation(refused, atr="500")

    assert result.complete is False
    assert result.buffer is None
    assert result.reason_codes == ("VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE",)


def test_a_look_ahead_refusal_survives_into_the_buffer() -> None:
    # The composition, not either owner, is what must stay point-in-time safe.
    future_zone = support_zone("9000", "9600")
    future_zone["detected_at"] = HARDENING_AS_OF + timedelta(days=1)
    refused = invalidation_for([future_zone])
    assert "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED" in refused.reason_codes

    result = volatility_buffer_for_invalidation(refused, atr="500")

    assert result.complete is False
    assert result.reason_codes == ("VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE",)


def test_canonical_path_accepts_the_persisted_invalidation_record() -> None:
    invalidation = invalidation_for([support_zone("9000", "9600")])

    from_object = volatility_buffer_for_invalidation(invalidation, atr="500")
    from_record = volatility_buffer_for_invalidation(
        invalidation.as_record(), atr="500"
    )

    assert from_object.as_record() == from_record.as_record()


def test_atr20_identity_is_persisted_and_reconstructable() -> None:
    result = volatility_buffer_for_invalidation(
        invalidation_for([support_zone("9000", "9600")]), atr="500"
    )
    record = result.as_record()

    assert record["atr_window"] == 20
    assert record["atr_multiplier"] == "0.30"
    assert record["atr"] == "500"
    assert record["atr_component"] == "150.00"
    # Everything needed to reproduce the buffer is on the record.
    assert record["level_noise_version"] == "LEVEL_NOISE_ESTIMATE_V1"
    assert record["level_noise_source"] == "DERIVED_FROM_ZONE"
    assert record["level_noise_estimate"] == "300"
    assert record["zone_lower_bound"] == "9000"
    assert record["zone_upper_bound"] == "9600"
    assert record["binding_term"] == "LEVEL_NOISE"
    assert record["buffer"] == "300"


def test_research_atr14_conventions_do_not_change_strategy_semantics() -> None:
    """An ATR14 value is labelled as such and never masquerades as ATR20."""

    strategy = calculate_volatility_buffer(atr="500")
    research = calculate_volatility_buffer(atr="500", atr_window=14)

    assert strategy.atr_window == 20
    assert research.atr_window == 14
    # The window is provenance, not an input to the arithmetic, so the buffer
    # value is unchanged; only the recorded identity differs.
    assert strategy.buffer == research.buffer == Decimal("150.00")
    assert strategy.as_record()["atr_window"] != research.as_record()["atr_window"]


def test_an_invalid_atr_window_or_noise_source_is_rejected() -> None:
    with pytest.raises(ValueError, match="atr_window must be >= 1"):
        calculate_volatility_buffer(atr="500", atr_window=0)
    with pytest.raises(ValueError, match="level_noise_source must be one of"):
        calculate_volatility_buffer(atr="500", level_noise_source="GUESSED")


def test_existing_numerical_outputs_are_unchanged_by_hardening() -> None:
    """The committed BTC-141 arithmetic must be byte-identical."""

    assert calculate_volatility_buffer(atr="1000").buffer == Decimal("300.00")
    assert calculate_volatility_buffer(
        atr="1000", level_noise_estimate="500"
    ).buffer == Decimal("500")
    assert calculate_volatility_buffer(
        atr="1000", level_noise_estimate="200"
    ).buffer == Decimal("300.00")
    grid = volatility_buffer_grid(atr="1000")
    assert [str(item.buffer) for item in grid.values()] == [
        "250.00",
        "500.00",
        "750.00",
    ]
