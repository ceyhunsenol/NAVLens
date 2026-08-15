"""Experimental, opt-in Yahoo Finance security-price source."""

from .batch import (
    YahooSecurityPriceBatchFailure,
    YahooSecurityPriceBatchOutcome,
    YahooSecurityPriceBatchResult,
    YahooSecurityPriceBatchSource,
    YahooSecurityPriceBatchSuccess,
    acquire_yahoo_security_price_batch,
)
from .client import YahooChartHttpClient
from .errors import (
    YahooSecurityPriceBatchError,
    YahooSecurityPriceCacheError,
    YahooSecurityPriceCacheIntegrityError,
    YahooSecurityPricePayloadError,
    YahooSecurityPriceRateLimitError,
    YahooSecurityPriceRequestError,
    YahooSecurityPriceSourceError,
    YahooSecurityPriceTransportError,
)
from .policy import YahooAcquisitionPolicy
from .provenance import YahooAcquisitionProvenance, YahooSecurityPriceAcquisitionResult
from .request import YahooSecurityPriceRequest
from .response import YahooChartHttpResponse
from .snapshots import YAHOO_SOURCE_ID
from .source import YahooChartResponseClient, YahooSecurityPriceSource
from .symbol_mapping import YahooSymbolMapping

__all__ = [
    "YAHOO_SOURCE_ID",
    "YahooAcquisitionPolicy",
    "YahooAcquisitionProvenance",
    "YahooChartHttpClient",
    "YahooChartHttpResponse",
    "YahooChartResponseClient",
    "YahooSecurityPriceBatchError",
    "YahooSecurityPriceBatchFailure",
    "YahooSecurityPriceBatchOutcome",
    "YahooSecurityPriceBatchResult",
    "YahooSecurityPriceBatchSource",
    "YahooSecurityPriceBatchSuccess",
    "YahooSecurityPriceAcquisitionResult",
    "YahooSecurityPriceCacheError",
    "YahooSecurityPriceCacheIntegrityError",
    "YahooSecurityPricePayloadError",
    "YahooSecurityPriceRateLimitError",
    "YahooSecurityPriceRequest",
    "YahooSecurityPriceRequestError",
    "YahooSecurityPriceSource",
    "YahooSecurityPriceSourceError",
    "YahooSecurityPriceTransportError",
    "YahooSymbolMapping",
    "acquire_yahoo_security_price_batch",
]
