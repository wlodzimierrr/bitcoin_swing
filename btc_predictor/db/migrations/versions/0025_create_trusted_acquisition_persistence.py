"""create trusted acquisition persistence

Revision ID: 0025_trusted_acquisition
Revises: 0024_actual_trade_entry
Create Date: 2026-09-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0025_trusted_acquisition"
down_revision = "0024_actual_trade_entry"
branch_labels = None
depends_on = None

COLLECTOR_ROLE = "btc_calendar_collector_writer"
READER_ROLE = "btc_predictor_scientific_reader"


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    for role in (COLLECTOR_ROLE, READER_ROLE):
        op.execute(
            f"""
DO $role_bootstrap$
DECLARE
    role_is_unsafe boolean;
BEGIN
    SELECT rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole
           OR rolreplication OR rolbypassrls
           OR EXISTS (
               SELECT 1 FROM pg_catalog.pg_auth_members
                WHERE member = pg_catalog.pg_roles.oid
           )
      INTO role_is_unsafe
      FROM pg_catalog.pg_roles
     WHERE rolname = '{role}';
    IF NOT FOUND THEN
        EXECUTE 'CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB '
                'NOCREATEROLE NOREPLICATION NOBYPASSRLS';
    ELSIF role_is_unsafe THEN
        RAISE EXCEPTION 'trusted-acquisition role {role} has unsafe attributes';
    END IF;
END
$role_bootstrap$;
"""
        )

    op.create_table(
        "etf_calendar_trusted_acquisitions",
        sa.Column("envelope_sha256", sa.String(length=64), nullable=False),
        sa.Column("signed_payload", sa.JSON(), nullable=False),
        sa.Column("signed_payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("signing_key_id", sa.String(length=128), nullable=False),
        sa.Column("signature_algorithm", sa.String(length=16), nullable=False),
        sa.Column("signature", sa.String(length=88), nullable=False),
        sa.Column("response_sha256", sa.String(length=64), nullable=False),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_profile_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=32), nullable=False),
        sa.Column("source_authority_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "signature_algorithm = 'Ed25519'",
            name="ck_etf_calendar_trusted_acquisitions_ed25519",
        ),
        sa.CheckConstraint(
            "response_received_at = acquired_at AND acquired_at = available_at",
            name="ck_etf_calendar_trusted_acquisitions_pit_equal",
        ),
        sa.PrimaryKeyConstraint(
            "envelope_sha256",
            name="pk_research_etf_calendar_trusted_acquisitions",
        ),
        sa.UniqueConstraint(
            "signed_payload_sha256",
            "signing_key_id",
            name="uq_etf_calendar_trusted_acquisitions_payload_key",
        ),
        schema="research",
        comment="Append-only Ed25519-signed ETF-calendar HTTPS acquisitions.",
    )
    table = "research.etf_calendar_trusted_acquisitions"
    op.execute("REVOKE CREATE ON SCHEMA research FROM PUBLIC")
    op.execute(f"REVOKE CREATE ON SCHEMA research FROM {COLLECTOR_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA research FROM {READER_ROLE}")
    op.execute(f"REVOKE ALL ON TABLE {table} FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA research TO {COLLECTOR_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON TABLE {table} TO {COLLECTOR_ROLE}")
    op.execute(f"REVOKE UPDATE, DELETE ON TABLE {table} FROM {COLLECTOR_ROLE}")
    op.execute(f"GRANT USAGE ON SCHEMA research TO {READER_ROLE}")
    op.execute(f"GRANT SELECT ON TABLE {table} TO {READER_ROLE}")
    op.execute(f"REVOKE INSERT, UPDATE, DELETE ON TABLE {table} FROM {READER_ROLE}")


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.drop_table("etf_calendar_trusted_acquisitions", schema="research")
