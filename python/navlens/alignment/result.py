"""Result contract for point-in-time alignment."""

from dataclasses import dataclass

from navlens import PortfolioCoverageReport
from navlens.datasets import HoldingSnapshot, SecurityPriceSnapshot

from .request import PointInTimeAlignmentRequest


@dataclass(frozen=True, slots=True)
class PointInTimeAlignmentResult:
    """Provenance and coverage report from point-in-time alignment."""

    request: PointInTimeAlignmentRequest
    holdings_snapshot: HoldingSnapshot
    report: PortfolioCoverageReport
    selected_price_snapshots: tuple[SecurityPriceSnapshot, ...]
