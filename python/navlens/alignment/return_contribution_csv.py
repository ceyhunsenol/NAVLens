"""Shared CSV operation for point-in-time return contribution."""

from navlens.sources import (
    read_holdings_snapshots,
    read_security_prices_csv,
)

from .point_in_time import align_point_in_time
from .return_contribution import (
    PointInTimeReturnContributionResult,
    calculate_point_in_time_return_contribution,
)
from .return_contribution_cli_args import ReturnContributionCliArguments


def calculate_return_contribution_from_csv(
    arguments: ReturnContributionCliArguments,
) -> PointInTimeReturnContributionResult:
    """Read CSV files and calculate point-in-time return contribution deterministically."""
    align_args = arguments.alignment_args
    holdings = read_holdings_snapshots(align_args.holdings_csv)
    prices = read_security_prices_csv(align_args.security_prices_csv)

    alignment_result = align_point_in_time(align_args.request, holdings, prices)

    return calculate_point_in_time_return_contribution(
        alignment_result,
        arguments.target_period,
    )
