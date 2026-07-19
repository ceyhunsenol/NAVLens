"""Orchestration for a provenance-carrying single-fund return dataset."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from navlens import calculate_price_returns
from navlens.sources.csv import read_price_records, to_price_observations

from .pandas_returns import dated_returns_to_series


@dataclass(frozen=True)
class FundReturnDataset:
    fund_id: str
    returns: pd.Series
    source_path: Path
    source_row_count: int


def load_fund_returns_csv(fund_id: str, path: str | Path) -> FundReturnDataset:
    source_path = Path(path)
    records = read_price_records(source_path)
    observations = to_price_observations(records)
    dated_returns = calculate_price_returns(fund_id, observations)
    return FundReturnDataset(
        fund_id=fund_id,
        returns=dated_returns_to_series(dated_returns),
        source_path=source_path,
        source_row_count=len(records),
    )
