"""CLI composition root for TCMB-backed FX-adjusted return contribution."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.datasets import (
    FxRateDatasetError,
    FxRateSourceError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
    SecurityPriceSourceError,
)
from navlens.sources import CsvHoldingsSourceError
from navlens.sources.tcmb import TcmbOrchestrationError

from .errors import PointInTimeAlignmentError
from .fx_return_contribution_formatting import format_fx_return_contribution_result
from .fx_return_contribution_tcmb import calculate_fx_return_contribution_from_tcmb
from .fx_return_contribution_tcmb_cli_args import (
    InvalidFxReturnContributionTcmbCliArgumentsError,
    parse_fx_return_contribution_tcmb_cli_arguments,
)

FX_RETURN_CONTRIBUTION_TCMB_CLI_OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    CsvHoldingsSourceError,
    SecurityPriceSourceError,
    FxRateSourceError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
    FxRateDatasetError,
    PointInTimeAlignmentError,
    TcmbOrchestrationError,
    NavlensValidationError,
    InvalidFxReturnContributionTcmbCliArgumentsError,
    OSError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run TCMB FX return contribution calculation and print formatted report."""
    try:
        args = parse_fx_return_contribution_tcmb_cli_arguments(argv)
        result = calculate_fx_return_contribution_from_tcmb(args)
    except FX_RETURN_CONTRIBUTION_TCMB_CLI_OPERATIONAL_ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_fx_return_contribution_result(result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
