"""Public-behavior tests for TCMB snapshot materialization."""

from collections.abc import Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from navlens import (
    CurrencyCode,
    CurrencyPair,
    FxRate,
    FxRateKind,
    FxRateObservation,
    MarketDate,
)
from navlens.datasets import FxRateSnapshot, select_fx_rate_snapshots
from navlens.sources.artifact_digest import sha256_bytes
from navlens.sources.tcmb import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TCMB_SOURCE_ID,
    TcmbAcquiredDailyRates,
    TcmbAcquisitionProvenance,
    TcmbDailyRatesDocument,
    TcmbMappingError,
    TcmbRawCacheEntry,
    TcmbRawCacheIntegrityError,
    TcmbResolvedRevisionAvailability,
    TcmbRevisionAvailabilityBasis,
    TcmbRevisionIndex,
    TcmbRevisionRecord,
    TcmbSnapshotMaterializationError,
    TcmbXmlParseError,
    materialize_tcmb_fx_rate_snapshots,
    store_tcmb_raw_artifact,
)

MARKET_DATE = MarketDate(2024, 1, 1)
FIRST_OBSERVED = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
USD_TRY = CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY"))


def _xml(
    *,
    date_text: str = "01.01.2024",
    buying: str = "30.00",
    unit: str = "1",
) -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="{date_text}">
  <Currency Kod="USD" CurrencyCode="USD">
    <Unit>{unit}</Unit>
    <ForexBuying>{buying}</ForexBuying>
    <ForexSelling>30.50</ForexSelling>
    <BanknoteBuying>29.90</BanknoteBuying>
    <BanknoteSelling>30.60</BanknoteSelling>
  </Currency>
</Tarih_Date>""".encode()


def _store_payload(
    root: Path,
    payload: bytes,
    *,
    first_observed_at: datetime = FIRST_OBSERVED,
) -> TcmbRawCacheEntry:
    digest = sha256_bytes(payload)
    provenance = TcmbAcquisitionProvenance(
        source_id=TCMB_SOURCE_ID,
        requested_archive_date=None,
        source_url="https://example.com/tcmb",
        retrieved_at=first_observed_at,
        sha256_hex=digest,
        availability_policy_id="test-policy",
        availability_policy_version="1",
        cache_hit=False,
    )
    acquisition = TcmbAcquiredDailyRates(
        raw_body=payload,
        document=TcmbDailyRatesDocument(date_text="01.01.2024", currencies=()),
        observations=(
            FxRateObservation(
                USD_TRY,
                MARKET_DATE,
                FxRate(1.0),
                FxRateKind("non_cash_buying"),
            ),
        ),
        scheduled_initial_available_at=None,
        provenance=provenance,
    )
    return store_tcmb_raw_artifact(root, acquisition)


def _record(
    entry: TcmbRawCacheEntry,
    *,
    first_observed_at: datetime = FIRST_OBSERVED,
) -> TcmbRevisionRecord:
    return TcmbRevisionRecord(
        sha256_hex=entry.sha256_hex,
        first_observed_at=first_observed_at,
        source_url="https://example.com/tcmb",
        requested_archive_date=None,
        scheduled_initial_available_at=None,
        availability_policy_id="test-policy",
        availability_policy_version="1",
    )


def _index(
    *revisions: TcmbRevisionRecord,
    market_date: MarketDate = MARKET_DATE,
) -> TcmbRevisionIndex:
    return TcmbRevisionIndex(
        schema_version=TCMB_REVISION_INDEX_SCHEMA_VERSION,
        source_id=TCMB_SOURCE_ID,
        market_date=market_date,
        revisions=tuple(revisions),
    )


def _resolved(
    revision: TcmbRevisionRecord,
    *,
    available_at: datetime | None = None,
    basis: TcmbRevisionAvailabilityBasis = TcmbRevisionAvailabilityBasis.first_observed,
) -> TcmbResolvedRevisionAvailability:
    return TcmbResolvedRevisionAvailability(
        sha256_hex=revision.sha256_hex,
        available_at=available_at or revision.first_observed_at,
        first_observed_at=revision.first_observed_at,
        basis=basis,
    )


def test_materializes_typed_snapshots_with_canonical_metadata(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)
    resolved = _resolved(
        revision,
        available_at=FIRST_OBSERVED - timedelta(hours=1),
        basis=TcmbRevisionAvailabilityBasis.scheduled_initial,
    )

    snapshots = materialize_tcmb_fx_rate_snapshots(
        tmp_path,
        _index(revision),
        (resolved,),
    )

    assert len(snapshots) == 4
    assert all(isinstance(snapshot, FxRateSnapshot) for snapshot in snapshots)
    assert all(snapshot.source_id == TCMB_SOURCE_ID for snapshot in snapshots)
    assert all(snapshot.available_at == resolved.available_at for snapshot in snapshots)
    assert all(snapshot.ingested_at == revision.first_observed_at for snapshot in snapshots)
    assert [snapshot.observation.kind for snapshot in snapshots] == [
        FxRateKind("non_cash_buying"),
        FxRateKind("non_cash_selling"),
        FxRateKind("cash_buying"),
        FxRateKind("cash_selling"),
    ]


def test_preserves_revision_and_provider_observation_order(tmp_path: Path) -> None:
    first_entry = _store_payload(tmp_path, _xml(buying="30.00"))
    second_time = FIRST_OBSERVED + timedelta(days=1)
    second_entry = _store_payload(
        tmp_path,
        _xml(buying="31.00"),
        first_observed_at=second_time,
    )
    first = _record(first_entry)
    second = _record(second_entry, first_observed_at=second_time)

    snapshots = materialize_tcmb_fx_rate_snapshots(
        tmp_path,
        _index(first, second),
        (_resolved(first), _resolved(second)),
    )

    assert len(snapshots) == 8
    assert snapshots[0].observation.rate == FxRate(30.0)
    assert snapshots[4].observation.rate == FxRate(31.0)
    assert [snapshot.observation.kind for snapshot in snapshots[:4]] == [
        snapshot.observation.kind for snapshot in snapshots[4:]
    ]


class _SinglePassAvailabilities(Iterable[TcmbResolvedRevisionAvailability]):
    def __init__(self, value: TcmbResolvedRevisionAvailability) -> None:
        self.value = value
        self.iterations = 0

    def __iter__(self) -> Iterator[TcmbResolvedRevisionAvailability]:
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("availability iterable consumed more than once")
        yield self.value


def test_consumes_availability_iterable_once(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)
    values = _SinglePassAvailabilities(_resolved(revision))

    materialize_tcmb_fx_rate_snapshots(tmp_path, _index(revision), values)

    assert values.iterations == 1


@pytest.mark.parametrize("count", [0, 2])
def test_rejects_availability_cardinality_mismatch(tmp_path: Path, count: int) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)

    with pytest.raises(TcmbSnapshotMaterializationError, match="expected 1"):
        materialize_tcmb_fx_rate_snapshots(
            tmp_path,
            _index(revision),
            (_resolved(revision),) * count,
        )


def test_rejects_duplicate_out_of_order_and_mismatched_digests(tmp_path: Path) -> None:
    first_entry = _store_payload(tmp_path, _xml(buying="30.00"))
    second_time = FIRST_OBSERVED + timedelta(days=1)
    second_entry = _store_payload(
        tmp_path,
        _xml(buying="31.00"),
        first_observed_at=second_time,
    )
    first = _record(first_entry)
    second = _record(second_entry, first_observed_at=second_time)
    index = _index(first, second)

    for values in [
        (_resolved(first), _resolved(first)),
        (_resolved(second), _resolved(first)),
    ]:
        with pytest.raises(TcmbSnapshotMaterializationError, match="digest mismatch"):
            materialize_tcmb_fx_rate_snapshots(tmp_path, index, values)


def test_rejects_first_observation_mismatch(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)
    mismatched = TcmbResolvedRevisionAvailability(
        sha256_hex=revision.sha256_hex,
        available_at=FIRST_OBSERVED,
        first_observed_at=FIRST_OBSERVED + timedelta(seconds=1),
        basis=TcmbRevisionAvailabilityBasis.first_observed,
    )

    with pytest.raises(TcmbSnapshotMaterializationError, match="first_observed_at mismatch"):
        materialize_tcmb_fx_rate_snapshots(tmp_path, _index(revision), (mismatched,))


def test_rejects_missing_raw_artifact(tmp_path: Path) -> None:
    payload = _xml()
    entry = TcmbRawCacheEntry(
        sha256_hex=sha256_bytes(payload),
        path=tmp_path / "not-present.xml",
        byte_count=len(payload),
        already_present=False,
    )
    revision = _record(entry)

    with pytest.raises(TcmbSnapshotMaterializationError, match="missing raw artifact"):
        materialize_tcmb_fx_rate_snapshots(
            tmp_path,
            _index(revision),
            (_resolved(revision),),
        )


def test_rejects_corrupted_artifact_with_chained_cause(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)
    entry.path.write_bytes(b"corrupted")

    with pytest.raises(TcmbSnapshotMaterializationError, match="raw cache") as error:
        materialize_tcmb_fx_rate_snapshots(
            tmp_path,
            _index(revision),
            (_resolved(revision),),
        )

    assert isinstance(error.value.__cause__, TcmbRawCacheIntegrityError)


@pytest.mark.parametrize(
    ("payload", "message", "cause_type"),
    [
        (b"<invalid", "parse error", TcmbXmlParseError),
        (_xml(unit="0"), "mapping error", TcmbMappingError),
    ],
)
def test_wraps_parser_and_mapper_errors(
    tmp_path: Path,
    payload: bytes,
    message: str,
    cause_type: type[Exception],
) -> None:
    entry = _store_payload(tmp_path, payload)
    revision = _record(entry)

    with pytest.raises(TcmbSnapshotMaterializationError, match=message) as error:
        materialize_tcmb_fx_rate_snapshots(
            tmp_path,
            _index(revision),
            (_resolved(revision),),
        )

    assert isinstance(error.value.__cause__, cause_type)


def test_rejects_mapped_market_date_mismatch(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml(date_text="02.01.2024"))
    revision = _record(entry)

    with pytest.raises(TcmbSnapshotMaterializationError, match="mapped market date"):
        materialize_tcmb_fx_rate_snapshots(
            tmp_path,
            _index(revision),
            (_resolved(revision),),
        )


def test_generic_selector_hides_future_correction_until_available(tmp_path: Path) -> None:
    initial_entry = _store_payload(tmp_path, _xml(buying="30.00"))
    correction_time = FIRST_OBSERVED + timedelta(days=1)
    correction_entry = _store_payload(
        tmp_path,
        _xml(buying="31.00"),
        first_observed_at=correction_time,
    )
    initial = _record(initial_entry)
    correction = _record(correction_entry, first_observed_at=correction_time)
    snapshots = materialize_tcmb_fx_rate_snapshots(
        tmp_path,
        _index(initial, correction),
        (_resolved(initial), _resolved(correction)),
    )

    before = select_fx_rate_snapshots(
        snapshots,
        source_id=TCMB_SOURCE_ID,
        pair=USD_TRY,
        kind=FxRateKind("non_cash_buying"),
        at_timestamp=correction_time - timedelta(seconds=1),
        pricing_as_of_date=MARKET_DATE,
    )
    after = select_fx_rate_snapshots(
        snapshots,
        source_id=TCMB_SOURCE_ID,
        pair=USD_TRY,
        kind=FxRateKind("non_cash_buying"),
        at_timestamp=correction_time,
        pricing_as_of_date=MARKET_DATE,
    )

    assert before[0].observation.rate == FxRate(30.0)
    assert after[0].observation.rate == FxRate(31.0)


@pytest.mark.parametrize(
    ("root", "index", "values", "message"),
    [
        (object(), object(), object(), "root must"),
        (Path("."), object(), object(), "index must"),
        (
            Path("."),
            _index(_record(TcmbRawCacheEntry("0" * 64, Path("x"), 0, False))),
            object(),
            "must be iterable",
        ),
    ],
)
def test_rejects_invalid_input_types(
    root: object,
    index: object,
    values: object,
    message: str,
) -> None:
    with pytest.raises(TcmbSnapshotMaterializationError, match=message):
        materialize_tcmb_fx_rate_snapshots(
            cast(str | Path, root),
            cast(TcmbRevisionIndex, index),
            cast(Iterable[TcmbResolvedRevisionAvailability], values),
        )


def test_does_not_mutate_inputs_or_raw_artifact(tmp_path: Path) -> None:
    entry = _store_payload(tmp_path, _xml())
    revision = _record(entry)
    index = _index(revision)
    values = [_resolved(revision)]
    raw_before = entry.path.read_bytes()

    materialize_tcmb_fx_rate_snapshots(tmp_path, index, values)

    assert index.revisions == (revision,)
    assert values == [_resolved(revision)]
    assert entry.path.read_bytes() == raw_before
