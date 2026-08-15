"""Provider-neutral Yahoo security-price source adapter."""

from collections.abc import Iterable
from types import MappingProxyType

from navlens.datasets.security_price_snapshots import SecurityPriceSnapshot
from navlens.datasets.security_price_source import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)

from .errors import (
    YahooSecurityPriceCacheError,
    YahooSecurityPriceCacheIntegrityError,
    YahooSecurityPricePayloadError,
    YahooSecurityPriceTransportError,
)
from .request import YahooSecurityPriceRequest
from .snapshots import YAHOO_SOURCE_ID
from .source import YahooSecurityPriceSource
from .symbol_mapping import YahooSymbolMapping


class YahooSecurityPriceSourceAdapter:
    """Adapter exposing Yahoo security-price acquisition as a provider-neutral source."""

    def __init__(
        self,
        source: YahooSecurityPriceSource,
        mappings: Iterable[YahooSymbolMapping],
    ) -> None:
        if not isinstance(source, YahooSecurityPriceSource):
            raise TypeError("source must be a YahooSecurityPriceSource instance")
        if not isinstance(mappings, Iterable):
            raise TypeError("mappings must be an iterable of YahooSymbolMapping instances")

        mapping_dict: dict[str, YahooSymbolMapping] = {}
        for item in mappings:
            if not isinstance(item, YahooSymbolMapping):
                raise TypeError("all items in mappings must be YahooSymbolMapping instances")
            key = item.normalized_instrument_id
            if key in mapping_dict:
                raise ValueError(f"duplicate mapping for canonical instrument ID: {key}")
            mapping_dict[key] = item

        self._source = source
        self._mappings = MappingProxyType(mapping_dict)

    @property
    def source_id(self) -> str:
        """Return the canonical Yahoo source identifier."""
        return YAHOO_SOURCE_ID

    @property
    def mappings(self) -> MappingProxyType[str, YahooSymbolMapping]:
        """Return the immutable canonical-to-Yahoo symbol mappings."""
        return self._mappings

    def fetch_security_prices(
        self,
        query: SecurityPriceQuery,
    ) -> tuple[SecurityPriceSnapshot, ...]:
        """Fetch security price snapshots for the canonical query via Yahoo."""
        if not isinstance(query, SecurityPriceQuery):
            raise TypeError("query must be a SecurityPriceQuery instance")

        mapping = self._mappings.get(query.normalized_instrument_id)
        if mapping is None:
            raise SecurityPriceUnmappedInstrumentError(
                f"no Yahoo mapping configured for instrument: {query.instrument_id}"
            )

        request = YahooSecurityPriceRequest(
            mapping=mapping,
            start_date=query.start_date,
            end_date=query.end_date,
        )

        try:
            return self._source.fetch(request)
        except (YahooSecurityPriceCacheIntegrityError, YahooSecurityPricePayloadError) as error:
            raise SecurityPriceCorruptedSourceDataError(
                f"corrupted Yahoo security price data: {error}"
            ) from error
        except (YahooSecurityPriceTransportError, YahooSecurityPriceCacheError) as error:
            raise SecurityPriceSourceUnavailableError(
                f"Yahoo security price source unavailable: {error}"
            ) from error
