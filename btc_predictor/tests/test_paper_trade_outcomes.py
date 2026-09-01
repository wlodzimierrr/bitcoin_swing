"""BTC-191: paper-trade outcome dataset joining entry state to final outcomes."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio.accounting import TradeFill, calculate_trade_accounting
from btc_predictor.portfolio.lifecycle_persistence import LifecycleProvenance
from btc_predictor.research import (
    ENTRY_FEATURE_AVAILABLE,
    ENTRY_FEATURE_MISSING_VALUE,
    ENTRY_FEATURE_NOT_OBSERVED,
    INITIAL_FEATURE_NAMES,
    PAPER_TRADE_OUTCOME_FEATURE_ID,
    PAPER_TRADE_OUTCOME_NAMES,
    PAPER_TRADE_OUTCOME_POLICY_VERSION,
    PAPER_TRADE_OUTCOME_PRODUCTION_STATUS,
    PAPER_TRADE_OUTCOME_PROMOTION_TICKET,
    PAPER_TRADE_OUTCOME_REASON_CODES,
    TRADE_OUTCOME_AVAILABLE,
    TRADE_OUTCOME_NOT_MEASURED,
    FeatureMatrixProvenance,
    FeatureObservation,
    PaperTradeEntry,
    PaperTradeOutcomeDefinition,
    PaperTradeOutcomeError,
    build_paper_trade_outcome_dataset,
    build_point_in_time_feature_matrix,
    decision_timestamp_range,
    restore_paper_trade_outcome_dataset,
)
from btc_predictor.research.feature_matrix import FeatureMatrixDefinition
from btc_predictor.signals.data_quality import RecommendationReasonCode


START = datetime(2024, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)
GRID = decision_timestamp_range(START, START + 5 * DAY, step=DAY)
EXTRACTION = START + timedelta(days=40)
FEATURE_SOURCE = "feature_pipeline"
ENTRY_SOURCE = "paper_advisory"
SYMBOL = "BTC-USD"
CONFIG = {
    "config_version": "strategy_config_v2",
    "strategy_version": "swing_v1.2",
    "parameter_set_id": "default_phase1",
}
WINNER = "trade-0001"
LOSER = "trade-0002"

ENTRY_REASON = RecommendationReasonCode(
    code="ENTRY_CONVICTION_VALID",
    source_component="entry_action",
    severity="info",
    detail="Entry conviction at or above the valid-trade threshold.",
)


def at(days: float) -> datetime:
    return START + timedelta(days=days)


def _feature_value(index: int, feature_name: str) -> float:
    return round(40.0 + index * 1.5 + len(feature_name) * 0.25, 6)


def _feature_observations(
    *,
    omit: tuple[tuple[int, str], ...] = (),
    none_valued: tuple[tuple[int, str], ...] = (),
    extra: tuple[FeatureObservation, ...] = (),
) -> tuple[FeatureObservation, ...]:
    rows: list[FeatureObservation] = []
    for index, decision_time in enumerate(GRID):
        for feature_name in INITIAL_FEATURE_NAMES:
            if (index, feature_name) in omit:
                continue
            value = (
                None
                if (index, feature_name) in none_valued
                else _feature_value(index, feature_name)
            )
            rows.append(
                FeatureObservation(
                    feature_name=feature_name,
                    value=value,
                    observation_time=decision_time,
                    available_at=decision_time,
                    source_id=FEATURE_SOURCE,
                )
            )
    return (*rows, *extra)


def _features(**kwargs):
    definition = kwargs.pop("definition", None)
    return build_point_in_time_feature_matrix(
        _feature_observations(**kwargs), GRID, definition=definition
    )


def fill(
    sequence: int,
    when: datetime,
    action: str,
    quantity: str,
    price: str,
    fee="0",
):
    return TradeFill(
        sequence=sequence,
        filled_at=when,
        action=action,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal(fee),
        source_event_id=f"fill-{sequence}",
        execution_bar_at=when,
        execution_bar_timeframe="1d",
    )


def bar(days: float, high: str, low: str) -> OhlcvBar:
    timestamp = at(days)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol=SYMBOL,
        timeframe="1d",
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(low),
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(hours=1),
    )


WINNER_FILLS = (
    fill(1, at(0.5), "ENTER", "2", "100000", "200"),
    fill(2, at(10), "EXIT", "2", "120000", "240"),
)
WINNER_BARS = (bar(2, "108000", "99000"), bar(5, "125000", "107000"))
LOSER_FILLS = (
    fill(1, at(3.25), "ENTER", "1", "110000", "110"),
    fill(2, at(9), "EXIT", "1", "105000", "105"),
)


def _accounting(fills=WINNER_FILLS, **kwargs):
    values = {
        "symbol": SYMBOL,
        "direction": "long",
        "initial_stop_price": "90000",
        "initial_stop_source_id": "stop-1",
        "exit_reason": "STRUCTURAL_STOP",
        "exit_reason_source_id": "exit-1",
        "config_metadata": CONFIG,
        **kwargs,
    }
    return calculate_trade_accounting(fills, **values)


def _accountings(**overrides):
    base = {
        WINNER: _accounting(excursion_bars=WINNER_BARS),
        LOSER: _accounting(
            LOSER_FILLS,
            initial_stop_price="100000",
            initial_stop_source_id="stop-2",
            exit_reason="HOLD_SCORE_COLLAPSE",
            exit_reason_source_id="exit-2",
        ),
    }
    base.update(overrides)
    return base


def _entry(trade_reference: str, index: int, **overrides) -> PaperTradeEntry:
    values = {
        "trade_reference": trade_reference,
        "entry_decision_timestamp": GRID[index],
        "data_available_at": GRID[index],
        "symbol": SYMBOL,
        "direction": "long",
        "decision": "ENTER",
        "setup": "BULL_TREND_CONTINUATION",
        "regime": "BULL",
        "provenance": LifecycleProvenance(
            recommendation_id=index + 1,
            strategy_version="swing_v1.2",
            parameter_set_id="default_phase1",
        ),
        "source_id": ENTRY_SOURCE,
        "reason_codes": (ENTRY_REASON,),
        **overrides,
    }
    return PaperTradeEntry(**values)


def _entries() -> tuple[PaperTradeEntry, ...]:
    return (_entry(WINNER, 0), _entry(LOSER, 3))


def _dataset(**kwargs):
    return build_paper_trade_outcome_dataset(
        kwargs.pop("entries", _entries()),
        kwargs.pop("accountings", _accountings()),
        kwargs.pop("features", _features()),
        extraction_time=kwargs.pop("extraction_time", EXTRACTION),
        **kwargs,
    )


def test_dataset_joins_entry_state_to_final_outcomes() -> None:
    dataset = _dataset()

    assert dataset.feature_id == PAPER_TRADE_OUTCOME_FEATURE_ID
    assert dataset.policy_version == PAPER_TRADE_OUTCOME_POLICY_VERSION
    assert dataset.trade_references == (WINNER, LOSER)
    row = dataset.row(WINNER)
    assert row.entry_decision_timestamp == GRID[0]
    assert row.opened_at == at(0.5)
    assert row.closed_at == at(10)
    assert row.entry_feature("TREND_SCORE").value == _feature_value(0, "TREND_SCORE")
    assert row.entry_feature("TREND_SCORE").status == ENTRY_FEATURE_AVAILABLE
    assert row.outcome("gross_pnl").value == Decimal("40000")
    assert row.outcome("fees").value == Decimal("440")
    assert row.outcome("funding").value == Decimal("0")
    assert row.outcome("net_pnl").value == Decimal("39560")
    assert row.outcome("initial_risk").value == Decimal("20000")
    assert row.outcome("r_multiple").value == Decimal("39560") / Decimal("20000")
    assert row.outcome("holding_days").value == Decimal("9.5")
    assert row.outcome("add_count").value == Decimal("0")
    assert row.outcome("maximum_quantity").value == Decimal("2")
    assert row.outcome("maximum_entry_notional").value == Decimal("200000")
    assert row.exit_reason == "STRUCTURAL_STOP"
    loser = dataset.row(LOSER)
    assert loser.entry_decision_timestamp == GRID[3]
    assert loser.outcome("net_pnl").value == Decimal("-5215")
    assert loser.exit_reason == "HOLD_SCORE_COLLAPSE"


def test_outcome_values_are_read_from_the_accounting_not_recomputed() -> None:
    accountings = _accountings()
    dataset = _dataset(accountings=accountings)

    row = dataset.row(WINNER)
    accounting = accountings[WINNER]
    for name in PAPER_TRADE_OUTCOME_NAMES:
        expected = getattr(accounting, name)
        outcome = row.outcome(name)
        if expected is None:
            assert outcome.status == TRADE_OUTCOME_NOT_MEASURED
            assert outcome.value is None
        else:
            assert outcome.status == TRADE_OUTCOME_AVAILABLE
            assert outcome.value == Decimal(expected)
    assert row.accounting_evidence_digest == accounting.evidence_digest
    assert row.accounting_reason_codes == accounting.reason_codes
    assert dataset.accounting_policy_version == accounting.policy_version
    assert dataset.r_multiple_convention == accounting.r_multiple_convention
    assert dataset.excursion_convention == accounting.excursion_convention


def test_entry_features_are_as_of_the_entry_decision_timestamp() -> None:
    late = FeatureObservation(
        feature_name="TREND_SCORE",
        value=99.0,
        observation_time=GRID[0],
        available_at=GRID[0] + timedelta(hours=6),
        source_id="late_revision",
        revision=1,
    )
    dataset = _dataset(features=_features(extra=(late,)))

    winner = dataset.row(WINNER).entry_feature("TREND_SCORE")
    assert winner.value == _feature_value(0, "TREND_SCORE")
    assert winner.source_id == FEATURE_SOURCE
    assert winner.available_at == GRID[0]
    assert winner.revision == 0
    revised = dataset.row(LOSER).entry_feature("TREND_SCORE")
    assert revised.value == _feature_value(3, "TREND_SCORE")
    assert revised.available_at == GRID[3]


def test_absent_entry_features_keep_an_explicit_status_and_no_value() -> None:
    dataset = _dataset(
        features=_features(
            omit=((0, "FLOW_SCORE"),), none_valued=((0, "RV_7"),)
        )
    )

    row = dataset.row(WINNER)
    unobserved = row.entry_feature("FLOW_SCORE")
    assert unobserved.status == ENTRY_FEATURE_NOT_OBSERVED
    assert unobserved.value is None
    assert unobserved.source_id is None
    assert unobserved.available_at is None
    assert unobserved.revision is None
    valueless = row.entry_feature("RV_7")
    assert valueless.status == ENTRY_FEATURE_MISSING_VALUE
    assert valueless.value is None
    assert valueless.source_id == FEATURE_SOURCE
    assert valueless.available_at == GRID[0]
    counts = dataset.coverage.entry_feature_status_counts["FLOW_SCORE"]
    assert counts == {
        ENTRY_FEATURE_AVAILABLE: 1,
        ENTRY_FEATURE_MISSING_VALUE: 0,
        ENTRY_FEATURE_NOT_OBSERVED: 1,
    }


def test_unmeasured_outcomes_cite_the_accounting_reason_code() -> None:
    dataset = _dataset()

    winner = dataset.row(WINNER)
    assert winner.outcome("maximum_favourable_excursion").status == (
        TRADE_OUTCOME_AVAILABLE
    )
    loser = dataset.row(LOSER)
    for name in (
        "maximum_favourable_excursion",
        "maximum_adverse_excursion",
        "mfe_r",
        "mae_r",
    ):
        outcome = loser.outcome(name)
        assert outcome.status == TRADE_OUTCOME_NOT_MEASURED
        assert outcome.value is None
        assert outcome.reason_code == "TRADE_ACCOUNTING_NO_EXCURSION_BARS"
        assert outcome.reason_code in loser.accounting_reason_codes
    assert dataset.coverage.outcome_status_counts["mfe_r"] == {
        TRADE_OUTCOME_AVAILABLE: 1,
        TRADE_OUTCOME_NOT_MEASURED: 1,
    }


def test_undefined_r_multiple_is_explicit_rather_than_zero() -> None:
    accountings = _accountings(
        **{
            WINNER: _accounting(
                excursion_bars=WINNER_BARS, initial_stop_price="100000"
            )
        }
    )
    dataset = _dataset(accountings=accountings)

    row = dataset.row(WINNER)
    assert row.outcome("initial_risk").value == Decimal("0")
    assert row.outcome("r_multiple").status == TRADE_OUTCOME_NOT_MEASURED
    assert row.outcome("r_multiple").reason_code == "TRADE_ACCOUNTING_R_UNDEFINED"
    assert row.outcome("maximum_favourable_excursion").status == (
        TRADE_OUTCOME_AVAILABLE
    )
    assert row.outcome("mfe_r").reason_code == "TRADE_ACCOUNTING_R_UNDEFINED"


def test_open_trades_have_no_final_outcome() -> None:
    open_fills = (WINNER_FILLS[0],)
    accountings = _accountings(
        **{
            WINNER: _accounting(
                open_fills,
                exit_reason=None,
                exit_reason_source_id=None,
                as_of=at(10),
            )
        }
    )

    with pytest.raises(PaperTradeOutcomeError, match="closed trades only"):
        _dataset(accountings=accountings)


def test_a_trade_closing_after_the_extraction_time_is_refused() -> None:
    with pytest.raises(PaperTradeOutcomeError, match="closed after the extraction"):
        _dataset(extraction_time=at(9.5))


def test_the_entry_decision_must_not_follow_the_opening_fill() -> None:
    entries = (_entry(WINNER, 1), _entry(LOSER, 3))

    with pytest.raises(PaperTradeOutcomeError, match="must not follow the opening"):
        _dataset(entries=entries)


def test_entry_decisions_outside_the_feature_grid_are_refused() -> None:
    entries = (
        _entry(
            WINNER,
            0,
            entry_decision_timestamp=GRID[0] + timedelta(hours=1),
            data_available_at=GRID[0],
        ),
        _entry(LOSER, 3),
    )

    with pytest.raises(PaperTradeOutcomeError, match="not a feature-matrix"):
        _dataset(entries=entries)


def test_entries_and_accountings_must_match_exactly() -> None:
    accountings = _accountings()
    del accountings[LOSER]
    with pytest.raises(PaperTradeOutcomeError, match="every entry requires"):
        _dataset(accountings=accountings)

    with pytest.raises(PaperTradeOutcomeError, match="without a recorded entry"):
        _dataset(entries=(_entry(WINNER, 0),))


def test_duplicate_trade_references_are_refused() -> None:
    entries = (_entry(WINNER, 0), _entry(WINNER, 3))

    with pytest.raises(PaperTradeOutcomeError, match="trade references must be unique"):
        _dataset(entries=entries)


def test_entry_and_executed_trade_must_agree_on_instrument_and_side() -> None:
    entries = (_entry(WINNER, 0, symbol="ETH-USD"), _entry(LOSER, 3))
    with pytest.raises(PaperTradeOutcomeError, match="symbol does not match"):
        _dataset(entries=entries)

    entries = (_entry(WINNER, 0, direction="short"), _entry(LOSER, 3))
    with pytest.raises(PaperTradeOutcomeError, match="direction does not match"):
        _dataset(entries=entries)


def test_one_dataset_holds_one_strategy_provenance() -> None:
    other = LifecycleProvenance(
        recommendation_id=7,
        strategy_version="swing_v1.2",
        parameter_set_id="candidate_a",
    )
    entries = (_entry(WINNER, 0, provenance=other), _entry(LOSER, 3))
    with pytest.raises(PaperTradeOutcomeError, match="does not match the recorded"):
        _dataset(entries=entries)

    accountings = _accountings(
        **{
            WINNER: _accounting(
                excursion_bars=WINNER_BARS,
                config_metadata={**CONFIG, "parameter_set_id": "candidate_a"},
            )
        }
    )
    features = _features(
        definition=FeatureMatrixDefinition(
            provenance=FeatureMatrixProvenance(parameter_set_id="candidate_a")
        )
    )
    with pytest.raises(PaperTradeOutcomeError, match="one dataset holds one"):
        _dataset(entries=entries, accountings=accountings, features=features)


def test_rows_are_ordered_and_deterministic_regardless_of_input_order() -> None:
    forward = _dataset()
    reversed_entries = _dataset(entries=tuple(reversed(_entries())))

    assert reversed_entries.trade_references == (WINNER, LOSER)
    assert reversed_entries.as_record() == forward.as_record()
    assert reversed_entries.dataset_id == forward.dataset_id
    assert reversed_entries.evidence_digest == forward.evidence_digest


def test_record_round_trip_restores_the_dataset() -> None:
    dataset = _dataset()
    record = json.loads(json.dumps(dataset.as_record()))

    restored = restore_paper_trade_outcome_dataset(record)

    assert restored == dataset
    assert restored.as_record() == dataset.as_record()
    assert restored.row(WINNER).outcome("net_pnl").value == Decimal("39560")
    assert restored.row(WINNER).entry_reason_codes == (ENTRY_REASON,)


def test_tampered_records_are_rejected() -> None:
    record = json.loads(json.dumps(_dataset().as_record()))

    altered = json.loads(json.dumps(record))
    altered["rows"][0]["outcomes"][3]["value"] = "999999"
    with pytest.raises(PaperTradeOutcomeError, match="does not match digest"):
        restore_paper_trade_outcome_dataset(altered)

    dropped = json.loads(json.dumps(record))
    dropped["rows"] = dropped["rows"][:1]
    with pytest.raises(PaperTradeOutcomeError, match="coverage does not match"):
        restore_paper_trade_outcome_dataset(dropped)

    recounted = json.loads(json.dumps(record))
    recounted["coverage"]["trade_count"] = 5
    with pytest.raises(PaperTradeOutcomeError, match="coverage does not match"):
        restore_paper_trade_outcome_dataset(recounted)

    relabelled = json.loads(json.dumps(record))
    relabelled["rows"][0]["strategy_version"] = "swing_v1.1"
    with pytest.raises(PaperTradeOutcomeError, match="row strategy_version"):
        restore_paper_trade_outcome_dataset(relabelled)


def test_an_unmeasured_outcome_cannot_invent_a_reason_code() -> None:
    record = json.loads(json.dumps(_dataset().as_record()))
    record["rows"][1]["outcomes"][8]["reason_code"] = "TRADE_ACCOUNTING_R_UNDEFINED"

    with pytest.raises(PaperTradeOutcomeError, match="reason code the accounting"):
        restore_paper_trade_outcome_dataset(record)


def test_coverage_counts_every_joined_trade() -> None:
    coverage = _dataset().coverage

    assert coverage.trade_count == 2
    assert coverage.direction_counts == {"long": 2, "short": 0}
    assert coverage.decision_counts["ENTER"] == 2
    assert coverage.decision_counts["WATCH"] == 0
    assert coverage.setup_counts["BULL_TREND_CONTINUATION"] == 2
    assert coverage.regime_counts["BULL"] == 2
    assert coverage.exit_reason_counts == {
        "HOLD_SCORE_COLLAPSE": 1,
        "STRUCTURAL_STOP": 1,
    }
    assert coverage.outcome_status_counts["net_pnl"] == {
        TRADE_OUTCOME_AVAILABLE: 2,
        TRADE_OUTCOME_NOT_MEASURED: 0,
    }


def test_definitions_are_restricted_to_owned_vocabularies() -> None:
    with pytest.raises(PaperTradeOutcomeError, match="BTC-165 accounting outputs"):
        PaperTradeOutcomeDefinition(outcome_names=("net_pnl", "sharpe"))

    definition = PaperTradeOutcomeDefinition(
        entry_feature_names=("NOT_A_FEATURE",), outcome_names=("net_pnl",)
    )
    with pytest.raises(PaperTradeOutcomeError, match="does not contain entry-state"):
        _dataset(definition=definition)


def test_a_narrower_definition_keeps_only_the_declared_columns() -> None:
    definition = PaperTradeOutcomeDefinition(
        entry_feature_names=("TREND_SCORE", "FLOW_SCORE"),
        outcome_names=("net_pnl", "r_multiple"),
    )
    dataset = _dataset(definition=definition)

    row = dataset.row(WINNER)
    assert tuple(item.feature_name for item in row.entry_features) == (
        "TREND_SCORE",
        "FLOW_SCORE",
    )
    assert tuple(item.outcome_name for item in row.outcomes) == (
        "net_pnl",
        "r_multiple",
    )
    assert dataset.definition.fingerprint != PaperTradeOutcomeDefinition().fingerprint
    assert restore_paper_trade_outcome_dataset(dataset.as_record()) == dataset


def test_lifecycle_provenance_is_persisted_for_every_row() -> None:
    dataset = _dataset()

    row = dataset.row(LOSER)
    assert row.recommendation_id == 4
    assert row.strategy_version == "swing_v1.2"
    assert row.parameter_set_id == "default_phase1"
    assert row.provenance == LifecycleProvenance(
        recommendation_id=4,
        strategy_version="swing_v1.2",
        parameter_set_id="default_phase1",
    )
    assert row.source_id == ENTRY_SOURCE
    assert row.exit_reason_source_id == "exit-2"
    assert row.initial_stop_source_id == "stop-2"
    assert row.entry_reason_codes == (ENTRY_REASON,)
    assert dataset.config_metadata["parameter_set_id"] == "default_phase1"
    assert dataset.feature_definition_fingerprint == (
        _features().definition.fingerprint
    )


def test_matrices_expose_values_and_missing_masks_to_numpy_consumers() -> None:
    dataset = _dataset(
        features=_features(
            omit=((0, "FLOW_SCORE"),), none_valued=((0, "RV_7"),)
        )
    )

    values, mask = dataset.entry_feature_matrix()
    assert values.shape == (2, len(INITIAL_FEATURE_NAMES))
    assert not values.flags.writeable
    assert not mask.flags.writeable
    flow = INITIAL_FEATURE_NAMES.index("FLOW_SCORE")
    realized_volatility = INITIAL_FEATURE_NAMES.index("RV_7")
    assert bool(mask[0, flow]) and bool(mask[0, realized_volatility])
    assert not bool(mask[1, flow])
    trend = INITIAL_FEATURE_NAMES.index("TREND_SCORE")
    assert values[0, trend] == _feature_value(0, "TREND_SCORE")

    outcomes, outcome_mask = dataset.outcome_matrix()
    assert outcomes.shape == (2, len(PAPER_TRADE_OUTCOME_NAMES))
    net = PAPER_TRADE_OUTCOME_NAMES.index("net_pnl")
    assert outcomes[0, net] == pytest.approx(39560.0)
    mfe = PAPER_TRADE_OUTCOME_NAMES.index("mfe_r")
    assert not bool(outcome_mask[0, mfe])
    assert bool(outcome_mask[1, mfe])
    assert np.isnan(outcomes[1, mfe])


def test_outcome_series_returns_exact_decimals_in_row_order() -> None:
    dataset = _dataset()

    assert dataset.outcome_series("net_pnl") == (
        Decimal("39560"),
        Decimal("-5215"),
    )
    assert dataset.outcome_series("mfe_r")[1] is None
    with pytest.raises(KeyError):
        dataset.outcome_series("sharpe")


def test_an_empty_dataset_is_wellformed_and_replayable() -> None:
    dataset = _dataset(entries=(), accountings={})

    assert dataset.rows == ()
    assert dataset.coverage.trade_count == 0
    assert dataset.coverage.exit_reason_counts == {}
    assert restore_paper_trade_outcome_dataset(dataset.as_record()) == dataset


def test_dataset_is_research_only_and_names_its_promotion_boundary() -> None:
    dataset = _dataset()

    assert dataset.production_status == PAPER_TRADE_OUTCOME_PRODUCTION_STATUS
    assert dataset.promotion_ticket == PAPER_TRADE_OUTCOME_PROMOTION_TICKET
    assert dataset.reason_codes == PAPER_TRADE_OUTCOME_REASON_CODES
    assert "PAPER_TRADE_OUTCOME_RESEARCH_ONLY" in dataset.reason_codes
    assert "PAPER_TRADE_OUTCOME_BTC_193_PROMOTION_REQUIRED" in dataset.reason_codes
