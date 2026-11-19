"""RBT-007 ``RUN_FIRST_RESEARCH_BACKTEST_V1``: the runner, the shared results, the audit and the report.

Every test is synthetic: the RBT-004/RBT-005 composer worlds, the committed
preregistration and throwaway directories. No real-data value is read or
computed, and nothing touches the private store, the holdout or BTC-019.
"""

from __future__ import annotations

import copy
import json
import pickle
import subprocess
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from btc_predictor.backtest.costs import cost_profile
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest import runner as rn
from btc_predictor.research_backtest import runner_metrics as rm
from btc_predictor.research_backtest import runner_report as rr
from btc_predictor.research_backtest import runner_shared as rs
from btc_predictor.research_backtest.replay_inputs import COINBASE_REPLAY_VENUE, canonical_json_bytes
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, Scenario, utc
from btc_predictor.tests.rbt005_management_fixtures import management_market

REPOSITORY = Path(__file__).resolve().parents[2]
START, LAST = utc(2024, 3, 25), utc(2024, 4, 18)
SCHEDULE = tuple(utc(2024, 3, 10) + DAY * index for index in range(40))
SYNTHETIC_FOLD_BARS = 24 * 7


# --- fixtures ----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def preregistration():
    return rn.read_preregistration(REPOSITORY)


@pytest.fixture(scope="module")
def markets():
    return {
        "BITSTAMP": management_market(end=utc(2024, 4, 20)).build(),
        "COINBASE": management_market(end=utc(2024, 4, 20), venue=COINBASE_REPLAY_VENUE).build(),
    }


def _registry(preregistration):
    registry = rn.Registry(champion=CONFIG)
    registry.add(rn.Variant(rn.CHAMPION, CONFIG, "CHAMPION"))
    for variant in rn.sweep_variants(preregistration["threshold_sweeps"]["sweeps"], CONFIG):
        if variant.sweep_index == 0:
            registry.add(variant)
    registry.add(rn.ablation_variant(preregistration["ablation"], CONFIG))
    return registry


GOLDEN = {
    "synthetic_golden": {
        "scenario_id": "synthetic_golden",
        "period": {"start": "2024-03-29", "end": "2024-04-05"},
        "cost_profile": "base",
        "starting_nav": "1000000",
        "plan": {"decisions": [{"on": "2024-03-30", "action": "ARM_ENTRY"}]},
    }
}


@pytest.fixture(scope="module")
def share_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("shared")


@pytest.fixture(scope="module")
def share(markets, share_dir):
    encoder = rs.ArgumentEncoder()
    for inputs in markets.values():
        rs.register_positioning_sources(encoder, inputs)
    store = rs.SharedResultStore(share_dir)
    return lambda: rs.shared_positioning(store, encoder)


@pytest.fixture(scope="module")
def context(markets, preregistration, share):
    with share():
        history = {"BITSTAMP": rn.continuous_history(markets["BITSTAMP"], CONFIG, LAST, SCHEDULE)}
    return rn.RunContext(
        inputs={"BITSTAMP": markets["BITSTAMP"]},
        registry=_registry(preregistration),
        evaluation={"BITSTAMP": (START, LAST)},
        golden=GOLDEN,
        fold_bars=SYNTHETIC_FOLD_BARS,
        history=history,
        schedule=SCHEDULE,
    )


@pytest.fixture(scope="module")
def headline(context, share):
    with share():
        return rn.execute_run(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context, record_management=True)


@pytest.fixture(scope="module")
def walk_forward(context, share):
    with share():
        return rn.execute_run(rn.RunSpec(rn.WALK_FORWARD, "BITSTAMP", rn.CHAMPION, "base"), context)


# --- the shared positioning results (the runtime ruling, ruling 6) -------------------------------


def test_the_share_covers_the_four_public_owners_and_ruling_6s_helpers():
    assert rs.SHARED_PUBLIC_FUNCTIONS == ("funding_health", "futures_basis_health", "open_interest_growth_health", "open_interest_intensity")
    assert set(rs.SHARED_HELPER_FUNCTIONS) == {
        "_open_interest_growth_by_time",
        "_funding_averages_by_time",
        "_futures_basis_averages_by_time",
        "_aggregate_open_interest_by_time",
    }


def test_rows_key_by_source_content_and_position(markets):
    a, b = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates, markets["COINBASE"].dataset.shared_snapshot.funding_rates
    assert a == b and a is not b
    encoder = rs.ArgumentEncoder()
    assert encoder.register_source(a) == encoder.register_source(b)
    key = encoder.key("funding_health", (a[:50],), {"as_of": utc(2024, 3, 1)})
    assert encoder.key("funding_health", (b[:50],), {"as_of": utc(2024, 3, 1)}) == key
    assert encoder.key("funding_health", (a[:49],), {"as_of": utc(2024, 3, 1)}) != key
    assert encoder.key("funding_health", (tuple(reversed(a[:50])),), {"as_of": utc(2024, 3, 1)}) != key
    assert encoder.key("funding_health", (a[:50],), {"as_of": utc(2024, 3, 2)}) != key
    assert encoder.key("funding_averages", (a[:50],), {"as_of": utc(2024, 3, 1)}) != key


def test_keys_keep_decimal_exponents_and_mapping_order():
    encoder = rs.ArgumentEncoder()
    assert encoder.key("f", (Decimal("1.0"),), {}) != encoder.key("f", (Decimal("1.00"),), {})
    first = {utc(2024, 1, 1): Decimal("1"), utc(2024, 1, 2): Decimal("2")}
    second = dict(reversed(list(first.items())))
    assert first == second
    assert encoder.key("f", (first,), {}) != encoder.key("f", (second,), {})
    assert encoder.key("f", (first,), {}) == encoder.key("f", (dict(first),), {})


def test_an_unregistered_row_or_a_naive_time_is_never_shared(markets):
    encoder = rs.ArgumentEncoder()
    rows = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates
    with pytest.raises(rs.Unencodable):
        encoder.key("funding_health", (rows[:3],), {})
    with pytest.raises(rs.Unencodable):
        encoder.key("f", (utc(2024, 1, 1).replace(tzinfo=None),), {})
    encoder.register_source(rows)
    copies = tuple(replace(row) for row in rows[:3])
    assert copies == rows[:3]
    with pytest.raises(rs.Unencodable):  # equal values, but not the source's objects
        encoder.key("funding_health", (copies,), {})


def test_the_store_serves_fresh_copies_and_refuses_another_keys_file(tmp_path):
    store = rs.SharedResultStore(tmp_path, memory_entries=1)
    store.put("a" * 64, "f", {"x": [1, 2]})
    served = store.get("a" * 64, "f")
    served["x"].append(3)
    assert store.get("a" * 64, "f") == {"x": [1, 2]}
    assert store.get("b" * 64, "f") is rs.MISSING
    with pytest.raises(rs.SharedPositioningError):
        store.get("a" * 64, "g")
    other = rs.SharedResultStore(tmp_path / "other")
    other.put("c" * 64, "f", 1)
    (tmp_path / "other" / "dd").mkdir()
    source = tmp_path / "other" / "cc" / ("c" * 64 + ".pickle")
    target = tmp_path / "other" / "dd" / ("d" * 64 + ".pickle")
    target.write_bytes(source.read_bytes())
    with pytest.raises(rs.SharedPositioningError):
        rs.SharedResultStore(tmp_path / "other").get("d" * 64, "f")


def test_shared_results_give_byte_identical_ledgers_across_venues(markets, tmp_path):
    first, last = utc(2024, 3, 28), utc(2024, 3, 31)

    def ledger(inputs):
        composer = ec.EntryComposer(inputs, strategy_config=CONFIG)
        instant = first
        while instant <= last:
            composer.record(composer.decide(instant))
            instant += DAY
        return composer.ledger_bytes()

    plain = {venue: ledger(inputs) for venue, inputs in markets.items()}
    encoder = rs.ArgumentEncoder()
    for inputs in markets.values():
        rs.register_positioning_sources(encoder, inputs)
    originals = {name: getattr(ec, name) for name in rs.SHARED_FUNCTIONS}
    with rs.shared_positioning(rs.SharedResultStore(tmp_path), encoder) as stats:
        shared = {venue: ledger(inputs) for venue, inputs in markets.items()}
    assert shared == plain
    assert {name: getattr(ec, name) for name in rs.SHARED_FUNCTIONS} == originals
    record = stats.as_record()
    assert all(entry["not_shared"] == 0 for entry in record.values())
    # the second venue is served entirely from the first venue's results
    assert all(entry["served"] >= entry["computed"] > 0 for entry in record.values())


def test_a_misbound_name_refuses_the_share(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "funding_health", lambda *args, **kwargs: None)
    with pytest.raises(rs.SharedPositioningError):
        with rs.shared_positioning(rs.SharedResultStore(tmp_path), rs.ArgumentEncoder()):
            pass


def test_an_unencodable_call_reaches_the_owner_unshared(markets, tmp_path):
    rows = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates
    with rs.shared_positioning(rs.SharedResultStore(tmp_path), rs.ArgumentEncoder()) as stats:
        result = ec.funding_health(rows, as_of=utc(2024, 3, 1))
    assert result == rs.positioning.funding_health(rows, as_of=utc(2024, 3, 1))
    assert stats.not_shared["funding_health"] == 1 and stats.computed["funding_health"] == 0


# --- the variants and the registry (ruling 2) ------------------------------------------------------


def test_the_sweep_variants_are_the_preregistered_candidates(preregistration):
    variants = rn.sweep_variants(preregistration["threshold_sweeps"]["sweeps"], CONFIG)
    swept = [record for record in preregistration["threshold_sweeps"]["sweeps"] if record["status"] == "SWEPT"]
    assert len(variants) == sum(len(record["candidate_values"]) for record in swept) == 68
    base = rn.prereg._configuration_mapping()
    for variant in variants:
        record = preregistration["threshold_sweeps"]["sweeps"][variant.sweep_index]
        value = Decimal(variant.value)
        assert value in {Decimal(item) for item in record["candidate_values"]}
        assert variant.config.run_metadata()["parameter_set_id"] == variant.variant_id
        assert rn.prereg._candidate_refusal(base, record["parameter"], record["parameter_paths"], value) is None
        updates = {path: rn._configured_number(base, path, value) for path in record["parameter_paths"]}
        assert rn._with_paths(base, updates, variant.variant_id) == variant.config
        unchanged = rn._with_paths(base, {}, variant.variant_id)
        assert (variant.config == unchanged) == (value == Decimal(record["configured_value"]))


def test_the_ablation_variant_holds_the_frozen_weights(preregistration):
    variant = rn.ablation_variant(preregistration["ablation"], CONFIG)
    weights = {key: Decimal(str(value)) for key, value in variant.config.scoring_weights.hold_score.items()}
    assert weights == {key: Decimal(value) for key, value in preregistration["ablation"]["variant_weights"].items()}
    assert weights["momentum_persistence"] == 0
    tampered = copy.deepcopy(preregistration["ablation"])
    tampered["variant_weights"]["trend"] = "0.3"
    with pytest.raises(rn.RunnerRefused, match="ABLATION_REFUSED"):
        rn.ablation_variant(tampered, CONFIG)


def test_only_a_registered_configuration_reaches_the_composer(context, markets):
    registered = next(variant for variant in context.registry.variants.values() if variant.role == rn.SWEEP)
    copy_of = rn.Variant(registered.variant_id, registered.config, registered.role)
    with pytest.raises(rn.RunnerRefused, match="REGISTRY_REFUSED"):
        rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=copy_of, registry=context.registry)
    composer = rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=registered, registry=context.registry)
    assert composer.strategy_config is registered.config
    decision = composer.decide(utc(2024, 3, 31))
    assert decision.composition.run.results["regime_classification"].config_metadata == registered.config.run_metadata()
    champion = rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=context.registry.variants[rn.CHAMPION], registry=context.registry)
    assert champion.strategy_config is CONFIG


# --- the frozen inputs and code (ruling 2) ----------------------------------------------------------


def test_the_preregistration_must_match_its_digest(tmp_path):
    directory = tmp_path / rn.prereg.ARTIFACT_DIRECTORY
    directory.mkdir(parents=True)
    data = (REPOSITORY / rn.PREREGISTRATION_PATH).read_bytes()
    (tmp_path / rn.PREREGISTRATION_PATH).write_bytes(data)
    (tmp_path / rn.PREREGISTRATION_DIGEST_PATH).write_bytes((REPOSITORY / rn.PREREGISTRATION_DIGEST_PATH).read_bytes())
    assert rn.read_preregistration(tmp_path)["code_commit"].startswith("2be45ad")
    (tmp_path / rn.PREREGISTRATION_PATH).write_bytes(data.replace(b'"base"', b'"BASE"', 1))
    with pytest.raises(rn.RunnerRefused, match="PREREGISTRATION_REFUSED"):
        rn.read_preregistration(tmp_path)


def test_every_frozen_choice_rederives_and_tampering_refuses(preregistration):
    rn.verify_preregistration(preregistration, CONFIG)
    for path, value in (
        (("threshold_sweeps", "sweeps", 0, "candidate_values"), ["72"]),
        (("cost_ladder", "rungs", "base", "fee_bps"), "1"),
        (("decision_schedule", "instants"), 2190),
        (("report", "metric_spec_sha256"), "0" * 64),
    ):
        tampered = copy.deepcopy(preregistration)
        node = tampered
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        with pytest.raises(rn.RunnerRefused, match="PREREGISTRATION_REFUSED"):
            rn.verify_preregistration(tampered, CONFIG)


def test_the_frozen_code_check_finds_a_changed_or_missing_file(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "a.py").write_text("one\n")
    (tmp_path / "b.py").write_text("two\n")
    git("add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c")
    commit = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    assert rn.frozen_code_mismatches(tmp_path, commit, ["a.py", "b.py"]) == []
    (tmp_path / "b.py").write_text("changed\n")
    (tmp_path / "c.py").write_text("new\n")
    assert rn.frozen_code_mismatches(tmp_path, commit, ["a.py", "b.py", "c.py"]) == ["b.py", "c.py"]


def test_the_loaded_repository_code_is_the_frozen_commit(preregistration):
    import sys

    paths = rn.frozen_code_paths(REPOSITORY, list(sys.modules.values()))
    assert "btc_predictor/research_backtest/entry_composer.py" in paths
    assert "btc_predictor/research_backtest/management_composer.py" in paths
    assert "btc_predictor/features/positioning.py" in paths
    assert rn.STRATEGY_CONFIG_PATH.as_posix() in paths and rn.GOLDEN_FIXTURE_PATH.as_posix() in paths
    assert not any((path.startswith("btc_predictor/tests/") and path.endswith(".py")) or Path(path).name in rn.RUNNER_MODULES for path in paths)
    assert rn.frozen_code_mismatches(REPOSITORY, preregistration["code_commit"], paths) == []


# --- windows, folds and runs ----------------------------------------------------------------------------


def test_a_headline_run_composes_exactly_its_window(headline):
    rows = headline.record["entry_ledger"]
    assert rows[0]["decision_at"] == START.isoformat() and rows[-1]["decision_at"] == LAST.isoformat()
    assert len(rows) == (LAST - START) // DAY + 1
    assert all(rn._bar_available_at(bar) < LAST + DAY for bar in headline.result.input_bars)
    assert headline.record["unaccounted"] == []
    assert headline.record["memory"]["matches_history"] and headline.record["memory"]["compared_rows"] == len(rows)
    assert headline.record["trade_entries"] == {"0": "2024-03-31T00:00:00+00:00"}
    assert headline.record["engine_events"]["INTENT:ARM_ENTRY:QUEUED"] == 1


def test_ruling_4_folds_are_4368_hourly_bars_from_the_evaluation_start(walk_forward):
    assert rn.FOLD_BARS == 4368
    folds = walk_forward.record["folds"]
    assert [fold["bars"] for fold in folds] == [SYNTHETIC_FOLD_BARS] * 3
    assert folds[0]["first_decision"] == START.isoformat()
    assert [fold["decisions"] for fold in folds] == [7, 7, 7]
    assert walk_forward.record["plan"]["embargo_periods"] == 0 and walk_forward.record["plan"]["scheme"] == "expanding"
    assert "regime_breakdown" in walk_forward.record and "validation" not in walk_forward.record["regime_breakdown"]


def test_a_fold_shifted_by_omitted_hours_starts_from_the_history_before_its_first_decision(preregistration):
    # review F1: two omitted hours shift every later fold to start at 02:00 (ruling 4's Bitfinex case)
    gapped = management_market(end=utc(2024, 4, 20), missing_hours=(utc(2024, 3, 26, 10), utc(2024, 3, 26, 11))).build()
    history = {"BITSTAMP": rn.continuous_history(gapped, CONFIG, LAST, SCHEDULE)}
    context = rn.RunContext(
        inputs={"BITSTAMP": gapped},
        registry=_registry(preregistration),
        evaluation={"BITSTAMP": (START, LAST)},
        fold_bars=SYNTHETIC_FOLD_BARS,
        history=history,
        schedule=SCHEDULE,
    )
    outcome = rn.execute_run(rn.RunSpec(rn.WALK_FORWARD, "BITSTAMP", rn.CHAMPION, "base"), context)
    folds = outcome.record["folds"]
    window = rn.bars_before(rn.venue_bars(gapped), LAST + DAY)
    starts = [rn._bar_available_at(window[w.test_start_index]) for w in rn.walk_forward_windows([bar.timestamp for bar in window], plan=rn.fold_plan_bars(CONFIG, window, START, SYNTHETIC_FOLD_BARS))]
    assert [start.hour for start in starts] == [0, 2, 2]
    assert [fold["first_decision"] for fold in folds] == [day.isoformat() for day in (START, utc(2024, 4, 2), utc(2024, 4, 9))]
    assert [fold["decisions"] for fold in folds] == [8, 7, 7]
    for fold, ledger, strategy in zip(folds, outcome.record["entry_ledgers"], outcome.composers, strict=True):
        first = rn.datetime.fromisoformat(fold["first_decision"])
        assert ledger[0]["decision_at"] == fold["first_decision"]
        seeded = strategy.entry.ledger[: strategy.entry.seeded]
        assert seeded == tuple(row for row in history["BITSTAMP"] if row.decision_at < first) and seeded[-1].decision_at == first - DAY
    assert outcome.record["memory"]["matches_history"] and outcome.record["unaccounted"] == []
    assert rn.first_decision_at(utc(2024, 4, 1, 2)) == utc(2024, 4, 2) and rn.first_decision_at(START) == START


def test_the_ruling_4_check_compares_the_preregistered_fold_dates(preregistration):
    frozen = preregistration["venues"]["BITSTAMP"]
    same = [
        {"fold_number": item["fold_number"], "first_decision": item["test_start"], "last_decision": item["test_end"], "decisions": 182}
        for item in frozen["walk_forward"]["folds"]
    ]
    assert rn_report_check("BITSTAMP", same, frozen)["equal"]
    shifted = copy.deepcopy(same)
    shifted[0]["last_decision"] = "2024-09-08T00:00:00+00:00"
    shifted[0]["decisions"] = 183
    check = rn_report_check("BITFINEX", shifted, frozen)
    assert not check["equal"] and check["decisions_per_fold"] == [183, 182, 182]


def rn_report_check(venue, folds, frozen):
    return rr.ruling4_check(venue, folds, frozen)


def test_a_golden_window_holds_each_period_days_close():
    first, last = rn.golden_window({"period": {"start": "2023-07-20", "end": "2023-08-25"}})
    assert (first, last) == (utc(2023, 7, 21), utc(2023, 8, 26))


def test_a_history_that_stops_short_of_a_window_refuses(context):
    short = replace(context, history={"BITSTAMP": tuple(row for row in context.history["BITSTAMP"] if row.decision_at < START - 2 * DAY)})
    with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
        short.seed("BITSTAMP", START)


def test_a_cold_start_differs_from_the_continuous_history(context, markets):
    seeded = rn.RegisteredEntryComposer(
        markets["BITSTAMP"], variant=context.registry.variants[rn.CHAMPION], registry=context.registry, history=context.seed("BITSTAMP", START)
    ).decide(START)
    cold = ec.EntryComposer(markets["BITSTAMP"], strategy_config=CONFIG).decide(START)
    reference = {row.decision_at: row for row in context.history["BITSTAMP"]}[START]
    assert seeded.row.regime == reference.regime
    assert cold.row.regime["previous_smoothed_score"] is None and seeded.row.regime["previous_smoothed_score"] is not None


def test_engine_events_are_counted_with_each_refusals_reasons():
    # RBT-006's surfaced point: entry conviction 72 has no risk band below 80, so its runs report the engine's outcomes
    def event(event_type, action, status, *reasons):
        return SimpleNamespace(event_type=event_type, action=action, status=status, reason_codes=reasons)

    first = SimpleNamespace(events=(event("INTENT", "ARM_ENTRY", "QUEUED"), event("INTENT", "ARM_ENTRY", "REFUSED", "A", "B")))
    second = SimpleNamespace(events=(event("INTENT", "ARM_ENTRY", "QUEUED"), event("ENTRY_EXECUTION", "ARM_ENTRY", "EXECUTED")))
    assert rn.event_counts([first, second]) == {
        "ENTRY_EXECUTION:ARM_ENTRY:EXECUTED": 1,
        "INTENT:ARM_ENTRY:QUEUED": 2,
        "INTENT:ARM_ENTRY:REFUSED:A,B": 1,
    }


def test_sweep_runs_execute_on_the_base_rungs_costs(context, share):
    variant = next(variant for variant in context.registry.variants.values() if variant.role == rn.SWEEP)
    with share():
        outcome = rn.execute_run(rn.RunSpec(rn.SWEEP, "BITSTAMP", variant.variant_id, "base"), context)
    assert outcome.validation.cost_profile is None
    assert outcome.validation.effective_costs.as_record() == cost_profile("base", config=variant.config).costs.as_record()


# --- metrics (the frozen definitions) ---------------------------------------------------------------


def test_the_run_view_keeps_btc182s_aggregate_conventions(walk_forward):
    validation = walk_forward.validation
    view = rm.validation_view(validation)
    assert view.mean_return_fraction == validation.mean_return_fraction
    assert view.summed_net_pnl == validation.summed_net_pnl
    assert view.worst_fold.fold_number == validation.worst_fold.fold_number
    assert view.best_fold.fold_number == validation.best_fold.fold_number
    assert [fold.return_fraction for fold in view.folds] == [fold.return_fraction for fold in validation.folds]


def _equity(points, *, start=utc(2024, 1, 1), nav="100"):
    curve = tuple(SimpleNamespace(as_of=start + timedelta(hours=hour), nav=Decimal(value)) for hour, value in points)
    result = SimpleNamespace(equity_curve=curve, started_at=start)
    return SimpleNamespace(starting_nav=Decimal(nav), result=result, fold_number=1)


def test_the_longest_drawdown_follows_its_frozen_definition():
    # drawdown from the starting NAV at started_at, recovered at hour 5
    assert rm._fold_longest_drawdown(_equity([(1, "99"), (3, "98"), (5, "100"), (6, "101")])) == (Decimal(5), True)
    # an unrecovered drawdown ends at the last point; the at-peak instant is that point's as_of
    assert rm._fold_longest_drawdown(_equity([(1, "101"), (2, "100"), (9, "100.5")])) == (Decimal(8), False)
    # equal lengths: the first is reported, recovered, before an equally long unrecovered one
    assert rm._fold_longest_drawdown(_equity([(1, "99"), (2, "100"), (3, "99"), (4, "99.5")])) == (Decimal(2), True)
    # never strictly below the running peak: zero hours
    assert rm._fold_longest_drawdown(_equity([(1, "100"), (2, "100"), (3, "102")])) == (Decimal(0), True)


def test_the_memory_check_finds_a_history_that_differs(context, headline):
    altered = []
    for row in context.history["BITSTAMP"]:
        if row.decision_at == utc(2024, 4, 1):
            row = replace(row, capitulation_flag_state=not row.capitulation_flag_state)
        altered.append(row)
    check = rn.memory_check(replace(context, history={"BITSTAMP": tuple(altered)}), "BITSTAMP", headline.composers)
    assert check["mismatches"] == ["2024-04-01T00:00:00+00:00"] and not check["matches_history"]


def test_sortino_statuses():
    assert rm._sortino((Decimal("0.1"),), "AVAILABLE") == (None, rm.INSUFFICIENT_PERIODS)
    assert rm._sortino((Decimal("0.1"), Decimal("0.2")), "AVAILABLE") == (None, rm.NO_DOWNSIDE)
    value, status = rm._sortino((Decimal("0.1"), Decimal("-0.1")), "AVAILABLE")
    assert status == "AVAILABLE" and value == Decimal("0")
    # mean 0.05 over sqrt(0.01 / 2): the downside deviation divides by n, not n - 1
    value, _ = rm._sortino((Decimal("0.2"), Decimal("-0.1")), "AVAILABLE")
    assert value == Decimal("0.707106781187")
    assert rm._sortino((), "UNDEFINED_NON_POSITIVE_NAV") == (None, "UNDEFINED_NON_POSITIVE_NAV")


def _trade(pnl, closed_at=1, *, closed=True, notional="100"):
    return SimpleNamespace(net_pnl=Decimal(pnl), closed=closed, closed_at=utc(2024, 1, closed_at), entry_notional=Decimal(notional), exit_notional=Decimal(notional), r_multiple=None)


def test_the_trade_metrics_follow_their_definitions(walk_forward):
    trades = (_trade("10", 1), _trade("-5", 2), _trade("0", 3), _trade("-1", 4), _trade("-2", 5), _trade("4", 6, closed=False))
    view = rm.RunView((rm.FoldView(1, walk_forward.validation.folds[0].result),))
    closed = tuple(trade for trade in trades if trade.closed)
    assert rm._losing_streak(closed)["value"] == "2"  # the flat trade ends the first streak
    assert rm._losing_streak(())["value"] == "0"
    factor = rm.setups._profit_factor(closed_count=0, closed_profit=Decimal(0), closed_loss=Decimal(0))
    assert factor == (None, "NO_CLOSED_TRADES")
    assert rm.setups._profit_factor(closed_count=1, closed_profit=Decimal(1), closed_loss=Decimal(0))[1] == "UNBOUNDED_NO_CLOSED_LOSSES"
    metrics = rm.run_metrics(view)
    assert set(metrics) == set(rm.PRIMARY_METRICS)
    assert all("status" in metric for metric in metrics.values())


def test_the_trade_metric_values_follow_their_definitions():
    trades = (_trade("10", 1), _trade("-5", 2), _trade("0", 3), _trade("-1", 4), _trade("-2", 5), _trade("4", 6, closed=False))
    curve = (
        SimpleNamespace(as_of=utc(2024, 1, 1, 1), nav=Decimal("100"), open_quantity=Decimal("1")),
        SimpleNamespace(as_of=utc(2024, 1, 1, 2), nav=Decimal("99"), open_quantity=Decimal("0")),
    )
    result = SimpleNamespace(
        trades=trades,
        equity_curve=curve,
        starting_nav=Decimal("100"),
        total_pnl=Decimal("-1"),
        net_pnl=Decimal("2"),
        final_lifecycle=SimpleNamespace(quantity=Decimal("1")),
        started_at=utc(2024, 1, 1),
        ended_at=utc(2024, 1, 3),
    )
    metrics = rm.run_metrics(rm.RunView((rm.FoldView(1, result),)))
    assert metrics["win_rate"]["value"] == "0.200000000000" and metrics["win_rate"]["winning_trades"] == 1  # flat is not a win
    assert metrics["average_winner"]["value"] == "10.000000000000"
    assert Decimal(metrics["average_loser"]["value"]) == Decimal("-2.666666666667")
    assert metrics["return_per_trade"]["value"] == "0.004000000000"  # mean of net_pnl / entry_notional over closed trades
    assert metrics["profit_factor"]["value"] == str(rm.setups._ratio(Decimal(10), Decimal(8)))
    assert metrics["time_in_market"]["value"] == "0.500000000000"
    assert metrics["turnover"]["value"] == "12.060301507538" and metrics["turnover"]["run_days"] == "2.000000000000"
    assert (metrics["number_of_trades"]["trades"], metrics["number_of_trades"]["closed_trades"], metrics["number_of_trades"]["open_at_end"]) == (6, 5, 1)
    assert metrics["longest_losing_streak"]["value"] == "2"
    assert metrics["expectancy"]["value"] == str(rm.sweeps._mean(tuple(Decimal(value) for value in ("10", "-5", "0", "-1", "-2"))))


def _fake_trade(entry, stop, mfe, mae, *, closed=True, exit_reason="STRUCTURAL_STOP"):
    return SimpleNamespace(
        average_entry_price=Decimal(entry),
        initial_stop_price=Decimal(stop),
        mfe_r=Decimal(mfe),
        mae_r=Decimal(mae),
        closed=closed,
        exit_reason=exit_reason,
        exit_notional=Decimal(entry) * 2,
        fills=(SimpleNamespace(action="ENTER", quantity=Decimal(2)), SimpleNamespace(action="EXIT", quantity=Decimal(2))),
    )


def test_the_cross_venue_measures_follow_clarification_4a():
    entries = {
        "BITSTAMP": [{"decision_at": "d1", "setup": "A"}, {"decision_at": "d2", "setup": "A"}],
        "COINBASE": [{"decision_at": "d1", "setup": "A"}, {"decision_at": "d3", "setup": "B"}],
    }
    trades = {"BITSTAMP": [_fake_trade("100", "90", "2", "-1")], "COINBASE": [_fake_trade("101", "90", "1.5", "-1", exit_reason="EXIT")]}
    trade_entries = {"BITSTAMP": {0: "d1"}, "COINBASE": {0: "d1"}}
    metric = {"value": "1", "status": "AVAILABLE"}
    undefined = {"value": None, "status": "NO_CLOSED_TRADES"}
    metrics = {"base": {"BITSTAMP": {name: metric for name in rm.PRIMARY_METRICS}, "COINBASE": {name: undefined for name in rm.PRIMARY_METRICS}}}
    result = rm.cross_venue(entries, trades, trade_entries, metrics)
    overlap = result["trade_set_overlap"]["pairs"][0]
    assert (overlap["matched"], overlap["only_first"], overlap["only_second"]) == (1, 1, 1)
    assert Decimal(overlap["overlap"]) == (Decimal(1) / Decimal(3)).quantize(Decimal("1E-12"))
    divergence = result["matched_trade_divergence"][0]
    assert divergence["matched"] == 1 and Decimal(divergence["average_entry_price"]["mean"]) == Decimal("0.01")
    assert Decimal(divergence["mfe_r"]["mean"]) == Decimal("-0.5")
    touch = result["stop_touch_divergence"][0]
    assert (touch["matched_closed"], touch["exactly_one_structural_stop"]) == (1, 1)
    assert result["metric_dispersion"]["base"]["expectancy"]["status"] == "UNDEFINED_ON_SOME_VENUE"


# --- the look-ahead audit (ruling 3) ----------------------------------------------------------------------


def test_truncated_inputs_keep_only_what_is_available_at_the_instant(markets):
    instant = utc(2024, 3, 20)
    truncated = rn.truncated_inputs(markets["BITSTAMP"], instant)
    shared = truncated.dataset.shared_snapshot
    assert truncated.dataset.price_bars and all(bar.ingested_at <= instant for bar in truncated.dataset.price_bars)
    assert all(bar.ingested_at <= instant for bar in shared.volume_bars)
    for rows in (shared.etf_flows, shared.funding_rates, shared.open_interest, shared.perp_volumes, truncated.futures_basis, truncated.market_caps, truncated.liquidation_percentiles):
        assert rows and all(row.available_at <= instant for row in rows)
    assert len(truncated.dataset.price_bars) < len(markets["BITSTAMP"].dataset.price_bars)
    assert truncated.etf_fund_launches == markets["BITSTAMP"].etf_fund_launches


def test_the_audit_sample_is_every_intent_plus_twenty_seeded_instants():
    instants = [START + DAY * index for index in range(60)]
    intents = {instants[3], instants[10]}
    sample = rn.audit_sample("BITSTAMP", instants, intents)
    assert len(sample) == 22 and {instant for instant, reason in sample if reason == "INTENT"} == intents
    assert sample == rn.audit_sample("BITSTAMP", list(reversed(instants)), intents)
    assert sample != rn.audit_sample("COINBASE", instants, intents)


def test_the_audit_passes_on_the_champion(context, headline, share):
    shards = [rn.audit_shard("BITSTAMP", context, headline.record, shard, 2, share=share) for shard in range(2)]
    summary = rn.audit_summary("BITSTAMP", shards)
    assert summary["passed"] and summary["reproduced_by_every_shard"]
    assert summary["audited"] == summary["sample_size"] == 25
    assert summary["management_checked"] > 0 and summary["intent_instants"] > 0


def test_the_audit_catches_an_injected_look_ahead(context, share, monkeypatch):
    real = ec._DecisionRun.run

    def peeking(self):
        # each row also records the close of the first bar after its instant
        decision = real(self)
        later = [bar for bar in self.c._hourly if bar.ingested_at > self.t]
        features = {**decision.row.features, "PEEK": later[0].close if later else None}
        return replace(decision, row=replace(decision.row, features=features))

    monkeypatch.setattr(ec._DecisionRun, "run", peeking)
    with share():
        outcome = rn.execute_run(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context)
    shard = rn.audit_shard("BITSTAMP", context, outcome.record, 0, 4, share=None)
    assert shard["reproduced"]
    assert shard["audited"] and all(not item["entry_row_equal"] for item in shard["audited"])


# --- the report ---------------------------------------------------------------------------------------


def test_the_hold_bands_are_rulebook_20s_at_the_configured_thresholds():
    bands = [rr.hold_band(Decimal(score), CONFIG) for score in ("85", "84.99", "70", "60", "59.9", "50", "49", "40", "39.99")]
    assert bands == ["HOLD_POSSIBLE_ADD", "HOLD", "HOLD", "HOLD_NO_ADD", "DEFENSIVE", "DEFENSIVE", "TRIM", "TRIM", "EXIT"]


def test_the_ablation_band_count_rescores_the_champions_own_inputs(headline, context):
    variant = next(variant for variant in context.registry.variants.values() if variant.role == rn.ABLATION)
    rows = headline.record["management_ledger"]
    counted = rr.ablation_band_differences(rows, CONFIG, variant.config)
    assert counted["hold_evaluations"] == sum(1 for row in rows if row["hold"] and row["hold"]["complete"])
    assert 0 <= counted["differing_action_band"] <= counted["hold_evaluations"]
    assert rr.ablation_band_differences(rows, CONFIG, CONFIG)["differing_action_band"] == 0
    tampered = copy.deepcopy(rows)
    tampered[0]["hold"]["score"] = "1"
    with pytest.raises(rn.RunnerRefused, match="ABLATION_REFUSED"):
        rr.ablation_band_differences(tampered, CONFIG, variant.config)


def test_gap_exposure_counts_lookbacks_that_span_an_omitted_bar():
    gapped = Scenario(start=utc(2024, 1, 1), end=utc(2024, 3, 1), missing_hours=(utc(2024, 2, 5, 10),)).build()
    whole = Scenario(start=utc(2024, 1, 1), end=utc(2024, 3, 1)).build()
    instants = [utc(2024, 2, 3), utc(2024, 2, 7), utc(2024, 2, 12), utc(2024, 2, 13), utc(2024, 2, 28)]
    exposed = rr.gap_exposure(gapped, instants)
    assert rr.gap_exposure(whole, instants)["latest_value"]["realized_volatility_from_daily_bars RV_7"] == 0
    assert exposed["days_before_an_omitted_daily_bar"] == ["2024-02-04"]
    # RV_7 reads 8 daily rows: on 2024-02-13 they still reach 2024-02-04, across the omitted day
    assert exposed["latest_value"]["realized_volatility_from_daily_bars RV_7"] == 3
    assert exposed["latest_value"]["realized_volatility_from_daily_bars RV_60"] == 4
    # the omitted week shows inside the weekly series once a later week exists
    assert exposed["weekly_swing_series"] == 1


def test_limitation_exposure_counts_recorded_codes_and_every_composition():
    entry = [
        {"reasons": ["NO_TRADE"], "flags": {"crowding": {"flagged": True}, "stress": {"mapped": None}}, "guard_refusals": [{"guard_id": "OI_GROWTH_ZERO_VARIANCE_GUARD_V1"}], "owner_reason_codes": {"x": {"reason_codes": ["LEVEL_VOLUME_PERCENTILE_WARM_UP"]}}},
        {"reasons": [ec.CAUSE_DECISION_PRICE_BAR_MISSING], "flags": {}, "guard_refusals": []},
    ]
    management = [{"hold": {"score": "70"}, "reasons": ["RULEBOOK_24_NO_ADDING_ENFORCED"], "intent": {"action": "TRAIL"}, "add": {"outcome": "NOT_EVALUATED"}}]
    gaps = {"latest_value": {"realized_volatility_from_daily_bars RV_7": 0}, "with_zscore_history": {"x": 0}, "weekly_swing_series": 0}
    rows = {row["limitation_id"]: row for row in rr.limitation_exposure(entry, management, gaps)}
    assert rows["SEVERE_CROWDING_IS_CROWDING"]["exposed_instants"] == 1
    assert rows["STRESS_NON_DISCRETIONARY_MISSING"]["exposed_instants"] == 1
    assert rows["E1_CLASS_FUNDING_AND_OI_GROWTH"]["exposed_instants"] == 1
    assert rows["LEVEL_VOLUME_PRE_WARM_UP_PIVOTS"]["exposed_instants"] == 1
    assert rows["RULEBOOK_24_NO_ADDING_ENFORCED"]["exposed_instants"] == 1
    assert rows["ONE_ADD_PER_STRUCTURE"]["exposed_instants"] == 1
    assert rows["REACTION_UNIT"]["exposed_instants"] == 1  # the missing-bar row composed nothing
    assert rows["BTC186_FIFTH_CANDIDATE"]["kind"] == "NOT_COMPOSED"


# --- end to end: the orchestration, the resume, the report and the index ------------------------------


@pytest.fixture(scope="module")
def end_to_end(markets, preregistration, tmp_path_factory):
    registry = _registry(preregistration)
    context = rn.RunContext(
        inputs=dict(markets),
        registry=registry,
        evaluation={venue: (START, LAST) for venue in markets},
        golden=GOLDEN,
        fold_bars=SYNTHETIC_FOLD_BARS,
        schedule=SCHEDULE,
    )
    specs = rn.run_plan(list(markets), registry, GOLDEN)
    workspace = rn.Workspace(tmp_path_factory.mktemp("work"))
    rn.execute_all(context, specs, workspace, workers=4, audit_shards=2, precompute_venue="BITSTAMP")

    def build():
        records = {spec.run_id: rn.read_run(workspace.directory, spec) for spec in specs}
        audits = {venue: rn.audit_summary(venue, rn.read_audit(workspace, venue, 2)) for venue in markets}
        instants = [instant for instant in SCHEDULE if START <= instant <= LAST]
        gaps = {venue: rr.gap_exposure(markets[venue], instants) for venue in markets}
        return rr.build_report(
            preregistration=preregistration,
            preregistration_sha256="synthetic",
            identity={"synthetic": True},
            context=context,
            specs=specs,
            records=records,
            audits=audits,
            gaps=gaps,
            sweep_specs=rn.sweep_specs(preregistration["threshold_sweeps"]["sweeps"], CONFIG)[:1],
            coverage_index={},
        )

    report, files = build()
    return SimpleNamespace(context=context, specs=specs, workspace=workspace, report=report, files=files, build=build)


def test_the_report_states_the_evidence_class_first(end_to_end):
    report = end_to_end.report
    assert next(iter(report)) == "evidence"
    evidence = report["evidence"]
    assert evidence["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING" and evidence["canonical_reference"] == "UNRESOLVED"
    assert len(evidence["prohibited_uses"]) == 5 and evidence["holdout"] == "NOT COLLECTED"
    assert set(evidence["named_limitations"]) == {"BITSTAMP", "COINBASE"}


def test_every_run_has_a_record_and_the_checks_pass(end_to_end):
    integrity = end_to_end.report["integrity"]
    assert integrity["runs"] == integrity["planned_runs"] == len(end_to_end.specs) == 2 * 10
    assert all(integrity["memory_matches_history"].values())
    assert integrity["unaccounted"] == {}
    assert all(audit["passed"] for audit in end_to_end.report["lookahead_audit"].values())


def test_every_rate_has_its_trade_count(end_to_end):
    for rungs in end_to_end.report["headline"].values():
        for entry in rungs.values():
            for name, metric in entry["metrics"].items():
                assert any(key in metric for key in ("closed_trades", "trades")), name


def test_the_sweeps_and_the_ablation_are_labelled_sensitivity_only(end_to_end):
    report = end_to_end.report
    for venue in ("BITSTAMP", "COINBASE"):
        assert report["ablation"][venue]["label"] == "SENSITIVITY_ONLY_NOT_SELECTION"
        sweep = report["sweeps"][venue][0]
        assert sweep["label"] == "SENSITIVITY_ONLY_NOT_SELECTION" and len(sweep["candidates"]) == 2
        assert all("validation" not in point for point in sweep["report"]["points"])


def test_the_golden_replay_reports_its_decisions_beside_the_scripted_ones(end_to_end):
    golden = end_to_end.report["golden_replays"]["synthetic_golden"]["BITSTAMP"]
    assert not golden["engine_refused"]
    assert golden["decisions_beside_scripted"][0]["scripted_action"] == "ARM_ENTRY"
    assert golden["decisions_beside_scripted"][0]["decision_at"] == "2024-03-31T00:00:00+00:00"


def test_a_resumed_run_skips_complete_work_and_reproduces_the_report(end_to_end):
    before = {spec.run_id: rn.run_file(end_to_end.workspace.directory, spec).read_bytes() for spec in end_to_end.specs}
    rn.execute_all(end_to_end.context, end_to_end.specs, end_to_end.workspace, workers=2, audit_shards=2, precompute_venue="BITSTAMP")
    after = {spec.run_id: rn.run_file(end_to_end.workspace.directory, spec).read_bytes() for spec in end_to_end.specs}
    assert before == after
    _report, files = end_to_end.build()
    assert files == end_to_end.files


def test_the_public_index_is_value_free(end_to_end):
    index = rr.public_index(end_to_end.report, end_to_end.files, private_commit=None)
    text = canonical_json_bytes(index).decode()
    for word in ("metrics", "trades", "nav", "pnl", "price", "equity", "score"):
        assert f'"{word}' not in text
    assert set(index["files"]) == set(end_to_end.files)
    assert index["memory_check_failures"] == 0 and index["runs"] == 20


def test_the_decision_ledgers_are_the_champions_base_run(end_to_end):
    ledger = json.loads(end_to_end.files[rr.ledger_file("BITSTAMP")])
    assert ledger["run"]["kind"] == rn.HEADLINE and ledger["run"]["cost_rung"] == "base"
    assert ledger["entry_rows"][0]["decision_at"] == START.isoformat()


def test_main_refuses_when_the_code_is_not_frozen(monkeypatch, tmp_path):
    from btc_predictor.research_backtest import dataset_build as build

    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)

    def refused(repository, commit):
        raise rn.RunnerRefused("FROZEN_CODE_REFUSED", "test")

    monkeypatch.setattr(rn, "require_frozen_code", refused)
    lines = []
    assert rn.main(["run", "--store", str(tmp_path)], out=lines.append) == 2
    assert lines == ["refused: FROZEN_CODE_REFUSED: test"]
    assert not (REPOSITORY / rn.prereg.ARTIFACT_DIRECTORY / rr.INDEX_FILE).exists()
