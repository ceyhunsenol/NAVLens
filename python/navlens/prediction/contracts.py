"""Immutable result contract for single return predictions."""

from dataclasses import dataclass
from datetime import datetime

from navlens import MarketDate, PredictionRequest, ReturnPrediction
from navlens._timestamps import datetime_to_utc_timestamp
from navlens.datasets.fund_unit_price_snapshots import FundUnitPriceSnapshot


@dataclass(frozen=True, slots=True)
class SingleReturnPredictionResult:
    """Immutable provenance envelope for one point-in-time return prediction."""

    request: PredictionRequest
    prediction: ReturnPrediction
    source_id: str
    prediction_timestamp: datetime
    pricing_as_of_date: MarketDate
    selected_snapshots: tuple[FundUnitPriceSnapshot, ...]
    training_return_count: int
    training_target_start_date: MarketDate
    training_target_end_date: MarketDate
    lookback: int
    target_definition: str

    def __post_init__(self) -> None:
        if not isinstance(self.request, PredictionRequest):
            raise ValueError("request must be a PredictionRequest instance")
        if not isinstance(self.prediction, ReturnPrediction):
            raise ValueError("prediction must be a ReturnPrediction instance")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        if not isinstance(self.target_definition, str) or not self.target_definition.strip():
            raise ValueError("target_definition must be a non-empty string")
        if not isinstance(self.pricing_as_of_date, MarketDate):
            raise ValueError("pricing_as_of_date must be a MarketDate instance")
        if not isinstance(self.training_target_start_date, MarketDate):
            raise ValueError("training_target_start_date must be a MarketDate instance")
        if not isinstance(self.training_target_end_date, MarketDate):
            raise ValueError("training_target_end_date must be a MarketDate instance")

        pred_ts = datetime_to_utc_timestamp(
            self.prediction_timestamp, "prediction_timestamp", ValueError
        )

        if (
            not isinstance(self.lookback, int)
            or isinstance(self.lookback, bool)
            or self.lookback < 1
        ):
            raise ValueError("lookback must be a positive integer")

        if not isinstance(self.training_return_count, int) or isinstance(
            self.training_return_count, bool
        ):
            raise ValueError("training_return_count must be an integer")

        if not isinstance(self.selected_snapshots, tuple) or not self.selected_snapshots:
            raise ValueError(
                "selected_snapshots must be a non-empty tuple of FundUnitPriceSnapshot"
            )

        expected_fund_id = self.request.fund_id
        last_date: MarketDate | None = None
        for snapshot in self.selected_snapshots:
            if not isinstance(snapshot, FundUnitPriceSnapshot):
                raise ValueError(
                    "selected_snapshots elements must be FundUnitPriceSnapshot instances"
                )
            if snapshot.fund_id != expected_fund_id:
                raise ValueError(
                    f"snapshot fund_id '{snapshot.fund_id}' does not match "
                    f"request '{expected_fund_id}'"
                )
            if snapshot.source_id != self.source_id:
                raise ValueError(
                    f"snapshot source_id '{snapshot.source_id}' does not match "
                    f"result '{self.source_id}'"
                )

            if last_date is not None and snapshot.observation.date <= last_date:
                raise ValueError("selected_snapshots market dates must be strictly increasing")
            last_date = snapshot.observation.date

        last_snap = self.selected_snapshots[-1]
        if last_snap.observation.date > self.pricing_as_of_date:
            raise ValueError("last observation date cannot exceed pricing_as_of_date")
        if last_snap.observation.date > self.request.prediction_date:
            raise ValueError("last observation date cannot exceed request.prediction_date")
        if self.pricing_as_of_date > self.request.prediction_date:
            raise ValueError("pricing_as_of_date cannot exceed request.prediction_date")

        data_as_of_ts = datetime_to_utc_timestamp(
            self.actual_data_as_of, "actual_data_as_of", ValueError
        )

        if self.request.generated_at.unix_seconds != pred_ts.unix_seconds:
            raise ValueError("request.generated_at timestamp mismatch with prediction_timestamp")

        if self.request.data_as_of.unix_seconds != data_as_of_ts.unix_seconds:
            raise ValueError("request.data_as_of timestamp mismatch with max selected available_at")

        if self.training_return_count != self.canonical_return_count:
            raise ValueError(
                f"training_return_count ({self.training_return_count}) must equal "
                f"canonical_return_count ({self.canonical_return_count})"
            )

        if self.training_target_row_count < 3:
            raise ValueError(
                f"training_target_row_count ({self.training_target_row_count}) must be at least 3"
            )

        expected_start = self.selected_snapshots[self.lookback + 1].observation.date
        if self.training_target_start_date != expected_start:
            raise ValueError(
                f"training_target_start_date ({self.training_target_start_date}) must match "
                f"selected_snapshots[lookback + 1].observation.date ({expected_start})"
            )

        expected_end = self.selected_snapshots[-1].observation.date
        if self.training_target_end_date != expected_end:
            raise ValueError(
                f"training_target_end_date ({self.training_target_end_date}) must match "
                f"selected_snapshots[-1].observation.date ({expected_end})"
            )

    @property
    def selected_snapshot_count(self) -> int:
        return len(self.selected_snapshots)

    @property
    def canonical_return_count(self) -> int:
        return len(self.selected_snapshots) - 1

    @property
    def training_target_row_count(self) -> int:
        return self.training_return_count - self.lookback

    @property
    def actual_data_as_of(self) -> datetime:
        return max(s.available_at for s in self.selected_snapshots)

    @property
    def last_observation_date(self) -> MarketDate:
        return self.selected_snapshots[-1].observation.date

    @property
    def last_observation_available_at(self) -> datetime:
        return self.selected_snapshots[-1].available_at

    @property
    def last_observation_ingested_at(self) -> datetime:
        return self.selected_snapshots[-1].ingested_at

    @property
    def fund_id(self) -> str:
        return self.request.fund_id

    @property
    def prediction_date(self) -> MarketDate:
        return self.request.prediction_date

    @property
    def target_date(self) -> MarketDate:
        return self.request.target_date

    @property
    def model_name(self) -> str:
        return self.prediction.model.name

    @property
    def model_version(self) -> str:
        return self.prediction.model.version

    @property
    def feature_schema_version(self) -> str:
        return self.prediction.model.feature_set_version

    @property
    def confidence_level(self) -> float:
        return self.prediction.confidence_level

    @property
    def expected_return_decimal(self) -> float:
        return self.prediction.expected_return

    @property
    def prediction_interval_lower_decimal(self) -> float:
        return self.prediction.lower_bound

    @property
    def prediction_interval_upper_decimal(self) -> float:
        return self.prediction.upper_bound
