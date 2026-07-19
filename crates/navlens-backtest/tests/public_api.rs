use navlens_backtest::{BacktestError, Observation, evaluate};
use navlens_core::DecimalReturn;

fn return_of(value: f64) -> DecimalReturn {
    DecimalReturn::new(value).expect("test return should be finite")
}

#[test]
fn evaluates_prediction_metrics() {
    let observations = [
        Observation {
            predicted: return_of(0.01),
            actual: return_of(0.02),
        },
        Observation {
            predicted: return_of(-0.02),
            actual: return_of(-0.01),
        },
        Observation {
            predicted: return_of(0.01),
            actual: return_of(-0.01),
        },
    ];

    let metrics = evaluate(&observations).expect("non-empty observations");
    assert_eq!(metrics.sample_count, 3);
    assert!((metrics.mean_absolute_error - (0.04 / 3.0)).abs() < 1e-12);
    assert!((metrics.root_mean_squared_error - (0.0006_f64 / 3.0).sqrt()).abs() < 1e-12);
    assert!((metrics.direction_accuracy - (2.0 / 3.0)).abs() < 1e-12);
}

#[test]
fn rejects_empty_backtest() {
    assert_eq!(evaluate(&[]), Err(BacktestError::NoObservations));
}
