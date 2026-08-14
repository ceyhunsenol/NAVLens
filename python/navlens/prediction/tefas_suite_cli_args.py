"""CLI argument mapping for same-snapshot TEFAS model suites."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from navlens import MarketDate
from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    build_tefas_cli_parser,
    tefas_cli_arguments_from_namespace,
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
class TefasPredictionSuiteCliArguments:
    """Validated acquisition and shared model-suite settings."""

    acquisition: TefasCliArguments
    prediction_date: MarketDate
    target_date: MarketDate
    options: PredictionModelSuiteOptions
    freshness: FundUnitPriceFreshnessPolicy
    output_format: str
    output_path: Path | None


def parse_tefas_prediction_suite_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionSuiteCliArguments:
    """Parse the keyless TEFAS model-suite command."""
    current_date = today or date.today()
    parser = build_tefas_cli_parser(
        today=current_date,
        prog="navlens-predict-tefas-suite",
        description="Run every prediction baseline over one acquired TEFAS history.",
    )
    parser.allow_abbrev = False
    add_tefas_prediction_options(parser, include_model_selection=False)
    values = parser.parse_args(argv)
    acquisition = tefas_cli_arguments_from_namespace(parser, values, current_date)
    options = tefas_prediction_options_from_namespace(parser, values, acquisition.as_of)
    return TefasPredictionSuiteCliArguments(
        acquisition,
        options.prediction_date,
        options.target_date,
        prediction_model_suite_options_from_model_options(options.model),
        options.freshness,
        options.output_format,
        options.output_path,
    )
