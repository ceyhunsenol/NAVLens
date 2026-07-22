"""Errors for point-in-time holdings/security-price alignment orchestration."""

from datetime import datetime


class PointInTimeAlignmentError(Exception):
    """Base exception for point-in-time alignment orchestration errors."""


class InvalidPointInTimeAlignmentRequestError(PointInTimeAlignmentError):
    """Raised when a PointInTimeAlignmentRequest fails validation."""


class MissingHoldingsSnapshotError(PointInTimeAlignmentError):
    """Raised when no eligible holdings snapshot is found for a request."""

    def __init__(self, fund_id: str, source_id: str, prediction_timestamp: datetime) -> None:
        self.fund_id = fund_id
        self.source_id = source_id
        self.prediction_timestamp = prediction_timestamp
        super().__init__(
            f"no eligible holdings snapshot found for fund_id={fund_id!r}, "
            f"source_id={source_id!r} at "
            f"prediction_timestamp={prediction_timestamp.isoformat()}"
        )
