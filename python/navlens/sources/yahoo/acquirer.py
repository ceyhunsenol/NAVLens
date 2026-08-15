"""Coordination of cache checking, network fetching, and rate-limit fallbacks."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from navlens._timestamps import validate_utc_timestamp
from navlens.sources.artifact_digest import sha256_bytes

from .cache_identity import YahooCacheIdentity, build_cache_paths
from .cache_record import YahooCacheRecord
from .cache_storage import is_cache_fresh, load_cache_record, store_cache_record
from .errors import YahooSecurityPriceCacheIntegrityError, YahooSecurityPriceRateLimitError
from .parser import parse_yahoo_chart_response
from .policy import YahooAcquisitionPolicy
from .provenance import YahooAcquisitionProvenance, YahooSecurityPriceAcquisitionResult
from .request import YahooSecurityPriceRequest
from .response import YahooChartHttpResponse
from .snapshots import YAHOO_SOURCE_ID, materialize_yahoo_security_price_snapshots


class YahooChartResponseClient(Protocol):
    """Consumer-owned transport capability required by the Yahoo source."""

    def fetch_chart_response(
        self, request: YahooSecurityPriceRequest
    ) -> YahooChartHttpResponse: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class YahooSecurityPriceAcquirer:
    """Coordinate cache, transport, fallback policy, and domain snapshot mapping."""

    def __init__(
        self,
        client: YahooChartResponseClient,
        cache_root: str | Path | None = None,
        policy: YahooAcquisitionPolicy | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._client = client
        self._cache_root = Path(cache_root) if cache_root is not None else None
        self._policy = policy or YahooAcquisitionPolicy()
        self._clock = clock

    def acquire(
        self,
        request: YahooSecurityPriceRequest,
        checked_at: datetime | None = None,
    ) -> YahooSecurityPriceAcquisitionResult:
        """Acquire security price snapshots from fresh cache, network, or marked fallback."""
        observation_time = checked_at if checked_at is not None else self._clock()
        validate_utc_timestamp(
            observation_time,
            "checked_at / observation time",
            YahooSecurityPriceCacheIntegrityError,
        )

        paths = None
        cached_record: YahooCacheRecord | None = None

        if self._cache_root is not None:
            paths = build_cache_paths(self._cache_root, request)
            cached_record = load_cache_record(paths, request)
            if cached_record is not None:
                if observation_time < cached_record.retrieved_at:
                    raise YahooSecurityPriceCacheIntegrityError(
                        "clock anomaly: check time precedes cache retrieval time"
                    )
                if not self._policy.force_refresh and is_cache_fresh(
                    cached_record,
                    observation_time,
                    self._policy.cache_ttl,
                ):
                    return self._build_result_from_record(
                        cached_record,
                        request,
                        paths.payload,
                        is_rate_limit_fallback=False,
                        is_stale=False,
                    )

        try:
            response = self._client.fetch_chart_response(request)
        except YahooSecurityPriceRateLimitError:
            if (
                self._cache_root is not None
                and self._policy.allow_stale_on_429
                and cached_record is not None
                and paths is not None
            ):
                is_stale = not is_cache_fresh(
                    cached_record,
                    observation_time,
                    self._policy.cache_ttl,
                )
                return self._build_result_from_record(
                    cached_record,
                    request,
                    paths.payload,
                    is_rate_limit_fallback=True,
                    is_stale=is_stale,
                )
            raise

        # Validate by parsing and materializing before any cache persistence
        document = parse_yahoo_chart_response(response.body)
        snapshots = materialize_yahoo_security_price_snapshots(
            document,
            request.mapping,
            response.retrieved_at,
        )

        payload_path = None
        if self._cache_root is not None and paths is not None:
            new_record = self._create_cache_record(request, response)
            store_cache_record(paths, new_record)
            payload_path = paths.payload

        provenance = YahooAcquisitionProvenance(
            source_url=response.source_url,
            retrieved_at=response.retrieved_at,
            sha256_hex=sha256_bytes(response.body),
            is_from_cache=False,
            is_rate_limit_fallback=False,
            is_stale=False,
            payload_path=payload_path,
        )
        return YahooSecurityPriceAcquisitionResult(snapshots=snapshots, provenance=provenance)

    def _create_cache_record(
        self,
        request: YahooSecurityPriceRequest,
        response: YahooChartHttpResponse,
    ) -> YahooCacheRecord:
        identity = YahooCacheIdentity(
            provider=YAHOO_SOURCE_ID,
            symbol=request.mapping.normalized_provider_symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return YahooCacheRecord(
            identity=identity,
            source_url=response.source_url,
            retrieved_at=response.retrieved_at,
            sha256_hex=sha256_bytes(response.body),
            byte_count=len(response.body),
            body=response.body,
        )

    def _build_result_from_record(
        self,
        record: YahooCacheRecord,
        request: YahooSecurityPriceRequest,
        payload_path: Path,
        *,
        is_rate_limit_fallback: bool,
        is_stale: bool,
    ) -> YahooSecurityPriceAcquisitionResult:
        document = parse_yahoo_chart_response(record.body)
        snapshots = materialize_yahoo_security_price_snapshots(
            document,
            request.mapping,
            record.retrieved_at,
        )
        provenance = YahooAcquisitionProvenance(
            source_url=record.source_url,
            retrieved_at=record.retrieved_at,
            sha256_hex=record.sha256_hex,
            is_from_cache=True,
            is_rate_limit_fallback=is_rate_limit_fallback,
            is_stale=is_stale,
            payload_path=payload_path,
        )
        return YahooSecurityPriceAcquisitionResult(snapshots=snapshots, provenance=provenance)
