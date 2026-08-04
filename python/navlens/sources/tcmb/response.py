"""HTTP response container for raw TCMB XML payloads."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TcmbHttpResponse:
    """Preserve exact TCMB response bytes with their request identity."""

    body: bytes
    source_url: str
    requested_archive_date: date | None
