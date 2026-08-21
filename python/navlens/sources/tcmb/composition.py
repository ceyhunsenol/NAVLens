"""Shared composition builder for TCMB FX rate sources."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from navlens import MarketCalendar, MarketDate, SessionKind, SessionOverride

from .client import TcmbHttpClient
from .errors import TcmbAcquisitionError
from .orchestration import (
    TcmbAcquisitionContext,
    TcmbCachePolicy,
    TcmbResponseClient,
)
from .source import (
    TcmbAcquisitionContextFactory,
    TcmbFxRateSource,
    TcmbOrchestrationSnapshotLoader,
)

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class TcmbSourceSettings:
    """Validated settings for constructing a TCMB FX rate source."""

    cache_root: Path
    cache_policy: TcmbCachePolicy
    http_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.cache_root, Path):
            raise TcmbAcquisitionError("cache_root must be a Path instance")
        if not isinstance(self.cache_policy, TcmbCachePolicy):
            raise TcmbAcquisitionError("cache_policy must be a TcmbCachePolicy instance")
        if isinstance(self.http_timeout_seconds, bool) or not isinstance(
            self.http_timeout_seconds, (int, float)
        ):
            raise TcmbAcquisitionError("http_timeout_seconds must be a numeric float")
        timeout = float(self.http_timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise TcmbAcquisitionError("http_timeout_seconds must be a finite positive number")


def create_tcmb_acquisition_context_factory(
    calendar: MarketCalendar,
    client: TcmbResponseClient,
    clock: Clock,
) -> TcmbAcquisitionContextFactory:
    """Create an acquisition-context factory that generates fresh contexts with clock timestamps."""
    if not isinstance(calendar, MarketCalendar):
        raise TypeError("calendar must be a MarketCalendar instance")
    if not isinstance(client, TcmbResponseClient):
        raise TypeError("client must be a TcmbResponseClient instance")
    if not callable(clock):
        raise TypeError("clock must be a callable returning datetime")

    def factory(market_date: MarketDate) -> TcmbAcquisitionContext:
        return TcmbAcquisitionContext(
            client=client,
            calendar=calendar,
            retrieved_at=clock(),
        )

    return factory


def build_tcmb_market_calendar(closed_dates: tuple[date, ...]) -> MarketCalendar:
    """Build a MarketCalendar containing closed session overrides for the given dates."""
    if not isinstance(closed_dates, tuple) or not all(type(d) is date for d in closed_dates):
        raise TypeError("closed_dates must be a tuple of date instances")
    if len(set(closed_dates)) != len(closed_dates):
        raise ValueError("closed_dates must not contain duplicates")

    overrides = [
        SessionOverride(MarketDate(d.year, d.month, d.day), SessionKind("closed"))
        for d in closed_dates
    ]
    return MarketCalendar(overrides)


def build_tcmb_fx_rate_source(
    settings: TcmbSourceSettings,
    calendar: MarketCalendar,
    *,
    client: TcmbResponseClient | None = None,
    clock: Clock | None = None,
) -> TcmbFxRateSource:
    """Construct a TcmbFxRateSource adhering to cache and context factory invariants."""
    if not isinstance(settings, TcmbSourceSettings):
        raise TypeError("settings must be a TcmbSourceSettings instance")
    if not isinstance(calendar, MarketCalendar):
        raise TypeError("calendar must be a MarketCalendar instance")

    context_factory: TcmbAcquisitionContextFactory | None = None
    if settings.cache_policy is not TcmbCachePolicy.cache_only:
        resolved_client = (
            client
            if client is not None
            else TcmbHttpClient(timeout_seconds=settings.http_timeout_seconds)
        )
        if not isinstance(resolved_client, TcmbResponseClient):
            raise TypeError("client must be a TcmbResponseClient instance")
        if clock is None or not callable(clock):
            raise TypeError("clock must be a callable when policy is not cache_only")

        context_factory = create_tcmb_acquisition_context_factory(
            calendar=calendar,
            client=resolved_client,
            clock=clock,
        )

    loader = TcmbOrchestrationSnapshotLoader(
        root=settings.cache_root,
        policy=settings.cache_policy,
        acquisition_context_factory=context_factory,
    )
    return TcmbFxRateSource(calendar, loader)
