"""Selection and mapping of dataset price snapshots into Rust candidates."""

from collections.abc import Sequence

from navlens import HoldingPosition, SecurityPriceHistoryCandidate
from navlens.datasets import SecurityPriceSnapshot, select_security_price_snapshots

from .request import PointInTimeAlignmentRequest


def select_price_candidates(
    request: PointInTimeAlignmentRequest,
    positions: Sequence[HoldingPosition],
    snapshots: Sequence[SecurityPriceSnapshot],
) -> tuple[
    tuple[SecurityPriceHistoryCandidate, ...],
    tuple[SecurityPriceSnapshot, ...],
]:
    """Select eligible snapshots and map non-empty histories to Rust candidates."""
    candidates: list[SecurityPriceHistoryCandidate] = []
    selected_snapshots: list[SecurityPriceSnapshot] = []

    for position in positions:
        selected = select_security_price_snapshots(
            snapshots,
            source_id=request.security_price_source_id,
            instrument_id=position.instrument_id,
            at_timestamp=request.prediction_timestamp,
            pricing_as_of_date=request.policy.pricing_as_of_date,
        )
        if selected:
            selected_snapshots.extend(selected)
            candidates.append(
                SecurityPriceHistoryCandidate(
                    position.instrument_id,
                    [snapshot.observation for snapshot in selected],
                )
            )

    return tuple(candidates), tuple(selected_snapshots)
