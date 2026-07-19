"""The single mapping from native dated returns to a pandas series."""

from collections.abc import Sequence

import pandas as pd

from navlens import DatedDecimalReturn

from .errors import FundReturnDatasetError


def dated_returns_to_series(values: Sequence[DatedDecimalReturn]) -> pd.Series:
    if not values:
        raise FundReturnDatasetError("at least one dated return is required")
    index = pd.to_datetime([str(value.date) for value in values])
    return pd.Series(
        [value.return_decimal for value in values],
        index=pd.DatetimeIndex(index, name="date"),
        name="return_decimal",
        dtype="float64",
    )
