"""CLI composition root for historical prediction evaluation."""

import sys
from collections.abc import Sequence

from .historical_cli_args import parse_historical_prediction_cli_arguments
from .historical_cli_errors import HISTORICAL_PREDICTION_CLI_OPERATIONAL_ERRORS
from .historical_cli_output import write_historical_prediction_run_result
from .historical_csv import evaluate_historical_prediction_from_csv


def main(argv: Sequence[str] | None = None) -> int:
    """Evaluate historical predictions from provider-neutral CSV inputs."""
    try:
        arguments = parse_historical_prediction_cli_arguments(argv)
        result = evaluate_historical_prediction_from_csv(arguments)
    except HISTORICAL_PREDICTION_CLI_OPERATIONAL_ERRORS as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    write_historical_prediction_run_result(
        result,
        arguments.output_format,
        text_stream=sys.stdout,
        binary_stream=sys.stdout.buffer,
    )
    return 0 if result.evaluation.skipped_period_count == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
