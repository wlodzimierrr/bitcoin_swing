"""Commit-confirmed PostgreSQL persistence for trusted acquisitions."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, Engine, Select, create_engine, select, text
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
DATABASE_IDENTITY_INVALID = "TRUSTED_ACQUISITION_DATABASE_IDENTITY_INVALID"
COLLECTOR_ROLE = "btc_calendar_collector_writer"
AUTHORITATIVE_TABLE = "research.etf_calendar_trusted_acquisitions"
AUTHORITATIVE_SCHEMA = "research"


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
            assert_authorized_collector_database_identity(connection)
            connection.execute(statement)
    except TrustedAcquisitionError:
        raise
    except Exception as error:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED) from error
    # Drop the committed transaction's pool so confirmation cannot reuse its
    # physical DBAPI connection.
    engine.dispose()
    try:
        with engine.connect() as confirmation:
            # Production deliberately uses the same configured collector URL for
            # write and confirmation; revalidate the independent connection.
            assert_authorized_collector_database_identity(confirmation)
            persisted = confirmation.execute(
                authoritative_envelope_query(str(intended["envelope_sha256"]))
            ).mappings().one_or_none()
    except TrustedAcquisitionError:
        raise
    except Exception as error:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED) from error
    if persisted is None:
        raise TrustedAcquisitionError(COMMIT_UNCONFIRMED)
    confirmed = rehydrate_verified_envelopes((persisted,))[0]
    if confirmed != intended:
        raise TrustedAcquisitionError("persisted trusted-acquisition envelope mismatch")
    return str(intended["envelope_sha256"])


def assert_authorized_collector_database_identity(connection: Connection) -> dict[str, Any]:
    """Prove the actual PostgreSQL session is the frozen least-privilege collector."""

    try:
        snapshot = _database_identity_snapshot(connection)
        required_true = (
            "session_or_current_is_collector_member",
            "collector_role_exists",
            "collector_role_nologin",
            "collector_role_safe",
            "collector_role_has_no_membership",
        )
        required_false = (
            "session_user_superuser",
            "current_user_superuser",
            "session_user_database_owner",
            "current_user_database_owner",
            "session_user_schema_owner",
            "current_user_schema_owner",
            "session_user_table_owner",
            "current_user_table_owner",
        )
        if any(snapshot.get(field) is not True for field in required_true):
            raise TrustedAcquisitionError(DATABASE_IDENTITY_INVALID)
        if any(snapshot.get(field) is not False for field in required_false):
            raise TrustedAcquisitionError(DATABASE_IDENTITY_INVALID)
        _assert_database_privileges(snapshot)
        return snapshot
    except TrustedAcquisitionError:
        raise
    except Exception as error:
        raise TrustedAcquisitionError(DATABASE_IDENTITY_INVALID) from error


def _database_identity_snapshot(connection: Connection) -> dict[str, Any]:
    statement = text(
        """
SELECT
    session_user::text AS session_user,
    current_user::text AS current_user,
    current_database()::text AS database_name,
    (
        pg_has_role(session_user, CAST(:collector_role AS name), 'MEMBER')
        OR pg_has_role(current_user, CAST(:collector_role AS name), 'MEMBER')
    ) AS session_or_current_is_collector_member,
    EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :collector_role
    ) AS collector_role_exists,
    COALESCE((
        SELECT NOT rolcanlogin FROM pg_catalog.pg_roles WHERE rolname = :collector_role
    ), false) AS collector_role_nologin,
    COALESCE((
        SELECT NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
          FROM pg_catalog.pg_roles WHERE rolname = :collector_role
    ), false) AS collector_role_safe,
    NOT EXISTS (
        SELECT 1
          FROM pg_catalog.pg_auth_members memberships
          JOIN pg_catalog.pg_roles collector ON collector.oid = memberships.member
         WHERE collector.rolname = :collector_role
    ) AS collector_role_has_no_membership,
    COALESCE((SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = session_user), true)
        AS session_user_superuser,
    COALESCE((SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = current_user), true)
        AS current_user_superuser,
    session_user = pg_catalog.pg_get_userbyid(
        (SELECT datdba FROM pg_catalog.pg_database WHERE datname = current_database())
    ) AS session_user_database_owner,
    current_user = pg_catalog.pg_get_userbyid(
        (SELECT datdba FROM pg_catalog.pg_database WHERE datname = current_database())
    ) AS current_user_database_owner,
    session_user = pg_catalog.pg_get_userbyid(
        (SELECT nspowner FROM pg_catalog.pg_namespace WHERE nspname = :schema_name)
    ) AS session_user_schema_owner,
    current_user = pg_catalog.pg_get_userbyid(
        (SELECT nspowner FROM pg_catalog.pg_namespace WHERE nspname = :schema_name)
    ) AS current_user_schema_owner,
    session_user = pg_catalog.pg_get_userbyid((
        SELECT relation.relowner
          FROM pg_catalog.pg_class relation
          JOIN pg_catalog.pg_namespace namespace ON namespace.oid = relation.relnamespace
         WHERE namespace.nspname = :schema_name AND relation.relname = :table_short_name
    )) AS session_user_table_owner,
    current_user = pg_catalog.pg_get_userbyid((
        SELECT relation.relowner
          FROM pg_catalog.pg_class relation
          JOIN pg_catalog.pg_namespace namespace ON namespace.oid = relation.relnamespace
         WHERE namespace.nspname = :schema_name AND relation.relname = :table_short_name
    )) AS current_user_table_owner,
    has_table_privilege(current_user, :table_name, 'SELECT') AS table_select,
    has_table_privilege(current_user, :table_name, 'INSERT') AS table_insert,
    has_table_privilege(current_user, :table_name, 'UPDATE') AS table_update,
    has_table_privilege(current_user, :table_name, 'DELETE') AS table_delete,
    has_schema_privilege(current_user, :schema_name, 'USAGE') AS schema_usage,
    has_schema_privilege(current_user, :schema_name, 'CREATE') AS schema_create
"""
    )
    row = connection.execute(
        statement,
        {
            "collector_role": COLLECTOR_ROLE,
            "schema_name": AUTHORITATIVE_SCHEMA,
            "table_name": AUTHORITATIVE_TABLE,
            "table_short_name": "etf_calendar_trusted_acquisitions",
        },
    ).mappings().one()
    return dict(row)


def _assert_database_privileges(snapshot: Mapping[str, Any]) -> None:
    required = {"table_select": True, "table_insert": True, "schema_usage": True}
    forbidden = {"table_update": False, "table_delete": False, "schema_create": False}
    if any(snapshot.get(name) is not value for name, value in required.items()):
        raise TrustedAcquisitionError(DATABASE_IDENTITY_INVALID)
    if any(snapshot.get(name) is not value for name, value in forbidden.items()):
        raise TrustedAcquisitionError(DATABASE_IDENTITY_INVALID)


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
