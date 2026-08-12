"""CLI arguments for fair live prediction history comparison."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonCliArguments:
    histories: tuple[tuple[Path, ...], ...]
    output_format: str
    output_path: Path | None


def parse_live_prediction_history_comparison_arguments(
    argv: Sequence[str] | None = None,
) -> LivePredictionHistoryComparisonCliArguments:
    parser = argparse.ArgumentParser(
        prog="navlens-compare-prediction-histories",
        description="Compare live model histories over identical realized periods.",
    )
    parser.add_argument(
        "--history",
        action="append",
        nargs="+",
        type=Path,
        required=True,
        help="Single/batch evaluation artifacts for one model; repeat per model.",
    )
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    return LivePredictionHistoryComparisonCliArguments(
        tuple(tuple(group) for group in values.history),
        values.output_format,
        values.output,
    )
