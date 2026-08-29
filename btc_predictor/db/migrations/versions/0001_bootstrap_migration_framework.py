"""bootstrap migration framework

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-08-24 00:00:00.000000
"""

from __future__ import annotations


revision = "0001_bootstrap"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Initialize Alembic revision tracking."""


def downgrade() -> None:
    """Return to an unmigrated schema state."""
