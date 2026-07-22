from datetime import UTC, datetime

import pytest
from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    InvalidPointInTimeAlignmentRequestError,
    MarketDate,
    PointInTimeAlignmentRequest,
    PriceAdjustment,
)


def policy() -> AlignmentPolicy:
    return AlignmentPolicy(
        CurrencyCode("TRY"),
        PriceAdjustment("total_return_adjusted"),
        MarketDate(2026, 1, 31),
        2,
        5,
    )


def request(**overrides: object) -> PointInTimeAlignmentRequest:
    values = {
        "fund_id": "AAL",
        "prediction_timestamp": datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
        "holdings_source_id": "kap",
        "security_price_source_id": "market",
        "policy": policy(),
    }
    values.update(overrides)
    return PointInTimeAlignmentRequest(**values)  # type: ignore[arg-type]


def test_accepts_valid_request() -> None:
    result = request()

    assert result.fund_id == "AAL"
    assert result.policy.pricing_as_of_date == MarketDate(2026, 1, 31)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fund_id", ""),
        ("holdings_source_id", " "),
        ("security_price_source_id", ""),
    ],
)
def test_rejects_blank_identifiers(field: str, value: str) -> None:
    with pytest.raises(InvalidPointInTimeAlignmentRequestError, match=field):
        request(**{field: value})


def test_rejects_non_policy_value() -> None:
    with pytest.raises(InvalidPointInTimeAlignmentRequestError, match="policy"):
        request(policy="not-a-policy")


def test_rejects_non_utc_prediction_timestamp() -> None:
    with pytest.raises(InvalidPointInTimeAlignmentRequestError, match="timezone"):
        request(prediction_timestamp=datetime(2026, 2, 1, 12, 0))
