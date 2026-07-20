"""Provenance captured for an unmodified TEFAS response artifact."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from navlens.sources.artifact_digest import sha256_artifact

from .request import TefasPriceRequest


@dataclass(frozen=True, slots=True)
class TefasPayloadProvenance:
    """Describe where, when, and for which interval a payload was acquired."""

    source_url: str
    downloaded_at: datetime
    original_filename: str
    sha256_hex: str
    request: TefasPriceRequest


def capture_payload_provenance(
    payload_path: str | Path,
    request: TefasPriceRequest,
    downloaded_at: datetime,
    source_url: str,
) -> TefasPayloadProvenance:
    """Hash a raw response artifact and attach its acquisition context."""
    if downloaded_at.tzinfo is None or downloaded_at.utcoffset() is None:
        raise ValueError("download timestamp must include a timezone")

    path = Path(payload_path)
    return TefasPayloadProvenance(
        source_url=source_url,
        downloaded_at=downloaded_at,
        original_filename=path.name,
        sha256_hex=sha256_artifact(path),
        request=request,
    )
