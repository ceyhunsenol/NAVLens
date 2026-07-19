import pytest
from navlens import (
    MarketDate,
    ModelDescriptor,
    NavlensValidationError,
    PredictionRequest,
    UtcTimestamp,
    create_return_prediction,
)


def test_builds_auditable_prediction_request_in_rust() -> None:
    request = PredictionRequest(
        "TRY-FUND-1",
        MarketDate(2026, 7, 19),
        MarketDate(2026, 7, 20),
        UtcTimestamp(2_000),
        UtcTimestamp(1_900),
    )

    assert request.fund_id == "TRY-FUND-1"
    assert str(request.prediction_date) == "2026-07-19"
    assert str(request.target_date) == "2026-07-20"
    assert request.generated_at.unix_seconds == 2_000
    assert request.data_as_of.unix_seconds == 1_900


def test_rejects_future_data_in_python_boundary() -> None:
    with pytest.raises(NavlensValidationError, match="must not be later"):
        PredictionRequest(
            "TRY-FUND-1",
            MarketDate(2026, 7, 19),
            MarketDate(2026, 7, 20),
            UtcTimestamp(2_000),
            UtcTimestamp(2_001),
        )


def test_builds_validated_return_prediction_in_rust() -> None:
    model = ModelDescriptor("ridge-baseline", "0.1.0", "market-v1")
    prediction = create_return_prediction(0.01, -0.02, 0.03, 0.9, model)

    assert prediction.expected_return == pytest.approx(0.01)
    assert prediction.lower_bound == pytest.approx(-0.02)
    assert prediction.upper_bound == pytest.approx(0.03)
    assert prediction.confidence_level == pytest.approx(0.9)
    assert prediction.model.name == "ridge-baseline"
    assert prediction.model.version == "0.1.0"
    assert prediction.model.feature_set_version == "market-v1"


def test_rejects_point_estimate_outside_interval() -> None:
    model = ModelDescriptor("ridge-baseline", "0.1.0", "market-v1")

    with pytest.raises(NavlensValidationError, match="inside prediction interval"):
        create_return_prediction(0.04, -0.02, 0.03, 0.9, model)
