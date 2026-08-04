"""HTTP transport client for fetching raw TCMB daily rates XML documents."""

import math
from datetime import date
from urllib.error import URLError
from urllib.request import Request, urlopen

from .errors import TcmbTransportError
from .response import TcmbHttpResponse

_TCMB_BASE_URL = "https://www.tcmb.gov.tr/kurlar"


def _build_tcmb_url(archive_date: date | None) -> str:
    if archive_date is None:
        return f"{_TCMB_BASE_URL}/today.xml"
    year_month = archive_date.strftime("%Y%m")
    day_month_year = archive_date.strftime("%d%m%Y")
    return f"{_TCMB_BASE_URL}/{year_month}/{day_month_year}.xml"


class TcmbHttpClient:
    """Fetch raw TCMB daily rates XML payloads over HTTP."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a finite positive number")
        self._timeout_seconds = timeout_seconds

    def fetch_daily_rates_response(
        self,
        archive_date: date | None = None,
    ) -> TcmbHttpResponse:
        url = _build_tcmb_url(archive_date)
        request = Request(
            url,
            headers={"Accept": "application/xml, text/xml"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read()
        except (URLError, TimeoutError) as error:
            raise TcmbTransportError(f"TCMB request to '{url}' failed: {error}") from error

        return TcmbHttpResponse(
            body=body,
            source_url=url,
            requested_archive_date=archive_date,
        )
