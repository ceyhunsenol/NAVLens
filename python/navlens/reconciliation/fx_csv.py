"""CSV workflow operation for FX-adjusted point-in-time fund-return reconciliation."""

from navlens.alignment.fx_return_contribution_csv import calculate_fx_return_contribution_from_csv
from navlens.sources import read_fund_unit_prices_csv

from .fx_cli_args import FxReconciliationCliArguments
from .fx_orchestration import reconcile_point_in_time_fx_adjusted_fund_return
from .fx_result import PointInTimeFxFundReturnReconciliationResult


def calculate_fx_reconciliation_from_csv(
    arguments: FxReconciliationCliArguments,
) -> PointInTimeFxFundReturnReconciliationResult:
    """Read CSV files and calculate FX-adjusted point-in-time fund-return reconciliation."""
    contrib_result = calculate_fx_return_contribution_from_csv(arguments.fx_contribution_args)
    fund_prices = read_fund_unit_prices_csv(arguments.fund_unit_prices_csv)

    return reconcile_point_in_time_fx_adjusted_fund_return(
        contrib_result,
        fund_prices,
        fund_price_source_id=arguments.fund_price_source_id,
    )
