use navlens_core::{CoreError, DecimalReturn, PortfolioComponent, PortfolioEstimate};

fn decimal_return(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return should be finite")
}

#[test]
fn calculates_weighted_return_after_expenses() {
    let components = [
        PortfolioComponent {
            weight: 0.7,
            market_return: decimal_return(0.02),
        },
        PortfolioComponent {
            weight: 0.2,
            market_return: decimal_return(-0.01),
        },
        PortfolioComponent {
            weight: 0.1,
            market_return: decimal_return(0.001),
        },
    ];
    let estimate = PortfolioEstimate {
        components: &components,
        daily_expense_rate: decimal_return(0.0001),
    };

    let result = estimate.calculate().expect("valid portfolio");
    assert!((result.value() - 0.012).abs() < 1e-12);
}

#[test]
fn rejects_invalid_weight_sum() {
    let components = [PortfolioComponent {
        weight: 0.8,
        market_return: decimal_return(0.01),
    }];
    let estimate = PortfolioEstimate {
        components: &components,
        daily_expense_rate: decimal_return(0.0),
    };

    assert_eq!(
        estimate.calculate(),
        Err(CoreError::WeightsDoNotSumToOne(0.8))
    );
}

#[test]
fn rejects_non_finite_returns() {
    assert_eq!(
        DecimalReturn::new(f64::NAN),
        Err(CoreError::NonFiniteNumber)
    );
}
