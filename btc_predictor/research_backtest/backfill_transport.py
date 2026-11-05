"""The network transport for RBT-003 Part B: the only backfill module that opens a connection.

Part A's adapters take a caller-supplied :class:`backfill_sources.Transport` and
never import a client; this module supplies the real one. It sends a ``GET``
only to the six hosts Part B uses (Binance's public archive and its listing
bucket, Kraken Futures, Coin Metrics Community, CoinGlass and Tardis's public
exchange metadata) and refuses any other URL before connecting. Transient
failures (a connection error, a timeout, HTTP 429 or a 5xx) are retried with a
growing pause, honouring a short ``Retry-After``; any other status, and the last
attempt's status, is returned unchanged for the fetcher to judge, so an error is
never read as an empty result. Headers (the CoinGlass key among them) are sent
and never logged, printed or put in an exception message.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from btc_predictor.research_backtest.backfill_sources import BackfillRefused, TransportResponse


ALLOWED_HOSTS = frozenset(
    {
        "data.binance.vision",
        "s3-ap-northeast-1.amazonaws.com",
        "futures.kraken.com",
        "community-api.coinmetrics.io",
        "open-api-v4.coinglass.com",
        "api.tardis.dev",
    }
)
USER_AGENT = "bitcoin-swing-research/1.0"
RETRIED_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_SECONDS = 120.0


class TransportFailed(RuntimeError):
    """Every attempt failed without an HTTP response; the message names the URL and the error type only."""


@dataclass
class UrllibTransport:
    """``GET`` with retries, a pause between requests and a host allowlist.

    ``opener`` and ``sleep`` are injectable so the tests never open a socket.
    """

    timeout_seconds: float = 120.0
    pause_seconds: float = 0.2
    attempts: int = 6
    backoff_seconds: float = 2.0
    opener: Callable[..., Any] = urllib.request.urlopen
    sleep: Callable[[float], None] = time.sleep
    requests: int = field(default=0, init=False)
    retries: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.attempts < 1 or self.timeout_seconds <= 0 or self.pause_seconds < 0 or self.backoff_seconds < 0:
            raise ValueError("the transport needs at least one attempt and non-negative pauses")

    def __call__(self, url: str, headers: Mapping[str, str]) -> TransportResponse:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.port is not None or parts.username:
            raise BackfillRefused("PROVIDER_REQUEST_MISMATCH", f"{parts.scheme}://{parts.hostname}: not an RBT-003 provider host")
        request_headers = {"User-Agent": USER_AGENT, **dict(headers)}
        failure = "no attempt"
        for attempt in range(self.attempts):
            if attempt:
                self.retries += 1
            self.sleep(self.pause_seconds if attempt == 0 else self._backoff(attempt, failure))
            self.requests += 1
            try:
                request = urllib.request.Request(url, headers=request_headers, method="GET")
                with self.opener(request, timeout=self.timeout_seconds) as response:
                    status, body = int(response.status), response.read()
            except urllib.error.HTTPError as error:
                status, body = int(error.code), _read_error_body(error)
                if status in RETRIED_STATUSES and attempt + 1 < self.attempts:
                    failure = _retry_after(error) or f"HTTP {status}"
                    continue
                return TransportResponse(status, body)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
                failure = type(error).__name__
                continue
            if status in RETRIED_STATUSES and attempt + 1 < self.attempts:
                failure = f"HTTP {status}"
                continue
            return TransportResponse(status, body)
        raise TransportFailed(f"{url}: no response after {self.attempts} attempts ({failure})")

    def _backoff(self, attempt: int, failure: str) -> float:
        if failure.startswith("retry-after:"):
            return min(float(failure.split(":", 1)[1]), MAX_RETRY_AFTER_SECONDS)
        return self.backoff_seconds * (2 ** (attempt - 1))


def _read_error_body(error: urllib.error.HTTPError) -> bytes:
    try:
        body = error.read()
    except Exception:  # noqa: BLE001 - an unreadable error body is an empty one
        return b""
    return body if isinstance(body, bytes) else b""


def _retry_after(error: urllib.error.HTTPError) -> str | None:
    value = error.headers.get("Retry-After") if error.headers is not None else None
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return f"retry-after:{seconds}" if 0 <= seconds else None
