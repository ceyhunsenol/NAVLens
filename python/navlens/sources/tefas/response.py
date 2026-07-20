"""Decoded TEFAS HTTP response with its original bytes."""

import json
from dataclasses import dataclass
from typing import cast

from .errors import TefasPayloadError


@dataclass(frozen=True, slots=True)
class TefasHttpResponse:
    """Keep the exact response body beside its validated JSON root."""

    body: bytes
    payload: dict[str, object]
    source_url: str


def decode_response(body: bytes, source_url: str) -> TefasHttpResponse:
    """Decode one response while requiring a JSON object root."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise TefasPayloadError("TEFAS response is not valid JSON") from error
    if not isinstance(payload, dict):
        raise TefasPayloadError("TEFAS response root must be an object")
    return TefasHttpResponse(
        body=body,
        payload=cast(dict[str, object], payload),
        source_url=source_url,
    )
