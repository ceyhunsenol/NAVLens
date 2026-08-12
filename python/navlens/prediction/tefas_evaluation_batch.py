"""Failure-isolated execution for stored TEFAS prediction artifacts."""

from dataclasses import dataclass
from pathlib import Path

from navlens import NavlensValidationError
from navlens.sources.tefas import TefasSourceError

from .errors import PredictionArtifactError
from .live_evaluation import LivePredictionEvaluationResult
from .prediction_artifact_collection import load_single_return_prediction_artifacts
from .tefas_evaluation_execution import EvaluateTefasPredictionArtifact


@dataclass(frozen=True, slots=True)
class TefasPredictionEvaluationSuccess:
    artifact_path: Path
    completed: LivePredictionEvaluationResult


@dataclass(frozen=True, slots=True)
class TefasPredictionEvaluationFailure:
    artifact_path: Path
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class TefasPredictionEvaluationBatchResult:
    successes: tuple[TefasPredictionEvaluationSuccess, ...]
    failures: tuple[TefasPredictionEvaluationFailure, ...]

    @property
    def total(self) -> int:
        return len(self.successes) + len(self.failures)


def evaluate_tefas_prediction_artifacts(
    paths: tuple[Path, ...],
    evaluator: EvaluateTefasPredictionArtifact,
) -> TefasPredictionEvaluationBatchResult:
    """Evaluate explicit paths sequentially while isolating expected failures."""
    if not paths:
        raise ValueError("prediction evaluation batch is empty")
    successes: list[TefasPredictionEvaluationSuccess] = []
    failures: list[TefasPredictionEvaluationFailure] = []
    for path in paths:
        try:
            artifacts = load_single_return_prediction_artifacts(path)
        except (
            OSError,
            PredictionArtifactError,
            TefasSourceError,
            NavlensValidationError,
        ) as error:
            _append_failure(failures, path, error)
            continue
        for artifact in artifacts:
            try:
                completed = evaluator.evaluate(artifact)
            except (
                OSError,
                PredictionArtifactError,
                TefasSourceError,
                NavlensValidationError,
            ) as error:
                _append_failure(failures, path, error)
            else:
                successes.append(TefasPredictionEvaluationSuccess(path, completed))
    return TefasPredictionEvaluationBatchResult(tuple(successes), tuple(failures))


def _append_failure(
    failures: list[TefasPredictionEvaluationFailure],
    path: Path,
    error: Exception,
) -> None:
    failures.append(TefasPredictionEvaluationFailure(path, type(error).__name__, str(error)))


def prediction_evaluation_batch_exit_code(
    result: TefasPredictionEvaluationBatchResult,
) -> int:
    if not result.failures:
        return 0
    return 2 if result.successes else 1
