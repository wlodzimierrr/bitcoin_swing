"""RBT-006 Part A: the freeze and preregistration definitions and the completeness-only pass.

Synthetic fixtures only (the RBT-004 composer world): no database, no network,
no real-data value. The completeness tests run the reviewed RBT-004 composer.
"""

from __future__ import annotations

import copy
import json
import os
import re
import socket
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.backtest.threshold_sweeps import THRESHOLD_PARAMETERS, threshold_sweep_spec
from btc_predictor.config.strategy import StrategyConfig
from btc_predictor.data import EtfFlow
from btc_predictor.features.hold import HoldScoreInput, calculate_hold_score
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest import preregistration as pr
from btc_predictor.research_backtest.completion_spec import CHAMPION_BASE_IDENTITY
from btc_predictor.research_backtest.replay_inputs import DATA_WINDOW
from btc_predictor.tests import rbt004_composer_fixtures as fx

CONFIG = fx.CONFIG
DAY = timedelta(days=1)
DIGEST = "ab" * 32
COMMIT = "cd" * 20
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("RBT-006 Part A opens no connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def days(first: datetime, count: int) -> list[datetime]:
    return [first + DAY * index for index in range(count)]


# --- ruling 1: ETF fund launch dates ----------------------------------------------------------


def flow(fund: str, day: date, value: str = "1") -> EtfFlow:
    available = datetime(day.year, day.month, day.day, tzinfo=UTC) + 2 * DAY
    return EtfFlow(
        fund=fund,
        observation_date=day,
        flow_usd=Decimal(value),
        aum_usd=None,
        provider="coinglass",
        source="synthetic",
        revision="r1",
        available_at=available,
        ingested_at=available,
    )


def documented_rows(value: str = "1") -> list[EtfFlow]:
    rows = []
    for fund, (first, _) in pr.DOCUMENTED_FIRST_TRADING_DATES.items():
        rows.extend(flow(fund, first + DAY * offset, value) for offset in (0, 1, 5))
    return rows


def test_each_fund_launches_on_its_first_evidence_row_named_by_the_evidence_digest() -> None:
    rows = list(reversed(documented_rows()))
    launches = pr.etf_fund_launches(rows, evidence_sha256=DIGEST)
    assert [launch.fund for launch in launches] == sorted(pr.DOCUMENTED_FIRST_TRADING_DATES)
    for launch in launches:
        assert launch.first_trading_date == pr.DOCUMENTED_FIRST_TRADING_DATES[launch.fund][0]
        assert f"sha256 {DIGEST}" in launch.source and pr.DOCUMENTED_FIRST_TRADING_DATES[launch.fund][1] in launch.source
    by_fund = {launch.fund: launch.first_trading_date for launch in launches}
    assert by_fund["BTC"] == date(2024, 7, 31) and by_fund["GBTC"] == date(2024, 1, 11)
    assert len(launches) == 11


# Written out here, not read from the module (review F4): the public first US
# trading dates and the documents establishing them.
PUBLIC_FIRST_TRADING_DATES = {
    "ARKB": (date(2024, 1, 11), "34-99306", "1869699/000101376225002798/"),
    "BITB": (date(2024, 1, 11), "34-99306", "1763415/000095017025040572/"),
    "BRRR": (date(2024, 1, 11), "34-99306", "1841175/000199937125003309/"),
    "BTC": (date(2024, 7, 31), "34-100610", "2015034/000095017025029405/"),
    "BTCO": (date(2024, 1, 11), "34-99306", "1855781/000095017025029444/"),
    "BTCW": (date(2024, 1, 11), "34-99306", "1850391/000121465925004851/"),
    "EZBC": (date(2024, 1, 11), "34-99306", "1992870/000119312524173040/"),
    "FBTC": (date(2024, 1, 11), "34-99306", "1852317/000095017025039452/"),
    "GBTC": (date(2024, 1, 11), "34-99306", "1588489/000095017025029408/"),
    "HODL": (date(2024, 1, 11), "34-99306", "1838028/000162828024001064/"),
    "IBIT": (date(2024, 1, 11), "34-99306", "1980994/000143774925006260/"),
}


def test_each_documented_date_cites_its_approval_order_and_the_funds_own_filing() -> None:
    documented = pr.DOCUMENTED_FIRST_TRADING_DATES
    assert set(documented) == set(PUBLIC_FIRST_TRADING_DATES)
    for fund, (day, release, filing) in PUBLIC_FIRST_TRADING_DATES.items():
        documented_day, citation = documented[fund]
        assert documented_day == day, fund
        assert f"SEC Release No. {release} " in citation and f"(https://www.sec.gov/Archives/edgar/data/{filing}" in citation, fund
        assert re.search(r"\(\d{10}-\d{2}-\d{6}\)", citation), fund  # the filing's accession number
        assert f"{day:%B} {day.day}, {day.year}" in citation, fund  # the filing's own statement of the date
    assert "CONFLICT" in documented["HODL"][1] and "January 10, 2024" in documented["HODL"][1]
    assert not [fund for fund, (_, citation) in documented.items() if fund != "HODL" and "CONFLICT" in citation]


def test_launch_dates_read_no_value() -> None:
    assert pr.etf_fund_launches(documented_rows("1"), evidence_sha256=DIGEST) == pr.etf_fund_launches(
        documented_rows("-98765.4321"), evidence_sha256=DIGEST
    )


@pytest.mark.parametrize(
    ("edit", "code"),
    [
        (lambda rows: [row for row in rows if not (row.fund == "IBIT" and row.observation_date == date(2024, 1, 11))], "ETF_LAUNCH_MISMATCH"),
        (lambda rows: [*rows, flow("FBTC", date(2024, 1, 10))], "ETF_LAUNCH_MISMATCH"),
        (lambda rows: [*rows, flow("DEFI", date(2024, 3, 14))], "ETF_LAUNCH_REFUSED"),
        (lambda rows: [row for row in rows if row.fund != "BTC"], "ETF_LAUNCH_REFUSED"),
        (lambda rows: [], "ETF_LAUNCH_REFUSED"),
        (lambda rows: [*rows, {"fund": "IBIT"}], "ETF_LAUNCH_REFUSED"),
    ],
    ids=["first-row-later", "first-row-earlier", "undocumented-fund", "documented-fund-absent", "no-row", "not-an-etf-row"],
)
def test_a_launch_that_is_not_the_documented_first_trading_day_refuses(edit, code) -> None:
    with pytest.raises(pr.PreregistrationRefused) as refused:
        pr.etf_fund_launches(edit(documented_rows()), evidence_sha256=DIGEST)
    assert refused.value.reason_code == code


@pytest.mark.parametrize("digest", ["", "AB" * 32, "ab" * 31, None, "ab" * 32 + "\n"])
def test_launches_need_the_evidence_digest(digest) -> None:
    with pytest.raises(pr.PreregistrationRefused, match="ETF_LAUNCH_REFUSED"):
        pr.etf_fund_launches(documented_rows(), evidence_sha256=digest)


# --- the decision schedule and ruling 2 -----------------------------------------------------------


def test_the_schedule_is_every_midnight_strictly_inside_the_data_window() -> None:
    schedule = pr.decision_schedule()
    assert schedule[0] == utc(2020, 1, 2) and schedule[-1] == utc(2025, 12, 31)
    assert len(schedule) == 2191 and len(set(schedule)) == 2191
    assert all(later - earlier == DAY for earlier, later in zip(schedule, schedule[1:]))
    assert all(DATA_WINDOW.start < instant < DATA_WINDOW.end and ec.is_daily_decision_instant(instant) for instant in schedule)
    assert DATA_WINDOW.end not in schedule  # its decision would execute in the holdout


def test_the_folds_start_at_the_evaluation_start_and_report_the_untested_tail() -> None:
    schedule = pr.decision_schedule()
    start = utc(2024, 3, 15)
    record = pr.fold_plan(start, schedule, strategy_config=CONFIG)
    train = schedule.index(start)
    assert record["training_periods"] == train
    plan = record["plan"]
    assert (plan["scheme"], plan["train_periods"], plan["test_periods"], plan["step_periods"], plan["embargo_periods"]) == (
        "expanding",
        train,
        182,
        182,
        0,
    )
    assert record["fold_count"] == (len(schedule) - train) // 182 == 3
    assert record["untested_periods"] == len(schedule) - train - 3 * 182 == (len(schedule) - train) % 182
    assert record["folds"][0]["test_start"] == start.isoformat()
    assert [fold["test_start"] for fold in record["folds"]] == [(start + DAY * 182 * n).isoformat() for n in range(3)]
    assert record["folds"][-1]["test_end"] == (start + DAY * (3 * 182 - 1)).isoformat()
    assert record["capital_policy_version"] == "INDEPENDENT_FOLD_CAPITAL_V1"


def test_a_late_start_leaves_no_fold_and_every_period_untested() -> None:
    schedule = pr.decision_schedule()
    record = pr.fold_plan(utc(2025, 8, 1), schedule, strategy_config=CONFIG)
    assert record["fold_count"] == 0 and record["folds"] == []
    assert record["untested_periods"] == len(schedule) - schedule.index(utc(2025, 8, 1))


@pytest.mark.parametrize("start", [utc(2020, 1, 2), utc(2026, 1, 1), datetime(2024, 3, 15, 1, tzinfo=UTC)])
def test_a_start_with_no_training_or_off_the_schedule_refuses(start) -> None:
    with pytest.raises(pr.PreregistrationRefused, match="FOLD_PLAN_REFUSED"):
        pr.fold_plan(start, pr.decision_schedule(), strategy_config=CONFIG)


def test_the_fold_plan_keeps_the_configured_expanding_scheme() -> None:
    rolling = replace(CONFIG, backtest=replace(CONFIG.backtest, walk_forward=replace(CONFIG.backtest.walk_forward, scheme="rolling")))
    with pytest.raises(pr.PreregistrationRefused, match="expanding"):
        pr.fold_plan(utc(2024, 3, 15), pr.decision_schedule(), strategy_config=rolling)


# --- ruling 3: the threshold-sweep grid -----------------------------------------------------------


@pytest.fixture(scope="module")
def sweeps() -> list[dict]:
    return pr.sweep_grid(CONFIG)


def test_one_sweep_per_distinct_configured_value(sweeps) -> None:
    assert [(sweep["parameter"], sweep["configured_value"]) for sweep in sweeps] == [
        ("entry_conviction", "80"),
        ("trend_minimum", "70"),
        ("trend_minimum", "55"),
        ("flow_minimum", "55"),
        ("positioning_minimum", "60"),
        ("structure_minimum", "70"),
        ("structure_minimum", "60"),
        ("reward_risk_minimum", "2"),
        ("stop_buffer_atr_multiplier", "0.3"),
        ("hold_threshold", "50"),
        ("hold_threshold", "40"),
        ("add_threshold", "85"),
        ("risk_budget_fraction_nav", "0.0035"),
        ("risk_budget_fraction_nav", "0.005"),
        ("risk_budget_fraction_nav", "0.006"),
    ]
    assert {sweep["parameter"] for sweep in sweeps} == set(THRESHOLD_PARAMETERS)
    paths = {(sweep["parameter"], sweep["configured_value"]): sweep["parameter_paths"] for sweep in sweeps}
    assert paths[("structure_minimum", "70")] == [
        "setup_requirements.bull_trend_continuation.structure_min",
        "setup_requirements.bullish_reset.structure_min",
    ]
    assert paths[("structure_minimum", "60")] == ["setup_requirements.capitulation_reversal.structure_min"]
    assert paths[("risk_budget_fraction_nav", "0.005")] == ["risk.schedule.1.risk_fraction_nav"]
    assert paths[("hold_threshold", "50")] == ["hold_thresholds.defensive_min"]
    assert paths[("hold_threshold", "40")] == ["hold_thresholds.exit_below", "hold_thresholds.trim_min"]
    assert all("bearish_distribution" not in path for sweep in sweeps for path in sweep["parameter_paths"])


def test_every_path_holds_its_configured_value(sweeps) -> None:
    base = pr._configuration_mapping()
    for sweep in sweeps:
        for path in sweep["parameter_paths"]:
            assert Decimal(str(pr._get_path(base, path))) == Decimal(sweep["configured_value"])


def test_candidates_the_configuration_refuses_are_dropped_with_their_reason(sweeps) -> None:
    by = {(sweep["parameter"], sweep["configured_value"]): sweep for sweep in sweeps}
    entry = by[("entry_conviction", "80")]
    assert entry["candidate_values"] == ["72", "80"] and entry["status"] == "SWEPT"
    assert [(item["value"], item["reason"]) for item in entry["dropped_candidates"]] == [
        (value, "STRATEGY_CONFIG: entry_thresholds values must be strictly increasing") for value in ("64", "88", "96")
    ]
    defensive = by[("hold_threshold", "50")]
    assert defensive["candidate_values"] == ["45", "50", "55"]
    assert [(item["value"], item["reason"]) for item in defensive["dropped_candidates"]] == [
        (value, "STRATEGY_CONFIG: hold_thresholds values must be strictly decreasing") for value in ("40", "60")
    ]
    trim_exit = by[("hold_threshold", "40")]
    assert trim_exit["candidate_values"] == ["32", "36", "40", "44", "48"] and trim_exit["dropped_candidates"] == []
    add = by[("add_threshold", "85")]
    assert add["candidate_values"] == ["68", "76.5", "85", "93.5"]
    assert [item["value"] for item in add["dropped_candidates"]] == ["102"]
    assert add["dropped_candidates"][0]["reason"].startswith("BTC185_OWNER:")
    stop = by[("stop_buffer_atr_multiplier", "0.3")]
    assert stop["status"] == "SWEPT" and stop["grid_rule"] == pr.STOP_BUFFER_GRID_RULE
    assert stop["candidate_values"] == ["0.25", "0.3", "0.5", "0.75"] and stop["dropped_candidates"] == []
    assert all(sweep["grid_rule"] == pr.UNIFORM_GRID_RULE for sweep in sweeps if sweep is not stop)
    assert by[("risk_budget_fraction_nav", "0.0035")]["candidate_values"] == ["0.0028", "0.00315", "0.0035", "0.00385", "0.0042"]
    assert by[("reward_risk_minimum", "2")]["candidate_values"] == ["1.6", "1.8", "2", "2.2", "2.4"]


def test_every_kept_candidate_is_a_valid_configuration_and_every_dropped_one_is_not(sweeps) -> None:
    base = pr._configuration_mapping()
    for sweep in sweeps:
        for values, accepted in ((sweep["candidate_values"], True), ([item["value"] for item in sweep["dropped_candidates"]], False)):
            for value in values:
                reason = pr._candidate_refusal(base, sweep["parameter"], sweep["parameter_paths"], Decimal(value))
                assert (reason is None) is accepted, (sweep["parameter"], value, reason)
        for value in sweep["candidate_values"]:
            data = copy.deepcopy(base)
            for path in sweep["parameter_paths"]:
                pr._set_path(data, path, float(value))
            StrategyConfig.from_mapping(data)


def test_each_swept_value_is_a_btc185_one_scalar_sweep(sweeps) -> None:
    for sweep in sweeps:
        if sweep["spec"] is None:
            continue
        spec = sweep["spec"]
        rebuilt = threshold_sweep_spec(
            parameter=sweep["parameter"],
            candidate_values=[Decimal(value) for value in sweep["candidate_values"]],
            baseline_value=Decimal(sweep["configured_value"]),
            parameter_paths=sweep["parameter_paths"],
            base_config_metadata=CHAMPION_BASE_IDENTITY,
            objective_metric="mean_return_fraction",
            plateau_tolerance=Decimal("0.005"),
        )
        assert rebuilt.as_record() == spec
        assert spec["objective_metric"] == "mean_return_fraction" and Decimal(spec["plateau_tolerance"]) == Decimal("0.005")
        assert Decimal(spec["baseline_value"]) == Decimal(sweep["configured_value"])
        assert sweep["label"] == "SENSITIVITY_ONLY_NOT_SELECTION" and sweep["cost_rung"] == "base"
    assert all(sweep["status"] == "SWEPT" for sweep in sweeps)


def test_a_value_left_with_fewer_than_two_candidates_is_recorded_as_not_swept(monkeypatch: pytest.MonkeyPatch) -> None:
    real = pr._candidate_refusal

    def only_the_configured_hold(base, parameter, paths, value):
        if parameter == "hold_threshold" and value != Decimal(str(pr._get_path(base, paths[0]))):
            return "STRATEGY_CONFIG: synthetic refusal"
        return real(base, parameter, paths, value)

    monkeypatch.setattr(pr, "_candidate_refusal", only_the_configured_hold)
    holds = [sweep for sweep in pr.sweep_grid(CONFIG) if sweep["parameter"] == "hold_threshold"]
    assert [(hold["status"], hold["spec"], hold["candidate_values"]) for hold in holds] == [
        ("NOT_SWEPT_FEWER_THAN_TWO_CANDIDATES", None, ["50"]),
        ("NOT_SWEPT_FEWER_THAN_TWO_CANDIDATES", None, ["40"]),
    ]
    assert [len(hold["dropped_candidates"]) for hold in holds] == [4, 4]


def _trim_decisions(strategy_config: StrategyConfig) -> list[tuple[str, ...]]:
    """The trim owner's reason codes at every half point of Hold Score, an open position and no other trigger."""

    from btc_predictor.signals.trim import TrimRuleInput, evaluate_trim_rules

    decisions = []
    for half in range(0, 201):
        inputs = TrimRuleInput(
            position_open=True,
            hold_score=Decimal(half) / 2,
            euphoria_active=False,
            crowding_active=False,
            current_flow_score=Decimal("50"),
            prior_flow_score=Decimal("50"),
        )
        decisions.append(tuple(evaluate_trim_rules(inputs, strategy_config=strategy_config).reason_codes))
    return decisions


def _configured(paths, value) -> StrategyConfig:
    data = pr._configuration_mapping()
    for path in paths:
        pr._set_path(data, path, float(value))
    return StrategyConfig.from_mapping(data)


def test_every_hold_candidate_changes_a_decision_of_the_trim_owner(sweeps) -> None:
    holds = [sweep for sweep in sweeps if sweep["parameter"] == "hold_threshold"]
    assert len(holds) == 2
    for sweep in holds:
        decisions = [_trim_decisions(_configured(sweep["parameter_paths"], value)) for value in sweep["candidate_values"]]
        assert all(first != second for first, second in zip(decisions, decisions[1:])), sweep["configured_value"]


def test_the_unread_hold_thresholds_change_no_decision_and_are_recorded() -> None:
    base = pr._configuration_mapping()
    champion = _trim_decisions(_configured([], 0))
    for path, value in (("hold_thresholds.possible_add_min", 88), ("hold_thresholds.hold_min", 77), ("hold_thresholds.no_add_min", 55)):
        assert _trim_decisions(_configured([path], value)) == champion, path
    assert pr.unread_sweep_paths() == [
        {
            "parameter": "hold_threshold",
            "paths": {path: str(pr._get_path(base, path)) for path in ("hold_thresholds.possible_add_min", "hold_thresholds.hold_min", "hold_thresholds.no_add_min")},
            "reason": pr.UNREAD_PATH_REASON,
        }
    ]
    assert {item["paths"]["hold_thresholds.hold_min"] for item in pr.unread_sweep_paths()} == {"70"}


_READER_EXCLUDED = ("tests/", "config/", "research_backtest/preregistration.py", "research_backtest/input_census_registry.py")


def _readers(leaf: str) -> list[str]:
    package = REPO / "btc_predictor"
    pattern = re.compile(rf"\.{leaf}\b|[\"']{leaf}[\"']")
    return sorted(
        str(path.relative_to(package))
        for path in package.rglob("*.py")
        if not str(path.relative_to(package)).startswith(_READER_EXCLUDED[:2])
        and str(path.relative_to(package)) not in _READER_EXCLUDED[2:]
        and pattern.search(path.read_text())
    )


def test_every_swept_path_has_a_reader_and_no_unread_path_has_one(sweeps) -> None:
    for sweep in sweeps:
        for path in sweep["parameter_paths"]:
            assert _readers(path.rsplit(".", 1)[-1]), path
    unread = [path for paths in pr.SWEEP_UNREAD_PATHS.values() for path in paths]
    assert unread and all(_readers(path.rsplit(".", 1)[-1]) == [] for path in unread)
    assert _readers("defensive_min") == ["signals/trim.py"] and "signals/exit_rules.py" in _readers("exit_below")


def test_an_unread_path_is_never_swept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(pr.SWEEP_UNREAD_PATHS, "add_threshold", ("add_thresholds.add_min",))
    with pytest.raises(pr.PreregistrationRefused, match="never swept"):
        pr.sweep_grid(CONFIG)


def test_the_grid_is_registered_only_against_the_champion() -> None:
    other = replace(CONFIG, identity=replace(CONFIG.identity, parameter_set_id="btc185-other"))
    with pytest.raises(pr.PreregistrationRefused, match="SWEEP_REFUSED"):
        pr.sweep_grid(other)


def test_a_missing_configuration_path_refuses() -> None:
    with pytest.raises(pr.PreregistrationRefused, match="SWEEP_REFUSED"):
        pr._set_path(pr._configuration_mapping(), "risk.schedule.3.risk_fraction_nav", 0.1)
    with pytest.raises(pr.PreregistrationRefused, match="SWEEP_REFUSED"):
        pr._set_path(pr._configuration_mapping(), "add_thresholds.add_minimum", 80)


# --- the Momentum Persistence ablation ---------------------------------------------------------------


def test_the_ablation_drops_momentum_persistence_and_renormalizes_proportionally() -> None:
    variant = pr.ablation_variant(CONFIG)
    assert variant["variant_weights"] == {
        "flow": "0.3076923",
        "momentum_persistence": "0",
        "positioning": "0.2307692",
        "structure": "0.1538461",
        "trend": "0.3076923",
    }
    assert variant["variant_weight_sum"] == "0.9999999"
    assert variant["label"] == "SENSITIVITY_ONLY_NOT_SELECTION" and variant["evaluation"]["cost_rung"] == "base"
    configured = {key: Decimal(value) for key, value in variant["configured_weights"].items()}
    remaining = sum(value for key, value in configured.items() if key != "momentum_persistence")
    for key, value in variant["variant_weights"].items():
        if key != "momentum_persistence":
            assert abs(Decimal(value) - configured[key] / remaining) < Decimal("0.00000005")


def test_the_variant_weights_are_a_valid_hold_score_that_ignores_momentum_persistence() -> None:
    data = pr._configuration_mapping()
    data["scoring_weights"]["hold_score"] = {key: float(value) for key, value in pr.ablation_variant(CONFIG)["variant_weights"].items()}
    data["identity"]["parameter_set_id"] = "rbt006-ablation-check"
    variant = StrategyConfig.from_mapping(data)
    scores = dict(trend_score=Decimal("70"), flow_score=Decimal("60"), positioning_score=Decimal("50"), structure_score=Decimal("40"))
    low = calculate_hold_score(HoldScoreInput(**scores, momentum_persistence_score=Decimal("0")), strategy_config=variant)
    high = calculate_hold_score(HoldScoreInput(**scores, momentum_persistence_score=Decimal("100")), strategy_config=variant)
    assert low.complete and low.score == high.score
    champion = calculate_hold_score(HoldScoreInput(**scores, momentum_persistence_score=Decimal("100")), strategy_config=CONFIG)
    assert champion.score != high.score


def test_the_ablation_follows_the_configured_weights() -> None:
    weights = {"trend": 0.2, "flow": 0.2, "positioning": 0.2, "structure": 0.2, "momentum_persistence": 0.2}
    other = replace(CONFIG, scoring_weights=replace(CONFIG.scoring_weights, hold_score=weights))
    assert set(pr.ablation_variant(other)["variant_weights"].values()) == {"0.2500000", "0"}


# --- ruling 4: the metric definitions -------------------------------------------------------------


def rulebook_primary_metrics() -> list[str]:
    text = (REPO / "docs/strategy/bitcoin_swing_predictor_rulebook_v1_2.md").read_text()
    section = text.split("# 28. Backtest and Research Rules", 1)[1]
    block = section.split("Primary metrics:", 1)[1].split("Additional data-source robustness metrics:", 1)[0]
    return [line[2:].strip() for line in block.splitlines() if line.startswith("- ")]


def test_every_rulebook_28_primary_metric_is_defined_once() -> None:
    spec = pr.metric_definitions()
    assert [metric["rulebook"] for metric in spec["metrics"]] == rulebook_primary_metrics()
    assert len({metric["metric"] for metric in spec["metrics"]}) == 16
    assert spec["report_version"] == "RESEARCH_BACKTEST_REPORT_V1" and spec["conventions"]["risk_free_rate"] == "zero"
    for metric in spec["metrics"]:
        assert metric["authority"] in ("OWNER_CONVENTION", "NEW_DEFINITION")
        assert metric["definition"] and metric["undefined"]
        assert bool(metric["owner"]) is (metric["authority"] == "OWNER_CONVENTION")


def test_every_owner_convention_names_existing_owner_code() -> None:
    import importlib

    for metric in pr.metric_definitions()["metrics"]:
        if metric["authority"] != "OWNER_CONVENTION":
            continue
        target = metric["owner"].split(" ")[0]
        module_name, _, attribute = target.rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, attribute), metric["owner"]
        source = Path(module.__file__).read_text()
        for policy in re.findall(r"\(([A-Z0-9_]+_V1)\)", metric["owner"]):
            assert policy in source, policy


def _statuses(text: str) -> set[str]:
    return {re.sub(r"\s*\(.*\)$", "", item.strip()) for item in text.split("|")}


def test_every_owner_convention_states_its_owners_exact_undefined_statuses() -> None:
    from btc_predictor.backtest import parameter_surfaces as ps
    from btc_predictor.backtest import setup_performance as sp

    def unavailable(statuses: tuple[str, ...]) -> set[str]:
        return set(statuses) - {"AVAILABLE"}

    owner_statuses = {
        "sharpe": unavailable(ps.SHARPE_STATUSES),
        "calmar": unavailable(ps.CALMAR_STATUSES),
        "max_drawdown": unavailable(ps.DRAWDOWN_STATUSES),
        "profit_factor": unavailable(sp.PROFIT_FACTOR_STATUSES),
    }
    owner_none = {"expectancy": "closed_trade_expectancy", "average_r_per_trade": "mean_r_multiple"}  # the owner's field is None
    metrics = {metric["metric"]: metric for metric in pr.metric_definitions()["metrics"]}
    owned = {name for name, metric in metrics.items() if metric["authority"] == "OWNER_CONVENTION"}
    assert owned == set(owner_statuses) | set(owner_none) | {"number_of_trades"}
    for name, statuses in owner_statuses.items():
        assert _statuses(metrics[name]["undefined"]) == statuses, name
    from btc_predictor.backtest.threshold_sweeps import ThresholdSweepMetrics

    for name, field in owner_none.items():
        assert metrics[name]["undefined"].endswith("(this specification's name for the owner's None)")
        assert field in metrics[name]["owner"] and "None" in str(ThresholdSweepMetrics.__annotations__[field])
    assert metrics["number_of_trades"]["undefined"].startswith("never undefined")


def test_a_new_definition_names_a_shared_condition_as_its_owner_does() -> None:
    from btc_predictor.backtest import parameter_surfaces as ps

    shared = {"NO_EQUITY_CURVE": ps.DRAWDOWN_NO_EQUITY_CURVE, "NON_POSITIVE_NAV": ps.DRAWDOWN_NON_POSITIVE_NAV, "INSUFFICIENT_PERIODS": ps.SHARPE_INSUFFICIENT_PERIODS}
    seen = set()
    for metric in pr.metric_definitions()["metrics"]:
        for status in _statuses(metric["undefined"]):
            for condition, owner_name in shared.items():
                if condition in status:
                    assert status == owner_name, (metric["metric"], status)
                    seen.add(condition)
    assert seen == set(shared)


def _longest_underwater(starting_nav: Decimal, points: list[tuple[Decimal, Decimal]]) -> tuple[Decimal, bool | None]:
    """A literal reading of the frozen longest-drawdown text, hours after started_at."""

    peak, peak_at, began = starting_nav, Decimal("0"), None
    longest: tuple[Decimal, bool | None] = (Decimal("0"), None)
    for at, nav in points:
        if nav >= peak:  # at the peak
            if began is not None and at - began > longest[0]:
                longest = (at - began, True)
            peak, peak_at, began = nav, at, None
        elif began is None:  # strictly below: a drawdown from the latest at-peak instant
            began = peak_at
    if began is not None and points[-1][0] - began > longest[0]:
        longest = (points[-1][0] - began, False)
    return longest


def test_longest_drawdown_is_the_longest_time_underwater_and_its_examples_follow_the_text() -> None:
    metric = next(metric for metric in pr.metric_definitions()["metrics"] if metric["metric"] == "longest_drawdown")
    for rule in ("strictly below the running peak", "starting NAV at the run's started_at", "at or above that peak (recovered)", "(unrecovered)", "0 hours", "the first is reported"):
        assert rule in metric["definition"], rule
    cases = {example["case"]: example for example in metric["examples"]}
    assert {"steady rise", "plateau at the peak", "first point below the starting NAV", "unrecovered at the run's end"} <= set(cases)
    for example in metric["examples"]:
        points = [(Decimal(at), Decimal(nav)) for at, nav in example["points"]]
        assert _longest_underwater(Decimal(example["starting_nav"]), points) == (Decimal(example["hours"]), example["recovered"]), example["case"]
    rise = cases["steady rise"]
    assert len(rise["points"]) >= 2 and all(Decimal(b[1]) > Decimal(a[1]) for a, b in zip([["0", rise["starting_nav"]], *rise["points"]], rise["points"]))


def test_the_metric_definitions_are_a_copy() -> None:
    first = pr.metric_definitions()
    first["metrics"][-2]["examples"].clear()
    assert pr.metric_definitions() != first


def test_the_stop_buffer_alone_uses_the_configured_grid_because_the_uniform_one_is_refused() -> None:
    base = pr._configuration_mapping()
    paths = pr.SWEEP_PARAMETER_PATHS["stop_buffer_atr_multiplier"]
    refused = [pr._candidate_refusal(base, "stop_buffer_atr_multiplier", paths, pr._plain(Decimal("0.3") * factor)) for factor in pr.SWEEP_FACTORS]
    assert [reason is None for reason in refused] == [False, False, True, False, False]
    assert all("sweep_atr_multipliers" in reason for reason in refused if reason is not None)
    assert base["stop_buffers"]["sweep_atr_multipliers"] == [0.25, 0.3, 0.5, 0.75]


def test_the_cross_venue_measures_cover_policy_section_8() -> None:
    spec = pr.metric_definitions()
    assert [measure["measure"] for measure in spec["cross_venue"]] == [
        "trade_set_overlap",
        "matched_trade_divergence",
        "stop_touch_divergence",
        "metric_dispersion",
    ]
    assert all(measure["authority"] == "NEW_DEFINITION" and measure["undefined"] for measure in spec["cross_venue"])
    divergence = spec["cross_venue"][1]["definition"]
    for item in ("entry price", "initial stop price", "exit price", "MFE", "MAE"):
        assert item in divergence
    assert "STRUCTURAL_STOP" in spec["cross_venue"][2]["definition"]
    policy = " ".join((REPO / "docs/policies/research_backtest_policy_v7.md").read_text().split())
    assert "trade-set overlap" in policy and "stop-touch divergence" in policy and "metric dispersion across the three venues" in policy


def test_the_metric_definitions_are_frozen_by_digest() -> None:
    assert pr.metric_definitions_sha256() == pr.sha256_hex(pr.metric_definitions_bytes())
    assert json.loads(pr.metric_definitions_bytes()) == pr.metric_definitions()
    assert pr.metric_definitions_sha256() == "e7ee45c7238958a4cb6abccaa736332f8f2c24ddf83dacc66a4a8629c3f105c6"


# --- the completeness-only pass ------------------------------------------------------------------


@pytest.fixture(scope="module")
def world():
    return fx.Scenario().build()


TRANSITION = days(utc(2024, 3, 8), 9)  # flow completes during this week in the default world


@pytest.fixture(scope="module")
def transition_pass(world):
    return pr.completeness_pass(world, TRANSITION, strategy_config=CONFIG)


@pytest.fixture(scope="module")
def composer_rows(world):
    composer = ec.EntryComposer(world, strategy_config=CONFIG)
    return fx.decide_consecutively(composer, TRANSITION[0], TRANSITION[-1])


def test_the_pass_agrees_with_the_full_composer_on_completeness(transition_pass, composer_rows) -> None:
    assert len(transition_pass.rows) == len(composer_rows) == 9
    assert any(row.complete for row in transition_pass.rows) and not all(row.complete for row in transition_pass.rows)
    for mine, full in zip(transition_pass.rows, composer_rows):
        assert mine.decision_at == full.decision_at
        assert dict(mine.components) == {name: full.components[name] is not None for name in ec.COMPONENT_NAMES}
        assert mine.core_regime == full.owner_reason_codes["regime_score"]["complete"]
        if full.outcome == ec.OUTCOME_STRUCTURALLY_UNEVALUABLE:
            assert {item.component: item.causes for item in mine.incomplete} == {item.component: item.causes for item in full.unevaluable}
        else:  # complete, or a NO_TRADE whose only gap is the structure's missing valid stop
            assert not mine.incomplete or (mine.structure_without_valid_stop and [item.component for item in mine.incomplete] == ["structure"])
        assert set(mine.unaccounted) <= set(full.unaccounted)
        assert mine.guard_refusals == tuple(refusal.guard_id for refusal in full.guard_refusals)


EARLY = days(utc(2021, 6, 8), 3)  # the world's first week: weekly structure and the long windows are still warming up


def test_the_pass_agrees_with_the_full_composer_at_the_first_instants(world) -> None:
    mine = pr.completeness_pass(world, EARLY, strategy_config=CONFIG).rows
    full = fx.decide_consecutively(ec.EntryComposer(world, strategy_config=CONFIG), EARLY[0], EARLY[-1])
    assert any(not dict(row.components)["structure"] for row in mine) and not any(row.complete for row in mine)
    for row, composed in zip(mine, full):
        assert dict(row.components) == {name: composed.components[name] is not None for name in ec.COMPONENT_NAMES}
        assert row.core_regime == composed.owner_reason_codes["regime_score"]["complete"]
        assert {item.component: item.causes for item in row.incomplete} == {item.component: item.causes for item in composed.unevaluable}
        assert set(row.unaccounted) <= set(composed.unaccounted)


def test_the_evaluation_start_is_the_first_instant_with_every_component_and_the_core_regime(transition_pass) -> None:
    start = transition_pass.evaluation_start
    first = next(row for row in transition_pass.rows if row.complete)
    assert start == first.decision_at and start > TRANSITION[0]
    assert all(not row.complete for row in transition_pass.rows if row.decision_at < start)
    assert transition_pass.summary()["evaluation_start"] == start.isoformat()


def test_the_pass_never_composes_conviction_flags_setups_or_an_intent(world) -> None:
    forbidden = (
        "calculate_entry_conviction",
        "classify_entry_action",
        "calculate_stress_flag",
        "calculate_crowding_flag",
        "calculate_euphoria_flag",
        "calculate_capitulation_flag",
        "detect_bull_trend_continuation",
        "detect_bullish_reset",
        "detect_capitulation_reversal",
        "detect_bearish_distribution",
        "calculate_regime_smoothing",
        "calculate_regime_classification",
    )
    with fx.recording(*forbidden, "calculate_regime_score") as calls:
        report = pr.completeness_pass(world, TRANSITION[-2:], strategy_config=CONFIG)
    assert all(calls[name] == [] for name in forbidden)
    assert len(calls["calculate_regime_score"]) == 2 and report.rows[-1].complete


@pytest.mark.parametrize(
    ("scenario", "first", "missing_at"),
    [
        (fx.Scenario(missing_hours=(datetime(2024, 3, 13, 23, tzinfo=UTC),)), utc(2024, 3, 13), [utc(2024, 3, 14)]),
        (fx.Scenario(), utc(2021, 5, 30), [utc(2021, 5, 30), utc(2021, 5, 31), utc(2021, 6, 1)]),  # before the first bar
    ],
    ids=["missing-hour", "pre-history"],
)
def test_a_missing_decision_bar_is_recorded_as_the_composer_records_it(scenario, first, missing_at) -> None:
    inputs = scenario.build()
    report = pr.completeness_pass(inputs, days(first, 3), strategy_config=CONFIG)
    full = fx.decide_consecutively(ec.EntryComposer(inputs, strategy_config=CONFIG), first, first + 2 * DAY)
    assert [row.decision_at for row in report.rows if not row.price_bar] == missing_at
    for mine, composed in zip(report.rows, full):
        assert mine.decision_at == composed.decision_at
        if mine.decision_at not in missing_at:
            continue
        assert composed.outcome == ec.OUTCOME_STRUCTURALLY_UNEVALUABLE and not mine.complete and not mine.core_regime
        assert dict(mine.components) == {name: False for name in ec.COMPONENT_NAMES}
        assert mine.incomplete == composed.unevaluable == (ec.UnevaluableComponent("decision_instant", (ec.CAUSE_DECISION_PRICE_BAR_MISSING,)),)
        assert mine.unaccounted == tuple(composed.unaccounted) == ()
    summary = report.summary()
    assert summary["cause_instant_counts"][f"decision_instant:{ec.CAUSE_DECISION_PRICE_BAR_MISSING}"] == len(missing_at)
    assert not [key for key in summary["cause_instant_counts"] if key.split(":")[0] in ec.COMPONENT_NAMES and ec.CAUSE_DECISION_PRICE_BAR_MISSING in key]


def test_an_unaccounted_missing_bar_cause_blocks_the_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    real = ec.accounted_cause
    monkeypatch.setattr(ec, "accounted_cause", lambda code, feature_id=None: None if code == ec.CAUSE_DECISION_PRICE_BAR_MISSING else real(code, feature_id))
    inputs = fx.Scenario(missing_hours=(datetime(2024, 3, 13, 23, tzinfo=UTC),)).build()
    report = pr.completeness_pass(inputs, [utc(2024, 3, 14)], strategy_config=CONFIG)
    assert report.unaccounted == (("2024-03-14T00:00:00+00:00", f"decision_instant:{ec.CAUSE_DECISION_PRICE_BAR_MISSING}"),)


def test_an_unaccounted_cause_is_recorded_and_blocks_the_freeze(world, monkeypatch: pytest.MonkeyPatch) -> None:
    real = ec.accounted_cause

    def without_history(code: str, feature_id: str | None = None):
        return None if "INSUFFICIENT_HISTORY" in code else real(code, feature_id)

    monkeypatch.setattr(ec, "accounted_cause", without_history)
    report = pr.completeness_pass(world, TRANSITION[:1], strategy_config=CONFIG)
    assert report.unaccounted and all("INSUFFICIENT_HISTORY" in code for _, code in report.unaccounted)
    with pytest.raises(pr.PreregistrationRefused) as refused:
        freeze({report.venue: report}, schedule=TRANSITION[:1])
    assert refused.value.reason_code == "FREEZE_BLOCKED_UNACCOUNTED"


def test_the_ledger_holds_flags_and_codes_but_no_value(world, transition_pass, composer_rows) -> None:
    ledger = transition_pass.ledger_bytes().decode()
    values = set()
    for row in composer_rows:
        values.update(str(value) for value in row.features.values() if isinstance(value, Decimal))
        values.update(str(value) for value in row.components.values() if value is not None)
    values.update(str(bar.close) for bar in world.dataset.price_bars if TRANSITION[0] - DAY <= bar.timestamp <= TRANSITION[-1])
    assert values and not [value for value in values if len(value) > 3 and value in ledger]
    record = json.loads(ledger)
    assert set(record["rows"][0]) == {
        "decision_at", "price_bar", "components", "core_regime", "complete", "incomplete",
        "structure_without_valid_stop", "unaccounted", "guard_refusals", "flow_calendar",
    }


@pytest.mark.parametrize(
    "instants",
    [
        [utc(2024, 3, 9), utc(2024, 3, 8)],
        [utc(2024, 3, 8), utc(2024, 3, 8)],
        [datetime(2024, 3, 8, 1, tzinfo=UTC)],
        [datetime(2024, 3, 8)],
    ],
    ids=["descending", "repeated", "not-midnight", "naive"],
)
def test_the_pass_needs_strictly_increasing_utc_midnights(world, instants) -> None:
    with pytest.raises(pr.PreregistrationRefused, match="COMPLETENESS_REFUSED"):
        pr.completeness_pass(world, instants, strategy_config=CONFIG)


# --- the preregistration artifact -----------------------------------------------------------------


def synthetic_row(at: datetime, complete: bool, *, calendar: tuple[date, date] | None = None, unaccounted: tuple[str, ...] = ()) -> pr.InstantCompleteness:
    return pr.InstantCompleteness(
        decision_at=at,
        price_bar=True,
        components=tuple((name, complete or name != "flow") for name in ec.COMPONENT_NAMES),
        core_regime=complete,
        incomplete=() if complete else (ec.UnevaluableComponent("flow", ("FLOW_Z_ETF_NORM_20D_INSUFFICIENT_HISTORY",)),),
        structure_without_valid_stop=False,
        unaccounted=unaccounted,
        guard_refusals=(),
        flow_calendar=calendar,
    )


SCHEDULE = pr.decision_schedule()
START = utc(2024, 3, 15)


def report_for(venue: str, start: datetime = START, **changes) -> pr.CompletenessReport:
    rows = [synthetic_row(at, at >= start) for at in SCHEDULE]
    for at, row in changes.items():
        rows[SCHEDULE.index(datetime.fromisoformat(at))] = row
    return pr.CompletenessReport(venue=venue, rows=tuple(rows))


INDEX = {
    "evidence_class": "RESEARCH_BACKTEST_NON_CERTIFYING",
    "build_record_sha256": "ef" * 32,
    "private_commit": "12" * 20,
    "manifests": {
        "shared_snapshot": {"manifest_version": "V_SHARED", "sha256": "34" * 32},
        "venue_bitstamp": {"manifest_version": "V_VENUE", "sha256": "56" * 32},
    },
}


def launches():
    return pr.etf_fund_launches(documented_rows(), evidence_sha256=DIGEST)


def freeze(reports, *, schedule=SCHEDULE, **changes):
    arguments = dict(
        code_commit=COMMIT,
        dataset_index=INDEX,
        dataset_index_sha256=DIGEST,
        etf_launches=launches(),
        completeness=reports,
        schedule=schedule,
        strategy_config=CONFIG,
    )
    arguments.update(changes)
    return pr.preregistration_record(**arguments)


@pytest.fixture(scope="module")
def frozen():
    return freeze({venue: report_for(venue) for venue in ("bitfinex", "bitstamp", "coinbase")})


def test_the_preregistration_binds_everything_the_ticket_lists(frozen) -> None:
    assert frozen["code_commit"] == COMMIT
    assert frozen["champion"]["research_strategy_id"] == "swing_v1.2+completion_v1"
    assert frozen["champion"]["completion_spec"]["sha256"] == ec.COMPLETION_SPEC_SHA256
    assert frozen["closure_table"]["definition_sha256"] == "2292388e4a91c1617275ac20ed9d6b45e4b9678525c020e1ccc6fc36a01d1710"
    assert frozen["composers"]["entry"]["version"] == "COMPOSE_CHAMPION_ENTRY_DECISION_V1"
    assert frozen["composers"]["management"]["version"] == "COMPOSE_CHAMPION_POSITION_MANAGEMENT_V1"
    assert frozen["datasets"]["manifests"] == INDEX["manifests"]
    assert frozen["datasets"]["private_commit"] == "12" * 20 and frozen["datasets"]["index_sha256"] == DIGEST
    assert frozen["cost_ladder"] == {
        "headline": "base",
        "rungs": {
            "optimistic": {"fee_bps": "5.0", "slippage_bps": "2.0", "funding_cost_bps_per_day": "0.0"},
            "base": {"fee_bps": "10.0", "slippage_bps": "5.0", "funding_cost_bps_per_day": "0.0"},
            "stress": {"fee_bps": "20.0", "slippage_bps": "25.0", "funding_cost_bps_per_day": "6.0"},
        },
    }
    assert frozen["policy"] == "RESEARCH_BACKTEST_POLICY_V7" and frozen["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING"
    assert frozen["report"]["metric_spec_sha256"] == pr.metric_definitions_sha256()
    assert frozen["ablation"] == pr.ablation_variant(CONFIG)
    assert frozen["threshold_sweeps"]["sweeps"] == pr.sweep_grid(CONFIG) and len(frozen["threshold_sweeps"]["sweeps"]) == 15
    assert frozen["threshold_sweeps"]["unread_paths"] == pr.unread_sweep_paths()
    assert len(frozen["etf_fund_launches"]) == 11
    assert frozen["decision_schedule"] == {
        "rule": "every UTC midnight strictly inside the data window",
        "first": "2020-01-02T00:00:00+00:00",
        "last": "2025-12-31T00:00:00+00:00",
        "instants": 2191,
    }
    for venue in ("bitfinex", "bitstamp", "coinbase"):
        assert frozen["venues"][venue]["evaluation_window"]["start"] == START.isoformat()
        assert frozen["venues"][venue]["walk_forward"] == pr.fold_plan(START, SCHEDULE, strategy_config=CONFIG)


def test_the_preregistration_bytes_are_deterministic_and_carry_no_time(frozen) -> None:
    again = freeze({venue: report_for(venue) for venue in ("bitfinex", "bitstamp", "coinbase")})
    assert pr.preregistration_bytes(frozen) == pr.preregistration_bytes(again)
    assert "created" not in json.dumps(frozen) and "generated_at" not in json.dumps(frozen)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (dict(code_commit="CD" * 20), "FREEZE_REFUSED"),
        (dict(code_commit="cd" * 32), "FREEZE_REFUSED"),
        (dict(dataset_index_sha256="xyz"), "FREEZE_REFUSED"),
        (dict(dataset_index={**INDEX, "evidence_class": "CERTIFYING"}), "FREEZE_REFUSED"),
        (dict(etf_launches=()), "FREEZE_REFUSED"),
        (dict(completeness={}), "FREEZE_REFUSED"),
        (dict(completeness={"bitstamp": report_for("coinbase")}), "FREEZE_REFUSED"),
        (dict(completeness={"bitstamp": pr.CompletenessReport("bitstamp", report_for("bitstamp").rows[:-1])}), "FREEZE_REFUSED"),
        (dict(completeness={"bitstamp": report_for("bitstamp", start=utc(2026, 1, 1))}), "FREEZE_REFUSED"),
        (
            dict(completeness={"bitstamp": report_for("bitstamp", **{"2024-05-01T00:00:00+00:00": synthetic_row(utc(2024, 5, 1), True, unaccounted=("flow_score:X_INPUT_MISSING",))})}),
            "FREEZE_BLOCKED_UNACCOUNTED",
        ),
        (
            dict(completeness={"bitstamp": report_for("bitstamp", **{"2024-05-01T00:00:00+00:00": synthetic_row(utc(2024, 5, 1), True, calendar=(date(2022, 12, 30), date(2024, 4, 29)))})}),
            "FREEZE_BLOCKED_CLOSURE_COVERAGE",
        ),
        (dict(strategy_config=replace(CONFIG, identity=replace(CONFIG.identity, parameter_set_id="other"))), "FREEZE_REFUSED"),
    ],
    ids=[
        "upper-case-commit", "long-commit", "index-digest", "certifying-index", "no-launches", "no-venue",
        "another-venue", "schedule-not-covered", "never-complete", "unaccounted", "closure-coverage", "not-the-champion",
    ],
)
def test_the_freeze_refuses_unless_every_condition_holds(change, code) -> None:
    arguments = {"completeness": {"bitstamp": report_for("bitstamp")}, **change}
    reports = arguments.pop("completeness")
    with pytest.raises(pr.PreregistrationRefused) as refused:
        freeze(reports, **arguments)
    assert refused.value.reason_code == code


def test_a_calendar_inside_the_closure_coverage_freezes() -> None:
    inside = report_for("bitstamp", **{"2024-05-01T00:00:00+00:00": synthetic_row(utc(2024, 5, 1), True, calendar=(date(2023, 12, 12), date(2024, 4, 29)))})
    assert freeze({"bitstamp": inside})["venues"]["bitstamp"]["completeness"]["closure_coverage_violations"] == []


# --- the command line, on the RBT-003 dataset tests' synthetic private store ------------------------

from btc_predictor.research_backtest import dataset_build as build  # noqa: E402
from btc_predictor.tests import test_research_backtest_dataset_build as dt  # noqa: E402

collected = dt.collected
world_store = dt.world  # the dataset tests' private copy of the collected store
VENUES = ("BITFINEX", "BITSTAMP", "COINBASE")
STORE_FUNDS = {"IBIT": (date(2024, 1, 11), "documented"), "GBTC": (date(2024, 1, 11), "documented")}


def store_evidence(store):
    return build.load_build_evidence(store, units=dt.units_of)


@pytest.fixture
def frozen_store(world_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dt.built(world_store)
    store = dt.git_store(world_store)
    public = tmp_path / "public"
    (public / build.INDEX_PATH.parent).mkdir(parents=True)
    monkeypatch.setattr(build, "PUBLIC_REPOSITORY", public)
    stored = build.load_dataset(store)
    (public / build.INDEX_PATH).write_bytes(build.dataset_index_bytes(stored, private_commit=build.private_commit(store, stored)))
    monkeypatch.setattr(pr, "DOCUMENTED_FIRST_TRADING_DATES", STORE_FUNDS)
    return world_store, public


class FakePass:
    """Complete from START, recording what each venue's pass was handed."""

    def __init__(self, **unaccounted_at: str) -> None:
        self.calls: list[tuple[ec.EntryComposerInputs, tuple[datetime, ...]]] = []
        self.unaccounted_at = unaccounted_at

    def __call__(self, inputs, schedule, *, strategy_config):
        self.calls.append((inputs, tuple(schedule)))
        venue = inputs.dataset.venue.venue_id
        rows = [synthetic_row(at, at >= START, unaccounted=(self.unaccounted_at[venue],) if venue in self.unaccounted_at and at == START else ()) for at in schedule]
        return pr.CompletenessReport(venue=venue, rows=tuple(rows))


def run_freeze(world, *, run_pass, commit=lambda: COMMIT):
    lines: list[str] = []
    status = pr.main(["freeze", "--store", str(world.root)], commit=commit, evidence=store_evidence, run_pass=run_pass, out=lines.append)
    return status, lines


def written(public: Path) -> dict[str, bytes]:
    directory = public / pr.ARTIFACT_DIRECTORY
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir()) if path.name.startswith("rbt006_")}


def test_the_command_line_freezes_the_stored_dataset(frozen_store) -> None:
    world, public = frozen_store
    fake = FakePass()
    status, lines = run_freeze(world, run_pass=fake)
    assert status == 0, lines
    files = written(public)
    assert sorted(files) == sorted(
        [pr.PREREGISTRATION_FILE, pr.PREREGISTRATION_DIGEST_FILE, *(pr.completeness_file(venue) for venue in VENUES)]
    )
    record = json.loads(files[pr.PREREGISTRATION_FILE])
    assert files[pr.PREREGISTRATION_FILE] == pr.preregistration_bytes(record)
    assert files[pr.PREREGISTRATION_DIGEST_FILE] == f"{pr.sha256_hex(files[pr.PREREGISTRATION_FILE])}  {pr.PREREGISTRATION_FILE}\n".encode()
    index_bytes = (public / build.INDEX_PATH).read_bytes()
    index = json.loads(index_bytes)
    assert record["datasets"]["index_sha256"] == pr.sha256_hex(index_bytes)
    assert record["datasets"]["private_commit"] == index["private_commit"] == dt.git(world.root, "rev-parse", "HEAD")
    assert record["datasets"]["manifests"] == index["manifests"] and len(index["manifests"]) == 5
    assert record["code_commit"] == COMMIT and sorted(record["venues"]) == list(VENUES)
    stored = build.load_dataset(dt.store_of(world))
    assert [launch["fund"] for launch in record["etf_fund_launches"]] == ["GBTC", "IBIT"]
    assert all(stored.record["inputs"]["etf_flows"]["sha256"] in launch["source"] for launch in record["etf_fund_launches"])
    for venue in VENUES:
        assert files[pr.completeness_file(venue)] == fake_report_bytes(fake, venue)
    assert lines[-1].startswith(f"preregistration written: {pr.ARTIFACT_DIRECTORY / pr.PREREGISTRATION_FILE} sha256 ")


def fake_report_bytes(fake: FakePass, venue: str) -> bytes:
    inputs, schedule = next(call for call in fake.calls if call[0].dataset.venue.venue_id == venue)
    return fake(inputs, schedule, strategy_config=CONFIG).ledger_bytes()


def test_each_venue_pass_gets_its_dataset_the_extended_snapshot_and_the_launches(frozen_store) -> None:
    world, _ = frozen_store
    fake = FakePass()
    assert run_freeze(world, run_pass=fake)[0] == 0
    stored = build.load_dataset(dt.store_of(world))
    datasets = build.build_replay_datasets(build.frozen_rows(stored), store_evidence(dt.store_of(world)))
    assert sorted(inputs.dataset.venue.venue_id for inputs, _ in fake.calls) == list(VENUES)
    for inputs, schedule in fake.calls:
        assert schedule == pr.decision_schedule()
        assert [launch.fund for launch in inputs.etf_fund_launches] == ["GBTC", "IBIT"]
        assert inputs.futures_basis == datasets.extended.futures_basis and inputs.market_caps == datasets.extended.market_caps
        assert inputs.dataset.manifest_sha256 in {dataset.manifest_sha256 for dataset in datasets.venues}


def test_an_index_that_is_not_the_stored_datasets_refuses_and_writes_nothing(frozen_store) -> None:
    world, public = frozen_store
    path = public / build.INDEX_PATH
    index = json.loads(path.read_bytes())
    index["private_commit"] = "0" * 40  # a well-formed index of another commit
    path.write_bytes(build.v1.canonical_json_bytes(index))
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, "REFUSED FREEZE_REFUSED: FREEZE_REFUSED: the public index is not the stored dataset's index")
    assert written(public) == {}


def test_a_dataset_not_committed_as_stored_refuses_and_writes_nothing(frozen_store) -> None:
    world, public = frozen_store
    (build.dataset_directory(dt.store_of(world)) / "inputs" / "stray.json").write_bytes(b"{}")
    status, lines = run_freeze(world, run_pass=FakePass())
    assert status == 1 and lines[-1].startswith("REFUSED PRIVATE_COMMIT_REFUSED") and written(public) == {}


def test_an_unaccounted_cause_in_any_venue_blocks_the_freeze(frozen_store) -> None:
    world, public = frozen_store
    status, lines = run_freeze(world, run_pass=FakePass(COINBASE="flow_score:SOMETHING_INPUT_MISSING"))
    assert status == 1 and lines[-1].startswith("REFUSED FREEZE_BLOCKED_UNACCOUNTED") and written(public) == {}
    assert "COINBASE: evaluation start" in "\n".join(lines) and "unaccounted 1" in "\n".join(lines)


def test_code_that_is_not_a_clean_commit_refuses(frozen_store) -> None:
    world, public = frozen_store

    def dirty() -> str:
        raise build.DatasetBuildRefused("CODE_COMMIT_REFUSED", "the public repository has uncommitted changes")

    status, lines = run_freeze(world, run_pass=FakePass(), commit=dirty)
    assert (status, lines) == (1, ["REFUSED CODE_COMMIT_REFUSED: CODE_COMMIT_REFUSED: the public repository has uncommitted changes"])
    assert written(public) == {}


def refused(line: str) -> str:
    return line.split(": ", 1)[0] + ": " + run_module().masked(line.split(": ", 1)[1])


def every_file(public: Path) -> dict[str, bytes]:
    return {str(path.relative_to(public)): path.read_bytes() for path in sorted(public.rglob("*")) if path.is_file() and not path.is_symlink()}


@pytest.mark.parametrize("venue", VENUES)
def test_a_link_at_any_destination_refuses_before_anything_is_written(frozen_store, tmp_path: Path, venue: str) -> None:
    world, public = frozen_store
    before = every_file(public)
    target = tmp_path / "elsewhere.json"
    (public / pr.ARTIFACT_DIRECTORY / pr.completeness_file(venue)).symlink_to(target)
    fake = FakePass()
    status, lines = run_freeze(world, run_pass=fake)
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {pr.completeness_file(venue)} is a symbolic link"))
    link = public / pr.ARTIFACT_DIRECTORY / pr.completeness_file(venue)
    assert len(fake.calls) == 3 and every_file(public) == before and link.is_symlink() and not target.exists()


@pytest.mark.parametrize("name", [pr.PREREGISTRATION_FILE, pr.PREREGISTRATION_DIGEST_FILE])
def test_an_existing_freeze_refuses_before_the_pass_and_is_left_as_it_was(frozen_store, name: str) -> None:
    world, public = frozen_store
    (public / pr.ARTIFACT_DIRECTORY / name).write_bytes(b"earlier")
    before = every_file(public)
    fake = FakePass()
    status, lines = run_freeze(world, run_pass=fake)
    assert (status, lines) == (1, [refused(f"REFUSED FREEZE_EXISTS: FREEZE_EXISTS: {name} exists; a freeze is never overwritten")])
    assert fake.calls == [] and every_file(public) == before


def test_an_existing_ledger_refuses_with_nothing_written(frozen_store) -> None:
    world, public = frozen_store
    (public / pr.ARTIFACT_DIRECTORY / pr.completeness_file("COINBASE")).write_bytes(b"earlier")
    before = every_file(public)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_EXISTS: FREEZE_EXISTS: {pr.completeness_file('COINBASE')} exists; a freeze is never overwritten"))
    assert every_file(public) == before


def test_a_linked_partial_or_directory_refuses(frozen_store, tmp_path: Path) -> None:
    world, public = frozen_store
    partial = public / pr.ARTIFACT_DIRECTORY / f"{pr.PREREGISTRATION_FILE}.partial"
    partial.symlink_to(tmp_path / "elsewhere")
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {partial.name} is a symbolic link"))
    partial.unlink()
    directory = public / pr.ARTIFACT_DIRECTORY
    moved = tmp_path / "real_directory"
    directory.rename(moved)
    directory.symlink_to(moved, target_is_directory=True)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {pr.ARTIFACT_DIRECTORY} is not a real directory"))
    assert sorted(path.name for path in moved.iterdir()) == [build.INDEX_PATH.name]


def test_the_preregistration_is_written_last(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, _ = frozen_store
    order: list[str] = []
    real = pr._place

    def recording(directory: int, name: str, data: bytes) -> int:
        order.append(name)
        return real(directory, name, data)

    monkeypatch.setattr(pr, "_place", recording)
    assert run_freeze(world, run_pass=FakePass())[0] == 0
    assert order == [*(pr.completeness_file(venue) for venue in VENUES), pr.PREREGISTRATION_DIGEST_FILE, pr.PREREGISTRATION_FILE]


# --- review N1: a change after the destination checks ----------------------------------------------

FIRST, SECOND, THIRD = (pr.completeness_file(venue) for venue in VENUES)


def interleave(monkeypatch: pytest.MonkeyPatch, at: str, change, *, before: bool = False) -> list[str]:
    """Another writer's ``change``, once, just before or just after this run places ``at``; returns what was placed."""

    real, placed = pr._place, []

    def interleaved(directory: int, name: str, data: bytes) -> int:
        if before and name == at:
            change()
        identity = real(directory, name, data)
        placed.append(name)
        if not before and name == at:
            change()
        return identity

    monkeypatch.setattr(pr, "_place", interleaved)
    return placed


def names_in(public: Path) -> list[str]:
    return sorted(path.name for path in (public / pr.ARTIFACT_DIRECTORY).iterdir())


def test_a_link_made_after_the_checks_refuses_and_leaves_nothing_of_this_run(frozen_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    before = every_file(public)
    target = tmp_path / "elsewhere.json"
    link = public / pr.ARTIFACT_DIRECTORY / THIRD
    placed = interleave(monkeypatch, FIRST, lambda: link.symlink_to(target))
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {THIRD} is a symbolic link"))
    assert placed == [FIRST, SECOND]  # two files were placed, and both removed
    assert every_file(public) == before and names_in(public) == sorted([build.INDEX_PATH.name, THIRD])
    assert link.is_symlink() and not target.exists()


def other_freeze(world) -> dict[str, bytes]:
    record, files = pr.freeze_from_store(dt.store_of(world), code_commit="ef" * 20, evidence=store_evidence, run_pass=FakePass())
    assert record["code_commit"] == "ef" * 20 and files[pr.PREREGISTRATION_FILE] != b""
    return dict(files)


def test_a_freeze_published_after_the_checks_is_never_overwritten(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    other = other_freeze(world)
    directory = public / pr.ARTIFACT_DIRECTORY

    def publish_other() -> None:
        for name, content in other.items():
            (directory / name).write_bytes(content)

    placed = interleave(monkeypatch, FIRST, publish_other, before=True)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_EXISTS: FREEZE_EXISTS: {FIRST} exists; a freeze is never overwritten"))
    assert placed == [] and written(public) == other


def test_a_refusal_after_a_placement_removes_only_this_runs_own_files(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    other = other_freeze(world)
    directory = public / pr.ARTIFACT_DIRECTORY

    def publish_the_rest() -> None:  # another writer that never overwrites places everything still free
        for name, content in other.items():
            if not (directory / name).exists():
                (directory / name).write_bytes(content)

    placed = interleave(monkeypatch, FIRST, publish_the_rest)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_EXISTS: FREEZE_EXISTS: {SECOND} exists; a freeze is never overwritten"))
    assert placed == [FIRST] and written(public) == {name: content for name, content in other.items() if name != FIRST}


@pytest.mark.parametrize("rewrite", ["other bytes in place", "same bytes, another file"])
def test_a_placed_file_another_writer_rewrote_is_left_to_it(frozen_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rewrite: str) -> None:
    world, public = frozen_store
    directory = public / pr.ARTIFACT_DIRECTORY
    first = directory / FIRST
    expected: list[bytes] = []

    def rewrite_then_link() -> None:
        if rewrite == "other bytes in place":
            first.write_bytes(b"another writer's ledger")  # the same file, other bytes
        else:
            content = first.read_bytes()
            first.unlink()
            first.write_bytes(content)  # the same bytes, another file
        expected.append(first.read_bytes())
        (directory / THIRD).symlink_to(tmp_path / "elsewhere.json")

    interleave(monkeypatch, FIRST, rewrite_then_link)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {THIRD} is a symbolic link"))
    assert first.read_bytes() == expected[0] and names_in(public) == sorted([build.INDEX_PATH.name, FIRST, THIRD])


def test_each_placed_file_is_held_open_until_the_publication_ends(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    """An inode number is reused at once, so a placed file is held open until the end: its identity stays its own."""

    world, public = frozen_store
    directory = public / pr.ARTIFACT_DIRECTORY
    real, held, checks = pr._place, [], []

    def same(status: os.stat_result, other: os.stat_result) -> bool:
        return (status.st_dev, status.st_ino) == (other.st_dev, other.st_ino)

    def holding(dir_fd: int, name: str, data: bytes) -> int:
        checks.extend(same(os.fstat(descriptor), os.stat(directory / earlier)) for earlier, descriptor in held)
        descriptor = real(dir_fd, name, data)
        held.append((name, descriptor))
        return descriptor

    monkeypatch.setattr(pr, "_place", holding)
    open_before = sorted(os.listdir("/proc/self/fd"))
    assert run_freeze(world, run_pass=FakePass())[0] == 0
    assert len(checks) == 1 + 2 + 3 + 4 and all(checks)
    assert sorted(os.listdir("/proc/self/fd")) == open_before  # and every descriptor is closed at the end


def test_a_partial_file_made_after_the_checks_refuses_and_is_left_to_its_writer(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    partial = public / pr.ARTIFACT_DIRECTORY / f"{SECOND}.partial"
    interleave(monkeypatch, FIRST, lambda: partial.write_bytes(b"theirs"))
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {partial.name} exists; a partial file is never reused"))
    assert names_in(public) == sorted([build.INDEX_PATH.name, partial.name]) and partial.read_bytes() == b"theirs"


def test_a_left_partial_file_refuses_before_the_pass_and_is_left_as_it_was(frozen_store) -> None:
    world, public = frozen_store
    partial = public / pr.ARTIFACT_DIRECTORY / f"{pr.PREREGISTRATION_FILE}.partial"
    partial.write_bytes(b"left")
    before = every_file(public)
    fake = FakePass()
    status, lines = run_freeze(world, run_pass=fake)
    assert (status, lines) == (1, [refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {partial.name} exists; a partial file is never reused")])
    assert fake.calls == [] and every_file(public) == before


def test_an_error_while_publishing_removes_what_this_run_placed(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    before = every_file(public)
    real = pr._place

    def failing(directory: int, name: str, data: bytes) -> int:
        if name == pr.PREREGISTRATION_FILE:
            raise OSError("no space left")
        return real(directory, name, data)

    monkeypatch.setattr(pr, "_place", failing)
    with pytest.raises(OSError, match="no space left"):
        run_freeze(world, run_pass=FakePass())
    assert every_file(public) == before and names_in(public) == [build.INDEX_PATH.name]


def test_a_failed_link_leaves_no_partial_file(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    before = every_file(public)

    def no_link(*args, **kwargs) -> None:
        raise OSError("link refused")

    monkeypatch.setattr(pr.os, "link", no_link)
    with pytest.raises(OSError, match="link refused"):
        run_freeze(world, run_pass=FakePass())
    assert every_file(public) == before and names_in(public) == [build.INDEX_PATH.name]


def test_a_directory_swapped_for_a_link_after_the_checks_is_never_followed(frozen_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    directory = public / pr.ARTIFACT_DIRECTORY
    moved, elsewhere = tmp_path / "moved", tmp_path / "elsewhere"
    elsewhere.mkdir()

    def swap() -> None:
        directory.rename(moved)
        directory.symlink_to(elsewhere, target_is_directory=True)

    # before publication opens the directory: refused, nothing written anywhere
    opened = pr._open_artifact_directory
    monkeypatch.setattr(pr, "_open_artifact_directory", lambda repository: (swap(), opened(repository))[1])
    status, lines = run_freeze(world, run_pass=FakePass())
    assert (status, lines[-1]) == (1, refused(f"REFUSED FREEZE_DESTINATION_REFUSED: FREEZE_DESTINATION_REFUSED: {pr.ARTIFACT_DIRECTORY} is not a real directory"))
    assert list(elsewhere.iterdir()) == [] and sorted(path.name for path in moved.iterdir()) == [build.INDEX_PATH.name]
    # while it publishes: every file goes on into the directory it opened, never through the link
    directory.unlink()
    moved.rename(directory)
    monkeypatch.setattr(pr, "_open_artifact_directory", opened)
    interleave(monkeypatch, FIRST, swap)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert status == 0, lines
    assert list(elsewhere.iterdir()) == []
    assert sorted(path.name for path in moved.iterdir()) == sorted([build.INDEX_PATH.name, *(pr.completeness_file(venue) for venue in VENUES), pr.PREREGISTRATION_DIGEST_FILE, pr.PREREGISTRATION_FILE])


def run_module():
    from btc_predictor.research_backtest import backfill_run

    return backfill_run


def test_the_real_pass_runs_on_the_stored_dataset(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    monkeypatch.setattr(pr, "decision_schedule", lambda window=DATA_WINDOW: tuple(days(utc(2020, 2, 2), 3)))
    status, lines = run_freeze(world, run_pass=pr.completeness_pass)
    assert status == 1 and lines[-1].startswith("REFUSED FREEZE_REFUSED") and "no decision instant is complete" in lines[-1]
    assert sorted(line for line in lines if "unaccounted" in line) == [f"{venue}: evaluation start None, unaccounted 0, closure coverage violations 0" for venue in VENUES]
    assert written(public) == {}


def test_inputs_that_do_not_rebuild_the_stored_manifests_refuse(frozen_store, monkeypatch: pytest.MonkeyPatch) -> None:
    world, public = frozen_store
    real = build.build_replay_datasets

    def drifted(rows, evidence):
        datasets = real(rows, evidence)
        venue = datasets.venues[0]
        return replace(datasets, venues=(replace(venue, manifest_bytes=venue.manifest_bytes + b" "), *datasets.venues[1:]))

    monkeypatch.setattr(build, "build_replay_datasets", drifted)
    status, lines = run_freeze(world, run_pass=FakePass())
    assert status == 1 and lines[-1] == "REFUSED FREEZE_REFUSED: FREEZE_REFUSED: the frozen inputs do not rebuild the stored manifests"
    assert written(public) == {}
