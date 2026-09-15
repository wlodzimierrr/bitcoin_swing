# Alembic Migrations

This directory contains the migration history for the Bitcoin Swing Predictor
database.

`0001_bootstrap` intentionally creates no application
tables. It exists to prove that a fresh database can be migrated, downgraded,
and recreated before the PostgreSQL schemas are added in `BTC-010`.

Migration `0025_trusted_acquisition` requires the migration credential to be a
database infrastructure authority able to create PostgreSQL roles. It
idempotently provisions the two NOLOGIN least-privilege group roles before any
GRANT. An existing role with login, superuser, createdb, createrole,
replication, or bypass-RLS capability fails the migration closed. Deployment-
specific LOGIN roles may receive membership separately. The authority group
roles themselves may not inherit membership in another role; an existing such
membership also fails closed.

Authoritative trusted-acquisition persistence validates the actual write and
independent confirmation sessions at runtime. `session_user` or `current_user`
must be a member of `btc_calendar_collector_writer`; both identities must be
non-superusers and non-owners of the database, `research` schema, and trusted
acquisition table. Effective `current_user` privileges must be exactly the
required SELECT/INSERT and schema USAGE boundary, without UPDATE, DELETE, or
schema CREATE. The production URL deliberately supplies the same collector
login to both connections, and each connection is validated independently.

The database/table owner and cluster superuser remain infrastructure trust
authorities; these ACLs do not defend against DBA compromise. Normal calendar
collector and scientific-reader credentials must be neither superusers nor
table owners. PUBLIC, collector, and reader have no CREATE privilege on the
`research` schema; the collector receives only SELECT/INSERT on the trusted
acquisition table and the reader receives only SELECT.
