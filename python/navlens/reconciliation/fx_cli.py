"""CLI composition root for FX-adjusted point-in-time fund-return reconciliation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.alignment.errors import (
    InvalidPointInTimeFxReturnContributionRequestError,
    PointInTimeAlignmentError,
)
from navlens.datasets import (
    FundUnitPriceDatasetError,
    FxRateDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from navlens.sources import (
    CsvFundUnitPriceSourceError,
    CsvFxRateSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
)

from .errors import (
    InvalidFundPriceSourceError,
    MissingExactFundUnitPriceSnapshotError,
    PointInTimeReconciliationError,
    UnexpectedNativeReturnCardinalityError,
)
from .formatting import format_point_in_time_fx_adjusted_fund_return_reconciliation_result
from .fx_cli_args import parse_fx_reconciliation_cli_arguments
from .fx_csv import calculate_fx_reconciliation_from_csv


def main(argv: Sequence[str] | None = None) -> int:
    """Run FX-adjusted fund return reconciliation from CLI arguments and print formatted report."""
    try:
        args = parse_fx_reconciliation_cli_arguments(argv)
        recon_result = calculate_fx_reconciliation_from_csv(args)

    except (
        CsvHoldingsSourceError,
        CsvSecurityPriceSourceError,
        CsvFxRateSourceError,
        CsvFundUnitPriceSourceError,
        PointInTimeAlignmentError,
        InvalidPointInTimeFxReturnContributionRequestError,
        PointInTimeReconciliationError,
        InvalidFundPriceSourceError,
        MissingExactFundUnitPriceSnapshotError,
        UnexpectedNativeReturnCardinalityError,
        HoldingDatasetError,
        SecurityPriceDatasetError,
        FxRateDatasetError,
        FundUnitPriceDatasetError,
        NavlensValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_point_in_time_fx_adjusted_fund_return_reconciliation_result(recon_result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
