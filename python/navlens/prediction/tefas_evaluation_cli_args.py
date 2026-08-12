"""CLI arguments for evaluating one stored prediction against TEFAS."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TefasPredictionEvaluationCliArguments:
    """Validated paths and acquisition settings for live evaluation."""

    prediction_artifact: Path
    as_of: date
    raw_root: Path
    output_format: str
    output_path: Path | None


def parse_tefas_prediction_evaluation_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionEvaluationCliArguments:
    """Parse one stored-prediction evaluation command."""
    parser = argparse.ArgumentParser(
        prog="navlens-evaluate-tefas-prediction",
        description="Compare one stored prediction with its published TEFAS return.",
    )
    parser.add_argument("prediction_artifact", type=Path)
    parser.add_argument("--as-of", type=_iso_date, default=today or date.today())
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/tefas"))
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    return TefasPredictionEvaluationCliArguments(
        values.prediction_artifact,
        values.as_of,
        values.raw_root,
        values.output_format,
        values.output,
    )


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error
