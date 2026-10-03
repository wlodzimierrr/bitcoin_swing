"""RBT-002A ``CHAMPION_COMPLETION_SPEC_V1`` (EPIC Y, non-certifying).

These tests pin:

- coverage (policy V6 section 6A.7): every owner-less, undefined row of the
  reviewed inventory, plus LEVEL_VOLUME_PERCENTILE (section 6A.8), is covered
  exactly once, occurrence by occurrence; an uncovered row, a double cover, an
  unknown id and a changed inventory digest each fail;
- the frozen definition: the persisted canonical JSON rebuilds byte for byte,
  its SHA-256 is recomputed, and it is identical under PYTHONHASHSEED
  0/1/8675309, another cwd and a fresh process;
- the binding rules: one z-score rule and one percentile rule, the section 6A.2
  source class and citation of every element (and a one-line rationale for each
  NEW_PARAMETER), the helpers' census status, long-only inert inputs, the two
  optional rulings, the section 6A.8 level-volume rules and the section 6A.9
  guard contract;
- the BTC-041 helpers the uniform rules name behave as declared, on synthetic
  values only;
- pre-registration: building the spec opens no socket, and the spec module
  imports no database or BTC-019 module directly; warm-up dates come from
  coverage facts, and the simulation's gap and window boundaries are pinned on
  synthetic snapshots.

Every fixture is synthetic. No database, market value or outcome is touched.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import os
import re
import socket
import subprocess
import sys
import tomllib
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features import volatility as volatility_owner
from btc_predictor.features.rolling import rolling_percentile, rolling_zscore
from btc_predictor.research_backtest import completion_spec as spec
from btc_predictor.research_backtest import coverage
from btc_predictor.research_backtest.completion_spec import CompletionSpecError


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "backtest_evidence" / "research_backtest_v1"
RULEBOOK = ROOT / "docs" / "strategy" / "bitcoin_swing_predictor_rulebook_v1_2.md"
FROZEN_SPEC_SHA256 = "123590d1d5bf7f33f3748358b10bbf25e854782e065e7c2cd9c9c2df423a78fe"

# The confirmed RBT-002 R2 list (25 undefined ids) plus LEVEL_VOLUME_PERCENTILE.
CONFIRMED_IDS = {
    "TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H",
    "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL",
    "RANGE_PERCENTILE", "DOWNSIDE_RETURN", "UPSIDE_RETURN",
    "LEVEL_REACTION_MAGNITUDE", "SEVERE_CROWDING_STATE",
    "MOMENTUM_PERSISTENCE_SCORE", "NEW_STRUCTURE_SCORE", "ADD_MOMENTUM_SCORE",
    "NEW_STRUCTURAL_CONFIRMATION", "REGIME_SUPPORTIVE_PREDICATE", "FLOW_SUPPORTIVE_PREDICATE",
    "REGIME_INVALIDATION_PREDICATE", "DATA_RISK_EXIT_PREDICATE",
    "CORRECTION_FROM_LOCAL_HIGH", "DISTRIBUTION_STATE", "SHORT_TRIGGER",
    "MEASURED_MOVE_REFERENCE", "CAPITULATION_EVENT",
    "LEVEL_VOLUME_PERCENTILE",
}


@pytest.fixture(scope="module")
def definition() -> dict[str, Any]:
    return spec.spec_definition()


@pytest.fixture(scope="module")
def entries() -> dict[str, spec.SpecEntry]:
    return {entry.input_id: entry for entry in spec.spec_entries()}


def _inventory() -> dict[str, Any]:
    return copy.deepcopy(spec.bound_inventory())


# --- coverage --------------------------------------------------------------------------------------


def test_the_spec_covers_exactly_the_confirmed_inputs(entries: dict[str, spec.SpecEntry]) -> None:
    assert set(entries) == CONFIRMED_IDS
    assert len(entries) == 26
    spec.check_coverage(tuple(entries.values()), spec.bound_inventory())


def test_every_ownerless_row_is_covered_occurrence_by_occurrence(entries: dict[str, spec.SpecEntry]) -> None:
    rows = [
        row for row in spec.bound_inventory()["input_surface"]["rows"]
        if row["kind"] in spec.COVERED_INVENTORY_KINDS
    ]
    assert len(rows) == 45
    supplied = {item.occurrence: entry.input_id for entry in entries.values() for item in entry.consumers}
    for row in rows:
        assert supplied[f"{row['owner']}.{row['name']}"] == row["input_id"]
    assert len(supplied) == len(rows)


def test_level_volume_is_the_superseded_rulebook_fallback_row(entries: dict[str, spec.SpecEntry]) -> None:
    kinds = {key: kind for key, (kind, _) in spec.ownerless_occurrences(spec.bound_inventory()).items()}
    assert kinds["LEVEL_VOLUME_PERCENTILE"] == "OWNERLESS_RULEBOOK_FALLBACK"
    assert entries["LEVEL_VOLUME_PERCENTILE"].inventory_kind == "OWNERLESS_RULEBOOK_FALLBACK"
    assert kinds["LIQUIDATION_PERCENTILE"] == "OWNERLESS_CERTIFIED_DEFINITION"
    assert "LIQUIDATION_PERCENTILE" not in entries


def _row(input_id: str, owner: str, name: str, kind: str = "OWNERLESS_UNDEFINED") -> dict[str, Any]:
    return {"input_id": input_id, "kind": kind, "owner": owner, "name": name}


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda rows: rows.append(_row("NEW_OWNERLESS_INPUT", "btc_predictor.features.trend.TrendScoreInput", "z_new")), "OWNERLESS_INPUT_UNCOVERED"),
        (lambda rows: rows.append(_row("TREND_Z_M4", "btc_predictor.features.trend.OtherInput", "z_m4")), "OCCURRENCES_DIFFER"),
        (lambda rows: rows.append(_row(None, "btc_predictor.features.trend.TrendScoreInput", "z_x")), "OWNERLESS_ROW_WITHOUT_ID"),
        (lambda rows: rows.append(_row("TREND_Z_M4", "x.Y", "z", kind="OWNERLESS_CERTIFIED_DEFINITION")), "OWNERLESS_KIND_CONFLICT"),
        (lambda rows: rows.append(_row("OTHER_CERTIFIED", "x.Y", "z", kind="OWNERLESS_CERTIFIED_DEFINITION")), "CERTIFIED_OWNERLESS_SET_CHANGED"),
        (lambda rows: rows.append(_row("ODD", "x.Y", "z", kind="OWNERLESS_SOMETHING")), "UNKNOWN_OWNERLESS_KIND"),
    ],
)
def test_an_inventory_change_fails_coverage(mutate: Any, code: str) -> None:
    inventory = _inventory()
    mutate(inventory["input_surface"]["rows"])
    with pytest.raises(CompletionSpecError) as raised:
        spec.check_coverage(spec.spec_entries(), inventory)
    assert raised.value.code == code


def test_an_inventory_input_that_becomes_defined_makes_the_spec_cover_an_unknown_id() -> None:
    inventory = _inventory()
    for row in inventory["input_surface"]["rows"]:
        if row["input_id"] == "UPSIDE_RETURN":
            row["kind"] = "DERIVED_BY_OWNER"
    with pytest.raises(CompletionSpecError) as raised:
        spec.check_coverage(spec.spec_entries(), inventory)
    assert raised.value.code == "SPEC_COVERS_UNKNOWN_INPUT"


def test_an_input_covered_twice_fails(entries: dict[str, spec.SpecEntry]) -> None:
    doubled = (*entries.values(), entries["SHORT_TRIGGER"])
    with pytest.raises(CompletionSpecError) as raised:
        spec.check_coverage(doubled, spec.bound_inventory())
    assert raised.value.code == "INPUT_COVERED_TWICE"


def test_an_uncovered_input_fails(entries: dict[str, spec.SpecEntry]) -> None:
    missing = tuple(entry for key, entry in entries.items() if key != "CAPITULATION_EVENT")
    with pytest.raises(CompletionSpecError) as raised:
        spec.check_coverage(missing, spec.bound_inventory())
    assert raised.value.code == "OWNERLESS_INPUT_UNCOVERED"


def test_an_occurrence_supplied_twice_fails(entries: dict[str, spec.SpecEntry]) -> None:
    entry = entries["UPSIDE_RETURN"]
    doubled = spec.SpecEntry(**{**entry.__dict__, "consumers": entry.consumers * 2})
    others = tuple(item for key, item in entries.items() if key != "UPSIDE_RETURN")
    with pytest.raises(CompletionSpecError) as raised:
        spec.check_coverage((*others, doubled), spec.bound_inventory())
    assert raised.value.code == "OCCURRENCE_COVERED_TWICE"


def test_the_inventory_is_bound_by_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = spec.inventory_path().read_bytes()
    assert hashlib.sha256(data).hexdigest() == spec.BOUND_INVENTORY_SHA256
    assert (ARTIFACTS / coverage.INVENTORY_DIGEST_FILENAME).read_text().split()[0] == spec.BOUND_INVENTORY_SHA256
    altered = tmp_path / spec.BOUND_INVENTORY_FILENAME
    altered.write_bytes(data.replace(b'"RESEARCH_BACKTEST_POLICY_V5"', b'"RESEARCH_BACKTEST_POLICY_V9"', 1))
    monkeypatch.setattr(spec, "inventory_path", lambda: altered)
    spec.bound_inventory_bytes.cache_clear()
    spec.bound_inventory.cache_clear()
    try:
        with pytest.raises(CompletionSpecError) as raised:
            spec.spec_definition()
        assert raised.value.code == "INVENTORY_DIGEST_MISMATCH"
        assert "rebind" in str(raised.value)
    finally:
        spec.bound_inventory_bytes.cache_clear()
        spec.bound_inventory.cache_clear()


# --- the frozen definition ---------------------------------------------------------------------


def test_the_persisted_definition_rebuilds_byte_for_byte() -> None:
    persisted = (ARTIFACTS / spec.SPEC_FILENAME).read_bytes()
    assert persisted == spec.spec_bytes()
    digest = hashlib.sha256(persisted).hexdigest()
    assert digest == FROZEN_SPEC_SHA256 == spec.spec_sha256()
    assert (ARTIFACTS / spec.SPEC_DIGEST_FILENAME).read_text(encoding="ascii") == f"{digest}  {spec.SPEC_FILENAME}\n"
    assert spec.verify_persisted() == digest


def test_the_definition_is_canonical_sorted_json() -> None:
    data = (ARTIFACTS / spec.SPEC_FILENAME).read_bytes()
    value = json.loads(data)
    assert json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii") == data


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_the_definition_is_identical_under_hash_seeds_another_cwd_and_a_fresh_process(seed: str, tmp_path: Path) -> None:
    environment = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
    output = tmp_path / "out"
    completed = subprocess.run(
        [sys.executable, "-m", "btc_predictor.research_backtest.completion_spec", "write", "--output-dir", str(output)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "spec:" in completed.stdout
    assert (output / spec.SPEC_FILENAME).read_bytes() == (ARTIFACTS / spec.SPEC_FILENAME).read_bytes()
    assert (output / spec.SPEC_DIGEST_FILENAME).read_bytes() == (ARTIFACTS / spec.SPEC_DIGEST_FILENAME).read_bytes()


def test_the_definition_header_carries_identity_and_scope(definition: dict[str, Any]) -> None:
    assert definition["spec_version"] == "CHAMPION_COMPLETION_SPEC_V1"
    assert definition["research_strategy_id"] == "swing_v1.2+completion_v1"
    assert definition["policy"] == "RESEARCH_BACKTEST_POLICY_V7"
    assert definition["scope"] == "EPIC_Y_RESEARCH_BACKTEST_ONLY"
    assert set(definition["excluded_uses"]) == {"ADVISORY", "PAPER_TRADING", "EPIC_X", "BTC_019"}
    assert definition["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING"
    assert definition["canonical_reference"] == "UNRESOLVED"
    assert definition["bound_inventory"]["sha256"] == spec.BOUND_INVENTORY_SHA256
    assert definition["champion_base_identity"] == {
        "strategy_version": "swing_v1.2", "config_version": "strategy_config_v2", "parameter_set_id": "default_phase1",
    }


# --- uniformity and source classes -----------------------------------------------------------------


def test_one_z_rule_and_one_percentile_rule(entries: dict[str, spec.SpecEntry]) -> None:
    z_ids = {key for key, entry in entries.items() if entry.uniform_rule == "UNIFORM_ZSCORE_V1"}
    pct_ids = {key for key, entry in entries.items() if entry.uniform_rule == "UNIFORM_PERCENTILE_V1"}
    assert z_ids == {"TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H",
                     "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"}
    assert pct_ids == {"RANGE_PERCENTILE", "LEVEL_VOLUME_PERCENTILE"}
    assert [rule.rule_id for rule in spec.UNIFORM_RULES] == ["UNIFORM_ZSCORE_V1", "UNIFORM_PERCENTILE_V1"]
    for rule in spec.UNIFORM_RULES:
        assert rule.exceptions == ()
    rejected = " ".join(spec.UNIFORM_ZSCORE.rejected_alternatives)
    assert "180 days" in rejected and "20 observations" in rejected and "daily decision instant" in rejected
    # The z-score inputs that reuse a z value carry no window of their own.
    for key in ("MOMENTUM_PERSISTENCE_SCORE", "ADD_MOMENTUM_SCORE"):
        assert entries[key].uniform_rule is None
        assert any(element.value == "UNIFORM_ZSCORE_V1" for element in entries[key].elements)


def test_the_uniform_rules_use_the_owner_numbers() -> None:
    assert spec.UNIFORM_ZSCORE_WINDOW_DAYS == 730 == volatility_owner.DEFAULT_VOLATILITY_PERCENTILE_WINDOW_DAYS
    assert spec.UNIFORM_ZSCORE_MIN_OBSERVATIONS == 30 == positioning_owner.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS
    assert spec.UNIFORM_PERCENTILE_WINDOW_DAYS == 730
    assert spec.UNIFORM_PERCENTILE_MIN_OBSERVATIONS == 365 == volatility_owner.DEFAULT_VOLATILITY_PERCENTILE_MIN_OBSERVATIONS
    z = {element.name: element for element in spec.UNIFORM_ZSCORE.elements}
    assert z["window"].source_class == spec.SOURCE_NEW_PARAMETER
    assert "730 days" in z["window"].value and "30" == z["minimum_prior_observations"].value
    assert z["degrees_of_freedom"].value.startswith("0")
    pct = {element.name: element for element in spec.UNIFORM_PERCENTILE.elements}
    assert pct["minimum_prior_observations"].value == "365" and "730 days" in pct["window"].value


def test_every_element_has_a_source_class_and_citation_and_new_parameters_a_rationale(definition: dict[str, Any]) -> None:
    elements = [element for entry in definition["entries"] for element in entry["elements"]]
    elements += [element for rule in definition["uniform_rules"] for element in rule["elements"]]
    assert elements
    for element in elements:
        assert element["source_class"] in spec.ELEMENT_SOURCE_CLASSES
        assert element["citation"].strip()
        if element["source_class"] in (spec.SOURCE_NEW_PARAMETER, spec.SOURCE_POLICY_RULING):
            assert element["rationale"].strip(), element["name"]
            assert "\n" not in element["rationale"]
    assert len(definition["new_parameters"]) == 17
    for item in definition["new_parameters"]:
        assert item["rationale"].strip() and item["citation"].strip()


def test_a_new_parameter_without_a_rationale_is_refused() -> None:
    with pytest.raises(CompletionSpecError) as raised:
        spec.Element("x", "1", spec.SOURCE_NEW_PARAMETER, "somewhere").as_record()
    assert raised.value.code == "RATIONALE_MISSING"


def test_the_governing_source_class_is_the_lowest_precedence_tier(entries: dict[str, spec.SpecEntry]) -> None:
    for entry in entries.values():
        if entry.disposition != spec.DISPOSITION_DEFINED:
            assert entry.source_class == spec.SOURCE_POLICY_RULING
            continue
        tiers = [element.source_class for element in entry.elements if element.source_class in spec.SOURCE_CLASSES]
        assert entry.source_class == max(tiers, key=spec.SOURCE_CLASSES.index)


_REPO_CITATION = re.compile(r"(btc_predictor/[\w/]+\.(?:py|toml)):(\d+)(?:-(\d+))?")
_RULEBOOK_LINES = re.compile(r"Rulebook v1\.2 section [^;]*?lines? (\d+)(?:-(\d+))?")


def _citations(definition: dict[str, Any]) -> list[str]:
    texts = [element["citation"] for entry in definition["entries"] for element in entry["elements"]]
    texts += [element["citation"] for rule in definition["uniform_rules"] for element in rule["elements"]]
    texts += [consumer["location"] for entry in definition["entries"] for consumer in entry["consumers"]]
    texts += [citation for guard in definition["positioning_zero_variance_guards"] for citation in guard["citations"]]
    return texts


def test_every_repository_line_citation_exists(definition: dict[str, Any]) -> None:
    checked = 0
    for text in _citations(definition):
        for path, first, last in _REPO_CITATION.findall(text):
            lines = (ROOT / path).read_text().splitlines()
            assert int(first) <= len(lines), text
            assert not last or int(first) <= int(last) <= len(lines), text
            checked += 1
    assert checked > 60


_SYMBOL_CITATION = re.compile(r"(btc_predictor/[\w/]+\.py):(\d+)(?:-(\d+))? ([A-Za-z_][\w.]*)")


def test_every_symbol_citation_names_code_at_its_line(definition: dict[str, Any]) -> None:
    checked = 0
    for text in _citations(definition):
        for path, first, last, symbol in _SYMBOL_CITATION.findall(text):
            lines = (ROOT / path).read_text().splitlines()
            end = max(int(last or first), int(first) + 15)
            window = "\n".join(lines[int(first) - 1 : end])
            name = symbol.rstrip(".").split(".")[-1]
            assert name in window, (text, name)
            checked += 1
    assert checked > 40


def test_every_rulebook_line_citation_exists(definition: dict[str, Any]) -> None:
    total = len(RULEBOOK.read_text().splitlines())
    found = 0
    for text in _citations(definition):
        for first, last in _RULEBOOK_LINES.findall(text):
            assert int(first) <= total and (not last or int(first) <= int(last) <= total), text
            found += 1
    assert found > 20


def test_every_consumer_location_names_its_symbol() -> None:
    for entry in spec.spec_entries():
        for consumer in entry.consumers:
            location, symbol = consumer.location.split(" ", 1)
            path, line = location.split(":")
            text = (ROOT / path).read_text().splitlines()[int(line) - 1]
            owner = symbol.split()[0].split(".")[0]
            field = consumer.occurrence.rsplit(".", 1)[1]
            assert owner in text or field in text, consumer
            module = consumer.occurrence.rsplit(".", 2)[0]
            assert path == module.replace(".", "/") + ".py"


# --- helpers and the census --------------------------------------------------------------------


def test_helper_census_status_matches_the_reviewed_roots(definition: dict[str, Any]) -> None:
    roots = {item["root"] for item in spec.bound_inventory()["input_surface"]["census"]["roots"]}
    census = definition["helpers_by_census_status"]
    assert census["CENSUS_ROOT"] and set(census["CENSUS_ROOT"]) <= roots
    assert not set(census["PROMOTE_TO_CENSUS_ROOT"]) & roots
    assert not set(census["CLASSIFIED_INPUT_SOURCE"]) & roots
    assert definition["composer_roots_to_promote"] == census["PROMOTE_TO_CENSUS_ROOT"]
    assert set(definition["composer_roots_to_promote"]) == {
        "btc_predictor.data.ohlcv.next_bar_timestamp",
        "btc_predictor.features.momentum.price_momentum_from_daily_bars",
        "btc_predictor.features.positioning._futures_basis_averages_by_time",
        "btc_predictor.features.positioning._futures_basis_history",
        "btc_predictor.features.positioning._funding_averages_by_time",
        "btc_predictor.features.positioning._funding_average_history",
        "btc_predictor.features.positioning._aggregate_open_interest_by_time",
        "btc_predictor.features.positioning._open_interest_growth_by_time",
        "btc_predictor.features.positioning._oi_growth_history",
        "btc_predictor.features.rolling.rolling_percentile",
        "btc_predictor.features.rolling.rolling_zscore",
        "btc_predictor.features.rolling.true_ranges",
        "btc_predictor.quant.comparisons.decision_greater_equal",
        "btc_predictor.quant.transforms.normal_cdf_score",
    }


def test_the_level_volume_source_helper_supplies_1h_bars(entries: dict[str, spec.SpecEntry]) -> None:
    symbols = {helper.symbol for helper in entries["LEVEL_VOLUME_PERCENTILE"].helpers}
    assert "btc_predictor.research_backtest.replay_inputs.build_shared_replay_snapshot" in symbols
    # BTC-040 derives only 1d/1w/1mo buckets, so it cannot be the 1h volume source.
    assert "btc_predictor.data.ohlcv.build_canonical_market_bars" not in symbols
    from btc_predictor.data import ohlcv
    assert "1h" not in ohlcv.CANONICAL_MARKET_BAR_TIMEFRAMES


def test_every_named_helper_exists() -> None:
    for status in spec.helper_census(spec.spec_entries()).values():
        for symbol in status:
            module_name, attribute = symbol.rsplit(".", 1)
            assert callable(getattr(importlib.import_module(module_name), attribute)), symbol


# --- section 6A rules ------------------------------------------------------------------------------


def test_short_only_inputs_are_inert_and_listed(entries: dict[str, spec.SpecEntry]) -> None:
    config = tomllib.loads((ROOT / "btc_predictor/config/strategy/default.toml").read_text())
    assert config["backtest"]["allow_short_trades"] is False
    inert = {key for key, entry in entries.items() if entry.disposition == spec.DISPOSITION_INERT}
    assert inert == {"SHORT_TRIGGER", "DISTRIBUTION_STATE"}
    for key in inert:
        assert entries[key].accounted_causes == ("INERT_SHORT_SIDE",)


def test_the_optional_inputs_are_ruled(entries: dict[str, spec.SpecEntry]) -> None:
    for key in ("MEASURED_MOVE_REFERENCE", "CAPITULATION_EVENT"):
        entry = entries[key]
        assert entry.disposition == spec.DISPOSITION_OMITTED
        (ruling,) = entry.elements
        assert ruling.source_class == spec.SOURCE_POLICY_RULING and ruling.rationale
    assert "structure" in entries["CAPITULATION_EVENT"].entry_components


def test_severe_crowding_is_the_existing_crowding_flag(entries: dict[str, spec.SpecEntry]) -> None:
    entry = entries["SEVERE_CROWDING_STATE"]
    assert "C.flagged if C.complete else None" in entry.rule
    assert any("calculate_crowding_flag" in helper.symbol for helper in entry.helpers)
    assert any(element.source_class == spec.SOURCE_POLICY_MANDATE and "6A.5" in element.citation for element in entry.elements)


def test_level_volume_follows_section_6a8(entries: dict[str, spec.SpecEntry], definition: dict[str, Any]) -> None:
    entry = entries["LEVEL_VOLUME_PERCENTILE"]
    elements = {element.name: element for element in entry.elements}
    assert "Bitstamp" in elements["source"].value and elements["source"].source_class == spec.SOURCE_POLICY_MANDATE
    assert entry.uniform_rule == "UNIFORM_PERCENTILE_V1"
    assert "binning" in " ".join(entry.notes)
    config = tomllib.loads((ROOT / "btc_predictor/config/strategy/default.toml").read_text())
    assert {key: Decimal(str(value)) for key, value in config["price_levels"]["level_strength_weights"].items()} == {
        key: Decimal("0.20") for key in ("timeframe", "touch_count", "reaction_magnitude", "volume", "confluence")
    }
    for venue in ("BITSTAMP", "COINBASE", "BITFINEX"):
        record = definition["warm_up"]["by_venue"][venue]["entries"]["LEVEL_VOLUME_PERCENTILE"]
        weekly = record["by_source_timeframe"]["1w"]
        assert weekly["first_pivot_bar_close"] == "2021-01-11T00:00:00+00:00"
        assert weekly["earliest_member_detection"] == "2021-02-01T00:00:00+00:00"
        assert record["by_source_timeframe"]["1mo"]["earliest_member_detection"] == "2021-04-01T00:00:00+00:00"


def test_the_e1_guard_contract(definition: dict[str, Any]) -> None:
    guard = definition["e1_guard"]
    assert guard["implemented_by"].startswith("RBT-004")
    assert {helper["symbol"]: helper["census"] for helper in guard["history_helpers"]} == {
        "btc_predictor.features.positioning.futures_basis_health": "CENSUS_ROOT",
        "btc_predictor.features.positioning._futures_basis_averages_by_time": "PROMOTE_TO_CENSUS_ROOT",
        "btc_predictor.features.positioning._futures_basis_history": "PROMOTE_TO_CENSUS_ROOT",
    }
    clauses = guard["clauses"]
    assert "Decimal ==" in clauses["5_equality"] and "whether or not" in clauses["5_equality"]
    assert "FUTURES_BASIS_ZERO_VARIANCE" in clauses["6_refusal"]
    for field in ("PositioningScoreInput.basis_health", "CrowdingFlagInput.basis_zscore", "StressFlagInput.basis_zscore", "EuphoriaFlagInput.basis_zscore"):
        assert field in clauses["6_refusal"]
    assert "STRUCTURALLY_UNEVALUABLE" in clauses["7_structural_unevaluability"]
    assert len(guard["required_tests"]) == 5
    assert any("reimplementing" in item for item in guard["prohibited"])
    assert "FUTURES_BASIS_ZERO_VARIANCE" in positioning_owner.FUTURES_BASIS_HEALTH_REASON_CODES


def test_every_defined_entry_states_point_in_time_and_missing_behaviour(entries: dict[str, spec.SpecEntry]) -> None:
    for entry in entries.values():
        assert entry.point_in_time.strip() and entry.missing_input.strip()
        assert "never" in entry.missing_input.lower(), entry.input_id


# --- warm-up -------------------------------------------------------------------------------------


def test_the_warm_up_primitives_reproduce_the_inventory_dates() -> None:
    inventory = spec.bound_inventory()
    requirements = spec._requirements_by_id()
    for venue in spec.REPLAY_VENUES:
        series = spec.venue_series(inventory["database_coverage"], venue)
        for input_id, expected in inventory["earliest_evaluable"]["venues"][venue.venue_id]["inputs"].items():
            if expected["status"] != "EVALUABLE":
                continue
            first = spec._first(spec.inventory_input_series(input_id, requirements, series))
            assert first is not None and first[1].isoformat() == expected["available_at"], (venue.venue_id, input_id)


def test_the_earliest_evaluable_effect_is_disclosed(definition: dict[str, Any]) -> None:
    for venue in ("BITSTAMP", "COINBASE", "BITFINEX"):
        effect = definition["earliest_evaluable_effect"][venue]
        assert effect["inventory_lower_bound_available_at"] == "2024-02-10T00:00:00+00:00"
        assert effect["spec_completed_status"] == "DATA_DEPENDENT_LOWER_BOUND"
        assert effect["lower_bound_due_to"] == ["structure"]
        assert effect["spec_completed_available_at"] == "2024-03-24T00:00:00+00:00"
        assert effect["days_later_than_inventory_lower_bound"] == 43
        assert "flow" in effect["binding_components"]
        assert effect["binding_entries"] == ["FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"]
        facts = definition["warm_up"]["by_venue"][venue]
        assert facts["core_regime"]["status"] == "EVALUABLE"
        assert facts["core_regime"]["available_at"] == "2024-03-24T00:00:00+00:00"
        entries = definition["warm_up"]["by_venue"][venue]["entries"]
        assert entries["FLOW_Z_ETF_NORM_20D"]["available_at"] == "2024-03-24T00:00:00+00:00"
        assert entries["FLOW_Z_ETF_NORM_5D"]["available_at"] == "2024-03-03T00:00:00+00:00"


def test_every_entry_has_a_warm_up_record_per_venue(definition: dict[str, Any]) -> None:
    for venue in ("BITSTAMP", "COINBASE", "BITFINEX"):
        records = definition["warm_up"]["by_venue"][venue]["entries"]
        assert set(records) == CONFIRMED_IDS
        for key, record in records.items():
            assert record["status"] in ("EVALUABLE", "NO_WARM_UP", "DATA_DEPENDENT_LOWER_BOUND"), (venue, key)
            assert record["input_id"] == key
            if record["status"] != "NO_WARM_UP":
                assert record["available_at"] is not None, (venue, key)
        assert {key for key, record in records.items() if record["binds_earliest_evaluable"]} == {
            "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL",
        }


def _snapshot_with_missing_bitstamp_hours(*hours: str) -> dict[str, Any]:
    snapshot = copy.deepcopy(spec.bound_inventory()["database_coverage"])
    venue = spec.SHARED_VOLUME_VENUE
    for entry in snapshot["raw_tables"]["raw.btc_ohlcv"]["series"]:
        key = entry["key"]
        if (key["exchange"], key["symbol"], key["provider"], key["timeframe"]) == (venue.exchange, venue.symbol, venue.provider, "1h"):
            entry["data_window"]["missing_runs"] = [[hour, hour, 1] for hour in hours]
    return snapshot


def test_level_volume_warm_up_on_the_inventory_snapshot() -> None:
    snapshot = spec.bound_inventory()["database_coverage"]
    result = spec.level_volume_warm_up(snapshot, spec.venue_series(snapshot, spec.SHARED_VOLUME_VENUE))
    assert result["1w"]["first_pivot_bar_close"] == "2021-01-11T00:00:00+00:00"
    assert result["1w"]["comparators_at_first_pivot"] == 369
    assert result["1mo"]["first_pivot_bar_close"] == "2021-02-01T00:00:00+00:00"
    assert result["1mo"]["comparators_at_first_pivot"] == 366


@pytest.mark.parametrize(
    ("hour", "close", "detection"),
    [
        # A missing hour in a comparator window removes 7 daily comparators.
        ("2020-06-15T05:00:00+00:00", "2021-01-18T00:00:00+00:00", "2021-02-08T00:00:00+00:00"),
        # A missing hour inside the pivot week leaves that pivot undefined.
        ("2021-01-10T23:00:00+00:00", "2021-01-18T00:00:00+00:00", "2021-02-08T00:00:00+00:00"),
    ],
)
def test_a_missing_bitstamp_hour_shifts_the_level_volume_warm_up(hour: str, close: str, detection: str) -> None:
    snapshot = _snapshot_with_missing_bitstamp_hours(hour)
    series = spec.venue_series(snapshot, spec.SHARED_VOLUME_VENUE)
    weekly = spec.level_volume_warm_up(snapshot, series)["1w"]
    assert weekly["first_pivot_bar_close"] == close
    assert weekly["earliest_member_detection"] == detection
    # Independent count: midnights in [e - 730 days, e) whose 168-hour window holds no missing hour.
    from datetime import UTC, datetime, timedelta
    e = datetime.fromisoformat(close)
    missing = datetime.fromisoformat(hour)
    start = datetime(2020, 1, 1, tzinfo=UTC)
    count = sum(
        1
        for days in range(730)
        if (d := e - timedelta(days=730) + timedelta(days=days)) - timedelta(days=7) >= start
        and not (d - timedelta(days=7) <= missing < d)
    )
    assert weekly["comparators_at_first_pivot"] == count >= 365


def test_the_true_range_series_needs_an_adjacent_prior_bar() -> None:
    from datetime import UTC, datetime, timedelta
    day = timedelta(days=1)
    first = datetime(2021, 1, 1, tzinfo=UTC)
    times = [first + index * day for index in range(6) if index != 3]
    daily = coverage.ObservationSeries(coverage.SERIES_DAILY, tuple((time, time + day) for time in times), "B", "S")
    series = spec._custom_series(spec.DAILY_TRUE_RANGE_FRACTION, {coverage.SERIES_DAILY: daily})
    assert series.times() == (first + day, first + 2 * day, first + 5 * day)
    returns = spec._custom_series(spec.DAILY_RETURN_7, {coverage.SERIES_DAILY: daily})
    assert returns.observations == ()


def test_the_trailing_window_counts_the_window_start_and_excludes_the_current_observation() -> None:
    from datetime import UTC, datetime, timedelta
    day = timedelta(days=1)
    first = datetime(2021, 1, 1, tzinfo=UTC)
    base = coverage.ObservationSeries("Q", tuple((first + index * day, first + (index + 1) * day) for index in range(10)), "B", "S")
    # [t - 3 days, t) holds exactly 3 prior observations from index 3 on; the current one never counts.
    kept = spec.trailing_window_series("Z", base, window=timedelta(days=3), min_prior=3)
    assert kept.times()[0] == first + 3 * day
    assert spec.trailing_window_series("Z", base, window=timedelta(days=3), min_prior=4).observations == ()


def test_warm_up_refuses_primitives_that_drift_from_the_inventory() -> None:
    inventory = _inventory()
    inputs = inventory["earliest_evaluable"]["venues"]["BITSTAMP"]["inputs"]
    inputs["MOMENTUM_4W"]["available_at"] = "2020-02-01T00:00:00+00:00"
    with pytest.raises(CompletionSpecError) as raised:
        spec.compute_warm_up(spec.spec_entries(), inventory)
    assert raised.value.code == "WARMUP_PRIMITIVES_DRIFT"


# --- the helpers behave as the uniform rules declare (synthetic values) ------------------------------


@pytest.mark.parametrize("value", ["0.015", "0.0608333333333333333333333333", "-0.07", "12345.678", "1E-9"])
@pytest.mark.parametrize("size", [30, 31, 179, 365, 729, 730])
def test_the_z_helper_refuses_an_exactly_constant_history(value: str, size: int) -> None:
    history = [Decimal(value)] * size
    assert rolling_zscore([*history, Decimal(value)], window=size, min_periods=30, sample=False)[-1] is None
    assert rolling_zscore([*history, Decimal(value) * 2 + 1], window=size, min_periods=30, sample=False)[-1] is None


def test_the_z_helper_is_a_population_prior_window_z_score() -> None:
    history = [Decimal(item) for item in range(1, 31)]
    mean = sum(history) / len(history)
    deviation = (sum((item - mean) ** 2 for item in history) / len(history)).sqrt()
    result = rolling_zscore([*history, Decimal(40)], window=len(history), min_periods=30, sample=False)[-1]
    assert result is not None and abs(result - (Decimal(40) - mean) / deviation) < Decimal("1E-12")
    # The current value never enters its own history.
    shifted = rolling_zscore([*history, Decimal(1000)], window=len(history), min_periods=30, sample=False)[-1]
    assert shifted is not None and abs(shifted - (Decimal(1000) - mean) / deviation) < Decimal("1E-9")


def test_the_percentile_helper_is_the_prior_window_midrank() -> None:
    history = [Decimal(item % 7) for item in range(365)]
    current = Decimal(3)
    less = sum(1 for item in history if item < current)
    equal = sum(1 for item in history if item == current)
    expected = (Decimal(less) + Decimal("0.5") * equal) / len(history) * 100
    result = rolling_percentile([*history, current], window=len(history), min_periods=365)[-1]
    assert result is not None and abs(result - expected) < Decimal("1E-9")
    assert rolling_percentile([*history[:364], current], window=364, min_periods=364)[-1] is not None


# --- pre-registration ------------------------------------------------------------------------------


def test_building_the_spec_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the completion spec must not open a connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert spec.spec_sha256() == FROZEN_SPEC_SHA256


def test_the_spec_module_imports_no_database_or_btc019_module_directly() -> None:
    tree = ast.parse(Path(spec.__file__).read_text())
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    for name in imported:
        assert not name.startswith(("sqlalchemy", "psycopg")), name
        assert "database" not in name and "btc019" not in name and "reference_composite" not in name, name


def test_the_pre_registration_record(definition: dict[str, Any]) -> None:
    record = definition["pre_registration"]
    assert record["database_connected"] is False
    assert record["market_values_read"] is False
    assert record["scores_signals_trades_or_performance_computed"] is False
    assert record["holdout"] == "NOT COLLECTED"
    assert spec.BOUND_INVENTORY_SHA256 in record["data_consulted"][0]
