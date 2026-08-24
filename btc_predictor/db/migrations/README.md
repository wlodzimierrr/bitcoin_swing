# Alembic Migrations

This directory contains the migration history for the Bitcoin Swing Predictor
database.

`0001_bootstrap_migration_framework` intentionally creates no application
tables. It exists to prove that a fresh database can be migrated, downgraded,
and recreated before the PostgreSQL schemas are added in `BTC-010`.
