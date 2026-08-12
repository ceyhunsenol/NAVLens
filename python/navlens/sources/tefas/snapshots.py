"""Point-in-time snapshot mapping for acquired TEFAS unit prices."""

from datetime import datetime

from navlens.datasets import FundUnitPriceSnapshot

from ..price_observations import to_price_observations
from .acquisition import TefasAcquisitionResult

TEFAS_SOURCE_ID = "tefas"


def to_fund_unit_price_snapshots(
    acquisition: TefasAcquisitionResult,
    *,
    acquired_at: datetime,
) -> tuple[FundUnitPriceSnapshot, ...]:
    """Map acquired records without inventing historical publication timestamps.

    TEFAS price-history payloads do not provide per-observation publication
    timestamps. Each record therefore becomes visible at the explicit acquisition
    timestamp, which is conservative and prevents future-data leakage.
    """
    observations = to_price_observations(acquisition.records)
    return tuple(
        FundUnitPriceSnapshot(
            fund_id=record.fund_code,
            observation=observation,
            available_at=acquired_at,
            ingested_at=acquired_at,
            source_id=TEFAS_SOURCE_ID,
        )
        for record, observation in zip(acquisition.records, observations, strict=True)
    )
