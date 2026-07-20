"""Atomic local storage for raw TEFAS responses and provenance."""

import json
from datetime import datetime

from navlens.storage import atomic_write_bytes

from .cache import TefasCachePaths
from .provenance import TefasPayloadProvenance, capture_payload_provenance
from .request import TefasPriceRequest
from .response import TefasHttpResponse, decode_response


def store_response(
    paths: TefasCachePaths,
    response: TefasHttpResponse,
    request: TefasPriceRequest,
    downloaded_at: datetime,
) -> TefasPayloadProvenance:
    """Atomically persist exact bytes followed by their provenance sidecar."""
    paths.payload.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(paths.payload, response.body)
    provenance = capture_payload_provenance(
        paths.payload, request, downloaded_at, response.source_url
    )
    metadata = {
        "source_url": provenance.source_url,
        "downloaded_at": provenance.downloaded_at.isoformat(),
        "original_filename": provenance.original_filename,
        "sha256": provenance.sha256_hex,
        "fund_code": request.normalized_fund_code,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
    }
    atomic_write_bytes(
        paths.metadata,
        json.dumps(metadata, sort_keys=True).encode("utf-8"),
    )
    return provenance


def load_response(paths: TefasCachePaths) -> TefasHttpResponse:
    """Load and decode a previously stored raw response."""
    metadata = json.loads(paths.metadata.read_text(encoding="utf-8"))
    return decode_response(paths.payload.read_bytes(), metadata["source_url"])
