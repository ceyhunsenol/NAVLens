"""CLI composition root for historical fund-return reconciliation dataset evaluation."""

import sys
from collections.abc import Sequence

from navlens import NavlensValidationError
from navlens.alignment.errors import PointInTimeAlignmentError
from navlens.datasets import (
    FundUnitPriceDatasetError,
    HoldingDatasetError,
    SecurityPriceDatasetError,
)
from navlens.sources import (
    CsvFundUnitPriceSourceError,
    CsvHoldingsSourceError,
    CsvSecurityPriceSourceError,
)

from .historical.errors import (
    HistoricalReconciliationDatasetError,
    InvalidHistoricalReconciliationRunConfigurationError,
)
from .historical.formatting import format_historical_reconciliation_evaluation
from .historical.schedule_csv import CsvHistoricalScheduleSourceError
from .historical.serialization import serialize_historical_reconciliation_evaluation
from .historical_cli_args import parse_historical_reconciliation_cli_arguments
from .historical_csv import evaluate_historical_reconciliation_from_csv


def main(argv: Sequence[str] | None = None) -> int:
    """Run historical fund return reconciliation dataset evaluation from CLI arguments."""
    try:
        args = parse_historical_reconciliation_cli_arguments(argv)
        evaluation = evaluate_historical_reconciliation_from_csv(args)

    except (
        InvalidHistoricalReconciliationRunConfigurationError,
        CsvHistoricalScheduleSourceError,
        CsvHoldingsSourceError,
        CsvSecurityPriceSourceError,
        CsvFundUnitPriceSourceError,
        HistoricalReconciliationDatasetError,
        PointInTimeAlignmentError,
        HoldingDatasetError,
        SecurityPriceDatasetError,
        FundUnitPriceDatasetError,
        NavlensValidationError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.output_format == "json":
        sys.stdout.buffer.write(serialize_historical_reconciliation_evaluation(evaluation))
    else:
        sys.stdout.write(format_historical_reconciliation_evaluation(evaluation) + "\n")

    return 0 if evaluation.skipped_period_count == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
