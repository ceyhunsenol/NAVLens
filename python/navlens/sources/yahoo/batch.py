"""Sequential, deduplicated Yahoo security-price batch acquisition."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, TypeAlias

from navlens._timestamps import validate_utc_timestamp

from .errors import YahooSecurityPriceBatchError, YahooSecurityPriceSourceError
from .provenance import YahooSecurityPriceAcquisitionResult
from .request import YahooSecurityPriceRequest


class YahooSecurityPriceBatchSource(Protocol):
    """Consumer-owned acquisition capability required by the Yahoo batch."""

    def acquire(
        self,
        request: YahooSecurityPriceRequest,
        checked_at: datetime | None = None,
    ) -> YahooSecurityPriceAcquisitionResult: ...


@dataclass(frozen=True, slots=True)
class YahooSecurityPriceBatchSuccess:
    """One requested acquisition that completed successfully."""

    request: YahooSecurityPriceRequest
    acquisition: YahooSecurityPriceAcquisitionResult

    def __post_init__(self) -> None:
        if not isinstance(self.request, YahooSecurityPriceRequest):
            raise YahooSecurityPriceBatchError(
                "success request must be a YahooSecurityPriceRequest"
            )
        if not isinstance(self.acquisition, YahooSecurityPriceAcquisitionResult):
            raise YahooSecurityPriceBatchError(
                "success acquisition must be a YahooSecurityPriceAcquisitionResult"
            )


@dataclass(frozen=True, slots=True)
class YahooSecurityPriceBatchFailure:
    """One expected source failure that did not stop the remaining batch."""

    request: YahooSecurityPriceRequest
    error: YahooSecurityPriceSourceError

    def __post_init__(self) -> None:
        if not isinstance(self.request, YahooSecurityPriceRequest):
            raise YahooSecurityPriceBatchError(
                "failure request must be a YahooSecurityPriceRequest"
            )
        if not isinstance(self.error, YahooSecurityPriceSourceError):
            raise YahooSecurityPriceBatchError("failure error must be a Yahoo source error")


YahooSecurityPriceBatchOutcome: TypeAlias = (
    YahooSecurityPriceBatchSuccess | YahooSecurityPriceBatchFailure
)


@dataclass(frozen=True, slots=True)
class YahooSecurityPriceBatchResult:
    """Ordered per-request outcomes from one failure-isolated batch."""

    outcomes: tuple[YahooSecurityPriceBatchOutcome, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcomes, tuple) or not self.outcomes:
            raise YahooSecurityPriceBatchError("batch outcomes must be a non-empty tuple")
        if not all(
            isinstance(outcome, (YahooSecurityPriceBatchSuccess, YahooSecurityPriceBatchFailure))
            for outcome in self.outcomes
        ):
            raise YahooSecurityPriceBatchError("batch outcomes contain an unsupported value")

    @property
    def total(self) -> int:
        """Return the original input request count, including duplicates."""
        return len(self.outcomes)

    @property
    def unique_request_count(self) -> int:
        """Return the number of normalized requests that were actually executed."""
        return len({_request_key(outcome.request) for outcome in self.outcomes})

    @property
    def successes(self) -> tuple[YahooSecurityPriceBatchSuccess, ...]:
        """Return successful outcomes in their original relative order."""
        return tuple(
            outcome
            for outcome in self.outcomes
            if isinstance(outcome, YahooSecurityPriceBatchSuccess)
        )

    @property
    def failures(self) -> tuple[YahooSecurityPriceBatchFailure, ...]:
        """Return failed outcomes in their original relative order."""
        return tuple(
            outcome
            for outcome in self.outcomes
            if isinstance(outcome, YahooSecurityPriceBatchFailure)
        )


def acquire_yahoo_security_price_batch(
    requests: Iterable[YahooSecurityPriceRequest],
    source: YahooSecurityPriceBatchSource,
    *,
    checked_at: datetime | None = None,
) -> YahooSecurityPriceBatchResult:
    """Acquire first-seen normalized requests once and preserve every input outcome."""
    materialized = tuple(requests)
    if not materialized:
        raise YahooSecurityPriceBatchError("batch requires at least one request")
    if not all(isinstance(request, YahooSecurityPriceRequest) for request in materialized):
        raise YahooSecurityPriceBatchError(
            "batch requests must be YahooSecurityPriceRequest values"
        )
    if checked_at is not None:
        validate_utc_timestamp(checked_at, "checked_at", YahooSecurityPriceBatchError)

    completed: dict[tuple[str, str, date, date], YahooSecurityPriceBatchOutcome] = {}
    outcomes: list[YahooSecurityPriceBatchOutcome] = []
    for request in materialized:
        key = _request_key(request)
        previous = completed.get(key)
        outcome = _repeat_outcome(previous, request) if previous is not None else None
        if outcome is None:
            outcome = _acquire_one(source, request, checked_at)
            completed[key] = outcome
        outcomes.append(outcome)
    return YahooSecurityPriceBatchResult(tuple(outcomes))


def _acquire_one(
    source: YahooSecurityPriceBatchSource,
    request: YahooSecurityPriceRequest,
    checked_at: datetime | None,
) -> YahooSecurityPriceBatchOutcome:
    try:
        acquisition = source.acquire(request, checked_at=checked_at)
    except YahooSecurityPriceSourceError as error:
        return YahooSecurityPriceBatchFailure(request, error)
    return YahooSecurityPriceBatchSuccess(request, acquisition)


def _repeat_outcome(
    outcome: YahooSecurityPriceBatchOutcome | None,
    request: YahooSecurityPriceRequest,
) -> YahooSecurityPriceBatchOutcome | None:
    if isinstance(outcome, YahooSecurityPriceBatchSuccess):
        return YahooSecurityPriceBatchSuccess(request, outcome.acquisition)
    if isinstance(outcome, YahooSecurityPriceBatchFailure):
        return YahooSecurityPriceBatchFailure(request, outcome.error)
    return None


def _request_key(request: YahooSecurityPriceRequest) -> tuple[str, str, date, date]:
    return (
        request.mapping.normalized_instrument_id,
        request.mapping.normalized_provider_symbol,
        request.start_date,
        request.end_date,
    )
