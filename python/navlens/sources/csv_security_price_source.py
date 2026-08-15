"""Provider-neutral CSV security-price source adapter."""

from collections import defaultdict
from datetime import date
from pathlib import Path

from navlens._native import MarketDate
from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot
from navlens.datasets.security_price_source import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceSourceUnavailableError,
)

from .security_prices_csv import (
    CsvSecurityPriceSourceError,
    CsvSecurityPriceUnavailableError,
    read_security_prices_csv,
)


class CsvSecurityPriceSource:
    """Provider-neutral adapter reading security-price snapshots from a CSV file."""

    def __init__(self, path: str | Path, source_id: str) -> None:
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        self._source_id = source_id.strip()
        self._path = Path(path)
        self._index = self._load_and_index()

    @property
    def source_id(self) -> str:
        """Return the normalized source identifier this adapter is bound to."""
        return self._source_id

    @property
    def path(self) -> Path:
        """Return the underlying CSV path."""
        return self._path

    def fetch_security_prices(
        self,
        query: SecurityPriceQuery,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        """Fetch candidate snapshots for the query matching the bound source_id."""
        if not isinstance(query, SecurityPriceQuery):
            raise TypeError("query must be a SecurityPriceQuery instance")

        candidates = self._index.get(query.normalized_instrument_id, ())
        if not candidates:
            return ()

        start_market_date = _date_to_market_date(query.start_date)
        end_market_date = _date_to_market_date(query.end_date)
        return tuple(
            snapshot
            for snapshot in candidates
            if start_market_date <= snapshot.observation.market_date <= end_market_date
        )

    def _load_and_index(self) -> dict[str, tuple[SecurityPriceSnapshot, ...]]:
        try:
            snapshots = read_security_prices_csv(self._path)
        except CsvSecurityPriceUnavailableError as error:
            raise SecurityPriceSourceUnavailableError(
                f"failed to access CSV security prices from {self._path}: {error}"
            ) from error
        except CsvSecurityPriceSourceError as error:
            raise SecurityPriceCorruptedSourceDataError(
                f"corrupted CSV security price data in {self._path}: {error}"
            ) from error

        grouped: dict[str, list[SecurityPriceSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            if snapshot.source_id == self._source_id:
                grouped[snapshot.observation.instrument_id].append(snapshot)

        return {inst_id: tuple(snaps) for inst_id, snaps in grouped.items()}


def _date_to_market_date(d: date) -> MarketDate:
    return MarketDate(d.year, d.month, d.day)
