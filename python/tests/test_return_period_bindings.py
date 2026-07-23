import pytest
from navlens import (
    MarketDate,
    NavlensValidationError,
    PeriodDecimalReturn,
    ReturnPeriod,
)


def test_valid_return_period() -> None:
    start = MarketDate(2026, 1, 1)
    end = MarketDate(2026, 1, 2)
    period = ReturnPeriod(start, end)

    assert period.period_start_date == start
    assert period.period_end_date == end
    expected_repr = (
        "ReturnPeriod("
        "period_start_date=MarketDate('2026-01-01'), "
        "period_end_date=MarketDate('2026-01-02'))"
    )
    assert repr(period) == expected_repr
    assert period == ReturnPeriod(start, end)
    assert hash(period) == hash(ReturnPeriod(start, end))


def test_rejects_same_date_return_period() -> None:
    d = MarketDate(2026, 1, 1)
    with pytest.raises(NavlensValidationError):
        ReturnPeriod(d, d)


def test_rejects_reversed_dates_return_period() -> None:
    d1 = MarketDate(2026, 1, 1)
    d2 = MarketDate(2026, 1, 2)
    with pytest.raises(NavlensValidationError):
        ReturnPeriod(d2, d1)


def test_period_decimal_return_preserves_fields() -> None:
    start = MarketDate(2026, 1, 1)
    end = MarketDate(2026, 1, 2)
    period = ReturnPeriod(start, end)
    ret = PeriodDecimalReturn(period, 0.05)

    assert ret.period == period
    assert ret.period_start_date == start
    assert ret.period_end_date == end
    assert ret.return_decimal == pytest.approx(0.05)
    expected_repr = (
        "PeriodDecimalReturn("
        "period=ReturnPeriod(period_start_date=MarketDate('2026-01-01'), "
        "period_end_date=MarketDate('2026-01-02')), "
        "return_decimal=0.05)"
    )
    assert repr(ret) == expected_repr


def test_period_decimal_return_negative_return() -> None:
    start = MarketDate(2026, 1, 1)
    end = MarketDate(2026, 1, 2)
    period = ReturnPeriod(start, end)
    ret = PeriodDecimalReturn(period, -0.15)

    assert ret.return_decimal == pytest.approx(-0.15)


@pytest.mark.parametrize("invalid_ret", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_decimal_return(invalid_ret: float) -> None:
    period = ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    with pytest.raises(NavlensValidationError, match="number must be finite"):
        PeriodDecimalReturn(period, invalid_ret)


def test_python_export_and_wrapper_type_safety() -> None:
    from navlens import PeriodDecimalReturn as ExportedPeriodDecimalReturn
    from navlens import ReturnPeriod as ExportedReturnPeriod

    period = ExportedReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2))
    pdr = ExportedPeriodDecimalReturn(period, 0.02)

    assert isinstance(period, ExportedReturnPeriod)
    assert isinstance(pdr, ExportedPeriodDecimalReturn)

    with pytest.raises(TypeError):
        ReturnPeriod("2026-01-01", MarketDate(2026, 1, 2))  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        PeriodDecimalReturn("invalid_period", 0.02)  # type: ignore[arg-type]
