"""CLI composition root for FX-adjusted point-in-time return contribution calculation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.datasets import FxRateDatasetError, HoldingDatasetError, SecurityPriceDatasetError
from navlens.sources import (
    CsvFxRateSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
)

from .errors import PointInTimeAlignmentError
from .fx_return_contribution_cli_args import parse_fx_return_contribution_cli_arguments
from .fx_return_contribution_csv import calculate_fx_return_contribution_from_csv
from .fx_return_contribution_formatting import format_fx_return_contribution_result


def main(argv: Sequence[str] | None = None) -> int:
    """Run FX-adjusted return contribution from CLI arguments and print formatted report."""
    try:
        args = parse_fx_return_contribution_cli_arguments(argv)
        contrib_result = calculate_fx_return_contribution_from_csv(args)
    except (
        CsvHoldingsSourceError,
        CsvSecurityPriceSourceError,
        CsvFxRateSourceError,
        PointInTimeAlignmentError,
        HoldingDatasetError,
        SecurityPriceDatasetError,
        FxRateDatasetError,
        NavlensValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_fx_return_contribution_result(contrib_result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
