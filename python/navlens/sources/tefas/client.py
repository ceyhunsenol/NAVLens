"""HTTP transport for the TEFAS price-history JSON endpoint."""

import json
from datetime import date
from typing import cast
from urllib.error import URLError
from urllib.request import Request, urlopen

from .errors import TefasPayloadError, TefasTransportError
from .query import build_price_query
from .request import TefasPriceRequest

PRICE_ENDPOINT = "https://www.tefas.gov.tr/api/funds/fonFiyatBilgiGetir"


class TefasHttpClient:
    """Fetch raw provider payloads without parsing financial records."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        self._timeout_seconds = timeout_seconds

    def fetch_price_payload(self, request: TefasPriceRequest, as_of: date) -> dict[str, object]:
        """POST one fund query and return its decoded JSON object."""
        body = json.dumps(build_price_query(request, as_of)).encode("utf-8")
        http_request = Request(
            PRICE_ENDPOINT,
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read())
        except (URLError, TimeoutError) as error:
            raise TefasTransportError(f"TEFAS request failed: {error}") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise TefasPayloadError("TEFAS response is not valid JSON") from error
        if not isinstance(payload, dict):
            raise TefasPayloadError("TEFAS response root must be an object")
        return cast(dict[str, object], payload)
