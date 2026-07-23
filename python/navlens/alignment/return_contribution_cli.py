"""CLI composition root for point-in-time return contribution calculation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.datasets import HoldingDatasetError, SecurityPriceDatasetError
from navlens.sources import (
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
    read_holdings_snapshots,
    read_security_prices_csv,
)

from .errors import PointInTimeAlignmentError
from .point_in_time import align_point_in_time
from .return_contribution import calculate_point_in_time_return_contribution
from .return_contribution_cli_args import parse_return_contribution_cli_arguments
from .return_contribution_formatting import format_return_contribution_result


def main(argv: Sequence[str] | None = None) -> int:
    """Run return contribution from CLI arguments and print formatted report."""
    try:
        args = parse_return_contribution_cli_arguments(argv)
        align_args = args.alignment_args

        holdings = read_holdings_snapshots(align_args.holdings_csv)
        prices = read_security_prices_csv(align_args.security_prices_csv)

        alignment_result = align_point_in_time(align_args.request, holdings, prices)

        contrib_result = calculate_point_in_time_return_contribution(
            alignment_result,
            args.target_period,
        )
    except (
        CsvHoldingsSourceError,
        CsvSecurityPriceSourceError,
        PointInTimeAlignmentError,
        HoldingDatasetError,
        SecurityPriceDatasetError,
        NavlensValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_return_contribution_result(contrib_result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
