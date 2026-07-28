"""CLI composition root for point-in-time return contribution calculation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.datasets import HoldingDatasetError, SecurityPriceDatasetError
from navlens.sources import (
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
)

from .errors import PointInTimeAlignmentError
from .return_contribution_cli_args import parse_return_contribution_cli_arguments
from .return_contribution_csv import calculate_return_contribution_from_csv
from .return_contribution_formatting import format_return_contribution_result


def main(argv: Sequence[str] | None = None) -> int:
    """Run return contribution from CLI arguments and print formatted report."""
    try:
        args = parse_return_contribution_cli_arguments(argv)
        contrib_result = calculate_return_contribution_from_csv(args)
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
