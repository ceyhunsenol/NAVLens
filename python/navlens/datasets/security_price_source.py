"""Provider-neutral security price source protocol, query, and error contracts."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from .security_price_snapshots import SecurityPriceSnapshot


class SecurityPriceQueryError(ValueError):
    """A security price query violates parameter invariants."""


class SecurityPriceSourceError(RuntimeError):
    """Base error for failures during security price source operations."""


class SecurityPriceUnmappedInstrumentError(SecurityPriceSourceError):
    """A canonical instrument ID has no configured mapping in a provider adapter."""


class SecurityPriceSourceUnavailableError(SecurityPriceSourceError):
    """A security price source backend or storage is unreachable or temporarily failed."""


class SecurityPriceCorruptedSourceDataError(SecurityPriceSourceError):
    """Security price source data violates schema, digest, or integrity invariants."""


@dataclass(frozen=True, slots=True)
class SecurityPriceQuery:
    """Provider-neutral query for security price snapshots of one instrument over a date range."""

    instrument_id: str
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, str) or not self.instrument_id.strip():
            raise SecurityPriceQueryError("instrument_id must be a non-empty string")
        if type(self.start_date) is not date:
            raise SecurityPriceQueryError("start_date must be an exact date instance")
        if type(self.end_date) is not date:
            raise SecurityPriceQueryError("end_date must be an exact date instance")
        if self.start_date > self.end_date:
            raise SecurityPriceQueryError(
                f"start_date ({self.start_date}) must be on or before end_date ({self.end_date})"
            )

    @property
    def normalized_instrument_id(self) -> str:
        """Return the trimmed canonical instrument identifier."""
        return self.instrument_id.strip()


class SecurityPriceSource(Protocol):
    """Consumer-owned source capability for retrieving security price snapshots."""

    @property
    def source_id(self) -> str:
        """Return the canonical source identifier emitted by this source."""
        ...

    def fetch_security_prices(
        self,
        query: SecurityPriceQuery,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        """Fetch candidate snapshots for the query without collapsing same-date revisions."""
        ...
