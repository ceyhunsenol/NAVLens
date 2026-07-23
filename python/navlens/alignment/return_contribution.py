"""Orchestration for calculating aligned portfolio return contributions."""

from dataclasses import dataclass

from navlens import ReturnContributionResult, ReturnPeriod, calculate_return_contribution

from .result import PointInTimeAlignmentResult


@dataclass(frozen=True, slots=True)
class PointInTimeReturnContributionResult:
    """Combined provenance and return contribution result."""

    alignment_result: PointInTimeAlignmentResult
    contribution_result: ReturnContributionResult


def calculate_point_in_time_return_contribution(
    alignment_result: PointInTimeAlignmentResult,
    target_period: ReturnPeriod,
) -> PointInTimeReturnContributionResult:
    """
    Calculates portfolio return contribution from an existing alignment result.

    This delegates the mathematical calculation and coverage mapping to the
    native layer without re-running data selection or alignment logic.
    """
    native_result = calculate_return_contribution(alignment_result.report, target_period)

    return PointInTimeReturnContributionResult(
        alignment_result=alignment_result,
        contribution_result=native_result,
    )
