"""Result contract for one walk-forward experiment."""

from dataclasses import dataclass

from navlens import BacktestMetrics

from .records import WalkForwardRecord


@dataclass(frozen=True)
class WalkForwardResult:
    """Chronological predictions paired with Rust-owned evaluation metrics."""

    fund_id: str
    records: tuple[WalkForwardRecord, ...]
    metrics: BacktestMetrics
