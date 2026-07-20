"""Executable adapter for explicit TEFAS data acquisition."""

import sys
from collections.abc import Sequence
from datetime import datetime

from .acquisition import AcquireTefasPrices
from .cli_arguments import parse_cli_arguments
from .cli_output import format_acquisition_result
from .client import TefasHttpClient
from .errors import TefasSourceError


def main(argv: Sequence[str] | None = None) -> int:
    """Acquire requested prices and return a process exit code."""
    arguments = parse_cli_arguments(argv)
    acquisition = AcquireTefasPrices(TefasHttpClient(), arguments.raw_root)
    try:
        result = acquisition.acquire(
            arguments.request,
            arguments.as_of,
            datetime.now().astimezone(),
        )
    except TefasSourceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(format_acquisition_result(result, arguments.request))
    return 0
