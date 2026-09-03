"""EPIC O integration: the risk engine composed end to end.

The ticket suites prove each owner in isolation. This suite exercises the
composition the epic actually claims:

    BTC-097 clusters
    -> BTC-140 structural invalidation
    -> BTC-141 volatility buffer (ATR via the BTC-041 bar boundary)
    -> BTC-142 initial stop
    -> BTC-143 R/R filter        BTC-144 risk budget
                                  -> BTC-145 position size
                                  -> BTC-146 aggregate risk at stop

and the properties that only exist across those seams: point-in-time
composition, fail-closed propagation, one owner per threshold, the money
identity, and long/short symmetry.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.levels.clustering import cluster_price_levels
from btc_predictor.quant.comparisons import decision_equal
from btc_predictor.risk import (
    BEARISH_DISTRIBUTION_SETUP,
    BULLISH_RESET_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    DEFAULT_BUFFER_ATR_MULTIPLIER,
    DEFAULT_BUFFER_ATR_WINDOW_DAYS,
    atr_from_daily_bars,
    calculate_initial_position_size,
    calculate_risk_at_stop,
    calculate_risk_budget,
    calculate_volatility_buffer,
    initial_position_size_for_trade,
    initial_stop_for_setup,
    minimum_reward_risk_from_config,
    reward_risk_for_stop,
    select_structural_invalidation,
    volatility_buffer_for_invalidation,
)

CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
AS_OF = datetime(2026, 6, 1, tzinfo=UTC)
DETECTED = datetime(2026, 1, 1, tzinfo=UTC)
BAR_ORIGIN = datetime(2026, 4, 1, tzinfo=UTC)
NAV = Decimal("1000000")
ENTRY = Decimal("10000")


# --- fixtures -------------------------------------------------------------


def zone(
    cluster_id: str,
    lower: str,
    upper: str,
    *,
    zone_type: str,
    detected_at: datetime = DETECTED,
    confluence: str = "75",
    timeframe: str = "1w",
) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": cluster_id,
        "zone_type": zone_type,
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": confluence,
        "member_count": 3,
        "detected_at": detected_at,
        "members": [{"source_timeframe": timeframe}],
    }


def daily_bars(count: int, *, skip: int | None = None) -> tuple[OhlcvBar, ...]:
    """Constant 2-wide daily sessions, so the true range is 2 throughout."""

    days = [day for day in range(count) if day != skip]
    bars = []
    for day in days:
        timestamp = BAR_ORIGIN + timedelta(days=day)
        bars.append(
            OhlcvBar(
                timestamp=timestamp,
                exchange="coinbase",
                symbol="BTC-USD",
                timeframe="1d",
                open=Decimal("10000"),
                high=Decimal("10001"),
                low=Decimal("9999"),
                close=Decimal("10000"),
                volume=Decimal("1"),
                provider="ccdata",
                ingested_at=timestamp + timedelta(days=1),
            )
        )
    return tuple(bars)


def long_chain(
    *,
    as_of: datetime = AS_OF,
    clusters=None,
    atr: object = "500",
    conviction: str = "92",
    resistance=None,
):
    """The whole long chain, returned stage by stage."""

    invalidation = select_structural_invalidation(
        clusters if clusters is not None else [zone("s1", "9400", "9600", zone_type="support")],
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=ENTRY,
        as_of=as_of,
        config_metadata=METADATA,
    )
    buffer = volatility_buffer_for_invalidation(
        invalidation, atr=atr, config_metadata=METADATA
    )
    stop = initial_stop_for_setup(invalidation, buffer, config_metadata=METADATA)
    rr = reward_risk_for_stop(
        stop,
        resistance_clusters=(
            resistance
            if resistance is not None
            else [zone("r1", "11575", "11800", zone_type="resistance")]
        ),
        as_of=as_of,
        setup=BULL_TREND_CONTINUATION_SETUP,
        config=CONFIG,
        config_metadata=METADATA,
    )
    budget = calculate_risk_budget(
        entry_conviction=conviction,
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )
    size = initial_position_size_for_trade(budget, stop, config_metadata=METADATA)
    return invalidation, buffer, stop, rr, budget, size


def short_chain(*, as_of: datetime = AS_OF, support=None):
    invalidation = select_structural_invalidation(
        [zone("r1", "10400", "10600", zone_type="resistance")],
        setup=BEARISH_DISTRIBUTION_SETUP,
        entry_price=ENTRY,
        as_of=as_of,
        config_metadata=METADATA,
    )
    buffer = volatility_buffer_for_invalidation(
        invalidation, atr="500", config_metadata=METADATA
    )
    stop = initial_stop_for_setup(invalidation, buffer, config_metadata=METADATA)
    rr = reward_risk_for_stop(
        stop,
        resistance_clusters=(
            support
            if support is not None
            else [zone("s1", "8200", "8425", zone_type="support")]
        ),
        as_of=as_of,
        setup=BEARISH_DISTRIBUTION_SETUP,
        config=CONFIG,
        config_metadata=METADATA,
    )
    return invalidation, buffer, stop, rr


# --- 1. the whole chain, with every intermediate state pinned -------------


def test_the_long_chain_composes_to_one_coherent_trade() -> None:
    invalidation, buffer, stop, rr, budget, size = long_chain()

    # BTC-140 takes the far edge of the zone, never its centre.
    assert invalidation.complete is True
    assert invalidation.invalidation_price == Decimal("9400")
    # BTC-141 derives level noise from that same zone, in one place only.
    assert buffer.level_noise_estimate == Decimal("100")
    assert buffer.buffer == Decimal("150.00")
    # BTC-142 = invalidation - buffer, and owns the stop's own geometry.
    assert stop.stop_price == Decimal("9250.00")
    assert stop.stop_distance_fraction == Decimal("0.075")
    # BTC-143 measures risk to that stop and reward to the near zone edge.
    assert rr.risk == Decimal("750.00")
    assert rr.reward == Decimal("1575")
    assert rr.passes is True
    # BTC-144 -> BTC-145.
    assert budget.risk_fraction_nav == Decimal("0.006")
    assert size.position_notional == Decimal("80000.000")
    assert size.position_quantity == Decimal("8.0000000")


def test_the_realized_position_spends_exactly_the_conviction_budget() -> None:
    _, _, stop, _, budget, size = long_chain()

    exposure = calculate_risk_at_stop(
        [
            {
                "tranche_id": "t1",
                "quantity": size.position_quantity,
                "entry_price": stop.entry_price,
            }
        ],
        stop_price=stop.stop_price,
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )

    # The identity the epic exists to guarantee, computed independently of the
    # sizing owner: notional * stop distance == the budgeted NAV fraction.
    assert exposure.risk_at_stop == Decimal("8.0000000") * Decimal("750.00")
    assert decision_equal(exposure.risk_at_stop, budget.risk_budget_amount)
    assert decision_equal(exposure.risk_fraction_nav, budget.risk_fraction_nav)
    assert exposure.within_maximum is True


def test_the_short_chain_mirrors_the_long_chain_exactly() -> None:
    invalidation, buffer, stop, rr = short_chain()

    # Mirrored geometry: the far edge upward, the buffer added, reward down.
    assert invalidation.direction == "short"
    assert invalidation.invalidation_price == Decimal("10600")
    assert buffer.buffer == Decimal("150.00")
    assert stop.stop_price == Decimal("10750.00")
    assert stop.stop_distance_fraction == Decimal("0.075")
    assert rr.risk == Decimal("750.00")
    assert rr.reward == Decimal("1575")

    long_exposure = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": "8", "entry_price": ENTRY}],
        stop_price=Decimal("9250.00"),
        nav=NAV,
        direction="long",
        config=CONFIG,
        config_metadata=METADATA,
    )
    short_exposure = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": "8", "entry_price": ENTRY}],
        stop_price=stop.stop_price,
        nav=NAV,
        direction="short",
        config=CONFIG,
        config_metadata=METADATA,
    )

    # Equal distance either side of entry is equal risk.
    assert short_exposure.risk_at_stop == long_exposure.risk_at_stop


# --- 2. point-in-time composition ----------------------------------------


def test_appending_later_structure_never_changes_an_earlier_decision() -> None:
    known = [zone("s1", "9400", "9600", zone_type="support")]
    later = [
        *known,
        zone("s2", "9700", "9750", zone_type="support", detected_at=AS_OF + timedelta(days=1)),
    ]

    before = long_chain(clusters=known)
    after = long_chain(clusters=later)

    # The later zone is nearer and would win if it were visible, so its
    # arrival is a real test of future-append invariance.
    assert after[0].invalidation_price == before[0].invalidation_price
    assert after[2].as_record() == before[2].as_record()


def test_a_reward_reference_from_the_future_cannot_pass_the_hard_gate() -> None:
    future = [
        zone(
            "r-future",
            "11575",
            "11800",
            zone_type="resistance",
            detected_at=AS_OF + timedelta(days=1),
        )
    ]

    _, _, _, rr, _, _ = long_chain(resistance=future)

    assert rr.passes is False
    assert rr.reward_risk is None
    assert "REWARD_RISK_NO_REWARD_REFERENCE" in rr.reason_codes
    assert "REWARD_RISK_REFERENCE_NOT_YET_AVAILABLE" in rr.reason_codes
    # The refused reference stays on the record, so the cause is auditable.
    assert [item.source_id for item in rr.considered_references] == ["r-future"]


def test_a_reference_without_availability_evidence_is_not_credible() -> None:
    # Rulebook 3A.2: unknown availability must not be read optimistically.
    _, _, stop, _, _, _ = long_chain()

    rr = reward_risk_for_stop(
        stop,
        swing_highs=[Decimal("11575")],
        as_of=AS_OF,
        setup=BULL_TREND_CONTINUATION_SETUP,
        config=CONFIG,
    )

    assert rr.passes is False
    assert "REWARD_RISK_REFERENCE_NOT_YET_AVAILABLE" in rr.reason_codes


def test_every_pit_filtered_stage_persists_the_time_it_filtered_against() -> None:
    invalidation, _, _, rr, _, _ = long_chain()

    # A persisted verdict that cannot name its decision time cannot be
    # re-checked for point-in-time correctness later.
    assert invalidation.as_record()["as_of"] == AS_OF.isoformat()
    assert rr.as_record()["as_of"] == AS_OF.isoformat()


# --- 3. fail-closed propagation ------------------------------------------


@pytest.mark.parametrize(
    ("clusters", "expected"),
    [
        ([], "STRUCTURAL_INVALIDATION_INPUT_MISSING"),
        (
            [zone("far", "8000", "8100", zone_type="support")],
            "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE",
        ),
        (
            [zone("weak", "9400", "9600", zone_type="support", confluence="10")],
            "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE",
        ),
        (
            [
                zone(
                    "future",
                    "9400",
                    "9600",
                    zone_type="support",
                    detected_at=AS_OF + timedelta(days=1),
                )
            ],
            "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED",
        ),
    ],
)
def test_any_invalidation_refusal_stops_the_whole_chain(
    clusters,
    expected: str,
) -> None:
    invalidation, buffer, stop, rr, _, size = long_chain(clusters=clusters)

    assert expected in invalidation.reason_codes
    # The refusal must not be relabelled as a legitimate ATR-only buffer.
    assert buffer.complete is False
    assert buffer.reason_codes == ("VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE",)
    assert stop.complete is False
    assert stop.stop_price is None
    assert rr.passes is False
    assert size.complete is False
    assert size.position_notional is None


def test_a_missing_atr_yields_no_stop_rather_than_a_zero_buffer() -> None:
    _, buffer, stop, _, _, size = long_chain(atr=None)

    assert buffer.complete is False
    assert stop.reason_codes == ("INITIAL_STOP_BUFFER_INCOMPLETE",)
    assert size.complete is False


def test_a_daily_outage_reaches_the_stop_as_a_missing_atr() -> None:
    # The gap must not be absorbed into an inflated true range: an inflated
    # ATR would widen the stop and shrink the position without anyone knowing.
    contiguous = atr_from_daily_bars(daily_bars(25), window=20)
    gapped = atr_from_daily_bars(daily_bars(25, skip=20), window=20)

    assert contiguous == Decimal("2.0")
    assert gapped is None

    _, buffer, stop, _, _, _ = long_chain(atr=gapped)
    assert buffer.complete is False
    assert stop.complete is False


def test_a_sub_threshold_conviction_produces_no_position_at_all() -> None:
    _, _, stop, _, budget, size = long_chain(conviction="79")

    assert budget.reason_codes == ("RISK_BUDGET_BELOW_MINIMUM_CONVICTION",)
    assert stop.complete is True  # the stop is fine; the trade is not
    assert size.reason_codes == ("INITIAL_POSITION_SIZE_NO_RISK_BUDGET",)
    assert size.position_notional is None


# --- 4. one owner per threshold ------------------------------------------


def test_the_rr_gate_uses_the_versioned_per_setup_minimum() -> None:
    # BTC-113 enforces setup_requirements.<setup>.minimum_rr independently. If
    # BTC-143 kept its own literal, the same R/R would pass here and fail
    # there for a short, which rulebook 11 requires to be stricter.
    assert minimum_reward_risk_from_config(
        BEARISH_DISTRIBUTION_SETUP, config=CONFIG
    ) == Decimal("2.5")
    for setup in (
        BULL_TREND_CONTINUATION_SETUP,
        BULLISH_RESET_SETUP,
        CAPITULATION_REVERSAL_SETUP,
    ):
        assert minimum_reward_risk_from_config(setup, config=CONFIG) == Decimal("2.0")

    _, _, _, long_rr, _, _ = long_chain()
    _, _, _, short_rr = short_chain()

    # Identical geometry, identical 2.1 ratio, different verdicts.
    assert long_rr.reward_risk == short_rr.reward_risk
    assert long_rr.passes is True
    assert short_rr.passes is False
    assert "REWARD_RISK_BELOW_MINIMUM" in short_rr.reason_codes


def test_the_buffer_parameters_match_the_versioned_config() -> None:
    # BTC-141 carries its rulebook 16.1 defaults as literals. They must not
    # silently diverge from the stop_buffers config a run is executed under.
    assert DEFAULT_BUFFER_ATR_WINDOW_DAYS == CONFIG.stop_buffers.atr_period
    assert DEFAULT_BUFFER_ATR_MULTIPLIER == Decimal(
        str(CONFIG.stop_buffers.atr_multiplier)
    )


def test_the_budget_cap_and_the_portfolio_ceiling_are_the_same_number() -> None:
    budget = calculate_risk_budget(
        entry_conviction="92", nav=NAV, config=CONFIG, config_metadata=METADATA
    )
    exposure = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": "1", "entry_price": ENTRY}],
        stop_price=Decimal("9250"),
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )

    configured = Decimal(str(CONFIG.risk.max_risk_at_stop_fraction_nav))
    assert budget.maximum_risk_fraction_nav == configured
    assert exposure.maximum_fraction_nav == configured


def test_a_config_tighter_than_the_soft_target_stays_usable() -> None:
    # A more conservative versioned ceiling is legitimate. BTC-144 accepts one,
    # so BTC-146 must not refuse to run under it.
    tight = dataclasses.replace(
        CONFIG,
        risk=dataclasses.replace(CONFIG.risk, max_risk_at_stop_fraction_nav=0.005),
    )

    budget = calculate_risk_budget(entry_conviction="92", nav=NAV, config=tight)
    exposure = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": "1", "entry_price": ENTRY}],
        stop_price=Decimal("9250"),
        nav=NAV,
        config=tight,
    )

    assert budget.risk_fraction_nav == Decimal("0.005")
    assert "RISK_BUDGET_CAPPED_AT_MAXIMUM" in budget.reason_codes
    assert exposure.maximum_fraction_nav == Decimal("0.005")
    assert exposure.target_fraction_nav == Decimal("0.005")
    # An explicit target above the ceiling is still a caller error.
    with pytest.raises(ValueError, match="must not exceed"):
        calculate_risk_at_stop(
            [{"tranche_id": "t1", "quantity": "1", "entry_price": ENTRY}],
            stop_price=Decimal("9250"),
            nav=NAV,
            target_fraction_nav=Decimal("0.0075"),
            config=tight,
        )


def test_the_rr_denominator_is_the_stop_not_the_bare_invalidation() -> None:
    # Rulebook 15 names "RiskToInvalidation"; rulebook 16 makes the stop the
    # level that represents thesis invalidation and rulebook 17 sizes risk at
    # the stop. REWARD_RISK_FILTER_V1 therefore measures risk to the BTC-142
    # stop, which is the more conservative of the two readings. Pinned so the
    # choice cannot drift silently.
    invalidation, _, stop, rr, _, _ = long_chain()

    assert rr.risk == stop.entry_price - stop.stop_price
    assert rr.risk > stop.entry_price - invalidation.invalidation_price


# --- 5. producer/consumer contract compatibility -------------------------


def test_the_clustering_owner_hands_over_in_every_supported_form() -> None:
    levels = [
        {
            "member_id": f"m{index}",
            "feature_id": "SWING",
            "level_type": "swing_low",
            "price": price,
            "detected_at": DETECTED,
            "source_timeframe": timeframe,
            "strength": Decimal("90"),
            "exchange": "coinbase",
            "symbol": "BTC-USD",
            "provider": "ccdata",
        }
        for index, (price, timeframe) in enumerate(
            [(Decimal("9400"), "1w"), (Decimal("9450"), "1mo"), (Decimal("9420"), "1d")]
        )
    ]
    clustered = cluster_price_levels(
        levels, as_of=AS_OF, reference_price=ENTRY
    )
    assert clustered.clusters

    from_object = select_structural_invalidation(
        clustered,
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=ENTRY,
        as_of=AS_OF,
    )
    from_record = select_structural_invalidation(
        clustered.as_record(),
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=ENTRY,
        as_of=AS_OF,
    )
    from_sequence = select_structural_invalidation(
        clustered.clusters,
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=ENTRY,
        as_of=AS_OF,
    )

    assert from_object.complete is True
    assert from_object.as_record() == from_record.as_record()
    assert from_object.as_record() == from_sequence.as_record()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_no_epic_o_boundary_accepts_a_non_finite_number(bad: float) -> None:
    # A NaN left to the bare Decimal comparisons raises decimal.InvalidOperation
    # -- an ArithmeticError naming no field -- or poisons a max/sum silently.
    with pytest.raises(ValueError):
        calculate_volatility_buffer(atr=bad)
    with pytest.raises(ValueError):
        calculate_volatility_buffer(atr="500", level_noise_estimate=bad)
    with pytest.raises(ValueError):
        calculate_initial_position_size(
            nav=NAV, risk_fraction_nav="0.006", stop_distance_fraction=bad
        )
    with pytest.raises(ValueError):
        calculate_risk_budget(entry_conviction="92", nav=bad)
    with pytest.raises(ValueError):
        calculate_risk_at_stop(
            [{"tranche_id": "t1", "quantity": bad, "entry_price": ENTRY}],
            stop_price=Decimal("9250"),
            nav=NAV,
            config=CONFIG,
        )


# --- 6. determinism and replay -------------------------------------------


def test_the_whole_chain_is_deterministic_and_order_independent() -> None:
    clusters = [
        zone("s1", "9400", "9600", zone_type="support"),
        zone("s2", "9000", "9200", zone_type="support"),
    ]

    first = long_chain(clusters=clusters)
    second = long_chain(clusters=list(reversed(clusters)))

    for left, right in zip(first, second, strict=True):
        assert left.as_record() == right.as_record()


def test_every_stage_is_re_derivable_from_the_stage_before_its_record() -> None:
    invalidation, buffer, stop, _, budget, size = long_chain()

    # Each canonical path accepts the persisted record as readily as the
    # object, so a replayed run reaches the same numbers.
    replayed_buffer = volatility_buffer_for_invalidation(
        invalidation.as_record(), atr="500", config_metadata=METADATA
    )
    replayed_stop = initial_stop_for_setup(
        invalidation.as_record(),
        replayed_buffer.as_record(),
        config_metadata=METADATA,
    )
    replayed_size = initial_position_size_for_trade(
        budget.as_record(), replayed_stop.as_record(), config_metadata=METADATA
    )

    assert replayed_buffer.as_record() == buffer.as_record()
    assert replayed_stop.as_record() == stop.as_record()
    assert replayed_size.as_record() == size.as_record()
