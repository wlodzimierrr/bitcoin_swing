"""RBT-001A: the replay builder extended to ``HISTORICAL_REPLAY_AVAILABILITY_V2``.

Synthetic fixtures only; no database, network or real-data value. Expected
availabilities and percentiles are computed here from the raw records and the
policy text, never read back from the builder.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import socket
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, Context, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.data import OpenInterest, aggregate_btc_derivatives_available_at
from btc_predictor.features.flow import CvdObservation
from btc_predictor.features.positioning import futures_basis_health, open_interest_intensity
from btc_predictor.research import prospective_integration_corpus as epic_x
from btc_predictor.research import us_equity_market_closures as closures
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest import replay_inputs_v2 as v2
from btc_predictor.research_backtest.entry_composer import EntryComposerInputs
from btc_predictor.tests import rbt001a_replay_fixtures as fx
from btc_predictor.tests.rbt001a_replay_fixtures import (
    BULK_INGESTED_AT,
    DAY,
    HOUR,
    MICROSECOND,
    OBSERVED,
    UNAVAILABLE,
    ZERO,
    basis_row,
    hour_evidence,
    liquidation_row,
    midnight,
    quarterly_expiry,
    utc,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "backtest_evidence" / "research_backtest_v1" / "rbt002_input_coverage_inventory_v1.json"
MARCH_2024 = quarterly_expiry(2024, 3)
JUNE_2024 = quarterly_expiry(2024, 6)


def build(**families: Any) -> v2.ExtendedReplaySnapshot:
    families.setdefault("shared_snapshot", fx.shared_snapshot())
    return v2.build_extended_replay_snapshot(**families)


def assert_refused(reason: str, **families: Any) -> v1.ReplayInputRefused:
    with pytest.raises(v1.ReplayInputRefused) as caught:
        build(**families)
    assert caught.value.reason_code == reason, str(caught.value)
    return caught.value


def inventory_rows() -> list[dict[str, Any]]:
    return json.loads(INVENTORY.read_text())["input_surface"]["rows"]


# --- versions, shapes and declared inputs ---------------------------------------------------


def test_every_classified_raw_and_discretionary_family_has_its_inventory_shape() -> None:
    rows = [row for row in inventory_rows() if row["kind"] in ("RAW_HISTORICAL", "DISCRETIONARY")]
    single = {}
    for row in rows:
        if len(row["families"]) == 1:
            single.setdefault(row["families"][0], set()).add(row["shape"])
    assert all(len(shapes) == 1 for shapes in single.values()), single
    assert {family: shapes.pop() for family, shapes in single.items()} == dict(v2.REPLAY_SHAPES_V2)
    # a multi-family row (the data-quality owner's rows) names only families in the table
    assert {family for row in rows for family in row["families"]} == set(v2.REPLAY_SHAPES_V2)


def test_the_discretionary_and_unsourceable_inputs_are_the_inventorys() -> None:
    rows = inventory_rows()
    assert set(v2.DISCRETIONARY_INPUTS) == {row["input_id"] for row in rows if row["kind"] == "DISCRETIONARY"}
    assert set(v2.UNSOURCEABLE_INPUTS) == {row["input_id"] for row in rows if row["kind"] == "ABSENT_RULEBOOK_FALLBACK"}


def test_the_v1_builder_and_its_versions_are_unchanged() -> None:
    assert v1.REPLAY_INPUTS_BUILDER_VERSION == "BUILD_HISTORICAL_REPLAY_INPUTS_V1"
    assert v1.REPLAY_AVAILABILITY_POLICY_VERSION == "HISTORICAL_REPLAY_AVAILABILITY_V1"
    assert v1.RESEARCH_BACKTEST_POLICY_VERSION == "RESEARCH_BACKTEST_POLICY_V2"
    assert set(v1.REPLAY_AVAILABILITY_RULES) == set(v1.SHARED_SNAPSHOT_FAMILIES) | {v1.REFERENCE_PRICE_FAMILY}
    assert v2.REPLAY_V2_REFUSAL_REASON_CODES[: len(v1.REPLAY_REFUSAL_REASON_CODES)] == v1.REPLAY_REFUSAL_REASON_CODES
    # the V1 builder still has no parameter for the families V2 adds
    assert not {"futures_basis", "market_caps", "liquidations"} & set(v1.build_shared_replay_snapshot.__kwdefaults__)


def test_a_v2_refusal_is_a_v1_refusal_with_a_closed_code_set() -> None:
    refusal = v2.ExtendedReplayInputRefused("FUTURES_BASIS_CONTRACT_REFUSED", "x")
    assert isinstance(refusal, v1.ReplayInputRefused) and refusal.reason_code == "FUTURES_BASIS_CONTRACT_REFUSED"
    with pytest.raises(ValueError, match="undeclared"):
        v2.ExtendedReplayInputRefused("NOT_A_CODE", "x")
    with pytest.raises(ValueError, match="undeclared"):
        v1.ReplayInputRefused("FUTURES_BASIS_CONTRACT_REFUSED", "x")


def test_the_missing_value_codes_are_the_frozen_adapter_contracts() -> None:
    contract = json.dumps(epic_x.prospective_liquidation_percentile_adapter_contract())
    assert v2.LIQUIDATION_FEED_UNAVAILABLE in contract
    assert v2.LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY in contract
    assert v2.LIQUIDATION_PERCENTILE_CONVENTION_OWNER in epic_x.LIQUIDATION_PERCENTILE_CONVENTION_OWNERS


# --- the closure table ---------------------------------------------------------------------


def test_the_shared_snapshot_must_count_etf_gaps_with_the_closure_table() -> None:
    plain = v1.build_shared_replay_snapshot(window=v1.DATA_WINDOW)
    assert_refused("CLOSURE_TABLE_REQUIRED", shared_snapshot=plain)
    partial = v1.build_shared_replay_snapshot(
        window=v1.DATA_WINDOW, etf_market_holidays=closures.load_closures(date(2024, 1, 1), date(2024, 12, 31))
    )
    assert_refused("CLOSURE_TABLE_REQUIRED", shared_snapshot=partial)
    record = build().manifest["closure_table"]
    assert record == {
        "table_version": closures.TABLE_VERSION,
        "definition_sha256": closures.DEFINITION_SHA256,
        "closure_table_file_sha256": closures.CLOSURE_TABLE_FILE_SHA256,
        "coverage_start": "2023-01-01",
        "coverage_end": "2026-12-31",
        "closure_count": len(fx.closure_holidays()),
    }


# --- futures basis ---------------------------------------------------------------------------


def test_a_basis_snapshot_is_available_at_its_hour_close_and_keeps_its_raw_times() -> None:
    t = utc(2024, 2, 1, 13)
    row = basis_row(t, MARCH_2024)
    snapshot = build(futures_basis=[row])
    (copy,) = snapshot.futures_basis
    assert copy == replace(row, available_at=t)
    (entry,) = snapshot.availability
    assert entry.modelled_available_at == entry.observation_end == t
    assert dict(entry.raw_times) == {"available_at": BULK_INGESTED_AT, "ingested_at": BULK_INGESTED_AT}
    assert dict(entry.identity)["expiry"] == MARCH_2024.isoformat()


def test_the_contract_annualisation_matches_an_independent_computation() -> None:
    t = utc(2024, 2, 1, 13)
    rate = Decimal("0.012345678901234567")
    seconds = int((MARCH_2024 - t).total_seconds())
    assert seconds == (57 * 24 - 5) * 3600  # 2024 is a leap year
    assert v2.contract_annualized_basis_rate(rate, t, MARCH_2024) == fx.annualized(rate, t, MARCH_2024)
    off = basis_row(t, MARCH_2024, rate)
    off = replace(off, annualized_basis_rate=off.annualized_basis_rate + Decimal("1e-18"))
    assert_refused("FUTURES_BASIS_CONTRACT_REFUSED", futures_basis=[off])


def test_a_contract_within_seven_days_of_expiry_is_excluded_and_recorded() -> None:
    at_seven = MARCH_2024 - 7 * DAY
    before = at_seven - HOUR
    rows = [basis_row(at_seven, MARCH_2024), basis_row(at_seven, JUNE_2024), basis_row(before, MARCH_2024)]
    snapshot = build(futures_basis=rows)
    assert [(row.observation_time, row.expiry) for row in snapshot.futures_basis] == [
        (before, MARCH_2024),
        (at_seven, JUNE_2024),
    ]
    (excluded,) = snapshot.excluded_futures_basis
    assert excluded.row == rows[0] and excluded.reason_code == v2.FUTURES_BASIS_WITHIN_7D_OF_EXPIRY
    section = snapshot.manifest["families"][v2.FUTURES_BASIS_FAMILY]
    assert section["excluded_count"] == 1
    assert section["excluded"][0]["time_to_expiry_seconds"] == 7 * 86_400
    assert section["excluded"][0]["reason_code"] == v2.FUTURES_BASIS_WITHIN_7D_OF_EXPIRY
    # the owner averages every row sharing an instant; the excluded row never reaches it
    health = futures_basis_health(snapshot.futures_basis, as_of=at_seven)
    assert health.observation_time == at_seven and health.source_record_count == 2
    assert health.annualized_basis_rate_avg == rows[1].annualized_basis_rate


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda row: replace(row, observation_time=row.observation_time + timedelta(minutes=30), annualized_basis_rate=fx.annualized(row.basis_rate, row.observation_time + timedelta(minutes=30), row.expiry)), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: replace(row, exchange="kraken"), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: replace(row, symbol="BTCUSDT"), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: replace(row, instrument="BTCUSD_PERP"), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: basis_row(row.observation_time, utc(2024, 4, 26, 8)), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: basis_row(utc(2024, 3, 29, 8), MARCH_2024, annualized_basis_rate=Decimal("0")), "FUTURES_BASIS_CONTRACT_REFUSED"),
        (lambda row: basis_row(utc(2019, 12, 31, 23), quarterly_expiry(2020, 3)), "PRE_2020_RECORD_REFUSED"),
        (lambda row: basis_row(utc(2026, 1, 2), quarterly_expiry(2026, 3)), "HOLDOUT_RECORD_REFUSED"),
        (lambda row: replace(row, basis_rate=Decimal("NaN")), "RECORD_TYPE_REFUSED"),
    ],
    ids=["off-hour", "exchange", "symbol", "instrument", "not-quarterly", "delivered", "pre-2020", "holdout", "nan"],
)
def test_a_basis_row_breaking_the_contract_is_refused(change: Any, reason: str) -> None:
    assert_refused(reason, futures_basis=[change(basis_row(utc(2024, 2, 1, 13), MARCH_2024))])


def test_a_duplicate_basis_row_is_refused_even_when_excluded() -> None:
    row = basis_row(MARCH_2024 - 2 * DAY, MARCH_2024)
    assert_refused("DUPLICATE_RECORD_REFUSED", futures_basis=[row, replace(row, ingested_at=row.ingested_at + HOUR)])


def test_an_unsourceable_record_is_refused_not_approximated() -> None:
    cvd = CvdObservation(observation_time=utc(2024, 2, 1), market_type="spot", cvd_usd=Decimal("1"), provider="x", available_at=utc(2024, 2, 1))
    assert_refused("UNSOURCEABLE_INPUT_REFUSED", futures_basis=[cvd])
    assert_refused("UNSOURCEABLE_INPUT_REFUSED", liquidations=[cvd])
    assert_refused("UNSOURCEABLE_INPUT_REFUSED", liquidation_hours=[cvd])
    assert_refused("UNSOURCEABLE_INPUT_REFUSED", market_cap_evidence=cvd)
    other = OpenInterest(utc(2024, 2, 1), "binance", "BTCUSDT", "BTC-PERP", Decimal("1"), "USD", "p", "s", utc(2024, 2, 1), utc(2024, 2, 1))
    assert_refused("RECORD_TYPE_REFUSED", futures_basis=[other])


def test_basis_gaps_count_hours_with_no_kept_contract() -> None:
    rows = [row for row in fx.basis_rows(utc(2024, 2, 1), utc(2024, 2, 2)) if row.observation_time != utc(2024, 2, 1, 5)]
    section = build(futures_basis=rows).manifest["families"][v2.FUTURES_BASIS_FAMILY]
    assert (section["gap_count"], section["missing_slot_count"]) == (1, 1)


# A caller may run the builder under any decimal context: the default (review
# F3's reproducer), a narrow one that rounds down, or one that traps nothing.
CALLER_CONTEXTS = {
    "default": Context(prec=28),
    "narrow": Context(prec=5, rounding=ROUND_DOWN),
    "untrapped": Context(prec=3, rounding=ROUND_CEILING, traps=[]),
}


def exactly(operation: Any) -> Decimal:
    with localcontext(Context(prec=80)):
        return operation()


@pytest.mark.parametrize("name", sorted(CALLER_CONTEXTS))
def test_a_valid_raw_row_is_checked_in_the_builders_own_decimal_context(name: str) -> None:
    """Review F3: a valid NUMERIC(38,18) row is accepted, and a one-unit error refused, under any caller context."""

    t = utc(2024, 2, 1, 13)
    row = basis_row(t, MARCH_2024, Decimal("100000000000"))
    assert len(row.annualized_basis_rate.as_tuple().digits) > 28  # beyond the default precision
    off = replace(row, annualized_basis_rate=exactly(lambda: row.annualized_basis_rate + Decimal("1e-18")))
    shared = fx.shared_snapshot()
    reference = build(shared_snapshot=shared, futures_basis=[row]).manifest_bytes
    with localcontext(CALLER_CONTEXTS[name]):
        assert build(shared_snapshot=shared, futures_basis=[row]).manifest_bytes == reference
        with pytest.raises(v1.ReplayInputRefused) as caught:
            build(shared_snapshot=shared, futures_basis=[off])
    assert caught.value.reason_code == "FUTURES_BASIS_CONTRACT_REFUSED"


@pytest.mark.parametrize(
    "change",
    [
        lambda row: basis_row(row.observation_time, row.expiry, Decimal("0.0123456789012345678")),
        lambda row: basis_row(row.observation_time, row.expiry, Decimal("1e20")),
        lambda row: replace(row, annualized_basis_rate=exactly(lambda: row.annualized_basis_rate + Decimal("1e-19"))),
    ],
    ids=["basis-19-places", "basis-21-digits", "annualized-19-places"],
)
def test_a_basis_value_the_raw_table_cannot_hold_is_refused(change: Any) -> None:
    """Ruling 6 reads the stored 18-place rate; an unpersistable value is no row (the 19th place was once accepted)."""

    assert_refused("RECORD_TYPE_REFUSED", futures_basis=[change(basis_row(utc(2024, 2, 1, 13), MARCH_2024))])


def test_trailing_zeros_beyond_18_places_still_fit_the_raw_table() -> None:
    row = basis_row(utc(2024, 2, 1, 13), MARCH_2024, Decimal("0.012300000000000000000"))
    assert row.basis_rate.as_tuple().exponent == -21
    assert build(futures_basis=[row]).futures_basis[0].basis_rate == Decimal("0.0123")


# --- market cap --------------------------------------------------------------------------------


def test_a_market_cap_for_day_d_is_stamped_d_plus_1_and_available_d_plus_2() -> None:
    evidence = fx.market_cap_evidence(date(2024, 2, 1), date(2024, 2, 3))
    snapshot = build(market_cap_evidence=evidence)
    assert [(cap.observation_time, cap.available_at) for cap in snapshot.market_caps] == [
        (utc(2024, 2, 2), utc(2024, 2, 3)),
        (utc(2024, 2, 3), utc(2024, 2, 4)),
        (utc(2024, 2, 4), utc(2024, 2, 5)),
    ]
    assert [cap.market_cap_usd for cap in snapshot.market_caps] == [value for _, value in evidence.rows]
    assert {cap.provider for cap in snapshot.market_caps} == {v2.MARKET_CAP_PROVIDER}
    assert all(v1.REVISION_HISTORY_UNAVAILABLE in entry.labels for entry in snapshot.availability)
    section = snapshot.manifest["families"][v2.BTC_MARKET_CAP_FAMILY]
    assert section["evidence"]["file_sha256"] == evidence.file_sha256 and section["evidence"]["row_count"] == 3


def test_the_market_cap_days_admitted_are_the_data_windows() -> None:
    edges = build(market_cap_evidence=fx.market_cap_evidence(date(2020, 1, 1), date(2020, 1, 1))).market_caps
    assert [(cap.observation_time, cap.available_at) for cap in edges] == [(utc(2020, 1, 2), utc(2020, 1, 3))]
    last = build(market_cap_evidence=fx.market_cap_evidence(date(2025, 12, 31), date(2025, 12, 31))).market_caps
    assert [(cap.observation_time, cap.available_at) for cap in last] == [(utc(2026, 1, 1), utc(2026, 1, 2))]
    assert_refused("PRE_2020_RECORD_REFUSED", market_cap_evidence=fx.market_cap_evidence(date(2019, 12, 31), date(2019, 12, 31)))
    assert_refused("HOLDOUT_RECORD_REFUSED", market_cap_evidence=fx.market_cap_evidence(date(2026, 1, 1), date(2026, 1, 1)))


def evidence_variants() -> list[tuple[str, bytes, str | None]]:
    rows = fx.market_cap_rows(date(2024, 2, 1), date(2024, 2, 3))
    good = fx.market_cap_bytes(rows)
    payload = json.loads(good)
    variants = [
        ("pretty", json.dumps(payload, indent=1, sort_keys=True).encode(), None),
        ("extra-key", v1.canonical_json_bytes({**payload, "note": "x"}), None),
        ("provider", v1.canonical_json_bytes({**payload, "provider": "coingecko"}), None),
        ("metric", v1.canonical_json_bytes({**payload, "metric": "CapRealUSD"}), None),
        ("zero", v1.canonical_json_bytes({**payload, "rows": [{"date": "2024-02-01", "market_cap_usd": "0"}]}), None),
        ("scale", v1.canonical_json_bytes({**payload, "rows": [{"date": "2024-02-01", "market_cap_usd": "100.0"}]}), None),
        ("duplicate", v1.canonical_json_bytes({**payload, "rows": [payload["rows"][0], payload["rows"][0]]}), None),
        ("unsorted", v1.canonical_json_bytes({**payload, "rows": payload["rows"][::-1]}), None),
        ("retrieved", v1.canonical_json_bytes({**payload, "retrieved_at": "yesterday"}), None),
        ("responses", v1.canonical_json_bytes({**payload, "response_sha256": []}), None),
        ("digest", good, "0" * 64),
    ]
    return variants


@pytest.mark.parametrize("name", [name for name, _, _ in evidence_variants()])
def test_a_malformed_or_unbound_market_cap_evidence_file_is_refused(name: str) -> None:
    _, data, bound = next(item for item in evidence_variants() if item[0] == name)
    with pytest.raises(v1.ReplayInputRefused) as caught:
        v2.parse_market_cap_evidence(data, expected_sha256=bound or hashlib.sha256(data).hexdigest())
    assert caught.value.reason_code == "MARKET_CAP_EVIDENCE_REFUSED"


def _redigested(evidence: v2.MarketCapEvidence, **changes: Any) -> v2.MarketCapEvidence:
    """``changes`` applied with ``file_sha256`` set to the digest of the changed record's own bytes."""

    changed = replace(evidence, **changes)
    data = fx.market_cap_bytes(changed.rows, source=changed.source, licence=changed.licence, retrieved_at=changed.retrieved_at, response_sha256=changed.response_sha256)
    return replace(changed, file_sha256=hashlib.sha256(data).hexdigest())


EVIDENCE_CHANGED_AFTER_PARSING = {
    "value": lambda e: replace(e, rows=((e.rows[0][0], Decimal("1")), *e.rows[1:])),
    "dropped-day": lambda e: replace(e, rows=e.rows[:-1]),
    "added-day": lambda e: replace(e, rows=(*e.rows, (e.rows[-1][0] + DAY, e.rows[-1][1]))),
    "source": lambda e: replace(e, source="https://example.invalid/caps"),
    "retrieved-at": lambda e: replace(e, retrieved_at=e.retrieved_at + HOUR),
    "responses": lambda e: replace(e, response_sha256=(fx.digest("other"),)),
    "digest-malformed": lambda e: replace(e, file_sha256="not-a-digest"),
    "digest-uppercase": lambda e: replace(e, file_sha256=e.file_sha256.upper()),
    "digest-other": lambda e: replace(e, file_sha256="0" * 64),
    "value-type": lambda e: replace(e, rows=((e.rows[0][0], float(e.rows[0][1])), *e.rows[1:])),
    "retrieved-type": lambda e: replace(e, retrieved_at="2026-10-02T12:00:00+00:00"),
    "duplicate-redigested": lambda e: _redigested(e, rows=(*e.rows, e.rows[-1])),
    "unsorted-redigested": lambda e: _redigested(e, rows=e.rows[::-1]),
    "zero-redigested": lambda e: _redigested(e, rows=((e.rows[0][0], Decimal("0")), *e.rows[1:])),
    "no-responses-redigested": lambda e: _redigested(e, response_sha256=()),
}


@pytest.mark.parametrize("name", sorted(EVIDENCE_CHANGED_AFTER_PARSING))
def test_market_cap_evidence_changed_after_parsing_is_refused(name: str) -> None:
    """Review F1: admission re-verifies the whole record against its file digest."""

    evidence = fx.market_cap_evidence(date(2024, 2, 1), date(2024, 2, 5))
    assert build(market_cap_evidence=evidence).market_caps
    assert_refused("MARKET_CAP_EVIDENCE_REFUSED", market_cap_evidence=EVIDENCE_CHANGED_AFTER_PARSING[name](evidence))


def test_a_self_consistent_redigested_record_is_a_different_bound_file() -> None:
    """A changed record carrying its own new digest is admitted as that file, and the manifest names it."""

    evidence = fx.market_cap_evidence(date(2024, 2, 1), date(2024, 2, 5))
    other = _redigested(evidence, rows=((evidence.rows[0][0], Decimal("1")), *evidence.rows[1:]))
    snapshot = build(market_cap_evidence=other)
    assert snapshot.market_caps[0].market_cap_usd == Decimal("1")
    assert snapshot.manifest["families"][v2.BTC_MARKET_CAP_FAMILY]["evidence"]["file_sha256"] == other.file_sha256 != evidence.file_sha256


def test_market_cap_evidence_loads_from_its_file(tmp_path: Path) -> None:
    data = fx.market_cap_bytes(fx.market_cap_rows(date(2024, 2, 1), date(2024, 2, 3)))
    path = tmp_path / "btc_market_cap_evidence_v1.json"
    path.write_bytes(data)
    evidence = v2.load_market_cap_evidence(path, expected_sha256=hashlib.sha256(data).hexdigest())
    assert evidence.file_sha256 == hashlib.sha256(data).hexdigest() and len(evidence.rows) == 3
    assert evidence.retrieved_at == fx.RETRIEVED_AT


def test_oi_intensity_sees_day_ds_market_cap_only_from_d_plus_2() -> None:
    day = date(2024, 2, 10)
    snapshot = build(market_cap_evidence=fx.market_cap_evidence(day, day))
    oi = tuple(replace(row, available_at=row.observation_time) for row in fx.open_interest(utc(2024, 2, 11), utc(2024, 2, 13)))
    before = open_interest_intensity(oi, snapshot.market_caps, as_of=utc(2024, 2, 12) - MICROSECOND, open_interest_unit="USD")
    at = open_interest_intensity(oi, snapshot.market_caps, as_of=utc(2024, 2, 12), open_interest_unit="USD")
    assert (before.market_cap_record_count, at.market_cap_record_count) == (0, 1)


# --- liquidations ----------------------------------------------------------------------------


def test_a_liquidation_hour_is_available_at_its_end() -> None:
    hour = utc(2024, 2, 1, 13)
    rows = [liquidation_row(hour, "long", Decimal("1500")), liquidation_row(hour, "short", Decimal("0"))]
    snapshot = build(liquidations=rows, liquidation_hours=[hour_evidence(hour)])
    assert [copy.available_at for copy in snapshot.liquidations] == [hour + HOUR, hour + HOUR]
    assert [replace(copy, available_at=BULK_INGESTED_AT) for copy in snapshot.liquidations] == rows
    assert {entry.modelled_available_at for entry in snapshot.availability} == {hour + HOUR}
    for at, count in ((hour + HOUR - MICROSECOND, 0), (hour + HOUR, 2)):
        assert aggregate_btc_derivatives_available_at(list(snapshot.liquidations), at).source_record_count == count


HOUR_AT = utc(2024, 2, 1, 13)


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        (liquidation_row(HOUR_AT, "long", Decimal("1"), exchange="binance"), "LIQUIDATION_UNIVERSE_REFUSED"),
        (liquidation_row(HOUR_AT, "long", Decimal("1"), symbol="PF_XBTUSD"), "LIQUIDATION_UNIVERSE_REFUSED"),
        (liquidation_row(HOUR_AT, "long", Decimal("1"), timeframe="5m"), "LIQUIDATION_UNIVERSE_REFUSED"),
        (liquidation_row(HOUR_AT, "buy", Decimal("1")), "LIQUIDATION_UNIVERSE_REFUSED"),
        (liquidation_row(HOUR_AT + timedelta(minutes=5), "long", Decimal("1")), "LIQUIDATION_UNIVERSE_REFUSED"),
        (liquidation_row(HOUR_AT, "long", None), "LIQUIDATION_NOTIONAL_MISSING"),
        (liquidation_row(HOUR_AT, "long", Decimal("-1")), "RECORD_TYPE_REFUSED"),
        (liquidation_row(HOUR_AT + HOUR, "long", Decimal("1")), "LIQUIDATION_HOUR_EVIDENCE_MISSING"),
        (liquidation_row(utc(2019, 12, 31, 23), "long", Decimal("1")), "PRE_2020_RECORD_REFUSED"),
        (liquidation_row(utc(2026, 1, 1), "long", Decimal("1")), "HOLDOUT_RECORD_REFUSED"),
        (liquidation_row(HOUR_AT, "long", Decimal("1.0000000000000000001")), "RECORD_TYPE_REFUSED"),
        (liquidation_row(HOUR_AT, "long", Decimal("1e20")), "RECORD_TYPE_REFUSED"),
        (liquidation_row(HOUR_AT, "long", Decimal("1"), quantity=Decimal("0.0000000000000000001")), "RECORD_TYPE_REFUSED"),
    ],
    ids=[
        "exchange", "symbol", "timeframe", "side", "off-hour", "no-notional", "negative", "no-evidence", "pre-2020", "holdout",
        "notional-19-places", "notional-21-digits", "quantity-19-places",
    ],
)
def test_a_liquidation_row_outside_the_contract_is_refused(row: Any, reason: str) -> None:
    assert_refused(reason, liquidations=[row], liquidation_hours=[hour_evidence(HOUR_AT)])


def test_a_duplicate_liquidation_side_or_hour_is_refused() -> None:
    row = liquidation_row(HOUR_AT, "long", Decimal("1"))
    assert_refused("DUPLICATE_RECORD_REFUSED", liquidations=[row, replace(row, provider="other")], liquidation_hours=[hour_evidence(HOUR_AT)])
    assert_refused("DUPLICATE_RECORD_REFUSED", liquidations=[row], liquidation_hours=[hour_evidence(HOUR_AT), hour_evidence(HOUR_AT)])


@pytest.mark.parametrize(
    ("evidence", "reason"),
    [
        (hour_evidence(HOUR_AT, OBSERVED, v2.CORROBORATION_DISAGREES), "LIQUIDATION_CORROBORATION_DISAGREES"),
        (hour_evidence(HOUR_AT, ZERO, v2.CORROBORATION_DISAGREES), "LIQUIDATION_CORROBORATION_DISAGREES"),
        (hour_evidence(HOUR_AT, OBSERVED, v2.CORROBORATION_SERIES_UNAVAILABLE), "LIQUIDATION_CORROBORATION_UNAVAILABLE"),
        (hour_evidence(HOUR_AT, OBSERVED, v2.CORROBORATION_NOT_APPLICABLE), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(HOUR_AT, UNAVAILABLE, v2.CORROBORATION_AGREES), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(HOUR_AT, epic_x.FEED_STATUS_LATE), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(HOUR_AT, epic_x.FEED_STATUS_INVALID), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(HOUR_AT, OBSERVED, "ROUGHLY"), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (replace(hour_evidence(HOUR_AT), evidence_sha256="abc"), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(HOUR_AT + timedelta(minutes=1)), "LIQUIDATION_HOUR_EVIDENCE_REFUSED"),
        (hour_evidence(utc(2026, 1, 1)), "HOLDOUT_RECORD_REFUSED"),
    ],
    ids=["disagrees", "zero-disagrees", "series-unavailable", "observed-not-applicable", "unavailable-agrees", "late", "invalid", "unknown-result", "digest", "off-hour", "holdout"],
)
def test_hour_evidence_that_cannot_show_completeness_is_refused(evidence: v2.LiquidationHourEvidence, reason: str) -> None:
    """Owner ruling 2: an hour that disagrees with Kraken's hourly series refuses the build."""

    assert_refused(reason, liquidation_hours=[evidence])


@pytest.mark.parametrize(
    ("status", "notionals", "accepted"),
    [
        (OBSERVED, ("1500",), True),
        (OBSERVED, (), False),
        (OBSERVED, ("0", "0"), False),
        (ZERO, (), True),
        (ZERO, ("0",), True),
        (ZERO, ("1",), False),
        (UNAVAILABLE, (), True),
        (UNAVAILABLE, ("0",), False),
    ],
)
def test_the_hour_status_must_agree_with_its_rows(status: str, notionals: tuple[str, ...], accepted: bool) -> None:
    rows = [liquidation_row(HOUR_AT, side, Decimal(value)) for side, value in zip(v2.LIQUIDATION_SIDES, notionals, strict=False)]
    families = {"liquidations": rows, "liquidation_hours": [hour_evidence(HOUR_AT, status)]}
    if accepted:
        build(**families)
    else:
        assert_refused("LIQUIDATION_HOUR_STATUS_INCONSISTENT", **families)


# --- LIQUIDATION_PERCENTILE --------------------------------------------------------------------

FIRST_DAY = date(2022, 1, 1)
LAST_DAY = date(2024, 3, 10)
UNAVAILABLE_HOUR = utc(2022, 6, 1, 3)
MISSING_HOUR = utc(2023, 4, 5, 22)
ZERO_DAY = date(2022, 9, 9)


@pytest.fixture(scope="module")
def history() -> fx.LiquidationHistory:
    return fx.liquidation_history(
        FIRST_DAY, LAST_DAY, unavailable_hours=[UNAVAILABLE_HOUR], missing_hours=[MISSING_HOUR], zero_days=[ZERO_DAY]
    )


@pytest.fixture(scope="module")
def liquidity(history: fx.LiquidationHistory) -> v2.ExtendedReplaySnapshot:
    return build(liquidations=history.rows, liquidation_hours=history.hours)


def oracle_totals(history: fx.LiquidationHistory) -> dict[date, Decimal | None]:
    """Each day's long-plus-short USD, or None unless all 24 hours are observed."""

    observed: dict[date, int] = {}
    for hour in history.hours:
        if hour.feed_status in (OBSERVED, ZERO):
            observed[hour.hour_start.date()] = observed.get(hour.hour_start.date(), 0) + 1
    totals: dict[date, Decimal | None] = {}
    day = history.first
    while day <= history.last:
        totals[day] = Decimal("0") if observed.get(day) == 24 else None
        day += DAY
    for row in history.rows:
        if totals[row.observation_time.date()] is not None:
            totals[row.observation_time.date()] += row.notional_usd  # type: ignore[operator]
    return totals


def midrank(value: Decimal, history: list[Decimal]) -> Decimal:
    below = sum(1 for item in history if item < value)
    equal = sum(1 for item in history if item == value)
    return (Decimal(below) + Decimal("0.5") * Decimal(equal)) / Decimal(len(history)) * Decimal(100)


def test_each_day_is_one_observation_available_at_its_end(liquidity: v2.ExtendedReplaySnapshot) -> None:
    days = liquidity.liquidation_percentiles
    assert [item.observation_date for item in days] == [FIRST_DAY + index * DAY for index in range((LAST_DAY - FIRST_DAY).days + 1)]
    assert all(item.available_at == midnight(item.observation_date) + DAY for item in days)


def test_the_percentiles_equal_an_independent_oracle(history: fx.LiquidationHistory, liquidity: v2.ExtendedReplaySnapshot) -> None:
    totals = oracle_totals(history)
    complete = [(day, total) for day, total in sorted(totals.items()) if total is not None]
    valued = 0
    for item in liquidity.liquidation_days:
        day = item.observation_date
        if totals[day] is None:
            assert item.observation.liquidation_percentile is None
            assert item.observation.reason_codes == (v2.LIQUIDATION_FEED_UNAVAILABLE,)
            continue
        prior = [total for other, total in complete if day - timedelta(days=730) <= other < day]
        assert item.daily_notional_usd == totals[day] and item.history_observation_count == len(prior)
        if len(prior) < 365:
            assert item.observation.liquidation_percentile is None
            assert item.observation.reason_codes == (v2.LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY,)
        else:
            assert item.observation.liquidation_percentile == midrank(totals[day], prior)  # type: ignore[arg-type]
            assert item.observation.reason_codes == ()
            valued += 1
    assert valued > 400


def test_the_daily_total_is_exact_at_the_raw_tables_scale() -> None:
    """Review F3: 38-digit notionals sum exactly, though their total exceeds the default precision."""

    day = date(2024, 2, 1)
    hours = fx.liquidation_history(day, day, notional_at=lambda index, side: Decimal(f"{12345678901234567000 + 2 * index + (side == 'long')}.123456789012345678"))
    assert all(len(row.notional_usd.as_tuple().digits) == 38 for row in hours.rows)
    (only,) = build(liquidations=hours.rows, liquidation_hours=hours.hours).liquidation_days
    exact = sum((Fraction(row.notional_usd) for row in hours.rows), Fraction(0))
    assert len(only.daily_notional_usd.as_tuple().digits) > 28  # type: ignore[union-attr]
    assert Fraction(only.daily_notional_usd) == exact  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["narrow", "untrapped"])
def test_no_daily_total_or_percentile_depends_on_the_callers_decimal_context(
    name: str, history: fx.LiquidationHistory, liquidity: v2.ExtendedReplaySnapshot
) -> None:
    """Review F3: the percentile runs under the stated default context, so a caller's context changes nothing."""

    shared = fx.shared_snapshot()
    with localcontext(CALLER_CONTEXTS[name]):
        again = build(shared_snapshot=shared, liquidations=history.rows, liquidation_hours=history.hours)
    assert again.manifest_bytes == liquidity.manifest_bytes
    assert any(len(item.observation.liquidation_percentile.as_tuple().digits) > 5 for item in again.liquidation_days if item.observation.liquidation_percentile is not None)


def test_an_incomplete_day_has_no_value_and_enters_no_history(liquidity: v2.ExtendedReplaySnapshot) -> None:
    by_day = {item.observation_date: item for item in liquidity.liquidation_days}
    for day in (UNAVAILABLE_HOUR.date(), MISSING_HOUR.date()):
        assert (by_day[day].complete, by_day[day].daily_notional_usd) == (False, None)
        assert by_day[day].observation.reason_codes == (v2.LIQUIDATION_FEED_UNAVAILABLE,)
    # the last day's window holds 730 days, two of them incomplete
    assert LAST_DAY - 730 * DAY <= UNAVAILABLE_HOUR.date() < MISSING_HOUR.date() < LAST_DAY
    assert by_day[LAST_DAY].history_observation_count == 728


def test_the_first_value_needs_365_prior_complete_days(liquidity: v2.ExtendedReplaySnapshot) -> None:
    complete = [item for item in liquidity.liquidation_days if item.complete]
    assert [item.observation.liquidation_percentile is None for item in complete[:365]] == [True] * 365
    first_valued = complete[365]
    assert first_valued.history_observation_count == 365 and first_valued.observation.liquidation_percentile is not None
    # the incomplete 2022-06-01 shifts the first value one day later
    assert first_valued.observation_date == date(2023, 1, 2)


def test_an_observed_zero_event_day_enters_history_as_zero(liquidity: v2.ExtendedReplaySnapshot) -> None:
    by_day = {item.observation_date: item for item in liquidity.liquidation_days}
    assert (by_day[ZERO_DAY].complete, by_day[ZERO_DAY].daily_notional_usd) == (True, Decimal("0"))
    # it is one of the complete days a later window counts (the oracle test checks the values)
    later = by_day[ZERO_DAY + 400 * DAY]
    window = [item for item in liquidity.liquidation_days if later.observation_date - 730 * DAY <= item.observation_date < later.observation_date]
    assert later.history_observation_count == sum(1 for item in window if item.complete)
    assert any(item.observation_date == ZERO_DAY for item in window)


def test_the_window_is_half_open_over_the_730_prior_days(history: fx.LiquidationHistory) -> None:
    target = date(2024, 2, 1)
    edge, outside = target - 730 * DAY, target - 731 * DAY

    def percentile_with(day: date, notional: Decimal) -> Decimal | None:
        rows = tuple(
            replace(row, notional_usd=notional, quantity=notional) if row.observation_time.date() == day else row
            for row in history.rows
        )
        snapshot = build(liquidations=rows, liquidation_hours=history.hours)
        return next(item for item in snapshot.liquidation_days if item.observation_date == target).observation.liquidation_percentile

    # move a window day from below to above the target's total: only a day inside the window matters
    assert percentile_with(edge, Decimal("1")) != percentile_with(edge, Decimal("10") ** 12)
    assert percentile_with(outside, Decimal("1")) == percentile_with(outside, Decimal("10") ** 12)


def test_the_composer_reads_day_d_at_d_plus_1(liquidity: v2.ExtendedReplaySnapshot) -> None:
    """The entry composer reads the day ``[t - 1 day, t)`` and requires ``available_at <= t``."""

    by_day = {item.observation_date: item for item in liquidity.liquidation_percentiles}
    t = utc(2023, 6, 1)
    assert by_day[(t - DAY).date()].available_at == t
    assert by_day[t.date()].available_at > t


# --- point in time through the real owners -----------------------------------------------------

PROPERTY_SEEDS = (3, 17, 29, 101, 8675309)


def perturbed_after(cut: datetime, history: fx.LiquidationHistory, basis: tuple[Any, ...], caps: v2.MarketCapEvidence) -> dict[str, Any]:
    """Every raw value not yet available at ``cut`` multiplied; nothing earlier touched."""

    rows = tuple(
        replace(row, notional_usd=row.notional_usd * 3, quantity=row.quantity * 3) if row.observation_time + HOUR > cut else row
        for row in history.rows
    )
    later = tuple(
        replace(row, basis_rate=row.basis_rate * 2, annualized_basis_rate=fx.annualized(row.basis_rate * 2, row.observation_time, row.expiry))
        if row.observation_time > cut
        else row
        for row in basis
    )
    cap_rows = tuple((day, value * 2 if midnight(day) + 2 * DAY > cut else value) for day, value in caps.rows)
    data = fx.market_cap_bytes(cap_rows)
    return {
        "liquidations": rows,
        "liquidation_hours": history.hours,
        "futures_basis": later,
        "market_cap_evidence": v2.parse_market_cap_evidence(data, expected_sha256=hashlib.sha256(data).hexdigest()),
    }


@pytest.fixture(scope="module")
def property_inputs(history: fx.LiquidationHistory) -> dict[str, Any]:
    window = (utc(2023, 12, 20), utc(2024, 3, 10))
    return {
        "history": history,
        "basis": fx.basis_rows(*window),
        "caps": fx.market_cap_evidence(window[0].date(), window[1].date()),
        "oi": tuple(replace(row, available_at=row.observation_time) for row in fx.open_interest(*window)),
        "window": window,
        "original": build(
            liquidations=history.rows,
            liquidation_hours=history.hours,
            futures_basis=fx.basis_rows(*window),
            market_cap_evidence=fx.market_cap_evidence(window[0].date(), window[1].date()),
        ),
    }


@pytest.mark.parametrize("seed", PROPERTY_SEEDS)
def test_nothing_is_visible_before_its_modelled_availability(seed: int, property_inputs: dict[str, Any]) -> None:
    """Perturbing every value not yet available at a cut changes no owner result at the cut.

    The owners are the real ones: ``futures_basis_health``,
    ``open_interest_intensity``, ``aggregate_btc_derivatives_available_at`` and
    the frozen adapter contract through the volatility owner's percentile. The
    perturbation must also change something later, so the property is not vacuous.
    """

    rng = random.Random(seed)
    start, end = property_inputs["window"]
    cut = start + timedelta(hours=rng.randrange(48, int((end - start) / HOUR) - 48))
    cut += rng.choice((timedelta(0), -MICROSECOND, timedelta(minutes=rng.randrange(1, 60))))
    history, basis, caps, oi = property_inputs["history"], property_inputs["basis"], property_inputs["caps"], property_inputs["oi"]
    original = property_inputs["original"]
    changed = build(**perturbed_after(cut, history, basis, caps))

    def at(snapshot: v2.ExtendedReplaySnapshot, moment: datetime) -> tuple[Any, ...]:
        visible_days = [item for item in snapshot.liquidation_percentiles if item.available_at <= moment]
        return (
            futures_basis_health(snapshot.futures_basis, as_of=moment),
            open_interest_intensity(oi, snapshot.market_caps, as_of=moment, open_interest_unit="USD"),
            aggregate_btc_derivatives_available_at(list(snapshot.liquidations), moment),
            visible_days,
        )

    assert at(original, cut) == at(changed, cut)
    assert at(original, end) != at(changed, end)
    # and each record's modelled availability is the policy table's, from the raw record
    for copy in original.futures_basis:
        assert copy.available_at == copy.observation_time
    for copy in original.liquidations:
        assert copy.available_at == copy.observation_time + HOUR
    for cap in original.market_caps:
        assert cap.available_at == cap.observation_time + DAY


# --- the manifest ------------------------------------------------------------------------------


def small_inputs() -> dict[str, Any]:
    hours = fx.liquidation_history(date(2024, 2, 1), date(2024, 2, 2), unavailable_hours=[utc(2024, 2, 1, 4)])
    return {
        "futures_basis": fx.basis_rows(utc(2024, 3, 20), utc(2024, 3, 23)),
        "market_cap_evidence": fx.market_cap_evidence(date(2024, 2, 1), date(2024, 2, 5)),
        "liquidations": hours.rows,
        "liquidation_hours": hours.hours,
    }


def test_the_manifest_binds_the_v1_snapshot_without_changing_it() -> None:
    shared = fx.shared_snapshot()
    before = shared.manifest_bytes
    snapshot = build(shared_snapshot=shared, **small_inputs())
    assert shared.manifest_bytes == before == fx.shared_snapshot().manifest_bytes
    manifest = snapshot.manifest
    assert snapshot.manifest_bytes == v1.canonical_json_bytes(manifest)
    assert v1.sha256_hex(snapshot.manifest_bytes) == snapshot.manifest_sha256
    assert manifest["shared_snapshot"] == {
        "manifest_version": v1.SHARED_SNAPSHOT_MANIFEST_VERSION,
        "builder_version": v1.REPLAY_INPUTS_BUILDER_VERSION,
        "availability_policy": v1.REPLAY_AVAILABILITY_POLICY_VERSION,
        "manifest_sha256": shared.manifest_sha256,
        "families": sorted(v1.SHARED_SNAPSHOT_FAMILIES),
        "rules_unchanged_under": v2.REPLAY_AVAILABILITY_POLICY_V2,
    }
    assert (manifest["manifest_version"], manifest["builder_version"], manifest["policy"], manifest["availability_policy"]) == (
        v2.EXTENDED_SNAPSHOT_MANIFEST_VERSION,
        v2.REPLAY_INPUTS_V2_BUILDER_VERSION,
        "RESEARCH_BACKTEST_POLICY_V7",
        "HISTORICAL_REPLAY_AVAILABILITY_V2",
    )
    assert manifest["shapes"] == dict(v2.REPLAY_SHAPES_V2)
    assert manifest["evidence_class"] == v1.RESEARCH_EVIDENCE_CLASS and manifest["canonical_reference"] == "UNRESOLVED"


def test_the_manifest_lists_the_declared_inputs() -> None:
    manifest = build().manifest
    assert {key: value["status"] for key, value in manifest["discretionary_inputs"].items()} == dict.fromkeys(v2.DISCRETIONARY_INPUTS, "NOT_ASSERTED")
    assert all(value["supplied"] is None and value["shape"] == "DISCRETIONARY" for value in manifest["discretionary_inputs"].values())
    assert {key: value["status"] for key, value in manifest["unsourceable_inputs"].items()} == dict.fromkeys(v2.UNSOURCEABLE_INPUTS, "REFUSED_NOT_APPROXIMATED")


def test_the_manifest_records_the_adapter_by_reference(liquidity: v2.ExtendedReplaySnapshot) -> None:
    section = liquidity.manifest["liquidation_percentile"]
    assert section["adapter"] == {
        "version": "PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1",
        "definition_sha256": epic_x.prospective_liquidation_percentile_adapter_contract()["definition_sha256"],
        "window_days": 730,
        "minimum_prior_observations": 365,
        "convention": "MIDRANK_PERCENTILE_OF_PRIOR_WINDOW_V1",
        "convention_owner": "btc_predictor.features.volatility._percentile_rank",
    }
    assert section["completeness_rule"] == "HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1"
    assert section["day_count"] == len(liquidity.liquidation_days)
    assert section["reason_code_counts"][v2.LIQUIDATION_FEED_UNAVAILABLE] == 2
    hour_section = liquidity.manifest["families"][v2.LIQUIDATIONS_FAMILY]["hour_evidence"]
    assert hour_section["status_counts"][UNAVAILABLE] == 1
    assert (hour_section["gaps"]["gap_count"], hour_section["gaps"]["missing_slot_count"]) == (1, 1)


@pytest.mark.parametrize("seed", PROPERTY_SEEDS[:3])
def test_the_manifest_is_identical_under_input_reordering(seed: int) -> None:
    inputs = small_inputs()
    rng = random.Random(seed)
    shuffled = {key: (value if key == "market_cap_evidence" else rng.sample(list(value), len(value))) for key, value in inputs.items()}
    assert build(**shuffled).manifest_bytes == build(**inputs).manifest_bytes


RUNNER = """
from btc_predictor.tests.test_research_backtest_replay_inputs_v2 import build, small_inputs
print(build(**small_inputs()).manifest_sha256)
"""


@pytest.mark.parametrize("seed", ("0", "1", "8675309"))
def test_the_manifest_is_identical_in_fresh_processes_hash_seeds_and_another_cwd(seed: str, tmp_path: Path) -> None:
    environment = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", RUNNER], cwd=tmp_path, env=environment, capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == build(**small_inputs()).manifest_sha256


def test_the_builder_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the replay builder opened a socket")

    inputs = small_inputs()
    shared = fx.shared_snapshot()
    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    assert build(shared_snapshot=shared, **inputs).manifest_sha256


# --- the entry composer's inputs ---------------------------------------------------------------


def test_the_snapshot_gives_the_entry_composer_its_inputs() -> None:
    shared = fx.shared_snapshot()
    snapshot = build(shared_snapshot=shared, **small_inputs())
    dataset = v1.build_venue_replay_dataset(venue=v1.BITSTAMP_REPLAY_VENUE, window=v1.DATA_WINDOW, price_bars=fx_price_bars(), shared_snapshot=shared)
    inputs = snapshot.entry_composer_inputs(dataset)
    assert type(inputs) is EntryComposerInputs
    assert (inputs.futures_basis, inputs.market_caps, inputs.liquidation_percentiles) == (
        snapshot.futures_basis,
        snapshot.market_caps,
        snapshot.liquidation_percentiles,
    )
    other = v1.build_venue_replay_dataset(
        venue=v1.BITSTAMP_REPLAY_VENUE, window=v1.DATA_WINDOW, price_bars=fx_price_bars(), shared_snapshot=v1.build_shared_replay_snapshot(window=v1.DATA_WINDOW)
    )
    with pytest.raises(v1.ReplayInputRefused) as caught:
        snapshot.entry_composer_inputs(other)
    assert caught.value.reason_code == "SHARED_SNAPSHOT_MISMATCH"


def fx_price_bars() -> tuple[Any, ...]:
    from btc_predictor.data import OhlcvBar

    bars = []
    for index in range(48):
        at = utc(2024, 2, 1) + index * HOUR
        price = Decimal(42_000 + index)
        bars.append(
            OhlcvBar(
                timestamp=at,
                exchange=v1.BITSTAMP_REPLAY_VENUE.exchange,
                symbol=v1.BITSTAMP_REPLAY_VENUE.symbol,
                timeframe="1h",
                open=price,
                high=price + 10,
                low=price - 10,
                close=price + 5,
                volume=Decimal("12"),
                provider=v1.BITSTAMP_REPLAY_VENUE.provider,
                ingested_at=BULK_INGESTED_AT,
            )
        )
    return tuple(bars)
