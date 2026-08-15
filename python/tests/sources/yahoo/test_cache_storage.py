import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from navlens.sources.artifact_digest import sha256_bytes
from navlens.sources.yahoo import (
    YAHOO_SOURCE_ID,
    YahooSecurityPriceCacheError,
    YahooSecurityPriceCacheIntegrityError,
    YahooSecurityPriceRequest,
    YahooSymbolMapping,
)
from navlens.sources.yahoo.cache_identity import YahooCacheIdentity, build_cache_paths
from navlens.sources.yahoo.cache_record import YahooCacheRecord
from navlens.sources.yahoo.cache_storage import (
    is_cache_fresh,
    load_cache_record,
    store_cache_record,
)


def _sample_request() -> YahooSecurityPriceRequest:
    return YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )


def _sample_record(body: bytes = b'{"chart": "sample"}') -> YahooCacheRecord:
    identity = YahooCacheIdentity(
        provider=YAHOO_SOURCE_ID,
        symbol="SYNTH.IS",
        start_date=date(2026, 7, 20),
        end_date=date(2026, 7, 22),
        schema_version=1,
    )
    return YahooCacheRecord(
        identity=identity,
        source_url="https://query1.finance.yahoo.com/v8/finance/chart/SYNTH.IS",
        retrieved_at=datetime(2026, 7, 23, 12, tzinfo=UTC),
        sha256_hex=sha256_bytes(body),
        byte_count=len(body),
        body=body,
    )


def test_atomic_store_and_load_round_trip(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()

    store_cache_record(paths, record)

    loaded = load_cache_record(paths, request)
    assert loaded is not None
    assert loaded.body == record.body
    assert loaded.sha256_hex == record.sha256_hex
    assert loaded.retrieved_at == record.retrieved_at
    assert loaded.source_url == record.source_url
    assert loaded.identity == record.identity
    assert loaded.byte_count == record.byte_count


def test_cache_miss_when_no_files_exist(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)

    assert load_cache_record(paths, request) is None


def test_incomplete_cache_pair_raises_integrity_error(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    # Delete metadata sidecar -> payload exists alone
    paths.metadata.unlink()
    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="incomplete cache pair"):
        load_cache_record(paths, request)

    # Restore metadata, delete payload -> metadata exists alone
    store_cache_record(paths, record)
    paths.payload.unlink()
    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="incomplete cache pair"):
        load_cache_record(paths, request)


def test_rejects_corrupted_payload_byte_count(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    # Corrupt payload bytes with different length
    paths.payload.write_bytes(b'{"chart": "tampered_different_len"}')

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="byte count"):
        load_cache_record(paths, request)


def test_rejects_corrupted_payload_digest(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    # Corrupt payload bytes preserving exact same length
    original_len = len(record.body)
    corrupted_body = b"X" * original_len
    paths.payload.write_bytes(corrupted_body)

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="digest"):
        load_cache_record(paths, request)


def test_rejects_corrupted_metadata_json(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    paths.metadata.write_bytes(b"not-valid-json")

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="decode"):
        load_cache_record(paths, request)


def test_rejects_mismatched_symbol_in_metadata(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    # Mutate symbol in metadata
    meta = json.loads(paths.metadata.read_text(encoding="utf-8"))
    meta["symbol"] = "OTHER.IS"
    paths.metadata.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="symbol"):
        load_cache_record(paths, request)


def test_rejects_mismatched_dates_in_metadata(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    meta = json.loads(paths.metadata.read_text(encoding="utf-8"))
    meta["start_date"] = "2026-07-19"
    paths.metadata.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="start_date"):
        load_cache_record(paths, request)


def test_rejects_unknown_extra_keys_in_metadata(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    meta = json.loads(paths.metadata.read_text(encoding="utf-8"))
    meta["unexpected_key"] = "evil"
    paths.metadata.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="schema"):
        load_cache_record(paths, request)


def test_freshness_within_ttl() -> None:
    record = _sample_record()
    retrieved_at = record.retrieved_at

    # Exactly at retrieval time -> fresh
    assert is_cache_fresh(record, retrieved_at, timedelta(hours=24)) is True

    # 1 hour after -> fresh
    assert is_cache_fresh(record, retrieved_at + timedelta(hours=1), timedelta(hours=24)) is True

    # 25 hours after with 24h TTL -> stale
    assert is_cache_fresh(record, retrieved_at + timedelta(hours=25), timedelta(hours=24)) is False

    # TTL is None -> fresh indefinitely
    assert is_cache_fresh(record, retrieved_at + timedelta(days=365), None) is True


def test_rejects_clock_anomaly_in_freshness() -> None:
    record = _sample_record()
    past_time = record.retrieved_at - timedelta(seconds=1)

    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="clock anomaly"):
        is_cache_fresh(record, past_time, timedelta(hours=24))


def test_rejects_invalid_ttl_types() -> None:
    record = _sample_record()
    with pytest.raises(YahooSecurityPriceCacheError):
        is_cache_fresh(record, record.retrieved_at, "24h")  # type: ignore[arg-type]
    with pytest.raises(YahooSecurityPriceCacheError):
        is_cache_fresh(record, record.retrieved_at, True)  # type: ignore[arg-type]
    with pytest.raises(YahooSecurityPriceCacheError):
        is_cache_fresh(record, record.retrieved_at, timedelta(seconds=-1))


def test_rejects_non_string_retrieved_at_or_sha256_in_metadata(tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)
    record = _sample_record()
    store_cache_record(paths, record)

    # Non-string retrieved_at (e.g. timestamp number)
    meta = json.loads(paths.metadata.read_text(encoding="utf-8"))
    meta["retrieved_at"] = 1784514600
    paths.metadata.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="retrieved_at"):
        load_cache_record(paths, request)

    # Non-string sha256
    meta["retrieved_at"] = record.retrieved_at.isoformat()
    meta["sha256"] = 123456
    paths.metadata.write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(YahooSecurityPriceCacheIntegrityError, match="sha256"):
        load_cache_record(paths, request)


def test_wraps_filesystem_inspection_failure(monkeypatch, tmp_path: Path) -> None:
    request = _sample_request()
    paths = build_cache_paths(tmp_path, request)

    def failing_is_file(self: Path) -> bool:
        raise OSError("permission denied during stat")

    monkeypatch.setattr(Path, "is_file", failing_is_file)
    with pytest.raises(YahooSecurityPriceCacheError, match="failed to inspect cache files"):
        load_cache_record(paths, request)
