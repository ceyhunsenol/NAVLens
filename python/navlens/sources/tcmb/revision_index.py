"""Versioned deterministic revision index for acquired TCMB artifacts."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from navlens import MarketDate
from navlens._timestamps import validate_utc_timestamp
from navlens.storage.atomic import atomic_write_bytes

from ._revision_index_contracts import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TcmbRevisionIndex,
    TcmbRevisionIndexUpdate,
    TcmbRevisionRecord,
)
from .acquisition import TcmbAcquiredDailyRates
from .errors import (
    TcmbRawCacheError,
    TcmbRevisionIndexError,
    TcmbRevisionIndexIntegrityError,
)
from .provenance import TCMB_SOURCE_ID
from .raw_cache import TcmbRawCacheEntry, _get_cache_path, load_tcmb_raw_artifact


def _get_index_path(root: Path, market_date: MarketDate) -> Path:
    return root / "tcmb" / "index" / "market-date" / f"{str(market_date)}.json"


def _parse_iso_datetime(value: object) -> datetime:
    try:
        if not isinstance(value, str):
            raise TypeError("datetime must be a string")
        dt = datetime.fromisoformat(value)
        validate_utc_timestamp(dt, "datetime", TcmbRevisionIndexIntegrityError)
        return dt.astimezone(UTC)
    except Exception as exc:
        raise TcmbRevisionIndexIntegrityError(f"invalid datetime '{value}': {exc}") from exc


def _parse_iso_date(value: object) -> date:
    try:
        if not isinstance(value, str):
            raise TypeError("date must be a string")
        return date.fromisoformat(value)
    except Exception as exc:
        raise TcmbRevisionIndexIntegrityError(f"invalid date '{value}': {exc}") from exc


def load_tcmb_revision_index(
    root: str | Path,
    market_date: MarketDate,
) -> TcmbRevisionIndex | None:
    """Load the revision index for a specific market date from disk."""
    if not isinstance(market_date, MarketDate):
        raise TcmbRevisionIndexError("market_date must be a MarketDate")

    root_path = Path(root)
    index_path = _get_index_path(root_path, market_date)

    if not index_path.exists():
        return None

    try:
        content = index_path.read_text(encoding="utf-8")
        data: object = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TcmbRevisionIndexIntegrityError(f"Index file is not valid JSON: {exc}") from exc
    except Exception as exc:
        raise TcmbRevisionIndexIntegrityError(f"Failed to read index: {exc}") from exc

    if not isinstance(data, dict):
        raise TcmbRevisionIndexIntegrityError("JSON root must be an object")

    try:
        document = dict(data)
        schema_version = document.pop("schema_version")
        source_id = document.pop("source_id")
        market_date_str = document.pop("market_date")
        revisions_data = document.pop("revisions")
        if document:
            raise TcmbRevisionIndexIntegrityError(f"unknown fields in index: {sorted(document)}")

        if not isinstance(revisions_data, list):
            raise TcmbRevisionIndexIntegrityError("revisions must be an array")

        revisions: list[TcmbRevisionRecord] = []
        for revision_data in revisions_data:
            if not isinstance(revision_data, dict):
                raise TcmbRevisionIndexIntegrityError("revision must be an object")

            revision = dict(revision_data)
            sha256 = revision.pop("sha256")
            first_obs_str = revision.pop("first_observed_at")
            source_url = revision.pop("source_url")
            req_arch_str = revision.pop("requested_archive_date")
            sched_str = revision.pop("scheduled_initial_available_at")
            pol_id = revision.pop("availability_policy_id")
            pol_ver = revision.pop("availability_policy_version")
            if revision:
                raise TcmbRevisionIndexIntegrityError(
                    f"unknown fields in revision: {sorted(revision)}"
                )

            revisions.append(
                TcmbRevisionRecord(
                    sha256_hex=sha256,
                    first_observed_at=_parse_iso_datetime(first_obs_str),
                    source_url=source_url,
                    requested_archive_date=_parse_iso_date(req_arch_str)
                    if req_arch_str is not None
                    else None,
                    scheduled_initial_available_at=_parse_iso_datetime(sched_str)
                    if sched_str is not None
                    else None,
                    availability_policy_id=pol_id,
                    availability_policy_version=pol_ver,
                )
            )

        indexed_date = _parse_iso_date(market_date_str)
        indexed_market_date = MarketDate(indexed_date.year, indexed_date.month, indexed_date.day)
        if indexed_market_date != market_date:
            raise TcmbRevisionIndexIntegrityError(
                "index market_date does not match its requested storage identity"
            )
        return TcmbRevisionIndex(
            schema_version=schema_version,
            source_id=source_id,
            market_date=indexed_market_date,
            revisions=tuple(revisions),
        )
    except TcmbRevisionIndexIntegrityError:
        raise
    except (KeyError, TypeError, ValueError, TcmbRevisionIndexError) as exc:
        raise TcmbRevisionIndexIntegrityError(f"index validation failed: {exc}") from exc


def _serialize_index(index: TcmbRevisionIndex) -> bytes:
    data = {
        "schema_version": index.schema_version,
        "source_id": index.source_id,
        "market_date": str(index.market_date),
        "revisions": [
            {
                "sha256": r.sha256_hex,
                "first_observed_at": r.first_observed_at.isoformat(),
                "source_url": r.source_url,
                "requested_archive_date": r.requested_archive_date.isoformat()
                if r.requested_archive_date
                else None,
                "scheduled_initial_available_at": r.scheduled_initial_available_at.isoformat()
                if r.scheduled_initial_available_at
                else None,
                "availability_policy_id": r.availability_policy_id,
                "availability_policy_version": r.availability_policy_version,
            }
            for r in index.revisions
        ],
    }
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return f"{json_str}\n".encode()


def record_tcmb_revision(
    root: str | Path,
    acquisition: TcmbAcquiredDailyRates,
    raw_entry: TcmbRawCacheEntry,
) -> TcmbRevisionIndexUpdate:
    """Register an acquired artifact in the deterministic revision index."""
    if not isinstance(acquisition, TcmbAcquiredDailyRates):
        raise TcmbRevisionIndexError("acquisition must be a TcmbAcquiredDailyRates")
    if not isinstance(raw_entry, TcmbRawCacheEntry):
        raise TcmbRevisionIndexError("raw_entry must be a TcmbRawCacheEntry")
    if raw_entry.sha256_hex != acquisition.provenance.sha256_hex:
        raise TcmbRevisionIndexError(
            "raw_entry.sha256_hex does not match acquisition.provenance.sha256_hex"
        )

    market_date = acquisition.observations[0].market_date
    for obs in acquisition.observations:
        if obs.market_date != market_date:
            raise TcmbRevisionIndexError(
                "all observations in an acquisition must have the same market_date"
            )

    root_path = Path(root)
    expected_raw_path = _get_cache_path(root_path, raw_entry.sha256_hex)
    if raw_entry.path != expected_raw_path:
        raise TcmbRevisionIndexError("raw cache entry path does not match its content address")

    try:
        cached_bytes = load_tcmb_raw_artifact(root_path, raw_entry.sha256_hex)
    except TcmbRawCacheError as exc:
        raise TcmbRevisionIndexIntegrityError(
            f"raw artifact integrity validation failed: {exc}"
        ) from exc
    if cached_bytes is None:
        raise TcmbRevisionIndexError("raw artifact is not present in the configured cache root")
    if cached_bytes != acquisition.raw_body or raw_entry.byte_count != len(cached_bytes):
        raise TcmbRevisionIndexError("raw cache entry does not match the acquisition artifact")

    existing_index = load_tcmb_revision_index(root_path, market_date)

    new_record = TcmbRevisionRecord(
        sha256_hex=raw_entry.sha256_hex,
        first_observed_at=acquisition.provenance.retrieved_at,
        source_url=acquisition.provenance.source_url,
        requested_archive_date=acquisition.provenance.requested_archive_date,
        scheduled_initial_available_at=acquisition.scheduled_initial_available_at,
        availability_policy_id=acquisition.provenance.availability_policy_id,
        availability_policy_version=acquisition.provenance.availability_policy_version,
    )

    if existing_index is None:
        new_index = TcmbRevisionIndex(
            schema_version=TCMB_REVISION_INDEX_SCHEMA_VERSION,
            source_id=TCMB_SOURCE_ID,
            market_date=market_date,
            revisions=(new_record,),
        )
        atomic_write_bytes(_get_index_path(root_path, market_date), _serialize_index(new_index))
        return TcmbRevisionIndexUpdate(index=new_index, revision_added=True, index_changed=True)

    record_map = {r.sha256_hex: r for r in existing_index.revisions}

    revision_added = False
    index_changed = False

    if new_record.sha256_hex not in record_map:
        record_map[new_record.sha256_hex] = new_record
        revision_added = True
        index_changed = True
    else:
        existing = record_map[new_record.sha256_hex]
        if new_record.first_observed_at < existing.first_observed_at:
            record_map[new_record.sha256_hex] = new_record
            index_changed = True

    if not index_changed:
        return TcmbRevisionIndexUpdate(
            index=existing_index,
            revision_added=False,
            index_changed=False,
        )

    new_revisions = tuple(
        sorted(record_map.values(), key=lambda r: (r.first_observed_at, r.sha256_hex))
    )

    new_index = TcmbRevisionIndex(
        schema_version=TCMB_REVISION_INDEX_SCHEMA_VERSION,
        source_id=TCMB_SOURCE_ID,
        market_date=market_date,
        revisions=new_revisions,
    )

    atomic_write_bytes(_get_index_path(root_path, market_date), _serialize_index(new_index))
    return TcmbRevisionIndexUpdate(
        index=new_index, revision_added=revision_added, index_changed=True
    )
