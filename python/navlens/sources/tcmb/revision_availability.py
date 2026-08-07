"""Deterministic availability resolution of versioned TCMB artifacts."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import validate_sha256_hex

from .errors import TcmbRevisionAvailabilityError
from .revision_index import TcmbRevisionIndex


class TcmbRevisionAvailabilityBasis(StrEnum):
    """Reasoning basis for the resolved availability of a revision."""

    scheduled_initial = "scheduled_initial"
    verified_publication = "verified_publication"
    first_observed = "first_observed"


@dataclass(frozen=True, slots=True)
class TcmbVerifiedPublication:
    """Explicitly verified publication timing for a specific artifact revision."""

    sha256_hex: str
    published_at: datetime

    def __post_init__(self) -> None:
        validate_sha256_hex(self.sha256_hex, "sha256_hex", TcmbRevisionAvailabilityError)
        validate_utc_timestamp(self.published_at, "published_at", TcmbRevisionAvailabilityError)


@dataclass(frozen=True, slots=True)
class TcmbResolvedRevisionAvailability:
    """Deterministically resolved availability timing for an artifact revision."""

    sha256_hex: str
    available_at: datetime
    first_observed_at: datetime
    basis: TcmbRevisionAvailabilityBasis

    def __post_init__(self) -> None:
        validate_sha256_hex(self.sha256_hex, "sha256_hex", TcmbRevisionAvailabilityError)
        validate_utc_timestamp(self.available_at, "available_at", TcmbRevisionAvailabilityError)
        validate_utc_timestamp(
            self.first_observed_at, "first_observed_at", TcmbRevisionAvailabilityError
        )
        if not isinstance(self.basis, TcmbRevisionAvailabilityBasis):
            raise TcmbRevisionAvailabilityError("basis must be a TcmbRevisionAvailabilityBasis")
        if self.available_at > self.first_observed_at:
            raise TcmbRevisionAvailabilityError(
                "available_at must not be later than first_observed_at"
            )


def resolve_tcmb_revision_availability(
    index: TcmbRevisionIndex,
    *,
    initial_revision_sha256_hex: str | None = None,
    verified_publications: Iterable[TcmbVerifiedPublication] = (),
) -> tuple[TcmbResolvedRevisionAvailability, ...]:
    """Resolve the availability timestamp for every observed revision in an index."""
    if not isinstance(index, TcmbRevisionIndex):
        raise TcmbRevisionAvailabilityError("index must be a TcmbRevisionIndex")

    evidence_map: dict[str, TcmbVerifiedPublication] = {}
    if not isinstance(verified_publications, Iterable):
        raise TcmbRevisionAvailabilityError("verified_publications must be iterable")

    for evidence in verified_publications:
        if not isinstance(evidence, TcmbVerifiedPublication):
            raise TcmbRevisionAvailabilityError(
                "verified_publications must contain only TcmbVerifiedPublication instances"
            )
        if evidence.sha256_hex in evidence_map:
            raise TcmbRevisionAvailabilityError(
                f"duplicate verified publication for digest: {evidence.sha256_hex}"
            )
        evidence_map[evidence.sha256_hex] = evidence

    if initial_revision_sha256_hex is not None:
        validate_sha256_hex(
            initial_revision_sha256_hex,
            "initial_revision_sha256_hex",
            TcmbRevisionAvailabilityError,
        )
        if index.revisions[0].sha256_hex != initial_revision_sha256_hex:
            raise TcmbRevisionAvailabilityError(
                "initial_revision_sha256_hex does not match the first revision in the index"
            )

    known_digests = {r.sha256_hex for r in index.revisions}
    for digest in evidence_map:
        if digest not in known_digests:
            raise TcmbRevisionAvailabilityError(
                f"verified publication digest not found in index: {digest}"
            )

    resolved: list[TcmbResolvedRevisionAvailability] = []

    for i, revision in enumerate(index.revisions):
        digest = revision.sha256_hex
        first_observed = revision.first_observed_at
        evidence = evidence_map.get(digest)

        if evidence is not None:
            if evidence.published_at > first_observed:
                raise TcmbRevisionAvailabilityError(
                    f"verified published_at ({evidence.published_at}) is later than "
                    f"first_observed_at ({first_observed}) for digest {digest}"
                )
            available_at = evidence.published_at
            basis = TcmbRevisionAvailabilityBasis.verified_publication
        elif initial_revision_sha256_hex == digest and i == 0:
            scheduled = revision.scheduled_initial_available_at
            if scheduled is None:
                raise TcmbRevisionAvailabilityError(
                    "explicit initial revision has no scheduled_initial_available_at"
                )
            if scheduled > first_observed:
                raise TcmbRevisionAvailabilityError(
                    f"scheduled_initial_available_at ({scheduled}) is later than "
                    f"first_observed_at ({first_observed}) for digest {digest}"
                )
            available_at = scheduled
            basis = TcmbRevisionAvailabilityBasis.scheduled_initial
        else:
            available_at = first_observed
            basis = TcmbRevisionAvailabilityBasis.first_observed

        resolved.append(
            TcmbResolvedRevisionAvailability(
                sha256_hex=digest,
                available_at=available_at,
                first_observed_at=first_observed,
                basis=basis,
            )
        )

    return tuple(resolved)
