"""CLI composition root for TCMB-backed historical FX reconciliation evaluation."""

import sys
from collections.abc import Sequence

from navlens.datasets import (
    FxRateDatasetError,
    FxRateSourceError,
    SecurityPriceSourceError,
)
from navlens.sources.tcmb import TcmbOrchestrationError

from .historical_cli_errors import HISTORICAL_CLI_OPERATIONAL_ERRORS
from .historical_cli_output import write_historical_reconciliation_evaluation
from .historical_fx_tcmb import evaluate_historical_fx_reconciliation_from_tcmb
from .historical_fx_tcmb_cli_args import (
    InvalidHistoricalFxTcmbCliArgumentsError,
    parse_historical_fx_tcmb_cli_arguments,
)

HISTORICAL_FX_TCMB_CLI_OPERATIONAL_ERRORS: tuple[type[BaseException], ...] = (
    HISTORICAL_CLI_OPERATIONAL_ERRORS
    + (
        FxRateSourceError,
        SecurityPriceSourceError,
        FxRateDatasetError,
        TcmbOrchestrationError,
        InvalidHistoricalFxTcmbCliArgumentsError,
    )
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run TCMB historical FX fund return reconciliation evaluation from CLI arguments."""
    try:
        args = parse_historical_fx_tcmb_cli_arguments(argv)
        evaluation = evaluate_historical_fx_reconciliation_from_tcmb(args)
    except HISTORICAL_FX_TCMB_CLI_OPERATIONAL_ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    write_historical_reconciliation_evaluation(
        evaluation,
        args.base_arguments.output_format,
        text_stream=sys.stdout,
        binary_stream=sys.stdout.buffer,
    )

    return 0 if evaluation.skipped_period_count == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
