"""Revision-safe acquisition capability for TCMB daily rates XML documents."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from navlens import FxRateObservation, MarketCalendar
from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import sha256_bytes

from .availability import initial_tcmb_available_at
from .errors import TcmbAcquisitionError
from .mapper import map_tcmb_daily_rates
from .parser import parse_tcmb_daily_rates_xml
from .provenance import TcmbAcquisitionProvenance, _build_tcmb_provenance
from .records import TcmbDailyRatesDocument
from .response import TcmbHttpResponse


@runtime_checkable
class TcmbResponseClient(Protocol):
    """Consumer-owned transport interface for fetching raw TCMB responses."""

    def fetch_daily_rates_response(
        self,
        archive_date: date | None = None,
    ) -> TcmbHttpResponse: ...


@dataclass(frozen=True, slots=True)
class TcmbAcquiredDailyRates:
    """Preserve one parsed and mapped artifact without assigning snapshot visibility."""

    raw_body: bytes
    document: TcmbDailyRatesDocument
    observations: tuple[FxRateObservation, ...]
    scheduled_initial_available_at: datetime | None
    provenance: TcmbAcquisitionProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.raw_body, bytes):
            raise TcmbAcquisitionError("raw_body must contain exact bytes")
        if not isinstance(self.document, TcmbDailyRatesDocument):
            raise TcmbAcquisitionError("document must be a TcmbDailyRatesDocument")
        if not isinstance(self.observations, tuple) or not self.observations:
            raise TcmbAcquisitionError("observations must be a non-empty tuple")
        if not all(isinstance(item, FxRateObservation) for item in self.observations):
            raise TcmbAcquisitionError("observations must contain FxRateObservation values")
        if self.scheduled_initial_available_at is not None:
            validate_utc_timestamp(
                self.scheduled_initial_available_at,
                "scheduled_initial_available_at",
                TcmbAcquisitionError,
            )
        if not isinstance(self.provenance, TcmbAcquisitionProvenance):
            raise TcmbAcquisitionError("provenance must be a TcmbAcquisitionProvenance")
        if sha256_bytes(self.raw_body) != self.provenance.sha256_hex:
            raise TcmbAcquisitionError("raw_body does not match the provenance SHA-256 digest")


def acquire_tcmb_daily_rates(
    client: TcmbResponseClient,
    *,
    archive_date: date | None,
    calendar: MarketCalendar,
    retrieved_at: datetime,
) -> TcmbAcquiredDailyRates:
    """Acquire, hash, parse, map, and capture provenance for one TCMB XML payload."""
    validate_utc_timestamp(retrieved_at, "retrieved_at", TcmbAcquisitionError)

    response = client.fetch_daily_rates_response(archive_date)
    if response.requested_archive_date != archive_date:
        raise TcmbAcquisitionError("response archive date does not match the acquisition request")
    sha256_hex = sha256_bytes(response.body)

    document = parse_tcmb_daily_rates_xml(response.body)
    observations = map_tcmb_daily_rates(document)

    market_date = observations[0].market_date
    scheduled_initial_available_at = initial_tcmb_available_at(market_date, calendar)

    provenance = _build_tcmb_provenance(
        source_url=response.source_url,
        requested_archive_date=archive_date,
        retrieved_at=retrieved_at,
        sha256_hex=sha256_hex,
        cache_hit=False,
    )

    return TcmbAcquiredDailyRates(
        raw_body=response.body,
        document=document,
        observations=observations,
        scheduled_initial_available_at=scheduled_initial_available_at,
        provenance=provenance,
    )
