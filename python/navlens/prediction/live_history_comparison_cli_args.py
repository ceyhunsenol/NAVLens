"""CLI arguments for fair live prediction history comparison."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonCliArguments:
    histories: tuple[tuple[Path, ...], ...] | None
    evaluation_artifacts: tuple[Path, ...] | None
    output_format: str
    output_path: Path | None


def parse_live_prediction_history_comparison_arguments(
    argv: Sequence[str] | None = None,
) -> LivePredictionHistoryComparisonCliArguments:
    parser = argparse.ArgumentParser(
        prog="navlens-compare-prediction-histories",
        description="Compare live model histories over identical realized periods.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--history",
        action="append",
        nargs="+",
        type=Path,
        help="Single/batch evaluation artifacts for one model; repeat per model.",
    )
    group.add_argument(
        "--evaluation-artifacts",
        nargs="+",
        type=Path,
        help="Daily single or batch evaluation artifacts containing mixed model predictions.",
    )
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    histories = (
        tuple(tuple(group_paths) for group_paths in values.history)
        if values.history is not None
        else None
    )
    evaluation_artifacts = (
        tuple(values.evaluation_artifacts) if values.evaluation_artifacts is not None else None
    )
    return LivePredictionHistoryComparisonCliArguments(
        histories,
        evaluation_artifacts,
        values.output_format,
        values.output,
    )
