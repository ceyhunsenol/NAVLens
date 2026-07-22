"""Explicit, provenance-carrying research datasets."""

from .errors import (
    FundReturnDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from .fund_returns import (
    FundReturnDataset,
    build_fund_return_dataset,
    load_fund_returns_csv,
)
from .holding_snapshots import HoldingSnapshot, select_latest_holdings_snapshot
from .pandas_returns import dated_returns_to_series
from .return_series import validated_decimal_returns
from .security_price_snapshots import (
    SecurityPriceSnapshot,
    select_security_price_snapshots,
)
from .tefas_returns import build_tefas_fund_returns

__all__ = [
    "FundReturnDataset",
    "FundReturnDatasetError",
    "HoldingDatasetError",
    "HoldingSnapshot",
    "SecurityPriceDatasetError",
    "SecurityPriceSnapshot",
    "build_fund_return_dataset",
    "build_tefas_fund_returns",
    "dated_returns_to_series",
    "load_fund_returns_csv",
    "select_latest_holdings_snapshot",
    "select_security_price_snapshots",
    "validated_decimal_returns",
]
