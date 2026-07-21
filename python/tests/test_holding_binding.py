import pytest
from navlens import AssetClass, HoldingPosition, NavlensValidationError


@pytest.mark.parametrize(
    "name",
    [
        "equity",
        "debt_security",
        "repo",
        "deposit",
        "investment_fund",
        "exchange_traded_fund",
        "precious_metal",
        "derivative",
        "cash",
        "other",
    ],
)
def test_round_trips_supported_asset_classes(name: str) -> None:
    asset_class = AssetClass(name)

    assert asset_class.name == name
    assert str(asset_class) == name


def test_constructs_asset_class_and_holding_position() -> None:
    asset_class = AssetClass("equity")
    position = HoldingPosition("US67066G1040", asset_class, 0.0544)

    assert asset_class.name == "equity"
    assert position.instrument_id == "US67066G1040"
    assert position.asset_class == asset_class
    assert position.fund_total_weight == pytest.approx(0.0544)


def test_rejects_invalid_instrument_identifier() -> None:
    with pytest.raises(NavlensValidationError, match="whitespace"):
        HoldingPosition("AAPL US", AssetClass("equity"), 0.05)


def test_rejects_weight_below_zero() -> None:
    with pytest.raises(NavlensValidationError, match="weight"):
        HoldingPosition("US67066G1040", AssetClass("equity"), -0.01)


def test_rejects_weight_above_one() -> None:
    with pytest.raises(NavlensValidationError, match="weight"):
        HoldingPosition("US67066G1040", AssetClass("equity"), 1.01)


def test_rejects_invalid_asset_class_input() -> None:
    with pytest.raises(NavlensValidationError, match="unknown asset class"):
        AssetClass("stock")


def test_requires_validated_asset_class_for_holding_position() -> None:
    with pytest.raises(TypeError):
        HoldingPosition("US67066G1040", "equity", 0.05)  # type: ignore[arg-type]


def test_preserves_decimal_weight_units() -> None:
    position = HoldingPosition("US67066G1040", AssetClass("debt_security"), 0.0544)

    assert position.fund_total_weight == pytest.approx(0.0544)


def test_preserves_cash_classification_on_holding_position() -> None:
    position = HoldingPosition("TRY", AssetClass("cash"), 0.10)

    assert position.asset_class.name == "cash"
