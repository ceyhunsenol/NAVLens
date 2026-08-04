"""Acquisition provenance for raw TCMB response payloads."""

from dataclasses import dataclass
from datetime import date, datetime

from navlens._timestamps import validate_utc_timestamp

from .availability import TCMB_AVAILABILITY_POLICY_ID, TCMB_AVAILABILITY_POLICY_VERSION
from .errors import TcmbAcquisitionError

TCMB_SOURCE_ID: str = "tcmb"


@dataclass(frozen=True, slots=True)
class TcmbAcquisitionProvenance:
    """Provenance captured for an acquired TCMB daily rates XML response."""

    source_id: str
    requested_archive_date: date | None
    source_url: str
    retrieved_at: datetime
    sha256_hex: str
    availability_policy_id: str
    availability_policy_version: str
    cache_hit: bool

    def __post_init__(self) -> None:
        if self.source_id != TCMB_SOURCE_ID:
            raise TcmbAcquisitionError(f"source_id must be '{TCMB_SOURCE_ID}'")
        if self.requested_archive_date is not None and not isinstance(
            self.requested_archive_date, date
        ):
            raise TcmbAcquisitionError("requested_archive_date must be a date or None")
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise TcmbAcquisitionError("source_url cannot be empty")

        validate_utc_timestamp(self.retrieved_at, "retrieved_at", TcmbAcquisitionError)
        _validate_sha256(self.sha256_hex)

        if not isinstance(self.availability_policy_id, str) or not self.availability_policy_id:
            raise TcmbAcquisitionError("availability_policy_id cannot be empty")
        if (
            not isinstance(self.availability_policy_version, str)
            or not self.availability_policy_version
        ):
            raise TcmbAcquisitionError("availability_policy_version cannot be empty")
        if not isinstance(self.cache_hit, bool):
            raise TcmbAcquisitionError("cache_hit must be a boolean")


def _build_tcmb_provenance(
    source_url: str,
    requested_archive_date: date | None,
    retrieved_at: datetime,
    sha256_hex: str,
    cache_hit: bool = False,
) -> TcmbAcquisitionProvenance:
    """Construct and validate provenance metadata for a TCMB response."""
    return TcmbAcquisitionProvenance(
        source_id=TCMB_SOURCE_ID,
        requested_archive_date=requested_archive_date,
        source_url=source_url,
        retrieved_at=retrieved_at,
        sha256_hex=sha256_hex,
        availability_policy_id=TCMB_AVAILABILITY_POLICY_ID,
        availability_policy_version=TCMB_AVAILABILITY_POLICY_VERSION,
        cache_hit=cache_hit,
    )


def _validate_sha256(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or not all(character in "0123456789abcdef" for character in value)
    ):
        raise TcmbAcquisitionError("sha256_hex must be a 64-character lowercase hex string")
