"""CLI argument mapping for live TEFAS prediction."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from navlens import MarketDate
from navlens.sources.tefas.cli_arguments import (
    TefasCliArguments,
    build_tefas_cli_parser,
    tefas_cli_arguments_from_namespace,
)

from .freshness import FundUnitPriceFreshnessPolicy
from .model_cli_options import PredictionModelOptions
from .tefas_cli_options import (
    add_tefas_prediction_options,
    tefas_prediction_options_from_namespace,
)


@dataclass(frozen=True, slots=True)
class TefasPredictionCliArguments:
    """Validated acquisition and prediction settings."""

    acquisition: TefasCliArguments
    prediction_date: MarketDate
    target_date: MarketDate
    model: PredictionModelOptions
    freshness: FundUnitPriceFreshnessPolicy
    output_format: str


def parse_tefas_prediction_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionCliArguments:
    """Parse the keyless TEFAS prediction command."""
    current_date = today or date.today()
    parser = build_tefas_cli_parser(
        today=current_date,
        prog="navlens-predict-tefas",
        description="Acquire TEFAS prices and predict the next published NAV return.",
    )
    add_tefas_prediction_options(parser)
    values = parser.parse_args(argv)
    acquisition = tefas_cli_arguments_from_namespace(parser, values, current_date)
    options = tefas_prediction_options_from_namespace(parser, values, acquisition.as_of)
    return TefasPredictionCliArguments(
        acquisition,
        options.prediction_date,
        options.target_date,
        options.model,
        options.freshness,
        options.output_format,
    )
