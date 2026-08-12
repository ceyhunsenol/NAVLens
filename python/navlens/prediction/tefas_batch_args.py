"""CLI argument mapping for sequential multi-fund TEFAS predictions."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    add_tefas_acquisition_arguments,
    reject_duplicate_tefas_funds,
    tefas_cli_arguments_for_fund,
)

from .tefas_cli_options import (
    TefasPredictionCliOptions,
    add_tefas_prediction_options,
    tefas_prediction_options_from_namespace,
)


@dataclass(frozen=True, slots=True)
class TefasPredictionBatchCliArguments:
    """Validated fund requests and shared prediction settings."""

    acquisitions: tuple[TefasCliArguments, ...]
    options: TefasPredictionCliOptions


def parse_tefas_prediction_batch_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionBatchCliArguments:
    """Map a multi-fund command into explicit requests and shared settings."""
    current_date = today or date.today()
    parser = argparse.ArgumentParser(
        prog="navlens-predict-tefas-batch",
        description="Acquire and predict next published NAV returns for multiple funds.",
    )
    parser.add_argument("fund_codes", nargs="+", help="unique TEFAS fund codes")
    add_tefas_acquisition_arguments(parser, current_date)
    add_tefas_prediction_options(parser)
    values = parser.parse_args(argv)
    acquisitions = tuple(
        tefas_cli_arguments_for_fund(parser, values, current_date, fund_code)
        for fund_code in values.fund_codes
    )
    reject_duplicate_tefas_funds(parser, acquisitions)
    options = tefas_prediction_options_from_namespace(parser, values, values.as_of)
    return TefasPredictionBatchCliArguments(acquisitions, options)
