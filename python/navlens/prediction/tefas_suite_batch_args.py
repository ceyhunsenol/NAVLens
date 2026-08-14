"""CLI argument mapping for multi-fund TEFAS prediction model-suite batches."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens import MarketDate
from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    add_tefas_acquisition_arguments,
    reject_duplicate_tefas_funds,
    tefas_cli_arguments_for_fund,
)

from .freshness import FundUnitPriceFreshnessPolicy
from .model_suite import (
    PredictionModelSuiteOptions,
    prediction_model_suite_options_from_model_options,
)
from .tefas_cli_options import (
    add_tefas_prediction_options,
    tefas_prediction_options_from_namespace,
)


@dataclass(frozen=True, slots=True)
class TefasPredictionSuiteBatchCliArguments:
    """Validated fund requests and shared model-suite settings."""

    acquisitions: tuple[TefasCliArguments, ...]
    prediction_date: MarketDate
    target_date: MarketDate
    suite_options: PredictionModelSuiteOptions
    freshness: FundUnitPriceFreshnessPolicy
    output_format: str
    output_path: Path | None


def parse_tefas_prediction_suite_batch_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionSuiteBatchCliArguments:
    """Map a multi-fund suite command into explicit requests and shared options."""
    current_date = today or date.today()
    parser = argparse.ArgumentParser(
        prog="navlens-predict-tefas-suite-batch",
        description="Acquire and run every baseline prediction model for multiple TEFAS funds.",
    )
    parser.allow_abbrev = False
    parser.add_argument("fund_codes", nargs="+", help="unique TEFAS fund codes")
    add_tefas_acquisition_arguments(parser, current_date)
    add_tefas_prediction_options(parser, include_model_selection=False)
    values = parser.parse_args(argv)
    acquisitions = tuple(
        tefas_cli_arguments_for_fund(parser, values, current_date, fund_code)
        for fund_code in values.fund_codes
    )
    reject_duplicate_tefas_funds(parser, acquisitions)
    options = tefas_prediction_options_from_namespace(parser, values, values.as_of)
    suite_options = prediction_model_suite_options_from_model_options(options.model)
    return TefasPredictionSuiteBatchCliArguments(
        acquisitions,
        options.prediction_date,
        options.target_date,
        suite_options,
        options.freshness,
        options.output_format,
        options.output_path,
    )
