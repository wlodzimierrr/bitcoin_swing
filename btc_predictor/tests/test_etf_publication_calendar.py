"""POSTP1-001V2A tests for the frozen ETF calendar authority.

All calendar evidence and flow rows are synthetic. The named 2026 dates are
sanity checks only; no fixture is prospective collection or scientific source
evidence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.data import EtfFlow
from btc_predictor.features import flow
from btc_predictor.research import etf_publication_calendar as cal


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / cal.OUTPUT_NAMESPACE
ACQUIRED = datetime(2025, 12, 15, tzinfo=UTC)
DECISION = datetime(2026, 12, 31, tzinfo=UTC)
HOLIDAYS_2026 = {
    date(2026, 1, 1): "CLOSED",
    date(2026, 1, 19): "CLOSED",
    date(2026, 2, 16): "CLOSED",
    date(2026, 4, 3): "CLOSED",
    date(2026, 5, 25): "CLOSED",
    date(2026, 6, 19): "CLOSED",
    date(2026, 7, 3): "CLOSED",
    date(2026, 9, 7): "CLOSED",
    date(2026, 11, 26): "CLOSED",
    date(2026, 11, 27): "OPEN_EARLY_CLOSE",
    date(2026, 12, 24): "OPEN_EARLY_CLOSE",
    date(2026, 12, 25): "CLOSED",
}


def populated_store(
    *,
    exceptions: dict[date, str] | None = None,
    available_at: datetime = ACQUIRED,
    coverage_start: date = date(2026, 1, 1),
    coverage_end: date = date(2026, 12, 31),
) -> cal.CalendarEvidenceStore:
    store = cal.CalendarEvidenceStore()
    for venue in cal.CANONICAL_VENUES:
        snapshot = cal.official_source_snapshot_record(
            venue_id=venue,
            source_document_identity=f"official://{venue}/2026-calendar",
            source_bytes=f"synthetic official {venue} schedule fixture".encode(),
            acquired_at=available_at,
            available_at=available_at,
        )
        source_sha = store.put(snapshot)
        schedule = cal.normalized_schedule_record(
            store,
            source_snapshot_sha256=source_sha,
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            exceptions=HOLIDAYS_2026 if exceptions is None else exceptions,
        )
        schedule_sha = store.put(schedule)
        current = coverage_start
        while current <= coverage_end:
            if current.weekday() < 5:
                store.put(
                    cal.venue_session_calendar_record(
                        store,
                        normalized_schedule_sha256=schedule_sha,
                        trade_date=current,
                    )
                )
            current += timedelta(days=1)
    return store


def add_revision(
    store: cal.CalendarEvidenceStore,
    *,
    venue: str,
    trade_date: date,
    status: str,
    available_at: datetime,
) -> str:
    snapshot = cal.official_source_snapshot_record(
        venue_id=venue,
        source_document_identity=f"official://{venue}/notice/{available_at.isoformat()}",
        source_bytes=f"synthetic notice {venue} {trade_date} {status}".encode(),
        acquired_at=available_at,
        available_at=available_at,
    )
    snapshot_sha = store.put(snapshot)
    schedule = cal.normalized_schedule_record(
        store,
        source_snapshot_sha256=snapshot_sha,
        coverage_start=trade_date,
        coverage_end=trade_date,
        exceptions={trade_date: status},
    )
    schedule_sha = store.put(schedule)
    return store.put(
        cal.venue_session_calendar_record(
            store,
            normalized_schedule_sha256=schedule_sha,
            trade_date=trade_date,
        )
    )


def flow_row(fund: str, day: date) -> EtfFlow:
    return EtfFlow(
        fund=fund,
        observation_date=day,
        flow_usd=Decimal("10"),
        aum_usd=Decimal("1000"),
        provider="synthetic",
        source="synthetic",
        revision="1",
        available_at=datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC),
        ingested_at=datetime.combine(day + timedelta(days=1), datetime.min.time(), UTC),
    )


def test_authority_identity_scope_and_safety_are_frozen() -> None:
    authority = cal.authority_definition()
    assert authority["authority_version"] == "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
    assert authority["program_ticket"] == "POSTP1-001V2A"
    assert authority["status"] == (
        "FROZEN_PRE_DATA_ETF_CALENDAR_AUTHORITY_AWAITING_XHIGH_REVIEW"
    )
    assert authority["final_classification"] == (
        "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert authority["certification"]["certified"] is False
    assert authority["safety"] == {
        "prospective_observations_collected": 0,
        "persistent_strategy_collection_started": False,
        "real_stage_b_evaluation": False,
        "v2_corrected_hash_issued": False,
        "v2_certified": False,
        "postp1_003r3_authorized": False,
        "postp1_004_authorized": False,
        "collection_authorized": False,
        "btc019_reopened": False,
        "btc019_sealed_data_accessed": False,
        "epic_t_modified": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    authority = cal.authority_definition()
    children = cal._children()
    assert authority["material_child_count"] == len(cal._CHILD_ARTIFACTS)
    assert authority["material_child_count"] == len(children)
    assert authority["child_definition_sha256"] == {
        name: payload["definition_sha256"] for name, payload in children.items()
    }
    for payload in children.values():
        cal._verify_definition_digest(payload)
    cal.verify_authority_definition(authority)


def test_persisted_artifacts_restore_exactly() -> None:
    restored = cal.restore_artifacts(ARTIFACT_DIR)
    assert restored == cal.authority_definition()
    assert restored["definition_sha256"] == (
        "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9"
    )


def test_hash_is_stable_across_fresh_process_hash_seed_and_cwd(tmp_path) -> None:
    script = (
        "from btc_predictor.research.etf_publication_calendar import "
        "authority_definition; print(authority_definition()['definition_sha256'])"
    )
    outputs = []
    for seed, cwd in (("1", ROOT), ("987654", tmp_path)):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(ROOT)
        outputs.append(
            subprocess.check_output(
                [sys.executable, "-c", script],
                cwd=cwd,
                env=environment,
                text=True,
            ).strip()
        )
    assert outputs == [cal.authority_definition()["definition_sha256"]] * 2


def test_authority_hash_is_stable_across_cwd_hash_seed_and_fresh_process(tmp_path) -> None:
    command = [
        sys.executable,
        "-c",
        (
            "from btc_predictor.research.etf_publication_calendar import "
            "authority_definition; print(authority_definition()['definition_sha256'])"
        ),
    ]
    hashes = set()
    for seed, cwd in (("1", ROOT), ("777", tmp_path)):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(ROOT)
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        hashes.add(completed.stdout.strip())
    assert hashes == {cal.authority_definition()["definition_sha256"]}


def test_every_material_child_mutation_moves_the_top_hash(monkeypatch) -> None:
    baseline = cal.authority_definition()["definition_sha256"]
    for _, builder_name in cal._CHILD_ARTIFACTS:
        original = getattr(cal, builder_name)

        def mutated(original=original):
            payload = original()
            payload.pop("definition_sha256")
            payload["synthetic_mutation"] = builder_name
            return cal._definition(payload)

        with monkeypatch.context() as context:
            context.setattr(cal, builder_name, mutated)
            assert cal.authority_definition()["definition_sha256"] != baseline


def test_source_snapshot_binds_exact_bytes_not_a_mutable_url() -> None:
    first = cal.official_source_snapshot_record(
        venue_id="NYSE_ARCA",
        source_document_identity="https://official.example/calendar",
        source_bytes=b"version one",
        acquired_at=ACQUIRED,
        available_at=ACQUIRED,
    )
    second = cal.official_source_snapshot_record(
        venue_id="NYSE_ARCA",
        source_document_identity="https://official.example/calendar",
        source_bytes=b"version two",
        acquired_at=ACQUIRED,
        available_at=ACQUIRED,
    )
    assert first["source_document_sha256"] != second["source_document_sha256"]
    assert first["record_sha256"] != second["record_sha256"]


def test_schedule_and_resolution_are_invariant_to_input_order() -> None:
    forward = populated_store(exceptions=dict(HOLIDAYS_2026.items()))
    reverse = populated_store(exceptions=dict(reversed(tuple(HOLIDAYS_2026.items()))))
    day = date(2026, 11, 27)
    assert cal.common_etf_session_status(day, DECISION, forward) == (
        cal.common_etf_session_status(day, DECISION, reverse)
    )


def test_wrong_source_authority_is_refused() -> None:
    store = cal.CalendarEvidenceStore()
    source = cal.official_source_snapshot_record(
        venue_id="NYSE_ARCA",
        source_document_identity="official://nyse",
        source_bytes=b"source",
        acquired_at=ACQUIRED,
        available_at=ACQUIRED,
    )
    source.pop("record_sha256")
    source["source_authority_id"] = "NASDAQ_TRADER_US_EQUITIES_CALENDAR"
    forged = cal._record(source)
    store.put(forged)
    with pytest.raises(cal.EtfCalendarAuthorityError, match="wrong source authority"):
        cal.normalized_schedule_record(
            store,
            source_snapshot_sha256=forged["record_sha256"],
            coverage_start=date(2026, 1, 1),
            coverage_end=date(2026, 12, 31),
            exceptions={},
        )


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 11, 25), cal.EXPECTED),
        (date(2026, 11, 28), cal.NOT_EXPECTED),
        (date(2026, 11, 26), cal.NOT_EXPECTED),
        (date(2026, 11, 27), cal.EXPECTED),
        (date(2026, 12, 24), cal.EXPECTED),
    ],
)
def test_2026_official_calendar_sanity_cases_are_classified(day, expected) -> None:
    store = populated_store()
    assert cal.common_etf_session_status(day, DECISION, store).state == expected


def test_early_close_remains_open_at_each_venue() -> None:
    store = populated_store()
    states = {
        cal.venue_session_status(venue, date(2026, 11, 27), DECISION, store).state
        for venue in cal.CANONICAL_VENUES
    }
    assert states == {"OPEN_EARLY_CLOSE"}


def test_one_full_venue_closure_makes_resolved_common_date_not_expected() -> None:
    store = populated_store(exceptions={})
    add_revision(
        store,
        venue="CBOE_BZX",
        trade_date=date(2026, 8, 25),
        status="CLOSED",
        available_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    result = cal.common_etf_session_status(
        date(2026, 8, 25), datetime(2026, 8, 26, tzinfo=UTC), store
    )
    assert result.state == cal.NOT_EXPECTED


def test_omitting_one_required_venue_record_fails_closed() -> None:
    complete = populated_store(exceptions={})
    rows = [
        row
        for row in complete.records()
        if not (
            row.get("record_kind") == cal.VENUE_SESSION_RECORD_KIND
            and row.get("venue_id") == "NASDAQ"
            and row.get("trade_date") == "2026-08-25"
        )
    ]
    attacked = cal.CalendarEvidenceStore(rows)
    result = cal.common_etf_session_status(date(2026, 8, 25), DECISION, attacked)
    assert result.state == cal.UNRESOLVED
    assert dict(result.venue_states)["NASDAQ"] == cal.UNRESOLVED


def test_wrong_venue_and_trade_date_substitutions_do_not_fill_missing_row() -> None:
    store = populated_store(exceptions={})
    retained = [
        row
        for row in store.records()
        if not (
            row.get("record_kind") == cal.VENUE_SESSION_RECORD_KIND
            and row.get("venue_id") == "NASDAQ"
            and row.get("trade_date") == "2026-08-25"
        )
    ]
    attacked = cal.CalendarEvidenceStore(retained)
    # Existing rows for the wrong venue and adjacent trade dates cannot substitute.
    assert cal.common_etf_session_status(
        date(2026, 8, 25), DECISION, attacked
    ).state == cal.UNRESOLVED


def test_latest_pit_revision_wins_and_future_revision_does_not_leak() -> None:
    store = populated_store(exceptions={})
    day = date(2026, 8, 25)
    close_time = datetime(2026, 8, 20, tzinfo=UTC)
    reopen_time = datetime(2026, 8, 24, tzinfo=UTC)
    add_revision(store, venue="NYSE_ARCA", trade_date=day, status="CLOSED", available_at=close_time)
    add_revision(store, venue="NYSE_ARCA", trade_date=day, status="OPEN_REGULAR", available_at=reopen_time)
    assert cal.venue_session_status(
        "NYSE_ARCA", day, datetime(2026, 8, 22, tzinfo=UTC), store
    ).state == "CLOSED"
    assert cal.venue_session_status(
        "NYSE_ARCA", day, datetime(2026, 8, 25, tzinfo=UTC), store
    ).state == "OPEN_REGULAR"


def test_incompatible_latest_same_timestamp_revisions_are_unresolved() -> None:
    store = populated_store(exceptions={})
    day = date(2026, 8, 25)
    revision_time = datetime(2026, 8, 24, tzinfo=UTC)
    add_revision(store, venue="NASDAQ", trade_date=day, status="CLOSED", available_at=revision_time)
    add_revision(
        store,
        venue="NASDAQ",
        trade_date=day,
        status="OPEN_EARLY_CLOSE",
        available_at=revision_time,
    )
    result = cal.venue_session_status("NASDAQ", day, DECISION, store)
    assert result.state == cal.UNRESOLVED
    assert result.reason_codes == ("CONFLICTING_LATEST_CALENDAR_REVISION",)


def test_expected_date_range_distinguishes_closed_and_unresolved() -> None:
    store = populated_store()
    result = cal.expected_etf_publication_dates(
        date(2026, 11, 26), date(2026, 11, 29), DECISION, store
    )
    assert result.state == cal.RESOLVED
    assert result.expected_dates == (date(2026, 11, 27),)
    assert result.unresolved_dates == ()


def test_missing_next_year_calendar_is_unresolved_not_weekday_open() -> None:
    store = populated_store()
    result = cal.common_etf_session_status(date(2027, 1, 4), DECISION, store)
    assert result.state == cal.UNRESOLVED


def test_five_and_twenty_day_adapter_reproduce_exact_owner_dates() -> None:
    store = populated_store()
    end = date(2026, 12, 24)
    calendar = cal.derive_etf_window_calendar(
        end_date=end,
        earliest_date=date(2026, 11, 1),
        window_days=20,
        decision_time=DECISION,
        evidence_store=store,
    )
    assert calendar.state == cal.RESOLVED
    flows = tuple(flow_row(fund, day) for day in calendar.expected_dates for fund in ("IBIT", "FBTC"))
    for window_days in (5, 20):
        result = cal.scientific_etf_flow_window(
            flows,
            as_of=DECISION,
            funds=("IBIT", "FBTC"),
            end_date=end,
            earliest_date=date(2026, 11, 1),
            window_days=window_days,
            evidence_store=store,
        )
        assert result.evaluability_state == "EVALUABLE"
        assert result.feature is not None
        assert result.feature.included_observation_dates == result.calendar.expected_dates
        assert result.feature.window_days == window_days


def test_closed_date_is_not_missing_but_expected_missing_flow_is() -> None:
    store = populated_store()
    end = date(2026, 11, 27)
    calendar = cal.derive_etf_window_calendar(
        end_date=end,
        earliest_date=date(2026, 11, 1),
        window_days=5,
        decision_time=DECISION,
        evidence_store=store,
    )
    assert date(2026, 11, 26) in calendar.market_holidays
    rows = tuple(flow_row("IBIT", day) for day in calendar.expected_dates[:-1])
    result = cal.scientific_etf_flow_window(
        rows,
        as_of=DECISION,
        funds=("IBIT",),
        end_date=end,
        earliest_date=date(2026, 11, 1),
        window_days=5,
        evidence_store=store,
    )
    assert result.feature is not None
    assert result.feature.reason_codes == ("ETF_FLOW_INPUT_MISSING",)
    assert date(2026, 11, 26) not in result.feature.included_observation_dates


def test_unresolved_calendar_never_invokes_feature(monkeypatch) -> None:
    store = cal.CalendarEvidenceStore()

    def forbidden(*args, **kwargs):  # pragma: no cover - called only on defect
        raise AssertionError("feature owner was invoked with unresolved calendar")

    monkeypatch.setattr(flow, "etf_flow_window", forbidden)
    result = cal.scientific_etf_flow_window(
        (),
        as_of=DECISION,
        funds=("IBIT",),
        end_date=date(2026, 8, 25),
        earliest_date=date(2026, 8, 1),
        window_days=5,
        evidence_store=store,
    )
    assert result.evaluability_state == "NOT_EVALUABLE"
    assert result.feature is None
    assert result.reason_codes == ("ETF_PUBLICATION_CALENDAR_UNRESOLVED",)


def test_formula_lookbacks_and_flow_acceleration_remain_unchanged() -> None:
    adapter = cal.etf_feature_adapter_contract()
    assert adapter["window_days"] == {"ETF_FLOW_5D": 5, "ETF_FLOW_20D": 20}
    assert adapter["flow_accel_formula"] == "ETFNorm_5 - ETFNorm_20 / 4"
    assert adapter["formula_changed"] is False
    assert flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS == 5
    assert flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS == 20


def test_authority_completion_is_not_falsely_reported_as_zero_change() -> None:
    diff = cal.authority_completion_semantic_diff_contract()
    assert diff["v1"] == "UNOWNED INPUT"
    assert diff["v2"] == cal.AUTHORITY_VERSION
    assert diff["calendar_authority_row_forced_to_zero"] is False
    assert diff["etf_feature_formula_changed"] == 0
    assert diff["etf_lookbacks_changed"] == 0


def test_artifacts_restore_exactly() -> None:
    restored = cal.restore_artifacts(ARTIFACT_DIR)
    assert restored == cal.authority_definition()


def test_hash_is_invariant_to_hashseed_cwd_and_fresh_process(tmp_path) -> None:
    command = [
        sys.executable,
        "-c",
        "from btc_predictor.research.etf_publication_calendar import authority_definition; print(authority_definition()['definition_sha256'])",
    ]
    expected = cal.authority_definition()["definition_sha256"]
    for seed, cwd in (("1", ROOT), ("999", tmp_path)):
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = str(ROOT)
        completed = subprocess.run(
            command, cwd=cwd, env=environment, text=True, capture_output=True, check=True
        )
        assert completed.stdout.strip() == expected


def test_persisted_artifacts_are_canonical_json_objects() -> None:
    for filename, _ in cal._CHILD_ARTIFACTS:
        payload = json.loads((ARTIFACT_DIR / filename).read_text(encoding="ascii"))
        assert payload == cal._children()[filename.removesuffix(".json")]
