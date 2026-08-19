"""Explicit, provenance-carrying research datasets."""

from .errors import (
    FundReturnDatasetError,
    FundUnitPriceDatasetError,
    FxRateDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from .fund_returns import (
    FundReturnDataset,
    build_fund_return_dataset,
    load_fund_returns_csv,
)
from .fund_unit_price_snapshots import (
    FundUnitPriceSnapshot,
    select_fund_unit_price_snapshots,
)
from .fx_rate_snapshots import (
    FxRateSnapshot,
    select_fx_rate_snapshots,
)
from .fx_rate_source import (
    FxRateCorruptedSourceDataError,
    FxRateQuery,
    FxRateQueryError,
    FxRateSource,
    FxRateSourceError,
    FxRateSourceUnavailableError,
    FxRateUnmappedPairError,
    FxRateUnsupportedKindError,
)
from .holding_snapshots import HoldingSnapshot, select_latest_holdings_snapshot
from .pandas_returns import dated_returns_to_series
from .return_series import validated_decimal_returns
from .security_price_snapshots import (
    SecurityPriceSnapshot,
    select_security_price_snapshots,
)
from .security_price_source import (
    SecurityPriceCorruptedSourceDataError,
    SecurityPriceQuery,
    SecurityPriceQueryError,
    SecurityPriceSource,
    SecurityPriceSourceError,
    SecurityPriceSourceUnavailableError,
    SecurityPriceUnmappedInstrumentError,
)
from .tefas_returns import build_tefas_fund_returns

__all__ = [
    "FundReturnDataset",
    "FundReturnDatasetError",
    "FundUnitPriceDatasetError",
    "FundUnitPriceSnapshot",
    "FxRateCorruptedSourceDataError",
    "FxRateDatasetError",
    "FxRateQuery",
    "FxRateQueryError",
    "FxRateSnapshot",
    "FxRateSource",
    "FxRateSourceError",
    "FxRateSourceUnavailableError",
    "FxRateUnmappedPairError",
    "FxRateUnsupportedKindError",
    "HoldingDatasetError",
    "HoldingSnapshot",
    "SecurityPriceCorruptedSourceDataError",
    "SecurityPriceDatasetError",
    "SecurityPriceQuery",
    "SecurityPriceQueryError",
    "SecurityPriceSnapshot",
    "SecurityPriceSource",
    "SecurityPriceSourceError",
    "SecurityPriceSourceUnavailableError",
    "SecurityPriceUnmappedInstrumentError",
    "build_fund_return_dataset",
    "build_tefas_fund_returns",
    "dated_returns_to_series",
    "load_fund_returns_csv",
    "select_fund_unit_price_snapshots",
    "select_fx_rate_snapshots",
    "select_latest_holdings_snapshot",
    "select_security_price_snapshots",
    "validated_decimal_returns",
]
