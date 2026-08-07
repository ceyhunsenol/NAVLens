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
    TcmbCacheMissError,
    TcmbMappingError,
    TcmbOrchestrationError,
    TcmbRawCacheError,
    TcmbRawCacheIntegrityError,
    TcmbRevisionAvailabilityError,
    TcmbRevisionIndexError,
    TcmbRevisionIndexIntegrityError,
    TcmbSnapshotMaterializationError,
    TcmbTransportError,
    TcmbXmlParseError,
)
from .mapper import map_tcmb_daily_rates
from .orchestration import (
    TcmbAcquisitionContext,
    TcmbCachePolicy,
    TcmbFxRateSnapshotResult,
    obtain_tcmb_fx_rate_snapshots,
)
from .parser import parse_tcmb_daily_rates_xml
from .provenance import TCMB_SOURCE_ID, TcmbAcquisitionProvenance
from .raw_cache import TcmbRawCacheEntry, load_tcmb_raw_artifact, store_tcmb_raw_artifact
from .records import TcmbCurrencyRecord, TcmbDailyRatesDocument
from .response import TcmbHttpResponse
from .revision_availability import (
    TcmbResolvedRevisionAvailability,
    TcmbRevisionAvailabilityBasis,
    TcmbVerifiedPublication,
    resolve_tcmb_revision_availability,
)
from .revision_index import (
    TCMB_REVISION_INDEX_SCHEMA_VERSION,
    TcmbRevisionIndex,
    TcmbRevisionIndexUpdate,
    TcmbRevisionRecord,
    load_tcmb_revision_index,
    record_tcmb_revision,
)
from .snapshot_materialization import materialize_tcmb_fx_rate_snapshots

__all__ = [
    "TCMB_AVAILABILITY_POLICY_ID",
    "TCMB_AVAILABILITY_POLICY_VERSION",
    "TCMB_REVISION_INDEX_SCHEMA_VERSION",
    "TCMB_SOURCE_ID",
    "TcmbAcquiredDailyRates",
    "TcmbAcquisitionContext",
    "TcmbAcquisitionError",
    "TcmbAcquisitionProvenance",
    "TcmbCacheMissError",
    "TcmbCachePolicy",
    "TcmbCurrencyRecord",
    "TcmbDailyRatesDocument",
    "TcmbHttpClient",
    "TcmbHttpResponse",
    "TcmbMappingError",
    "TcmbFxRateSnapshotResult",
    "TcmbOrchestrationError",
    "TcmbRawCacheEntry",
    "TcmbRawCacheError",
    "TcmbRawCacheIntegrityError",
    "TcmbResolvedRevisionAvailability",
    "TcmbResponseClient",
    "TcmbRevisionAvailabilityBasis",
    "TcmbRevisionAvailabilityError",
    "TcmbRevisionIndex",
    "TcmbRevisionIndexError",
    "TcmbRevisionIndexIntegrityError",
    "TcmbRevisionIndexUpdate",
    "TcmbRevisionRecord",
    "TcmbSnapshotMaterializationError",
    "TcmbTransportError",
    "TcmbVerifiedPublication",
    "TcmbXmlParseError",
    "acquire_tcmb_daily_rates",
    "initial_tcmb_available_at",
    "load_tcmb_raw_artifact",
    "load_tcmb_revision_index",
    "map_tcmb_daily_rates",
    "materialize_tcmb_fx_rate_snapshots",
    "obtain_tcmb_fx_rate_snapshots",
    "parse_tcmb_daily_rates_xml",
    "record_tcmb_revision",
    "resolve_tcmb_revision_availability",
    "store_tcmb_raw_artifact",
]
