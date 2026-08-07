"""Validated contracts for the TCMB artifact revision index."""

from dataclasses import dataclass
from datetime import date, datetime

from navlens import MarketDate
from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import validate_sha256_hex

from .errors import TcmbRevisionIndexError
from .provenance import TCMB_SOURCE_ID

TCMB_REVISION_INDEX_SCHEMA_VERSION: int = 1


@dataclass(frozen=True, slots=True)
class TcmbRevisionRecord:
    """Metadata for one observed revision of a TCMB artifact."""

    sha256_hex: str
    first_observed_at: datetime
    source_url: str
    requested_archive_date: date | None
    scheduled_initial_available_at: datetime | None
    availability_policy_id: str
    availability_policy_version: str

    def __post_init__(self) -> None:
        validate_sha256_hex(self.sha256_hex, "sha256_hex", TcmbRevisionIndexError)
        validate_utc_timestamp(self.first_observed_at, "first_observed_at", TcmbRevisionIndexError)
        if not isinstance(self.source_url, str) or not self.source_url.strip():
            raise TcmbRevisionIndexError("source_url cannot be empty")
        if (
            self.requested_archive_date is not None
            and type(self.requested_archive_date) is not date
        ):
            raise TcmbRevisionIndexError("requested_archive_date must be a date or None")
        if self.scheduled_initial_available_at is not None:
            validate_utc_timestamp(
                self.scheduled_initial_available_at,
                "scheduled_initial_available_at",
                TcmbRevisionIndexError,
            )
        if (
            not isinstance(self.availability_policy_id, str)
            or not self.availability_policy_id.strip()
        ):
            raise TcmbRevisionIndexError("availability_policy_id cannot be empty")
        if (
            not isinstance(self.availability_policy_version, str)
            or not self.availability_policy_version.strip()
        ):
            raise TcmbRevisionIndexError("availability_policy_version cannot be empty")


@dataclass(frozen=True, slots=True)
class TcmbRevisionIndex:
    """Versioned revisions observed for one TCMB market date."""

    schema_version: int
    source_id: str
    market_date: MarketDate
    revisions: tuple[TcmbRevisionRecord, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != TCMB_REVISION_INDEX_SCHEMA_VERSION
        ):
            raise TcmbRevisionIndexError(
                f"schema_version must be exactly {TCMB_REVISION_INDEX_SCHEMA_VERSION}"
            )
        if self.source_id != TCMB_SOURCE_ID:
            raise TcmbRevisionIndexError(f"source_id must be exactly '{TCMB_SOURCE_ID}'")
        if not isinstance(self.market_date, MarketDate):
            raise TcmbRevisionIndexError("market_date must be a MarketDate")
        if not isinstance(self.revisions, tuple) or not self.revisions:
            raise TcmbRevisionIndexError("revisions must be a non-empty tuple")

        seen_digests: set[str] = set()
        previous_key: tuple[datetime, str] | None = None
        for revision in self.revisions:
            if not isinstance(revision, TcmbRevisionRecord):
                raise TcmbRevisionIndexError("all revisions must be TcmbRevisionRecord instances")
            if revision.sha256_hex in seen_digests:
                raise TcmbRevisionIndexError(
                    f"duplicate digest in revisions: {revision.sha256_hex}"
                )
            seen_digests.add(revision.sha256_hex)

            revision_key = (revision.first_observed_at, revision.sha256_hex)
            if previous_key is not None and revision_key < previous_key:
                raise TcmbRevisionIndexError(
                    "revisions must be sorted by first_observed_at, then sha256_hex"
                )
            previous_key = revision_key


@dataclass(frozen=True, slots=True)
class TcmbRevisionIndexUpdate:
    """Result of attempting to record an acquisition revision."""

    index: TcmbRevisionIndex
    revision_added: bool
    index_changed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.index, TcmbRevisionIndex):
            raise TcmbRevisionIndexError("index must be a TcmbRevisionIndex")
        if not isinstance(self.revision_added, bool) or not isinstance(self.index_changed, bool):
            raise TcmbRevisionIndexError("revision_added and index_changed must be booleans")
        if self.revision_added and not self.index_changed:
            raise TcmbRevisionIndexError("revision_added cannot be True if index_changed is False")
