"""Provider-neutral FX-rate source adapter backed by TCMB orchestration."""

from collections.abc import Callable, Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from navlens import MarketCalendar, MarketDate
from navlens.datasets import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateSnapshot,
    FxRateSourceUnavailableError,
    FxRateUnmappedPairError,
)

from .errors import (
    TcmbAcquisitionError,
    TcmbCacheMissError,
    TcmbMappingError,
    TcmbOrchestrationError,
    TcmbRawCacheError,
    TcmbRevisionAvailabilityError,
    TcmbRevisionIndexError,
    TcmbSnapshotMaterializationError,
    TcmbTransportError,
    TcmbXmlParseError,
)
from .orchestration import (
    TcmbAcquisitionContext,
    TcmbCachePolicy,
    obtain_tcmb_fx_rate_snapshots,
)
from .provenance import TCMB_SOURCE_ID

TcmbAcquisitionContextFactory = Callable[[MarketDate], TcmbAcquisitionContext]


class TcmbDailySnapshotLoader(Protocol):
    """Provider-internal capability for loading every revision of one TCMB day."""

    def load(self, market_date: MarketDate) -> tuple[FxRateSnapshot, ...]:
        """Load all retained revisions for one market date."""
        ...


class TcmbOrchestrationSnapshotLoader:
    """Adapt TCMB cache-aware orchestration to a per-market-date loader."""

    def __init__(
        self,
        root: str | Path,
        policy: TcmbCachePolicy,
        acquisition_context_factory: TcmbAcquisitionContextFactory | None = None,
    ) -> None:
        if not isinstance(root, (str, Path)):
            raise TypeError("root must be a string or Path")
        if not isinstance(policy, TcmbCachePolicy):
            raise TypeError("policy must be a TcmbCachePolicy")
        _validate_context_factory(policy, acquisition_context_factory)
        self._root = Path(root)
        self._policy = policy
        self._context_factory = acquisition_context_factory

    def load(self, market_date: MarketDate) -> tuple[FxRateSnapshot, ...]:
        """Obtain every retained revision for one TCMB market date."""
        context = self._build_context(market_date)
        archive_date = date.fromisoformat(str(market_date))
        result = obtain_tcmb_fx_rate_snapshots(
            self._root,
            market_date,
            self._policy,
            acquisition_context=context,
            archive_date=archive_date,
        )
        return result.snapshots

    def _build_context(self, market_date: MarketDate) -> TcmbAcquisitionContext | None:
        if self._context_factory is None:
            return None
        context = self._context_factory(market_date)
        if not isinstance(context, TcmbAcquisitionContext):
            raise TypeError("acquisition_context_factory must return TcmbAcquisitionContext")
        return context


class TcmbFxRateSource:
    """Retrieve provider-neutral FX candidates through TCMB's cache-aware boundary."""

    def __init__(self, calendar: MarketCalendar, loader: TcmbDailySnapshotLoader) -> None:
        if not isinstance(calendar, MarketCalendar):
            raise TypeError("calendar must be a MarketCalendar")
        if not callable(getattr(loader, "load", None)):
            raise TypeError("loader must implement TcmbDailySnapshotLoader")
        self._calendar = calendar
        self._loader = loader

    @property
    def source_id(self) -> str:
        """Return TCMB's canonical source identifier."""
        return TCMB_SOURCE_ID

    def fetch_fx_rates(self, query: FxRateQuery) -> tuple[FxRateSnapshot, ...]:
        """Fetch exact-pair and exact-kind candidates without selecting revisions."""
        if not isinstance(query, FxRateQuery):
            raise TypeError("query must be an FxRateQuery instance")
        if query.pair.quote_currency.code != "TRY":
            raise FxRateUnmappedPairError(
                "TCMB source supports only directional pairs quoted in TRY"
            )

        snapshots: list[FxRateSnapshot] = []
        for current_date in _inclusive_dates(query.start_date, query.end_date):
            market_date = MarketDate(current_date.year, current_date.month, current_date.day)
            if self._calendar.session_on(market_date).is_open():
                snapshots.extend(self._load_candidates(market_date, query))
        return tuple(snapshots)

    def _load_candidates(
        self,
        market_date: MarketDate,
        query: FxRateQuery,
    ) -> tuple[FxRateSnapshot, ...]:
        try:
            snapshots = self._loader.load(market_date)
        except TcmbCacheMissError as error:
            raise FxRateSourceUnavailableError(str(error)) from error
        except TcmbOrchestrationError as error:
            _raise_mapped_orchestration_error(error, market_date)
        _validate_loaded_snapshots(snapshots, market_date)
        return tuple(
            snapshot
            for snapshot in snapshots
            if snapshot.observation.pair == query.pair and snapshot.observation.kind == query.kind
        )


def _validate_context_factory(
    policy: TcmbCachePolicy,
    factory: TcmbAcquisitionContextFactory | None,
) -> None:
    if policy is TcmbCachePolicy.cache_only and factory is not None:
        raise ValueError("acquisition_context_factory must be omitted for cache_only policy")
    if policy is not TcmbCachePolicy.cache_only and not callable(factory):
        raise ValueError(f"acquisition_context_factory is required for {policy.value} policy")


def _inclusive_dates(start_date: date, end_date: date) -> Iterator[date]:
    day_count = (end_date - start_date).days
    for offset in range(day_count + 1):
        yield start_date + timedelta(days=offset)


def _validate_loaded_snapshots(
    snapshots: object,
    requested_market_date: MarketDate,
) -> None:
    if not isinstance(snapshots, tuple) or not all(
        isinstance(snapshot, FxRateSnapshot) for snapshot in snapshots
    ):
        raise FxRateCorruptedSourceDataError(
            "TCMB loader must return a tuple of FxRateSnapshot values"
        )
    for snapshot in snapshots:
        if snapshot.source_id != TCMB_SOURCE_ID:
            raise FxRateCorruptedSourceDataError(
                f"TCMB loader returned foreign source_id {snapshot.source_id!r}"
            )
        if snapshot.observation.market_date != requested_market_date:
            raise FxRateCorruptedSourceDataError(
                "TCMB loader returned a snapshot for a different market date"
            )


def _raise_mapped_orchestration_error(
    error: TcmbOrchestrationError,
    market_date: MarketDate,
) -> None:
    cause = _root_cause(error)
    message = f"TCMB snapshot acquisition failed for {market_date}: {error}"
    if isinstance(cause, (TcmbTransportError, OSError)):
        raise FxRateSourceUnavailableError(message) from error
    if isinstance(
        cause,
        (
            TcmbAcquisitionError,
            TcmbMappingError,
            TcmbRawCacheError,
            TcmbRevisionAvailabilityError,
            TcmbRevisionIndexError,
            TcmbSnapshotMaterializationError,
            TcmbXmlParseError,
        ),
    ):
        raise FxRateCorruptedSourceDataError(message) from error
    raise error


def _root_cause(error: BaseException) -> BaseException:
    current = error
    seen: set[int] = set()
    while current.__cause__ is not None and id(current) not in seen:
        seen.add(id(current))
        current = current.__cause__
    return current
