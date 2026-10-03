"""Research database environment for the EPIC Y research backtest.

``RESEARCH_BACKTEST_POLICY_V6`` section 9 isolates EPIC Y from the BTC-019
research-only modules, so EPIC Y reads the database environment through this
helper instead of ``btc019_empirical``. It reads the same five ``POSTGRES_*``
names and builds the same ``postgresql+psycopg://`` URL. Neither the URL nor any
value is printed, logged or persisted here; a missing variable is reported by
name only.
"""

from __future__ import annotations

import os
from urllib.parse import quote_plus

DATABASE_ENVIRONMENT_NAMES = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
)


class DatabaseEnvironmentError(ValueError):
    """Some ``POSTGRES_*`` variables are unset or empty; only their names are kept."""

    def __init__(self, missing: tuple[str, ...], *, invalid: tuple[str, ...] = ()) -> None:
        self.missing = missing
        self.invalid = invalid
        message = (f"invalid PostgreSQL environment variables: {list(invalid)}" if invalid
                   else f"missing PostgreSQL environment variables: {list(missing)}")
        super().__init__(message)


def database_url_from_environment() -> str:
    """The research database URL from the five ``POSTGRES_*`` variables.

    User and password are ``quote_plus``-encoded. An unset or empty variable
    raises :class:`DatabaseEnvironmentError` naming every missing variable,
    never a value.
    """

    missing = tuple(name for name in DATABASE_ENVIRONMENT_NAMES if not os.getenv(name))
    if missing:
        raise DatabaseEnvironmentError(missing)
    # POSIX environment decoding can expose non-UTF-8 bytes as surrogates.
    # quote_plus would raise UnicodeEncodeError retaining the credential in
    # .object and repr. Detect those code points before invoking the encoder,
    # without ever constructing a value-bearing exception or exception chain.
    invalid = tuple(
        name for name in ("POSTGRES_USER", "POSTGRES_PASSWORD")
        if any("\ud800" <= char <= "\udfff" for char in os.environ[name])
    )
    if invalid:
        raise DatabaseEnvironmentError((), invalid=invalid)
    return (
        f"postgresql+psycopg://{quote_plus(os.environ['POSTGRES_USER'])}:"
        f"{quote_plus(os.environ['POSTGRES_PASSWORD'])}@{os.environ['POSTGRES_HOST']}:"
        f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
