"""Orchestration for cached TEFAS price acquisition."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from time import sleep
from typing import Protocol

from .cache import is_cache_fresh, price_cache_paths
from .errors import TefasTransportError
from .parser import parse_price_records
from .policy import TefasAccessPolicy
from .records import TefasPriceRecord
from .request import TefasPriceRequest
from .response import TefasHttpResponse
from .storage import load_response, store_response


class TefasResponseClient(Protocol):
    """Transport capability consumed by price acquisition."""

    def fetch_price_response(
        self, request: TefasPriceRequest, as_of: date
    ) -> TefasHttpResponse: ...


@dataclass(frozen=True, slots=True)
class TefasAcquisitionResult:
    """Return parsed records and the raw artifact that produced them."""

    records: tuple[TefasPriceRecord, ...]
    payload_path: Path
    from_cache: bool


class AcquireTefasPrices:
    """Coordinate cache, transport, storage, and provider parsing."""

    def __init__(
        self,
        client: TefasResponseClient,
        raw_root: str | Path,
        policy: TefasAccessPolicy | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._client = client
        self._raw_root = Path(raw_root)
        self._policy = policy or TefasAccessPolicy()
        self._sleep = sleeper
        self._lock = Lock()

    def acquire(
        self, request: TefasPriceRequest, as_of: date, acquired_at: datetime
    ) -> TefasAcquisitionResult:
        """Return cached or freshly acquired records for one explicit request."""
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise ValueError("acquisition timestamp must include a timezone")
        paths = price_cache_paths(self._raw_root, request, as_of)
        with self._lock:
            cached = is_cache_fresh(paths, acquired_at, self._policy.cache_ttl)
            response = load_response(paths) if cached else self._fetch(request, as_of)
            if not cached:
                store_response(paths, response, request, acquired_at)
        records = parse_price_records(response.payload, request)
        return TefasAcquisitionResult(tuple(records), paths.payload, cached)

    def _fetch(self, request: TefasPriceRequest, as_of: date) -> TefasHttpResponse:
        for attempt in range(1, self._policy.maximum_attempts + 1):
            try:
                return self._client.fetch_price_response(request, as_of)
            except TefasTransportError:
                if attempt == self._policy.maximum_attempts:
                    raise
                delay = max(self._policy.minimum_interval, self._policy.retry_delay(attempt))
                self._sleep(delay.total_seconds())
        raise AssertionError("unreachable retry state")
