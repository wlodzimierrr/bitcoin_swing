"""Deterministic synthetic replays for the RBT-005 management-composer tests.

The position comes from the RBT-004 fixtures' natural Setup A entry: the market
``trending_close(daily_drift=0.0003, cycle_days=80.0, cycle_amplitude=0.07)``
arms at 2024-03-31 00:00 and the next bar fills at 01:00. Management branches
the synthetic market does not reach on its own are shown with named
interventions, as RBT-004 shows Setup B and C: a stated owner input, keyword
argument or result field is replaced at a stated decision instant, and the real
owner always runs.

Determinism: no randomness, clock, network or database; every series is a
closed-form function of its index, inside the data window.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest

from btc_predictor.backtest.engine import BacktestResult, run_backtest
from btc_predictor.research_backtest import entry_composer, management_composer
from btc_predictor.research_backtest.entry_composer import EntryComposer, EntryComposerInputs, EntryDecision
from btc_predictor.research_backtest.management_composer import ArmedEntry, ManagementComposer, ManagementDecision
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, trending_close, utc

ARMED_AT = utc(2024, 3, 31)
FILLED_AT = utc(2024, 3, 31, 1)
ENGINE_START = utc(2024, 3, 24, 23)


def management_market(end: datetime = utc(2024, 4, 20), **changes: Any) -> Scenario:
    return Scenario(end=end, close_at=trending_close(daily_drift=0.0003, cycle_days=80.0, cycle_amplitude=0.07), **changes)


class Interventions:
    """Substitute stated owner inputs at stated decision instants; the real owners always run.

    ``instant`` is the instant of the engine callback being served, so an
    intervention keyed on a decision instant never touches the callbacks between
    decisions (where a pending ADD is resolved).
    """

    def __init__(self, patch: pytest.MonkeyPatch) -> None:
        self.instant: datetime | None = None
        self.applied: list[tuple[str, datetime]] = []
        self._patch = patch

    def strategy(self, champion: ManagementComposer) -> Callable[[Any], Any]:
        def serve(context: Any) -> Any:
            self.instant = context.as_of
            return champion(context)

        return serve

    def inputs(self, module: ModuleType, name: str, at: set[datetime], **changes: Any) -> None:
        """Replace fields of the owner's first positional input."""

        real = getattr(module, name)

        def wrapper(inputs: Any, *args: Any, **kwargs: Any) -> Any:
            if self.instant in at:
                inputs = replace(inputs, **changes)
                self.applied.append((name, self.instant))
            return real(inputs, *args, **kwargs)

        self._patch.setattr(module, name, wrapper)

    def kwargs(self, module: ModuleType, name: str, at: set[datetime], **changes: Any) -> None:
        """Replace keyword arguments of the owner call."""

        real = getattr(module, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.instant in at:
                kwargs = {**kwargs, **changes}
                self.applied.append((name, self.instant))
            return real(*args, **kwargs)

        self._patch.setattr(module, name, wrapper)

    def result(self, module: ModuleType, name: str, at: set[datetime], **changes: Any) -> None:
        """Replace fields of the owner's result ("t" stands for the decision instant)."""

        real = getattr(module, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = real(*args, **kwargs)
            if self.instant in at:
                self.applied.append((name, self.instant))
                return replace(result, **{key: (self.instant if value == "t" else value) for key, value in changes.items()})
            return result

        self._patch.setattr(module, name, wrapper)


@dataclass(frozen=True)
class Captured:
    """Everything one management decision was composed from, to compose it again."""

    decision: EntryDecision
    lifecycle: Any
    nav: Decimal
    armed: ArmedEntry
    prior_flow: Any


@dataclass
class ManagedRun:
    inputs: EntryComposerInputs
    champion: ManagementComposer
    result: BacktestResult
    applied: list[tuple[str, datetime]]
    captured: dict[datetime, Captured] = field(default_factory=dict)

    def redecide(self, instant: datetime, *, armed: ArmedEntry | None = None, **composition_changes: Any) -> ManagementDecision:
        """Compose the captured decision at ``instant`` again, on a fresh management ledger.

        ``composition_changes`` replace fields of the entry composition (named
        interventions on the shared owner results); everything else is as
        captured.
        """

        item = self.captured[instant]
        decision = item.decision
        if composition_changes:
            decision = replace(decision, composition=replace(decision.composition, **composition_changes))
        return ManagementComposer(self.champion.entry).decide(
            decision, lifecycle=item.lifecycle, nav=item.nav, armed=armed or item.armed, prior_flow=item.prior_flow
        )

    def rows(self) -> dict[datetime, Any]:
        return {row.decision_at: row for row in self.champion.ledger}

    def events(self, *, event_type: str | None = None, action: str | None = None) -> list[Any]:
        return [
            event
            for event in self.result.events
            if (event_type is None or event.event_type == event_type) and (action is None or event.action == action)
        ]


def engine_bars(inputs: EntryComposerInputs, start: datetime, end: datetime, *, drop: tuple[datetime, ...] = ()) -> tuple[Any, ...]:
    return tuple(bar for bar in inputs.dataset.price_bars if start <= bar.timestamp < end and bar.timestamp not in drop)


def managed_run(
    scenario: Scenario,
    *,
    engine_end: datetime,
    setup: Callable[[Interventions], None] | None = None,
    bars: Callable[[EntryComposerInputs], tuple[Any, ...]] | None = None,
    modify: Callable[[EntryComposerInputs], EntryComposerInputs] | None = None,
    capture: bool = True,
) -> ManagedRun:
    """Run the composed champion through BTC-180 from ENGINE_START to ``engine_end``."""

    inputs = scenario.build() if modify is None else modify(scenario.build())
    champion = ManagementComposer(EntryComposer(inputs, strategy_config=CONFIG))
    captured: dict[datetime, Captured] = {}
    decide = champion.decide

    def capturing(decision: EntryDecision, **kwargs: Any) -> ManagementDecision:
        captured[decision.row.decision_at] = Captured(decision, **kwargs)
        return decide(decision, **kwargs)

    if capture:
        champion.decide = capturing  # type: ignore[method-assign]
    engine = bars(inputs) if bars is not None else engine_bars(inputs, ENGINE_START, engine_end)
    with pytest.MonkeyPatch.context() as patch:
        interventions = Interventions(patch)
        if setup is not None:
            setup(interventions)
        result = run_backtest(engine, strategy=interventions.strategy(champion), strategy_config=CONFIG, symbol=engine[0].symbol)
    if capture:
        del champion.decide
    return ManagedRun(inputs, champion, result, interventions.applied, captured)


def decision_price(inputs: EntryComposerInputs, instant: datetime) -> Decimal:
    return next(bar.close for bar in inputs.dataset.price_bars if bar.ingested_at == instant)


# --- the shared replays (each built once per test process) -----------------------------------

# The trail-and-add instant: a higher low under P_t confirms after the entry, so
# the trail advances; the Add Score's NewStructure component is raised to 90 so
# the add (otherwise blocked only by ADD_SCORE_BELOW_MINIMUM, 83.2) clears 85.
TRAIL_AT = utc(2024, 4, 2)
TRAIL_HIGHER_LOW_FRACTION = Decimal("0.985")
TRAIL_NEW_STRUCTURE_SCORE = Decimal("90")


def higher_low_at(
    interventions: Interventions,
    inputs: EntryComposerInputs,
    instants: set[datetime],
    *,
    formed: datetime | None = None,
    price: Decimal | None = None,
) -> None:
    """The BTC-122 higher low confirms at each instant.

    By default it lies at 98.5% of ``P_t`` and formed the day before; ``formed``
    and ``price`` pin one structure across instants.
    """

    for instant in instants:
        level = price if price is not None else (decision_price(inputs, instant) * TRAIL_HIGHER_LOW_FRACTION).quantize(Decimal("0.01"))
        interventions.result(
            entry_composer, "evaluate_higher_low_trigger", {instant},
            triggered=True, higher_low_price=level, higher_low_timestamp=formed or instant - DAY, detected_at="t",
        )


def add_score_lifted(interventions: Interventions, instants: set[datetime]) -> None:
    interventions.inputs(management_composer, "calculate_add_score", instants, new_structure_score=TRAIL_NEW_STRUCTURE_SCORE)


@contextmanager
def trail_add_interventions(inputs: EntryComposerInputs) -> Iterator[None]:
    """The trail-and-add interventions of :func:`trail_add_run`, to compose TRAIL_AT again."""

    with pytest.MonkeyPatch.context() as patch:
        interventions = Interventions(patch)
        interventions.instant = TRAIL_AT
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})
        yield


@functools.lru_cache(maxsize=None)
def natural_run() -> ManagedRun:
    """The natural Setup A position managed for two weeks: HOLD and TRIM, the trail held."""

    return managed_run(management_market(end=utc(2024, 4, 14)), engine_end=utc(2024, 4, 13, 6))


@functools.lru_cache(maxsize=None)
def trail_add_run() -> ManagedRun:
    """TRAIL at TRAIL_AT with the ADD pending; the ADD follows at the next callback."""

    market = management_market(end=utc(2024, 4, 8))
    inputs = market.build()

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})

    return managed_run(market, engine_end=utc(2024, 4, 5, 6), setup=setup)


__all__ = [
    "ARMED_AT", "CONFIG", "DAY", "ENGINE_START", "FILLED_AT", "HOUR", "TRAIL_AT", "Captured", "Interventions", "ManagedRun",
    "add_score_lifted", "decision_price", "engine_bars", "higher_low_at", "managed_run", "management_market", "natural_run",
    "trail_add_interventions", "trail_add_run", "utc",
]
