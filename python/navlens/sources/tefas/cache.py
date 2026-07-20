"""Deterministic cache identity and freshness for TEFAS responses."""

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from .query import build_price_query
from .request import TefasPriceRequest


@dataclass(frozen=True, slots=True)
class TefasCachePaths:
    """Locate one raw response and its provenance sidecar."""

    payload: Path
    metadata: Path


def price_cache_paths(root: str | Path, request: TefasPriceRequest, as_of: date) -> TefasCachePaths:
    """Derive paths from the effective provider query and acquisition date."""
    identity = {
        "as_of": as_of.isoformat(),
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "query": build_price_query(request, as_of),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    stem = f"price-{as_of.isoformat()}-{sha256(encoded).hexdigest()[:16]}"
    directory = Path(root)
    return TefasCachePaths(directory / f"{stem}.json", directory / f"{stem}.metadata.json")


def is_cache_fresh(paths: TefasCachePaths, checked_at: datetime, ttl: timedelta) -> bool:
    """Return whether both artifacts exist and metadata remains inside its TTL."""
    if not paths.payload.is_file() or not paths.metadata.is_file():
        return False
    try:
        metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
        downloaded_at = datetime.fromisoformat(metadata["downloaded_at"])
        expected_digest = metadata["sha256"]
        source_url = metadata["source_url"]
        actual_digest = sha256(paths.payload.read_bytes()).hexdigest()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    if (
        downloaded_at.tzinfo is None
        or not isinstance(source_url, str)
        or actual_digest != expected_digest
    ):
        return False
    age = checked_at - downloaded_at
    return timedelta(0) <= age <= ttl
