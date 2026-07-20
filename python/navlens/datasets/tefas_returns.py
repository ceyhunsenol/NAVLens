"""TEFAS-to-dataset boundary mapping."""

from navlens.sources.tefas import TefasAcquisitionResult

from .errors import FundReturnDatasetError
from .fund_returns import FundReturnDataset, build_fund_return_dataset


def build_tefas_fund_returns(acquisition: TefasAcquisitionResult) -> FundReturnDataset:
    """Build returns from one acquired TEFAS fund without refetching data."""
    fund_id = _single_fund_id(acquisition)
    return build_fund_return_dataset(fund_id, acquisition.records, acquisition.payload_path)


def _single_fund_id(acquisition: TefasAcquisitionResult) -> str:
    fund_ids = {record.fund_code for record in acquisition.records}
    if not fund_ids:
        raise FundReturnDatasetError("TEFAS dataset requires at least one price record")
    if len(fund_ids) != 1:
        raise FundReturnDatasetError("TEFAS dataset cannot contain multiple funds")
    return fund_ids.pop()
