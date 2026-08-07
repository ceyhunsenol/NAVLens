"""TCMB daily rates source capabilities."""

from .acquisition import TcmbAcquiredDailyRates, TcmbResponseClient, acquire_tcmb_daily_rates
from .availability import (
    TCMB_AVAILABILITY_POLICY_ID,
    TCMB_AVAILABILITY_POLICY_VERSION,
    initial_tcmb_available_at,
)
from .client import TcmbHttpClient
from .errors import (
    TcmbAcquisitionError,
    TcmbMappingError,
    TcmbRawCacheError,
    TcmbRawCacheIntegrityError,
    TcmbRevisionIndexError,
    TcmbRevisionIndexIntegrityError,
    TcmbTransportError,
    TcmbXmlParseError,
)
from .mapper import map_tcmb_daily_rates
from .parser import parse_tcmb_daily_rates_xml
from .provenance import TCMB_SOURCE_ID, TcmbAcquisitionProvenance
from .raw_cache import TcmbRawCacheEntry, load_tcmb_raw_artifact, store_tcmb_raw_artifact
from .records import TcmbCurrencyRecord, TcmbDailyRatesDocument
from .response import TcmbHttpResponse
from .revision_index import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TcmbRevisionIndex,
    TcmbRevisionIndexUpdate,
    TcmbRevisionRecord,
    load_tcmb_revision_index,
    record_tcmb_revision,
)

__all__ = [
    "TCMB_AVAILABILITY_POLICY_ID",
    "TCMB_AVAILABILITY_POLICY_VERSION",
    "TCMB_REVISION_INDEX_SCHEMA_VERSION",
    "TCMB_SOURCE_ID",
    "TcmbAcquiredDailyRates",
    "TcmbAcquisitionError",
    "TcmbAcquisitionProvenance",
    "TcmbCurrencyRecord",
    "TcmbDailyRatesDocument",
    "TcmbHttpClient",
    "TcmbHttpResponse",
    "TcmbMappingError",
    "TcmbRawCacheEntry",
    "TcmbRawCacheError",
    "TcmbRawCacheIntegrityError",
    "TcmbResponseClient",
    "TcmbRevisionIndex",
    "TcmbRevisionIndexError",
    "TcmbRevisionIndexIntegrityError",
    "TcmbRevisionIndexUpdate",
    "TcmbRevisionRecord",
    "TcmbTransportError",
    "TcmbXmlParseError",
    "acquire_tcmb_daily_rates",
    "initial_tcmb_available_at",
    "load_tcmb_raw_artifact",
    "load_tcmb_revision_index",
    "map_tcmb_daily_rates",
    "parse_tcmb_daily_rates_xml",
    "record_tcmb_revision",
    "store_tcmb_raw_artifact",
]
