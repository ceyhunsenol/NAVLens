"""CSV workflow operation for FX-adjusted point-in-time return contribution."""

from navlens.sources import (
    read_fx_rates_csv,
    read_holdings_snapshots,
    read_security_prices_csv,
)

from .fx_orchestration import calculate_point_in_time_fx_adjusted_return_contribution
from .fx_request import PointInTimeFxReturnContributionRequest
from .fx_result import PointInTimeFxAdjustedReturnContributionResult
from .fx_return_contribution_cli_args import FxReturnContributionCliArguments
from .point_in_time import align_point_in_time


def calculate_fx_return_contribution_from_csv(
    arguments: FxReturnContributionCliArguments,
) -> PointInTimeFxAdjustedReturnContributionResult:
    """Read CSV files and calculate FX-adjusted point-in-time return contribution."""
    align_args = arguments.alignment_args
    holdings = read_holdings_snapshots(align_args.holdings_csv)
    prices = read_security_prices_csv(align_args.security_prices_csv)
    fx_rates = read_fx_rates_csv(arguments.fx_rates_csv)

    alignment_result = align_point_in_time(align_args.request, holdings, prices)
    fx_request = PointInTimeFxReturnContributionRequest(
        alignment_result=alignment_result,
        target_period=arguments.target_period,
        fx_source_id=arguments.fx_source_id,
        fx_policy=arguments.fx_policy,
    )

    return calculate_point_in_time_fx_adjusted_return_contribution(fx_request, fx_rates)
