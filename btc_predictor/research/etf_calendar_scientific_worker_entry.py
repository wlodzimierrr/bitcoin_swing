"""One-shot isolated ETF-calendar scientific worker entrypoint.

``POSTP1-001V2A-PAD4`` freezes ``ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1``.
This file is the *only* scientific worker entrypoint.  It is launched as a
fresh exec'd CPython 3.12.14 process by the controller, it serves exactly one
canonical scientific request, it emits exactly one canonical response on stdout
and it exits.  No Python object, module, class, function or pickle crosses the
process boundary; only deterministic canonical data does.

Because ``sys.path`` is parent-controlled and is only established inside
``main``, this file deliberately performs every project import inside a
function.  Those are ordinary static import declarations: the certified project
source manifest is derived from them mechanically, and the closed worker-coding
rule forbids ``exec``, ``eval``, ``compile``, ``__import__``, ``importlib``,
``runpy``, ``marshal`` and ``pickle`` anywhere in authoritative worker source.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping


EXIT_SUCCESS = 0
EXIT_REFUSED = 3
EXIT_PROTOCOL_FAILURE = 4
EXIT_WRONG_INTERPRETER = 5

REFUSE_SCIENTIFIC_AUTHORITY = "REFUSE_SCIENTIFIC_AUTHORITY"


def live_interpreter_identity() -> dict[str, Any]:
    """Read the live interpreter identity using only the standard library.

    This runs before any project import so that a wrong interpreter refuses
    before the certified source universe is executed at all.  It holds no
    frozen constant of its own: the expected identity is request material that
    the controller binds from the single owning authority.
    """

    bootstrap = sys.modules.get("_frozen_importlib_external")
    magic = getattr(bootstrap, "MAGIC_NUMBER", b"")
    version = sys.version_info
    return {
        "implementation_name": sys.implementation.name,
        "version_major": version.major,
        "version_minor": version.minor,
        "version_micro": version.micro,
        "version_releaselevel": version.releaselevel,
        "version_serial": version.serial,
        "hexversion": sys.hexversion,
        "cache_tag": sys.implementation.cache_tag,
        "magic_number_hex": bytes(magic).hex(),
    }


def _load_protocol() -> Any:
    from btc_predictor.research import etf_calendar_worker_protocol as protocol

    return protocol


def _load_calendar() -> Any:
    from btc_predictor.research import etf_publication_calendar as calendar

    return calendar


def _load_etf_flow_type() -> Any:
    from btc_predictor.data.etf_flows import EtfFlow

    return EtfFlow


# ---------------------------------------------------------------------------
# Evidence reconstruction
# ---------------------------------------------------------------------------


def reconstruct_evidence_store(calendar: Any, mode: str, records: Any) -> Any:
    """Rebuild a read-only scientific evidence view from canonical data only.

    A live ``CalendarEvidenceStore`` object is never transferred.  Under the
    authoritative mode the worker replays production-signed trusted-acquisition
    envelopes through the certified trusted-persistence authority.  The
    prototype mode of this decision replays already-verified canonical records
    and is explicitly non-authoritative.
    """

    protocol = _load_protocol()
    store = calendar.CalendarEvidenceStore()
    envelope_kind = calendar._trusted.ENVELOPE_KIND
    order = {
        envelope_kind: 0,
        calendar.SOURCE_SNAPSHOT_KIND: 1,
        calendar.NORMALIZED_SCHEDULE_KIND: 2,
        calendar.VENUE_SESSION_RECORD_KIND: 3,
    }
    rows = sorted(
        records,
        key=lambda row: (
            order.get(row.get("record_kind"), 99),
            row.get("record_sha256", ""),
        ),
    )
    for row in rows:
        kind = row.get("record_kind")
        if kind not in order:
            raise protocol.ScientificWorkerProtocolError(
                "UNKNOWN_EVIDENCE_RECORD_KIND", repr(kind)
            )
        if kind == calendar.SOURCE_SNAPSHOT_KIND:
            if mode != protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE:
                raise protocol.ScientificWorkerProtocolError(
                    "UNSIGNED_ACQUISITION_REFUSED_UNDER_AUTHORITATIVE_ADMISSION", ""
                )
            _install_non_authoritative_snapshot(calendar, store, row)
            continue
        store.put(row)
    return store


def _install_non_authoritative_snapshot(calendar: Any, store: Any, row: Any) -> None:
    """Prototype-only replay of an already-verified acquisition snapshot.

    The frozen authoritative admission mode is production-signed envelope
    replay; this path exists so that the adversarial isolation regressions of
    this decision can execute the real scientific owners without a production
    signing capability, and every response it produces is stamped
    non-authoritative.
    """

    source = calendar._verify_source_snapshot(row)
    store._records[source[calendar.RECORD_DIGEST_FIELD]] = source


# ---------------------------------------------------------------------------
# Deterministic result encoding
# ---------------------------------------------------------------------------


def _encode_calendar_window(result: Any) -> dict[str, Any]:
    return {
        "state": result.state,
        "expected_dates": [day.isoformat() for day in result.expected_dates],
        "market_holidays": sorted(day.isoformat() for day in result.market_holidays),
        "unresolved_dates": [day.isoformat() for day in result.unresolved_dates],
        "reason_codes": list(result.reason_codes),
    }


def _encode_common_session(result: Any) -> dict[str, Any]:
    return {
        "trade_date": result.trade_date.isoformat(),
        "state": result.state,
        "venue_states": [[venue, state] for venue, state in result.venue_states],
        "reason_codes": list(result.reason_codes),
    }


def _encode_feature(feature: Any) -> dict[str, Any] | None:
    if feature is None:
        return None
    return {
        "feature_id": feature.feature_id,
        "normalized_feature_id": feature.normalized_feature_id,
        "window_days": feature.window_days,
        "observation_date": feature.observation_date.isoformat(),
        "included_observation_dates": [
            day.isoformat() for day in feature.included_observation_dates
        ],
        "funds": list(feature.funds),
        "flow_sum_usd": _encode_decimal(feature.flow_sum_usd),
        "total_aum_usd": _encode_decimal(feature.total_aum_usd),
        "normalized_flow": _encode_decimal(feature.normalized_flow),
        "source_record_count": feature.source_record_count,
        "complete": feature.complete,
        "reason_codes": list(feature.reason_codes),
    }


def _encode_decimal(value: Any) -> str | None:
    return None if value is None else str(value)


def _encode_scientific_flow(result: Any) -> dict[str, Any]:
    return {
        "evaluability_state": result.evaluability_state,
        "calendar": _encode_calendar_window(result.calendar),
        "feature": _encode_feature(result.feature),
        "reason_codes": list(result.reason_codes),
    }


# ---------------------------------------------------------------------------
# Frozen operations
# ---------------------------------------------------------------------------


def evaluate_operation(
    calendar: Any,
    operation: str,
    inputs: Mapping[str, Any],
    decision_time: Any,
    store: Any,
) -> tuple[Any, dict[str, Any]]:
    """Evaluate exactly one frozen read-only scientific operation."""

    protocol = _load_protocol()
    if operation == "common_etf_session_status":
        raw = calendar.common_etf_session_status(
            protocol.canonical_date(inputs["trade_date"], "trade_date"),
            decision_time,
            store,
        )
        return raw, _encode_common_session(raw)
    if operation == "derive_etf_window_calendar":
        raw = calendar.derive_etf_window_calendar(
            end_date=protocol.canonical_date(inputs["end_date"], "end_date"),
            earliest_date=protocol.canonical_date(
                inputs["earliest_date"], "earliest_date"
            ),
            window_days=inputs["window_days"],
            decision_time=decision_time,
            evidence_store=store,
        )
        return raw, _encode_calendar_window(raw)
    if operation == "scientific_etf_flow_window":
        raw = calendar.scientific_etf_flow_window(
            _etf_flows(protocol, inputs["etf_flows"]),
            as_of=protocol.canonical_utc_timestamp(inputs["as_of"], "as_of"),
            funds=tuple(inputs["funds"]),
            end_date=protocol.canonical_date(inputs["end_date"], "end_date"),
            earliest_date=protocol.canonical_date(
                inputs["earliest_date"], "earliest_date"
            ),
            window_days=inputs["window_days"],
            evidence_store=store,
        )
        return raw, _encode_scientific_flow(raw)
    raise protocol.ScientificWorkerProtocolError(
        "UNKNOWN_SCIENTIFIC_OPERATION", repr(operation)
    )


def _etf_flows(protocol: Any, rows: Any) -> tuple[Any, ...]:
    flow_type = _load_etf_flow_type()
    return tuple(
        flow_type(
            fund=row["fund"],
            observation_date=protocol.canonical_date(
                row["observation_date"], "observation_date"
            ),
            flow_usd=Decimal(row["flow_usd"]),
            aum_usd=None if row["aum_usd"] is None else Decimal(row["aum_usd"]),
            provider=row["provider"],
            source=row["source"],
            revision=row["revision"],
            available_at=protocol.canonical_utc_timestamp(
                row["available_at"], "available_at"
            ),
            ingested_at=protocol.canonical_utc_timestamp(
                row["ingested_at"], "ingested_at"
            ),
        )
        for row in rows
    )


# ---------------------------------------------------------------------------
# One-shot worker
# ---------------------------------------------------------------------------


def serve_one_request(raw_request: bytes, entry_path: Path) -> dict[str, Any]:
    """Serve exactly one scientific request and return the canonical response."""

    protocol = _load_protocol()
    protocol.claim_single_request()
    if len(raw_request) > protocol.MAX_REQUEST_BYTES:
        raise protocol.ScientificWorkerProtocolError(
            "REQUEST_EXCEEDS_THE_FROZEN_INPUT_SIZE_LIMIT", str(len(raw_request))
        )
    request = protocol.validate_request(
        protocol.assert_canonical_request_bytes(raw_request)
    )
    payload = request.payload
    request_digest = protocol.digest_bytes(raw_request)

    # Section 26 — worker source and environment self-verification.
    protocol.verify_proof_interpreter_identity()
    startup = protocol.verify_controlled_startup(payload["sys_path"])
    project_root = request.project_root
    expected_entry = (
        project_root / protocol.WORKER_ENTRYPOINT_RELATIVE_PATH
    ).resolve()
    if entry_path.resolve() != expected_entry:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_IS_NOT_THE_CERTIFIED_PATH",
            f"{entry_path} != {expected_entry}",
        )
    observed_entry_sha = protocol.file_sha256(expected_entry)
    if observed_entry_sha != payload["worker_entrypoint_sha256"]:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_SOURCE_MISMATCH", observed_entry_sha
        )
    observed_protocol_sha = protocol.file_sha256(
        (project_root / protocol.WORKER_PROTOCOL_RELATIVE_PATH).resolve()
    )
    if observed_protocol_sha != payload["worker_protocol_sha256"]:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_PROTOCOL_SOURCE_MISMATCH", observed_protocol_sha
        )
    entries = request.source_entries
    resolved = protocol.verify_project_source_manifest(project_root, entries)
    protocol.verify_third_party_manifest(request.third_party)

    # Section 27 — every loaded project module is certified, before evaluation.
    calendar = _load_calendar()
    protocol.verify_loaded_project_modules(
        entries, resolved, payload["required_project_modules"], "PRE_EXECUTION"
    )
    if calendar.FROZEN_AUTHORITY_DEFINITION_SHA256 != payload[
        "calendar_authority_sha256"
    ]:
        raise protocol.ScientificWorkerProtocolError(
            "CALENDAR_AUTHORITY_IDENTITY_MISMATCH",
            calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        )
    if calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256 != payload[
        "trusted_persistence_authority_sha256"
    ]:
        raise protocol.ScientificWorkerProtocolError(
            "TRUSTED_PERSISTENCE_IDENTITY_MISMATCH",
            calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256,
        )

    store = reconstruct_evidence_store(
        calendar, payload["evidence_admission_mode"], payload["evidence_records"]
    )
    raw_result, encoded = evaluate_operation(
        calendar,
        payload["operation"],
        payload["operation_inputs"],
        request.decision_time,
        store,
    )

    # Section 24 — the admitted result must already be fully materialized.
    protocol.refuse_lazy_result(raw_result)
    protocol.refuse_lazy_result(encoded)

    # Section 28 — defence in depth, never runtime object attestation.
    protocol.verify_loaded_project_modules(
        entries, resolved, payload["required_project_modules"], "POST_EXECUTION"
    )
    loaded = protocol.verify_project_source_manifest(project_root, entries)
    if loaded != resolved:
        raise protocol.ScientificWorkerProtocolError(
            "CERTIFIED_SOURCE_DRIFTED_DURING_EXECUTION", ""
        )

    response = protocol.build_response(
        response_schema_version=protocol.RESPONSE_SCHEMA_VERSION,
        status=protocol.SUCCESS,
        failure_reason=None,
        worker_authority_version=protocol.WORKER_AUTHORITY_VERSION,
        worker_authority_sha256=payload["worker_authority_sha256"],
        calendar_authority_sha256=calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        trusted_persistence_authority_sha256=(
            calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256
        ),
        interpreter_identity=protocol.current_interpreter_identity(),
        worker_entrypoint_sha256=observed_entry_sha,
        worker_protocol_sha256=observed_protocol_sha,
        project_source_manifest_digest=protocol.manifest_digest(entries),
        third_party_manifest_digest=protocol.third_party_manifest_digest(
            request.third_party
        ),
        loaded_project_modules=len(resolved),
        interpreter_flags=startup["interpreter_flags"],
        sys_path_digest=startup["sys_path_digest"],
        request_schema_version=protocol.REQUEST_SCHEMA_VERSION,
        request_digest=request_digest,
        operation=payload["operation"],
        evidence_admission_mode=payload["evidence_admission_mode"],
        decision_time=payload["decision_time"],
        result=encoded,
        result_digest=protocol.result_digest(encoded),
        post_execution_source_verification="PASS",
        one_request_one_process=True,
    )
    protocol.assert_address_free(response)
    return response


def refusal_response(reason: str, request_digest: str | None) -> dict[str, Any]:
    """A deterministic typed failure never carries a scientific result."""

    protocol = _load_protocol()
    return protocol.build_response(
        response_schema_version=protocol.RESPONSE_SCHEMA_VERSION,
        status=protocol.REFUSED,
        failure_reason=reason,
        worker_authority_version=protocol.WORKER_AUTHORITY_VERSION,
        worker_authority_sha256=None,
        calendar_authority_sha256=None,
        trusted_persistence_authority_sha256=None,
        interpreter_identity=None,
        worker_entrypoint_sha256=None,
        worker_protocol_sha256=None,
        project_source_manifest_digest=None,
        third_party_manifest_digest=None,
        loaded_project_modules=None,
        interpreter_flags=None,
        sys_path_digest=None,
        request_schema_version=protocol.REQUEST_SCHEMA_VERSION,
        request_digest=request_digest,
        operation=None,
        evidence_admission_mode=None,
        decision_time=None,
        result=None,
        result_digest=None,
        post_execution_source_verification="NOT_REACHED",
        one_request_one_process=True,
    )


def _declared_interpreter_identity(raw_request: bytes) -> dict[str, Any] | None:
    """Read the expected interpreter identity without validating the request.

    An unreadable or malformed payload declares nothing, so the ordinary
    canonical-protocol path produces the typed refusal instead.
    """

    try:
        payload = json.loads(raw_request.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    declared = payload.get("interpreter_identity") if isinstance(payload, dict) else None
    return declared if isinstance(declared, dict) else None


def main(argv: list[str], raw_request: bytes, entry_path: Path) -> tuple[int, bytes]:
    """Return the worker exit status and the single canonical stdout payload."""

    sys.path[:] = [str(entry) for entry in json.loads(argv[1])]
    declared = _declared_interpreter_identity(raw_request)
    if declared is not None and live_interpreter_identity() != declared:
        return EXIT_WRONG_INTERPRETER, b""
    protocol = _load_protocol()
    try:
        response = serve_one_request(raw_request, entry_path)
        status = EXIT_SUCCESS
    except protocol.ScientificWorkerProtocolError as error:
        response = refusal_response(error.reason, None)
        status = EXIT_REFUSED
    except Exception as error:  # deterministic typed failure, never partial admission
        response = refusal_response(
            f"WORKER_SCIENTIFIC_EXCEPTION:{type(error).__name__}", None
        )
        status = EXIT_REFUSED
    payload = protocol.canonical_json_bytes(response) + b"\n"
    if len(payload) > protocol.MAX_RESPONSE_BYTES:
        return EXIT_PROTOCOL_FAILURE, b""
    return status, payload


if __name__ == "__main__":  # pragma: no cover - exercised through the controller
    _status, _payload = main(
        sys.argv, sys.stdin.buffer.read(), Path(__file__).resolve()
    )
    if _status == EXIT_WRONG_INTERPRETER:
        sys.stderr.write(f"{REFUSE_SCIENTIFIC_AUTHORITY}: frozen proof interpreter mismatch\n")
    sys.stdout.buffer.write(_payload)
    sys.stdout.buffer.flush()
    raise SystemExit(_status)
