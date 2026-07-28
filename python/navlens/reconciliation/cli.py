"""CLI composition root for point-in-time fund-return reconciliation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.alignment.errors import PointInTimeAlignmentError
from navlens.alignment.return_contribution_csv import calculate_return_contribution_from_csv
from navlens.datasets import (
    FundUnitPriceDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from navlens.sources import (
    CsvFundUnitPriceSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
    read_fund_unit_prices_csv,
)

from .cli_args import parse_reconciliation_cli_arguments
from .errors import (
    InvalidFundPriceSourceError,
    MissingExactFundUnitPriceSnapshotError,
    PointInTimeReconciliationError,
    UnexpectedNativeReturnCardinalityError,
)
from .formatting import format_point_in_time_fund_return_reconciliation_result
from .orchestration import reconcile_point_in_time_fund_return


def main(argv: Sequence[str] | None = None) -> int:
    """Run fund return reconciliation from CLI arguments and print formatted report."""
    try:
        args = parse_reconciliation_cli_arguments(argv)

        contrib_result = calculate_return_contribution_from_csv(args.contribution_args)

        fund_prices = read_fund_unit_prices_csv(args.fund_unit_prices_csv)

        recon_result = reconcile_point_in_time_fund_return(
            contrib_result,
            fund_prices,
            fund_price_source_id=args.fund_price_source_id,
        )

    except (
        CsvHoldingsSourceError,
        CsvSecurityPriceSourceError,
        CsvFundUnitPriceSourceError,
        PointInTimeAlignmentError,
        PointInTimeReconciliationError,
        InvalidFundPriceSourceError,
        MissingExactFundUnitPriceSnapshotError,
        UnexpectedNativeReturnCardinalityError,
        HoldingDatasetError,
        SecurityPriceDatasetError,
        FundUnitPriceDatasetError,
        NavlensValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(format_point_in_time_fund_return_reconciliation_result(recon_result))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
