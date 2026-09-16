"""Opt-in destructive validation against an explicitly disposable PostgreSQL server."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from psycopg import sql
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL

from btc_predictor.db import current_database_revision, upgrade_database
from btc_predictor.research import trusted_acquisition as trusted
from btc_predictor.research import trusted_acquisition_persistence as persistence


pytestmark = pytest.mark.skipif(
    os.environ.get("BTC_TRUSTED_ACQUISITION_DISPOSABLE_POSTGRES") != "1",
    reason="explicit disposable PostgreSQL opt-in is required",
)

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = persistence.COLLECTOR_ROLE
READER = "btc_predictor_scientific_reader"


def _project_postgres() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _url(values: dict[str, str], database: str, user: str, password: str) -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password,
        host=values["POSTGRES_HOST"],
        port=int(values["POSTGRES_PORT"]),
        database=database,
    )


def _url_string(values: dict[str, str], database: str, user: str, password: str) -> str:
    return _url(values, database, user, password).render_as_string(hide_password=False)


def _admin_connection(values: dict[str, str]):
    return psycopg.connect(
        host=values["POSTGRES_HOST"],
        port=values["POSTGRES_PORT"],
        dbname=values["POSTGRES_DB"],
        user=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        autocommit=True,
    )


def _execute(connection, statement: str, *identifiers: str) -> None:
    connection.execute(sql.SQL(statement).format(*(sql.Identifier(x) for x in identifiers)))


def _assert_refuses(url: URL) -> None:
    engine = create_engine(url)
    try:
        with engine.connect() as connection, pytest.raises(
            trusted.TrustedAcquisitionError,
            match=persistence.DATABASE_IDENTITY_INVALID,
        ):
            persistence.assert_authorized_collector_database_identity(connection)
    finally:
        engine.dispose()


def _test_envelope(
    *, response_digit: str = "1", available_at: str = "2026-09-15T12:00:00+00:00"
) -> tuple[dict, trusted.VerificationKey]:
    signer = trusted.AcquisitionSigner(
        Ed25519PrivateKey.from_private_bytes(bytes(range(32))),
        "TEST_ONLY_POSTGRES_RUNTIME_V1",
    )
    payload = {
        "response_sha256": response_digit * 64,
        "response_received_at": "2026-09-15T12:00:00+00:00",
        "acquired_at": "2026-09-15T12:00:00+00:00",
        "available_at": available_at,
        "source_profile_id": "TEST_ONLY_SOURCE",
        "venue_id": "TEST",
        "source_authority_id": "TEST_ONLY_AUTHORITY",
    }
    return signer.sign_payload(payload), signer.verification_key()


def _test_rehydrator(key: trusted.VerificationKey):
    def restore(rows):
        restored = []
        for row in rows:
            envelope = {
                "record_kind": trusted.ENVELOPE_KIND,
                "schema_version": 1,
                "authority_identity": trusted.AUTHORITY_VERSION,
                "signed_payload": row["signed_payload"],
                "signed_payload_sha256": row["signed_payload_sha256"],
                "signing_key_id": row["signing_key_id"],
                "signature_algorithm": row["signature_algorithm"],
                "signature": row["signature"],
                "envelope_sha256": row["envelope_sha256"],
            }
            payload = trusted.verify_test_envelope_non_authoritative_test_only(envelope, key)
            persistence._assert_projection_equality(row, payload)
            restored.append(envelope)
        return tuple(restored)
    return restore


def test_real_postgresql_migration_acl_identity_and_durability(monkeypatch) -> None:
    values = _project_postgres()
    nonce = f"{os.getpid()}_{secrets.token_hex(4)}"
    database = f"btc_ta_r2_{nonce}"
    safe_database = f"btc_ta_r2_safe_{nonce}"
    unsafe_database = f"btc_ta_r2_unsafe_{nonce}"
    password = secrets.token_urlsafe(24)
    alternate_group = f"btc_ta_r3_alternate_safe_group_{nonce}"
    roles = {
        name: f"btc_ta_r2_{name}_{nonce}"
        for name in (
            "collector", "reader", "unrelated", "owner", "table_owner",
                "schema_owner", "superuser", "extra_update", "extra_delete",
                "schema_create", "alternate_login", "parent",
        )
    }
    databases = [database, safe_database, unsafe_database]

    with _admin_connection(values) as admin:
        present = admin.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", ([COLLECTOR, READER],)
        ).fetchall()
        if present:
            pytest.skip("fixed authority roles already exist; disposable-cluster isolation absent")
        try:
            # Fresh full-chain migration proves migration 0025 provisions both roles itself.
            _execute(admin, "CREATE DATABASE {}", database)
            upgrade_database(_url_string(values, database, values["POSTGRES_USER"], values["POSTGRES_PASSWORD"]))
            assert current_database_revision(
                _url_string(values, database, values["POSTGRES_USER"], values["POSTGRES_PASSWORD"])
            ) == "0025_trusted_acquisition"
            role_rows = admin.execute(
                """SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                          rolreplication, rolbypassrls
                     FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname""",
                ([COLLECTOR, READER],),
            ).fetchall()
            assert role_rows == [
                (COLLECTOR, False, False, False, False, False, False),
                (READER, False, False, False, False, False, False),
            ]

            # A second fresh database proves safe pre-existing roles are idempotent.
            _execute(admin, "CREATE DATABASE {}", safe_database)
            upgrade_database(
                _url_string(values, safe_database, values["POSTGRES_USER"], values["POSTGRES_PASSWORD"])
            )

            # Real logins exercise inherited collector authority and each refusal class.
            for name, role in roles.items():
                if name == "parent":
                    continue
                attributes = " SUPERUSER" if name == "superuser" else ""
                _execute(admin, f"CREATE ROLE {{}} LOGIN{attributes}", role)
                admin.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                ))
            _execute(admin, "GRANT {} TO {}", COLLECTOR, roles["collector"])
            _execute(admin, "GRANT {} TO {}", READER, roles["reader"])
            _execute(admin, "GRANT {} TO {}", COLLECTOR, roles["extra_update"])
            _execute(admin, "GRANT {} TO {}", COLLECTOR, roles["extra_delete"])
            _execute(admin, "GRANT {} TO {}", COLLECTOR, roles["schema_create"])
            _execute(
                admin,
                "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOBYPASSRLS",
                alternate_group,
            )
            _execute(admin, "GRANT {} TO {}", alternate_group, roles["alternate_login"])

            db_url = _url(values, database, values["POSTGRES_USER"], values["POSTGRES_PASSWORD"])
            admin_engine = create_engine(db_url)
            try:
                with admin_engine.begin() as connection:
                    connection.execute(text(
                        f'GRANT UPDATE ON research.etf_calendar_trusted_acquisitions TO "{roles["extra_update"]}"'
                    ))
                    connection.execute(text(
                        f'GRANT DELETE ON research.etf_calendar_trusted_acquisitions TO "{roles["extra_delete"]}"'
                    ))
                    connection.execute(text(f'GRANT CREATE ON SCHEMA research TO "{roles["schema_create"]}"'))
                    acl = connection.execute(text(
                        """SELECT
                          has_table_privilege(:collector, :table_name, 'SELECT'),
                          has_table_privilege(:collector, :table_name, 'INSERT'),
                          has_table_privilege(:collector, :table_name, 'UPDATE'),
                          has_table_privilege(:collector, :table_name, 'DELETE'),
                          has_table_privilege(:reader, :table_name, 'SELECT'),
                          has_table_privilege(:reader, :table_name, 'INSERT'),
                          (SELECT NOT EXISTS (
                              SELECT 1
                                FROM aclexplode(COALESCE(relation.relacl, acldefault('r', relation.relowner))) acl
                               WHERE acl.grantee = 0
                           ) FROM pg_class relation WHERE relation.oid = to_regclass(:table_name)),
                          has_schema_privilege(:collector, 'research', 'CREATE'),
                          has_schema_privilege(:reader, 'research', 'CREATE')"""
                    ), {"collector": COLLECTOR, "reader": READER, "table_name": persistence.AUTHORITATIVE_TABLE}).one()
                    assert tuple(acl) == (True, True, False, False, True, False, True, False, False)
            finally:
                admin_engine.dispose()

            collector_url = _url(values, database, roles["collector"], password)
            collector_engine = create_engine(collector_url)
            try:
                with collector_engine.connect() as connection:
                    snapshot = persistence.assert_authorized_collector_database_identity(connection)
                    assert snapshot["session_user"] == roles["collector"]
                    assert snapshot["current_user"] == roles["collector"]
            finally:
                collector_engine.dispose()

            # An independently safe alternate group and a login authorized only
            # through it cannot replace the exact parent-bound collector role.
            alternate_engine = create_engine(
                _url(values, database, roles["alternate_login"], password)
            )
            alternate_connects = 0

            @event.listens_for(alternate_engine, "connect")
            def count_alternate_connect(dbapi_connection, connection_record):
                nonlocal alternate_connects
                alternate_connects += 1

            alternate_envelope, _ = _test_envelope(response_digit="9")
            try:
                with monkeypatch.context() as context:
                    context.setattr(persistence, "COLLECTOR_ROLE", alternate_group)
                    with pytest.raises(
                        trusted.TrustedAcquisitionError, match="material values differ"
                    ):
                        persistence._append_with_owned_engine_non_authoritative_test_only(
                            alternate_engine,
                            envelope=alternate_envelope,
                            payload=alternate_envelope["signed_payload"],
                        )
                assert alternate_connects == 0
            finally:
                alternate_engine.dispose()
            for name in (
                "reader", "unrelated", "alternate_login", "superuser", "extra_update",
                "extra_delete", "schema_create",
            ):
                _assert_refuses(_url(values, database, roles[name], password))

            # Owner identities refuse even if separately made collector members.
            for name in ("owner", "table_owner", "schema_owner"):
                _execute(admin, "GRANT {} TO {}", COLLECTOR, roles[name])
            _execute(admin, "ALTER DATABASE {} OWNER TO {}", database, roles["owner"])
            with create_engine(db_url).begin() as connection:
                connection.execute(text(f'ALTER TABLE research.etf_calendar_trusted_acquisitions OWNER TO "{roles["table_owner"]}"'))
                connection.execute(text(f'ALTER SCHEMA research OWNER TO "{roles["schema_owner"]}"'))
            for name in ("owner", "table_owner", "schema_owner"):
                _assert_refuses(_url(values, database, roles[name], password))

            # Restore infrastructure ownership, then prove real commit/new-connection visibility.
            _execute(admin, "ALTER DATABASE {} OWNER TO {}", database, values["POSTGRES_USER"])
            with create_engine(db_url).begin() as connection:
                connection.execute(text(f'ALTER SCHEMA research OWNER TO "{values["POSTGRES_USER"]}"'))
                connection.execute(text(
                    f'ALTER TABLE research.etf_calendar_trusted_acquisitions OWNER TO "{values["POSTGRES_USER"]}"'
                ))
                connection.execute(text(f'GRANT SELECT, INSERT ON research.etf_calendar_trusted_acquisitions TO "{COLLECTOR}"'))
                connection.execute(text(f'REVOKE UPDATE, DELETE ON research.etf_calendar_trusted_acquisitions FROM "{COLLECTOR}"'))
            envelope, verification_key = _test_envelope()
            monkeypatch.setattr(persistence, "rehydrate_verified_envelopes", _test_rehydrator(verification_key))
            engine = create_engine(collector_url)
            try:
                first = persistence._append_with_owned_engine_non_authoritative_test_only(
                    engine, envelope=envelope, payload=envelope["signed_payload"]
                )
                second = persistence._append_with_owned_engine_non_authoritative_test_only(
                    engine, envelope=envelope, payload=envelope["signed_payload"]
                )
                assert first == second == envelope["envelope_sha256"]
                with engine.connect() as connection:
                    assert connection.execute(text(
                        "SELECT count(*) FROM research.etf_calendar_trusted_acquisitions"
                    )).scalar_one() == 1
            finally:
                engine.dispose()

            # A real constraint failure cannot report committed success.
            bad_envelope, bad_key = _test_envelope(
                response_digit="2", available_at="2026-09-15T12:00:01+00:00"
            )
            monkeypatch.setattr(persistence, "rehydrate_verified_envelopes", _test_rehydrator(bad_key))
            engine = create_engine(collector_url)
            try:
                with pytest.raises(
                    trusted.TrustedAcquisitionError, match=persistence.COMMIT_UNCONFIRMED
                ):
                    persistence._append_with_owned_engine_non_authoritative_test_only(
                        engine, envelope=bad_envelope, payload=bad_envelope["signed_payload"]
                    )
            finally:
                engine.dispose()
            with create_engine(db_url).connect() as connection:
                assert connection.execute(text(
                    "SELECT count(*) FROM research.etf_calendar_trusted_acquisitions "
                    "WHERE envelope_sha256 = :identity"
                ), {"identity": bad_envelope["envelope_sha256"]}).scalar_one() == 0

            # Commit followed by a deterministic independent-connect failure is ambiguous.
            confirmation_envelope, confirmation_key = _test_envelope(response_digit="3")
            monkeypatch.setattr(
                persistence, "rehydrate_verified_envelopes", _test_rehydrator(confirmation_key)
            )
            engine = create_engine(collector_url)
            connects = 0

            @event.listens_for(engine, "connect")
            def fail_confirmation(dbapi_connection, connection_record):
                nonlocal connects
                connects += 1
                if connects == 2:
                    raise RuntimeError("deterministic confirmation failure")

            try:
                with pytest.raises(
                    trusted.TrustedAcquisitionError, match=persistence.COMMIT_UNCONFIRMED
                ):
                    persistence._append_with_owned_engine_non_authoritative_test_only(
                        engine,
                        envelope=confirmation_envelope,
                        payload=confirmation_envelope["signed_payload"],
                    )
            finally:
                engine.dispose()
            with create_engine(db_url).connect() as connection:
                assert connection.execute(text(
                    "SELECT count(*) FROM research.etf_calendar_trusted_acquisitions "
                    "WHERE envelope_sha256 = :identity"
                ), {"identity": confirmation_envelope["envelope_sha256"]}).scalar_one() == 1

            conflicting = dict(envelope)
            conflicting["signature"] = "A" * 86 + "=="
            conflicting["envelope_sha256"] = trusted.sha256_json(
                {key: value for key, value in conflicting.items() if key != "envelope_sha256"}
            )
            engine = create_engine(collector_url)
            try:
                with pytest.raises(trusted.TrustedAcquisitionError):
                    persistence._append_with_owned_engine_non_authoritative_test_only(
                        engine, envelope=conflicting, payload=conflicting["signed_payload"]
                    )
            finally:
                engine.dispose()

            # Independently exercise every migration-time unsafe group-role attribute.
            _execute(admin, "DROP DATABASE {} WITH (FORCE)", database)
            _execute(admin, "DROP DATABASE {} WITH (FORCE)", safe_database)
            for group, member in (
                (COLLECTOR, roles["collector"]), (READER, roles["reader"]),
                (COLLECTOR, roles["extra_update"]), (COLLECTOR, roles["schema_create"]),
                (COLLECTOR, roles["extra_delete"]),
                (COLLECTOR, roles["owner"]), (COLLECTOR, roles["table_owner"]),
                (COLLECTOR, roles["schema_owner"]),
            ):
                _execute(admin, "REVOKE {} FROM {}", group, member)
            _execute(admin, "DROP ROLE {}", COLLECTOR)
            _execute(admin, "DROP ROLE {}", READER)
            for target in (COLLECTOR, READER):
                for unsafe in (
                    "LOGIN", "SUPERUSER", "CREATEDB", "CREATEROLE", "REPLICATION", "BYPASSRLS", "MEMBERSHIP",
                ):
                    _execute(admin, "DROP DATABASE IF EXISTS {} WITH (FORCE)", unsafe_database)
                    _execute(admin, "CREATE DATABASE {}", unsafe_database)
                    for fixed in (COLLECTOR, READER):
                        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(fixed)))
                    other = READER if target == COLLECTOR else COLLECTOR
                    _execute(admin, "CREATE ROLE {} NOLOGIN", other)
                    attribute = "NOLOGIN" if unsafe == "MEMBERSHIP" else unsafe
                    _execute(admin, f"CREATE ROLE {{}} {attribute}", target)
                    if unsafe == "MEMBERSHIP":
                        _execute(admin, "CREATE ROLE {} NOLOGIN", roles["parent"])
                        _execute(admin, "GRANT {} TO {}", roles["parent"], target)
                    with pytest.raises(Exception):
                        upgrade_database(_url_string(
                            values, unsafe_database, values["POSTGRES_USER"], values["POSTGRES_PASSWORD"]
                        ))
                    if unsafe == "MEMBERSHIP":
                        _execute(admin, "REVOKE {} FROM {}", roles["parent"], target)
                        _execute(admin, "DROP ROLE {}", roles["parent"])
                    for fixed in (COLLECTOR, READER):
                        admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(fixed)))
        finally:
            for database_name in databases:
                _execute(admin, "DROP DATABASE IF EXISTS {} WITH (FORCE)", database_name)
            existing = {
                row[0] for row in admin.execute(
                    "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)",
                    ([*roles.values(), alternate_group, COLLECTOR, READER],),
                ).fetchall()
            }
            for group, member in (
                (COLLECTOR, roles["collector"]), (READER, roles["reader"]),
                (COLLECTOR, roles["extra_update"]), (COLLECTOR, roles["schema_create"]),
                (COLLECTOR, roles["extra_delete"]),
                (COLLECTOR, roles["owner"]), (COLLECTOR, roles["table_owner"]),
                (COLLECTOR, roles["schema_owner"]), (roles["parent"], COLLECTOR),
                (roles["parent"], READER),
                (alternate_group, roles["alternate_login"]),
            ):
                if group in existing and member in existing:
                    admin.execute(sql.SQL("REVOKE {} FROM {}").format(
                        sql.Identifier(group), sql.Identifier(member)
                    ))
            for role in [*roles.values(), COLLECTOR, READER, alternate_group]:
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
