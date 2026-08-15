from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot

from .acquirer import YahooChartResponseClient, YahooSecurityPriceAcquirer
from .client import YahooChartHttpClient
from .policy import YahooAcquisitionPolicy
from .provenance import YahooSecurityPriceAcquisitionResult
from .request import YahooSecurityPriceRequest


def _utc_now() -> datetime:
    return datetime.now(UTC)


class YahooSecurityPriceSource:
    """Acquire unadjusted daily closes from Yahoo's experimental chart boundary."""

    def __init__(
        self,
        client: YahooChartResponseClient | None = None,
        cache_root: str | Path | None = None,
        policy: YahooAcquisitionPolicy | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._client = client or YahooChartHttpClient()
        self._acquirer = YahooSecurityPriceAcquirer(
            client=self._client,
            cache_root=cache_root,
            policy=policy,
            clock=clock,
        )

    def fetch(
        self,
        request: YahooSecurityPriceRequest,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        """Fetch and map one instrument without fabricating historical publication times."""
        return self._acquirer.acquire(request).snapshots

    def acquire(
        self,
        request: YahooSecurityPriceRequest,
        checked_at: datetime | None = None,
    ) -> YahooSecurityPriceAcquisitionResult:
        """Acquire snapshots together with auditable cache and fallback provenance."""
        return self._acquirer.acquire(request, checked_at=checked_at)
