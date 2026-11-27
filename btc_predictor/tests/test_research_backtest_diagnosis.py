"""RBT-007A ``DIAGNOSE_STRUCTURAL_INCOMPLETENESS_V1``: the replay, the traces, the report and the command.

Every test is synthetic: the RBT-004 composer worlds, the RBT-003 dataset tests'
collected store and throwaway directories. No real-data value is read or
computed, and nothing touches the private store, the holdout or BTC-019.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from btc_predictor.research_backtest import diagnosis as dg
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest import preregistration as prereg
from btc_predictor.research_backtest import runner
from btc_predictor.research_backtest import runner_report as rr
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes
from btc_predictor.tests import rbt004_composer_fixtures as fx

REPOSITORY = Path(__file__).resolve().parents[2]
VENUE = "BITSTAMP"
GAP_FUND, GAP_DAY = "ARKB", date(2024, 4, 9)
INSTANTS = tuple(fx.utc(2024, 4, 12) + fx.DAY * index for index in range(3))
LIQUIDATION_DAY = date(2024, 4, 11)
MISSING_HOUR = fx.utc(2024, 4, 9, 13)
EVIDENCE = dg.SourceEvidence(
    etf_days={GAP_DAY: {"IBIT": True, "FBTC": True, GAP_FUND: False}},
    liquidation_hours={
        datetime(2024, 4, 11, 5, tzinfo=UTC): "NO_EXECUTION_IN_HOUR",
        datetime(2024, 4, 11, 6, tzinfo=UTC): "WITHHELD_RULING_16",
    },
    liquidation_evidence_days=(date(2021, 6, 1), date(2024, 4, 30)),
    liquidation_history={},
    liquidation_window_days=730,
    liquidation_minimum=30,
    still_missing_hours={VENUE: frozenset({MISSING_HOUR})},
)


def ledger_rows(world, instants):
    composer = ec.EntryComposer(world, strategy_config=fx.CONFIG)
    for instant in instants:
        composer.record(composer.decide(instant))
    return json.loads(composer.ledger_bytes())["rows"]


def diagnose(world, instants=INSTANTS, evidence=EVIDENCE, rows=None):
    rows = ledger_rows(world, instants) if rows is None else rows
    return dg.diagnose_venue(world, rows, instants, evidence, strategy_config=fx.CONFIG)


def without_fund_day(world, fund=GAP_FUND, day=GAP_DAY):
    shared = world.dataset.shared_snapshot
    flows = tuple(flow for flow in shared.etf_flows if (flow.fund, flow.observation_date) != (fund, day))
    return replace(world, dataset=replace(world.dataset, shared_snapshot=replace(shared, etf_flows=flows)))


def roots(decision, component):
    return decision["incomplete"][component]["roots"]


# --- fixtures ----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def base():
    return fx.Scenario().build()


@pytest.fixture(scope="module")
def flow_world(base):
    return without_fund_day(base)


@pytest.fixture(scope="module")
def flow_rows(flow_world):
    return ledger_rows(flow_world, INSTANTS)


@pytest.fixture(scope="module")
def flow_result(flow_world, flow_rows):
    return diagnose(flow_world, rows=flow_rows)


# --- the replay agrees with the ledger, and the traces ----------------------------------------------


def test_a_missing_fund_day_is_traced_through_the_flow_owners_windows(flow_result):
    assert [decision["outcome"] for decision in flow_result["decisions"]] == [dg.LEDGER_OUTCOME_UNEVALUABLE] * 3
    for decision in flow_result["decisions"]:
        assert decision["disagreements"] == []
        (root,) = roots(decision, "flow")
        assert root["code"] == "ETF_FLOW_INPUT_MISSING" and root["rule"] == "ETF_WINDOW_NEEDS_EVERY_FUND_EVERY_DAY"
        assert {(item["fund"], item["date"]) for item in root["observations"]} == {(GAP_FUND, GAP_DAY.isoformat())}
        assert {item["window"] for item in root["observations"]} == {"5D", "20D"}
        assert {(item["origin"], item["class"]) for item in root["observations"]} == {("FUND_LISTED_WITHOUT_VALUE", dg.SOURCE_ABSENT)}
        flow = decision["incomplete"]["flow"]
        assert flow["untraced"] == [] and "FLOW_Z_ETF_NORM_20D_INPUT_MISSING" in flow["derived"]


def test_a_row_stored_but_not_yet_available_is_a_build_rule(base):
    shared = base.dataset.shared_snapshot
    late = fx.utc(2024, 5, 1)
    flows = tuple(
        replace(flow, available_at=late, ingested_at=late) if (flow.fund, flow.observation_date) == (GAP_FUND, GAP_DAY) else flow
        for flow in shared.etf_flows
    )
    world = replace(base, dataset=replace(base.dataset, shared_snapshot=replace(shared, etf_flows=flows)))
    (decision,) = diagnose(world, INSTANTS[:1])["decisions"]
    assert decision["disagreements"] == []
    observations = roots(decision, "flow")[0]["observations"]
    assert {(item["fund"], item["origin"], item["class"]) for item in observations} == {(GAP_FUND, "ROW_NOT_YET_AVAILABLE", dg.BUILD_RULE)}


def test_the_etf_origin_reads_the_frozen_flow_history():
    evidence = replace(EVIDENCE, etf_days={GAP_DAY: {"IBIT": True, GAP_FUND: False, "FBTC": True}, date(2024, 4, 10): {"IBIT": True}})
    assert evidence.etf_origin(GAP_FUND, GAP_DAY) == "FUND_LISTED_WITHOUT_VALUE"
    assert evidence.etf_origin("IBIT", GAP_DAY) == "LISTED_WITH_VALUE_NOT_IN_DATASET"
    assert evidence.etf_origin(GAP_FUND, date(2024, 4, 10)) == "FUND_NOT_LISTED"
    assert evidence.etf_origin(GAP_FUND, date(2024, 4, 11)) == "FLOW_HISTORY_DAY_ABSENT"
    assert {dg.ORIGIN_CLASS[origin] for origin in ("FUND_LISTED_WITHOUT_VALUE", "FUND_NOT_LISTED", "FLOW_HISTORY_DAY_ABSENT")} == {dg.SOURCE_ABSENT}
    assert dg.ORIGIN_CLASS["LISTED_WITH_VALUE_NOT_IN_DATASET"] == dg.BUILD_RULE


def test_an_unavailable_liquidation_day_is_traced_to_its_hours(base):
    observations = [
        ec.LiquidationPercentileObservation(item.observation_date, None, item.available_at, ("LIQUIDATION_FEED_UNAVAILABLE",))
        if item.observation_date == LIQUIDATION_DAY
        else item
        for item in base.liquidation_percentiles
    ]
    world = replace(base, liquidation_percentiles=tuple(observations))
    decision = diagnose(world, INSTANTS[:1])["decisions"][0]
    assert decision["disagreements"] == []
    (root,) = roots(decision, "volatility")
    assert root["code"] == ec.CAUSE_LIQUIDATION_PERCENTILE_MISSING and root["rule"] == "LIQUIDATION_DAY_NEEDS_24_OBSERVED_HOURS"
    assert [(item["hour"], item["origin"], item["class"]) for item in root["observations"]] == [
        ("2024-04-11T05:00:00+00:00", "NO_EXECUTION_IN_HOUR", dg.SOURCE_ABSENT),
        ("2024-04-11T06:00:00+00:00", "WITHHELD_RULING_16", dg.BUILD_RULE),
    ]
    assert sorted(decision["incomplete"]["volatility"]["derived"]) == ["ORDERLINESS_INPUT_MISSING", "VOLATILITY_SCORE_INPUT_MISSING"]


def test_a_short_liquidation_history_is_warm_up_only_near_the_evidence_start(base):
    observations = [
        ec.LiquidationPercentileObservation(item.observation_date, None, item.available_at, ("LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY",))
        if item.observation_date == LIQUIDATION_DAY
        else item
        for item in base.liquidation_percentiles
    ]
    composer = ec.EntryComposer(replace(base, liquidation_percentiles=tuple(observations)), strategy_config=fx.CONFIG)
    run = dg._DiagnosisRun(composer, INSTANTS[0], position_open=False)
    late_start = replace(EVIDENCE, liquidation_evidence_days=(date(2023, 6, 1), date(2024, 4, 30)), liquidation_history={LIQUIDATION_DAY: 12})
    (item,) = dg._trace_liquidation(run, late_start)
    assert (item["origin"], item["class"], item["complete_days"], item["minimum"]) == ("INSUFFICIENT_COMPLETE_DAYS_WARM_UP", dg.WARM_UP, 12, 30)
    (item,) = dg._trace_liquidation(run, EVIDENCE)
    assert (item["origin"], item["class"]) == ("INSUFFICIENT_COMPLETE_DAYS", dg.OTHER)
    (item,) = dg._trace_liquidation(run, replace(EVIDENCE, liquidation_evidence_days=None))
    assert item["origin"] == "DAY_NOT_IN_EVIDENCE"


def test_a_missing_price_hour_is_traced_through_its_absent_session():
    world = fx.Scenario(missing_hours=(MISSING_HOUR,)).build()
    instants = tuple(fx.utc(2024, 4, 11) + fx.DAY * index for index in range(2))
    rows = ledger_rows(world, instants)
    for evidence, origin in ((EVIDENCE, "STILL_MISSING_AFTER_REREQUEST"), (replace(EVIDENCE, still_missing_hours={}), "HOUR_MISSING_NOT_REREQUESTED")):
        first, second = diagnose(world, instants, evidence, rows)["decisions"]
        assert first["disagreements"] == second["disagreements"] == []
        hour = [(MISSING_HOUR.isoformat(), origin, dg.SOURCE_ABSENT)]
        (volatility,) = roots(first, "volatility")
        assert volatility["code"] == "RANGE_PERCENTILE_INPUT_MISSING" and volatility["rule"] == "DAILY_SESSION_NEEDS_EVERY_HOUR"
        assert [(item["hour"], item["origin"], item["class"]) for item in volatility["observations"]] == hour
        for decision in (first, second):
            (structure,) = roots(decision, "structure")
            assert structure["code"] == "VOLATILITY_BUFFER_INPUT_MISSING"
            assert [(item["hour"], item["origin"], item["class"]) for item in structure["observations"]] == hour
        assert "volatility" not in second["incomplete"]  # the range percentile needs only the last bar's prior session


def test_a_zero_open_interest_prior_is_traced():
    start = fx.utc(2023, 6, 1)

    def open_interest(index):
        day = start + timedelta(days=index)
        return 0 if fx.utc(2024, 4, 4) <= day <= fx.utc(2024, 4, 5) else 5_000_000_000 + 1_000_000 * ((index % 97) - 48)

    world = fx.Scenario(oi_at=open_interest).build()
    rows = ledger_rows(world, INSTANTS[:1])
    (decision,) = diagnose(world, INSTANTS[:1], rows=rows)["decisions"]
    assert decision["disagreements"] == []
    tampered = json.loads(json.dumps(rows))
    tampered[0]["unevaluable"][0]["causes"] = tampered[0]["unevaluable"][0]["causes"][:1]
    (other,) = diagnose(world, INSTANTS[:1], rows=tampered)["decisions"]
    assert len(other["disagreements"]) == 1 and other["disagreements"][0].startswith("replayed positioning")
    (root,) = roots(decision, "positioning")
    assert root["rule"] == "OI_GROWTH_NEEDS_NONZERO_PRIOR"
    assert root["observations"] == [
        {
            "observation_time": "2024-04-12T00:00:00+00:00",
            "prior_time": "2024-04-05T00:00:00+00:00",
            "rows_at_prior": 1,
            "origin": "SOURCE_ZERO_TOTAL",
            "class": dg.OTHER,
        }
    ]
    assert decision["incomplete"]["positioning"]["derived"] == ["POSITIONING_SCORE_INPUT_MISSING"]


def test_a_missing_decision_bar_is_traced_to_its_hour():
    hour = fx.utc(2024, 4, 11, 23)
    world = fx.Scenario(missing_hours=(hour,)).build()
    (decision,) = diagnose(world, INSTANTS[:1], replace(EVIDENCE, still_missing_hours={VENUE: frozenset({hour})}))["decisions"]
    assert decision["disagreements"] == [] and list(decision["incomplete"]) == ["decision_instant"]
    (root,) = roots(decision, "decision_instant")
    assert root["code"] == ec.CAUSE_DECISION_PRICE_BAR_MISSING
    assert [(item["hour"], item["origin"]) for item in root["observations"]] == [(hour.isoformat(), "STILL_MISSING_AFTER_REREQUEST")]


def test_a_stop_refused_by_geometry_is_traced_to_its_rule(base):
    composer = ec.EntryComposer(base, strategy_config=fx.CONFIG)
    run = dg._DiagnosisRun(composer, INSTANTS[0], position_open=False)
    codes = ["STRUCTURAL_INVALIDATION_WRONG_SIDE", "INITIAL_STOP_INVALIDATION_INCOMPLETE", "STRUCTURAL_INVALIDATION_NO_CANDIDATE"]
    traced = dg._trace_component("structure", codes, run, EVIDENCE, 15)
    assert traced["untraced"] == [] and traced["derived"] == ["INITIAL_STOP_INVALIDATION_INCOMPLETE"]
    assert traced["roots"] == [
        {
            "code": "STRUCTURAL_INVALIDATION_NO_CANDIDATE+STRUCTURAL_INVALIDATION_WRONG_SIDE",
            "rule": "STRUCTURAL_STOP_GEOMETRY",
            "observations": [{"codes": ["STRUCTURAL_INVALIDATION_NO_CANDIDATE", "STRUCTURAL_INVALIDATION_WRONG_SIDE"], "origin": "MARKET_GEOMETRY", "class": dg.OTHER}],
        }
    ]


def test_a_complete_decision_is_attributed_per_setup_from_the_ledger(base):
    rows = ledger_rows(base, INSTANTS[:1])
    (decision,) = diagnose(base, INSTANTS[:1], rows=rows)["decisions"]
    assert decision["incomplete"] == {} and decision["disagreements"] == []
    assert decision["reasons"] == [dg.REASON_NO_SETUP]
    expected = {
        label.split(":", 1)[1]: list(result["reason_codes"]) for label, result in rows[0]["owner_reason_codes"].items() if label.startswith("setup:")
    }
    assert {setup: found["codes"] for setup, found in decision["setups"].items()} == expected
    assert all(found["first"] == (found["codes"][0] if found["codes"] else None) for found in decision["setups"].values())


def test_setups_keep_the_owners_code_order():
    row = {"owner_reason_codes": {"setup:B": {"complete": False, "reason_codes": ["Z_FIRST", "A_SECOND"]}, "setup:A": {"complete": True, "reason_codes": []}, "flow_score": {}}}
    assert dg._setups(row) == {
        "A": {"complete": True, "codes": [], "first": None},
        "B": {"complete": False, "codes": ["Z_FIRST", "A_SECOND"], "first": "Z_FIRST"},
    }


# --- disagreements, untraced causes and refusals -------------------------------------------------------


def test_a_decision_that_disagrees_with_its_ledger_row_refuses_publication(flow_world, flow_rows):
    tampered = json.loads(json.dumps(flow_rows))
    tampered[1]["unevaluable"][0]["causes"] = tampered[1]["unevaluable"][0]["causes"][1:]
    result = diagnose(flow_world, rows=tampered)
    assert [bool(decision["disagreements"]) for decision in result["decisions"]] == [False, True, False]
    report = dg.build_report({}, {VENUE: result})
    assert dg.publication_refusals(report) == [f"{VENUE}: 1 decision(s) disagree with the ledger"]
    assert result["summary"]["disagreements"][0]["decision_at"] == INSTANTS[1].isoformat()


def test_a_no_valid_stop_row_must_be_a_geometry_only_gap_in_the_replay(flow_world, flow_rows):
    tampered = json.loads(json.dumps(flow_rows))
    tampered[0].update(outcome=ec.OUTCOME_NO_TRADE, reasons=[dg.REASON_NO_STOP], unevaluable=[])
    decision = diagnose(flow_world, rows=tampered)["decisions"][0]
    assert decision["disagreements"] == ["the ledger's no-valid-stop NO_TRADE is not a geometry-only structure gap in the replay"]


def test_unknown_and_rootless_causes_are_listed_untraced(base):
    composer = ec.EntryComposer(base, strategy_config=fx.CONFIG)
    run = dg._DiagnosisRun(composer, INSTANTS[0], position_open=False)
    run.replay()
    unknown = dg._trace_component("flow", ["SOME_NEW_CAUSE"], run, EVIDENCE, 15)
    assert unknown["untraced"] == [{"code": "SOME_NEW_CAUSE", "reason": "no tracer for this cause"}] and unknown["roots"] == []
    derived = dg._trace_component("volatility", ["ORDERLINESS_INPUT_MISSING"], run, EVIDENCE, 15)
    assert derived["untraced"] == [{"code": None, "reason": "only derived causes, no root"}]
    empty = dg._trace_component("flow", ["ETF_FLOW_INPUT_MISSING"], run, EVIDENCE, 15)  # the windows are complete here
    assert empty["untraced"] == [{"code": "ETF_FLOW_INPUT_MISSING", "reason": "its root trace found no missing or unusable observation"}]


def test_the_ledger_must_be_exactly_the_window_inside_the_data_window(base, flow_rows):
    with pytest.raises(dg.DiagnosisRefused, match="LEDGER_REFUSED"):
        dg.diagnose_venue(base, flow_rows[:2], INSTANTS, EVIDENCE, strategy_config=fx.CONFIG)
    with pytest.raises(dg.DiagnosisRefused, match="LEDGER_REFUSED"):
        dg.diagnose_venue(base, [*flow_rows, flow_rows[0]], INSTANTS, EVIDENCE, strategy_config=fx.CONFIG)
    for outside in (datetime(2026, 1, 1, tzinfo=UTC), datetime(2019, 12, 31, tzinfo=UTC)):
        with pytest.raises(dg.DiagnosisRefused, match="WINDOW_REFUSED"):
            dg.diagnose_venue(base, flow_rows, (*INSTANTS, outside), EVIDENCE, strategy_config=fx.CONFIG)


def test_unobserved_kraken_hours_are_classified_from_their_records():
    records = [
        {"hour_start": "2021-06-03T00:00:00+00:00", "feed_status": "OBSERVED_ZERO_EVENTS", "incident": False, "execution_count": 4},
        {"hour_start": "2021-06-03T01:00:00+00:00", "feed_status": "SOURCE_UNAVAILABLE", "incident": True, "execution_count": 9},
        {"hour_start": "2021-06-03T02:00:00+00:00", "feed_status": "SOURCE_UNAVAILABLE", "incident": False, "execution_count": 0},
    ]
    assert dg.unobserved_hour_origins(records) == {
        datetime(2021, 6, 3, 1, tzinfo=UTC): "KRAKEN_REPORTED_INCIDENT",
        datetime(2021, 6, 3, 2, tzinfo=UTC): "NO_EXECUTION_IN_HOUR",
    }
    with pytest.raises(dg.DiagnosisRefused, match="EVIDENCE_REFUSED"):
        dg.unobserved_hour_origins([{**records[2], "execution_count": 3}])


# --- the summary, the report and the public index -----------------------------------------------------


def test_the_summary_counts_each_distinct_gap_and_the_decisions_it_leaves_incomplete(flow_result):
    summary = flow_result["summary"]
    assert summary["decisions"] == 3 and summary["outcomes"] == {dg.LEDGER_OUTCOME_UNEVALUABLE: 3}
    assert summary["etf"]["missing_fund_days"] == 1
    assert summary["etf"]["most_decisions"] == [{"fund": GAP_FUND, "date": GAP_DAY.isoformat(), "origin": "FUND_LISTED_WITHOUT_VALUE", "decisions": 3}]
    assert summary["decisions_by_class"] == {dg.SOURCE_ABSENT: 3}
    assert summary["decisions_by_rule"] == {"ETF_WINDOW_NEEDS_EVERY_FUND_EVERY_DAY": 3}
    assert summary["untraced"] == [] and summary["disagreements"] == []


def report_digest() -> str:
    """The flow world's report files' digest, built from scratch (run in a fresh process by the test below)."""

    world = without_fund_day(fx.Scenario().build())
    report = dg.build_report({"code_commit": "0" * 40}, {VENUE: diagnose(world)})
    files = dg.report_files(report)
    index = canonical_json_bytes(dg.public_index(report, files))
    return hashlib.sha256(b"".join(files[name] for name in sorted(files)) + index).hexdigest()


def test_the_report_reproduces_byte_for_byte_in_a_fresh_process(flow_result):
    report = dg.build_report({"code_commit": "0" * 40}, {VENUE: flow_result})
    files = dg.report_files(report)
    mine = hashlib.sha256(b"".join(files[name] for name in sorted(files)) + canonical_json_bytes(dg.public_index(report, files))).hexdigest()
    environment = {**os.environ, "PYTHONHASHSEED": "8675309"}
    command = [sys.executable, "-c", "from btc_predictor.tests.test_research_backtest_diagnosis import report_digest; print(report_digest())"]
    fresh = subprocess.run(command, cwd=REPOSITORY, env=environment, capture_output=True, text=True, check=True)
    assert fresh.stdout.strip() == mine


def test_the_public_index_is_value_free(flow_result):
    report = dg.build_report({"code_commit": "0" * 40, "private_dataset_commit": "f" * 40}, {VENUE: flow_result})
    files = dg.report_files(report)
    index = dg.public_index(report, files)
    assert set(index) == {"index_version", "ticket", "evidence_class", "prohibited_uses", "holdout", "identity", "files", "venues", "private_repository_commit"}
    assert index["venues"] == {VENUE: {"decisions_examined": 3, "untraced": 0, "ledger_disagreements": 0}}
    assert index["files"] == {name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in files.items()}
    assert index["holdout"] == "NOT COLLECTED" and index["private_repository_commit"] is None
    text = canonical_json_bytes(index).decode()
    assert GAP_FUND not in text and not re.search(r"20\d\d-\d\d-\d\d", text)  # no fund and no date reaches it


def test_the_markdown_states_the_evidence_class_and_every_venue(flow_result):
    report = dg.build_report({}, {VENUE: flow_result})
    text = dg.report_markdown(report)
    assert text.startswith(f"# RBT-007A diagnosis ({dg.DIAGNOSIS_VERSION})")
    assert f"**Evidence class:** {dg.EVIDENCE_CLASS}. **Holdout:** NOT COLLECTED." in text
    assert all(use in text for use in dg.PROHIBITED_USES) and f"## {VENUE}" in text


# --- RBT-007's ledgers, the code check and the command ------------------------------------------------


def write_ledger_and_index(tmp_path, data, bound=None):
    store, repository = tmp_path / "store", tmp_path / "public"
    (store / prereg.ARTIFACT_DIRECTORY.name).mkdir(parents=True)
    (repository / prereg.ARTIFACT_DIRECTORY).mkdir(parents=True)
    name = rr.ledger_file(VENUE)
    (store / prereg.ARTIFACT_DIRECTORY.name / name).write_bytes(data)
    bound = data if bound is None else bound
    index = {"files": {name: {"sha256": hashlib.sha256(bound).hexdigest(), "size": len(bound)}}, "identity": {"run_code_commit": "a" * 40}}
    (repository / prereg.ARTIFACT_DIRECTORY / rr.INDEX_FILE).write_bytes(canonical_json_bytes(index))
    return store, repository


def test_rbt007s_ledgers_must_be_the_files_its_public_index_binds(tmp_path):
    data = canonical_json_bytes({"venue": VENUE, "entry_rows": [{"decision_at": "x"}]})
    store, repository = write_ledger_and_index(tmp_path / "good", data)
    ledgers, bound = dg.rbt007_ledgers(store, repository, [VENUE])
    assert ledgers == {VENUE: [{"decision_at": "x"}]} and bound["identity"] == {"run_code_commit": "a" * 40}
    store, repository = write_ledger_and_index(tmp_path / "changed", data, bound=data + b" ")
    with pytest.raises(dg.DiagnosisRefused, match="LEDGER_REFUSED"):
        dg.rbt007_ledgers(store, repository, [VENUE])
    other = canonical_json_bytes({"venue": "COINBASE", "entry_rows": []})
    store, repository = write_ledger_and_index(tmp_path / "venue", other)
    with pytest.raises(dg.DiagnosisRefused, match="is not BITSTAMP's ledger"):
        dg.rbt007_ledgers(store, repository, [VENUE])
    store, repository = write_ledger_and_index(tmp_path / "missing", data)
    (store / prereg.ARTIFACT_DIRECTORY.name / rr.ledger_file(VENUE)).unlink()
    with pytest.raises(dg.DiagnosisRefused, match="LEDGER_REFUSED"):
        dg.rbt007_ledgers(store, repository, [VENUE])


def test_the_code_check_exempts_only_the_diagnosis_and_binds_the_runner_to_rbt007s_run(monkeypatch):
    calls = []
    mine = "btc_predictor/research_backtest/diagnosis.py"
    monkeypatch.setattr(runner, "frozen_code_paths", lambda repository, modules: [mine, "btc_predictor/features/flow.py"])
    monkeypatch.setattr(runner, "frozen_code_mismatches", lambda repository, commit, paths: calls.append((commit, list(paths))) or [])
    assert dg.require_code(REPOSITORY, "f" * 40, "r" * 40) == {"frozen_code_files_checked": 1, "runner_files_checked": 4}
    assert calls == [
        ("f" * 40, ["btc_predictor/features/flow.py"]),
        ("r" * 40, [f"btc_predictor/research_backtest/{name}" for name in runner.RUNNER_MODULES]),
    ]
    monkeypatch.setattr(runner, "frozen_code_mismatches", lambda repository, commit, paths: ["btc_predictor/features/flow.py"] if commit == "f" * 40 else [])
    with pytest.raises(dg.DiagnosisRefused, match="FROZEN_CODE_REFUSED"):
        dg.require_code(REPOSITORY, "f" * 40, "r" * 40)
    monkeypatch.setattr(runner, "frozen_code_mismatches", lambda repository, commit, paths: list(paths) if commit == "r" * 40 else [])
    with pytest.raises(dg.DiagnosisRefused, match="RBT-007's run commit"):
        dg.require_code(REPOSITORY, "f" * 40, "r" * 40)


def test_the_loaded_owners_are_the_frozen_commits():
    record = runner.read_preregistration(REPOSITORY)
    index = json.loads((REPOSITORY / prereg.ARTIFACT_DIRECTORY / rr.INDEX_FILE).read_bytes())
    checked = dg.require_code(REPOSITORY, record["code_commit"], index["identity"]["run_code_commit"])
    assert checked["frozen_code_files_checked"] > 100 and checked["runner_files_checked"] == 4


def test_main_publishes_nothing_on_a_refusal(tmp_path, monkeypatch):
    from btc_predictor.research_backtest import dataset_build as build

    public = tmp_path / "public"
    (public / prereg.ARTIFACT_DIRECTORY).mkdir(parents=True)
    for path in (runner.PREREGISTRATION_PATH, runner.PREREGISTRATION_DIGEST_PATH):
        shutil.copyfile(REPOSITORY / path, public / path)
    before = {path: path.read_bytes() for path in public.rglob("*") if path.is_file()}
    monkeypatch.setattr(build, "PUBLIC_REPOSITORY", public)
    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)
    empty = tmp_path / "store"
    (empty / ".git").mkdir(parents=True)
    lines = []
    status = dg.main(["--store", str(empty), "--out", str(tmp_path / "out")], out=lines.append)
    assert status == 2 and len(lines) == 1 and lines[0].startswith("refused: ")
    assert not (tmp_path / "out").exists()
    assert {path: path.read_bytes() for path in public.rglob("*") if path.is_file()} == before


def stub_pipeline(monkeypatch, tmp_path, result, *, dataset_commit="d" * 40):
    """``main`` with its expensive stages stubbed: the frozen inputs, the ledgers, the evidence, the code check and the replay."""

    from types import SimpleNamespace

    from btc_predictor.research_backtest import dataset_build as build

    public = tmp_path / "public"
    (public / prereg.ARTIFACT_DIRECTORY).mkdir(parents=True, exist_ok=True)
    for path in (runner.PREREGISTRATION_PATH, runner.PREREGISTRATION_DIGEST_PATH):
        shutil.copyfile(REPOSITORY / path, public / path)
    monkeypatch.setattr(build, "PUBLIC_REPOSITORY", public)
    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)
    frozen = SimpleNamespace(inputs={VENUE: object()}, private_commit=dataset_commit, index_sha256="e" * 64)
    identity = {"private_dataset_commit": "d" * 40, "dataset_index_sha256": "e" * 64, "run_code_commit": "a" * 40}
    monkeypatch.setattr(runner, "load_frozen_inputs", lambda store: frozen)
    monkeypatch.setattr(runner, "verify_preregistration", lambda *args, **kwargs: None)
    monkeypatch.setattr(dg, "rbt007_ledgers", lambda root, repository, venues: ({VENUE: []}, {"index_sha256": "1" * 64, "identity": identity}))
    monkeypatch.setattr(dg, "load_source_evidence", lambda store, venues: EVIDENCE)
    monkeypatch.setattr(dg, "require_code", lambda repository, frozen_commit, run_commit: {"frozen_code_files_checked": 1, "runner_files_checked": 4})
    monkeypatch.setattr(dg, "diagnose_venue", lambda inputs, rows, instants, evidence, **kwargs: result)
    store = tmp_path / "store"
    (store / ".git").mkdir(parents=True, exist_ok=True)
    return public, store


def run_main(store, out):
    lines = []
    return dg.main(["--store", str(store), "--out", str(out)], out=lines.append), lines


def test_main_publishes_the_private_files_and_the_index_once(flow_result, tmp_path, monkeypatch):
    public, store = stub_pipeline(monkeypatch, tmp_path, flow_result)
    status, lines = run_main(store, tmp_path / "out")
    assert status == 0, lines
    written = {path.name: path.read_bytes() for path in (tmp_path / "out").iterdir()}
    assert sorted(written) == [dg.REPORT_FILE, dg.REPORT_MARKDOWN_FILE]
    index = json.loads((public / prereg.ARTIFACT_DIRECTORY / dg.INDEX_FILE).read_bytes())
    assert index["files"] == {name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in written.items()}
    report = json.loads(written[dg.REPORT_FILE])
    assert report["identity"]["rbt007_run_code_commit"] == "a" * 40 and report["identity"]["private_dataset_commit"] == "d" * 40
    status, lines = run_main(store, tmp_path / "out")  # a diagnosis is published once
    assert status == 2 and "OUTPUT_REFUSED" in lines[-1]
    assert {path.name: path.read_bytes() for path in (tmp_path / "out").iterdir()} == written


def test_main_publishes_nothing_when_a_replay_disagrees_or_the_ledgers_bind_another_dataset(flow_world, flow_rows, tmp_path, monkeypatch):
    tampered = json.loads(json.dumps(flow_rows))
    tampered[0]["unevaluable"] = []
    disagreeing = diagnose(flow_world, rows=tampered)
    for name, result, commit in (("disagrees", disagreeing, "d" * 40), ("other", disagreeing, "9" * 40)):
        public, store = stub_pipeline(monkeypatch, tmp_path / name, result, dataset_commit=commit)
        status, lines = run_main(store, tmp_path / name / "out")
        assert status == 2 and lines[-1].startswith("refused: ")
        assert ("PUBLICATION_REFUSED" if name == "disagrees" else "were not run on the loaded dataset") in lines[-1]
        assert not (tmp_path / name / "out").exists() and not (public / prereg.ARTIFACT_DIRECTORY / dg.INDEX_FILE).exists()


def test_the_module_reads_no_database_or_network_and_writes_only_fresh_files():
    tree = ast.parse(Path(dg.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    forbidden = ("database", "sqlalchemy", "psycopg", "backfill_transport", "requests", "urllib", "socket", "http")
    assert not [name for name in imported if any(part in name.split(".") or name.endswith(part) for part in forbidden)]
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not calls & {"write_bytes", "write_text", "unlink", "rmtree", "replace_whole"}
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"]


# --- the evidence loader, on the RBT-003 dataset tests' synthetic private store ---------------------------

from btc_predictor.tests import test_research_backtest_dataset_build as dt  # noqa: E402

collected = dt.collected
world_store = dt.world  # the dataset tests' private copy of the collected store


def test_the_evidence_loader_reads_the_stored_collection(world_store):
    dt.built(world_store)
    store = dt.git_store(world_store)
    evidence = dg.load_source_evidence(store, ("BITFINEX", "BITSTAMP", "COINBASE"), units=dt.units_of)
    assert evidence.etf_days == {date(2024, 1, 11): {"IBIT": True, "GBTC": True}, date(2024, 2, 1): {"IBIT": True}}
    assert evidence.etf_origin("GBTC", date(2024, 2, 1)) == "FUND_NOT_LISTED"
    assert evidence.liquidation_hours == {dt.DISAGREEING_HOUR: "WITHHELD_RULING_16"}  # ruling 16; every other hour observed
    assert evidence.liquidation_evidence_days == (dt.LIQUIDATION_DAY, dt.DISAGREEING_DAY)
    assert set(evidence.liquidation_history) >= {dt.LIQUIDATION_DAY, dt.DISAGREEING_DAY}
    assert set(evidence.still_missing_hours) == {"BITFINEX", "BITSTAMP", "COINBASE"} and evidence.still_missing_hours["BITSTAMP"] == frozenset()
    assert evidence.liquidation_window_days > 0 and evidence.liquidation_minimum > 0
