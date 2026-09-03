"""BTC-224 golden historical scenarios.

The ticket asks for hand-reviewed BTC periods and the strategy behaviour those
periods are expected to produce. Everything upstream of this suite is tested
against constructed bars: BTC-220 pins the mathematics, BTC-221 the
point-in-time filters, BTC-222 the risk invariants and BTC-223 the paper
execution chain, and every one of them invents the price series that makes its
point. A constructed series can only demonstrate the behaviour its author
already had in mind.

A golden scenario is the opposite instrument. Six real periods of BTC history
are frozen with their review, the trade plan a reviewer drew on them, and the
behaviour the system is expected to produce -- and the suite replays each one
through the real BTC-180 engine and the BTC-141..165 owners it routes to. The
fixture is `golden/btc_golden_scenarios_v1.json`, derived from the pinned
BTC-019 Coinbase artifact through `derive_ohlcv_bars`, carrying its own bar
digest so a silently edited session is a failure rather than a new expectation.

Three things are separated deliberately.

- Market facts come from the frozen bars: which session a zone was touched in,
  where a stop sat, what the ATR was, what a fill cost.
- Judgement comes from the recorded review: the structural level a stop hangs
  on, the conviction, and the BTC-154/157/158 states (regime, flow,
  positioning, euphoria, crowding) that no price-only replay can know. These
  are hand-reviewed scenario inputs with their reasoning written down, never
  mechanical proxies invented here.
- Arithmetic comes from the owners: BTC-141 buffers, BTC-142 stops, BTC-144/145
  sizing, BTC-155 tranches, BTC-156 trails, BTC-160..165 execution and
  accounting.

What the suite adds over the owner suites is the pairing of a real period with
a stated expectation. The expectations are hand-derived from the sessions --
the fill price of an entry whose zone the market opened above, the R multiple
of a stop that a 7.22% session took out, the exit that got out four sessions
before a capitulation -- and are re-derived here from the bars by arithmetic
that does not call the owner being checked. A defect that changes what the
strategy does on real history fails here even when every constructed unit test
still passes.

Two scope limits are stated in the fixture rather than assumed. The bars are
one venue's series, pinned by artifact digest, because
`PRICE_SOURCE_POLICY_V1` leaves the canonical BTC reference unresolved; the
October 2025 scenario exists precisely because the source choice decides
whether its stop is touched. And the review inputs are a reviewer's reading of
each period, not a claim about what the full feature stack would have scored.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.backtest import (
    ADD_ACTION,
    ARM_ENTRY_ACTION,
    BACKTEST_END_POLICY_VERSION,
    BACKTEST_ENGINE_FEATURE_ID,
    BACKTEST_ENGINE_POLICY_VERSION,
    BACKTEST_NAV_POLICY_VERSION,
    COST_PROFILES,
    EXIT_ACTION,
    TRAIL_ACTION,
    TRIM_ACTION,
    BacktestContext,
    BacktestIntent,
    BacktestResult,
    restore_backtest_result,
    run_backtest,
    validate_backtest_bars,
)
from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar, next_bar_timestamp
from btc_predictor.portfolio import execution_costs_from_config
from btc_predictor.risk import (
    HIGHER_LOW,
    ConfirmedTrailingStructure,
    atr_from_daily_bars,
    calculate_initial_stop,
    calculate_risk_budget,
    trail_stop_for_position,
    volatility_buffer_for_invalidation,
)
from btc_predictor.signals import (
    AddRequirementsInput,
    ExitRuleInput,
    TrimRuleInput,
    evaluate_add_requirements,
    evaluate_exit_rules,
    evaluate_trim_rules,
)


GOLDEN_PATH = Path(__file__).parent / "golden" / "btc_golden_scenarios_v1.json"
GOLDEN_SCHEMA_VERSION = "GOLDEN_HISTORICAL_SCENARIO_V1"
GOLDEN_AVAILABILITY_POLICY_VERSION = "GOLDEN_BAR_AVAILABILITY_SESSION_CLOSE_V1"
GOLDEN_STRUCTURE_SOURCE_FEATURE_ID = "GOLDEN_SCENARIO_REVIEWED_STRUCTURE"

DOCUMENT = json.loads(GOLDEN_PATH.read_text())
DATASET = DOCUMENT["dataset"]
SCENARIOS = tuple(DOCUMENT["scenarios"])
SCENARIO_IDS = tuple(scenario["scenario_id"] for scenario in SCENARIOS)

CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
COSTS = execution_costs_from_config(CONFIG)
BASIS_POINT = Decimal("10000")
SYMBOL = DATASET["symbol"]
DAY = timedelta(days=1)


def scenario_by_id(scenario_id: str) -> dict[str, Any]:
    for scenario in SCENARIOS:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise AssertionError(f"unknown golden scenario {scenario_id!r}")


def session_start(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(tzinfo=UTC)


def available_at(day: str) -> datetime:
    """A session is decision-available at its close boundary."""

    return session_start(day) + DAY


def bar_from_record(record: dict[str, str]) -> OhlcvBar:
    timestamp = session_start(record["t"])
    return OhlcvBar(
        timestamp=timestamp,
        exchange=DATASET["exchange"],
        symbol=DATASET["symbol"],
        timeframe=DATASET["bar_timeframe"],
        open=Decimal(record["o"]),
        high=Decimal(record["h"]),
        low=Decimal(record["l"]),
        close=Decimal(record["c"]),
        volume=Decimal(record["v"]),
        provider=DATASET["provider"],
        ingested_at=next_bar_timestamp(timestamp, DATASET["bar_timeframe"]),
    )


def bars_digest(records: list[dict[str, str]]) -> str:
    payload = [[r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]] for r in records]
    body = json.dumps(payload, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


@lru_cache(maxsize=None)
def scenario_bars(scenario_id: str) -> tuple[OhlcvBar, ...]:
    scenario = scenario_by_id(scenario_id)
    return tuple(bar_from_record(record) for record in scenario["bars"])


def bar_on(scenario_id: str, day: str) -> OhlcvBar:
    for bar in scenario_bars(scenario_id):
        if bar.timestamp.date().isoformat() == day:
            return bar
    raise AssertionError(f"{scenario_id} has no session on {day}")


class GoldenScenarioStrategy:
    """Replay one reviewed plan: market facts from the bars, judgement from the review.

    The plan names the sessions a reviewer acted on and the states they read.
    Every number the strategy hands the engine is produced here by the owner
    that owns it -- BTC-141 for the buffer, BTC-142 for the stop, BTC-156 for a
    trail, BTC-154/157/158 for the add, trim and exit decisions -- from bars the
    engine has already declared visible.
    """

    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario_id = scenario["scenario_id"]
        self.direction = scenario["plan"]["direction"]
        self.decisions: dict[str, dict[str, Any]] = {}
        for decision in scenario["plan"]["decisions"]:
            day = decision["on"]
            if day in self.decisions:
                raise AssertionError(f"{self.scenario_id} plans two decisions on {day}")
            self.decisions[day] = decision
        self.seen: list[str] = []

    def __call__(self, context: BacktestContext) -> BacktestIntent | None:
        day = context.bar.timestamp.date().isoformat()
        decision = self.decisions.get(day)
        if decision is None:
            return None
        self.seen.append(day)
        action = decision["action"]
        source_id = f"{self.scenario_id}:{action.lower()}:{day}"
        if action == ARM_ENTRY_ACTION:
            return self._arm_entry(context, decision, source_id)
        if action == TRAIL_ACTION:
            return self._trail(context, decision, source_id)
        if action == ADD_ACTION:
            return self._add(context, decision, source_id)
        if action == TRIM_ACTION:
            return self._trim(context, decision, source_id)
        if action == EXIT_ACTION:
            return self._exit(context, decision, source_id)
        raise AssertionError(f"unsupported planned action {action!r}")

    def _atr(self, context: BacktestContext) -> Decimal | None:
        return atr_from_daily_bars(
            context.bars,
            window=CONFIG.stop_buffers.atr_period,
        )

    def _buffer(self, context: BacktestContext, zone: dict[str, Any] | None):
        selection = dict(zone) if zone is not None else {}
        return volatility_buffer_for_invalidation(
            selection,
            atr=self._atr(context),
            atr_multiplier=Decimal(str(CONFIG.stop_buffers.atr_multiplier)),
            atr_window=CONFIG.stop_buffers.atr_period,
            config_metadata=METADATA,
        )

    def _arm_entry(
        self,
        context: BacktestContext,
        decision: dict[str, Any],
        source_id: str,
    ) -> BacktestIntent:
        lower = Decimal(decision["entry_zone_lower"])
        upper = Decimal(decision["entry_zone_upper"])
        buffer = self._buffer(
            context,
            {"selected_zone_lower_bound": lower, "selected_zone_upper_bound": upper},
        )
        # A long is sized on the worst price its zone can fill at, so the
        # realised risk of a zone-boundary fill cannot exceed the plan's.
        reference = upper if self.direction == "long" else lower
        stop = calculate_initial_stop(
            invalidation_price=Decimal(decision["invalidation_price"]),
            buffer=buffer.buffer,
            direction=self.direction,
            entry_price=reference,
            config_metadata=METADATA,
        )
        return BacktestIntent(
            action=ARM_ENTRY_ACTION,
            direction=self.direction,
            entry_zone_lower=lower,
            entry_zone_upper=upper,
            initial_stop=stop,
            entry_conviction=Decimal(decision["entry_conviction"]),
            source_id=source_id,
        )

    def _trail(
        self,
        context: BacktestContext,
        decision: dict[str, Any],
        source_id: str,
    ) -> BacktestIntent:
        level_day = decision["structure_level_date"]
        structure = ConfirmedTrailingStructure(
            structure_id=decision["structure_id"],
            source_feature_id=GOLDEN_STRUCTURE_SOURCE_FEATURE_ID,
            direction=context.lifecycle.direction,
            structure_type=decision["structure_type"],
            price=Decimal(decision["structure_price"]),
            level_timestamp=session_start(level_day),
            detected_at=available_at(level_day),
            config_metadata=METADATA,
            reason_codes=tuple(decision.get("structure_reason_codes", ())),
        )
        result = trail_stop_for_position(
            context.lifecycle,
            structure=structure,
            buffer=self._buffer(context, None),
            current_price=context.bar.close,
            as_of=context.as_of,
        )
        return BacktestIntent(
            action=TRAIL_ACTION,
            direction=context.lifecycle.direction,
            trailing_stop=result,
            source_id=source_id,
        )

    def _add(
        self,
        context: BacktestContext,
        decision: dict[str, Any],
        source_id: str,
    ) -> BacktestIntent:
        inputs = decision["add_inputs"]
        requirements = evaluate_add_requirements(
            AddRequirementsInput(
                position_profitable=inputs["position_profitable"],
                new_structural_confirmation=inputs["new_structural_confirmation"],
                signed_risk_improvement=Decimal(inputs["signed_risk_improvement"]),
                regime_supportive=inputs["regime_supportive"],
                flow_supportive=inputs["flow_supportive"],
                positioning_healthy=inputs["positioning_healthy"],
                add_score=Decimal(inputs["add_score"]),
                projected_risk_at_stop_within_maximum=inputs[
                    "projected_risk_at_stop_within_maximum"
                ],
            ),
            strategy_config=CONFIG,
        )
        return BacktestIntent(
            action=ADD_ACTION,
            direction=context.lifecycle.direction,
            requirements=requirements,
            source_id=source_id,
        )

    def _trim(
        self,
        context: BacktestContext,
        decision: dict[str, Any],
        source_id: str,
    ) -> BacktestIntent:
        inputs = decision["trim_inputs"]
        signal = evaluate_trim_rules(
            TrimRuleInput(
                position_open=context.position_open,
                hold_score=Decimal(inputs["hold_score"]),
                euphoria_active=inputs["euphoria_active"],
                crowding_active=inputs["crowding_active"],
                current_flow_score=Decimal(inputs["current_flow_score"]),
                prior_flow_score=Decimal(inputs["prior_flow_score"]),
            ),
            strategy_config=CONFIG,
        )
        return BacktestIntent(
            action=TRIM_ACTION,
            direction=context.lifecycle.direction,
            trim_signal=signal,
            source_id=source_id,
        )

    def _exit(
        self,
        context: BacktestContext,
        decision: dict[str, Any],
        source_id: str,
    ) -> BacktestIntent:
        inputs = decision["exit_inputs"]
        signal = evaluate_exit_rules(
            ExitRuleInput(
                position_open=context.position_open,
                direction=context.lifecycle.direction,
                standing_stop=context.standing_stop,
                current_price=context.bar.close,
                hold_score=Decimal(inputs["hold_score"]),
                regime_invalidated=inputs["regime_invalidated"],
                data_risk_exit_required=inputs["data_risk_exit_required"],
                manual_research_override=inputs["manual_research_override"],
            ),
            strategy_config=CONFIG,
            evaluated_at=context.as_of,
        )
        assert signal.signal, f"{self.scenario_id}: the reviewed exit did not signal"
        return BacktestIntent(
            action=EXIT_ACTION,
            direction=context.lifecycle.direction,
            exit_reason=signal.exit_reasons[0],
            source_id=source_id,
        )


def replay(
    scenario: dict[str, Any],
    *,
    cost_profile: str | None = None,
    bar_limit: int | None = None,
    strategy: GoldenScenarioStrategy | None = None,
) -> BacktestResult:
    bars = scenario_bars(scenario["scenario_id"])
    if bar_limit is not None:
        bars = bars[:bar_limit]
    return run_backtest(
        bars,
        strategy=strategy if strategy is not None else GoldenScenarioStrategy(scenario),
        symbol=SYMBOL,
        starting_nav=Decimal(scenario["starting_nav"]),
        strategy_config=CONFIG,
        cost_profile=cost_profile or scenario["cost_profile"],
        strategy_id=f"golden:{scenario['scenario_id']}",
    )


@lru_cache(maxsize=None)
def golden_result(scenario_id: str, cost_profile: str | None = None) -> BacktestResult:
    return replay(scenario_by_id(scenario_id), cost_profile=cost_profile)


def material_events(result: BacktestResult) -> tuple[Any, ...]:
    """Every event except the per-session check of an untouched resting stop."""

    return tuple(event for event in result.events if event.status != "RESTING")


EVIDENCE_PRICE_KEYS = (
    "reference_price",
    "average_fill_price",
    "filled_quantity",
    "stop_price",
)


def event_session(event: Any) -> str:
    """The session an event belongs to, undoing the close-boundary availability."""

    return (event.occurred_at - DAY).date().isoformat()


def event_record(event: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "session": event_session(event),
        "event_type": event.event_type,
        "action": event.action,
        "status": event.status,
        "reason_codes": list(event.reason_codes),
    }
    evidence = event.evidence if isinstance(event.evidence, dict) else {}
    for key in EVIDENCE_PRICE_KEYS:
        value = evidence.get(key)
        if value is not None:
            record[key] = value
    return record


def fill_events(result: BacktestResult) -> tuple[Any, ...]:
    """Every event that moved quantity, in engine order."""

    return tuple(
        event
        for event in result.events
        if event.status == "EXECUTED"
        and event.event_type.endswith("_EXECUTION")
        and event.evidence.get("filled_quantity") not in (None, "0")
    )


OPENING_ACTIONS = ("ENTER", "ADD")

# Notionals are carried through the BTC-144 float64 quant owner, so a Decimal
# re-derivation agrees to the owner's precision rather than digit for digit.
QUANT_RELATIVE_TOLERANCE = Decimal("1e-12")


def agrees(actual: Decimal, expected: Decimal) -> bool:
    scale = max(abs(expected), Decimal("1"))
    return abs(actual - expected) <= QUANT_RELATIVE_TOLERANCE * scale


def is_opening(event: Any) -> bool:
    return event.evidence["action"] in OPENING_ACTIONS


@pytest.fixture(params=SCENARIOS, ids=SCENARIO_IDS)
def scenario(request: pytest.FixtureRequest) -> dict[str, Any]:
    return request.param


# --- the fixture itself --------------------------------------------------


def test_the_fixture_pins_one_source_and_states_the_scope_of_its_expectations() -> None:
    """A golden expectation is only as fixed as the series it was reviewed on."""

    assert DOCUMENT["schema_version"] == GOLDEN_SCHEMA_VERSION
    assert DOCUMENT["review_status"] == "HAND_REVIEWED"
    assert DATASET["derivation_owner"] == "btc_predictor.data.ohlcv.derive_ohlcv_bars"
    assert DATASET["availability_policy_version"] == GOLDEN_AVAILABILITY_POLICY_VERSION
    assert DATASET["price_source_policy_version"] == "PRICE_SOURCE_POLICY_V1"
    # BTC-019 has approved no canonical reference, so the fixture must say so
    # rather than let one venue's series read as the price of Bitcoin.
    assert DATASET["canonical_reference_status"] == "UNRESOLVED"
    assert len(DATASET["source_artifact_sha256"]) == 64
    assert int(DATASET["source_artifact_sha256"], 16) >= 0
    assert DATASET["source_artifact"].endswith(".jsonl.gz")
    assert DATASET["source_timeframe"] == "1h"
    assert DATASET["bar_timeframe"] == "1d"
    assert "re-sourcing" in DATASET["source_scope_note"]
    assert len(SCENARIOS) == len(set(SCENARIO_IDS)) == 6


def test_every_scenario_carries_a_written_review_and_a_stated_expectation(
    scenario: dict[str, Any],
) -> None:
    assert scenario["title"].strip()
    assert len(scenario["review"]) >= 4
    assert all(line.strip() for line in scenario["review"])
    assert len(scenario["expected_behaviour"]) >= 3
    assert all(line.strip() for line in scenario["expected_behaviour"])
    start, end = scenario["period"]["start"], scenario["period"]["end"]
    assert date.fromisoformat(start) < date.fromisoformat(end)
    assert scenario["cost_profile"] in COST_PROFILES
    assert Decimal(scenario["starting_nav"]) > 0


def test_every_scenario_series_matches_its_recorded_digest(
    scenario: dict[str, Any],
) -> None:
    """An edited session is a fixture failure, never a new expectation."""

    assert scenario["bars_digest"] == bars_digest(scenario["bars"])
    assert scenario["bar_count"] == len(scenario["bars"])


def test_every_scenario_series_is_a_replayable_canonical_daily_series(
    scenario: dict[str, Any],
) -> None:
    bars = scenario_bars(scenario["scenario_id"])

    assert validate_backtest_bars(bars, symbol=SYMBOL) == bars
    assert bars[0].timestamp.date().isoformat() == scenario["period"]["start"]
    assert bars[-1].timestamp.date().isoformat() == scenario["period"]["end"]
    expected_sessions = (
        date.fromisoformat(scenario["period"]["end"])
        - date.fromisoformat(scenario["period"]["start"])
    ).days + 1
    # A missing session would silently change what a decision could see.
    assert len(bars) == expected_sessions
    for previous, current in zip(bars, bars[1:]):
        assert current.timestamp - previous.timestamp == DAY
    for bar in bars:
        assert bar.timeframe == "1d"
        assert (bar.exchange, bar.provider) == (DATASET["exchange"], DATASET["provider"])
        assert bar.timestamp.hour == 0
        # The availability policy the fixture declares: a session is decision
        # material only once it has closed.
        assert bar.ingested_at == bar.timestamp + DAY
        assert bar.low <= min(bar.open, bar.close)
        assert bar.high >= max(bar.open, bar.close)
        assert bar.volume > 0


def test_every_planned_level_is_traceable_to_a_reviewed_session(
    scenario: dict[str, Any],
) -> None:
    """The plan is a reading of these sessions, not numbers chosen to pass."""

    scenario_id = scenario["scenario_id"]
    bars = scenario_bars(scenario_id)
    sessions = [bar.timestamp.date().isoformat() for bar in bars]
    decisions = scenario["plan"]["decisions"]

    assert [decision["on"] for decision in decisions] == sorted(
        decision["on"] for decision in decisions
    )
    for decision in decisions:
        assert decision["on"] in sessions
        index = sessions.index(decision["on"])
        if decision["action"] == ARM_ENTRY_ACTION:
            # The stop buffer is an ATR20 term, so an entry decision must sit
            # far enough into the window for that window to be complete.
            assert index > CONFIG.stop_buffers.atr_period
            lower = Decimal(decision["entry_zone_lower"])
            upper = Decimal(decision["entry_zone_upper"])
            assert lower < upper
            visible = bars[: index + 1]
            assert min(bar.low for bar in visible) <= lower
            assert upper <= max(bar.high for bar in visible)
            level_day = decision["invalidation_date"]
            assert sessions.index(level_day) <= index
            assert Decimal(decision["invalidation_price"]) == bar_on(
                scenario_id, level_day
            ).low
            assert Decimal(decision["entry_conviction"]) >= Decimal(
                str(CONFIG.entry_thresholds.valid_trade_min)
            )
        if decision["action"] == TRAIL_ACTION:
            level_day = decision["structure_level_date"]
            assert sessions.index(level_day) < index
            assert Decimal(decision["structure_price"]) == bar_on(
                scenario_id, level_day
            ).low
            assert decision["structure_type"] == HIGHER_LOW


# --- the reviewed behaviour ----------------------------------------------


def test_every_planned_decision_is_reached_on_its_reviewed_session(
    scenario: dict[str, Any],
) -> None:
    """A plan may not carry a decision the replay never reaches."""

    strategy = GoldenScenarioStrategy(scenario)
    replay(scenario, strategy=strategy)

    assert strategy.seen == [
        decision["on"] for decision in scenario["plan"]["decisions"]
    ]


def test_each_scenario_reproduces_its_reviewed_event_stream(
    scenario: dict[str, Any],
) -> None:
    result = golden_result(scenario["scenario_id"])

    assert [event_record(event) for event in material_events(result)] == scenario[
        "expected"
    ]["events"]
    assert [event.sequence for event in result.events] == list(
        range(1, len(result.events) + 1)
    )


def test_each_scenario_reproduces_its_reviewed_outcome(
    scenario: dict[str, Any],
) -> None:
    result = golden_result(scenario["scenario_id"])
    expected = scenario["expected"]
    final = result.equity_curve[-1]

    assert list(result.reason_codes) == expected["reason_codes"]
    assert result.missed_entries == expected["missed_entries"]
    assert result.stopped_out == expected["stopped_out"]
    assert result.final_lifecycle.state == expected["final_state"]
    assert str(final.open_quantity) == expected["final_open_quantity"]
    assert str(result.ending_nav) == expected["ending_nav"]
    stop = result.final_lifecycle.stop_price
    assert (None if stop is None else str(stop)) == expected["final_standing_stop"]
    assert result.bar_count == scenario["bar_count"]
    assert result.symbol == SYMBOL
    assert result.feature_id == BACKTEST_ENGINE_FEATURE_ID
    assert result.policy_version == BACKTEST_ENGINE_POLICY_VERSION
    assert result.end_policy_version == BACKTEST_END_POLICY_VERSION
    # The configuration and the priced assumption a replay needs are persisted.
    assert result.config_metadata == METADATA
    assert result.cost_profile is not None
    assert result.cost_profile.profile == scenario["cost_profile"]
    assert result.cost_profile.as_record()["config_metadata"] == METADATA
    # Every scenario is reviewed on the shared configured assumption, the same
    # one advisory and paper trading price against.
    assert result.effective_costs == COSTS
    assert "BACKTEST_COST_PROFILE_APPLIED" in result.reason_codes


def test_each_scenario_reproduces_its_reviewed_trades(
    scenario: dict[str, Any],
) -> None:
    result = golden_result(scenario["scenario_id"])
    expected = scenario["expected"]["trades"]

    assert len(result.trades) == len(expected)
    for trade, review in zip(result.trades, expected):
        assert (trade.opened_at - DAY).date().isoformat() == review["opened_session"]
        assert trade.closed == review["closed"]
        closed_session = (
            None if trade.closed_at is None else (trade.closed_at - DAY).date().isoformat()
        )
        assert closed_session == review["closed_session"]
        assert str(trade.initial_quantity) == review["initial_quantity"]
        assert str(trade.initial_entry_price) == review["initial_entry_price"]
        assert str(trade.average_entry_price) == review["average_entry_price"]
        assert str(trade.initial_stop_price) == review["initial_stop_price"]
        assert str(trade.initial_risk) == review["initial_risk"]
        assert str(trade.entry_notional) == review["entry_notional"]
        assert str(trade.exit_notional) == review["exit_notional"]
        assert str(trade.gross_pnl) == review["gross_pnl"]
        assert str(trade.fees) == review["fees"]
        assert str(trade.funding) == review["funding"]
        assert str(trade.net_pnl) == review["net_pnl"]
        actual_r = None if trade.r_multiple is None else str(trade.r_multiple)
        assert actual_r == review["r_multiple"]
        assert trade.add_count == review["add_count"]
        assert trade.trim_count == review["trim_count"]
        assert trade.exit_reason == review["exit_reason"]


def test_every_event_persists_its_reason_codes_and_configuration(
    scenario: dict[str, Any],
) -> None:
    """A replay needs the codes and the configuration, not only the numbers."""

    result = golden_result(scenario["scenario_id"])

    assert result.as_record()["config_metadata"] == METADATA
    for event in result.events:
        assert event.reason_codes
        assert event.source_id
        evidence = event.evidence
        metadata = evidence.get("config_metadata")
        if metadata is None and isinstance(evidence.get("intent"), dict):
            metadata = evidence["intent"].get("config_metadata")
        if metadata is not None:
            assert metadata == METADATA


def test_the_standing_stop_is_resolved_on_exactly_the_sessions_it_protected(
    scenario: dict[str, Any],
) -> None:
    """The events the expectation does not list are accounted for, not ignored.

    A stop is resolved against every session the ledger entered carrying a
    position, plus the entry session itself through the pre-authorised bracket.
    Every one of those resolutions is a resting check except the fill that ends
    the trade, so a scenario cannot quietly stop protecting a live position.
    """

    result = golden_result(scenario["scenario_id"])
    protected: list[str] = []
    previous = None
    for point in result.equity_curve:
        if previous is not None and previous.open_quantity > 0:
            protected.append(point.bar_timestamp.date().isoformat())
        previous = point
    protected.extend(
        event_session(event)
        for event in result.events
        if event.event_type == "ENTRY_EXECUTION" and event.status == "EXECUTED"
    )
    checks = [event for event in result.events if event.event_type == "STOP_EXECUTION"]

    assert [event_session(event) for event in checks] == sorted(set(protected))
    for event in checks[:-1] if result.stopped_out else checks:
        assert event.status == "RESTING"
        assert event.action is None
        assert event.reason_codes == ("STOP_NOT_TOUCHED", "STOP_EXECUTION_RESTING")
    if result.stopped_out:
        assert checks[-1].status == "EXECUTED"
        assert checks[-1].action == EXIT_ACTION


# --- the same figures, re-derived without the owner that produced them ----


def test_every_fill_is_the_reviewed_session_geometry_priced_by_the_cost_policy(
    scenario: dict[str, Any],
) -> None:
    """Re-derive each fill from the bar and the bps, not from the executor."""

    result = golden_result(scenario["scenario_id"])
    costs = result.effective_costs
    slippage = costs.slippage_bps / BASIS_POINT
    fee_rate = costs.fee_bps / BASIS_POINT
    stop_prices = [Decimal(trade.initial_stop_price) for trade in result.trades]
    stop_prices += [
        Decimal(event.evidence["stop_price"])
        for event in result.events
        if event.event_type == "TRAILING_STOP" and event.status == "APPLIED"
    ]

    for event in fill_events(result):
        evidence = event.evidence
        bar = bar_on(scenario["scenario_id"], event_session(event))
        reference = Decimal(evidence["reference_price"])
        quantity = Decimal(evidence["filled_quantity"])
        fill = Decimal(evidence["average_fill_price"])
        buying = is_opening(event)

        if event.event_type == "ENTRY_EXECUTION":
            lower = Decimal(evidence["intent"]["entry_zone_lower"])
            upper = Decimal(evidence["intent"]["entry_zone_upper"])
            assert bar.low <= upper and bar.high >= lower
            expected_reference = min(max(bar.open, lower), upper)
        elif event.event_type == "STOP_EXECUTION":
            # The stop the ledger carried, gapped only if the session opened
            # through it.
            assert reference in stop_prices or reference == bar.open
            expected_reference = bar.open if bar.open < reference else reference
        else:
            expected_reference = bar.open
        assert reference == expected_reference
        assert bar.low <= reference <= bar.high

        direction = Decimal("1") + (slippage if buying else -slippage)
        assert fill == reference * direction
        assert agrees(Decimal(evidence["notional"]), quantity * fill)
        assert agrees(Decimal(evidence["fee"]), quantity * fill * fee_rate)
        assert agrees(
            Decimal(evidence["slippage_cost"]),
            abs(quantity * fill - quantity * reference),
        )


def test_every_entry_is_sized_from_its_conviction_budget_and_stop_distance(
    scenario: dict[str, Any],
) -> None:
    """The first tranche risks exactly its share of the conviction budget."""

    result = golden_result(scenario["scenario_id"])
    tranche_share = Decimal(str(CONFIG.risk.tranche_schedule[0]))
    nav = Decimal(scenario["starting_nav"])

    for event in result.events:
        if event.event_type != "ENTRY_EXECUTION" or event.status != "EXECUTED":
            continue
        intent = event.evidence["intent"]
        planned_entry = Decimal(intent["entry_zone_upper"])
        quantity = Decimal(event.evidence["filled_quantity"])
        trade = next(
            trade
            for trade in result.trades
            if trade.initial_quantity == quantity
        )
        budget = calculate_risk_budget(
            entry_conviction=Decimal(
                next(
                    decision["entry_conviction"]
                    for decision in scenario["plan"]["decisions"]
                    if decision["action"] == ARM_ENTRY_ACTION
                    and Decimal(decision["entry_zone_upper"]) == planned_entry
                )
            ),
            nav=nav,
            config=CONFIG,
        )
        planned_tranche_risk = quantity * (planned_entry - trade.initial_stop_price)
        expected = budget.risk_budget_amount * tranche_share

        assert abs(planned_tranche_risk - expected) < Decimal("0.000000001")
        # Sizing is planned on the worst price the zone can fill at, so the
        # realised risk can exceed the plan only by that boundary fill's own
        # slippage, and a session that opened inside the zone spends less.
        slippage = result.effective_costs.slippage_bps / BASIS_POINT
        realised = quantity * (trade.initial_entry_price - trade.initial_stop_price)
        assert realised <= planned_tranche_risk + quantity * planned_entry * slippage
        assert realised / nav <= Decimal(
            str(CONFIG.risk.max_risk_at_stop_fraction_nav)
        )


def carried_funding(result: BacktestResult) -> Decimal:
    """Re-derive the carry from the sessions rather than from the engine.

    Funding is charged at the start of a session on the quantity the ledger
    carried into it -- the previous session's closing quantity -- and a
    canonical daily session is one day of carry. Taking the engine's own
    funding number instead would leave carry as the one cost in this
    reconciliation that is never independently derived.
    """

    rate = result.effective_costs.funding_cost_bps_per_day / BASIS_POINT
    carried = Decimal("0")
    total = Decimal("0")
    for bar, point in zip(result.input_bars, result.equity_curve, strict=True):
        total += carried * bar.close * rate
        carried = point.open_quantity
    return total


@pytest.mark.parametrize("cost_profile", COST_PROFILES)
def test_the_money_reconciles_from_the_fills_alone(
    scenario: dict[str, Any],
    cost_profile: str,
) -> None:
    """Walk the fills once, on one convention, and land on the engine's NAV.

    Run on every rung, because the base rung prices no carry: a reconciliation
    that only ever sees a zero funding term is not reconciling one.
    """

    result = golden_result(scenario["scenario_id"], cost_profile)
    fee_rate = result.effective_costs.fee_bps / BASIS_POINT
    opening_notional = Decimal("0")
    closing_notional = Decimal("0")
    closed_quantity = Decimal("0")
    fees = Decimal("0")
    for event in fill_events(result):
        quantity = Decimal(event.evidence["filled_quantity"])
        notional = quantity * Decimal(event.evidence["average_fill_price"])
        fees += notional * fee_rate
        if is_opening(event):
            opening_notional += notional
        else:
            closing_notional += notional
            closed_quantity += quantity

    trade = result.trades[-1] if result.trades else None
    average_entry = trade.average_entry_price if trade is not None else Decimal("0")
    gross = closing_notional - average_entry * closed_quantity
    funding = carried_funding(result)
    open_quantity = result.equity_curve[-1].open_quantity
    unrealized = (
        (result.input_bars[-1].close - average_entry) * open_quantity
        if open_quantity > 0
        else Decimal("0")
    )
    nav = Decimal(scenario["starting_nav"]) + gross - fees - funding + unrealized

    assert abs(result.account.fees_paid - fees) < Decimal("0.000000001")
    assert abs(result.ending_nav - nav) < Decimal("0.000000001")
    total_funding = sum((item.funding for item in result.trades), Decimal("0"))
    assert abs(total_funding - funding) < Decimal("0.000000001")
    if trade is not None and trade.closed:
        assert abs(trade.gross_pnl - gross) < Decimal("0.000000001")
        assert abs(trade.net_pnl - (gross - fees - funding)) < Decimal("0.000000001")
        assert opening_notional == trade.entry_notional
        assert closing_notional == trade.exit_notional
        # R is the reviewed headline of every scenario, so it is re-derived
        # here too rather than resting on the recorded expectation alone: net
        # of every cost, over the risk the entry actually took.
        initial_risk = trade.initial_quantity * (
            trade.initial_entry_price - trade.initial_stop_price
        )
        assert initial_risk > 0
        assert abs(
            trade.r_multiple - (gross - fees - funding) / initial_risk
        ) < Decimal("0.000000001")


def test_no_scenario_averages_down_widens_a_stop_or_leaves_the_risk_ceiling(
    scenario: dict[str, Any],
) -> None:
    """The three rulebook invariants, checked on real sessions end to end."""

    result = golden_result(scenario["scenario_id"])
    quantity = Decimal("0")
    basis = Decimal("0")
    for event in fill_events(result):
        price = Decimal(event.evidence["average_fill_price"])
        filled = Decimal(event.evidence["filled_quantity"])
        if is_opening(event):
            if quantity > 0:
                assert price > basis / quantity
            quantity += filled
            basis += price * filled
        else:
            average = basis / quantity
            basis -= average * filled
            quantity -= filled

    stops = [result.trades[0].initial_stop_price] + [
        Decimal(event.evidence["stop_price"])
        for event in result.events
        if event.event_type == "TRAILING_STOP" and event.status == "APPLIED"
    ]
    for previous, current in zip(stops, stops[1:]):
        assert current > previous

    ceiling = Decimal(str(CONFIG.risk.max_risk_at_stop_fraction_nav))
    for point in result.equity_curve:
        if point.risk_fraction_nav is not None:
            assert Decimal("0") <= point.risk_fraction_nav <= ceiling


# --- determinism and point-in-time replay --------------------------------


def test_scenario_replays_are_deterministic_and_restore_from_their_own_evidence(
    scenario: dict[str, Any],
) -> None:
    first = replay(scenario)
    second = replay(scenario)

    assert first.as_record() == second.as_record()
    assert first.evidence_digest == second.evidence_digest
    assert first.run_id == second.run_id
    assert first.input_digest == second.input_digest
    assert restore_backtest_result(first.as_record()) == first
    assert first.as_record()["nav_policy_version"] == BACKTEST_NAV_POLICY_VERSION


def test_truncating_a_window_never_rewrites_an_earlier_session(
    scenario: dict[str, Any],
) -> None:
    """The BTC-221 replay property, asserted on the engine over real history."""

    full = golden_result(scenario["scenario_id"])
    sessions = len(scenario["bars"])

    for limit in (sessions // 2, sessions - 3):
        short = replay(scenario, bar_limit=limit)
        assert [point.as_record() for point in short.equity_curve] == [
            point.as_record() for point in full.equity_curve[:limit]
        ]
        # The only event a shorter window adds is the notice that its last
        # decision never reached an eligible session.
        kept = [
            event.as_record()
            for event in short.events
            if event.status != "UNEXECUTED"
        ]
        assert kept == [event.as_record() for event in full.events][: len(kept)]


# --- what only real sessions can show ------------------------------------


def test_a_continuously_traded_series_never_gaps_through_a_stop(
    scenario: dict[str, Any],
) -> None:
    """Every stop in the fixture fills at the stop price, and here is why.

    BTC-223 pins the gapped-stop path with constructed bars. On a 24/7 series
    the session boundary carries no gap to open through -- each session opens
    within a tick of the previous close -- so a stop inside a session's range
    is always offered at its own price, and the loss beyond -1R is slippage and
    fees rather than an unfilled distance.
    """

    bars = scenario_bars(scenario["scenario_id"])
    for previous, current in zip(bars, bars[1:]):
        assert abs(current.open - previous.close) / previous.close < Decimal("0.001")

    result = golden_result(scenario["scenario_id"])
    for event in result.events:
        if event.event_type != "STOP_EXECUTION" or event.status != "EXECUTED":
            continue
        evidence = event.evidence
        bar = bar_on(scenario["scenario_id"], event_session(event))
        assert evidence["gapped"] is False
        assert "STOP_FILL_AT_STOP_PRICE" in event.reason_codes
        assert bar.open > Decimal(evidence["reference_price"]) > bar.low


def test_the_cost_ladder_reprices_a_scenario_without_changing_its_decisions(
    scenario: dict[str, Any],
) -> None:
    """BTC-181 changes what a period cost, never what the review decided."""

    results = {
        profile: replay(scenario, cost_profile=profile) for profile in COST_PROFILES
    }
    paths = {
        profile: tuple(
            (event_session(event), event.event_type, event.action, event.status)
            for event in material_events(result)
            if event.event_type != "FUNDING"
        )
        for profile, result in results.items()
    }
    assert len(set(paths.values())) == 1

    nets = {
        profile: sum((trade.net_pnl for trade in result.trades), Decimal("0"))
        for profile, result in results.items()
    }
    assert nets["optimistic"] > nets["base"] > nets["stress"]
    assert (
        results["optimistic"].ending_nav
        > results["base"].ending_nav
        > results["stress"].ending_nav
    )
    for profile, result in results.items():
        assert result.cost_profile.profile == profile
        assert result.cost_profile.as_record()["profile"] == profile
        funding = sum((trade.funding for trade in result.trades), Decimal("0"))
        held_overnight = any(
            point.open_quantity > 0 for point in result.equity_curve
        )
        # Only the stress rung prices carry, and only a position that survived
        # a session boundary can pay it.
        assert funding > 0 if (profile == "stress" and held_overnight) else funding == 0


# --- the findings each period was chosen for -----------------------------


def test_the_october_2023_trend_is_marked_open_rather_than_force_closed() -> None:
    result = golden_result("2023_10_reclaim_trend_runner")
    trade = result.trades[0]
    final = result.equity_curve[-1]

    assert result.end_policy_version == BACKTEST_END_POLICY_VERSION
    assert "BACKTEST_POSITION_OPEN_AT_END" in result.reason_codes
    assert result.final_lifecycle.state == "OPEN_ADDED"
    assert not trade.closed
    assert trade.closed_at is None
    # No closing fill exists, so there is no realized R to report.
    assert trade.r_multiple is None
    assert trade.add_count == 1
    assert result.stopped_out == 0
    assert all(
        event.status != "EXECUTED"
        for event in result.events
        if event.event_type == "STOP_EXECUTION"
    )
    entry, addition = fill_events(result)
    assert Decimal(addition.evidence["average_fill_price"]) > Decimal(
        entry.evidence["average_fill_price"]
    )
    # Two reviewed higher lows, and a standing stop that ended above the
    # average entry, which is why BTC-146 floors the remaining risk at zero.
    trails = [
        event
        for event in result.events
        if event.event_type == "TRAILING_STOP" and event.status == "APPLIED"
    ]
    assert len(trails) == 2
    assert result.final_lifecycle.stop_price > trade.average_entry_price
    assert final.open_quantity == trade.initial_quantity + Decimal(
        addition.evidence["filled_quantity"]
    )
    assert final.nav > result.starting_nav


def test_the_january_2024_zone_that_was_never_touched_costs_nothing() -> None:
    scenario = scenario_by_id("2024_01_etf_launch_sell_the_news")
    result = golden_result(scenario["scenario_id"])
    missed = next(
        event
        for event in result.events
        if event.event_type == "ENTRY_EXECUTION" and event.status == "MISSED"
    )
    session = event_session(missed)
    bar = bar_on(scenario["scenario_id"], session)
    intent = missed.evidence["intent"]

    assert result.missed_entries == 1
    assert bar.high < Decimal(intent["entry_zone_lower"])
    assert missed.reason_codes == (
        "ENTRY_ZONE_NOT_TOUCHED",
        "ENTRY_EXECUTION_MISSED",
        "ENTRY_DO_NOT_CHASE",
    )
    assert Decimal(missed.evidence["filled_quantity"]) == 0
    assert Decimal(missed.evidence["notional"]) == 0
    assert Decimal(missed.evidence["fee"]) == 0
    # The account is untouched until the second, reviewed entry fills.
    point = next(
        item
        for item in result.equity_curve
        if item.bar_timestamp.date().isoformat() == session
    )
    assert point.nav == result.starting_nav
    assert point.cash == result.starting_nav
    assert point.open_quantity == 0
    # The miss is terminal: it is never re-armed on a later session.
    assert [
        event_session(event)
        for event in result.events
        if event.event_type == "ENTRY_EXECUTION"
    ] == ["2024-01-12", "2024-01-23"]


def test_the_january_2024_reclaim_is_stopped_on_its_own_entry_session() -> None:
    scenario_id = "2024_01_etf_launch_sell_the_news"
    result = golden_result(scenario_id)
    entry, stop = fill_events(result)
    trade = result.trades[0]
    bar = bar_on(scenario_id, event_session(entry))

    assert event_session(entry) == event_session(stop) == "2024-01-23"
    assert trade.opened_at == trade.closed_at
    assert bar.low <= trade.initial_stop_price < bar.open
    assert trade.exit_reason == "STRUCTURAL_STOP"
    assert trade.r_multiple < Decimal("-1")
    # One session holds no intrabar path, so BTC-165 reports no excursion
    # rather than inventing one.
    assert trade.maximum_favourable_excursion is None
    assert trade.maximum_adverse_excursion is None
    assert trade.excursion_bars == ()


def test_the_july_2024_exit_beat_the_stop_and_left_before_the_capitulation() -> None:
    scenario_id = "2024_07_regime_invalidation_exit"
    result = golden_result(scenario_id)
    trade = result.trades[0]
    exit_event = next(
        event for event in result.events if event.event_type == "EXIT_EXECUTION"
    )
    exit_session = event_session(exit_event)
    exit_price = Decimal(exit_event.evidence["average_fill_price"])
    slippage = result.effective_costs.slippage_bps / BASIS_POINT

    assert trade.exit_reason == "REGIME_INVALIDATION"
    assert exit_session == "2024-07-31"
    assert result.stopped_out == 0

    # The stop was still untouched when the exit filled, and the next session
    # would have taken it: the reviewed counterfactual, priced from the bars.
    stop_price = trade.initial_stop_price
    assert bar_on(scenario_id, exit_session).low > stop_price
    next_session = bar_on(scenario_id, "2024-08-01")
    assert next_session.low < stop_price < next_session.open
    stop_fill = stop_price * (Decimal("1") - slippage)
    assert exit_price > stop_fill
    entry_price = trade.initial_entry_price
    stop_r = -(entry_price - stop_fill) / (entry_price - stop_price)
    assert stop_r < Decimal("-1") < trade.r_multiple < Decimal("-0.3")

    # And nothing was exposed to the 5 August unwind.
    capitulation = bar_on(scenario_id, "2024-08-05")
    assert capitulation.low < exit_price * Decimal("0.8")
    assert all(
        point.open_quantity == 0
        for point in result.equity_curve
        if point.bar_timestamp.date().isoformat() > exit_session
    )
    navs = {
        point.nav
        for point in result.equity_curve
        if point.bar_timestamp.date().isoformat() >= exit_session
    }
    assert navs == {result.ending_nav}


def test_the_march_2024_stop_made_the_queued_trim_stale() -> None:
    scenario_id = "2024_02_ath_trend_tranches"
    result = golden_result(scenario_id)
    trade = result.trades[0]
    stop_event = next(
        event
        for event in result.events
        if event.event_type == "STOP_EXECUTION" and event.status == "EXECUTED"
    )
    stale = next(event for event in result.events if event.status == "STALE")

    assert "BACKTEST_INTENT_STALE" in result.reason_codes
    assert event_session(stale) == event_session(stop_event) == "2024-03-15"
    assert stale.sequence > stop_event.sequence
    assert stale.action == TRIM_ACTION
    assert stale.reason_codes == ("POSITION_STATE_CHANGED_BEFORE_EXECUTION",)
    # Exactly one trim reached the ledger, and it did not re-base the average
    # entry, so the R denominator is still the risk taken at entry.
    assert trade.trim_count == 1
    assert trade.average_entry_price == trade.initial_entry_price
    assert trade.initial_risk == trade.initial_quantity * (
        trade.initial_entry_price - trade.initial_stop_price
    )
    assert trade.r_multiple > Decimal("8")


def test_the_october_2025_stop_is_scoped_to_the_pinned_source() -> None:
    scenario = scenario_by_id("2025_10_source_sensitive_stop")
    sensitivity = scenario["source_sensitivity"]
    result = golden_result(scenario["scenario_id"])
    trade = result.trades[0]
    session = sensitivity["session"]
    bar = bar_on(scenario["scenario_id"], session)
    lows = {
        venue: Decimal(value) for venue, value in sensitivity["venue_lows"].items()
    }

    # The recorded venue evidence must agree with the series the fixture ships.
    assert lows[DATASET["provider"]] == bar.low
    assert trade.exit_reason == "STRUCTURAL_STOP"
    assert (trade.closed_at - DAY).date().isoformat() == session
    # The stop sits inside the band the venues disagreed over, which is the
    # whole reason this expectation is source scoped.
    assert lows["bitfinex"] < lows["coinbase"] < trade.initial_stop_price < lows["bitstamp"]
    assert sensitivity["policy_reference"].startswith("PRICE_SOURCE_POLICY_V1")
    assert DATASET["canonical_reference_status"] == "UNRESOLVED"
    assert Decimal("-1.1") < trade.r_multiple < Decimal("-1")
    # The stop was not a shakeout: the window closes below it.
    assert result.input_bars[-1].close < trade.initial_stop_price


def test_the_reviewed_february_2024_add_is_still_refused_in_composition() -> None:
    """A limit this period reaches on real sessions, recorded rather than hidden.

    The reviewed plan added a second tranche on 27 February. BTC-155 allocates
    that tranche as a notional divided by a price, which does not terminate in
    Decimal's context, and BTC-165's pro-rata trim basis then misses its own
    cash-flow identity. BTC-223 found the same composition gap on constructed
    bars and left it to its owner; this pins that the gap is reachable from an
    ordinary review of an ordinary period, so the replayed plan carries the
    trim and the add is held here until the owner makes the basis exact.
    """

    scenario = scenario_by_id("2024_02_ath_trend_tranches")
    limit = scenario["known_composition_limit"]
    decisions = sorted(
        [*scenario["plan"]["decisions"], limit["decision"]],
        key=lambda decision: decision["on"],
    )
    reviewed = {
        **scenario,
        "plan": {**scenario["plan"], "decisions": decisions},
    }

    assert limit["decision"]["action"] == ADD_ACTION
    with pytest.raises(ValueError, match=limit["expected_error"]):
        replay(reviewed)
