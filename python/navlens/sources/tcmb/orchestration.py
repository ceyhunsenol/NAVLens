"""Cache-aware request orchestration for TCMB FX-rate snapshots."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from navlens import MarketCalendar, MarketDate
from navlens._timestamps import validate_utc_timestamp
from navlens.datasets import FxRateSnapshot

from .acquisition import (
    TcmbAcquiredDailyRates,
    TcmbResponseClient,
    acquire_tcmb_daily_rates,
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
from .raw_cache import store_tcmb_raw_artifact
from .revision_availability import (
    TcmbVerifiedPublication,
    resolve_tcmb_revision_availability,
)
from .revision_index import (
    TcmbRevisionIndex,
    TcmbRevisionIndexUpdate,
    load_tcmb_revision_index,
    record_tcmb_revision,
)
from .snapshot_materialization import materialize_tcmb_fx_rate_snapshots


class TcmbCachePolicy(StrEnum):
    """Caller-controlled cache behavior for TCMB artifact orchestration."""

    cache_only = "cache_only"
    prefer_cache = "prefer_cache"
    refresh = "refresh"


@dataclass(frozen=True, slots=True)
class TcmbAcquisitionContext:
    """Dependencies and observation time required for network acquisition."""

    client: TcmbResponseClient
    calendar: MarketCalendar
    retrieved_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.client, TcmbResponseClient):
            raise TcmbOrchestrationError("client must implement TcmbResponseClient")
        if not isinstance(self.calendar, MarketCalendar):
            raise TcmbOrchestrationError("calendar must be a MarketCalendar")
        validate_utc_timestamp(self.retrieved_at, "retrieved_at", TcmbOrchestrationError)


@dataclass(frozen=True, slots=True)
class TcmbFxRateSnapshotResult:
    """Materialized snapshots and observable orchestration outcome."""

    snapshots: tuple[FxRateSnapshot, ...]
    requested_policy: TcmbCachePolicy
    acquired: bool
    revision_added: bool
    index_changed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.snapshots, tuple) or not all(
            isinstance(snapshot, FxRateSnapshot) for snapshot in self.snapshots
        ):
            raise TcmbOrchestrationError("snapshots must be a tuple of FxRateSnapshot values")
        if not isinstance(self.requested_policy, TcmbCachePolicy):
            raise TcmbOrchestrationError("requested_policy must be a TcmbCachePolicy")
        if not all(
            isinstance(value, bool)
            for value in (self.acquired, self.revision_added, self.index_changed)
        ):
            raise TcmbOrchestrationError("outcome flags must be booleans")
        if self.revision_added and not self.index_changed:
            raise TcmbOrchestrationError("revision_added requires index_changed")
        if not self.acquired and (self.revision_added or self.index_changed):
            raise TcmbOrchestrationError("cache-only outcomes cannot report index changes")


def obtain_tcmb_fx_rate_snapshots(
    root: str | Path,
    market_date: MarketDate,
    policy: TcmbCachePolicy,
    *,
    acquisition_context: TcmbAcquisitionContext | None = None,
    archive_date: date | None = None,
    initial_revision_sha256_hex: str | None = None,
    verified_publications: Iterable[TcmbVerifiedPublication] = (),
) -> TcmbFxRateSnapshotResult:
    """Obtain every observed TCMB revision under an explicit cache policy."""
    _validate_request(root, market_date, policy, acquisition_context, archive_date)
    evidence = _materialize_evidence(verified_publications)

    if policy is not TcmbCachePolicy.refresh:
        index = _load_index(root, market_date)
        if index is not None:
            snapshots = _resolve_and_materialize(root, index, initial_revision_sha256_hex, evidence)
            return _build_result(snapshots, policy, acquired=False)
        if policy is TcmbCachePolicy.cache_only:
            raise TcmbCacheMissError(
                f"no cached revision index found for market date {market_date}"
            )

    context = _require_acquisition_context(acquisition_context, policy)
    update = _acquire_and_record(root, market_date, archive_date, context)
    snapshots = _resolve_and_materialize(root, update.index, initial_revision_sha256_hex, evidence)
    return _build_result(snapshots, policy, acquired=True, update=update)


def _validate_request(
    root: str | Path,
    market_date: MarketDate,
    policy: TcmbCachePolicy,
    context: TcmbAcquisitionContext | None,
    archive_date: date | None,
) -> None:
    if not isinstance(root, (str, Path)):
        raise TcmbOrchestrationError("root must be a string or Path")
    if not isinstance(market_date, MarketDate):
        raise TcmbOrchestrationError("market_date must be a MarketDate")
    if not isinstance(policy, TcmbCachePolicy):
        raise TcmbOrchestrationError("policy must be a TcmbCachePolicy")
    if archive_date is not None and type(archive_date) is not date:
        raise TcmbOrchestrationError("archive_date must be a date or None")
    if policy is TcmbCachePolicy.cache_only and context is not None:
        raise TcmbOrchestrationError(
            "acquisition_context must not be supplied for cache_only policy"
        )
    if context is not None and not isinstance(context, TcmbAcquisitionContext):
        raise TcmbOrchestrationError("acquisition_context must be a TcmbAcquisitionContext")


def _materialize_evidence(
    values: Iterable[TcmbVerifiedPublication],
) -> tuple[TcmbVerifiedPublication, ...]:
    if not isinstance(values, Iterable):
        raise TcmbOrchestrationError("verified_publications must be iterable")
    return tuple(values)


def _require_acquisition_context(
    context: TcmbAcquisitionContext | None,
    policy: TcmbCachePolicy,
) -> TcmbAcquisitionContext:
    if context is None:
        raise TcmbOrchestrationError(f"acquisition_context is required for {policy.value} policy")
    return context


def _load_index(root: str | Path, market_date: MarketDate) -> TcmbRevisionIndex | None:
    try:
        return load_tcmb_revision_index(root, market_date)
    except (TcmbRevisionIndexError, OSError) as error:
        raise TcmbOrchestrationError(
            f"failed to load revision index for market date {market_date}: {error}"
        ) from error


def _acquire_and_record(
    root: str | Path,
    market_date: MarketDate,
    archive_date: date | None,
    context: TcmbAcquisitionContext,
) -> TcmbRevisionIndexUpdate:
    try:
        acquisition = acquire_tcmb_daily_rates(
            context.client,
            archive_date=archive_date,
            calendar=context.calendar,
            retrieved_at=context.retrieved_at,
        )
    except (
        TcmbAcquisitionError,
        TcmbMappingError,
        TcmbTransportError,
        TcmbXmlParseError,
        OSError,
    ) as error:
        raise TcmbOrchestrationError(f"acquisition failed: {error}") from error

    actual_date = acquisition.observations[0].market_date
    if actual_date != market_date:
        raise TcmbOrchestrationError(
            f"acquired market date {actual_date} does not match requested market date {market_date}"
        )
    return _persist_acquisition(root, acquisition)


def _persist_acquisition(
    root: str | Path,
    acquisition: TcmbAcquiredDailyRates,
) -> TcmbRevisionIndexUpdate:
    try:
        raw_entry = store_tcmb_raw_artifact(root, acquisition)
    except (TcmbRawCacheError, OSError) as error:
        raise TcmbOrchestrationError(f"failed to store raw artifact: {error}") from error
    try:
        return record_tcmb_revision(root, acquisition, raw_entry)
    except (TcmbRevisionIndexError, OSError) as error:
        raise TcmbOrchestrationError(f"failed to record revision index: {error}") from error


def _resolve_and_materialize(
    root: str | Path,
    index: TcmbRevisionIndex,
    initial_revision_sha256_hex: str | None,
    verified_publications: tuple[TcmbVerifiedPublication, ...],
) -> tuple[FxRateSnapshot, ...]:
    try:
        availabilities = resolve_tcmb_revision_availability(
            index,
            initial_revision_sha256_hex=initial_revision_sha256_hex,
            verified_publications=verified_publications,
        )
        return materialize_tcmb_fx_rate_snapshots(root, index, availabilities)
    except (
        TcmbRawCacheError,
        TcmbRevisionAvailabilityError,
        TcmbSnapshotMaterializationError,
        OSError,
    ) as error:
        raise TcmbOrchestrationError(
            f"failed to resolve or materialize snapshots for {index.market_date}: {error}"
        ) from error


def _build_result(
    snapshots: tuple[FxRateSnapshot, ...],
    policy: TcmbCachePolicy,
    *,
    acquired: bool,
    update: TcmbRevisionIndexUpdate | None = None,
) -> TcmbFxRateSnapshotResult:
    return TcmbFxRateSnapshotResult(
        snapshots=snapshots,
        requested_policy=policy,
        acquired=acquired,
        revision_added=update.revision_added if update else False,
        index_changed=update.index_changed if update else False,
    )
