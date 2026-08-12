"""CLI argument mapping for live prediction history reports."""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LivePredictionHistoryCliArguments:
    """Input artifacts and output settings for one history report."""

    evaluation_artifacts: tuple[Path, ...]
    output_format: str
    output_path: Path | None


def parse_live_prediction_history_arguments(
    argv: Sequence[str] | None = None,
) -> LivePredictionHistoryCliArguments:
    """Parse explicit evaluation artifact paths without filesystem discovery."""
    parser = argparse.ArgumentParser(
        prog="navlens-summarize-prediction-evaluations",
        description="Aggregate stored live prediction evaluations through Rust metrics.",
    )
    parser.add_argument("evaluation_artifacts", nargs="+", type=Path)
    parser.add_argument("--output-format", choices=["text", "json"], default="text")
    parser.add_argument("--output", type=Path)
    values = parser.parse_args(argv)
    return LivePredictionHistoryCliArguments(
        tuple(values.evaluation_artifacts),
        values.output_format,
        values.output,
    )
