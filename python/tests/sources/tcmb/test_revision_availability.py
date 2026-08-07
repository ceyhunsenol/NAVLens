"""Public-behavior tests for TCMB revision availability resolution."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta, timezone
from typing import cast

import pytest
from navlens import MarketDate
from navlens.sources.tcmb import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TCMB_SOURCE_ID,
    TcmbResolvedRevisionAvailability,
    TcmbRevisionAvailabilityBasis,
    TcmbRevisionAvailabilityError,
    TcmbRevisionIndex,
    TcmbRevisionRecord,
    TcmbVerifiedPublication,
    resolve_tcmb_revision_availability,
)

FIRST_OBSERVED = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
SCHEDULED = datetime(2024, 1, 1, 11, 0, tzinfo=UTC)


def _record(
    digit: str = "0",
    *,
    first_observed_at: datetime = FIRST_OBSERVED,
    scheduled_initial_available_at: datetime | None = SCHEDULED,
) -> TcmbRevisionRecord:
    return TcmbRevisionRecord(
        sha256_hex=digit * 64,
        first_observed_at=first_observed_at,
        source_url="https://example.com/tcmb",
        requested_archive_date=None,
        scheduled_initial_available_at=scheduled_initial_available_at,
        availability_policy_id="test-policy",
        availability_policy_version="1",
    )


def _index(*revisions: TcmbRevisionRecord) -> TcmbRevisionIndex:
    return TcmbRevisionIndex(
        schema_version=TCMB_REVISION_INDEX_SCHEMA_VERSION,
        source_id=TCMB_SOURCE_ID,
        market_date=MarketDate(2024, 1, 1),
        revisions=tuple(revisions),
    )


def _evidence(digit: str, published_at: datetime) -> TcmbVerifiedPublication:
    return TcmbVerifiedPublication(sha256_hex=digit * 64, published_at=published_at)


def test_conservative_default_uses_first_observation_for_every_revision() -> None:
    first = _record()
    second = _record(
        "1",
        first_observed_at=FIRST_OBSERVED + timedelta(hours=1),
    )

    resolved = resolve_tcmb_revision_availability(_index(first, second))

    assert [item.available_at for item in resolved] == [
        first.first_observed_at,
        second.first_observed_at,
    ]
    assert all(item.basis is TcmbRevisionAvailabilityBasis.first_observed for item in resolved)


def test_explicit_initial_uses_schedule_but_later_revision_does_not() -> None:
    first = _record()
    second = _record(
        "1",
        first_observed_at=FIRST_OBSERVED + timedelta(hours=1),
    )

    resolved = resolve_tcmb_revision_availability(
        _index(first, second),
        initial_revision_sha256_hex=first.sha256_hex,
    )

    assert resolved[0].available_at == SCHEDULED
    assert resolved[0].basis is TcmbRevisionAvailabilityBasis.scheduled_initial
    assert resolved[1].available_at == second.first_observed_at
    assert resolved[1].basis is TcmbRevisionAvailabilityBasis.first_observed


def test_verified_correction_overrides_first_observation() -> None:
    revision = _record()
    publication = _evidence("0", FIRST_OBSERVED - timedelta(minutes=30))

    resolved = resolve_tcmb_revision_availability(
        _index(revision),
        verified_publications=(publication,),
    )

    assert resolved[0].available_at == publication.published_at
    assert resolved[0].basis is TcmbRevisionAvailabilityBasis.verified_publication


def test_verified_initial_overrides_schedule_and_does_not_require_one() -> None:
    revision = _record(scheduled_initial_available_at=None)
    publication = _evidence("0", FIRST_OBSERVED - timedelta(minutes=30))

    resolved = resolve_tcmb_revision_availability(
        _index(revision),
        initial_revision_sha256_hex=revision.sha256_hex,
        verified_publications=(publication,),
    )

    assert resolved[0].available_at == publication.published_at
    assert resolved[0].basis is TcmbRevisionAvailabilityBasis.verified_publication


def test_unknown_evidence_digest_is_rejected() -> None:
    with pytest.raises(TcmbRevisionAvailabilityError, match="not found in index"):
        resolve_tcmb_revision_availability(
            _index(_record()),
            verified_publications=(_evidence("1", SCHEDULED),),
        )


def test_duplicate_evidence_is_rejected() -> None:
    first = _evidence("0", SCHEDULED)
    duplicate = _evidence("0", SCHEDULED + timedelta(minutes=1))

    with pytest.raises(TcmbRevisionAvailabilityError, match="duplicate"):
        resolve_tcmb_revision_availability(
            _index(_record()),
            verified_publications=(first, duplicate),
        )


@pytest.mark.parametrize(
    "published_at",
    [
        datetime(2024, 1, 1, 11, 0),
        datetime(2024, 1, 1, 14, 0, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_verified_publication_requires_utc(published_at: datetime) -> None:
    with pytest.raises(TcmbRevisionAvailabilityError, match="timezone|UTC"):
        _evidence("0", published_at)


def test_verified_publication_after_first_observation_is_rejected() -> None:
    publication = _evidence("0", FIRST_OBSERVED + timedelta(seconds=1))

    with pytest.raises(TcmbRevisionAvailabilityError, match="later than first_observed_at"):
        resolve_tcmb_revision_availability(
            _index(_record()),
            verified_publications=(publication,),
        )


@pytest.mark.parametrize("initial_digit", ["1", "2"])
def test_initial_digest_must_identify_first_revision(initial_digit: str) -> None:
    first = _record()
    second = _record("1", first_observed_at=FIRST_OBSERVED + timedelta(hours=1))

    with pytest.raises(TcmbRevisionAvailabilityError, match="first revision"):
        resolve_tcmb_revision_availability(
            _index(first, second),
            initial_revision_sha256_hex=initial_digit * 64,
        )


def test_explicit_initial_without_schedule_is_rejected() -> None:
    revision = _record(scheduled_initial_available_at=None)

    with pytest.raises(TcmbRevisionAvailabilityError, match="no scheduled"):
        resolve_tcmb_revision_availability(
            _index(revision),
            initial_revision_sha256_hex=revision.sha256_hex,
        )


def test_schedule_after_first_observation_is_rejected() -> None:
    revision = _record(scheduled_initial_available_at=FIRST_OBSERVED + timedelta(seconds=1))

    with pytest.raises(TcmbRevisionAvailabilityError, match="later than first_observed_at"):
        resolve_tcmb_revision_availability(
            _index(revision),
            initial_revision_sha256_hex=revision.sha256_hex,
        )


def test_order_and_inputs_are_preserved() -> None:
    first = _record()
    second = _record("1", first_observed_at=FIRST_OBSERVED + timedelta(hours=1))
    index = _index(first, second)
    evidence = [_evidence("1", FIRST_OBSERVED + timedelta(minutes=30))]

    resolved = resolve_tcmb_revision_availability(
        index,
        verified_publications=evidence,
    )

    assert [item.sha256_hex for item in resolved] == [first.sha256_hex, second.sha256_hex]
    assert index.revisions == (first, second)
    assert evidence == [_evidence("1", FIRST_OBSERVED + timedelta(minutes=30))]


def test_resolved_contract_rejects_availability_after_first_observation() -> None:
    with pytest.raises(TcmbRevisionAvailabilityError, match="must not be later"):
        TcmbResolvedRevisionAvailability(
            sha256_hex="0" * 64,
            available_at=FIRST_OBSERVED + timedelta(seconds=1),
            first_observed_at=FIRST_OBSERVED,
            basis=TcmbRevisionAvailabilityBasis.verified_publication,
        )


@pytest.mark.parametrize(
    ("index", "publications", "message"),
    [
        (object(), (), "index must"),
        (_index(_record()), object(), "must be iterable"),
        (_index(_record()), (object(),), "must contain only"),
    ],
)
def test_resolver_rejects_invalid_input_types(
    index: object,
    publications: object,
    message: str,
) -> None:
    with pytest.raises(TcmbRevisionAvailabilityError, match=message):
        resolve_tcmb_revision_availability(
            cast(TcmbRevisionIndex, index),
            verified_publications=cast(Iterable[TcmbVerifiedPublication], publications),
        )


def test_result_contract_is_strongly_typed() -> None:
    resolved = resolve_tcmb_revision_availability(_index(_record()))[0]

    assert isinstance(resolved, TcmbResolvedRevisionAvailability)
    assert isinstance(resolved.available_at, datetime)
    assert isinstance(resolved.first_observed_at, datetime)
    assert isinstance(resolved.basis, TcmbRevisionAvailabilityBasis)
