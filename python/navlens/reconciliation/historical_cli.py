"""CLI composition root for historical fund-return reconciliation dataset evaluation."""

import sys
from collections.abc import Sequence

from .historical_cli_args import parse_historical_reconciliation_cli_arguments
from .historical_cli_errors import HISTORICAL_CLI_OPERATIONAL_ERRORS
from .historical_cli_output import write_historical_reconciliation_evaluation
from .historical_csv import evaluate_historical_reconciliation_from_csv


def main(argv: Sequence[str] | None = None) -> int:
    """Run historical fund return reconciliation dataset evaluation from CLI arguments."""
    try:
        args = parse_historical_reconciliation_cli_arguments(argv)
        evaluation = evaluate_historical_reconciliation_from_csv(args)
    except HISTORICAL_CLI_OPERATIONAL_ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    write_historical_reconciliation_evaluation(
        evaluation,
        args.output_format,
        text_stream=sys.stdout,
        binary_stream=sys.stdout.buffer,
    )

    return 0 if evaluation.skipped_period_count == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
