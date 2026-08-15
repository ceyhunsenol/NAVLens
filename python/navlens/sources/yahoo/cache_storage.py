"""Atomic persistence and strict integrity validation for cached Yahoo responses."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import sha256_bytes, validate_sha256_hex
from navlens.storage.atomic import atomic_write_bytes

from .cache_identity import YAHOO_CACHE_SCHEMA_VERSION, YahooCacheIdentity, YahooCachePaths
from .cache_record import YahooCacheRecord
from .errors import YahooSecurityPriceCacheError, YahooSecurityPriceCacheIntegrityError
from .request import YahooSecurityPriceRequest
from .snapshots import YAHOO_SOURCE_ID

_REQUIRED_METADATA_KEYS = frozenset(
    {
        "byte_count",
        "end_date",
        "provider",
        "retrieved_at",
        "schema_version",
        "sha256",
        "source_url",
        "start_date",
        "symbol",
    }
)


def store_cache_record(paths: YahooCachePaths, record: YahooCacheRecord) -> None:
    """Atomically write raw payload bytes followed by metadata sidecar commit marker."""
    if not isinstance(paths, YahooCachePaths):
        raise YahooSecurityPriceCacheError("paths must be a YahooCachePaths instance")
    if not isinstance(record, YahooCacheRecord):
        raise YahooSecurityPriceCacheError("record must be a YahooCacheRecord instance")

    metadata = {
        "byte_count": record.byte_count,
        "end_date": record.identity.end_date.isoformat(),
        "provider": record.identity.provider,
        "retrieved_at": record.retrieved_at.isoformat(),
        "schema_version": record.identity.schema_version,
        "sha256": record.sha256_hex,
        "source_url": record.source_url,
        "start_date": record.identity.start_date.isoformat(),
        "symbol": record.identity.symbol,
    }
    encoded_metadata = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")

    try:
        atomic_write_bytes(paths.payload, record.body)
        atomic_write_bytes(paths.metadata, encoded_metadata)
    except OSError as error:
        raise YahooSecurityPriceCacheError(f"failed to store cache record: {error}") from error


def load_cache_record(
    paths: YahooCachePaths,
    request: YahooSecurityPriceRequest,
) -> YahooCacheRecord | None:
    """Load and strictly validate a cached response against its expected identity and digest."""
    if not isinstance(paths, YahooCachePaths):
        raise YahooSecurityPriceCacheError("paths must be a YahooCachePaths instance")
    if not isinstance(request, YahooSecurityPriceRequest):
        raise YahooSecurityPriceCacheError("request must be a YahooSecurityPriceRequest")

    try:
        payload_exists = paths.payload.is_file()
        metadata_exists = paths.metadata.is_file()
    except OSError as error:
        raise YahooSecurityPriceCacheError(f"failed to inspect cache files: {error}") from error

    if not payload_exists and not metadata_exists:
        return None
    if payload_exists != metadata_exists:
        raise YahooSecurityPriceCacheIntegrityError(
            "incomplete cache pair: missing payload or metadata commit marker"
        )

    metadata = _read_and_decode_metadata(paths.metadata)
    _validate_metadata_fields(metadata, request)

    body = _read_payload_bytes(paths.payload)
    if len(body) != metadata["byte_count"]:
        raise YahooSecurityPriceCacheIntegrityError(
            "cached payload byte count does not match metadata"
        )
    if sha256_bytes(body) != metadata["sha256"]:
        raise YahooSecurityPriceCacheIntegrityError("cached payload digest does not match metadata")

    retrieved_at = datetime.fromisoformat(metadata["retrieved_at"])  # type: ignore[arg-type]
    identity = YahooCacheIdentity(
        provider=str(metadata["provider"]),
        symbol=str(metadata["symbol"]),
        start_date=request.start_date,
        end_date=request.end_date,
        schema_version=int(metadata["schema_version"]),  # type: ignore[arg-type]
    )
    return YahooCacheRecord(
        identity=identity,
        source_url=str(metadata["source_url"]),
        retrieved_at=retrieved_at,
        sha256_hex=str(metadata["sha256"]),
        byte_count=int(metadata["byte_count"]),  # type: ignore[arg-type]
        body=body,
    )


def is_cache_fresh(
    record: YahooCacheRecord,
    checked_at: datetime,
    ttl: timedelta | None,
) -> bool:
    """Return whether a valid cache record is fresh relative to checked_at and TTL."""
    if not isinstance(record, YahooCacheRecord):
        raise YahooSecurityPriceCacheError("record must be a YahooCacheRecord")
    validate_utc_timestamp(checked_at, "checked_at", YahooSecurityPriceCacheError)

    if checked_at < record.retrieved_at:
        raise YahooSecurityPriceCacheIntegrityError(
            "clock anomaly: check time precedes cache retrieval time"
        )
    if ttl is None:
        return True
    if not isinstance(ttl, timedelta) or isinstance(ttl, bool) or ttl < timedelta(0):
        raise YahooSecurityPriceCacheError("ttl must be a non-negative timedelta or None")
    return (checked_at - record.retrieved_at) <= ttl


def _read_and_decode_metadata(path: Path) -> dict[str, object]:
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise YahooSecurityPriceCacheIntegrityError(
            f"failed to read or decode cache metadata: {error}"
        ) from error
    if not isinstance(data, dict):
        raise YahooSecurityPriceCacheIntegrityError("metadata JSON root must be an object")
    return data


def _validate_metadata_fields(
    metadata: dict[str, object],
    request: YahooSecurityPriceRequest,
) -> None:
    if set(metadata.keys()) != _REQUIRED_METADATA_KEYS:
        raise YahooSecurityPriceCacheIntegrityError("metadata keys do not match expected schema")

    schema_version = metadata["schema_version"]
    if (
        type(schema_version) is not int
        or isinstance(schema_version, bool)
        or schema_version != YAHOO_CACHE_SCHEMA_VERSION
    ):
        raise YahooSecurityPriceCacheIntegrityError("metadata schema_version is invalid")

    if metadata["provider"] != YAHOO_SOURCE_ID:
        raise YahooSecurityPriceCacheIntegrityError("metadata provider does not match Yahoo source")
    if metadata["symbol"] != request.mapping.normalized_provider_symbol:
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata symbol does not match requested symbol"
        )
    if metadata["start_date"] != request.start_date.isoformat():
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata start_date does not match requested start_date"
        )
    if metadata["end_date"] != request.end_date.isoformat():
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata end_date does not match requested end_date"
        )

    source_url = metadata["source_url"]
    if not isinstance(source_url, str) or not source_url.strip():
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata source_url must be a non-empty string"
        )

    raw_retrieved_at = metadata["retrieved_at"]
    if not isinstance(raw_retrieved_at, str) or not raw_retrieved_at.strip():
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata retrieved_at must be an ISO datetime string"
        )
    try:
        retrieved_at = datetime.fromisoformat(raw_retrieved_at)
        validate_utc_timestamp(retrieved_at, "retrieved_at", YahooSecurityPriceCacheIntegrityError)
    except (ValueError, TypeError) as error:
        raise YahooSecurityPriceCacheIntegrityError(
            f"invalid retrieved_at in metadata: {error}"
        ) from error

    raw_sha256 = metadata["sha256"]
    if not isinstance(raw_sha256, str):
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata sha256 must be a 64-character lowercase hex string"
        )
    validate_sha256_hex(raw_sha256, "sha256", YahooSecurityPriceCacheIntegrityError)

    byte_count = metadata["byte_count"]
    if type(byte_count) is not int or isinstance(byte_count, bool) or byte_count < 0:
        raise YahooSecurityPriceCacheIntegrityError(
            "metadata byte_count must be a non-negative integer"
        )


def _read_payload_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise YahooSecurityPriceCacheIntegrityError(
            f"failed to read cache payload: {error}"
        ) from error
