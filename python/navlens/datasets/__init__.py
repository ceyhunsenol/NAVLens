"""Explicit, provenance-carrying research datasets."""

from .errors import FundReturnDatasetError
from .fund_returns import (
    FundReturnDataset,
    build_fund_return_dataset,
    load_fund_returns_csv,
)
from .pandas_returns import dated_returns_to_series
from .tefas_returns import build_tefas_fund_returns

__all__ = [
    "FundReturnDataset",
    "FundReturnDatasetError",
    "build_fund_return_dataset",
    "build_tefas_fund_returns",
    "dated_returns_to_series",
    "load_fund_returns_csv",
]
