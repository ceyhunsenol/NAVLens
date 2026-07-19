"""Explicit, provenance-carrying research datasets."""

from .errors import FundReturnDatasetError
from .fund_returns import FundReturnDataset, load_fund_returns_csv
from .pandas_returns import dated_returns_to_series

__all__ = [
    "FundReturnDataset",
    "FundReturnDatasetError",
    "dated_returns_to_series",
    "load_fund_returns_csv",
]
