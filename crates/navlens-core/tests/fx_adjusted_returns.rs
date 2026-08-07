use navlens_core::{
    CoreError, DecimalReturn, FxAdjustedPeriodReturn, FxRate, GrossReturnComponent, UnitPrice,
    calculate_decimal_return, calculate_fx_decimal_return,
};

const TOLERANCE: f64 = 1e-12;

fn decimal_return(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return must be finite")
}

fn assert_close(actual: f64, expected: f64) {
    assert!(
        (actual - expected).abs() <= TOLERANCE,
        "expected {expected}, got {actual}"
    );
}

fn adjusted(security: f64, fx: f64) -> FxAdjustedPeriodReturn {
    FxAdjustedPeriodReturn::calculate(decimal_return(security), decimal_return(fx))
        .expect("test inputs must produce a valid adjusted return")
}

#[test]
fn calculates_positive_fx_decimal_return() {
    let result =
        calculate_fx_decimal_return(FxRate::new(30.0).unwrap(), FxRate::new(33.0).unwrap())
            .unwrap();

    assert_close(result.value(), 0.10);
}

#[test]
fn calculates_negative_fx_decimal_return() {
    let result =
        calculate_fx_decimal_return(FxRate::new(33.0).unwrap(), FxRate::new(30.0).unwrap())
            .unwrap();

    assert_close(result.value(), (30.0 / 33.0) - 1.0);
}

#[test]
fn calculates_flat_fx_decimal_return() {
    let rate = FxRate::new(30.0).unwrap();

    assert_close(
        calculate_fx_decimal_return(rate, rate).unwrap().value(),
        0.0,
    );
}

#[test]
fn preserves_unit_price_return_behavior() {
    let result = calculate_decimal_return(
        UnitPrice::new(100.0).unwrap(),
        UnitPrice::new(110.0).unwrap(),
    )
    .unwrap();

    assert_close(result.value(), 0.10);
}

#[test]
fn composes_security_and_fx_gains_multiplicatively() {
    assert_close(adjusted(0.10, 0.10).decimal_return().value(), 0.21);
}

#[test]
fn composes_security_loss_and_fx_gain_multiplicatively() {
    assert_close(adjusted(-0.10, 0.10).decimal_return().value(), -0.01);
}

#[test]
fn preserves_single_component_and_flat_returns() {
    assert_close(adjusted(0.10, 0.0).decimal_return().value(), 0.10);
    assert_close(adjusted(0.0, 0.10).decimal_return().value(), 0.10);
    assert_close(adjusted(0.0, 0.0).decimal_return().value(), 0.0);
}

#[test]
fn composes_negative_fx_return_multiplicatively() {
    assert_close(adjusted(0.20, -0.10).decimal_return().value(), 0.08);
}

#[test]
fn rejects_security_return_at_or_below_negative_one() {
    for value in [-1.0, -1.25] {
        assert_eq!(
            FxAdjustedPeriodReturn::calculate(decimal_return(value), decimal_return(0.05)),
            Err(CoreError::NonPositiveGrossReturn {
                component: GrossReturnComponent::Security,
                decimal_return: value,
            })
        );
    }
}

#[test]
fn rejects_fx_return_at_or_below_negative_one() {
    for value in [-1.0, -1.25] {
        assert_eq!(
            FxAdjustedPeriodReturn::calculate(decimal_return(0.05), decimal_return(value)),
            Err(CoreError::NonPositiveGrossReturn {
                component: GrossReturnComponent::ForeignExchange,
                decimal_return: value,
            })
        );
    }
}

#[test]
fn validates_security_before_fx_when_both_are_invalid() {
    assert_eq!(
        FxAdjustedPeriodReturn::calculate(decimal_return(-1.0), decimal_return(-1.0)),
        Err(CoreError::NonPositiveGrossReturn {
            component: GrossReturnComponent::Security,
            decimal_return: -1.0,
        })
    );
}

#[test]
fn rejects_non_finite_composed_result() {
    assert_eq!(
        FxAdjustedPeriodReturn::calculate(decimal_return(f64::MAX), decimal_return(f64::MAX),),
        Err(CoreError::NonFiniteNumber)
    );
}

#[test]
fn exposes_the_canonical_calculated_decimal_return() {
    let result = adjusted(0.25, -0.20);

    assert_close(result.decimal_return().value(), 0.0);
}
