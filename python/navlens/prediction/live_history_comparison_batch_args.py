"""CLI argument parsing for multi-scope live history comparison."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryComparisonBatchCliArguments:
    evaluation_artifacts: tuple[Path, ...]
    output_format: str
    output_path: Path | None


def parse_live_prediction_history_comparison_batch_arguments(
    argv: Sequence[str] | None = None,
) -> LivePredictionHistoryComparisonBatchCliArguments:
    """Parse positional evaluation artifact paths and output configuration."""
    parser = argparse.ArgumentParser(
        prog="navlens-compare-prediction-histories-batch",
        description="Compare multi-fund live model histories with per-scope failure isolation.",
    )
    parser.add_argument(
        "evaluation_artifacts",
        nargs="+",
        type=Path,
        help="Single or batch evaluation artifacts containing multi-fund predictions.",
    )
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    return LivePredictionHistoryComparisonBatchCliArguments(
        tuple(values.evaluation_artifacts),
        values.output_format,
        values.output,
    )
