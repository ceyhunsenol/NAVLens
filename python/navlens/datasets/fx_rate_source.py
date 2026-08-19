"""Provider-neutral FX rate source protocol, query, and error contracts."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from navlens import CurrencyPair, FxRateKind

from .fx_rate_snapshots import FxRateSnapshot


class FxRateQueryError(ValueError):
    """An FX rate query violates parameter invariants."""


class FxRateSourceError(RuntimeError):
    """Base error for failures during FX rate source operations."""


class FxRateUnmappedPairError(FxRateSourceError):
    """A canonical currency pair has no configured mapping in a provider adapter."""


class FxRateUnsupportedKindError(FxRateSourceError):
    """A requested FX rate kind is unsupported by a provider adapter."""


class FxRateSourceUnavailableError(FxRateSourceError):
    """An FX rate source backend or storage is unreachable or temporarily failed."""


class FxRateCorruptedSourceDataError(FxRateSourceError):
    """FX rate source data violates schema, digest, or integrity invariants."""


@dataclass(frozen=True, slots=True)
class FxRateQuery:
    """Provider-neutral query for FX rate snapshots of one currency pair over a date range."""

    pair: CurrencyPair
    kind: FxRateKind
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.pair, CurrencyPair):
            raise FxRateQueryError("pair must be a CurrencyPair instance")
        if not isinstance(self.kind, FxRateKind):
            raise FxRateQueryError("kind must be an FxRateKind instance")
        if type(self.start_date) is not date:
            raise FxRateQueryError("start_date must be an exact date instance")
        if type(self.end_date) is not date:
            raise FxRateQueryError("end_date must be an exact date instance")
        if self.start_date > self.end_date:
            raise FxRateQueryError(
                f"start_date ({self.start_date}) must be on or before end_date ({self.end_date})"
            )


class FxRateSource(Protocol):
    """Consumer-owned source capability for retrieving FX rate snapshots."""

    @property
    def source_id(self) -> str:
        """Return the canonical source identifier emitted by this source."""
        ...

    def fetch_fx_rates(
        self,
        query: FxRateQuery,
    ) -> tuple[FxRateSnapshot, ...]:
        """Fetch candidate snapshots for the query without collapsing same-date revisions."""
        ...
