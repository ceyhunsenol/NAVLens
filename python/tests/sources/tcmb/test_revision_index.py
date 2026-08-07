import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens import CurrencyCode, CurrencyPair, FxRate, FxRateKind, FxRateObservation, MarketDate
from navlens.sources.artifact_digest import sha256_bytes
from navlens.sources.tcmb.acquisition import TcmbAcquiredDailyRates
from navlens.sources.tcmb.errors import TcmbRevisionIndexError, TcmbRevisionIndexIntegrityError
from navlens.sources.tcmb.provenance import TcmbAcquisitionProvenance
from navlens.sources.tcmb.raw_cache import TcmbRawCacheEntry, store_tcmb_raw_artifact
from navlens.sources.tcmb.records import TcmbDailyRatesDocument
from navlens.sources.tcmb.revision_index import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TcmbRevisionIndex,
    TcmbRevisionIndexUpdate,
    TcmbRevisionRecord,
    load_tcmb_revision_index,
    record_tcmb_revision,
)


def _index_path(root: Path, market_date: MarketDate) -> Path:
    return root / "tcmb" / "index" / "market-date" / f"{market_date}.json"


def _build_dummy_acquisition(
    content: bytes,
    dt: datetime,
    md: MarketDate,
    *,
    source_url: str = "https://example.com/tcmb",
) -> TcmbAcquiredDailyRates:
    sha256_hex = sha256_bytes(content)
    provenance = TcmbAcquisitionProvenance(
        source_id="tcmb",
        requested_archive_date=date(2026, 1, 15),
        source_url=source_url,
        retrieved_at=dt,
        sha256_hex=sha256_hex,
        availability_policy_id="test_policy",
        availability_policy_version="1.0",
        cache_hit=False,
    )
    obs = FxRateObservation(
        CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
        md,
        FxRate(1.0),
        FxRateKind("non_cash_buying"),
    )
    return TcmbAcquiredDailyRates(
        raw_body=content,
        document=TcmbDailyRatesDocument(date_text="2026-01-15", currencies=()),
        observations=(obs,),
        scheduled_initial_available_at=dt,
        provenance=provenance,
    )


def test_tcmb_revision_record_invariants() -> None:
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    valid_sha256 = "a" * 64

    TcmbRevisionRecord(
        sha256_hex=valid_sha256,
        first_observed_at=dt,
        source_url="http",
        requested_archive_date=date(2026, 1, 1),
        scheduled_initial_available_at=dt,
        availability_policy_id="p",
        availability_policy_version="v",
    )

    with pytest.raises(TcmbRevisionIndexError, match="sha256_hex must be"):
        TcmbRevisionRecord("invalid", dt, "http", None, None, "p", "v")

    with pytest.raises(TcmbRevisionIndexError, match="must include a timezone"):
        TcmbRevisionRecord(valid_sha256, datetime(2026, 1, 1), "http", None, None, "p", "v")

    with pytest.raises(TcmbRevisionIndexError, match="source_url cannot be empty"):
        TcmbRevisionRecord(valid_sha256, dt, " ", None, None, "p", "v")

    with pytest.raises(TcmbRevisionIndexError, match="requested_archive_date"):
        TcmbRevisionRecord(valid_sha256, dt, "http", dt, None, "p", "v")

    with pytest.raises(TcmbRevisionIndexError, match="availability_policy_id"):
        TcmbRevisionRecord(valid_sha256, dt, "http", None, None, " ", "v")


def test_tcmb_revision_index_invariants() -> None:
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    valid_sha256 = "a" * 64
    md = MarketDate(2026, 1, 15)

    rec1 = TcmbRevisionRecord(valid_sha256, dt, "http", None, None, "p", "v")

    TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "tcmb", md, (rec1,))

    with pytest.raises(TcmbRevisionIndexError, match="schema_version must be exactly"):
        TcmbRevisionIndex(99, "tcmb", md, (rec1,))

    with pytest.raises(TcmbRevisionIndexError, match="schema_version must be exactly"):
        TcmbRevisionIndex(True, "tcmb", md, (rec1,))

    with pytest.raises(TcmbRevisionIndexError, match="source_id must be exactly"):
        TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "other", md, (rec1,))

    with pytest.raises(TcmbRevisionIndexError, match="non-empty tuple"):
        TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "tcmb", md, ())

    with pytest.raises(TcmbRevisionIndexError, match="duplicate digest"):
        TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "tcmb", md, (rec1, rec1))

    rec2 = TcmbRevisionRecord("b" * 64, dt, "http", None, None, "p", "v")
    with pytest.raises(TcmbRevisionIndexError, match="sorted"):
        TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "tcmb", md, (rec2, rec1))


def test_tcmb_revision_index_update_invariants() -> None:
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    rec1 = TcmbRevisionRecord("a" * 64, dt, "http", None, None, "p", "v")
    idx = TcmbRevisionIndex(TCMB_REVISION_INDEX_SCHEMA_VERSION, "tcmb", md, (rec1,))

    TcmbRevisionIndexUpdate(idx, False, False)
    TcmbRevisionIndexUpdate(idx, True, True)

    with pytest.raises(TcmbRevisionIndexError, match="cannot be True if index_changed is False"):
        TcmbRevisionIndexUpdate(idx, True, False)


def test_first_acquisition_creates_revision(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)

    update = record_tcmb_revision(tmp_path, acq, raw_entry)

    assert update.revision_added is True
    assert update.index_changed is True
    assert len(update.index.revisions) == 1
    assert update.index.revisions[0].sha256_hex == raw_entry.sha256_hex

    index_path = _index_path(tmp_path, md)
    assert index_path.exists()
    assert index_path.name == "2026-01-15.json"


def test_same_digest_does_not_create_second_revision(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry1 = store_tcmb_raw_artifact(tmp_path, acq)
    record_tcmb_revision(tmp_path, acq, raw_entry1)

    dt_later = datetime(2026, 1, 15, 13, 0, tzinfo=UTC)
    acq_later = _build_dummy_acquisition(b"content1", dt_later, md)
    raw_entry2 = store_tcmb_raw_artifact(tmp_path, acq_later)

    update2 = record_tcmb_revision(tmp_path, acq_later, raw_entry2)

    assert update2.revision_added is False
    assert update2.index_changed is False
    assert len(update2.index.revisions) == 1
    assert update2.index.revisions[0].first_observed_at == dt


def test_earlier_first_observed_at_updates_metadata(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md, source_url="https://example.com/later")
    raw_entry1 = store_tcmb_raw_artifact(tmp_path, acq)
    record_tcmb_revision(tmp_path, acq, raw_entry1)

    dt_earlier = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    acq_earlier = _build_dummy_acquisition(
        b"content1", dt_earlier, md, source_url="https://example.com/earlier"
    )
    raw_entry2 = store_tcmb_raw_artifact(tmp_path, acq_earlier)

    update2 = record_tcmb_revision(tmp_path, acq_earlier, raw_entry2)

    assert update2.revision_added is False
    assert update2.index_changed is True
    assert len(update2.index.revisions) == 1
    assert update2.index.revisions[0].first_observed_at == dt_earlier
    assert update2.index.revisions[0].source_url == "https://example.com/earlier"


def test_different_content_creates_second_revision(tmp_path: Path) -> None:
    dt1 = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq1 = _build_dummy_acquisition(b"content1", dt1, md)
    raw_entry1 = store_tcmb_raw_artifact(tmp_path, acq1)
    record_tcmb_revision(tmp_path, acq1, raw_entry1)

    dt2 = datetime(2026, 1, 15, 14, 0, tzinfo=UTC)
    acq2 = _build_dummy_acquisition(b"content2", dt2, md)
    raw_entry2 = store_tcmb_raw_artifact(tmp_path, acq2)
    update2 = record_tcmb_revision(tmp_path, acq2, raw_entry2)

    assert update2.revision_added is True
    assert update2.index_changed is True
    assert len(update2.index.revisions) == 2


def test_load_malformed_json_raises_integrity_error(tmp_path: Path) -> None:
    md = MarketDate(2026, 1, 15)
    index_path = _index_path(tmp_path, md)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("{malformed", encoding="utf-8")

    with pytest.raises(TcmbRevisionIndexIntegrityError):
        load_tcmb_revision_index(tmp_path, md)


def test_load_returns_none_if_missing(tmp_path: Path) -> None:
    md = MarketDate(2026, 1, 15)
    assert load_tcmb_revision_index(tmp_path, md) is None


def test_malformed_json_is_not_overwritten(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    index_path = _index_path(tmp_path, md)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("{malformed", encoding="utf-8")

    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)

    with pytest.raises(TcmbRevisionIndexIntegrityError):
        record_tcmb_revision(tmp_path, acq, raw_entry)

    assert index_path.read_text(encoding="utf-8") == "{malformed"


def test_load_rejects_market_date_that_disagrees_with_storage_identity(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)
    record_tcmb_revision(tmp_path, acq, raw_entry)

    index_path = _index_path(tmp_path, md)
    document = json.loads(index_path.read_text(encoding="utf-8"))
    document["market_date"] = "2026-01-16"
    index_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(TcmbRevisionIndexIntegrityError, match="market_date"):
        load_tcmb_revision_index(tmp_path, md)


def test_missing_raw_artifact_rejected(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)

    raw_entry.path.unlink()

    with pytest.raises(TcmbRevisionIndexError, match="not present"):
        record_tcmb_revision(tmp_path, acq, raw_entry)


def test_corrupted_raw_artifact_rejected(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)
    raw_entry.path.write_bytes(b"corrupted")

    with pytest.raises(TcmbRevisionIndexIntegrityError, match="integrity"):
        record_tcmb_revision(tmp_path, acq, raw_entry)


def test_mismatched_raw_entry_and_acquisition_rejected(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq1 = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry1 = store_tcmb_raw_artifact(tmp_path, acq1)

    acq2 = _build_dummy_acquisition(b"content2", dt, md)

    with pytest.raises(TcmbRevisionIndexError, match="does not match acquisition.provenance"):
        record_tcmb_revision(tmp_path, acq2, raw_entry1)


def test_raw_entry_path_must_match_content_address(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    stored_entry = store_tcmb_raw_artifact(tmp_path, acq)
    mismatched_entry = TcmbRawCacheEntry(
        sha256_hex=stored_entry.sha256_hex,
        path=tmp_path / "wrong.xml",
        byte_count=stored_entry.byte_count,
        already_present=stored_entry.already_present,
    )

    with pytest.raises(TcmbRevisionIndexError, match="path"):
        record_tcmb_revision(tmp_path, acq, mismatched_entry)


def test_json_is_deterministic(tmp_path: Path) -> None:
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
    md = MarketDate(2026, 1, 15)
    acq = _build_dummy_acquisition(b"content1", dt, md)
    raw_entry = store_tcmb_raw_artifact(tmp_path, acq)
    record_tcmb_revision(tmp_path, acq, raw_entry)

    index_path = _index_path(tmp_path, md)
    content = index_path.read_text(encoding="utf-8")

    assert " " not in content
    assert content.endswith("\n")
    assert content.count("\n") == 1
