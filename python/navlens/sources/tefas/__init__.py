"""TEFAS HTTP acquisition and provider parsing."""

from ..price_observations import to_price_observations
from .acquisition import AcquireTefasPrices, TefasAcquisitionResult
from .client import TefasHttpClient
from .errors import TefasPayloadError, TefasRequestError, TefasSourceError, TefasTransportError
from .parser import parse_price_records
from .policy import TefasAccessPolicy
from .provenance import TefasPayloadProvenance, capture_payload_provenance
from .records import TefasPriceRecord
from .request import TefasPriceRequest
from .snapshots import TEFAS_SOURCE_ID, to_fund_unit_price_snapshots

__all__ = [
    "TefasAccessPolicy",
    "TefasAcquisitionResult",
    "TefasHttpClient",
    "TefasPayloadError",
    "TefasPayloadProvenance",
    "TefasPriceRecord",
    "TefasPriceRequest",
    "TefasRequestError",
    "TefasSourceError",
    "TefasTransportError",
    "TEFAS_SOURCE_ID",
    "AcquireTefasPrices",
    "capture_payload_provenance",
    "parse_price_records",
    "to_price_observations",
    "to_fund_unit_price_snapshots",
]
