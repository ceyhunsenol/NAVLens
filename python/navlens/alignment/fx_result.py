"""Result contract for point-in-time FX-aware return contribution orchestration."""

from dataclasses import dataclass

from navlens import FxAdjustedReturnContributionResult
from navlens.datasets import FxRateSnapshot

from .fx_request import PointInTimeFxReturnContributionRequest


@dataclass(frozen=True, slots=True)
class PointInTimeFxAdjustedReturnContributionResult:
    """Provenance and native FX-adjusted return contribution result."""

    request: PointInTimeFxReturnContributionRequest
    contribution_result: FxAdjustedReturnContributionResult
    selected_fx_snapshots: tuple[FxRateSnapshot, ...]
