"""Provider-neutral CSV FX-rate source adapter."""

from collections import defaultdict
from datetime import date
from pathlib import Path

from navlens._native import CurrencyPair, FxRateKind, MarketDate
from navlens.datasets.fx_rate_snapshots import FxRateSnapshot
from navlens.datasets.fx_rate_source import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateSourceUnavailableError,
)

from .fx_rates_csv import (
    CsvFxRateSourceError,
    CsvFxRateUnavailableError,
    read_fx_rates_csv,
)


class CsvFxRateSource:
    """Provider-neutral adapter reading FX-rate snapshots from a CSV file."""

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

    def fetch_fx_rates(
        self,
        query: FxRateQuery,
    ) -> tuple[FxRateSnapshot, ...]:
        """Fetch candidate snapshots for the query matching the bound source_id."""
        if not isinstance(query, FxRateQuery):
            raise TypeError("query must be an FxRateQuery instance")

        candidates = self._index.get((query.pair, query.kind), ())
        if not candidates:
            return ()

        start_market_date = _date_to_market_date(query.start_date)
        end_market_date = _date_to_market_date(query.end_date)
        return tuple(
            snapshot
            for snapshot in candidates
            if start_market_date <= snapshot.observation.market_date <= end_market_date
        )

    def _load_and_index(
        self,
    ) -> dict[tuple[CurrencyPair, FxRateKind], tuple[FxRateSnapshot, ...]]:
        try:
            snapshots = read_fx_rates_csv(self._path)
        except CsvFxRateUnavailableError as error:
            raise FxRateSourceUnavailableError(
                f"failed to access CSV FX rates from {self._path}: {error}"
            ) from error
        except CsvFxRateSourceError as error:
            raise FxRateCorruptedSourceDataError(
                f"corrupted CSV FX rate data in {self._path}: {error}"
            ) from error

        grouped: dict[tuple[CurrencyPair, FxRateKind], list[FxRateSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            if snapshot.source_id == self._source_id:
                key = (snapshot.observation.pair, snapshot.observation.kind)
                grouped[key].append(snapshot)

        return {key: tuple(snaps) for key, snaps in grouped.items()}


def _date_to_market_date(d: date) -> MarketDate:
    return MarketDate(d.year, d.month, d.day)
