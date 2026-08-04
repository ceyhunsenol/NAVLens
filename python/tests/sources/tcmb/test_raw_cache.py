from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import navlens.sources.tcmb.raw_cache as raw_cache_module
import pytest
from navlens import CurrencyCode, CurrencyPair, FxRate, FxRateKind, FxRateObservation, MarketDate
from navlens.sources.artifact_digest import sha256_bytes
from navlens.sources.tcmb.acquisition import TcmbAcquiredDailyRates
from navlens.sources.tcmb.errors import TcmbRawCacheError, TcmbRawCacheIntegrityError
from navlens.sources.tcmb.provenance import TCMB_SOURCE_ID, TcmbAcquisitionProvenance
from navlens.sources.tcmb.raw_cache import (
    TcmbRawCacheEntry,
    load_tcmb_raw_artifact,
    store_tcmb_raw_artifact,
)
from navlens.sources.tcmb.records import TcmbDailyRatesDocument


def _build_dummy_acquisition(content: bytes) -> TcmbAcquiredDailyRates:
    sha256_hex = sha256_bytes(content)
    provenance = TcmbAcquisitionProvenance(
        source_id=TCMB_SOURCE_ID,
        requested_archive_date=date(2023, 1, 1),
        source_url="https://example.com/tcmb",
        retrieved_at=datetime(2023, 1, 2, tzinfo=UTC),
        sha256_hex=sha256_hex,
        availability_policy_id="test_policy",
        availability_policy_version="1.0",
        cache_hit=False,
    )
    obs = FxRateObservation(
        CurrencyPair(CurrencyCode("USD"), CurrencyCode("TRY")),
        MarketDate(2023, 1, 1),
        FxRate(1.0),
        FxRateKind("non_cash_buying"),
    )
    return TcmbAcquiredDailyRates(
        raw_body=content,
        document=TcmbDailyRatesDocument(date_text="2023-01-01", currencies=()),
        observations=(obs,),
        scheduled_initial_available_at=None,
        provenance=provenance,
    )


def test_tcmb_raw_cache_entry_invariants(tmp_path: Path) -> None:
    valid_digest = "a" * 64

    entry = TcmbRawCacheEntry(
        sha256_hex=valid_digest,
        path=tmp_path,
        byte_count=100,
        already_present=False,
    )
    assert entry.sha256_hex == valid_digest

    with pytest.raises(TcmbRawCacheError, match="sha256_hex must be"):
        TcmbRawCacheEntry("short", tmp_path, 100, False)

    with pytest.raises(TcmbRawCacheError, match="path must be"):
        TcmbRawCacheEntry(valid_digest, cast(Path, "not_a_path"), 100, False)

    with pytest.raises(TcmbRawCacheError, match="byte_count must be"):
        TcmbRawCacheEntry(valid_digest, tmp_path, -5, False)

    with pytest.raises(TcmbRawCacheError, match="already_present must be"):
        TcmbRawCacheEntry(valid_digest, tmp_path, 100, cast(bool, "not_a_bool"))


@pytest.mark.parametrize(
    "invalid_digest",
    ["A" * 64, "a" * 63, "a" * 65, "g" * 64, "a" * 31 + "/b" + "a" * 31],
)
def test_public_load_rejects_invalid_digest(tmp_path: Path, invalid_digest: str) -> None:
    with pytest.raises(TcmbRawCacheError):
        load_tcmb_raw_artifact(tmp_path, invalid_digest)


def test_store_creates_content_addressed_file(tmp_path: Path) -> None:
    content = b"<test>content</test>"
    acquisition = _build_dummy_acquisition(content)

    entry = store_tcmb_raw_artifact(tmp_path, acquisition)

    assert entry.sha256_hex == acquisition.provenance.sha256_hex
    assert entry.byte_count == len(content)
    assert entry.already_present is False
    assert entry.path.exists()
    assert entry.path.read_bytes() == content
    assert entry.path == (
        tmp_path / "tcmb" / "raw" / "sha256" / entry.sha256_hex[:2] / f"{entry.sha256_hex}.xml"
    )

    assert acquisition.provenance.source_url not in str(entry.path)
    assert "2023" not in str(entry.path)
    assert acquisition.provenance.cache_hit is False
    parent_dir = entry.path.parent
    assert len(list(parent_dir.iterdir())) == 1
    assert entry.path.name.endswith(".xml")


def test_store_twice_sets_already_present_and_does_not_overwrite(tmp_path: Path) -> None:
    content = b"<test>content</test>"
    acquisition = _build_dummy_acquisition(content)

    entry1 = store_tcmb_raw_artifact(tmp_path, acquisition)

    stat1 = entry1.path.stat()

    entry2 = store_tcmb_raw_artifact(tmp_path, acquisition)

    assert entry2.already_present is True
    assert entry2.path == entry1.path

    stat2 = entry2.path.stat()
    assert stat1.st_mtime_ns == stat2.st_mtime_ns


def test_different_contents_create_different_paths(tmp_path: Path) -> None:
    acq1 = _build_dummy_acquisition(b"rev1")
    acq2 = _build_dummy_acquisition(b"rev2")

    entry1 = store_tcmb_raw_artifact(tmp_path, acq1)
    entry2 = store_tcmb_raw_artifact(tmp_path, acq2)

    assert entry1.path != entry2.path
    assert entry1.path.exists()
    assert entry2.path.exists()


def test_load_returns_exact_bytes(tmp_path: Path) -> None:
    content = b"<test>load</test>"
    acq = _build_dummy_acquisition(content)
    store_tcmb_raw_artifact(tmp_path, acq)

    loaded = load_tcmb_raw_artifact(tmp_path, acq.provenance.sha256_hex)
    assert loaded == content


def test_load_returns_none_for_missing(tmp_path: Path) -> None:
    digest = "a" * 64
    assert load_tcmb_raw_artifact(tmp_path, digest) is None


def test_load_validates_digest_format(tmp_path: Path) -> None:
    with pytest.raises(TcmbRawCacheError):
        load_tcmb_raw_artifact(tmp_path, "invalid")


def test_store_rejects_acquisition_with_mismatched_digest(tmp_path: Path) -> None:
    acq = _build_dummy_acquisition(b"correct")

    class MismatchedAcquisition:
        raw_body = b"tampered"
        provenance = acq.provenance

    with pytest.raises(TcmbRawCacheError, match="does not match provenance"):
        store_tcmb_raw_artifact(tmp_path, cast(TcmbAcquiredDailyRates, MismatchedAcquisition()))


def test_store_and_load_detect_corrupted_files(tmp_path: Path) -> None:
    content = b"<test>corrupt</test>"
    acq = _build_dummy_acquisition(content)
    entry = store_tcmb_raw_artifact(tmp_path, acq)

    entry.path.write_bytes(b"corrupted content")

    with pytest.raises(TcmbRawCacheIntegrityError, match="corrupted"):
        load_tcmb_raw_artifact(tmp_path, acq.provenance.sha256_hex)

    with pytest.raises(TcmbRawCacheIntegrityError, match="corrupted"):
        store_tcmb_raw_artifact(tmp_path, acq)


def test_store_uses_atomic_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    atomic_called = False

    def fake_atomic_write(path: Path, content: bytes) -> None:
        nonlocal atomic_called
        atomic_called = True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    monkeypatch.setattr(raw_cache_module, "atomic_write_bytes", fake_atomic_write)

    acq = _build_dummy_acquisition(b"atomic")
    store_tcmb_raw_artifact(tmp_path, acq)

    assert atomic_called is True
