"""CLI arguments for batch evaluation of stored TEFAS predictions."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .tefas_evaluation_cli_args import _iso_date


@dataclass(frozen=True, slots=True)
class TefasPredictionEvaluationBatchArguments:
    prediction_artifacts: tuple[Path, ...]
    as_of: date
    raw_root: Path
    output_format: str
    output_path: Path | None


def parse_tefas_prediction_evaluation_batch_arguments(
    argv: Sequence[str] | None = None,
    today: date | None = None,
) -> TefasPredictionEvaluationBatchArguments:
    parser = argparse.ArgumentParser(
        prog="navlens-evaluate-tefas-prediction-batch",
        description="Evaluate stored TEFAS predictions with per-artifact isolation.",
    )
    parser.add_argument("prediction_artifacts", nargs="+", type=Path)
    parser.add_argument("--as-of", type=_iso_date, default=today or date.today())
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/tefas"))
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    return TefasPredictionEvaluationBatchArguments(
        tuple(values.prediction_artifacts),
        values.as_of,
        values.raw_root,
        values.output_format,
        values.output,
    )
