"""Orchestration for a provenance-carrying single-fund return dataset."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from navlens import calculate_price_returns
from navlens.sources.csv import read_price_records
from navlens.sources.price_observations import to_price_observations
from navlens.sources.price_record import PriceRecord

from .pandas_returns import dated_returns_to_series


@dataclass(frozen=True)
class FundReturnDataset:
    """Dated decimal returns with the source artifact that produced them."""

    fund_id: str
    returns: pd.Series
    source_path: Path
    source_row_count: int


def load_fund_returns_csv(fund_id: str, path: str | Path) -> FundReturnDataset:
    """Parse one CSV artifact and build its canonical return dataset."""
    source_path = Path(path)
    records = read_price_records(source_path)
    return build_fund_return_dataset(fund_id, records, source_path)


def build_fund_return_dataset(
    fund_id: str,
    records: Sequence[PriceRecord],
    source_path: str | Path,
) -> FundReturnDataset:
    """Build a source-neutral dataset through Rust-owned return calculations."""
    observations = to_price_observations(records)
    dated_returns = calculate_price_returns(fund_id, observations)
    return FundReturnDataset(
        fund_id=fund_id,
        returns=dated_returns_to_series(dated_returns),
        source_path=Path(source_path),
        source_row_count=len(records),
    )
