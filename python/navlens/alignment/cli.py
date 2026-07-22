"""CLI composition root for point-in-time holdings and price alignment."""

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

from .cli_args import parse_alignment_cli_arguments
from .errors import PointInTimeAlignmentError
from .formatting import format_alignment_result
from .point_in_time import align_point_in_time


def main(argv: Sequence[str] | None = None) -> int:
    """Run point-in-time alignment from CLI arguments and print formatted report."""
    try:
        args = parse_alignment_cli_arguments(argv)
        holdings = read_holdings_snapshots(args.holdings_csv)
        prices = read_security_prices_csv(args.security_prices_csv)
        result = align_point_in_time(args.request, holdings, prices)
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

    print(format_alignment_result(result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
