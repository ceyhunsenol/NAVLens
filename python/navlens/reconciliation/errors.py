"""Typed errors for point-in-time fund-return reconciliation."""

from datetime import datetime

from navlens import MarketDate


class PointInTimeReconciliationError(Exception):
    """Base error for Python point-in-time reconciliation orchestration."""


class InvalidFundPriceSourceError(PointInTimeReconciliationError):
    """Raised when the requested fund-price source identifier is invalid."""

    def __init__(self, source_id: object) -> None:
        self.source_id = source_id
        super().__init__(f"fund_price_source_id must be a non-empty string; got {source_id!r}")


class MissingExactFundUnitPriceSnapshotError(PointInTimeReconciliationError):
    """Raised when an exact period-boundary fund-price snapshot is unavailable."""

    def __init__(
        self,
        fund_id: str,
        source_id: str,
        required_date: MarketDate,
        prediction_timestamp: datetime,
    ) -> None:
        self.fund_id = fund_id
        self.source_id = source_id
        self.required_date = required_date
        self.prediction_timestamp = prediction_timestamp
        super().__init__(
            f"no exact fund unit-price snapshot found for fund_id={fund_id!r}, "
            f"source_id={source_id!r}, required_date={required_date} at "
            f"prediction_timestamp={prediction_timestamp.isoformat()}"
        )


class UnexpectedNativeReturnCardinalityError(PointInTimeReconciliationError):
    """Raised when two exact observations do not produce one native period return."""

    def __init__(self, actual_count: int) -> None:
        self.expected_count = 1
        self.actual_count = actual_count
        super().__init__(
            "native period-return calculation produced an unexpected result count: "
            f"expected 1, got {actual_count}"
        )
