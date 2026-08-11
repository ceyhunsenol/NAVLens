"""Command-line argument parsing for historical prediction evaluation."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .historical.scope import HistoricalPredictionEvaluationScope


@dataclass(frozen=True, slots=True)
class HistoricalPredictionCliArguments:
    """Validated CLI inputs for historical prediction evaluation."""

    schedule_csv: Path
    fund_unit_prices_csv: Path
    output_format: str
    scope: HistoricalPredictionEvaluationScope


def build_historical_prediction_cli_parser() -> argparse.ArgumentParser:
    """Build the historical prediction CLI parser."""
    parser = argparse.ArgumentParser(
        prog="navlens-evaluate-historical-prediction-csv",
        description="Evaluate point-in-time historical fund return predictions.",
    )
    _add_input_arguments(parser)
    _add_scope_arguments(parser)
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output report format (default: text).",
    )
    return parser


def _add_input_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--schedule-csv",
        required=True,
        type=Path,
        help="Path to the historical prediction schedule CSV.",
    )
    parser.add_argument(
        "--fund-unit-prices-csv",
        required=True,
        type=Path,
        help="Path to provider-neutral fund unit-price snapshots CSV.",
    )


def _add_scope_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fund-id", required=True, help="Target fund identifier.")
    parser.add_argument("--source-id", required=True, help="Fund price source identifier.")
    parser.add_argument("--lookback", type=int, default=5, help="Lagged return count.")
    parser.add_argument(
        "--minimum-training-returns",
        type=int,
        default=None,
        help="Minimum historical returns required for model fitting.",
    )
    parser.add_argument(
        "--confidence-level",
        type=float,
        default=0.90,
        help="Prediction interval confidence level in (0, 1).",
    )
    parser.add_argument("--model-version", default="v1", help="Model version identifier.")


def parse_historical_prediction_cli_arguments(
    argv: Sequence[str] | None = None,
) -> HistoricalPredictionCliArguments:
    """Parse raw arguments into a validated historical prediction command."""
    parser = build_historical_prediction_cli_parser()
    args = parser.parse_args(argv)
    scope = HistoricalPredictionEvaluationScope(
        fund_id=args.fund_id.strip(),
        source_id=args.source_id.strip(),
        lookback=args.lookback,
        confidence_level=args.confidence_level,
        model_version=args.model_version.strip(),
        minimum_training_returns=args.minimum_training_returns,
    )
    return HistoricalPredictionCliArguments(
        schedule_csv=args.schedule_csv,
        fund_unit_prices_csv=args.fund_unit_prices_csv,
        output_format=args.output_format,
        scope=scope,
    )
