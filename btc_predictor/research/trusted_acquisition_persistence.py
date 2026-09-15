"""Commit-confirmed PostgreSQL persistence for trusted acquisitions."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, Select, create_engine, select
from sqlalchemy.dialects.postgresql import insert

from btc_predictor.db.research import etf_calendar_trusted_acquisitions
from btc_predictor.research.trusted_acquisition import (
    AUTHORITY_VERSION,
    ENVELOPE_KIND,
    TrustedAcquisitionError,
    _assert_runtime_semantics,
    verify_production_envelope,
)


DATABASE_URL_ENV_VAR = "BTC_PREDICTOR_DATABASE_URL"
COMMIT_UNCONFIRMED = "TRUSTED_ACQUISITION_COMMIT_UNCONFIRMED"


class PostgresTrustedAcquisitionAppender:
    """Production facade with no caller-selected connection or trust root."""

    def append(self, envelope: Mapping[str, Any]) -> str:
        return append_production_envelope_committed(envelope)


def append_production_envelope_committed(envelope: Mapping[str, Any]) -> str:
    """Return identity only after owned commit and independent exact readback."""

    _assert_runtime_semantics()
    payload = verify_production_envelope(envelope)
    configured = os.environ.get(DATABASE_URL_ENV_VAR)
    if not configured:
        raise TrustedAcquisitionError("production PostgreSQL configuration is unavailable")
    engine = create_engine(configured)
    try:
        return _append_with_owned_engine_non_authoritative_test_only(
            engine, envelope=envelope, payload=payload
        )
    finally:
        engine.dispose()


def _append_with_owned_engine_non_authoritative_test_only(
    engine: Engine, *, envelope: Mapping[str, Any], payload: Mapping[str, Any]
) -> str:
    """Transaction primitive exposed only for deterministic infrastructure tests."""

    if engine.dialect.name != "postgresql":
        raise TrustedAcquisitionError("authoritative acquisition append requires PostgreSQL")
    intended = dict(envelope)
    statement = insert(etf_calendar_trusted_acquisitions).values(
        **_persistence_values(intended, payload)
    ).on_conflict_do_nothing()
    try:
        with engine.begin() as connection:
            connection.execute(statement)
    except Exception as error:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED) from error
    # Drop the committed transaction's pool so confirmation cannot reuse its
    # physical DBAPI connection.
    engine.dispose()
    try:
        with engine.connect() as confirmation:
            persisted = confirmation.execute(
                authoritative_envelope_query(str(intended["envelope_sha256"]))
            ).mappings().one_or_none()
    except Exception as error:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED) from error
    if persisted is None:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED)
    confirmed = rehydrate_verified_envelopes((persisted,))[0]
    if confirmed != intended:
        raise TrustedAcquisitionError("persisted trusted-acquisition envelope mismatch")
    return str(intended["envelope_sha256"])


def _persistence_values(
    envelope: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "envelope_sha256": envelope["envelope_sha256"],
        "signed_payload": dict(payload),
        "signed_payload_sha256": envelope["signed_payload_sha256"],
        "signing_key_id": envelope["signing_key_id"],
        "signature_algorithm": envelope["signature_algorithm"],
        "signature": envelope["signature"],
        "response_sha256": payload["response_sha256"],
        "response_received_at": _utc(payload["response_received_at"]),
        "acquired_at": _utc(payload["acquired_at"]),
        "available_at": _utc(payload["available_at"]),
        "source_profile_id": payload["source_profile_id"],
        "venue_id": payload["venue_id"],
        "source_authority_id": payload["source_authority_id"],
        "created_at": datetime.now(UTC),
    }


def authoritative_envelope_query(envelope_sha256: str | None = None) -> Select:
    query = select(etf_calendar_trusted_acquisitions)
    if envelope_sha256 is not None:
        query = query.where(
            etf_calendar_trusted_acquisitions.c.envelope_sha256 == envelope_sha256
        )
    return query.order_by(etf_calendar_trusted_acquisitions.c.envelope_sha256)


def rehydrate_verified_envelopes(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Rehydrate only fixed-production-key envelopes and verify every projection."""

    _assert_runtime_semantics()
    envelopes: list[dict[str, Any]] = []
    for row in rows:
        envelope = {
            "record_kind": ENVELOPE_KIND,
            "schema_version": 1,
            "authority_identity": AUTHORITY_VERSION,
            "signed_payload": row["signed_payload"],
            "signed_payload_sha256": row["signed_payload_sha256"],
            "signing_key_id": row["signing_key_id"],
            "signature_algorithm": row["signature_algorithm"],
            "signature": row["signature"],
            "envelope_sha256": row["envelope_sha256"],
        }
        payload = verify_production_envelope(envelope)
        _assert_projection_equality(row, payload)
        envelopes.append(envelope)
    return tuple(envelopes)


def _assert_projection_equality(row: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
    for field in ("response_sha256", "source_profile_id", "venue_id", "source_authority_id"):
        if field in row and row[field] != payload[field]:
            raise TrustedAcquisitionError(f"persisted projection mismatch: {field}")
    for field in ("response_received_at", "acquired_at", "available_at"):
        if field in row and _utc(row[field]) != _utc(payload[field]):
            raise TrustedAcquisitionError(f"persisted projection mismatch: {field}")


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if (
        not isinstance(parsed, datetime)
        or parsed.tzinfo is None
        or parsed.utcoffset() != UTC.utcoffset(None)
    ):
        raise TrustedAcquisitionError("persisted acquisition timestamp must be UTC")
    return parsed
